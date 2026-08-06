from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from main.management.commands.once_dedupe_receipts import Command
from main.models import Item, ItemTrade, TradeReceipt
from main.profile_stats import return_profile_stats


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


def make_item(name='Test Item', item_id=1, te_value=1000):
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


def make_item_trade(owner, item, seller='Bob', price=10, quantity=1):
    return ItemTrade.objects.create(owner=owner, seller=seller, item=item, price=price, quantity=quantity)


def make_trade_receipt(owner, seller, item_trades, created_at):
    receipt = TradeReceipt.objects.create(owner=owner, seller=seller)
    receipt.items_trades.set(item_trades)
    # bypass auto_now_add to control ordering/window in tests
    TradeReceipt.objects.filter(pk=receipt.pk).update(created_at=created_at)
    receipt.refresh_from_db()
    return receipt


# ---------------------------------------------------------------------------
# once_dedupe_receipts
# ---------------------------------------------------------------------------

class DedupeReceiptsCommandTests(TestCase):

    def setUp(self):
        self.now = timezone.now()
        self.owner = make_user('trader1')
        self.item = make_item()

    def test_identical_receipts_within_window_removes_later_one(self):
        trade1 = make_item_trade(self.owner, self.item, quantity=2)
        trade2 = make_item_trade(self.owner, self.item, quantity=2)
        first = make_trade_receipt(self.owner, 'Bob', [trade1], self.now)
        second = make_trade_receipt(self.owner, 'Bob', [trade2], self.now + timedelta(seconds=30))

        Command().handle(dry_run=False)

        self.assertTrue(TradeReceipt.objects.filter(pk=first.pk).exists())
        self.assertFalse(TradeReceipt.objects.filter(pk=second.pk).exists())
        self.assertFalse(ItemTrade.objects.filter(pk=trade2.pk).exists())

    def test_receipts_outside_window_are_not_merged(self):
        trade1 = make_item_trade(self.owner, self.item, quantity=2)
        trade2 = make_item_trade(self.owner, self.item, quantity=2)
        first = make_trade_receipt(self.owner, 'Bob', [trade1], self.now)
        second = make_trade_receipt(self.owner, 'Bob', [trade2], self.now + timedelta(minutes=5))

        Command().handle(dry_run=False)

        self.assertTrue(TradeReceipt.objects.filter(pk=first.pk).exists())
        self.assertTrue(TradeReceipt.objects.filter(pk=second.pk).exists())

    def test_different_quantities_not_treated_as_duplicate(self):
        trade1 = make_item_trade(self.owner, self.item, quantity=1)
        trade2 = make_item_trade(self.owner, self.item, quantity=2)
        first = make_trade_receipt(self.owner, 'Bob', [trade1], self.now)
        second = make_trade_receipt(self.owner, 'Bob', [trade2], self.now + timedelta(seconds=30))

        Command().handle(dry_run=False)

        self.assertTrue(TradeReceipt.objects.filter(pk=first.pk).exists())
        self.assertTrue(TradeReceipt.objects.filter(pk=second.pk).exists())

    def test_two_separate_rows_vs_one_combined_row_still_compared_correctly(self):
        # Both receipts have the same item split across two ItemTrade rows of qty=1 each --
        # the multiset must match another receipt shaped the same way, not a combined qty=2 row.
        trade1a = make_item_trade(self.owner, self.item, quantity=1)
        trade1b = make_item_trade(self.owner, self.item, quantity=1)
        trade2a = make_item_trade(self.owner, self.item, quantity=1)
        trade2b = make_item_trade(self.owner, self.item, quantity=1)
        first = make_trade_receipt(self.owner, 'Bob', [trade1a, trade1b], self.now)
        second = make_trade_receipt(self.owner, 'Bob', [trade2a, trade2b], self.now + timedelta(seconds=30))

        Command().handle(dry_run=False)

        self.assertTrue(TradeReceipt.objects.filter(pk=first.pk).exists())
        self.assertFalse(TradeReceipt.objects.filter(pk=second.pk).exists())

    def test_different_sellers_not_merged(self):
        trade1 = make_item_trade(self.owner, self.item, seller='Bob', quantity=1)
        trade2 = make_item_trade(self.owner, self.item, seller='Alice', quantity=1)
        first = make_trade_receipt(self.owner, 'Bob', [trade1], self.now)
        second = make_trade_receipt(self.owner, 'Alice', [trade2], self.now + timedelta(seconds=30))

        Command().handle(dry_run=False)

        self.assertTrue(TradeReceipt.objects.filter(pk=first.pk).exists())
        self.assertTrue(TradeReceipt.objects.filter(pk=second.pk).exists())

    def test_dry_run_leaves_db_unchanged(self):
        trade1 = make_item_trade(self.owner, self.item, quantity=1)
        trade2 = make_item_trade(self.owner, self.item, quantity=1)
        first = make_trade_receipt(self.owner, 'Bob', [trade1], self.now)
        second = make_trade_receipt(self.owner, 'Bob', [trade2], self.now + timedelta(seconds=30))

        Command().handle(dry_run=True)

        self.assertTrue(TradeReceipt.objects.filter(pk=first.pk).exists())
        self.assertTrue(TradeReceipt.objects.filter(pk=second.pk).exists())

    def test_profile_stats_trade_count_decreases_after_cleanup(self):
        trade1 = make_item_trade(self.owner, self.item, price=5, quantity=1)
        trade2 = make_item_trade(self.owner, self.item, price=5, quantity=1)
        make_trade_receipt(self.owner, 'Bob', [trade1], self.now)
        make_trade_receipt(self.owner, 'Bob', [trade2], self.now + timedelta(seconds=30))

        before = return_profile_stats(self.owner)

        Command().handle(dry_run=False)

        after = return_profile_stats(self.owner)

        self.assertLess(after['number_of_items_bought'], before['number_of_items_bought'])
