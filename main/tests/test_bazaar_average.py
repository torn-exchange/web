from unittest.mock import patch, Mock
from django.test import TestCase

from main.management.commands.update_items2 import get_lowest_market_price
from main.services.api.weav3r.marketplace_api_service import Weav3rMarketplaceApiService


def make_itemmarket_response(listing_prices):
    return Mock(
        content=(
            '{"itemmarket": {"listings": '
            + str([{"price": p} for p in listing_prices]).replace("'", '"')
            + '}}'
        ).encode(),
    )


# ---------------------------------------------------------------------------
# get_lowest_market_price() — 3-source min (Torn market_value, itemmarket, bazaar_average)
# ---------------------------------------------------------------------------

class GetLowestMarketPriceBazaarAverageTests(TestCase):

    @patch('main.management.commands.update_items2.requests.get')
    def test_bazaar_average_lowers_te_value(self, mock_get):
        # itemmarket listings average to 100, avg_market_price=90, bazaar_average=80 -> 80 wins
        mock_get.return_value = make_itemmarket_response([100, 100, 100])
        result = get_lowest_market_price('1', 'key', avg_market_price=90, bazaar_average=80)
        self.assertEqual(result, 80)

    @patch('main.management.commands.update_items2.requests.get')
    def test_bazaar_average_ignored_when_higher(self, mock_get):
        # bazaar_average is the highest of the three -> doesn't change the result
        mock_get.return_value = make_itemmarket_response([100, 100, 100])
        result = get_lowest_market_price('1', 'key', avg_market_price=90, bazaar_average=200)
        self.assertEqual(result, 90)

    @patch('main.management.commands.update_items2.requests.get')
    def test_bazaar_average_none_falls_back_to_two_source(self, mock_get):
        # No bazaar_average available for this item -> identical to pre-task 2-source behaviour
        mock_get.return_value = make_itemmarket_response([100, 100, 100])
        result = get_lowest_market_price('1', 'key', avg_market_price=90, bazaar_average=None)
        self.assertEqual(result, 90)

    @patch('main.management.commands.update_items2.requests.get')
    def test_bazaar_average_zero_is_ignored(self, mock_get):
        # A falsy/zero bazaar_average must not win over real prices
        mock_get.return_value = make_itemmarket_response([100, 100, 100])
        result = get_lowest_market_price('1', 'key', avg_market_price=90, bazaar_average=0)
        self.assertEqual(result, 90)


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
