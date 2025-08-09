import json
import requests
import  concurrent.futures

from django.db import connection, reset_queries
from django.core.management.base import BaseCommand

from users.models import Profile


class Command(BaseCommand):
    def _prune(self):
        profiles = get_profiles_with_keys()
                
        def check_profile(profile):
            return profile.id if not ping_torn_api(profile.api_key) else None

        MAX_THREADS = 4

        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
            results = list(executor.map(check_profile, profiles))

        # Filter out None values
        ids_to_prune = [result for result in results if result is not None]
        
        print("New invalid keys to delete:", len(ids_to_prune))
        
        # Bulk update all profiles with those IDs
        Profile.objects.filter(id__in=ids_to_prune).update(api_key='')
        
        print('Done!')
        print("Total database queries:", len(connection.queries))


    def handle(self, *args, **options):
        reset_queries()
        self._prune()


# get all non-empty API keys from the DB
def get_profiles_with_keys():
    profiles_with_keys = Profile.objects.exclude(api_key='')
    print("Total API keys to check:", len(profiles_with_keys))
    
    # If there are no profiles with API keys, handle it accordingly
    if not profiles_with_keys.exists():
        return ''

    return profiles_with_keys


# Make a dummy call just to check whether the key is still valid or not
def ping_torn_api(api_key):
    url = f'https://api.torn.com/v2/market/?selections=timestamp&key={api_key}'
    req = requests.get(url)
    data = json.loads(req.content)
    
    # Possible errors:
    #  2 => Incorrect key
    # 10 => Key owner is in federal jail
    # 13 => The key is temporary disabled due to owner inactivity
    # 16 => Access level of this key is not high enough
    # 18 => API key has been paused by the owner
    if data.get("error", {}).get("code") in {2, 10, 13, 16, 18}:
        return False
    
    return True
