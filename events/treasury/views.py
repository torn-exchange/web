from django.contrib import messages
from django.db import transaction
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from events.models import (
    EventRole,
    TreasuryLedgerEntry,
    TreasuryRequest,
    TreasuryRequestLine,
)
from events.roles import require_event_role
from events.treasury import ledger
from events.treasury.log_parser import parse_log

EVENT_KEY = "elimination"


def _is_treasurer(request):
    return bool(request.event_roles & EventRole.TREASURY_ROLES)


@require_event_role(EVENT_KEY, EventRole.TREASURY_ROLES | {EventRole.MEMBER})
def treasury_home(request):
    team = request.event_team
    year = request.event_year
    stock, cash = ledger.on_hand(team, EVENT_KEY, year)

    my_open_request = (
        TreasuryRequest.objects.filter(
            event_key=EVENT_KEY, year=year, team_name=team, requester=request.event_profile,
            status__in=TreasuryRequest.OPEN_STATUSES,
        )
        .prefetch_related("lines")
        .first()
    )

    ctx = {
        "page_title": f"{request.event.label} treasury - Torn Exchange",
        "team": team,
        "is_treasurer": _is_treasurer(request),
        "stock": stock,
        "cash": cash,
        "my_open_request": my_open_request,
        "my_requests": TreasuryRequest.objects.filter(
            event_key=EVENT_KEY, year=year, team_name=team, requester=request.event_profile,
        ).prefetch_related("lines")[:10],
    }

    if _is_treasurer(request):
        ctx["entries"] = TreasuryLedgerEntry.objects.filter(
            event_key=EVENT_KEY, year=year, team_name=team
        ).select_related("item", "created_by").order_by("-occurred_at")[:200]
        ctx["donor_totals"] = ledger.donor_totals(team, EVENT_KEY, year)
        ctx["open_requests"] = (
            TreasuryRequest.objects.filter(
                event_key=EVENT_KEY, year=year, team_name=team,
                status__in=TreasuryRequest.OPEN_STATUSES,
            )
            .select_related("requester")
            .prefetch_related("lines")
        )
        ctx["totals"] = {
            "donated": sum(
                e.total_value or 0
                for e in ctx["entries"] if e.direction == TreasuryLedgerEntry.IN
            ),
            "distributed": sum(
                e.total_value or 0
                for e in ctx["entries"] if e.direction == TreasuryLedgerEntry.OUT
            ),
        }
    return render(request, "events/treasury/dashboard.html", ctx)


@require_event_role(EVENT_KEY, EventRole.TREASURY_ROLES)
def treasury_import(request):
    if request.method == "POST":
        raw_text = request.POST.get("raw_text", "")
        rows, skipped = parse_log(raw_text)
        if request.POST.get("action") == "confirm":
            batch = ledger.import_log_rows(
                rows, team_name=request.event_team, event_key=EVENT_KEY,
                year=request.event_year, created_by=request.event_profile,
                raw_text=raw_text, skipped_count=len(skipped),
            )
            messages.success(
                request,
                f"Imported {batch.imported_count} entries "
                f"({len(rows) - batch.imported_count} duplicates, {len(skipped)} unrecognised).",
            )
            return redirect("treasury_home")
        return render(request, "events/treasury/import.html", {
            "page_title": "Import Torn log - Torn Exchange",
            "raw_text": raw_text, "rows": rows, "skipped": skipped, "previewed": True,
        })
    return render(request, "events/treasury/import.html", {
        "page_title": "Import Torn log - Torn Exchange", "raw_text": "", "previewed": False,
    })


@require_POST
@require_event_role(EVENT_KEY, EventRole.TREASURY_ROLES)
def treasury_add_entry(request):
    try:
        qty = max(1, int(request.POST.get("quantity") or 1))
    except ValueError:
        qty = 1
    ledger.add_manual_entry(
        team_name=request.event_team, event_key=EVENT_KEY, year=request.event_year,
        created_by=request.event_profile,
        direction=request.POST.get("direction", TreasuryLedgerEntry.IN),
        item_name=(request.POST.get("item_name") or "").strip(),
        quantity=qty,
        counterparty_name=(request.POST.get("counterparty_name") or "").strip(),
        message=(request.POST.get("message") or "").strip(),
        occurred_at=timezone.now(),
    )
    messages.success(request, "Entry added.")
    return redirect("treasury_home")


@require_POST
@require_event_role(EVENT_KEY, EventRole.TREASURY_ROLES)
def treasury_delete_entry(request, entry_id):
    entry = get_object_or_404(
        TreasuryLedgerEntry, id=entry_id, team_name=request.event_team, event_key=EVENT_KEY
    )
    entry.delete()
    messages.success(request, "Entry deleted.")
    return redirect("treasury_home")


@require_POST
@require_event_role(EVENT_KEY, {EventRole.MEMBER})
def treasury_request_create(request):
    team, year = request.event_team, request.event_year
    # one open request per member
    existing = TreasuryRequest.objects.filter(
        event_key=EVENT_KEY, year=year, team_name=team, requester=request.event_profile,
        status__in=TreasuryRequest.OPEN_STATUSES,
    ).first()
    req = existing or TreasuryRequest(
        event_key=EVENT_KEY, year=year, team_name=team,
        requester=request.event_profile,
        requester_torn_id=request.event_profile.torn_id or "",
    )
    req.note = (request.POST.get("note") or "").strip()
    req.save()
    req.lines.all().delete()

    names = request.POST.getlist("item_name")
    qtys = request.POST.getlist("quantity")
    from main.models import Item
    for name, qty in zip(names, qtys):
        name = (name or "").strip()
        if not name:
            continue
        try:
            qty = max(1, int(qty))
        except (ValueError, TypeError):
            qty = 1
        item = Item.objects.filter(name__iexact=name).first()
        TreasuryRequestLine.objects.create(
            request=req, item=item, item_name=name, quantity_requested=qty
        )
    if not req.lines.exists():
        req.delete()
        messages.error(request, "Add at least one item to your request.")
    else:
        req.recompute_status()
        req.save(update_fields=["status"])
        messages.success(request, "Request submitted to your treasurer.")
    return redirect("treasury_home")


@require_POST
@require_event_role(EVENT_KEY, {EventRole.MEMBER})
def treasury_request_cancel(request, request_id):
    req = get_object_or_404(
        TreasuryRequest, id=request_id, requester=request.event_profile,
        team_name=request.event_team,
    )
    req.status = TreasuryRequest.CANCELLED
    req.save(update_fields=["status", "updated_at"])
    messages.success(request, "Request cancelled.")
    return redirect("treasury_home")


@require_POST
@require_event_role(EVENT_KEY, EventRole.TREASURY_ROLES)
def treasury_fulfil_line(request, line_id):
    line = get_object_or_404(
        TreasuryRequestLine, id=line_id, request__team_name=request.event_team,
        request__event_key=EVENT_KEY,
    )
    try:
        traded = int(request.POST.get("quantity_traded") or 0)
    except ValueError:
        traded = 0
    if traded <= 0:
        messages.error(request, "Enter a quantity greater than zero.")
        return redirect("treasury_home")
    ledger.fulfil_request_line(line, quantity_traded=traded, actor=request.event_profile)
    messages.success(request, f"Recorded {traded}x {line.item_name} to {line.request.requester.name}.")
    return redirect("treasury_home")


@require_POST
@require_event_role(EVENT_KEY, EventRole.TREASURY_ROLES)
def treasury_decline_request(request, request_id):
    req = get_object_or_404(
        TreasuryRequest, id=request_id, team_name=request.event_team, event_key=EVENT_KEY
    )
    req.status = TreasuryRequest.DECLINED
    req.resolved_by = request.event_profile
    req.save(update_fields=["status", "resolved_by", "updated_at"])
    messages.success(request, "Request declined.")
    return redirect("treasury_home")
