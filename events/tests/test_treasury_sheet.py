from datetime import datetime, timezone

from django.test import SimpleTestCase, TestCase
from django.contrib.auth.models import User

from users.models import Profile
from main.models import Item
from events import config
from events.models import EventParticipation, EventRole, TreasuryLedgerEntry
from events.treasury import ledger
from events.treasury.sheet import parse_sheet

YEAR = config.ELIMINATION_YEAR


class SheetParserTests(SimpleTestCase):
    def test_tsv_with_header(self):
        text = "Item\tDonated\tIssued\tCurrent Inventory\nXanax\t1806\t414\t1392\nFirst Aid Kit\t1958\t0\t1958"
        rows, skipped = parse_sheet(text)
        self.assertEqual(rows, [
            {"item_name": "Xanax", "donated": 1806, "issued": 414},
            {"item_name": "First Aid Kit", "donated": 1958, "issued": 0},
        ])

    def test_csv_without_header(self):
        rows, _ = parse_sheet("Xanax,10,2\nMorphine,5,0")
        self.assertEqual(rows[0], {"item_name": "Xanax", "donated": 10, "issued": 2})

    def test_title_and_zero_rows_skipped(self):
        text = ("ELIMINATIONS TEAM — SUPPLIER INVENTORY\n"
                "Item\tDonated\tIssued\n"
                "Xanax\t100\t5\n"
                "Thong\t0\t0\n")
        rows, skipped = parse_sheet(text)
        self.assertEqual([r["item_name"] for r in rows], ["Xanax"])
        # title row, header row, and the all-zero "Thong" row
        self.assertEqual(len(skipped), 3)

    def test_comma_thousands(self):
        rows, _ = parse_sheet("Item,Donated,Issued\nXanax,\"1,806\",414")
        self.assertEqual(rows[0]["donated"], 1806)


def _mk(name, tid, team, roles=()):
    u = User.objects.create(username=str(tid))
    p = u.profile
    p.name = name; p.torn_id = str(tid); p.active_trader = True; p.save()
    EventParticipation.objects.create(profile=p, event_key="elimination", year=YEAR, group_name=team)
    for r in roles:
        EventRole.objects.create(profile=p, event_key="elimination", year=YEAR, team_name=team, role=r)
    return p


class SheetImportExportTests(TestCase):
    def setUp(self):
        self.tr = _mk("Trez", 5551, "Wolves", roles=[EventRole.TREASURER])
        Item.objects.create(
            name="Xanax", description="", requirement="", item_type="Drug", weapon_type=None,
            buy_price=0, sell_price=0, market_value=800000, circulation=1, image_url="",
            TE_value=800000, item_id=206,
        )

    def test_import_creates_in_and_out_baseline(self):
        rows = [{"item_name": "Xanax", "donated": 1806, "issued": 414}]
        batch = ledger.import_sheet_rows(
            rows, team_name="Wolves", event_key="elimination", year=YEAR,
            created_by=self.tr, raw_text="x",
        )
        self.assertEqual(batch.imported_count, 2)
        summary = ledger.item_summary("Wolves", "elimination", YEAR)
        self.assertEqual(summary[0], {
            "item_name": "Xanax", "donated": 1806, "issued": 414, "current": 1392,
            "needs_review": False,
        })

    def test_reimport_replaces_previous_sheet_baseline(self):
        ledger.import_sheet_rows(
            [{"item_name": "Xanax", "donated": 100, "issued": 0}],
            team_name="Wolves", event_key="elimination", year=YEAR,
            created_by=self.tr, raw_text="a",
        )
        ledger.import_sheet_rows(
            [{"item_name": "Xanax", "donated": 250, "issued": 10}],
            team_name="Wolves", event_key="elimination", year=YEAR,
            created_by=self.tr, raw_text="b",
        )
        summary = ledger.item_summary("Wolves", "elimination", YEAR)
        self.assertEqual(summary[0]["donated"], 250)
        self.assertEqual(summary[0]["issued"], 10)

    def test_reimport_keeps_manual_entries(self):
        ledger.add_manual_entry(
            team_name="Wolves", event_key="elimination", year=YEAR, created_by=self.tr,
            direction="in", item_name="Xanax", quantity=50,
            occurred_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
        )
        ledger.import_sheet_rows(
            [{"item_name": "Xanax", "donated": 100, "issued": 0}],
            team_name="Wolves", event_key="elimination", year=YEAR,
            created_by=self.tr, raw_text="a",
        )
        # manual 50 + sheet 100
        self.assertEqual(ledger.item_summary("Wolves", "elimination", YEAR)[0]["donated"], 150)

    def test_export_view_returns_csv(self):
        ledger.import_sheet_rows(
            [{"item_name": "Xanax", "donated": 1806, "issued": 414}],
            team_name="Wolves", event_key="elimination", year=YEAR,
            created_by=self.tr, raw_text="x",
        )
        self.client.force_login(self.tr.user)
        r = self.client.get("/events/elimination/treasury/export.csv")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "text/csv")
        body = r.content.decode()
        self.assertIn("Item,Donated,Issued,Current Inventory", body)
        self.assertIn("Xanax,1806,414,1392", body)

    def test_import_sheet_view_preview_then_confirm(self):
        self.client.force_login(self.tr.user)
        text = "Item\tDonated\tIssued\nXanax\t10\t2"
        r = self.client.post("/events/elimination/treasury/import-sheet",
                             {"raw_text": text, "action": "preview"})
        self.assertContains(r, "Confirm")
        r = self.client.post("/events/elimination/treasury/import-sheet",
                             {"raw_text": text, "action": "confirm"})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(TreasuryLedgerEntry.objects.filter(team_name="Wolves").count(), 2)

    def test_member_cannot_export_or_import_sheet(self):
        member = _mk("Memb", 5552, "Wolves")
        self.client.force_login(member.user)
        self.assertEqual(self.client.get("/events/elimination/treasury/export.csv").status_code, 403)
        self.assertEqual(self.client.get("/events/elimination/treasury/import-sheet").status_code, 403)
