from __future__ import annotations

import logging
from typing import Optional

from events import config
from events.base import AbstractEvent
from events.elimination import sync

logger = logging.getLogger("cron")

EVENT_KEY = "elimination"


class EliminationEvent(AbstractEvent):
    key = EVENT_KEY
    label = "Elimination"

    def current_year(self) -> int:
        return config.ELIMINATION_YEAR

    def is_active(self) -> bool:
        return bool(config.ELIMINATION_ENABLED)

    # -- sync ------------------------------------------------------------
    def sync_participant(self, profile, profile_api_data: dict) -> None:
        try:
            competition = (profile_api_data or {}).get("competition")
            sync.upsert_participation(profile, competition, self.current_year())
        except Exception as e:  # never break the online-status poll
            log_error_safely(e)

    def sync_standings(self) -> None:
        sync.sync_standings(self.current_year())

    # -- reads ---------------------------------------------------------
    def _participation(self, profile):
        from events.models import EventParticipation

        if profile is None:
            return None
        return (
            EventParticipation.objects.filter(
                profile=profile, event_key=self.key, year=self.current_year()
            )
            .first()
        )

    def profile_api_payload(self, profile) -> Optional[dict]:
        part = self._participation(profile)
        if part is None or not part.group_name:
            return None
        from events.models import EventRole

        roles = sorted(
            EventRole.objects.filter(
                profile=profile, event_key=self.key, year=self.current_year()
            ).values_list("role", flat=True)
        )
        return {
            "team": part.group_name,
            "position": part.position,
            "score": part.score,
            "status": part.status or None,
            "roles": roles,
        }

    # -- pricing -----------------------------------------------------
    def has_group_pricing(self) -> bool:
        return True

    def same_group(self, owner_profile, viewer_profile) -> bool:
        if owner_profile is None or viewer_profile is None:
            return False
        owner_part = self._participation(owner_profile)
        viewer_part = self._participation(viewer_profile)
        return bool(
            owner_part
            and viewer_part
            and owner_part.group_name
            and owner_part.group_name == viewer_part.group_name
        )

    # -- page ------------------------------------------------------
    def template_name(self) -> str:
        return "events/elimination.html"

    def page_context(self, viewer_profile) -> dict:
        from events.models import EventGroupStanding
        from events.elimination.team_traders import team_traders_for, all_participating_traders

        part = self._participation(viewer_profile)
        team = part.group_name if part else ""
        standings = list(
            EventGroupStanding.objects.filter(event_key=self.key, year=self.current_year())
        )
        all_teams, totals = all_participating_traders(self.current_year())
        return {
            "event_label": self.label,
            "event_year": self.current_year(),
            "is_authenticated": viewer_profile is not None,
            "viewer_team": team,
            "in_event": bool(part),
            "standings": standings,
            "my_team_standing": next((s for s in standings if s.group_name == team), None),
            "team_traders": team_traders_for(team) if team else [],
            # public content
            "all_teams": all_teams,
            "totals": totals,
        }


def log_error_safely(e):
    try:
        from main.te_utils import log_error

        log_error(e)
    except Exception:
        logger.exception("elimination.sync_participant failed")
