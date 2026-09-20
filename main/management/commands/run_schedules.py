import time

from django.core.management.base import BaseCommand
from main.models import ItemBonus
from main.services.schedule.schedule_service import ScheduleService
from main.services.monitoring.cron_command import run_monitored

POLL_INTERVAL_SECONDS = 20


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
            time.sleep(POLL_INTERVAL_SECONDS)

    def run(self):
        try:
            runnable = ScheduleService.get_runnable()
            if runnable:
                run_monitored('run_schedules', ScheduleService.handle, runnable, verbose=False)
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f'Unhandled exception: {e} tracestring not object: {e.__traceback__}'
                )
            )
