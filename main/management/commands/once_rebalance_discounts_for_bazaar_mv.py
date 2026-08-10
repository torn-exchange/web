from django.core.management.base import BaseCommand
from django.utils import timezone

from main.models import Item, Listing
from main.services.api.weav3r.marketplace_api_service import Weav3rMarketplaceApiService

# Discount must stay within the range accepted elsewhere (main/api.py's
# modify_listing), so a rebalance target outside it can't be represented.
MIN_DISCOUNT = -100
MAX_DISCOUNT = 100


def rebalance_discounts_to_preserve_effective_price(item, dry_run=False):
    """
    Recalculates the `discount` on every discount-based Listing for `item` so
    that `effective_price` stays exactly where it was before `item.TE_value`
    just changed, instead of drifting down with it. Fixed-price-only listings
    (discount is None) are untouched, since they were never driven by
    TE_value in the first place.

    Expects `item.TE_value` to already hold the NEW value (it doesn't need to
    be persisted yet -- an in-memory change is enough, see the command below),
    and relies on each Listing's `effective_price` still holding the value
    that was computed under the OLD TE_value.

    Works for all three listing shapes uniformly: discount-only (effective_price
    is the discount price, which gets recalculated to match itself); discount+price
    where discount was binding (same as discount-only); and discount+price where
    the fixed price was binding (the new discount price is set to exactly equal
    price, so `min(discount_price, price)` still resolves to `price`).
    """
    for listing in Listing.objects.filter(item=item, discount__isnull=False).select_related('owner__settings'):
        old_effective_price = listing.effective_price
        if old_effective_price is None or not item.TE_value:
            # Nothing to preserve, or TE_value is 0/None so no discount can hit
            # a nonzero target -- leave the listing for normal recalculation.
            continue

        new_discount = 100.0 - (old_effective_price / item.TE_value * 100.0)

        if new_discount < MIN_DISCOUNT or new_discount > MAX_DISCOUNT:
            print(
                f'Skipping discount rebalance for Listing {listing.id}: required discount '
                f'{new_discount:.2f}% is outside the [{MIN_DISCOUNT}, {MAX_DISCOUNT}] range'
            )
            continue

        new_discount = round(new_discount, 4)
        if dry_run:
            print(f'Would set Listing {listing.id} discount {listing.discount} -> {new_discount}')
            continue

        listing.discount = new_discount
        listing.save(update_fields=['discount', 'effective_price'])

        # Up to ~0.1% rounding drift is expected/accepted; anything more suggests a bug.
        new_effective_price = listing.effective_price or 0
        drift = abs(new_effective_price - old_effective_price)
        tolerance = max(1, abs(old_effective_price) * 0.001)
        if drift > tolerance:
            print(
                f'WARNING: Listing {listing.id} drifted by {drift} after discount rebalance '
                f'(old effective_price={old_effective_price}, new={new_effective_price})'
            )


class Command(BaseCommand):
    help = (
        'One-time deploy-time script for the bazaar_average rollout. Must be run '
        'exactly once, before the first bazaar-aware update_items2 run in production. '
        'Fetches weav3r bazaar averages once and, for every Item where bazaar_average '
        'is lower than the current TE_value (the new value is min(current TE_value, '
        'bazaar_average) -- current TE_value is already min(market_value, itemmarket '
        'price), so the other two sources never need to be re-fetched), rebalances '
        'discount-based listings so their effective_price is preserved, then persists '
        'the new TE_value/bazaar_average/bazaar_fetched_at onto the item. After this '
        'runs, ordinary update_items2 runs handle TE_value/bazaar_average like any '
        'other routine price change, with no special preservation -- this is a one-time '
        'accommodation for the rollout, not a permanent behavior.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Report what would change without writing anything.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        bazaar_by_item_id = Weav3rMarketplaceApiService.get_bazaar_averages_by_item_id()
        if not bazaar_by_item_id:
            self.stdout.write(self.style.WARNING('weav3r returned no data; nothing to do.'))
            return

        items_affected = 0
        for item in Item.objects.exclude(item_id__isnull=True).exclude(TE_value__isnull=True):
            bazaar_average = bazaar_by_item_id.get(item.item_id)
            if not bazaar_average:
                continue

            new_te_value = min(item.TE_value, bazaar_average)
            if new_te_value >= item.TE_value:
                continue  # bazaar_average isn't actually the lowest; nothing changes

            self.stdout.write(
                f'Item(id={item.id}, name={item.name!r}): TE_value {item.TE_value} -> {new_te_value} '
                f'(bazaar_average={bazaar_average})'
            )

            item.TE_value = new_te_value
            if not dry_run:
                # Must be persisted BEFORE rebalancing: rebalance saves each Listing,
                # which recalculates effective_price via self.item.TE_value -- and
                # since the Listing queryset doesn't select_related('item'), that's a
                # fresh DB fetch, not this in-memory `item`. If the new TE_value isn't
                # in the DB yet, every recalculated effective_price would be computed
                # against the stale old value instead.
                item.bazaar_average = bazaar_average
                item.bazaar_fetched_at = timezone.now()
                item.save(update_fields=['TE_value', 'bazaar_average', 'bazaar_fetched_at'])

            rebalance_discounts_to_preserve_effective_price(item, dry_run=dry_run)

            items_affected += 1

        self.stdout.write(self.style.SUCCESS(
            f'{"Would rebalance" if dry_run else "Rebalanced"} {items_affected} item(s)'
        ))
