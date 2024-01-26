from django.core.management.base import BaseCommand
from main.models import TradeReceipt, ItemTrade


class Command(BaseCommand):

    def _clean(self):

        for item in ItemTrade.objects.all():
            if len(item.seller) > 250:
                item.seller = ''
                item.save()
                print('altering field')

        for item in TradeReceipt.objects.all():
            if len(item.seller) > 250:
                item.seller = ''
                item.save()
                print('altering field')

    def handle(self, *args, **options):
        self._clean()
