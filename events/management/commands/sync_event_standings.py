"""Sync team/group standings for every active Torn event.

Run on cron every ~10-15 min while any event is live (see
crons/sync_event_standings.sh). No-op when no event is active.
"""
from main.services.monitoring.cron_command import MonitoredCommand
from main.te_utils import log_error
from events.registry import active_events


class Command(MonitoredCommand):
    help = "Fetch and store group standings for all active Torn events."

    def handle(self, *args, **options):
        events = active_events()
        if not events:
            self.stdout.write("No active events.")
            return

        for event in events:
            try:
                event.sync_standings()
                self.stdout.write(f"Synced standings for '{event.key}'.")
            except Exception as e:
                log_error(e)
                self.stderr.write(f"Failed to sync '{event.key}': {e}")
