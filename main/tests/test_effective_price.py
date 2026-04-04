from django.test import TestCase
from django.contrib.auth.models import User
from users.models import Profile, Settings
from main.models import Item, Listing
from main.management.commands.update_items2 import recalculate_listings_for_item


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


def make_listing(profile, item, price=None, discount=None):
    return Listing.objects.create(
        owner=profile,
        item=item,
        price=price,
        discount=discount,
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
        # ensure global fee starts at 0
        self.profile.settings.trade_global_fee = 0
        self.profile.settings.save()

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

    def test_discount_only_no_global_fee(self):
        # 10% discount on 100_000 → 90_000
        listing = make_listing(self.profile, self.item, price=None, discount=10.0)
        self.assertEqual(listing.effective_price, 90_000)

    def test_discount_only_with_global_fee(self):
        # 10% user discount + 5% global fee = 15% total → 85_000
        self.profile.settings.trade_global_fee = 5
        self.profile.settings.save()
        listing = make_listing(self.profile, self.item, price=None, discount=10.0)
        self.assertEqual(listing.effective_price, 85_000)

    def test_discount_zero_with_global_fee(self):
        # discount=0, global_fee=10 → 90_000
        self.profile.settings.trade_global_fee = 10
        self.profile.settings.save()
        listing = make_listing(self.profile, self.item, price=None, discount=0.0)
        self.assertEqual(listing.effective_price, 90_000)

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

    # --- global fee should NOT apply to custom items (item_id > 9000) -------

    def test_global_fee_not_applied_to_custom_item(self):
        custom_item = make_item(name='Plushie Set', te_value=100_000, item_id=9998)
        self.profile.settings.trade_global_fee = 10
        self.profile.settings.save()
        # Only user discount of 10% → 90_000  (global fee ignored)
        listing = make_listing(self.profile, custom_item, price=None, discount=10.0)
        self.assertEqual(listing.effective_price, 90_000)

    def test_global_fee_not_applied_to_another_custom_item(self):
        custom_item = make_item(name='Flower Set', te_value=200_000, item_id=9999)
        self.profile.settings.trade_global_fee = 5
        self.profile.settings.save()
        # Only user discount 20% → 160_000  (global fee ignored)
        listing = make_listing(self.profile, custom_item, price=None, discount=20.0)
        self.assertEqual(listing.effective_price, 160_000)

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

    def test_effective_price_reflects_updated_global_fee(self):
        """
        Currently (property-based): effective_price is always recalculated live,
        so changing trade_global_fee immediately affects the result.
        After migration to a stored field, updating Settings must trigger
        a re-save of all related Listings (via signal or explicit update).
        """
        listing = make_listing(self.profile, self.item, price=None, discount=10.0)
        self.assertEqual(listing.effective_price, 90_000)  # fee=0: 10% off

        self.profile.settings.trade_global_fee = 10
        self.profile.settings.save()
        listing.refresh_from_db()

        # 10% user + 10% global = 20% total → 80_000
        self.assertEqual(listing.effective_price, 80_000)

    def test_effective_price_reflects_updated_te_value(self):
        """
        After migration, when update_items2 changes Item.TE_value,
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
