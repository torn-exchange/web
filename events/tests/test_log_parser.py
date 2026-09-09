from django.test import SimpleTestCase

from events.treasury.log_parser import parse_log


class LogParserTests(SimpleTestCase):
    def parse_one(self, line):
        rows, skipped = parse_log(line)
        return rows[0] if rows else None, skipped

    def test_inbound_quantity(self):
        row, _ = self.parse_one("21:05:02 - 31/08/26 SirIcyDragon sent 3x Xanax to you")
        self.assertEqual(row["direction"], "in")
        self.assertEqual(row["counterparty_name"], "SirIcyDragon")
        self.assertEqual((row["quantity"], row["item_name"]), (3, "Xanax"))
        self.assertFalse(row["needs_review"])

    def test_inbound_single_with_message(self):
        row, _ = self.parse_one(
            "04:11:50 - 22/06/26 CharmRiver sent a Shaped Charge to you with the message: For upcoming OC"
        )
        self.assertEqual((row["quantity"], row["item_name"]), (1, "Shaped Charge"))
        self.assertEqual(row["message"], "For upcoming OC")

    def test_outbound_some_defaults_to_one_and_flags(self):
        row, _ = self.parse_one("23:58:41 - 19/08/26 You sent some Xanax to MegaGodzilla")
        self.assertEqual(row["direction"], "out")
        self.assertEqual((row["quantity"], row["item_name"]), (1, "Xanax"))
        self.assertTrue(row["needs_review"])

    def test_outbound_quantity_multiword_item(self):
        row, _ = self.parse_one(
            "20:02:29 - 20/04/26 You sent 50x Bottle of Kandy Kane to SokolM with the message: gl"
        )
        self.assertEqual((row["quantity"], row["item_name"]), (50, "Bottle of Kandy Kane"))
        self.assertEqual(row["counterparty_name"], "SokolM")

    def test_cash(self):
        row, _ = self.parse_one("10:00:00 - 01/01/26 RichGuy sent you $1,000,000")
        self.assertTrue(row["is_cash"])
        self.assertEqual(row["total_value"], 1_000_000)
        self.assertEqual(row["direction"], "in")

    def test_unrecognised_line_is_skipped_not_dropped(self):
        rows, skipped = parse_log("not a log line at all\n10:00:00 - 01/01/26 blah blah")
        self.assertEqual(rows, [])
        self.assertEqual(len(skipped), 2)

    def test_all_four_examples(self):
        text = """21:05:02 - 31/08/26 SirIcyDragon sent 3x Xanax to you
04:11:50 - 22/06/26 CharmRiver sent a Shaped Charge to you with the message: For upcoming OC
23:58:41 - 19/08/26 You sent some Xanax to MegaGodzilla
20:02:29 - 20/04/26 You sent 50x Bottle of Kandy Kane to SokolM with the message: x"""
        rows, skipped = parse_log(text)
        self.assertEqual(len(rows), 4)
        self.assertEqual(len(skipped), 0)
        self.assertEqual([r["direction"] for r in rows], ["in", "in", "out", "out"])
        self.assertEqual(sum(r["needs_review"] for r in rows), 1)
