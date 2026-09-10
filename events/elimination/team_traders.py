"""Shared query: active TE traders on a given Elimination team.

Used by both the ``/events/elimination/`` page and the ``/api/team_traders``
endpoint so the two never drift.
"""
from __future__ import annotations

from django.db.models import OuterRef, Subquery

from events import config

EVENT_KEY = "elimination"


def team_traders_for(team_name: str, year: int | None = None):
    """Return a list of dicts describing active traders on ``team_name``.

    Mirrors the filters used by ``/api/active_traders`` (active_trader flag +
    non-negative vote score).
    """
    from users.models import Profile
    from main.models import TradeReceipt
    from events.models import EventParticipation, EventTraderSettings

    if not team_name:
        return []
    year = year or config.ELIMINATION_YEAR

    last_receipt_qs = (
        TradeReceipt.objects.filter(owner=OuterRef("pk"))
        .order_by("-created_at")
        .values("created_at")[:1]
    )

    profiles = (
        Profile.objects.filter(
            active_trader=True,
            event_participations__event_key=EVENT_KEY,
            event_participations__year=year,
            event_participations__group_name=team_name,
        )
        .annotate(last_receipt_at=Subquery(last_receipt_qs))
        .distinct()
    )
    profiles = [p for p in profiles if (p.vote_score or 0) >= 0]

    discount_by_profile = {
        s.profile_id: s.group_discount_pct
        for s in EventTraderSettings.objects.filter(
            event_key=EVENT_KEY, year=year, profile__in=profiles
        )
    }

    rows = []
    for p in profiles:
        rows.append(
            {
                "torn_id": int(p.torn_id) if p.torn_id else None,
                "name": p.name,
                "activity_status": p.activity_status,
                "votes": p.vote_score,
                "team_discount": discount_by_profile.get(p.id, 0),
                "price_list_url": f"https://tornexchange.com/prices/{p.torn_id}",
                "last_trade": int(p.last_receipt_at.timestamp()) if p.last_receipt_at else None,
            }
        )
    rows.sort(key=lambda r: (-(r["votes"] or 0), r["name"].lower() if r["name"] else ""))
    return rows


def all_participating_traders(year: int | None = None):
    """Every active TE trader who has an Elimination team this year, grouped.

    Returns ``(teams, totals)`` where ``teams`` is a list of
    ``{"team": name, "trader_count": n, "discount_count": n, "traders": [...]}``
    ordered by trader count desc, and ``totals`` is a summary dict. Used by the
    public Elimination page.
    """
    from users.models import Profile
    from events.models import EventParticipation, EventTraderSettings

    year = year or config.ELIMINATION_YEAR

    parts = (
        EventParticipation.objects.filter(event_key=EVENT_KEY, year=year)
        .exclude(group_name="")
        .select_related("profile")
    )
    discount_by_profile = {
        s.profile_id: s.group_discount_pct
        for s in EventTraderSettings.objects.filter(event_key=EVENT_KEY, year=year)
        if s.group_discount_pct > 0
    }

    by_team: dict[str, list] = {}
    for part in parts:
        p = part.profile
        if not p.active_trader or (p.vote_score or 0) < 0:
            continue
        by_team.setdefault(part.group_name, []).append(
            {
                "torn_id": int(p.torn_id) if p.torn_id else None,
                "name": p.name,
                "activity_status": p.activity_status,
                "votes": p.vote_score,
                "team_discount": discount_by_profile.get(p.id, 0),
            }
        )

    teams = []
    for name, traders in by_team.items():
        traders.sort(key=lambda r: (-(r["votes"] or 0), (r["name"] or "").lower()))
        teams.append(
            {
                "team": name,
                "trader_count": len(traders),
                "discount_count": sum(1 for t in traders if t["team_discount"]),
                "traders": traders,
            }
        )
    teams.sort(key=lambda t: (-t["trader_count"], t["team"].lower()))

    totals = {
        "trader_count": sum(t["trader_count"] for t in teams),
        "team_count": len(teams),
        "discount_count": sum(t["discount_count"] for t in teams),
    }
    return teams, totals
