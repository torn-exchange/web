"""Event-aware pricing.

The teammate discount is **viewer-dependent** and therefore can never live in
``Listing.effective_price`` (which is denormalized and shared by everyone).
It is computed here at display / API time only.
"""
from __future__ import annotations

from events.registry import active_events

# Custom TE items (Sets, Properties, ...) -- the global trade fee already skips
# these, so team discounts skip them too for consistency.
_CUSTOM_ITEM_CUTOFF = 9000


def team_price_fn(owner_profile, viewer_profile):
    """Resolve the teammate-discount context for ``viewer_profile`` looking at
    ``owner_profile``'s price list **once**, and return a cheap per-listing
    pricing function ``fn(listing) -> (price, pct, event_key)``.

    Returns ``None`` when no discount can apply (not logged in, not a group-mate,
    no active group-pricing event) so the caller can skip the whole list.
    All DB work (team lookups, trader-wide %) happens here, not per listing.
    """
    if owner_profile is None or viewer_profile is None:
        return None

    for event in active_events():
        if not event.has_group_pricing():
            continue
        if not event.same_group(owner_profile, viewer_profile):
            continue

        from events.models import EventTraderSettings

        row = EventTraderSettings.objects.filter(
            profile=owner_profile, event_key=event.key, year=event.current_year()
        ).first()
        trader_pct = int(row.group_discount_pct) if row else 0
        event_key = event.key

        def _price(listing):
            base = listing.effective_price
            if base is None:
                return base, 0, None
            try:
                item_id = int(listing.item.item_id)
            except (TypeError, ValueError):
                item_id = 0
            if item_id > _CUSTOM_ITEM_CUTOFF:
                return base, 0, None
            override = getattr(listing, "event_discount_pct", None)
            pct = int(override) if override is not None else trader_pct
            if pct <= 0:
                return base, 0, None
            pct = min(pct, 90)
            return round(base * (100 - pct) / 100.0), pct, event_key

        return _price

    return None


def event_effective_price(listing, viewer_profile):
    """Single-listing convenience wrapper around :func:`team_price_fn`.

    Returns ``(price, applied_pct, event_key)``; falls back to
    ``(listing.effective_price, 0, None)``.
    """
    fn = team_price_fn(listing.owner, viewer_profile)
    if fn is None:
        return listing.effective_price, 0, None
    return fn(listing)


def save_trader_event_settings(profile, post_data):
    """Persist the trader's per-event settings from a POST dict.

    Reads ``event_<key>_discount`` fields; ignores unknown / inactive events.
    """
    from events.models import EventTraderSettings

    saved = {}
    for event in active_events():
        if not event.has_group_pricing():
            continue
        field = f"event_{event.key}_discount"
        if field not in post_data:
            continue
        try:
            pct = max(0, min(90, int(float(post_data.get(field) or 0))))
        except (TypeError, ValueError):
            continue
        EventTraderSettings.objects.update_or_create(
            profile=profile,
            event_key=event.key,
            year=event.current_year(),
            defaults={"group_discount_pct": pct},
        )
        saved[event.key] = pct
    return saved


def price_list_team_banner(owner_profile, viewer_profile):
    """Decide which Elimination banner (if any) a price list should show.

    Returns a dict or None:
      {"state": "teammate", "team": "<name>", "event_label": "Elimination"}
        -- viewer is logged in and on the SAME Elimination team as the trader
      {"state": "login", "event_label": "Elimination"}
        -- viewer is anonymous, trader is in an Elimination team
    None in every other case (trader not in a team; logged-in viewer not on the
    trader's team; event inactive).
    """
    from events.registry import get_event

    event = get_event("elimination")
    if event is None or not event.is_active():
        return None

    owner_part = event._participation(owner_profile)
    owner_team = owner_part.group_name if owner_part else ""
    if not owner_team:
        return None

    if viewer_profile is None:
        return {"state": "login", "event_label": event.label}

    viewer_part = event._participation(viewer_profile)
    viewer_team = viewer_part.group_name if viewer_part else ""
    if viewer_team and viewer_team == owner_team:
        return {"state": "teammate", "team": owner_team, "event_label": event.label}
    return None


def trader_event_settings(profile):
    """Return ``{event_key: group_discount_pct}`` for active group-pricing events."""
    from events.models import EventTraderSettings

    result = {}
    for event in active_events():
        if not event.has_group_pricing():
            continue
        row = EventTraderSettings.objects.filter(
            profile=profile, event_key=event.key, year=event.current_year()
        ).first()
        result[event.key] = row.group_discount_pct if row else 0
    return result
