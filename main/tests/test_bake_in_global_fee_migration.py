from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

# 'main' is pinned at its current leaf in both states -- it isn't moving, but
# project_state() only includes apps reachable from the listed nodes, so it
# has to be named explicitly for apps.get_model('main', ...) to work below.
MIGRATE_FROM = [
    ('users', '0001_initial_squashed_0034_profile_on_vacation'),
    ('main', '0059_receipt_management_changelog_entry'),
]
MIGRATE_TO = [
    ('users', '0035_remove_settings_trade_global_fee'),
    ('main', '0059_receipt_management_changelog_entry'),
]


class BakeInGlobalFeeMigrationTests(TransactionTestCase):
    """
    Exercises the data migration in users/migrations/0035_remove_settings_trade_global_fee.py
    directly, using historical model state -- unlike a plain management command, this runs
    against the DB schema as it exists mid-migration (trade_global_fee column still present),
    which is the only place this logic can safely run once the field is gone from models.py.
    """

    def setUp(self):
        self.executor = MigrationExecutor(connection)
        self.executor.migrate(MIGRATE_FROM)
        self.executor.loader.build_graph()

    def tearDown(self):
        # Leave the DB on the latest migration state for subsequent tests.
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(executor.loader.graph.leaf_nodes())

    def _make_listing(self, apps, discount, price=None, item_id=1, te_value=100_000, trade_global_fee=0):
        # Historical models built from migration state carry only fields, not the
        # custom Listing.save()/calculate_effective_price() from main/models.py --
        # effective_price has to be computed here exactly as that method would.
        User = apps.get_model('auth', 'User')
        Profile = apps.get_model('users', 'Profile')
        Settings = apps.get_model('users', 'Settings')
        Item = apps.get_model('main', 'Item')
        Listing = apps.get_model('main', 'Listing')

        user = User.objects.create(username=f'trader{item_id}')
        profile = Profile.objects.create(user=user, name='trader', torn_id=str(user.pk))
        Settings.objects.create(owner=profile, trade_global_fee=trade_global_fee)
        item = Item.objects.create(
            name='Item', description='', requirement='', item_type='Melee',
            buy_price=0, sell_price=0, market_value=te_value, circulation=10000,
            image_url='', TE_value=te_value, item_id=item_id,
        )

        global_fee = 0 if item_id > 9000 else trade_global_fee
        discount_fraction = (100.0 - ((discount or 0) + global_fee)) / 100.0
        discount_price = discount_fraction * round(te_value)
        effective_price = round(discount_price) if price is None else round(min(discount_price, price))

        return Listing.objects.create(
            owner=profile, item=item, price=price, discount=discount, effective_price=effective_price,
        )

    def test_fee_folded_into_discount_preserves_effective_price(self):
        old_apps = self.executor.loader.project_state(MIGRATE_FROM).apps
        listing = self._make_listing(old_apps, discount=10.0, trade_global_fee=5)
        old_effective_price = listing.effective_price
        self.assertEqual(old_effective_price, 85_000)  # 15% off 100_000

        self.executor.migrate(MIGRATE_TO)
        self.executor.loader.build_graph()
        new_apps = self.executor.loader.project_state(MIGRATE_TO).apps
        Listing = new_apps.get_model('main', 'Listing')
        migrated = Listing.objects.get(pk=listing.pk)

        self.assertEqual(migrated.discount, 15.0)
        self.assertEqual(migrated.effective_price, old_effective_price)

    def test_out_of_range_bake_in_is_left_untouched(self):
        old_apps = self.executor.loader.project_state(MIGRATE_FROM).apps
        listing = self._make_listing(old_apps, discount=98.0, trade_global_fee=5, item_id=2)

        self.executor.migrate(MIGRATE_TO)
        self.executor.loader.build_graph()
        new_apps = self.executor.loader.project_state(MIGRATE_TO).apps
        Listing = new_apps.get_model('main', 'Listing')
        migrated = Listing.objects.get(pk=listing.pk)

        self.assertEqual(migrated.discount, 98.0)

    def test_zero_fee_listing_untouched(self):
        old_apps = self.executor.loader.project_state(MIGRATE_FROM).apps
        listing = self._make_listing(old_apps, discount=10.0, trade_global_fee=0, item_id=3)

        self.executor.migrate(MIGRATE_TO)
        self.executor.loader.build_graph()
        new_apps = self.executor.loader.project_state(MIGRATE_TO).apps
        Listing = new_apps.get_model('main', 'Listing')
        migrated = Listing.objects.get(pk=listing.pk)

        self.assertEqual(migrated.discount, 10.0)
