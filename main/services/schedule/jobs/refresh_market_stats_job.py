from main.models import Job
from main.market_stats import refresh_all
from main.services.schedule.jobs.abstract_job import AbstractJob


class RefreshMarketStatsJob(AbstractJob):
    """Recompute the homepage "Torn Market Pulse" aggregates into the file cache.

    Anonymised activity counters + daily-trades sparkline + traders-online list.
    Scheduled via a Schedule row (see migration 0060) to run every ~10 minutes so
    the homepage view never has to run these site-wide aggregates itself.
    """

    def handle(self, job: Job, payload: dict):
        self.job = job
        refresh_all()
