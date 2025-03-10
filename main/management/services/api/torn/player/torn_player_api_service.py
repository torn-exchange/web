from main.management.services.api.torn.torn_api_service import TornAPIService


class TornPlayerAPIService(TornAPIService):
    def get(self, endpoint: str, query_params: dict = None, access_level: str = None) -> dict:
        endpoint = f"/user{endpoint}"
        return super().get(endpoint, query_params)