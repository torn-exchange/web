from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.utils import timezone

from main.models import Item, ItemTrade, TradeReceipt
from main import market_stats


def make_profile(username, **kwargs):
    user = User.objects.create(username=username)
    profile = user.profile
    profile.name = username
    profile.torn_id = username
    for k, v in kwargs.items():
        setattr(profile, k, v)
    profile.save()
    return profile


def make_item(name='Xanax', item_id=206, te_value=800_000):
    return Item.objects.create(
        name=name, description='', requirement='', item_type='Drug', weapon_type=None,
        buy_price=0, sell_price=0, market_value=te_value, circulation=100000,
        image_url='', TE_value=te_value, item_id=item_id,
    )


def make_receipt(owner, item, *, price, quantity, created_at, count=1):
    receipt = TradeReceipt.objects.create(owner=owner, seller='buyer')
    for _ in range(count):
        trade = ItemTrade.objects.create(
            owner=owner, seller='buyer', item=item, price=price, quantity=quantity,
        )
        receipt.items_trades.add(trade)  # m2m_changed keeps total_amount in sync
    TradeReceipt.objects.filter(pk=receipt.pk).update(created_at=created_at)
    return receipt


@override_settings(CACHES={
    'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'},
    'file': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
             'LOCATION': 'market-stats-tests'},
})
class ActivityStatsTests(TestCase):
    def setUp(self):
        self.now = timezone.now()
        self.profile = make_profile('trader1')
        self.item = make_item()

    def test_empty_data_returns_zeros_not_errors(self):
        data = market_stats.compute_activity()
        by_key = {p['key']: p for p in data['periods']}
        self.assertEqual(by_key['today']['trades'], 0)
        self.assertEqual(by_key['week']['value_display'], '$0')
        self.assertIsNone(by_key['today']['trades_change'])
        self.assertEqual(len(data['daily_trades']), market_stats.DAILY_TRADES_DAYS)
        self.assertIsNone(data['biggest_today'])

    def test_period_windows(self):
        # today (guard the sub-minute window right after UTC midnight)
        midnight = self.now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_ts = max(midnight + timedelta(seconds=1), self.now - timedelta(seconds=30))
        make_receipt(self.profile, self.item, price=1000, quantity=10, created_at=today_ts)
        # 3 days ago -> in last 7 days but not today
        make_receipt(self.profile, self.item, price=1000, quantity=5,
                     created_at=self.now - timedelta(days=3))
        # 20 days ago -> only in last 30 days
        make_receipt(self.profile, self.item, price=1000, quantity=1,
                     created_at=self.now - timedelta(days=20))

        by_key = {p['key']: p for p in market_stats.compute_activity()['periods']}
        self.assertEqual(by_key['today']['trades'], 1)
        self.assertEqual(by_key['week']['trades'], 2)
        self.assertEqual(by_key['month']['trades'], 3)
        self.assertEqual(by_key['today']['items'], 10)
        self.assertEqual(by_key['today']['value'], 10_000)

    def test_value_moved_ignores_null_total_amount(self):
        # Recent receipts often have a NULL denormalised total_amount; value
        # must still be summed from the item trades themselves.
        r = make_receipt(self.profile, self.item, price=1000, quantity=50,
                         created_at=self.now - timedelta(minutes=5))
        TradeReceipt.objects.filter(pk=r.pk).update(total_amount=None)

        by_key = {p['key']: p for p in market_stats.compute_activity()['periods']}
        self.assertEqual(by_key['today']['value'], 50_000)
        self.assertEqual(market_stats.compute_activity()['biggest_today']['value_display'], '$50.00k')

    def test_biggest_today_is_anonymous(self):
        make_receipt(self.profile, self.item, price=1000, quantity=100,
                     created_at=self.now - timedelta(minutes=5), count=3)
        biggest = market_stats.compute_activity()['biggest_today']
        self.assertEqual(biggest['item_count'], 3)
        self.assertEqual(set(biggest.keys()), {'value_display', 'item_count'})

    def test_daily_trades_sparkline(self):
        make_receipt(self.profile, self.item, price=1, quantity=1,
                     created_at=self.now - timedelta(days=1))
        bars = market_stats.compute_activity()['daily_trades']
        self.assertEqual(bars[-2]['count'], 1)
        self.assertEqual(bars[-2]['height_pct'], 100)
        self.assertEqual(bars[-1]['count'], 0)

    def test_format_money(self):
        self.assertEqual(market_stats.format_money(0), '$0')
        self.assertEqual(market_stats.format_money(2_170_000_000), '$2.17b')
        self.assertEqual(market_stats.format_money(754_467), '$754.47k')


@override_settings(CACHES={
    'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'},
    'file': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
             'LOCATION': 'market-stats-online-tests'},
})
class OnlineStatsTests(TestCase):
    def test_stale_when_no_recent_status_check(self):
        p = make_profile('t1', api_key='abc', activity_status='Online',
                         last_active=timezone.now())
        p.__class__.objects.filter(pk=p.pk).update(
            updated_at=timezone.now() - timedelta(hours=2))
        data = market_stats.compute_online()
        self.assertTrue(data['stale'])
        self.assertEqual(data['traders'], [])
        self.assertEqual(data['count'], 0)

    def test_lists_online_active_traders_when_fresh(self):
        make_profile('online_trader', api_key='abc', activity_status='Online',
                     active_trader=True, last_active=timezone.now(), vote_score=5)
        make_profile('idle_trader', api_key='abc', activity_status='Idle',
                     active_trader=True, last_active=timezone.now())
        make_profile('offline_no_key', activity_status='Online', active_trader=True,
                     last_active=timezone.now())

        data = market_stats.compute_online()
        self.assertFalse(data['stale'])
        self.assertEqual([t['name'] for t in data['traders']], ['online_trader'])
        self.assertEqual(data['count'], 1)

    def test_get_helpers_are_cache_first(self):
        make_profile('online_trader', api_key='abc', activity_status='Online',
                     active_trader=True, last_active=timezone.now())
        market_stats.refresh_all()
        with self.assertNumQueries(0):
            market_stats.get_activity()
            market_stats.get_online()
