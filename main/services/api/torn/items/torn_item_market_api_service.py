from main.services.api.torn.torn_api_service import TornAPIService
from typing import Optional, Dict


class TornItemMarketAPIService(TornAPIService):
    def get(self, endpoint: str, query_params: dict = None, access_level: str = None) -> Dict:
        endpoint = f"/market{endpoint}"
        return super().get(endpoint, query_params)

    def get_items(self, item_id: int, offset = 0, bonus = None) -> Dict:
        params = {'id': item_id, 'offset': offset, 'selections': 'itemmarket'}
        if bonus is not None:
            params['bonus'] = bonus
        return self.get('', params)

    def get_rw_items(self, item_id: int, offset = 0, bonus = 'Any') -> Dict:
        return self.get_items(item_id, offset, bonus)