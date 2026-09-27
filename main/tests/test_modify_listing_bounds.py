import json

from django.test import TestCase
from django.urls import reverse

from main.models import Listing
from main.tests.test_effective_price import make_user, make_item, make_listing


class ModifyListingBoundsTests(TestCase):
    """Validation matrix for lower_bound/upper_bound via the public
    /api/modify_listing endpoint, mirroring the equivalent tests for the
    Edit Price page's own save endpoint."""

    def setUp(self):
        self.user, self.profile = make_user('api_trader')
        self.profile.api_key = 'test-api-key'
        self.profile.save()
        self.item = make_item(name='Xanax', te_value=1_000_000, item_id=301)
        self.listing = make_listing(self.profile, self.item, price=None, discount=10.0)

    def post(self, listings):
        return self.client.post(
            reverse('modify_listing'),
            data=json.dumps({'key': self.profile.api_key, 'listings': listings}),
            content_type='application/json',
        )

    def test_valid_bounds_are_saved_and_clamp_effective_price(self):
        response = self.post([
            {'item_id': self.item.item_id, 'action': 'update', 'discount': 90,
             'lower_bound': 500_000, 'upper_bound': 950_000},
        ])

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['data']['updated_listings'], [self.item.item_id])

        self.listing.refresh_from_db()
        self.assertEqual(self.listing.lower_bound, 500_000)
        self.assertEqual(self.listing.upper_bound, 950_000)
        # 90% off 1_000_000 = 100_000, clamped up to the 500_000 floor
        self.assertEqual(self.listing.effective_price, 500_000)

    def test_lower_bound_greater_than_upper_bound_is_rejected(self):
        response = self.post([
            {'item_id': self.item.item_id, 'action': 'update', 'discount': 10,
             'lower_bound': 900_000, 'upper_bound': 800_000},
        ])

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['data']['failed_listings'], [self.item.item_id])

        self.listing.refresh_from_db()
        self.assertIsNone(self.listing.lower_bound)
        self.assertIsNone(self.listing.upper_bound)

    def test_negative_bound_is_rejected(self):
        response = self.post([
            {'item_id': self.item.item_id, 'action': 'update', 'discount': 10,
             'lower_bound': -5000},
        ])

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['data']['failed_listings'], [self.item.item_id])

        self.listing.refresh_from_db()
        self.assertIsNone(self.listing.lower_bound)

    def test_bounds_omitted_leaves_existing_bounds_untouched(self):
        self.listing.lower_bound = 400_000
        self.listing.upper_bound = 900_000
        self.listing.save()

        response = self.post([
            {'item_id': self.item.item_id, 'action': 'update', 'discount': 20},
        ])

        self.assertEqual(response.status_code, 200)
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.lower_bound, 400_000)
        self.assertEqual(self.listing.upper_bound, 900_000)

    def test_fixed_price_conflicting_with_bounds_is_rejected(self):
        response = self.post([
            {'item_id': self.item.item_id, 'action': 'update', 'fixed_price': 30_000,
             'lower_bound': 50_000},
        ])

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['data']['failed_listings'], [self.item.item_id])

        self.listing.refresh_from_db()
        self.assertEqual(self.listing.discount, 10.0)
        self.assertIsNone(self.listing.lower_bound)

    def test_new_fixed_price_conflicting_with_existing_bounds_is_rejected(self):
        """Existing bounds that were fine for the old price/discount must be
        re-validated against a newly submitted fixed price."""
        self.listing.lower_bound = 500_000
        self.listing.save()

        response = self.post([
            {'item_id': self.item.item_id, 'action': 'update', 'fixed_price': 30_000},
        ])

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['data']['failed_listings'], [self.item.item_id])

        self.listing.refresh_from_db()
        self.assertEqual(self.listing.discount, 10.0)
        self.assertIsNone(self.listing.price)
