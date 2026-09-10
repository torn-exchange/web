"""Parse a pasted / uploaded team supplier sheet into summary rows.

Accepts CSV or TSV (Google Sheets / Excel copy-paste is tab-separated;
"Download as CSV" is comma-separated). Expected columns, in any order, matched
by header name (case-insensitive):

    Item | Donated | Issued | Current Inventory (optional, ignored)

If no recognisable header row is present, the first three columns are taken as
Item, Donated, Issued.
"""
from __future__ import annotations

import csv
import io

_ITEM_KEYS = {"item", "name", "item name"}
_DONATED_KEYS = {"donated", "in", "received", "donations"}
_ISSUED_KEYS = {"issued", "out", "sent", "distributed", "given"}


def _sniff_rows(text: str):
    text = text.strip("﻿\n\r ")
    if not text:
        return []
    delimiter = "\t" if text.count("\t") >= text.count(",") else ","
    return [r for r in csv.reader(io.StringIO(text), delimiter=delimiter) if any(c.strip() for c in r)]


def _to_int(value) -> int:
    try:
        return max(0, int(str(value).strip().replace(",", "") or 0))
    except (TypeError, ValueError):
        return 0


def parse_sheet(text: str):
    """Return ``(rows, skipped)``.

    ``rows``: ``[{"item_name", "donated", "issued"}]``.
    ``skipped``: raw rows that had no item name or no numbers.
    """
    raw_rows = _sniff_rows(text)
    if not raw_rows:
        return [], []

    header = [c.strip().lower() for c in raw_rows[0]]
    has_header = any(h in _ITEM_KEYS for h in header)

    if has_header:
        idx_item = next((i for i, h in enumerate(header) if h in _ITEM_KEYS), 0)
        idx_don = next((i for i, h in enumerate(header) if h in _DONATED_KEYS), 1)
        idx_iss = next((i for i, h in enumerate(header) if h in _ISSUED_KEYS), 2)
        body = raw_rows[1:]
    else:
        idx_item, idx_don, idx_iss = 0, 1, 2
        body = raw_rows

    rows, skipped = [], []
    for raw in body:
        name = (raw[idx_item].strip() if idx_item < len(raw) else "")
        # skip section headers / totals rows
        if not name or name.lower().startswith(("elimination", "total", "supplier inventory")):
            skipped.append(raw)
            continue
        donated = _to_int(raw[idx_don]) if idx_don < len(raw) else 0
        issued = _to_int(raw[idx_iss]) if idx_iss < len(raw) else 0
        if donated == 0 and issued == 0:
            skipped.append(raw)
            continue
        rows.append({"item_name": name, "donated": donated, "issued": issued})
    return rows, skipped
