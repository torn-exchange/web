from events.registry import active_events


def events(request):
    """Expose active events (+ the viewer's roles) to every template (navbar)."""
    try:
        evs = active_events()
    except Exception:
        evs = []

    profile = getattr(getattr(request, "user", None), "profile", None)
    nav = []
    for e in evs:
        roles = set()
        if profile is not None:
            try:
                from events.roles import roles_for

                roles = roles_for(profile, e.key, e.current_year())
            except Exception:
                roles = set()
        nav.append({
            "key": e.key,
            "label": e.label,
            "roles": sorted(roles),
            "has_role": bool(roles),
            "is_captain": bool(roles & {"captain", "vice_captain"}),
        })

    return {
        "active_events": [{"key": n["key"], "label": n["label"]} for n in nav],
        "event_nav": nav,
    }
