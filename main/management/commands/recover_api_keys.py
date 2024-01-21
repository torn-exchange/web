from users.models import Profile
import json
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    def _recover(self):
        with open('old_profiles.json','r') as file:
            data = json.load(file)
        for item in data:
            name = (item.get('fields').get('name'))
            api_key = (item.get('fields').get('api_key'))
            user = Profile.objects.filter(name=name).first()
            print(user)
            user.api_key = api_key
            user.save()
    def handle(self, *args, **options):
        self._recover()