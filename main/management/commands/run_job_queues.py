import sys
import subprocess
import time

from django.core.management.base import BaseCommand
from main.models import ItemBonus, Job
from main.services.monitoring.cron_command import run_monitored


class Command(BaseCommand):
    help = 'Runs jobs on a schedule'

    def handle(self, *args, **options):
        while True:
            self.run()
            time.sleep(5)


    def run(self):
        queue_groups = Job.objects.values('queue').distinct()

        for queue_group in queue_groups:
            queue = queue_group['queue']
            run_monitored(f'run_job_queues.{queue}', self.run_queue, queue, verbose=False)

    def run_queue(self, queue: str):
        subprocess.Popen([sys.executable, "manage.py", "run_jobs", queue])
