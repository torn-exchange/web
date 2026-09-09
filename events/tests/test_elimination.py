import json

from django.test import TestCase
from django.contrib.auth.models import User

from users.models import Profile
from main.models import Item, Listing
from events import config
from events.models import EventParticipation, EventTraderSettings
from events.registry import get_event
from events.pricing import event_effective_price, save_trader_event_settings


YEAR = config.ELIMINATION_YEAR


_TORN_ID = [1000]


def make_profile(username, votes=0):
    _TORN_ID[0] += 1
    user = User.objects.create(username=username)
    p = user.profile
    p.name = username
    p.torn_id = str(_TORN_ID[0])
    p.api_key = f"key-{username}"
    p.active_trader = True
    p.save()
    return p


def make_item(item_id=1, te_value=100_000):
    return Item.objects.create(
        name=f"Item {item_id}", description="", requirement="", item_type="Melee",
        weapon_type=None, buy_price=0, sell_price=0, market_value=te_value,
        circulation=1, image_url="", TE_value=te_value, item_id=item_id,
    )


def put_on_team(profile, team, year=YEAR):
    return EventParticipation.objects.create(
        profile=profile, event_key="elimination", year=year, group_name=team
    )


class SyncParticipantTests(TestCase):
    def setUp(self):
        self.p = make_profile("owner")
        self.event = get_event("elimination")

    def test_upserts_team_from_competition(self):
        self.event.sync_participant(self.p, {"competition": {"name": "Elimination", "team": "Wolves", "score": 5}})
        part = EventParticipation.objects.get(profile=self.p, event_key="elimination", year=YEAR)
        self.assertEqual(part.group_name, "Wolves")
        self.assertEqual(part.score, 5)

    def test_unknown_team_stored_blank(self):
        self.event.sync_participant(self.p, {"competition": {"name": "Elimination", "team": "Unknown"}})
        part = EventParticipation.objects.get(profile=self.p)
        self.assertEqual(part.group_name, "")

    def test_ignores_other_competition(self):
        self.event.sync_participant(self.p, {"competition": {"name": "Dog Tags", "team": "x"}})
        self.assertFalse(EventParticipation.objects.filter(profile=self.p).exists())

    def test_no_competition_is_noop(self):
        self.event.sync_participant(self.p, {"last_action": {"status": "Online"}})
        self.assertFalse(EventParticipation.objects.filter(profile=self.p).exists())


class TeamPricingTests(TestCase):
    def setUp(self):
        self.owner = make_profile("seller")
        self.mate = make_profile("mate")
        self.stranger = make_profile("stranger")
        self.item = make_item(item_id=1)
        self.custom_item = make_item(item_id=9001)
        self.listing = Listing.objects.create(owner=self.owner, item=self.item, price=100_000)
        self.custom_listing = Listing.objects.create(owner=self.owner, item=self.custom_item, price=100_000)
        put_on_team(self.owner, "Wolves")
        put_on_team(self.mate, "Wolves")
        put_on_team(self.stranger, "Bears")
        EventTraderSettings.objects.create(
            profile=self.owner, event_key="elimination", year=YEAR, group_discount_pct=10
        )

    def test_teammate_gets_discount(self):
        price, pct, key = event_effective_price(self.listing, self.mate)
        self.assertEqual(pct, 10)
        self.assertEqual(price, 90_000)
        self.assertEqual(key, "elimination")

    def test_non_teammate_unchanged(self):
        price, pct, key = event_effective_price(self.listing, self.stranger)
        self.assertEqual((price, pct, key), (100_000, 0, None))

    def test_anonymous_unchanged(self):
        self.assertEqual(event_effective_price(self.listing, None), (100_000, 0, None))

    def test_custom_item_skipped(self):
        self.assertEqual(event_effective_price(self.custom_listing, self.mate), (100_000, 0, None))

    def test_per_listing_override_wins(self):
        self.listing.event_discount_pct = 25
        self.listing.save()
        price, pct, _ = event_effective_price(self.listing, self.mate)
        self.assertEqual((price, pct), (75_000, 25))

    def test_inactive_event_unchanged(self):
        with self.settings():
            from unittest.mock import patch
            with patch("events.config.ELIMINATION_ENABLED", False):
                self.assertEqual(event_effective_price(self.listing, self.mate), (100_000, 0, None))

    def test_save_trader_event_settings(self):
        save_trader_event_settings(self.owner, {"event_elimination_discount": "15"})
        row = EventTraderSettings.objects.get(profile=self.owner, event_key="elimination", year=YEAR)
        self.assertEqual(row.group_discount_pct, 15)


class ApiTests(TestCase):
    def setUp(self):
        self.owner = make_profile("apiowner")
        self.mate = make_profile("apimate")
        put_on_team(self.owner, "Wolves")
        put_on_team(self.mate, "Wolves")
        make_profile("negvotes")

    def test_profile_endpoint_includes_event(self):
        resp = self.client.get(f"/api/profile?user_id={self.owner.torn_id}&key={self.mate.api_key}")
        body = json.loads(resp.content)
        self.assertEqual(body["data"]["event"]["elimination"]["team"], "Wolves")

    def test_elimination_page_is_public(self):
        from django.core.cache import cache
        cache.clear()
        resp = self.client.get("/events/elimination/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Wolves")

    def test_team_traders_endpoint(self):
        resp = self.client.get(f"/api/team_traders?key={self.mate.api_key}")
        body = json.loads(resp.content)
        self.assertEqual(body["data"]["team"], "Wolves")
        names = [t["name"] for t in body["data"]["traders"]]
        self.assertIn("apiowner", names)
        self.assertIn("apimate", names)
