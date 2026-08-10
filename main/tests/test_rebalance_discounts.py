from django.contrib.auth.models import User
from django.test import TestCase

from main.management.commands.once_rebalance_discounts_for_bazaar_mv import (
    rebalance_discounts_to_preserve_effective_price,
)
from main.models import Item, Listing


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_user(username):
    user = User.objects.create(username=username)
    profile = user.profile
    profile.name = username
    profile.torn_id = username
    profile.save()
    return profile


def make_item(name='Test Item', item_id=1, te_value=100_000):
    return Item.objects.create(
        name=name,
        description='',
        requirement='',
        item_type='Melee',
        weapon_type=None,
        buy_price=0,
        sell_price=0,
        market_value=te_value,
        circulation=10000,
        image_url='',
        TE_value=te_value,
        item_id=item_id,
    )


def make_listing(profile, item, price=None, discount=None):
    return Listing.objects.create(owner=profile, item=item, price=price, discount=discount)


def drop_te_value(item, new_te_value):
    """Simulate the item's TE_value changing (e.g. bazaar_average folded in)
    without touching any Listing, mirroring the state rebalance runs against."""
    Item.objects.filter(pk=item.pk).update(TE_value=new_te_value)
    item.refresh_from_db()
    return item


# ---------------------------------------------------------------------------
# rebalance_discounts_to_preserve_effective_price
# ---------------------------------------------------------------------------

class RebalanceDiscountsTests(TestCase):

    def setUp(self):
        self.profile = make_user('trader1')

    def test_fixed_price_only_listing_untouched(self):
        item = make_item(te_value=100_000)
        listing = make_listing(self.profile, item, price=80_000, discount=None)
        old_effective_price = listing.effective_price

        item = drop_te_value(item, 40_000)
        rebalance_discounts_to_preserve_effective_price(item)

        listing.refresh_from_db()
        self.assertIsNone(listing.discount)
        self.assertEqual(listing.price, 80_000)
        self.assertEqual(listing.effective_price, old_effective_price)

    def test_discount_only_effective_price_preserved(self):
        item = make_item(te_value=100_000)
        listing = make_listing(self.profile, item, price=None, discount=10.0)
        old_effective_price = listing.effective_price  # 90_000
        self.assertEqual(old_effective_price, 90_000)

        item = drop_te_value(item, 50_000)
        rebalance_discounts_to_preserve_effective_price(item)

        listing.refresh_from_db()
        self.assertEqual(listing.effective_price, old_effective_price)
        # sanity: new discount should be much steeper against the lower TE_value
        self.assertLess(listing.discount, 10.0)

    def test_price_was_binding_stays_binding_after_rebalance(self):
        # discount_price = 90_000, fixed price = 50_000 -> price binds, effective_price = 50_000
        item = make_item(te_value=100_000)
        listing = make_listing(self.profile, item, price=50_000, discount=10.0)
        old_effective_price = listing.effective_price
        self.assertEqual(old_effective_price, 50_000)

        item = drop_te_value(item, 40_000)
        rebalance_discounts_to_preserve_effective_price(item)

        listing.refresh_from_db()
        self.assertEqual(listing.effective_price, 50_000)
        self.assertEqual(listing.price, 50_000)

    def test_out_of_range_discount_is_skipped(self):
        # Preserving a high effective_price against a near-zero new TE_value would
        # require a discount far outside [-100, 100] -- must be left untouched.
        item = make_item(te_value=100_000)
        listing = make_listing(self.profile, item, price=None, discount=10.0)
        original_discount = listing.discount

        item = drop_te_value(item, 100)
        rebalance_discounts_to_preserve_effective_price(item)

        listing.refresh_from_db()
        self.assertEqual(listing.discount, original_discount)

    def test_te_value_zero_is_skipped_without_crashing(self):
        item = make_item(te_value=100_000)
        listing = make_listing(self.profile, item, price=None, discount=10.0)
        original_discount = listing.discount

        item = drop_te_value(item, 0)
        rebalance_discounts_to_preserve_effective_price(item)

        listing.refresh_from_db()
        self.assertEqual(listing.discount, original_discount)

    def test_listing_with_no_price_or_discount_untouched(self):
        item = make_item(te_value=100_000)
        listing = make_listing(self.profile, item, price=None, discount=None)

        item = drop_te_value(item, 40_000)
        rebalance_discounts_to_preserve_effective_price(item)

        listing.refresh_from_db()
        self.assertIsNone(listing.discount)
        self.assertIsNone(listing.effective_price)

    def test_dry_run_leaves_listing_unchanged(self):
        item = make_item(te_value=100_000)
        listing = make_listing(self.profile, item, price=None, discount=10.0)
        original_discount = listing.discount
        original_effective_price = listing.effective_price

        item = drop_te_value(item, 50_000)
        rebalance_discounts_to_preserve_effective_price(item, dry_run=True)

        listing.refresh_from_db()
        self.assertEqual(listing.discount, original_discount)
        self.assertEqual(listing.effective_price, original_effective_price)


# ---------------------------------------------------------------------------
# once_rebalance_discounts_for_bazaar_mv (the deploy-time command)
# ---------------------------------------------------------------------------

from unittest.mock import patch

from main.management.commands.once_rebalance_discounts_for_bazaar_mv import Command


class RebalanceCommandTests(TestCase):

    def setUp(self):
        self.profile = make_user('trader1')

    @patch(
        'main.management.commands.once_rebalance_discounts_for_bazaar_mv'
        '.Weav3rMarketplaceApiService.get_bazaar_averages_by_item_id'
    )
    def test_command_updates_te_value_and_rebalances(self, mock_get_averages):
        item = make_item(te_value=100_000, item_id=206)
        listing = make_listing(self.profile, item, price=None, discount=10.0)
        old_effective_price = listing.effective_price  # 90_000
        mock_get_averages.return_value = {206: 50_000}

        Command().handle(dry_run=False)

        item.refresh_from_db()
        listing.refresh_from_db()
        self.assertEqual(item.TE_value, 50_000)
        self.assertEqual(item.bazaar_average, 50_000)
        self.assertIsNotNone(item.bazaar_fetched_at)
        self.assertEqual(listing.effective_price, old_effective_price)

    @patch(
        'main.management.commands.once_rebalance_discounts_for_bazaar_mv'
        '.Weav3rMarketplaceApiService.get_bazaar_averages_by_item_id'
    )
    def test_command_skips_item_when_bazaar_average_not_lower(self, mock_get_averages):
        item = make_item(te_value=100_000, item_id=206)
        mock_get_averages.return_value = {206: 150_000}

        Command().handle(dry_run=False)

        item.refresh_from_db()
        self.assertEqual(item.TE_value, 100_000)
        self.assertIsNone(item.bazaar_average)

    @patch(
        'main.management.commands.once_rebalance_discounts_for_bazaar_mv'
        '.Weav3rMarketplaceApiService.get_bazaar_averages_by_item_id'
    )
    def test_command_skips_item_with_no_bazaar_coverage(self, mock_get_averages):
        item = make_item(te_value=100_000, item_id=206)
        mock_get_averages.return_value = {}

        Command().handle(dry_run=False)

        item.refresh_from_db()
        self.assertEqual(item.TE_value, 100_000)

    @patch(
        'main.management.commands.once_rebalance_discounts_for_bazaar_mv'
        '.Weav3rMarketplaceApiService.get_bazaar_averages_by_item_id'
    )
    def test_command_dry_run_leaves_db_unchanged(self, mock_get_averages):
        item = make_item(te_value=100_000, item_id=206)
        listing = make_listing(self.profile, item, price=None, discount=10.0)
        mock_get_averages.return_value = {206: 50_000}

        Command().handle(dry_run=True)

        item.refresh_from_db()
        listing.refresh_from_db()
        self.assertEqual(item.TE_value, 100_000)
        self.assertIsNone(item.bazaar_average)
        self.assertEqual(listing.discount, 10.0)
