from unittest.mock import patch

from django.test import TestCase
from django.contrib.auth.models import User
from users.models import Profile, Settings
from main.models import Item, Listing
from main.management.commands.update_items_fast import (
    create_or_update_sets,
    recalculate_listings_for_item,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_user(username):
    """Create a User + Profile (signal auto-creates Profile; Settings auto-created by Profile.save)."""
    user = User.objects.create(username=username)
    # signals.py auto-creates a bare Profile on User creation; populate required fields
    profile = user.profile
    profile.name = username
    profile.torn_id = username
    profile.save()
    return user, profile


def make_item(name='Test Item', te_value=100_000, item_id=1):
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


def make_listing(profile, item, price=None, discount=None, lower_bound=None, upper_bound=None):
    return Listing.objects.create(
        owner=profile,
        item=item,
        price=price,
        discount=discount,
        lower_bound=lower_bound,
        upper_bound=upper_bound,
    )


# ---------------------------------------------------------------------------
# effective_price unit tests — mirrors calculate_effective_price() logic
# ---------------------------------------------------------------------------

class EffectivePriceCalculationTests(TestCase):
    """
    Tests for Listing.effective_price (currently a @property).
    These tests document the exact expected behaviour so we can verify
    nothing breaks when the field is converted to a stored DB column.
    """

    def setUp(self):
        self.user, self.profile = make_user('trader1')
        self.item = make_item(name='Sword', te_value=100_000, item_id=1)

    # --- both null → None ---------------------------------------------------

    def test_both_null_returns_none(self):
        listing = make_listing(self.profile, self.item, price=None, discount=None)
        self.assertIsNone(listing.effective_price)

    # --- fixed price only (no discount) -------------------------------------

    def test_fixed_price_only_returns_rounded_price(self):
        listing = make_listing(self.profile, self.item, price=80_000, discount=None)
        self.assertEqual(listing.effective_price, 80_000)

    def test_fixed_price_rounds_correctly(self):
        listing = make_listing(self.profile, self.item, price=80_001, discount=None)
        self.assertEqual(listing.effective_price, 80_001)

    # --- discount only (no fixed price) -------------------------------------

    def test_discount_only(self):
        # 10% discount on 100_000 → 90_000
        listing = make_listing(self.profile, self.item, price=None, discount=10.0)
        self.assertEqual(listing.effective_price, 90_000)

    def test_discount_zero(self):
        listing = make_listing(self.profile, self.item, price=None, discount=0.0)
        self.assertEqual(listing.effective_price, 100_000)

    # --- both discount and price set → take the minimum ---------------------

    def test_min_takes_fixed_price_when_lower(self):
        # discounted price = 90_000, fixed price = 70_000 → min = 70_000
        listing = make_listing(self.profile, self.item, price=70_000, discount=10.0)
        self.assertEqual(listing.effective_price, 70_000)

    def test_min_takes_discounted_price_when_lower(self):
        # discounted price = 90_000, fixed price = 95_000 → min = 90_000
        listing = make_listing(self.profile, self.item, price=95_000, discount=10.0)
        self.assertEqual(listing.effective_price, 90_000)

    def test_fixed_price_equals_discounted_price(self):
        # 10% off 100_000 = 90_000, fixed = 90_000 → 90_000
        listing = make_listing(self.profile, self.item, price=90_000, discount=10.0)
        self.assertEqual(listing.effective_price, 90_000)

    # --- TE_value = 0 -------------------------------------------------------

    def test_te_value_zero_with_discount_returns_zero(self):
        item = make_item(name='ZeroItem', te_value=0, item_id=2)
        listing = make_listing(self.profile, item, price=None, discount=10.0)
        self.assertEqual(listing.effective_price, 0)

    def test_te_value_zero_with_discount_and_fixed_price_returns_zero(self):
        # discounted = 0, fixed = 50_000 → min = 0
        item = make_item(name='ZeroItem2', te_value=0, item_id=3)
        listing = make_listing(self.profile, item, price=50_000, discount=10.0)
        self.assertEqual(listing.effective_price, 0)

    # --- 100% discount (free) -----------------------------------------------

    def test_hundred_percent_discount_returns_zero(self):
        listing = make_listing(self.profile, self.item, price=None, discount=100.0)
        self.assertEqual(listing.effective_price, 0)

    # --- staleness tests: document expected behaviour after migration --------

    def test_effective_price_unaffected_by_settings_changes(self):
        """
        Global fee has been removed: effective_price is now driven purely by
        the listing's own price/discount and the item's TE_value, so changing
        unrelated Settings fields must not alter it.
        """
        listing = make_listing(self.profile, self.item, price=None, discount=10.0)
        self.assertEqual(listing.effective_price, 90_000)

        self.profile.settings.trade_enable_sets = False
        self.profile.settings.save()
        listing.refresh_from_db()

        self.assertEqual(listing.effective_price, 90_000)

    def test_effective_price_reflects_updated_te_value(self):
        """
        After migration, when the item-update command changes Item.TE_value,
        a follow-up script must update Listing.effective_price for all
        listings of that item.
        """
        listing = make_listing(self.profile, self.item, price=None, discount=10.0)
        self.assertEqual(listing.effective_price, 90_000)  # 10% off 100_000

        self.item.TE_value = 200_000
        self.item.save()
        recalculate_listings_for_item(self.item)
        listing.refresh_from_db()

        # 10% off 200_000 = 180_000
        self.assertEqual(listing.effective_price, 180_000)


class EffectivePriceBoundsTests(TestCase):
    """
    Tests for the lower_bound/upper_bound fixed-dollar clamps layered on top
    of calculate_effective_price()'s existing price/discount logic.
    """

    def setUp(self):
        self.user, self.profile = make_user('trader1')
        self.item = make_item(name='Xanax', te_value=1_000_000, item_id=1)

    def test_lower_bound_only_raw_above_bound_unaffected(self):
        # 10% off 1_000_000 = 900_000, well above the 500_000 floor
        listing = make_listing(self.profile, self.item, discount=10.0, lower_bound=500_000)
        self.assertEqual(listing.effective_price, 900_000)

    def test_lower_bound_only_raw_below_bound_clamped_up(self):
        # 90% off 1_000_000 = 100_000, below the 500_000 floor
        listing = make_listing(self.profile, self.item, discount=90.0, lower_bound=500_000)
        self.assertEqual(listing.effective_price, 500_000)

    def test_upper_bound_only_raw_below_bound_unaffected(self):
        # 10% off 1_000_000 = 900_000, below the 950_000 ceiling
        listing = make_listing(self.profile, self.item, discount=10.0, upper_bound=950_000)
        self.assertEqual(listing.effective_price, 900_000)

    def test_upper_bound_only_raw_above_bound_clamped_down(self):
        # discount is 0 -> raw = 1_000_000, above the 950_000 ceiling
        listing = make_listing(self.profile, self.item, discount=0.0, upper_bound=950_000)
        self.assertEqual(listing.effective_price, 950_000)

    def test_both_bounds_raw_inside_range_unaffected(self):
        listing = make_listing(
            self.profile, self.item, discount=10.0, lower_bound=800_000, upper_bound=950_000
        )
        self.assertEqual(listing.effective_price, 900_000)

    def test_both_bounds_raw_below_lower_clamped_to_lower(self):
        listing = make_listing(
            self.profile, self.item, discount=90.0, lower_bound=800_000, upper_bound=950_000
        )
        self.assertEqual(listing.effective_price, 800_000)

    def test_both_bounds_raw_above_upper_clamped_to_upper(self):
        listing = make_listing(
            self.profile, self.item, discount=0.0, lower_bound=800_000, upper_bound=950_000
        )
        self.assertEqual(listing.effective_price, 950_000)

    def test_bounds_equal_pinned_to_exact_value(self):
        listing = make_listing(
            self.profile, self.item, discount=10.0, lower_bound=820_000, upper_bound=820_000
        )
        self.assertEqual(listing.effective_price, 820_000)

    def test_lower_greater_than_upper_falls_back_to_upper(self):
        """
        Not a supported configuration (blocked by validation at the write
        layer and a DB CheckConstraint), but calculate_effective_price()
        must still behave deterministically if a bad pair ever reaches it --
        clamping lower-then-upper collapses the result to upper_bound.
        Uses an unsaved instance to bypass the DB constraint.
        """
        listing = Listing(
            owner=self.profile, item=self.item, discount=10.0,
            lower_bound=900_000, upper_bound=800_000,
        )
        self.assertEqual(listing.calculate_effective_price(), 800_000)

    def test_price_only_listing_is_not_clamped_by_bounds(self):
        """
        A fixed price is authoritative: bounds never clamp it, even when
        they conflict (that's flagged separately by bounds_conflict(), see
        BoundsConflictTests below -- calculate_effective_price() itself
        always trusts the fixed price).
        """
        listing = make_listing(
            self.profile, self.item, price=1_500_000, lower_bound=None, upper_bound=1_000_000
        )
        self.assertEqual(listing.effective_price, 1_500_000)

    def test_price_and_discount_combo_is_not_clamped_by_bounds(self):
        """When both price and discount are set, min(price, discount_price)
        is still authoritative -- bounds validate it but never clamp it."""
        # 10% off 1_000_000 = 900_000; min(900_000, 70_000) = 70_000, which
        # falls below the 500_000 lower bound -- would be clamped up under
        # the old behavior, but must stay 70_000 now.
        listing = make_listing(
            self.profile, self.item, price=70_000, discount=10.0,
            lower_bound=500_000,
        )
        self.assertEqual(listing.effective_price, 70_000)

    def test_te_value_zero_with_lower_bound_floor_wins(self):
        item = make_item(name='ZeroItemBounded', te_value=0, item_id=4)
        listing = make_listing(self.profile, item, discount=10.0, lower_bound=500_000)
        self.assertEqual(listing.effective_price, 500_000)

    def test_bound_tracks_te_value_propagation(self):
        """As TE_value drifts via recalculate_listings_for_item, the floor
        should engage/disengage correctly."""
        listing = make_listing(self.profile, self.item, discount=50.0, lower_bound=600_000)
        # 50% off 1_000_000 = 500_000, below the 600_000 floor
        self.assertEqual(listing.effective_price, 600_000)

        self.item.TE_value = 2_000_000
        self.item.save()
        recalculate_listings_for_item(self.item)
        listing.refresh_from_db()
        # 50% off 2_000_000 = 1_000_000, now above the floor
        self.assertEqual(listing.effective_price, 1_000_000)

        self.item.TE_value = 1_000_000
        self.item.save()
        recalculate_listings_for_item(self.item)
        listing.refresh_from_db()
        # back to 500_000 raw, floor re-engages
        self.assertEqual(listing.effective_price, 600_000)


class BoundsConflictTests(TestCase):
    """Tests for Listing.bounds_conflict(), the validation used at write
    time to reject bounds that are inconsistent with price/discount instead
    of silently overriding a fixed price or leaving orphaned bounds."""

    def setUp(self):
        self.user, self.profile = make_user('trader1')
        self.item = make_item(name='Xanax', te_value=1_000_000, item_id=1)

    def test_no_bounds_set_is_never_a_conflict(self):
        listing = make_listing(self.profile, self.item, price=30_000)
        self.assertIsNone(listing.bounds_conflict())

    def test_negative_lower_bound_is_a_conflict(self):
        listing = Listing(owner=self.profile, item=self.item, price=30_000, lower_bound=-1)
        self.assertIsNotNone(listing.bounds_conflict())

    def test_negative_upper_bound_is_a_conflict(self):
        listing = Listing(owner=self.profile, item=self.item, price=30_000, upper_bound=-1)
        self.assertIsNotNone(listing.bounds_conflict())

    def test_lower_greater_than_upper_is_a_conflict(self):
        listing = Listing(
            owner=self.profile, item=self.item, price=30_000,
            lower_bound=900_000, upper_bound=800_000,
        )
        self.assertIsNotNone(listing.bounds_conflict())

    def test_bounds_without_price_or_discount_is_a_conflict(self):
        """Orphaned bounds -- nothing for them to bound -- must be cleared
        before the trader can remove price/discount entirely."""
        listing = Listing(owner=self.profile, item=self.item, lower_bound=500_000)
        self.assertIsNotNone(listing.bounds_conflict())

    def test_fixed_price_below_lower_bound_is_a_conflict(self):
        listing = Listing(owner=self.profile, item=self.item, price=30_000, lower_bound=50_000)
        self.assertIsNotNone(listing.bounds_conflict())

    def test_fixed_price_above_upper_bound_is_a_conflict(self):
        listing = Listing(owner=self.profile, item=self.item, price=100_000, upper_bound=50_000)
        self.assertIsNotNone(listing.bounds_conflict())

    def test_fixed_price_within_bounds_is_not_a_conflict(self):
        listing = Listing(
            owner=self.profile, item=self.item, price=60_000,
            lower_bound=50_000, upper_bound=70_000,
        )
        self.assertIsNone(listing.bounds_conflict())

    def test_discount_only_never_conflicts_since_bounds_clamp_it(self):
        """A purely discount-driven price is always clamped to fit, so it
        never conflicts regardless of the raw value."""
        listing = Listing(
            owner=self.profile, item=self.item, discount=90.0,
            lower_bound=500_000, upper_bound=950_000,
        )
        self.assertIsNone(listing.bounds_conflict())

    def test_price_and_discount_combo_checked_against_final_min(self):
        # 10% off 1_000_000 = 900_000; min(900_000, 70_000) = 70_000, below
        # the 500_000 floor -> conflict, since price is authoritative here.
        listing = Listing(
            owner=self.profile, item=self.item, price=70_000, discount=10.0,
            lower_bound=500_000,
        )
        self.assertIsNotNone(listing.bounds_conflict())


class CreateOrUpdateSetsRecalculatesListingsTests(TestCase):
    """
    Plushie Set (item_id 9998) and Flower Set (item_id 9999) get their
    TE_value from the points market rather than from _process_item_row's
    normal update path, so create_or_update_sets() must itself trigger
    recalculate_listings_for_item -- otherwise traders' stored
    effective_price for these two items goes stale until they manually
    re-save their listing (see trader reports of Plushie/Flower Set prices
    not updating).
    """

    def setUp(self):
        self.user, self.profile = make_user('trader1')

    @patch('main.management.commands.update_items_fast.get_points_market_value')
    def test_plushie_and_flower_set_effective_price_updates_with_points_price(self, mock_points):
        mock_points.return_value = 30_000
        create_or_update_sets()

        plushie = Item.objects.get(item_id=9998)
        flower = Item.objects.get(item_id=9999)
        plushie_listing = make_listing(self.profile, plushie, price=None, discount=0.25)
        flower_listing = make_listing(self.profile, flower, price=None, discount=0.25)

        # 0.25% off 300_000 = 299_250
        self.assertEqual(plushie_listing.effective_price, 299_250)
        self.assertEqual(flower_listing.effective_price, 299_250)

        mock_points.return_value = 31_000
        create_or_update_sets()
        plushie_listing.refresh_from_db()
        flower_listing.refresh_from_db()

        # 0.25% off 310_000 = 309_225
        self.assertEqual(plushie_listing.effective_price, 309_225)
        self.assertEqual(flower_listing.effective_price, 309_225)
