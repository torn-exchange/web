"""Helpers the ``main`` API layer calls to expose event data."""
from __future__ import annotations

from events.registry import active_events


def build_event_payload(profile) -> dict:
    """Return ``{"elimination": {...}, ...}`` for ``/api/profile``.

    Only includes events that are active AND that this profile is
    meaningfully participating in.
    """
    payload = {}
    for event in active_events():
        try:
            data = event.profile_api_payload(profile)
        except Exception:
            data = None
        if data:
            payload[event.key] = data
    return payload
