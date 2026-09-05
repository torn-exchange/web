"""Site-wide, anonymised marketplace stats for the homepage "Torn Market Pulse".

Everything here is aggregate only - trade counts, item totals, money totals,
a daily-trades sparkline and a count of traders online now. No individual trade,
trader name + value + item is ever exposed (that would be an OPSEC / mugging
risk for Torn players). The one list of names shown - "traders online now" - is
the same public "advertising availability" data already surfaced on the
listings and price-list pages, and it is hidden when the online-status cron
looks stale.

Numbers are recomputed out-of-band by ``RefreshMarketStatsJob`` into the
``file`` cache backend, so the homepage view never runs these aggregates. On a
cold cache each getter computes its value inline once and caches it.
"""
from datetime import timedelta

from django.core.cache import caches
from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone

from main.models import ItemTrade, TradeReceipt
from users.models import Profile


def _cache():
    return caches["file"]


CACHE_TTL = 60 * 45  # safety net; the refresh job rewrites these well before expiry
ACTIVITY_KEY = "market_stats:activity"
ONLINE_KEY = "market_stats:online"

DAILY_TRADES_DAYS = 14
ONLINE_TRADERS_LIMIT = 24
# If the newest Profile.updated_at (the online-status cron touches every checked
# profile on each run) is older than this, treat the online list as unreliable.
ONLINE_STALE_AFTER = timedelta(minutes=30)


def format_money(value):
    """Compact currency label, e.g. 2170000000 -> '$2.17b'."""
    value = value or 0
    for threshold, suffix in ((1_000_000_000_000, "t"), (1_000_000_000, "b"), (1_000_000, "m"), (1_000, "k")):
        if abs(value) >= threshold:
            return f"${value / threshold:.2f}{suffix}"
    return f"${value:,}"


def _pct_change(current, previous):
    if not previous:
        return None
    return round((current - previous) / previous * 100, 1)


def _window(start, end=None):
    receipts = TradeReceipt.objects.filter(created_at__gte=start)
    trades_qs = ItemTrade.objects.filter(tradereceipt__created_at__gte=start)
    if end is not None:
        receipts = receipts.filter(created_at__lt=end)
        trades_qs = trades_qs.filter(tradereceipt__created_at__lt=end)
    return {
        "trades": receipts.count(),
        "items": trades_qs.aggregate(q=Sum("quantity"))["q"] or 0,
        "value": receipts.aggregate(v=Sum("total_amount"))["v"] or 0,
    }


def _period(key, label, start, prev_start, compare=True):
    now = timezone.now()
    current = _window(start, now)
    # Comparing a partial day against a full one is misleading, so "today" skips it.
    previous = _window(prev_start, start) if compare else {"trades": None, "value": None}
    return {
        "key": key,
        "label": label,
        "trades": current["trades"],
        "trades_display": f"{current['trades']:,}",
        "items": current["items"],
        "items_display": f"{current['items']:,}",
        "value": current["value"],
        "value_display": format_money(current["value"]),
        "trades_change": _pct_change(current["trades"], previous["trades"]),
        "value_change": _pct_change(current["value"], previous["value"]),
    }


def _daily_trades():
    since = timezone.now() - timedelta(days=DAILY_TRADES_DAYS)
    rows = (
        TradeReceipt.objects.filter(created_at__gte=since)
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(count=Count("id"))
    )
    counts = {r["day"]: r["count"] for r in rows}
    today = timezone.now().date()
    days = [today - timedelta(days=i) for i in range(DAILY_TRADES_DAYS - 1, -1, -1)]
    peak = max([counts.get(d, 0) for d in days] + [1])
    return [
        {
            "label": d.strftime("%b %d"),
            "count": counts.get(d, 0),
            "height_pct": round(counts.get(d, 0) / peak * 100),
        }
        for d in days
    ]


def _biggest_today():
    start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    receipt = (
        TradeReceipt.objects.filter(created_at__gte=start, total_amount__isnull=False)
        .order_by("-total_amount")
        .first()
    )
    if not receipt or not receipt.total_amount:
        return None
    item_count = receipt.items_trades.count()
    return {
        "value_display": format_money(receipt.total_amount),
        "item_count": item_count,
    }


def compute_activity():
    now = timezone.now()
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = midnight - timedelta(days=6)
    month_start = midnight - timedelta(days=29)

    data = {
        "periods": [
            _period("today", "Today", midnight, midnight - timedelta(days=1), compare=False),
            _period("week", "Last 7 days", week_start, week_start - timedelta(days=7)),
            _period("month", "Last 30 days", month_start, month_start - timedelta(days=30)),
        ],
        "daily_trades": _daily_trades(),
        "biggest_today": _biggest_today(),
        "generated_at": now.isoformat(),
    }
    _cache().set(ACTIVITY_KEY, data, CACHE_TTL)
    return data


def compute_online():
    keyed = Profile.objects.exclude(api_key="").exclude(api_key__isnull=True)
    latest_check = keyed.order_by("-updated_at").values_list("updated_at", flat=True).first()
    stale = latest_check is None or (timezone.now() - latest_check) > ONLINE_STALE_AFTER

    traders = []
    if not stale:
        recent_cutoff = timezone.now() - timedelta(minutes=20)
        online_qs = keyed.filter(
            active_trader=True,
            activity_status="Online",
            last_active__gte=recent_cutoff,
        ).order_by("-vote_score")
        traders = [
            {"name": p.name, "vote_score": p.vote_score}
            for p in online_qs[:ONLINE_TRADERS_LIMIT]
        ]
        count = online_qs.count()
    else:
        count = 0

    data = {
        "stale": stale,
        "count": count,
        "traders": traders,
        "overflow": max(0, count - len(traders)),
        "checked_at": latest_check.isoformat() if latest_check else None,
    }
    _cache().set(ONLINE_KEY, data, CACHE_TTL)
    return data


def refresh_all():
    """Called by the scheduled job."""
    compute_activity()
    compute_online()


# --- read helpers used by views (cache-first, compute-on-miss) -----------------

def get_activity():
    return _cache().get(ACTIVITY_KEY) or compute_activity()


def get_online():
    cached = _cache().get(ONLINE_KEY)
    return cached if cached is not None else compute_online()
