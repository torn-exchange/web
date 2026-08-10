import json

from django.test import TestCase
from django.urls import reverse

from main.models import Item, Listing
from main.tests.test_effective_price import make_user, make_item, make_listing


class EditPriceListSaveItemsTests(TestCase):
    """The save endpoint should touch only the items it's explicitly told
    about, leaving every other listing (in categories the trader never
    opened) completely untouched."""

    def setUp(self):
        self.user, self.profile = make_user('save_items_trader')
        self.client.force_login(self.user)
        self.item_a = make_item(name='Item A', te_value=100_000, item_id=101)
        self.item_b = make_item(name='Item B', te_value=200_000, item_id=102)
        self.listing_a = make_listing(self.profile, self.item_a, price=None, discount=5.0)
        self.listing_b = make_listing(self.profile, self.item_b, price=150_000, discount=None)

    def post_items(self, items):
        return self.client.post(
            reverse('edit_price_list_save_items'),
            data=json.dumps({'items': items}),
            content_type='application/json',
        )

    def test_updating_one_item_leaves_others_untouched(self):
        response = self.post_items([
            {'item_id': self.item_a.item_id, 'price': None, 'discount': '10.0'},
        ])

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['updated'], [self.item_a.item_id])
        self.assertEqual(data['failed'], [])

        self.listing_a.refresh_from_db()
        self.assertEqual(self.listing_a.discount, 10.0)

        # untouched listing must be byte-for-byte the same
        self.listing_b.refresh_from_db()
        self.assertEqual(self.listing_b.price, 150_000)
        self.assertIsNone(self.listing_b.discount)

    def test_delete_flag_removes_only_that_listing(self):
        response = self.post_items([
            {'item_id': self.item_b.item_id, 'delete': True},
        ])

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['deleted'], [self.item_b.item_id])

        self.assertFalse(Listing.objects.filter(owner=self.profile, item=self.item_b).exists())
        self.assertTrue(Listing.objects.filter(owner=self.profile, item=self.item_a).exists())

    def test_creates_listing_for_item_with_no_existing_listing(self):
        item_c = make_item(name='Item C', te_value=50_000, item_id=103)

        response = self.post_items([
            {'item_id': item_c.item_id, 'price': '25000', 'discount': None},
        ])

        self.assertEqual(response.status_code, 200)
        listing = Listing.objects.get(owner=self.profile, item=item_c)
        self.assertEqual(listing.price, 25000)

    def test_discount_over_100_is_rejected_without_touching_listing(self):
        response = self.post_items([
            {'item_id': self.item_a.item_id, 'price': None, 'discount': '150.0'},
        ])

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['failed'], [self.item_a.item_id])

        self.listing_a.refresh_from_db()
        self.assertEqual(self.listing_a.discount, 5.0)

    def test_unknown_item_id_is_reported_as_failed(self):
        response = self.post_items([{'item_id': 999999, 'price': '100'}])

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['failed'], [999999])

    def test_requires_login(self):
        self.client.logout()
        response = self.post_items([{'item_id': self.item_a.item_id, 'price': '100'}])
        self.assertNotEqual(response.status_code, 200)


class EditPriceListCategoryFragmentTests(TestCase):
    def setUp(self):
        self.user, self.profile = make_user('fragment_trader')
        self.client.force_login(self.user)
        self.item = make_item(name='Fragment Item', te_value=100_000, item_id=201)
        self.item.circulation = 10_000
        self.item.save()

    def test_valid_category_returns_its_items(self):
        response = self.client.get(reverse('edit_price_list_category_fragment'), {'type': 'Melee'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Fragment Item')

    def test_invalid_category_is_rejected(self):
        response = self.client.get(reverse('edit_price_list_category_fragment'), {'type': 'Not A Category'})
        self.assertEqual(response.status_code, 404)
