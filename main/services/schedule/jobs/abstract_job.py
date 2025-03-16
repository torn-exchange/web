import json
from datetime import datetime
from main.models import Job, Schedule, JobLog
from django.utils import timezone


class AbstractJob:

    job_queue = 'default'
    available_at = datetime.now().timestamp()

    def __init__(self):
        self.job = None

    def dispatch(self, job: str, payload: dict):
        Job.objects.create(
            job=job,
            queue=self.job_queue,
            payload=json.dumps(payload),
            available_at=self.available_at,
            created_at=datetime.now().timestamp()
        )

    def queue(self, queue: str):
        self.job_queue = queue
        return self

    def at(self, timestamp):
        self.available_at = timestamp
        return self

    def log(self, status: str, message: dict = dict()):
        current_class = self.__class__.__name__
        JobLog.objects.create(
            job=current_class,
            status=status,
            message=message,
            created_at=datetime.now().timestamp()
        )

    def resolve(self, success: bool):
        if success:
            self.job.delete()
        else:
            self.job.attempts += 1
            self.job.available_at = timezone.now()
            self.reserved_at = None
            self.job.save()

    def handle(self, payload: dict):
        raise NotImplementedError('You must implement the handle method in your job class')