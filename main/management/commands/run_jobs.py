import signal
import subprocess
import time
import importlib

from django.core.management.base import BaseCommand
from main.models import ItemBonus, Job
from main.services.schedule.schedule_service import ScheduleService
from django.utils import timezone


class Command(BaseCommand):
    help = "Runs the job queue"

    def add_arguments(self, parser):
        parser.add_argument(
            "queue",
            type=str,
            help="The name of the job queue (e.g., 'default')",
        )

    def handle(self, *args, **options):
        queue = options["queue"]

        try:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Running job queue {queue}'
                )
            )

            self.run(queue)
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error: {e}"))

    def run(self, queue: str):
        jobs = Job.objects.filter(
            queue=queue,
            available_at__lte=timezone.now(),
            reserved_at__isnull=True,
        )


        for job_entry in jobs:
            try:
                job_entry.reserved_at = timezone.now()
                job_entry.available_at = None
                job_entry.attempts += 1
                job_entry.save()

                job_class = self.get_job_class(job_entry)
                job = job_class()
                job.handle(job_entry, job_entry.payload)

            except Exception as e:
                self.stderr.write(
                    self.style.ERROR(
                        f"Error running job {job_entry.id} - {job_entry.job}: {e}"
                    )
                )
                continue

    def get_job_class(self, job: Job):
        module_name, class_name = job.job.rsplit('.', 1)

        try:
            module = importlib.import_module(module_name)
            class_loaded = getattr(module, class_name, None)

            if class_loaded is None:
                raise ImportError(f"Class '{class_name}' not found in module '{module_name}'")

            if not isinstance(class_loaded, type):
                raise TypeError(f"Expected a class but got {type(class_loaded)}")

            return class_loaded

        except ModuleNotFoundError as e:
            raise ImportError(f"Module '{module_name}' not found") from e
