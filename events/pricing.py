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


def event_effective_price(listing, viewer_profile):
    """Return ``(price, applied_pct, event_key)``.

    ``price`` is ``listing.effective_price`` with the owner's active-event
    teammate discount applied, iff ``viewer_profile`` is a verified group-mate.
    Falls back to ``(listing.effective_price, 0, None)``.
    """
    base = listing.effective_price
    if base is None or viewer_profile is None:
        return base, 0, None

    try:
        item_id = int(listing.item.item_id)
    except (TypeError, ValueError):
        item_id = 0
    if item_id > _CUSTOM_ITEM_CUTOFF:
        return base, 0, None

    owner_profile = listing.owner
    for event in active_events():
        if not event.has_group_pricing():
            continue
        if not event.same_group(owner_profile, viewer_profile):
            continue

        pct = _discount_pct(listing, owner_profile, event)
        if pct <= 0:
            continue
        pct = min(pct, 90)
        discounted = round(base * (100 - pct) / 100.0)
        return discounted, pct, event.key

    return base, 0, None


def _discount_pct(listing, owner_profile, event) -> int:
    override = getattr(listing, "event_discount_pct", None)
    if override is not None:
        return int(override)

    from events.models import EventTraderSettings

    row = EventTraderSettings.objects.filter(
        profile=owner_profile, event_key=event.key, year=event.current_year()
    ).first()
    return int(row.group_discount_pct) if row else 0


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
