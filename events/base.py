"""The event interface every Torn event implements.

An event is a small strategy object. Core apps (``main``, ``users``) never
import a concrete event -- they go through the registry and this interface, so
adding next year's Halloween event is a new module, not edits to core code.
"""
from __future__ import annotations

from typing import Optional


class AbstractEvent:
    #: stable slug, used as ``event_key`` on the generic models and as the
    #: key in the ``/api/profile`` ``event`` object. Never change it.
    key: str = ""
    #: human label for pages / admin.
    label: str = ""

    # -- lifecycle ---------------------------------------------------------
    def current_year(self) -> int:
        raise NotImplementedError

    def is_active(self) -> bool:
        """Drives every feature toggle: sync, API payload, nav, pricing."""
        raise NotImplementedError

    # -- sync ------------------------------------------------------------
    def sync_participant(self, profile, profile_api_data: dict) -> None:
        """Upsert this profile's participation from an already-fetched Torn
        ``user?selections=profile`` response dict. Must be safe to call for
        every trader on every online-status poll; must never raise."""
        raise NotImplementedError

    def sync_standings(self) -> None:
        """Fetch group (team) standings from Torn and upsert
        ``EventGroupStanding`` rows. Called by ``sync_event_standings``."""
        raise NotImplementedError

    # -- read models --------------------------------------------------
    def profile_api_payload(self, profile) -> Optional[dict]:
        """Return the dict for ``/api/profile`` -> ``event[<key>]``, or None
        if this profile is not meaningfully in the event."""
        return None

    # -- pricing -------------------------------------------------------
    def has_group_pricing(self) -> bool:
        """True if traders can offer a same-group (teammate) discount."""
        return False

    def same_group(self, owner_profile, viewer_profile) -> bool:
        """True if viewer is a verified group-mate of owner for this event."""
        return False

    # -- page ----------------------------------------------------------
    def page_context(self, viewer_profile) -> dict:
        return {}

    def template_name(self) -> str:
        return ""
