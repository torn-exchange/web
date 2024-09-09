import requests
import json
import traceback

from django.core.management.base import BaseCommand
from django.utils import timezone
from users.models import Profile
from main.models import Listing
from datetime import datetime


'''
Command that should be run every 10 minutes as a cron job.
It checks player's online status.
'''
class Command(BaseCommand):
    def _update(self):
        print('Updating activity status of all profiles')
        active_traders = set(
            [a.owner.user for a in Listing.objects.filter().distinct('owner')])
        other_advertisers = set([a.user for a in Profile.objects.filter(settings__job_seeking=True) |
                                 Profile.objects.filter(settings__selling_losses=True) |
                                 Profile.objects.filter(settings__selling_revives=True) |
                                 Profile.objects.filter(
                                     settings__selling_company=True)
                                 ])
        users_to_be_checked = active_traders.union(other_advertisers)

        for profile in Profile.objects.filter(user__in=users_to_be_checked):
            if profile.api_key != '':
                req = requests.get(
                    f'https://api.torn.com/user/?selections=profile&key={profile.api_key}')
                data = json.loads(req.content)
                
                try:
                    status = data['last_action']['status']
                    time_stamp = data['last_action']['timestamp']
                    date_time = datetime.fromtimestamp(time_stamp)
                    naive_datetime = date_time
                    aware_datetime = timezone.make_aware(naive_datetime)
                    
                    profile.activity_status = status
                    profile.last_active = aware_datetime
                    profile.save()
                    print(profile.name, status, date_time)
                except KeyError as e:
                    if data.get('error').get('error') == 'Incorrect key':
                        print(f'{profile.name} API key stale, cleaning from DB!')
                        profile.api_key = ''
                        profile.activity_status = 'Offline'
                        profile.save()
                        traceback.print_exc()
                    pass
        print('Done')

    def handle(self, *args, **options):
        self._update()
