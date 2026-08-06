import requests


class Weav3rMarketplaceApiService:
    """
    Client for weav3r.dev's public marketplace endpoint, used as a third price
    source (bazaar average) alongside Torn's own market_value and TE's
    itemmarket-derived price when computing Item.TE_value.
    """

    base_url = "https://weav3r.dev/api/marketplace"

    @classmethod
    def get(cls):
        try:
            response = requests.get(cls.base_url, timeout=15)
            response.raise_for_status()
            return {"success": True, "data": response.json()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @classmethod
    def get_bazaar_averages_by_item_id(cls):
        """
        Returns {item_id: bazaar_average} for O(1) lookup during the item
        update loop. Returns {} on any failure so a weav3r outage never
        blocks the hourly item sync.
        """
        result = cls.get()
        if not result["success"]:
            return {}

        averages = {}
        for row in result["data"]:
            item_id = row.get("item_id")
            bazaar_average = row.get("bazaar_average")
            if item_id is not None and bazaar_average:
                averages[item_id] = bazaar_average
        return averages
