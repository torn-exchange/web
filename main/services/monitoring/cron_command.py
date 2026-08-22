import logging
import time

import newrelic.agent
from django.core.management.base import BaseCommand

from main.te_utils import log_error

logger = logging.getLogger("cron")


def run_monitored(name, func, *args, verbose=True, **kwargs):
    """Run func(*args, **kwargs) wrapped in a New Relic background_task
    transaction plus structured start/success/failure logging.

    Used directly by daemon-loop commands (run_schedules, run_job_queues)
    to instrument each pass individually, since wrapping their whole
    infinite loop in one transaction wouldn't be meaningful in APM.
    MonitoredCommand uses the same wrapping for single-shot commands.

    verbose=False logs start/success at DEBUG instead of INFO, so routine
    passes of a tight polling loop (every ~5s, forever) don't flood the
    cron_file log handler — failures still always log at ERROR, and the
    New Relic APM transaction is still created either way, so per-iteration
    "did it run, how long" visibility isn't lost, only the log noise is.
    """
    routine_level = logging.INFO if verbose else logging.DEBUG
    start = time.monotonic()
    logger.log(routine_level, "cron.start", extra={"cron_command": name})

    try:
        result = _run_in_background_task(name, func, args, kwargs)
        duration_ms = int((time.monotonic() - start) * 1000)
        logger.log(
            routine_level,
            "cron.success",
            extra={"cron_command": name, "duration_ms": duration_ms},
        )
        return result
    except Exception as e:
        duration_ms = int((time.monotonic() - start) * 1000)
        logger.error(
            "cron.failure",
            extra={"cron_command": name, "duration_ms": duration_ms},
            exc_info=True,
        )
        log_error(e)
        raise


def _run_in_background_task(name, func, args, kwargs):
    try:
        application = newrelic.agent.application()
    except Exception:
        application = None

    if application is None:
        return func(*args, **kwargs)

    with newrelic.agent.BackgroundTask(application, name=name, group="Cron"):
        return func(*args, **kwargs)


class MonitoredCommand(BaseCommand):
    """Base class for management commands invoked by cron.

    Wraps execute() in a New Relic background_task transaction and emits
    structured start/success/failure logs, so cron runs get the same
    "did it run, how long, did it fail" visibility that web requests get
    from APM automatically. Subclasses just implement handle() as usual.
    """

    def execute(self, *args, **options):
        name = self.__class__.__module__.rsplit(".", 1)[-1]
        return run_monitored(name, super().execute, *args, **options)
