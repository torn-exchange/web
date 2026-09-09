from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from users.models import Profile
from events.models import EventParticipation, EventRole, EventGroupStanding
from events.roles import require_event_role
from events.treasury import ledger

EVENT_KEY = "elimination"

# roles a captain / vice-captain may assign
ASSIGNABLE = [EventRole.VICE_CAPTAIN, EventRole.TREASURER, EventRole.TEAM_TRADER]


@require_event_role(EVENT_KEY, EventRole.ADMIN_ROLES)
def captain_dashboard(request):
    team, year = request.event_team, request.event_year

    roster = (
        EventParticipation.objects.filter(event_key=EVENT_KEY, year=year, group_name=team)
        .select_related("profile")
        .order_by("profile__name")
    )
    roles_by_profile = {}
    for r in EventRole.objects.filter(event_key=EVENT_KEY, year=year, team_name=team):
        roles_by_profile.setdefault(r.profile_id, []).append(r.role)

    members = [
        {"profile": p.profile, "roles": roles_by_profile.get(p.profile_id, [])}
        for p in roster
    ]
    stock, cash = ledger.on_hand(team, EVENT_KEY, year)
    standing = EventGroupStanding.objects.filter(
        event_key=EVENT_KEY, year=year, group_name=team
    ).first()

    return render(request, "events/captain.html", {
        "page_title": f"{request.event.label} captain - Torn Exchange",
        "team": team,
        "members": members,
        "assignable_roles": ASSIGNABLE,
        "standing": standing,
        "donor_totals": ledger.donor_totals(team, EVENT_KEY, year)[:5],
        "stock_lines": len(stock),
        "cash": cash,
    })


@require_POST
@require_event_role(EVENT_KEY, EventRole.ADMIN_ROLES)
def captain_set_role(request):
    team, year = request.event_team, request.event_year
    torn_id = request.POST.get("torn_id")
    role = request.POST.get("role")
    grant = request.POST.get("grant") == "1"

    if role not in ASSIGNABLE:
        messages.error(request, "That role can't be assigned here.")
        return redirect("captain_dashboard")

    target = get_object_or_404(Profile, torn_id=torn_id)
    on_team = EventParticipation.objects.filter(
        profile=target, event_key=EVENT_KEY, year=year, group_name=team
    ).exists()
    if not on_team:
        messages.error(request, f"{target.name} isn't on your team.")
        return redirect("captain_dashboard")

    if grant:
        EventRole.objects.get_or_create(
            profile=target, event_key=EVENT_KEY, year=year, role=role,
            defaults={"team_name": team, "granted_by": request.event_profile},
        )
        messages.success(request, f"{target.name} is now {role.replace('_', ' ')}.")
    else:
        EventRole.objects.filter(
            profile=target, event_key=EVENT_KEY, year=year, role=role, team_name=team
        ).delete()
        messages.success(request, f"Removed {role.replace('_', ' ')} from {target.name}.")
    return redirect("captain_dashboard")
