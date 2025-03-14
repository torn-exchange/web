import json
from datetime import datetime

from main.models import Job, Schedule


class Job:

    job_queue = 'default'
    available_at = datetime.now().timestamp()

    @classmethod
    def dispatch(cls, job: str, payload: dict):
        Job.objects.create(
            job=job,
            queue=cls.job_queue,
            payload=json.dumps(payload),
            available_at=cls.available_at,
            created_at=datetime.now().timestamp()
        )

    @classmethod
    def queue(cls, queue: str):
        cls.job_queue = queue
        return cls

    @classmethod
    def at(cls, timestamp):
        cls.available_at = timestamp
        return cls

    @classmethod
    def handle(cls, payload: dict):
        raise NotImplementedError('You must implement the handle method in your job class')