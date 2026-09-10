"""Sync logic for the Elimination event.

Two data sources, neither of which needs Torn to add anything:

* per-trader team: the ``competition`` object already present in the
  ``user?selections=profile`` response TE fetches every 10 min in
  ``check_online_status``. Shape during the event::

      {"name": "Elimination", "score": 0, "team": "Unknown", "attacks": 0}

  ``team`` is ``"Unknown"`` until the player is assigned to a team.

* team standings: the Torn API v2 ``/torn/elimination`` endpoint.
"""
from __future__ import annotations

import logging

from main.te_utils import log_error

logger = logging.getLogger("cron")

EVENT_KEY = "elimination"
_NO_TEAM = {"", "unknown", "none", "n/a"}


def _clean_team(value) -> str:
    if not value:
        return ""
    value = str(value).strip()
    return "" if value.lower() in _NO_TEAM else value


def upsert_participation(profile, competition: dict, year: int):
    """Create/update this profile's EventParticipation from a ``competition`` dict."""
    from events.models import EventParticipation

    if not competition or str(competition.get("name", "")).lower() != "elimination":
        return None

    team = _clean_team(competition.get("team"))
    defaults = {
        "group_name": team,
        "position": competition.get("position"),
        "score": competition.get("score"),
        "status": str(competition.get("status") or ""),
        "data": competition,
    }
    obj, _ = EventParticipation.objects.update_or_create(
        profile=profile, event_key=EVENT_KEY, year=year, defaults=defaults
    )
    return obj


def sync_standings(year: int):
    """Fetch ``/torn/elimination`` and upsert EventGroupStanding rows."""
    from events.models import EventGroupStanding
    from events.services.torn_elimination_api_service import TornEliminationAPIService

    result = TornEliminationAPIService.get_standings()
    if not result.get("success"):
        logger.warning("elimination.standings.unavailable", extra={"error": result.get("error")})
        return 0

    teams = (result.get("data") or {}).get("teams") or []
    count = 0
    for team in teams:
        name = _clean_team(team.get("name")) or _clean_team(team.get("team"))
        if not name:
            continue
        EventGroupStanding.objects.update_or_create(
            event_key=EVENT_KEY,
            year=year,
            group_name=name,
            defaults={
                "group_key": str(team.get("team") or ""),
                "position": team.get("position"),
                "score": team.get("score"),
                "lives": team.get("lives"),
                "status": str(team.get("status") or ""),
                "data": team,
            },
        )
        count += 1
    logger.info("elimination.standings.synced", extra={"teams": count})
    return count
