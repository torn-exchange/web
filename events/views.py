from functools import wraps

from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.cache import cache_page

from users.models import Profile
from events.registry import active_events, get_event


def _cache_for_anonymous(timeout):
    """Cache the response for anonymous visitors only; logged-in users always
    get a fresh, personalised render."""
    def decorator(view_func):
        cached = cache_page(timeout)(view_func)

        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if request.user.is_authenticated:
                return view_func(request, *args, **kwargs)
            return cached(request, *args, **kwargs)

        return _wrapped

    return decorator


def event_index(request):
    events = active_events()
    if len(events) == 1:
        return redirect("event_page", key=events[0].key)
    return render(
        request,
        "events/index.html",
        {"page_title": "Torn Events - Torn Exchange", "events": events},
    )


@_cache_for_anonymous(300)
def event_page(request, key):
    event = get_event(key)
    if event is None or not event.is_active():
        raise Http404("Unknown or inactive event")

    profile = None
    if request.user.is_authenticated:
        profile = Profile.objects.filter(user=request.user).first()
        # Refresh the viewer's own participation on demand so a first-time
        # visitor doesn't have to wait for the next online-status poll.
        _refresh_participation(event, profile)

    context = {
        "page_title": f"{event.label} {event.current_year()} - Torn Exchange",
        "event_key": event.key,
    }
    context.update(event.page_context(profile))
    return render(request, event.template_name(), context)


def _refresh_participation(event, profile):
    if profile is None or not profile.api_key:
        return
    try:
        import os
        import requests

        comment = os.getenv("API_COMMENT") or ""
        resp = requests.get(
            f"https://api.torn.com/user/?selections=profile&key={profile.api_key}{comment}",
            timeout=8,
        )
        data = resp.json()
        if "error" not in data:
            event.sync_participant(profile, data)
    except Exception:
        pass
