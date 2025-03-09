from django.core.management.base import BaseCommand
from django.db.models import Q
from users.models import Profile
from main.models import Listing

class Command(BaseCommand):
    help = 'Updates listings hidden status based on owner hidden categories'

    def _update(self):
        # Get profiles with non-empty hidden_categories
        profiles = Profile.objects.exclude(hidden_categories={}).exclude(hidden_categories__isnull=True)
        
        self.stdout.write(f'Found {profiles.count()} profiles with hidden categories')
        
        update_count = 0
        for profile in profiles:
            # Get hidden categories for this profile
            hidden_cats = [cat for cat, is_hidden in profile.hidden_categories.items() if is_hidden]
            
            if not hidden_cats:
                continue
                
            # Find and update listings
            listings_to_update = Listing.objects.filter(
                owner=profile,
                item__item_type__in=hidden_cats,
                hidden=False  # Only update those not already hidden
            )
            
            count = listings_to_update.count()
            if count:
                listings_to_update.update(hidden=True)
                update_count += count
                self.stdout.write(
                    f'Updated {count} listings for {profile.name} '
                    f'(categories: {", ".join(hidden_cats)})'
                )

        self.stdout.write(
            self.style.SUCCESS(f'Successfully updated {update_count} listings')
        )

    def handle(self, *args, **options):
        self._update()
