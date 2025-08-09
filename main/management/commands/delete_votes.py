from django.core.management.base import BaseCommand
from users.models import Profile
from django.core.exceptions import ObjectDoesNotExist


class Command(BaseCommand):
    
    def add_arguments(self, parser):
        parser.add_argument('name', nargs='?', type=str)

    def _vote_check(self, name):
        try:
            profile = Profile.objects.filter(name=name).get()
        except ObjectDoesNotExist:
            print(f'User "{name}" does not exist')
            return
        
        deleted = 0
        for vote_item in profile.votes.user_ids():
            profile.votes.delete(vote_item[0])
            deleted += 1
            
        print("Number of deleted votes:", deleted)

    def handle(self, *args, **options):
        if options['name']:
            name = options['name']
            print("Deleting names for user: ", name)
            self._vote_check(name)
        else:
            print("You must provide a user name")
        
