from datetime import datetime, timezone

from django.test import TestCase
from django.contrib.auth.models import User

from users.models import Profile
from main.models import Item
from events import config
from events.models import (
    EventParticipation, EventRole, TreasuryLedgerEntry, TreasuryRequest, TreasuryRequestLine,
)
from events.treasury import ledger
from events.treasury.log_parser import parse_log

YEAR = config.ELIMINATION_YEAR
_TID = [5000]
_IID = [7000]


def mk(name, team=None, roles=()):
    _TID[0] += 1
    u = User.objects.create(username=name)
    p = u.profile
    p.name = name
    p.torn_id = str(_TID[0])
    p.api_key = "k-" + name
    p.active_trader = True
    p.save()
    if team:
        EventParticipation.objects.create(
            profile=p, event_key="elimination", year=YEAR, group_name=team
        )
    for r in roles:
        EventRole.objects.create(
            profile=p, event_key="elimination", year=YEAR, team_name=team, role=r
        )
    return p


def item(name, value=1000):
    _IID[0] += 1
    return Item.objects.create(
        name=name, description="", requirement="", item_type="Drug", weapon_type=None,
        buy_price=0, sell_price=0, market_value=value, circulation=1, image_url="",
        TE_value=value, item_id=_IID[0],
    )


class LedgerBalanceTests(TestCase):
    def setUp(self):
        self.treasurer = mk("tr", "Wolves", roles=[EventRole.TREASURER])
        item("Xanax", 800000)

    def _entry(self, direction, qty, name="Xanax", review=False):
        return ledger.add_manual_entry(
            team_name="Wolves", event_key="elimination", year=YEAR,
            created_by=self.treasurer, direction=direction, item_name=name,
            quantity=qty, occurred_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
        )

    def test_on_hand_nets_in_and_out(self):
        self._entry("in", 100)
        self._entry("out", 30)
        stock, cash = ledger.on_hand("Wolves", "elimination", YEAR)
        self.assertEqual(stock, [{"item_name": "Xanax", "quantity": 70, "needs_review": False}])

    def test_total_value_snapshot(self):
        e = self._entry("in", 10)
        self.assertEqual(e.total_value, 10 * 800000)

    def test_team_isolation(self):
        self._entry("in", 100)
        stock, _ = ledger.on_hand("Bears", "elimination", YEAR)
        self.assertEqual(stock, [])


class LogImportTests(TestCase):
    def setUp(self):
        self.treasurer = mk("tr2", "Wolves", roles=[EventRole.TREASURER])
        item("Xanax", 800000)

    def test_import_then_reimport_dedups(self):
        text = "21:05:02 - 31/08/26 Donor sent 3x Xanax to you"
        rows, skipped = parse_log(text)
        b1 = ledger.import_log_rows(rows, team_name="Wolves", event_key="elimination",
                                    year=YEAR, created_by=self.treasurer, raw_text=text)
        self.assertEqual(b1.imported_count, 1)
        rows, _ = parse_log(text)
        b2 = ledger.import_log_rows(rows, team_name="Wolves", event_key="elimination",
                                   year=YEAR, created_by=self.treasurer, raw_text=text)
        self.assertEqual(b2.imported_count, 0)
        self.assertEqual(TreasuryLedgerEntry.objects.filter(team_name="Wolves").count(), 1)


class RequestFulfilTests(TestCase):
    def setUp(self):
        self.treasurer = mk("trez", "Wolves", roles=[EventRole.TREASURER])
        self.member = mk("memb", "Wolves")
        self.xan = item("Xanax", 800000)
        ledger.add_manual_entry(team_name="Wolves", event_key="elimination", year=YEAR,
                                created_by=self.treasurer, direction="in", item_name="Xanax",
                                quantity=100, occurred_at=datetime(2026, 9, 1, tzinfo=timezone.utc))

    def _make_request(self, qty):
        req = TreasuryRequest.objects.create(
            event_key="elimination", year=YEAR, team_name="Wolves",
            requester=self.member, requester_torn_id=self.member.torn_id,
        )
        line = TreasuryRequestLine.objects.create(
            request=req, item=self.xan, item_name="Xanax", quantity_requested=qty
        )
        return req, line

    def test_fulfil_decrements_on_hand_by_traded_amount(self):
        req, line = self._make_request(10)
        ledger.fulfil_request_line(line, quantity_traded=8, actor=self.treasurer)
        stock, _ = ledger.on_hand("Wolves", "elimination", YEAR)
        self.assertEqual(stock[0]["quantity"], 92)
        line.refresh_from_db(); req.refresh_from_db()
        self.assertEqual(line.quantity_fulfilled, 8)
        self.assertEqual(req.status, TreasuryRequest.PARTIAL)

    def test_full_fulfilment_marks_fulfilled(self):
        req, line = self._make_request(10)
        ledger.fulfil_request_line(line, quantity_traded=10, actor=self.treasurer)
        req.refresh_from_db()
        self.assertEqual(req.status, TreasuryRequest.FULFILLED)


class TreasuryViewTests(TestCase):
    def setUp(self):
        self.treasurer = mk("vtr", "Wolves", roles=[EventRole.TREASURER])
        self.member = mk("vmb", "Wolves")
        self.outsider = mk("vout", "Bears")
        item("Xanax", 800000)
        ledger.add_manual_entry(team_name="Wolves", event_key="elimination", year=YEAR,
                                created_by=self.treasurer, direction="in",
                                counterparty_name="BigDonor", item_name="Xanax", quantity=50,
                                occurred_at=datetime(2026, 9, 1, tzinfo=timezone.utc))

    def login(self, profile):
        self.client.force_login(profile.user)

    def test_treasurer_sees_ledger(self):
        self.login(self.treasurer)
        r = self.client.get("/events/elimination/treasury/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "BigDonor")
        self.assertContains(r, "Ledger")

    def test_member_sees_inventory_not_donors(self):
        self.login(self.member)
        r = self.client.get("/events/elimination/treasury/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Request items")
        self.assertNotContains(r, "BigDonor")
        self.assertNotContains(r, "Ledger")

    def test_outsider_sees_only_own_team(self):
        # A Bears member can open the treasury page, but scoped to Bears -- never
        # Wolves' ledger or donors.
        self.login(self.outsider)
        r = self.client.get("/events/elimination/treasury/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Bears")
        self.assertNotContains(r, "BigDonor")

    def test_non_participant_forbidden(self):
        stranger = mk("nostub")  # no team at all
        self.login(stranger)
        r = self.client.get("/events/elimination/treasury/")
        self.assertEqual(r.status_code, 403)

    def test_member_cannot_import(self):
        self.login(self.member)
        r = self.client.get("/events/elimination/treasury/import")
        self.assertEqual(r.status_code, 403)

    def test_member_creates_request(self):
        self.login(self.member)
        r = self.client.post("/events/elimination/treasury/request", {
            "item_name": ["Xanax"], "quantity": ["10"], "note": "need for war",
        })
        self.assertEqual(r.status_code, 302)
        req = TreasuryRequest.objects.get(requester=self.member)
        self.assertEqual(req.lines.first().quantity_requested, 10)


class CaptainViewTests(TestCase):
    def setUp(self):
        self.captain = mk("cap", "Wolves", roles=[EventRole.CAPTAIN])
        self.member = mk("cmemb", "Wolves")
        self.other_team_member = mk("otm", "Bears")

    def test_captain_grants_treasurer_within_team(self):
        self.client.force_login(self.captain.user)
        r = self.client.post("/events/elimination/captain/role", {
            "torn_id": self.member.torn_id, "role": "treasurer", "grant": "1",
        })
        self.assertEqual(r.status_code, 302)
        self.assertTrue(EventRole.objects.filter(
            profile=self.member, role="treasurer", team_name="Wolves").exists())

    def test_captain_cannot_grant_outside_team(self):
        self.client.force_login(self.captain.user)
        self.client.post("/events/elimination/captain/role", {
            "torn_id": self.other_team_member.torn_id, "role": "treasurer", "grant": "1",
        })
        self.assertFalse(EventRole.objects.filter(profile=self.other_team_member).exists())

    def test_member_cannot_open_captain_dashboard(self):
        self.client.force_login(self.member.user)
        r = self.client.get("/events/elimination/captain/")
        self.assertEqual(r.status_code, 403)
