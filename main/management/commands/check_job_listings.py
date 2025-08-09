from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from users.models import Settings


class Command(BaseCommand):
    def _update(self):
        print('Removing stale job listings')
        for setting in Settings.objects.filter(job_seeking=True, job_post_start_date__lte=timezone.now()-timedelta(days=40)):
            print(f'Job listing for {setting.owner.name} has become stale')
            setting.job_seeking = False
            setting.save()

    def handle(self, *args, **options):
        self._update()
