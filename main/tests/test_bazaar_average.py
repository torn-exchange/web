import json
from unittest.mock import patch, Mock
from django.test import TestCase

from main.management.commands.update_items_fast import get_lowest_market_price, weighted_itemmarket_price
from main.services.api.weav3r.marketplace_api_service import Weav3rMarketplaceApiService


def make_itemmarket_response(listing_prices=None, listings=None):
    # listing_prices: shorthand for a flat list of prices, each treated as
    # amount=1 (uniform weighting) -- listings: full [{"price", "amount"}, ...]
    # for tests that need to control quantities directly.
    if listings is None:
        listings = [{"price": p, "amount": 1} for p in listing_prices]
    return Mock(content=json.dumps({"itemmarket": {"listings": listings}}).encode())


# ---------------------------------------------------------------------------
# get_lowest_market_price() — 3-source min (Torn market_value, itemmarket, bazaar_average)
# ---------------------------------------------------------------------------

class GetLowestMarketPriceBazaarAverageTests(TestCase):

    @patch('main.management.commands.update_items_fast.requests.get')
    def test_bazaar_average_lowers_te_value(self, mock_get):
        # itemmarket listings average to 100, avg_market_price=90, bazaar_average=80 -> 80 wins
        mock_get.return_value = make_itemmarket_response([100, 100, 100])
        result = get_lowest_market_price('1', 'key', avg_market_price=90, bazaar_average=80)
        self.assertEqual(result, 80)

    @patch('main.management.commands.update_items_fast.requests.get')
    def test_bazaar_average_ignored_when_higher(self, mock_get):
        # bazaar_average is the highest of the three -> doesn't change the result
        mock_get.return_value = make_itemmarket_response([100, 100, 100])
        result = get_lowest_market_price('1', 'key', avg_market_price=90, bazaar_average=200)
        self.assertEqual(result, 90)

    @patch('main.management.commands.update_items_fast.requests.get')
    def test_bazaar_average_none_falls_back_to_two_source(self, mock_get):
        # No bazaar_average available for this item -> identical to pre-task 2-source behaviour
        mock_get.return_value = make_itemmarket_response([100, 100, 100])
        result = get_lowest_market_price('1', 'key', avg_market_price=90, bazaar_average=None)
        self.assertEqual(result, 90)

    @patch('main.management.commands.update_items_fast.requests.get')
    def test_bazaar_average_zero_is_ignored(self, mock_get):
        # A falsy/zero bazaar_average must not win over real prices
        mock_get.return_value = make_itemmarket_response([100, 100, 100])
        result = get_lowest_market_price('1', 'key', avg_market_price=90, bazaar_average=0)
        self.assertEqual(result, 90)

    @patch('main.management.commands.update_items_fast.requests.get')
    def test_single_lowball_itemmarket_listing_no_longer_craters_te_price(self, mock_get):
        # Regression test for the "prices dropping suddenly" reports: a lone
        # 1-unit troll listing at price 1 used to dominate a flat top-3 mean
        # and crash TE_value; it must no longer win over real prices.
        mock_get.return_value = make_itemmarket_response(
            listings=[{"price": 1, "amount": 1}] + [{"price": 1000, "amount": 10}] * 9
        )
        result = get_lowest_market_price('1', 'key', avg_market_price=1050, bazaar_average=None)
        self.assertGreater(result, 990)


# ---------------------------------------------------------------------------
# weighted_itemmarket_price() — drop the cheapest listing, then a
# quantity-weighted average of the rest, over the first 10 listings
# ---------------------------------------------------------------------------

class WeightedItemmarketPriceTests(TestCase):

    def test_drops_cheapest_listing_before_averaging(self):
        # cheapest (1@1) is dropped entirely; remaining are equal price/amount
        listings = [{"price": 1, "amount": 1}] + [{"price": 100, "amount": 10}] * 9
        self.assertEqual(weighted_itemmarket_price(listings), 100)

    def test_low_quantity_outlier_barely_moves_weighted_average(self):
        # A 1-unit troll listing at price 1 sitting among 9 real listings at
        # 1000 (10 units each) should barely move the average, unlike a flat
        # mean which would be dragged down proportionally to 1/9th.
        listings = [{"price": 1, "amount": 1}] + [{"price": 1000, "amount": 10}] * 9
        result = weighted_itemmarket_price(listings)
        self.assertGreater(result, 990)

    def test_only_considers_first_ten_listings(self):
        # An 11th, cheaper listing outside the window must not affect the result
        listings = [{"price": 100, "amount": 10}] * 10 + [{"price": 1, "amount": 1000}]
        self.assertEqual(weighted_itemmarket_price(listings), 100)

    def test_single_listing_has_nothing_to_drop_against(self):
        listings = [{"price": 500, "amount": 1}]
        self.assertEqual(weighted_itemmarket_price(listings), 500)

    def test_missing_amount_defaults_to_uniform_weighting(self):
        listings = [{"price": 1}, {"price": 100}, {"price": 100}]
        self.assertEqual(weighted_itemmarket_price(listings), 100)


# ---------------------------------------------------------------------------
# Weav3rMarketplaceApiService — must never raise, must degrade to {}
# ---------------------------------------------------------------------------

class Weav3rMarketplaceApiServiceTests(TestCase):

    @patch('main.services.api.weav3r.marketplace_api_service.requests.get')
    def test_successful_response_is_indexed_by_item_id(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = {
            "items": [
                {"item_id": 206, "item_name": "Xanax", "bazaar_average": 824411},
                {"item_id": 207, "item_name": "Other", "bazaar_average": None},
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = Weav3rMarketplaceApiService.get_bazaar_averages_by_item_id()

        self.assertEqual(result, {206: 824411})

    @patch('main.services.api.weav3r.marketplace_api_service.requests.get')
    def test_http_failure_returns_empty_dict(self, mock_get):
        mock_get.side_effect = Exception('connection refused')

        result = Weav3rMarketplaceApiService.get_bazaar_averages_by_item_id()

        self.assertEqual(result, {})
