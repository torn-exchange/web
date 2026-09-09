from django.contrib import admin, messages

from events.models import (
    EventParticipation,
    EventGroupStanding,
    EventTraderSettings,
    EventRole,
    TreasuryLedgerEntry,
    TreasuryImportBatch,
    TreasuryRequest,
    TreasuryRequestLine,
)


@admin.register(EventParticipation)
class EventParticipationAdmin(admin.ModelAdmin):
    list_display = ("profile", "event_key", "year", "group_name", "position", "score", "captain_proof_url", "synced_at")
    list_filter = ("event_key", "year", "group_name")
    search_fields = ("profile__name", "profile__torn_id", "group_name")
    raw_id_fields = ("profile",)
    actions = ("grant_captain",)

    @admin.action(description="Grant Captain role (verify captain_proof_url first)")
    def grant_captain(self, request, queryset):
        granted = 0
        for part in queryset:
            if not part.group_name:
                self.message_user(request, f"{part.profile.name}: no team, skipped", messages.WARNING)
                continue
            _, created = EventRole.objects.get_or_create(
                profile=part.profile, event_key=part.event_key, year=part.year,
                role=EventRole.CAPTAIN,
                defaults={"team_name": part.group_name},
            )
            granted += int(created)
        self.message_user(request, f"Granted Captain to {granted} player(s).")


@admin.register(EventGroupStanding)
class EventGroupStandingAdmin(admin.ModelAdmin):
    list_display = ("event_key", "year", "group_name", "position", "score", "lives", "status", "synced_at")
    list_filter = ("event_key", "year")


@admin.register(EventTraderSettings)
class EventTraderSettingsAdmin(admin.ModelAdmin):
    list_display = ("profile", "event_key", "year", "group_discount_pct")
    list_filter = ("event_key", "year")
    search_fields = ("profile__name", "profile__torn_id")
    raw_id_fields = ("profile",)


@admin.register(EventRole)
class EventRoleAdmin(admin.ModelAdmin):
    list_display = ("profile", "role", "team_name", "event_key", "year", "granted_by", "granted_at")
    list_filter = ("event_key", "year", "role", "team_name")
    search_fields = ("profile__name", "profile__torn_id", "team_name")
    raw_id_fields = ("profile", "granted_by")


class TreasuryRequestLineInline(admin.TabularInline):
    model = TreasuryRequestLine
    extra = 0


@admin.register(TreasuryLedgerEntry)
class TreasuryLedgerEntryAdmin(admin.ModelAdmin):
    list_display = ("team_name", "direction", "item_name", "quantity", "counterparty_name",
                    "total_value", "occurred_at", "source", "needs_review")
    list_filter = ("event_key", "year", "team_name", "direction", "source", "needs_review")
    search_fields = ("counterparty_name", "item_name")
    raw_id_fields = ("item", "created_by", "batch", "request")


@admin.register(TreasuryImportBatch)
class TreasuryImportBatchAdmin(admin.ModelAdmin):
    list_display = ("team_name", "event_key", "year", "created_by", "imported_count",
                    "skipped_count", "created_at")
    list_filter = ("event_key", "year", "team_name")


@admin.register(TreasuryRequest)
class TreasuryRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "team_name", "requester", "status", "created_at", "updated_at")
    list_filter = ("event_key", "year", "team_name", "status")
    search_fields = ("requester__name",)
    inlines = (TreasuryRequestLineInline,)
