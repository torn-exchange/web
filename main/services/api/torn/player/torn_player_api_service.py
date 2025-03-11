from main.services.api.torn.torn_api_service import TornAPIService
from typing import Optional, Dict


class TornPlayerAPIService(TornAPIService):
    def get(self, endpoint: str, query_params: dict = None, access_level: str = None) -> Dict:
        endpoint = f"/user{endpoint}"
        return super().get(endpoint, query_params)

    def get_profile(self, player_id: Optional[int] = None) -> Dict:
        params = {'selections': 'profile'}
        if player_id is not None:
            params['id'] = player_id

        return self.get('', params)
