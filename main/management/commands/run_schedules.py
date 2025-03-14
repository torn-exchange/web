import time

from django.core.management.base import BaseCommand
from main.models import ItemBonus
from main.services.schedule.schedule_service import ScheduleService


class Command(BaseCommand):
    help = 'Runs jobs on a schedule'

    def handle(self, *args, **options):
        while True:
            self.stdout.write(
                self.style.SUCCESS(
                    'Running scheduled jobs...'
                )
            )
            self.run()
            time.sleep(5)

    def run(self):
        try:
            ScheduleService.handle()
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f'Unhandled exception: {e} tracestring not object: {e.__traceback__}'
                )
            )
