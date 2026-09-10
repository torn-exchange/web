"""Parse pasted Torn item-log lines into treasury ledger rows.

Supported line shapes (all prefixed ``HH:MM:SS - DD/MM/YY``)::

    SirIcyDragon sent 3x Xanax to you
    CharmRiver sent a Shaped Charge to you with the message: For upcoming OC
    You sent some Xanax to MegaGodzilla
    You sent 50x Bottle of Kandy Kane to SokolM with the message: ...
    SomeGuy sent you $1,000,000
    You sent $500,000 to SomeGuy

Unrecognised lines are returned in ``skipped`` (never dropped silently).
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

PREFIX_RE = re.compile(
    r"^(?P<time>\d{2}:\d{2}:\d{2})\s*-\s*(?P<date>\d{2}/\d{2}/\d{2})\s+(?P<body>.+?)\s*$"
)
MESSAGE_RE = re.compile(r"\s+with the message:\s*(?P<msg>.*)$", re.DOTALL)

# body patterns -> (direction, who_group, payload_group)
BODY_PATTERNS = [
    ("out", re.compile(r"^You sent \$(?P<amt>[\d,]+) to (?P<who>.+)$"), "cash"),
    ("in", re.compile(r"^(?P<who>.+?) sent you \$(?P<amt>[\d,]+)$"), "cash"),
    ("out", re.compile(r"^You sent (?P<payload>.+?) to (?P<who>.+)$"), "item"),
    ("in", re.compile(r"^(?P<who>.+?) sent (?P<payload>.+?) to you$"), "item"),
    ("in", re.compile(r"^(?P<who>.+?) sent you (?P<payload>.+)$"), "item"),
]

QTY_NUM_RE = re.compile(r"^(?P<n>\d[\d,]*)\s*x?\s+(?P<item>.+)$", re.IGNORECASE)
QTY_WORD_RE = re.compile(r"^(?P<w>an?|some)\s+(?P<item>.+)$", re.IGNORECASE)


def _parse_dt(date_s: str, time_s: str):
    dd, mm, yy = (int(x) for x in date_s.split("/"))
    hh, mi, ss = (int(x) for x in time_s.split(":"))
    return datetime(2000 + yy, mm, dd, hh, mi, ss, tzinfo=timezone.utc)


def _parse_payload(payload: str):
    """Return (quantity, item_name, needs_review)."""
    payload = payload.strip()
    m = QTY_NUM_RE.match(payload)
    if m:
        return int(m.group("n").replace(",", "")), m.group("item").strip(), False
    m = QTY_WORD_RE.match(payload)
    if m:
        word = m.group("w").lower()
        return 1, m.group("item").strip(), (word == "some")
    # no recognisable quantity marker -> assume 1, flag it
    return 1, payload, True


def parse_log(text: str):
    """Parse the whole paste. Returns ``(rows, skipped)``.

    ``rows`` are dicts: direction, counterparty_name, item_name, is_cash,
    quantity, total_value (cash only), message, occurred_at, needs_review, raw.
    """
    rows, skipped = [], []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        pm = PREFIX_RE.match(line)
        if not pm:
            skipped.append(raw)
            continue

        body = pm.group("body")
        message = ""
        mm = MESSAGE_RE.search(body)
        if mm:
            message = mm.group("msg").strip()
            body = body[: mm.start()].strip()

        occurred_at = _parse_dt(pm.group("date"), pm.group("time"))

        matched = False
        for direction, pattern, kind in BODY_PATTERNS:
            bm = pattern.match(body)
            if not bm:
                continue
            matched = True
            who = bm.group("who").strip()
            if kind == "cash":
                amount = int(bm.group("amt").replace(",", ""))
                rows.append({
                    "direction": direction, "counterparty_name": who,
                    "item_name": "Cash", "is_cash": True, "quantity": 1,
                    "total_value": amount, "message": message,
                    "occurred_at": occurred_at, "needs_review": False, "raw": raw,
                })
            else:
                qty, item_name, needs_review = _parse_payload(bm.group("payload"))
                rows.append({
                    "direction": direction, "counterparty_name": who,
                    "item_name": item_name, "is_cash": False, "quantity": qty,
                    "total_value": None, "message": message,
                    "occurred_at": occurred_at, "needs_review": needs_review, "raw": raw,
                })
            break

        if not matched:
            skipped.append(raw)

    return rows, skipped
