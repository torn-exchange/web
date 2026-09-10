from main.services.api.torn.torn_api_service import TornAPIService


class TornEliminationAPIService(TornAPIService):
    """Reads the Torn v2 ``/torn/elimination`` team-standings endpoint.

    Inherits key selection (``get_key`` picks a working trader key, falling
    back to ``SYSTEM_API_KEY``) and error handling from ``TornAPIService``.
    """

    @classmethod
    def get_standings(cls):
        return cls.get("/torn/elimination")
