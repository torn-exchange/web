"""Static configuration for Torn events.

Each event's ``is_active`` / ``current_year`` reads from here. Keeping it in one
module (rather than scattered constants or new DB columns) means switching an
event on/off between years is a one-line change, and a future ``EventConfig``
DB model could replace this without touching any caller.
"""

# --- Elimination -----------------------------------------------------------
# Torn's yearly team competition. Runs September 2026 (12 teams).
ELIMINATION_ENABLED = True
ELIMINATION_YEAR = 2026
