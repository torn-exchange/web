import json
from collections import defaultdict

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render

from main.filters import ReceiptSearchFilter
from main.models import TradeReceipt
from users.models import Profile

RESULTS_PER_PAGE = 25


@login_required
def receipt_management(request):
    """
    Search/management page for a trader's receipts, covering both roles:
    receipts where the logged-in profile is the buyer (`TradeReceipt.owner`,
    a real FK) and receipts where they're the seller (`TradeReceipt.seller`,
    a free-text name matched case-insensitively against `Profile.name` -
    sellers aren't linked relationally yet, see TODO.md Task 6).
    """
    profile = Profile.objects.filter(user=request.user).get()

    # Nothing is queried until the trader actually submits a search - on a
    # production-sized receipts table, running the buyer/seller OR query
    # unconditionally on every page load (including the bare GET before any
    # filter is chosen) was making the page hang for minutes.
    has_search = bool(request.GET)

    receipt_filter = ReceiptSearchFilter(
        request.GET if has_search else None,
        queryset=TradeReceipt.objects.none(),
        profile=profile,
    )
    receipts = []

    if has_search:
        base_qs = TradeReceipt.objects.filter(
            Q(owner=profile) | Q(seller__iexact=profile.name)
        ).select_related('owner').prefetch_related('items_trades', 'items_trades__item')

        receipt_filter = ReceiptSearchFilter(request.GET, queryset=base_qs, profile=profile)
        receipts = list(receipt_filter.qs.order_by('-created_at'))

        # Amount filtering happens in Python: `TradeReceipt.total` is a Python
        # property summed over the prefetched items_trades. A DB-side Sum()
        # annotation over the same items_trades M2M would be corrupted by the
        # item_name/quantity filters above joining that relation a second time
        # (row fan-out inflates the sum). Per-trader receipt counts are bounded
        # (thousands, not millions), so filtering the already-narrowed list in
        # Python is cheap and avoids that correctness trap.
        amount_min = _parse_int(request.GET.get('amount_min'))
        amount_max = _parse_int(request.GET.get('amount_max'))
        if amount_min is not None:
            receipts = [r for r in receipts if r.total >= amount_min]
        if amount_max is not None:
            receipts = [r for r in receipts if r.total <= amount_max]

        for r in receipts:
            r.role = 'buyer' if r.owner_id == profile.id else 'seller'

    histogram_data = _build_histogram(receipts)

    paginator = Paginator(receipts, RESULTS_PER_PAGE)
    page = request.GET.get('page')
    results = paginator.get_page(page)

    context = {
        'filter': receipt_filter,
        'receipts': results,
        'listings': results,  # for main/includes/pagination.html
        'result_count': len(receipts),
        'histogram_data': json.dumps(histogram_data),
        'has_search': has_search,
    }
    return render(request, 'main/receipt_management.html', context)


def _parse_int(value):
    if value in (None, ''):
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _build_histogram(receipts):
    counts_by_day = defaultdict(int)
    for r in receipts:
        day = r.created_at.date().isoformat()
        counts_by_day[day] += 1
    return [[day, count] for day, count in sorted(counts_by_day.items())]
