import requests
from datetime import datetime
from typing import Any, Dict, Type

from main.services.api.torn.torn_api_error_handler import TornApiErrorHandler
from users.models import Profile
from random import choice
import os


class TornAPIService:
    base_url: str = "https://api.torn.com/v2"
    api_key: str = None

    @classmethod
    def get_key(cls, access_level: str = 'None'):
        if cls.api_key is not None:
            return cls.api_key

        profiles_with_keys = Profile.objects.exclude(api_key='')
        if not profiles_with_keys.exists():
            return os.getenv('SYSTEM_API_KEY')

        return choice(profiles_with_keys).api_key

    @classmethod
    def set_key(cls, key: str) -> Type['TornAPIService']:
        cls.api_key = key
        return cls

    @classmethod
    def get(cls, endpoint: str, query_params: Dict[str, Any] = None, access_level: str = None) -> Dict[str, Any]:
        query_params = query_params or {}
        headers = {"Authorization": f"ApiKey {cls.get_key(access_level)}"}

        response = None
        try:
            response = requests.get(f"{cls.base_url}{endpoint}", headers=headers, params=query_params)
            response.raise_for_status()
            return cls.handle_response(response.json())
        except requests.ConnectionError as e:
            return {"success": False, "message": f"Connection failed: {str(e)}"}
        except requests.HTTPError as e:
            return cls.handle_error_response(response)

    @classmethod
    def handle_response(cls, response: Dict[str, Any]) -> Dict[str, Any]:
        if "error" in response:
            if "code" in response["error"]:
                TornApiErrorHandler.handle_error(response["error"]["code"])
            return {"success": False, "message": str(response["error"])}
        return {"success": True, "data": response}

    @classmethod
    def handle_error_response(cls, response: requests.Response) -> Dict[str, Any]:
        status_code = response.status_code
        error_messages = {
            400: "Bad Request: Invalid request.",
            401: "Unauthorized: Invalid API key.",
            404: "Not Found: The requested resource could not be found.",
            500: "Internal Server Error: Please try again later."
        }
        return {"success": False, "message": error_messages.get(status_code, f"An error occurred: {response.text}")}

