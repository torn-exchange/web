"""The event registry.

Everything outside the ``events`` app that needs "the events happening right
now" goes through :func:`active_events`. Register a new event by adding its
instance to ``_ALL_EVENTS``.
"""
from __future__ import annotations

from typing import List, Optional

from events.base import AbstractEvent
from events.elimination.event import EliminationEvent

_ALL_EVENTS: List[AbstractEvent] = [
    EliminationEvent(),
]

_BY_KEY = {e.key: e for e in _ALL_EVENTS}


def all_events() -> List[AbstractEvent]:
    return list(_ALL_EVENTS)


def get_event(key: str) -> Optional[AbstractEvent]:
    return _BY_KEY.get(key)


def active_events() -> List[AbstractEvent]:
    return [e for e in _ALL_EVENTS if e.is_active()]
