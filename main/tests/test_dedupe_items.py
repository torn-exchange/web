from datetime import timedelta

from django.contrib.auth.models import User
from django.db import connection
from django.test import TestCase
from django.utils import timezone

from main.management.commands.once_dedupe_items import Command
from main.models import Item, ItemTrade, ItemVariation, Listing
from users.models import Profile


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


def make_item(name, item_id, last_updated=None):
    item = Item.objects.create(
        name=name,
        description='',
        requirement='',
        item_type='Melee',
        weapon_type=None,
        buy_price=0,
        sell_price=0,
        market_value=1000,
        circulation=10000,
        image_url='',
        TE_value=1000,
        item_id=item_id,
    )
    if last_updated is not None:
        Item.objects.filter(pk=item.pk).update(last_updated=last_updated)
        item.refresh_from_db()
    return item


def make_listing(owner, item, price=100, last_updated=None):
    listing = Listing.objects.create(owner=owner, item=item, price=price)
    if last_updated is not None:
        Listing.objects.filter(pk=listing.pk).update(last_updated=last_updated)
        listing.refresh_from_db()
    return listing


class DuplicateItemIdTestCase(TestCase):
    """
    The unique_non_null_item_id partial index (migration 0054) makes it
    impossible to create two Item rows with the same item_id through normal
    ORM/DB operations -- which is exactly the pre-existing-duplicate state
    once_dedupe_items is meant to clean up. Drop the index for the duration
    of each test's transaction (TestCase rolls the whole transaction back
    afterwards, so the index is intact again for the next test).
    """

    def setUp(self):
        with connection.cursor() as cursor:
            cursor.execute('DROP INDEX unique_non_null_item_id')


# ---------------------------------------------------------------------------
# once_dedupe_items — FK reassignment and collision resolution
# ---------------------------------------------------------------------------

class DedupeItemsCommandTests(DuplicateItemIdTestCase):

    def setUp(self):
        super().setUp()
        self.now = timezone.now()

    def test_keeps_newest_as_canonical(self):
        older = make_item('Old Name', item_id=5, last_updated=self.now - timedelta(days=1))
        newer = make_item('New Name', item_id=5, last_updated=self.now)

        Command().handle(dry_run=False)

        self.assertFalse(Item.objects.filter(pk=older.pk).exists())
        self.assertTrue(Item.objects.filter(pk=newer.pk).exists())

    def test_reassigns_item_trade_fk(self):
        owner = make_user('trader1')
        older = make_item('Old Name', item_id=5, last_updated=self.now - timedelta(days=1))
        newer = make_item('New Name', item_id=5, last_updated=self.now)
        trade = ItemTrade.objects.create(owner=owner, item=older, price=10, quantity=1)

        Command().handle(dry_run=False)

        trade.refresh_from_db()
        self.assertEqual(trade.item_id, newer.id)

    def test_reassigns_item_variation_fk(self):
        older = make_item('Old Name', item_id=5, last_updated=self.now - timedelta(days=1))
        newer = make_item('New Name', item_id=5, last_updated=self.now)
        variation = ItemVariation.objects.create(item=older, quality=1.0)

        Command().handle(dry_run=False)

        variation.refresh_from_db()
        self.assertEqual(variation.item_id, newer.id)

    def test_listing_reassigned_when_no_collision(self):
        owner = make_user('trader1')
        older = make_item('Old Name', item_id=5, last_updated=self.now - timedelta(days=1))
        newer = make_item('New Name', item_id=5, last_updated=self.now)
        listing = make_listing(owner, older)

        Command().handle(dry_run=False)

        listing.refresh_from_db()
        self.assertEqual(listing.item_id, newer.id)

    def test_listing_collision_keeps_newer_of_the_two_dup_side_newer(self):
        owner = make_user('trader1')
        older_item = make_item('Old Name', item_id=5, last_updated=self.now - timedelta(days=1))
        canonical_item = make_item('New Name', item_id=5, last_updated=self.now)

        # owner already has a listing on the canonical item (stale, older)...
        canonical_listing = make_listing(owner, canonical_item, price=50, last_updated=self.now - timedelta(hours=2))
        # ...but their listing on the duplicate item is more recently updated
        dup_listing = make_listing(owner, older_item, price=99, last_updated=self.now - timedelta(hours=1))

        Command().handle(dry_run=False)

        self.assertFalse(Listing.objects.filter(pk=canonical_listing.pk).exists())
        dup_listing.refresh_from_db()
        self.assertEqual(dup_listing.item_id, canonical_item.id)
        self.assertEqual(dup_listing.price, 99)

    def test_listing_collision_keeps_newer_of_the_two_canonical_side_newer(self):
        owner = make_user('trader1')
        older_item = make_item('Old Name', item_id=5, last_updated=self.now - timedelta(days=1))
        canonical_item = make_item('New Name', item_id=5, last_updated=self.now)

        canonical_listing = make_listing(owner, canonical_item, price=50, last_updated=self.now - timedelta(hours=1))
        dup_listing = make_listing(owner, older_item, price=99, last_updated=self.now - timedelta(hours=2))

        Command().handle(dry_run=False)

        self.assertFalse(Listing.objects.filter(pk=dup_listing.pk).exists())
        canonical_listing.refresh_from_db()
        self.assertEqual(canonical_listing.price, 50)

    def test_no_collision_left_after_run(self):
        owner = make_user('trader1')
        older_item = make_item('Old Name', item_id=5, last_updated=self.now - timedelta(days=1))
        canonical_item = make_item('New Name', item_id=5, last_updated=self.now)
        make_listing(owner, canonical_item, last_updated=self.now - timedelta(hours=2))
        make_listing(owner, older_item, last_updated=self.now - timedelta(hours=1))

        Command().handle(dry_run=False)

        remaining = Listing.objects.filter(owner=owner, item__item_id=5)
        self.assertEqual(remaining.count(), 1)

    def test_dry_run_makes_no_changes(self):
        owner = make_user('trader1')
        older = make_item('Old Name', item_id=5, last_updated=self.now - timedelta(days=1))
        newer = make_item('New Name', item_id=5, last_updated=self.now)
        listing = make_listing(owner, older)

        Command().handle(dry_run=True)

        self.assertTrue(Item.objects.filter(pk=older.pk).exists())
        self.assertTrue(Item.objects.filter(pk=newer.pk).exists())
        listing.refresh_from_db()
        self.assertEqual(listing.item_id, older.id)

    def test_non_duplicate_items_untouched(self):
        solo = make_item('Solo Item', item_id=42)
        null_id_1 = Item.objects.create(
            name='No Id 1', description='', requirement='', item_type='Melee',
            buy_price=0, sell_price=0, market_value=0, circulation=0, image_url='',
        )
        null_id_2 = Item.objects.create(
            name='No Id 2', description='', requirement='', item_type='Melee',
            buy_price=0, sell_price=0, market_value=0, circulation=0, image_url='',
        )

        Command().handle(dry_run=False)

        self.assertTrue(Item.objects.filter(pk=solo.pk).exists())
        self.assertTrue(Item.objects.filter(pk=null_id_1.pk).exists())
        self.assertTrue(Item.objects.filter(pk=null_id_2.pk).exists())


# ---------------------------------------------------------------------------
# unique_non_null_item_id constraint itself
# ---------------------------------------------------------------------------

class UniqueItemIdConstraintTests(TestCase):

    def test_rejects_duplicate_non_null_item_id(self):
        Item.objects.create(
            name='First', description='', requirement='', item_type='Melee',
            buy_price=0, sell_price=0, market_value=0, circulation=0, image_url='', item_id=7,
        )
        with self.assertRaises(Exception):
            Item.objects.create(
                name='Second', description='', requirement='', item_type='Melee',
                buy_price=0, sell_price=0, market_value=0, circulation=0, image_url='', item_id=7,
            )

    def test_allows_multiple_null_item_ids(self):
        Item.objects.create(
            name='A', description='', requirement='', item_type='Melee',
            buy_price=0, sell_price=0, market_value=0, circulation=0, image_url='',
        )
        Item.objects.create(
            name='B', description='', requirement='', item_type='Melee',
            buy_price=0, sell_price=0, market_value=0, circulation=0, image_url='',
        )
        self.assertEqual(Item.objects.filter(item_id__isnull=True).count(), 2)


# ---------------------------------------------------------------------------
# update_items2 upsert now keys on item_id, not name
# ---------------------------------------------------------------------------

class UpsertKeyedOnItemIdTests(TestCase):

    def test_rename_updates_existing_row_instead_of_creating_duplicate(self):
        item = make_item('Old Name', item_id=5)

        Item.objects.update_or_create(
            item_id=5,
            defaults=dict(
                name='New Name',
                description='', requirement='', item_type='Melee', weapon_type=None,
                buy_price=0, sell_price=0, market_value=1000, circulation=10000,
                image_url='', TE_value=1000,
            ),
        )

        self.assertEqual(Item.objects.filter(item_id=5).count(), 1)
        item.refresh_from_db()
        self.assertEqual(item.name, 'New Name')
