import base64
import hashlib
import hmac
import time
import urllib.parse
from typing import Dict, List, Optional, Any
import requests
from datetime import datetime, timedelta

from config.settings import settings
from src.models.schemas import MarketData


class BrickLinkClient:
    BASE_URL = "https://api.bricklink.com/api/store/v1"

    def __init__(self):
        self.consumer_key = settings.bricklink_consumer_key
        self.consumer_secret = settings.bricklink_consumer_secret
        self.token_value = settings.bricklink_token_value
        self.token_secret = settings.bricklink_token_secret

    def _generate_oauth_signature(
        self, method: str, url: str, params: Dict[str, str]
    ) -> str:
        """Generate OAuth 1.0 signature for BrickLink API"""
        # Sort parameters
        sorted_params = sorted(params.items())
        param_string = urllib.parse.urlencode(sorted_params)

        # Create base string
        base_string = f"{method.upper()}&{urllib.parse.quote(url, safe='')}&{urllib.parse.quote(param_string, safe='')}"

        # Create signing key
        signing_key = f"{urllib.parse.quote(self.consumer_secret, safe='')}&{urllib.parse.quote(self.token_secret, safe='')}"

        # Generate signature
        signature = hmac.new(
            signing_key.encode("utf-8"), base_string.encode("utf-8"), hashlib.sha1
        ).digest()

        return urllib.parse.quote(base64.b64encode(signature).decode("utf-8"), safe="")

    def _get_oauth_headers(
        self, method: str, url: str, params: Optional[Dict] = None
    ) -> Dict[str, str]:
        """Generate OAuth headers for API request"""
        if params is None:
            params = {}

        oauth_params = {
            "oauth_consumer_key": self.consumer_key,
            "oauth_token": self.token_value,
            "oauth_signature_method": "HMAC-SHA1",
            "oauth_timestamp": str(int(time.time())),
            "oauth_nonce": str(int(time.time() * 1000)),
            "oauth_version": "1.0",
        }

        # Combine with request params for signature generation
        all_params = {**params, **oauth_params}

        # Generate signature
        oauth_params["oauth_signature"] = self._generate_oauth_signature(
            method, url, all_params
        )

        # Create authorization header
        auth_header = "OAuth " + ", ".join(
            f'{k}="{v}"' for k, v in sorted(oauth_params.items())
        )

        return {"Authorization": auth_header}

    def search_items(self, item_type: str, search_term: str) -> List[Dict[str, Any]]:
        """Search for items on BrickLink"""
        if not all(
            [
                self.consumer_key,
                self.consumer_secret,
                self.token_value,
                self.token_secret,
            ]
        ):
            return []

        url = f"{self.BASE_URL}/items/{item_type}"
        params = {"name": search_term}

        try:
            headers = self._get_oauth_headers("GET", url, params)
            response = requests.get(url, params=params, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                return data.get("data", [])
            else:
                print(f"BrickLink API error: {response.status_code} - {response.text}")
                return []

        except Exception as e:
            print(f"Error calling BrickLink API: {e}")
            return []

    def get_price_guide(
        self, item_type: str, item_no: str, condition: str = "U"
    ) -> Optional[MarketData]:
        """Get price guide data for a specific item"""
        if not all(
            [
                self.consumer_key,
                self.consumer_secret,
                self.token_value,
                self.token_secret,
            ]
        ):
            return None

        url = f"{self.BASE_URL}/items/{item_type}/{item_no}/price"
        params = {
            "guide_type": "stock",
            "new_or_used": condition,  # N for new, U for used
            "currency_code": "USD",
        }

        try:
            headers = self._get_oauth_headers("GET", url, params)
            response = requests.get(url, params=params, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                price_data = data.get("data", {})

                return MarketData(
                    current_price=price_data.get("avg_price"),
                    avg_price_6m=price_data.get(
                        "avg_price"
                    ),  # BrickLink doesn't provide 6m specific
                    times_sold=price_data.get("times_sold"),
                    availability=self._determine_availability(
                        price_data.get("times_sold", 0)
                    ),
                )
            else:
                print(f"BrickLink price guide error: {response.status_code}")
                return None

        except Exception as e:
            print(f"Error getting price guide: {e}")
            return None

    def get_item_details(
        self, item_type: str, item_no: str
    ) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific item"""
        if not all(
            [
                self.consumer_key,
                self.consumer_secret,
                self.token_value,
                self.token_secret,
            ]
        ):
            return None

        url = f"{self.BASE_URL}/items/{item_type}/{item_no}"

        try:
            headers = self._get_oauth_headers("GET", url)
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                return data.get("data", {})
            else:
                return None

        except Exception as e:
            print(f"Error getting item details: {e}")
            return None

    def _determine_availability(self, times_sold: int) -> str:
        """Determine availability based on times sold"""
        if times_sold == 0:
            return "very_rare"
        elif times_sold < 10:
            return "rare"
        elif times_sold < 50:
            return "uncommon"
        else:
            return "common"

    def get_similar_items(
        self, item_name: str, theme: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Find similar items based on name and theme"""
        results = []

        # Search minifigures
        minifig_results = self.search_items("MINIFIG", item_name)
        results.extend(minifig_results)

        # Search sets if relevant
        set_results = self.search_items("SET", item_name)
        results.extend(set_results)

        # Filter by theme if provided
        if theme:
            results = [
                item
                for item in results
                if theme.lower() in item.get("category_name", "").lower()
            ]

        return results[:10]  # Limit results
