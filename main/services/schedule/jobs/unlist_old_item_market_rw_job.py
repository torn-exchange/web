from main.models import ItemVariation, Job
from main.services.schedule.jobs.abstract_job import AbstractJob


class UnlistOldItemMarketRW(AbstractJob):
    def handle(self, job: Job, payload: dict):
        self.job = job
        print("Marking outdated item variations as unsaleable...")
        super().log("Started")

        latest_record = ItemVariation.objects.filter(market_type="item market").order_by("-last_sync_at").first()

        if not latest_record:
            super().log("No items found for update")
            super().resolve(True)
            return

        latest_sync_at = latest_record.last_sync_at

        updated_count = ItemVariation.objects.filter(
            market_type="item market"
        ).exclude(last_sync_at=latest_sync_at).update(is_saleable=False)

        super().log("Complete", {"updated_items": updated_count})
        super().resolve(True)