import signal
import subprocess
import time

from django.core.management.base import BaseCommand
from main.models import ItemBonus, Job
from main.services.schedule.schedule_service import ScheduleService


class Command(BaseCommand):
    help = "Runs the job queue"

    def handle(self, *args, **options):
        queue = args[0]

        try:
            self.stdout.write(self.style.SUCCESS("Running job queue"))
            self.run(queue)
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error: {e}"))

    def run(self, queue: str):
        jobs = Job.objects.filter(
            queue=queue,
            available_at__lte=time.time()
        )

        for job in jobs:
            try:
                job_class = self.get_job_class(job)
                job_class.handle(job.payload)
            except Exception as e:
                self.stderr.write(
                    self.style.ERROR(
                        f"Error running job {job.id} - {job.job}: {e}"
                    )
                )
                continue

    def get_job_class(self, job: Job):
        module_name, class_name = job.job.rsplit('.', 1)
        module = __import__(module_name, fromlist=[class_name])
        class_loaded = getattr(module, class_name)
        return class_loaded
