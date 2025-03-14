import subprocess
import time

from django.core.management.base import BaseCommand
from main.models import ItemBonus, Job
from main.services.schedule.schedule_service import ScheduleService


class Command(BaseCommand):
    help = 'Runs jobs on a schedule'

    def handle(self, *args, **options):
        while True:
            self.stdout.write(
                self.style.SUCCESS(
                    'Running job queue'
                )
            )
            self.run()
            time.sleep(30)

    def run(self):
        queue_groups = Job.objects.values('queue').distinct()

        for queue_group in queue_groups:
            queue = queue_group['queue']
            self.stdout.write(
                self.style.SUCCESS(
                    f'Running job queue {queue}'
                )
            )
            self.run_queue(queue)

    def run_queue(self, queue: str):
        subprocess.run(['python', 'manage.py', 'jobs', queue])

