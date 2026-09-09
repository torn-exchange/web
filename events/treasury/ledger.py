"""Treasury ledger service: item resolution, dedup, balances, request fulfilment."""
from __future__ import annotations

import hashlib
from collections import defaultdict

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from events.models import (
    TreasuryLedgerEntry,
    TreasuryImportBatch,
    TreasuryRequest,
    TreasuryRequestLine,
)


def resolve_item(item_name: str):
    """Return (Item|None, unit_value, needs_review_for_unmatched)."""
    from main.models import Item

    if not item_name or item_name.lower() == "cash":
        return None, 0, False
    item = Item.objects.filter(name__iexact=item_name.strip()).order_by("-last_updated").first()
    if item is None:
        return None, 0, True
    return item, (item.TE_value or 0), False


def _entry_kwargs(row, *, team_name, event_key, year, created_by, source, source_ref=""):
    item, unit_value, unmatched = resolve_item(row["item_name"])
    quantity = row.get("quantity") or 1
    needs_review = bool(row.get("needs_review")) or unmatched
    fingerprint = TreasuryLedgerEntry.make_fingerprint(
        team_name, row["direction"], row["occurred_at"],
        row["counterparty_name"], row["item_name"], quantity,
    )
    return {
        "event_key": event_key,
        "year": year,
        "team_name": team_name,
        "direction": row["direction"],
        "counterparty_name": row.get("counterparty_name", ""),
        "counterparty_torn_id": row.get("counterparty_torn_id", ""),
        "item": item,
        "item_name": row["item_name"],
        "is_cash": bool(row.get("is_cash")),
        "quantity": quantity,
        "unit_value": unit_value,
        "total_value": row.get("total_value"),
        "message": row.get("message", ""),
        "occurred_at": row["occurred_at"],
        "source": source,
        "source_ref": source_ref,
        "line_fingerprint": fingerprint,
        "needs_review": needs_review,
        "created_by": created_by,
    }


@transaction.atomic
def import_log_rows(rows, *, team_name, event_key, year, created_by, raw_text, skipped_count=0):
    """Create ledger entries for parsed log rows, skipping duplicates by fingerprint."""
    raw_hash = hashlib.sha1(raw_text.encode("utf-8")).hexdigest()
    batch = TreasuryImportBatch.objects.create(
        event_key=event_key, year=year, team_name=team_name, created_by=created_by,
        raw_hash=raw_hash, line_count=len(rows) + skipped_count, skipped_count=skipped_count,
    )

    existing = set(
        TreasuryLedgerEntry.objects.filter(
            event_key=event_key, year=year, team_name=team_name
        ).values_list("line_fingerprint", flat=True)
    )
    imported = 0
    seen = set()
    for row in rows:
        kwargs = _entry_kwargs(
            row, team_name=team_name, event_key=event_key, year=year,
            created_by=created_by, source="log_paste", source_ref=str(batch.id),
        )
        fp = kwargs["line_fingerprint"]
        if fp in existing or fp in seen:
            continue
        seen.add(fp)
        entry = TreasuryLedgerEntry(batch=batch, **kwargs)
        entry.save()
        imported += 1

    batch.imported_count = imported
    batch.save(update_fields=["imported_count"])
    return batch


def add_manual_entry(*, team_name, event_key, year, created_by, direction, item_name,
                     quantity, counterparty_name="", counterparty_torn_id="", message="",
                     is_cash=False, total_value=None, occurred_at=None, request=None):
    row = {
        "direction": direction, "counterparty_name": counterparty_name,
        "counterparty_torn_id": counterparty_torn_id, "item_name": item_name,
        "is_cash": is_cash, "quantity": quantity, "total_value": total_value,
        "message": message, "occurred_at": occurred_at or timezone.now(),
        "needs_review": False,
    }
    kwargs = _entry_kwargs(
        row, team_name=team_name, event_key=event_key, year=year,
        created_by=created_by, source="manual",
    )
    entry = TreasuryLedgerEntry(request=request, **kwargs)
    entry.save()
    return entry


def on_hand(team_name, event_key, year):
    """Return a list of {item_name, quantity, needs_review} for current stock."""
    entries = TreasuryLedgerEntry.objects.filter(
        event_key=event_key, year=year, team_name=team_name, is_cash=False
    )
    qty = defaultdict(int)
    flagged = set()
    for e in entries:
        sign = 1 if e.direction == TreasuryLedgerEntry.IN else -1
        key = e.item.name if e.item else e.item_name
        qty[key] += sign * (e.quantity or 0)
        if e.needs_review:
            flagged.add(key)
    rows = [
        {"item_name": name, "quantity": q, "needs_review": name in flagged}
        for name, q in sorted(qty.items())
        if q != 0 or name in flagged
    ]
    cash_in = entries.model.objects.filter(
        event_key=event_key, year=year, team_name=team_name, is_cash=True,
        direction=TreasuryLedgerEntry.IN,
    ).aggregate(s=Sum("total_value"))["s"] or 0
    cash_out = entries.model.objects.filter(
        event_key=event_key, year=year, team_name=team_name, is_cash=True,
        direction=TreasuryLedgerEntry.OUT,
    ).aggregate(s=Sum("total_value"))["s"] or 0
    return rows, (cash_in - cash_out)


def donor_totals(team_name, event_key, year):
    entries = TreasuryLedgerEntry.objects.filter(
        event_key=event_key, year=year, team_name=team_name,
        direction=TreasuryLedgerEntry.IN,
    )
    totals = defaultdict(int)
    for e in entries:
        totals[e.counterparty_name or "(unknown)"] += (e.total_value or 0)
    return sorted(totals.items(), key=lambda kv: -kv[1])


@transaction.atomic
def fulfil_request_line(line: TreasuryRequestLine, *, quantity_traded, actor):
    """Record `quantity_traded` of this line as an OUT entry and update the request."""
    req = line.request
    entry = add_manual_entry(
        team_name=req.team_name, event_key=req.event_key, year=req.year,
        created_by=actor, direction=TreasuryLedgerEntry.OUT,
        item_name=line.item.name if line.item else line.item_name,
        quantity=quantity_traded,
        counterparty_name=req.requester.name,
        counterparty_torn_id=req.requester_torn_id,
        message=f"request #{req.id}", request=req,
    )
    line.quantity_fulfilled += quantity_traded
    line.save(update_fields=["quantity_fulfilled"])
    req.resolved_by = actor
    req.recompute_status()
    req.save(update_fields=["status", "resolved_by", "updated_at"])
    return entry
