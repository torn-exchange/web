from typing import Optional
from datetime import timedelta
from django.utils import timezone
from main.models import Schedule, Job


class ScheduleService:

    @classmethod
    def handle(cls):
        for schedule in cls.get_runnable():
            if schedule.unique:
                existing = Job.objects.filter(job=schedule.job, payload=schedule.payload).first()
                if existing is not None:
                    continue

            schedule.last_ran_at = timezone.now()
            schedule.save()

            cls.dispatch(schedule.job, schedule.payload)

    @classmethod
    def dispatch(cls, job: str, payload: dict):
        Job.objects.create(
            job=job,
            queue='default',
            payload=payload,
            available_at=timezone.now(),
            created_at=timezone.now()
        )

    @classmethod
    def get_runnable(cls):
        schedules = Schedule.objects.filter(active=True).all()

        runnable = []
        for schedule in schedules:
            if not cls.should_run(schedule.run_at, schedule.last_ran_at):
                continue

            runnable.append(schedule)
        return runnable

    @classmethod
    def should_run(cls, run_at: dict, last_ran_at: Optional[timezone.datetime]) -> bool:
        now = timezone.now()

        if last_ran_at is not None and timezone.is_naive(last_ran_at):
            last_ran_at = timezone.make_aware(last_ran_at)

        every = run_at.get("every")
        x = run_at.get("x", 0)
        period = run_at.get("period")

        if not every or not period:
            return False

        if last_ran_at is None:
            return True

        elapsed_time = now - last_ran_at

        if period == "second":
            elapsed_seconds = elapsed_time.total_seconds()
            return elapsed_seconds >= every and now.second % every == x

        elif period == "minute":
            elapsed_minutes = elapsed_time.total_seconds() // 60
            return elapsed_minutes >= every and now.minute % every == x

        elif period == "hour":
            elapsed_hours = elapsed_time.total_seconds() // 3600
            return elapsed_hours >= every and now.hour % every == x

        elif period == "day":
            elapsed_days = elapsed_time.days
            return elapsed_days >= every and now.day % every == x

        elif period == "week":
            elapsed_weeks = elapsed_time.days // 7
            return elapsed_weeks >= every and now.isoweekday() == x

        elif period == "month":
            elapsed_months = (now.year - last_ran_at.year) * 12 + (now.month - last_ran_at.month)
            return elapsed_months >= every and now.day == x

        elif period == "year":
            elapsed_years = now.year - last_ran_at.year
            return elapsed_years >= every and now.month == x

        return False