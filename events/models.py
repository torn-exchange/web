import hashlib

from django.db import models

from users.models import Profile


class EventParticipation(models.Model):
    """A single profile's standing in one event, for one year.

    ``event_key`` is the event slug (e.g. ``"elimination"``). ``group_name`` is
    the team/faction name for group events, blank for solo events or before a
    team has been assigned. ``data`` keeps the raw event payload for
    forward-compatibility.
    """

    profile = models.ForeignKey(
        Profile, on_delete=models.CASCADE, related_name="event_participations"
    )
    event_key = models.CharField(max_length=40)
    year = models.IntegerField()
    group_name = models.CharField(max_length=100, blank=True, default="")
    position = models.IntegerField(null=True, blank=True)
    score = models.BigIntegerField(null=True, blank=True)
    status = models.CharField(max_length=50, blank=True, default="")
    data = models.JSONField(default=dict, blank=True)
    # Phase 2: link to the team's official Torn announcement, supplied by a
    # would-be captain and checked by a site admin before granting the role.
    captain_proof_url = models.URLField(blank=True, default="")
    synced_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("profile", "event_key", "year")
        indexes = [models.Index(fields=["event_key", "year", "group_name"])]

    def __str__(self):
        return f"{self.profile.name} - {self.event_key} {self.year} ({self.group_name or 'no team'})"


class EventGroupStanding(models.Model):
    """A team/faction row in an event leaderboard, for one year."""

    event_key = models.CharField(max_length=40)
    year = models.IntegerField()
    group_name = models.CharField(max_length=100)
    group_key = models.CharField(max_length=100, blank=True, default="")
    position = models.IntegerField(null=True, blank=True)
    score = models.BigIntegerField(null=True, blank=True)
    lives = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=50, blank=True, default="")
    data = models.JSONField(default=dict, blank=True)
    synced_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("event_key", "year", "group_name")
        ordering = ["position", "-score"]

    def __str__(self):
        return f"{self.event_key} {self.year}: {self.group_name} (#{self.position})"


class EventTraderSettings(models.Model):
    """Per-trader, per-event preferences. Deliberately separate from
    ``users.Settings`` so event churn never touches core models."""

    profile = models.ForeignKey(
        Profile, on_delete=models.CASCADE, related_name="event_trader_settings"
    )
    event_key = models.CharField(max_length=40)
    year = models.IntegerField()
    group_discount_pct = models.IntegerField(default=0)
    data = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = ("profile", "event_key", "year")

    def __str__(self):
        return f"{self.profile.name} - {self.event_key} {self.year}: -{self.group_discount_pct}%"


# ---------------------------------------------------------------------------
# Phase 2 — team treasury
# ---------------------------------------------------------------------------

class EventRole(models.Model):
    """A player's role on a team for one event year.

    ``captain`` is granted by a site admin (after checking
    ``EventParticipation.captain_proof_url``); the captain grants the rest.
    ``member`` is implicit for anyone with a matching ``EventParticipation`` and
    is not usually stored as a row -- see ``events.roles``.
    """

    CAPTAIN = "captain"
    VICE_CAPTAIN = "vice_captain"
    TREASURER = "treasurer"
    TEAM_TRADER = "team_trader"
    MEMBER = "member"
    ROLE_CHOICES = [
        (CAPTAIN, "Captain"),
        (VICE_CAPTAIN, "Vice-captain"),
        (TREASURER, "Treasurer"),
        (TEAM_TRADER, "Team trader"),
        (MEMBER, "Member"),
    ]
    #: roles allowed to see/write the treasury ledger
    TREASURY_ROLES = {CAPTAIN, VICE_CAPTAIN, TREASURER}
    #: roles allowed to assign other roles
    ADMIN_ROLES = {CAPTAIN, VICE_CAPTAIN}

    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="event_roles")
    event_key = models.CharField(max_length=40)
    year = models.IntegerField()
    team_name = models.CharField(max_length=100)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    granted_by = models.ForeignKey(
        Profile, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    granted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("profile", "event_key", "year", "role")
        indexes = [models.Index(fields=["event_key", "year", "team_name", "role"])]

    def __str__(self):
        return f"{self.profile.name} = {self.role} ({self.team_name} {self.event_key} {self.year})"


class TreasuryLedgerEntry(models.Model):
    IN = "in"
    OUT = "out"
    DIRECTIONS = [(IN, "Donation in"), (OUT, "Payout out")]

    SOURCE_CHOICES = [
        ("helper_trade", "TE Helper trade"),
        ("log_paste", "Torn log paste"),
        ("manual", "Manual entry"),
    ]

    event_key = models.CharField(max_length=40)
    year = models.IntegerField()
    team_name = models.CharField(max_length=100)
    direction = models.CharField(max_length=3, choices=DIRECTIONS)

    counterparty_name = models.CharField(max_length=100, blank=True, default="")
    counterparty_torn_id = models.CharField(max_length=20, blank=True, default="")

    item = models.ForeignKey("main.Item", on_delete=models.SET_NULL, null=True, blank=True)
    item_name = models.CharField(max_length=200, blank=True, default="")
    is_cash = models.BooleanField(default=False)
    quantity = models.IntegerField(default=1)
    unit_value = models.BigIntegerField(default=0)
    total_value = models.BigIntegerField(null=True, blank=True)

    message = models.TextField(blank=True, default="")
    occurred_at = models.DateTimeField()
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default="manual")
    source_ref = models.CharField(max_length=64, blank=True, default="")
    batch = models.ForeignKey(
        "events.TreasuryImportBatch", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="entries",
    )
    request = models.ForeignKey(
        "events.TreasuryRequest", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="ledger_entries",
    )
    line_fingerprint = models.CharField(max_length=40, blank=True, default="")
    needs_review = models.BooleanField(default=False)

    created_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["event_key", "year", "team_name"]),
            models.Index(fields=["team_name", "direction"]),
            models.Index(fields=["team_name", "counterparty_name"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["event_key", "year", "line_fingerprint"],
                condition=models.Q(line_fingerprint__gt=""),
                name="uniq_treasury_line_fingerprint",
            )
        ]

    @staticmethod
    def make_fingerprint(team_name, direction, occurred_at, counterparty, item_name, quantity):
        raw = "|".join([
            str(team_name), str(direction), str(occurred_at), str(counterparty or "").lower(),
            str(item_name or "").lower(), str(quantity),
        ])
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()

    def recompute_total(self):
        if self.is_cash:
            return
        self.total_value = (self.quantity or 0) * (self.unit_value or 0)

    def save(self, *args, **kwargs):
        if not self.is_cash and self.total_value is None:
            self.recompute_total()
        super().save(*args, **kwargs)

    def __str__(self):
        label = "cash" if self.is_cash else f"{self.quantity}x {self.item_name}"
        return f"{self.team_name} {self.direction} {label} ({self.counterparty_name})"


class TreasuryImportBatch(models.Model):
    event_key = models.CharField(max_length=40)
    year = models.IntegerField()
    team_name = models.CharField(max_length=100)
    created_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, related_name="+")
    raw_hash = models.CharField(max_length=40)
    line_count = models.IntegerField(default=0)
    imported_count = models.IntegerField(default=0)
    skipped_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["event_key", "year", "team_name"])]

    def __str__(self):
        return f"Import {self.team_name} {self.created_at:%Y-%m-%d} (+{self.imported_count})"


class TreasuryRequest(models.Model):
    OPEN = "open"
    PARTIAL = "partial"
    FULFILLED = "fulfilled"
    DECLINED = "declined"
    CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (OPEN, "Open"), (PARTIAL, "Partially fulfilled"), (FULFILLED, "Fulfilled"),
        (DECLINED, "Declined"), (CANCELLED, "Cancelled"),
    ]
    OPEN_STATUSES = {OPEN, PARTIAL}

    event_key = models.CharField(max_length=40)
    year = models.IntegerField()
    team_name = models.CharField(max_length=100)
    requester = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="treasury_requests")
    requester_torn_id = models.CharField(max_length=20, blank=True, default="")
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=OPEN)
    note = models.TextField(blank=True, default="")
    resolved_by = models.ForeignKey(
        Profile, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["event_key", "year", "team_name", "status"])]
        ordering = ["-created_at"]

    def recompute_status(self):
        if self.status in (self.DECLINED, self.CANCELLED):
            return
        lines = list(self.lines.all())
        if lines and all(line.quantity_fulfilled >= line.quantity_requested for line in lines):
            self.status = self.FULFILLED
        elif any(line.quantity_fulfilled > 0 for line in lines):
            self.status = self.PARTIAL
        else:
            self.status = self.OPEN

    def __str__(self):
        return f"Request #{self.pk} by {self.requester.name} ({self.team_name}) - {self.status}"


class TreasuryRequestLine(models.Model):
    request = models.ForeignKey(TreasuryRequest, on_delete=models.CASCADE, related_name="lines")
    item = models.ForeignKey("main.Item", on_delete=models.SET_NULL, null=True, blank=True)
    item_name = models.CharField(max_length=200)
    quantity_requested = models.IntegerField(default=1)
    quantity_fulfilled = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.quantity_fulfilled}/{self.quantity_requested} {self.item_name}"
