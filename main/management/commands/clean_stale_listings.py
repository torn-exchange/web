from main.services.monitoring.cron_command import MonitoredCommand
from main.models import Listing, TradeReceipt, set_listing_hidden_reason
from users.models import User, Profile
import datetime


class Command(MonitoredCommand):

    def _clean(self):
        today = datetime.datetime.now(tz=datetime.timezone.utc)
        last_month = today - datetime.timedelta(days=30)

        active_trade_user_ids = set(
            TradeReceipt.objects.filter(
                created_at__range=(last_month, today)
            ).distinct('owner').values_list('owner__user', flat=True)
        )
        users_logged_in_recently_ids = set(
            User.objects.filter(last_login__range=(last_month, today)).values_list('pk', flat=True)
        )

        active_user_ids = active_trade_user_ids.union(users_logged_in_recently_ids)
        active_profiles = Profile.objects.filter(user__pk__in=active_user_ids)

        inactive_listings = Listing.objects.exclude(owner__in=active_profiles)
        inactive_profile_ids = set(inactive_listings.values_list('owner__pk', flat=True))

        set_listing_hidden_reason(inactive_listings, inactivity=True)

        Profile.objects.filter(pk__in=inactive_profile_ids).update(active_trader=False)

    def handle(self, *args, **options):
        self._clean()
