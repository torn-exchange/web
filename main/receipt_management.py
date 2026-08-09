import json

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncDate
from django.shortcuts import render

from main.filters import ReceiptSearchFilter
from main.models import ItemTrade, TradeReceipt
from users.models import Profile

RESULTS_PER_PAGE = 25


@login_required
def receipt_management(request):
    """
    Search/management page for a trader's receipts, covering both roles:
    receipts where the logged-in profile is the buyer (`TradeReceipt.owner`,
    a real FK) and receipts where they're the seller (`TradeReceipt.seller`,
    a free-text name matched case-insensitively against `Profile.name` -
    sellers aren't relationally linked yet, see TODO.md Task 6).

    Nothing is queried until the trader actually submits a search - on a
    production-sized receipts table, running the buyer/seller OR query
    unconditionally on every page load (including the bare GET before any
    filter is chosen) was making the page hang for minutes.

    The page (25 rows) is the only thing fetched with items_trades
    prefetched; the result count and both charts are computed as separate
    aggregate queries scoped to the matched receipt ids rather than by
    materializing every matching receipt in Python. A trader with tens of
    thousands of receipts (this codebase's own top traders included) made
    that materialize-then-filter approach take minutes.
    """
    profile = Profile.objects.filter(user=request.user).get()

    has_search = bool(request.GET)

    receipt_filter = ReceiptSearchFilter(
        request.GET if has_search else None,
        queryset=TradeReceipt.objects.none(),
        profile=profile,
    )

    result_count = 0
    histogram_data = []
    item_quantity_data = []
    page_obj = None
    item_name_query = request.GET.get('item_name', '').strip()

    if has_search:
        base_qs = TradeReceipt.objects.filter(
            Q(owner=profile) | Q(seller__iexact=profile.name)
        )
        receipt_filter = ReceiptSearchFilter(request.GET, queryset=base_qs, profile=profile)
        matched_qs = receipt_filter.qs  # already .distinct()'d by the filter

        paginator = Paginator(matched_qs.order_by('-created_at'), RESULTS_PER_PAGE)
        result_count = paginator.count
        page_obj = paginator.get_page(request.GET.get('page'))

        page_pks = [r.pk for r in page_obj.object_list]
        receipts_by_pk = {
            r.pk: r for r in TradeReceipt.objects.filter(pk__in=page_pks)
            .select_related('owner')
            .prefetch_related('items_trades', 'items_trades__item')
        }
        page_receipts = [receipts_by_pk[pk] for pk in page_pks]
        for r in page_receipts:
            r.role = 'buyer' if r.owner_id == profile.id else 'seller'
            # `seller` on the model is always the seller's name, which is the
            # logged-in trader's own name on seller-role rows (that's how
            # those rows were matched in the first place) - the counterparty
            # to show is whoever isn't them: the other party in the trade.
            r.counterparty = r.seller if r.role == 'buyer' else r.owner.name
        page_obj.object_list = page_receipts

        histogram_data = _build_histogram(matched_qs)
        if item_name_query:
            item_quantity_data = _build_item_quantity_series(matched_qs, item_name_query)

    context = {
        'filter': receipt_filter,
        'receipts': page_obj or [],
        'listings': page_obj or [],  # for main/includes/pagination.html
        'result_count': result_count,
        'histogram_data': json.dumps(histogram_data),
        'item_quantity_data': json.dumps(item_quantity_data),
        'searched_item_name': item_name_query if has_search else '',
        'has_search': has_search,
    }
    return render(request, 'main/receipt_management.html', context)


def _build_histogram(matched_qs):
    rows = (
        matched_qs
        .annotate(day=TruncDate('created_at'))
        .values('day')
        .annotate(count=Count('id', distinct=True))
        .order_by('day')
    )
    return [[row['day'].isoformat(), row['count']] for row in rows]


def _build_item_quantity_series(matched_qs, item_name_query):
    """One point per receipt: how many units of the searched item it contains."""
    rows = (
        ItemTrade.objects
        .filter(tradereceipt__in=matched_qs, item__name__icontains=item_name_query)
        .values('tradereceipt', 'tradereceipt__created_at')
        .annotate(qty=Sum('quantity'))
        .order_by('tradereceipt__created_at')
    )
    return [[row['tradereceipt__created_at'].isoformat(), row['qty']] for row in rows]
