from django.core.management.base import BaseCommand
from main.models import Listing, TradeReceipt
from users.models import User
import datetime


class Command(BaseCommand):

    def _clean(self):
        today = datetime.date.today()
        last_month = today - datetime.timedelta(days=30)
        active_traders = set([a.owner.user for a in TradeReceipt.objects.filter(
            created_at__range=(last_month, today)).distinct('owner')])
        users_logged_in_recently = set(
            [a for a in User.objects.filter(last_login__range=(last_month, today))])
        listings_to_delete = Listing.objects.exclude(
            owner__user__in=active_traders.union(users_logged_in_recently)).delete()

    def handle(self, *args, **options):
        self._clean()
