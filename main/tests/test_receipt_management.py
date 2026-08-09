from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from main.filters import ReceiptSearchFilter
from main.models import Item, ItemTrade, TradeReceipt


def make_user(username):
    user = User.objects.create(username=username)
    profile = user.profile
    profile.name = username
    profile.torn_id = username
    profile.save()
    return user, profile


def make_item(name='Xanax', item_id=206, te_value=800000):
    return Item.objects.create(
        name=name,
        description='',
        requirement='',
        item_type='Drug',
        weapon_type=None,
        buy_price=0,
        sell_price=0,
        market_value=te_value,
        circulation=10000,
        image_url='',
        TE_value=te_value,
        item_id=item_id,
    )


def make_item_trade(owner, item, seller, price=10, quantity=1):
    return ItemTrade.objects.create(owner=owner, seller=seller, item=item, price=price, quantity=quantity)


def make_trade_receipt(owner, seller, item_trades, created_at):
    receipt = TradeReceipt.objects.create(owner=owner, seller=seller)
    receipt.items_trades.set(item_trades)
    TradeReceipt.objects.filter(pk=receipt.pk).update(created_at=created_at)
    receipt.refresh_from_db()
    return receipt


class ReceiptSearchFilterTests(TestCase):

    def setUp(self):
        self.now = timezone.now()
        self.user, self.profile = make_user('trader1')
        _, self.other_profile = make_user('Glasnost')
        self.xanax = make_item(name='Xanax', item_id=206)
        self.plushie = make_item(name='Plushie', item_id=999)

        # trader1 buys 50 Xanax from Glasnost
        self.purchase_trade = make_item_trade(self.profile, self.xanax, seller='Glasnost', price=800000, quantity=50)
        self.purchase_receipt = make_trade_receipt(
            self.profile, 'Glasnost', [self.purchase_trade], self.now - timedelta(days=40))

        # trader1 buys 5 Plushies from Someone
        self.plushie_trade = make_item_trade(self.profile, self.plushie, seller='Someone', price=100, quantity=5)
        self.plushie_receipt = make_trade_receipt(
            self.profile, 'Someone', [self.plushie_trade], self.now - timedelta(days=1))

        # Glasnost buys 200 Xanax from trader1 (trader1 was the seller here)
        self.sale_trade = make_item_trade(self.other_profile, self.xanax, seller='trader1', price=850000, quantity=200)
        self.sale_receipt = make_trade_receipt(
            self.other_profile, 'trader1', [self.sale_trade], self.now - timedelta(days=2))

    def base_queryset(self):
        from django.db.models import Q
        return TradeReceipt.objects.filter(
            Q(owner=self.profile) | Q(seller__iexact=self.profile.name)
        )

    def test_default_returns_all_receipts_for_both_roles(self):
        f = ReceiptSearchFilter({}, queryset=self.base_queryset(), profile=self.profile)
        pks = set(f.qs.values_list('pk', flat=True))
        self.assertEqual(pks, {self.purchase_receipt.pk, self.plushie_receipt.pk, self.sale_receipt.pk})

    def test_filter_by_seller_name(self):
        f = ReceiptSearchFilter({'seller': 'glasn'}, queryset=self.base_queryset(), profile=self.profile)
        pks = set(f.qs.values_list('pk', flat=True))
        self.assertEqual(pks, {self.purchase_receipt.pk})

    def test_filter_by_item_and_quantity(self):
        f = ReceiptSearchFilter(
            {'item_name': 'Xanax', 'quantity_min': 100},
            queryset=self.base_queryset(), profile=self.profile)
        pks = set(f.qs.values_list('pk', flat=True))
        self.assertEqual(pks, {self.sale_receipt.pk})

    def test_item_and_quantity_do_not_cross_match_different_trades(self):
        # No single item trade in these receipts has both item=Plushie and quantity>=100.
        f = ReceiptSearchFilter(
            {'item_name': 'Plushie', 'quantity_min': 100},
            queryset=self.base_queryset(), profile=self.profile)
        self.assertEqual(f.qs.count(), 0)

    def test_filter_by_date_range(self):
        date_from = (self.now - timedelta(days=3)).date().isoformat()
        f = ReceiptSearchFilter({'date_from': date_from}, queryset=self.base_queryset(), profile=self.profile)
        pks = set(f.qs.values_list('pk', flat=True))
        self.assertEqual(pks, {self.plushie_receipt.pk, self.sale_receipt.pk})

    def test_filter_by_role_buyer(self):
        f = ReceiptSearchFilter({'role': 'buyer'}, queryset=self.base_queryset(), profile=self.profile)
        pks = set(f.qs.values_list('pk', flat=True))
        self.assertEqual(pks, {self.purchase_receipt.pk, self.plushie_receipt.pk})

    def test_filter_by_role_seller(self):
        f = ReceiptSearchFilter({'role': 'seller'}, queryset=self.base_queryset(), profile=self.profile)
        pks = set(f.qs.values_list('pk', flat=True))
        self.assertEqual(pks, {self.sale_receipt.pk})

    def test_filters_are_combinable(self):
        f = ReceiptSearchFilter(
            {'role': 'buyer', 'item_name': 'Xanax'},
            queryset=self.base_queryset(), profile=self.profile)
        pks = set(f.qs.values_list('pk', flat=True))
        self.assertEqual(pks, {self.purchase_receipt.pk})


class ReceiptManagementViewTests(TestCase):

    def setUp(self):
        self.now = timezone.now()
        self.user, self.profile = make_user('trader1')
        self.item = make_item()
        self.trade = make_item_trade(self.profile, self.item, seller='Glasnost', price=800000, quantity=50)
        self.receipt = make_trade_receipt(self.profile, 'Glasnost', [self.trade], self.now)

    def test_requires_login(self):
        response = self.client.get(reverse('receipt_management'))
        self.assertNotEqual(response.status_code, 200)

    def test_bare_page_load_runs_no_search(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('receipt_management'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['result_count'], 0)
        self.assertFalse(response.context['has_search'])
        self.assertNotContains(response, 'Glasnost')

    def test_lists_own_receipts_when_search_submitted(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('receipt_management'), {'seller': ''})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['has_search'])
        self.assertContains(response, 'Glasnost')

    def test_amount_filter_applied_in_view(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('receipt_management'), {'amount_min': 100_000_000})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['result_count'], 0)

        response = self.client.get(reverse('receipt_management'), {'amount_min': 1000})
        self.assertEqual(response.context['result_count'], 1)


class DeleteReceiptOwnershipTests(TestCase):

    def setUp(self):
        self.now = timezone.now()
        self.owner_user, self.owner_profile = make_user('trader1')
        self.other_user, self.other_profile = make_user('trader2')
        self.item = make_item()
        self.trade = make_item_trade(self.owner_profile, self.item, seller='Glasnost')
        self.receipt = make_trade_receipt(self.owner_profile, 'Glasnost', [self.trade], self.now)

    def test_anonymous_cannot_delete(self):
        response = self.client.post(reverse('delete_receipt', args=[self.receipt.id]))
        self.assertNotEqual(response.status_code, 200)
        self.assertTrue(TradeReceipt.objects.filter(pk=self.receipt.pk).exists())

    def test_other_user_cannot_delete_someone_elses_receipt(self):
        self.client.force_login(self.other_user)
        response = self.client.post(reverse('delete_receipt', args=[self.receipt.id]))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(TradeReceipt.objects.filter(pk=self.receipt.pk).exists())

    def test_owner_can_delete_own_receipt(self):
        self.client.force_login(self.owner_user)
        response = self.client.post(reverse('delete_receipt', args=[self.receipt.id]))
        self.assertIn(response.status_code, (301, 302))
        self.assertFalse(TradeReceipt.objects.filter(pk=self.receipt.pk).exists())
