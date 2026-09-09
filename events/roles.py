"""Event role resolution + view guards (Phase 2).

``member`` is implicit: any logged-in profile with an ``EventParticipation`` for
the team is a member, no ``EventRole`` row required. The explicit roles
(captain / vice_captain / treasurer / team_trader) are ``EventRole`` rows.
"""
from __future__ import annotations

from functools import wraps

from django.http import HttpResponseForbidden

from events.models import EventRole, EventParticipation
from events.registry import get_event


def _participation(profile, event_key, year):
    if profile is None:
        return None
    return EventParticipation.objects.filter(
        profile=profile, event_key=event_key, year=year
    ).exclude(group_name="").first()


def team_for(profile, event_key, year) -> str:
    part = _participation(profile, event_key, year)
    return part.group_name if part else ""


def roles_for(profile, event_key, year) -> set:
    """Return the set of role strings this profile holds for the event/year,
    including implicit ``member``."""
    if profile is None:
        return set()
    roles = set(
        EventRole.objects.filter(
            profile=profile, event_key=event_key, year=year
        ).values_list("role", flat=True)
    )
    if _participation(profile, event_key, year) is not None:
        roles.add(EventRole.MEMBER)
    return roles


def has_role(profile, event_key, year, allowed: set) -> bool:
    return bool(roles_for(profile, event_key, year) & set(allowed))


def can_manage_roles(profile, event_key, year) -> bool:
    return has_role(profile, event_key, year, EventRole.ADMIN_ROLES)


def require_event_role(event_key: str, allowed: set):
    """View decorator. ``allowed`` is a set of role strings; ``{"member"}`` just
    needs an EventParticipation. Attaches ``request.event``, ``request.event_year``,
    ``request.event_team``, ``request.event_roles``."""

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            event = get_event(event_key)
            if event is None or not event.is_active():
                return HttpResponseForbidden("Event not active")
            if not request.user.is_authenticated:
                return HttpResponseForbidden("Login required")

            profile = getattr(request.user, "profile", None)
            year = event.current_year()
            roles = roles_for(profile, event_key, year)
            if not roles & set(allowed):
                return HttpResponseForbidden("You don't have access to this team page")

            request.event = event
            request.event_year = year
            request.event_team = team_for(profile, event_key, year)
            request.event_roles = roles
            request.event_profile = profile
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator
