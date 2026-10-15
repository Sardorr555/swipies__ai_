#
#  Copyright 2025 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
import logging
from typing import Any, Dict, List, Optional
from urllib.parse import urlsplit

from api.crm.base import CRMProviderBase
from api.crm.transport import CRMTransport, SSRFSecurityException
from api.crm.clients.amocrm import mask_phone_dynamic
from api.crm.clients.bitrix24 import normalize_phone_to_e164

logger = logging.getLogger("HubSpotClient")


class HubSpotError(Exception):
    """Base exception for HubSpot provider errors."""
    pass


class HubSpotAuthError(HubSpotError):
    """Raised when HubSpot access token is invalid or expired."""
    pass


class HubSpotClient(CRMProviderBase):
    """Hardened client for HubSpot CRM REST API v3."""

    def __init__(self, transport: Optional[CRMTransport] = None):
        self.transport = transport or CRMTransport(
            allowed_schemes=frozenset({"https"}),
            default_timeout=15.0,
        )
        self.base_url = "https://api.hubapi.com"

    def _get_headers(self, connection_config: Dict[str, Any]) -> Dict[str, str]:
        token = (
            connection_config.get("access_token")
            or connection_config.get("api_key")
            or connection_config.get("token", "")
        ).strip()
        if not token:
            raise HubSpotAuthError("Missing access_token / private app token in HubSpot connection config.")
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def refresh_auth(self, connection_config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate HubSpot credentials by pinging contact schema."""
        headers = self._get_headers(connection_config)
        test_url = f"{self.base_url}/crm/v3/objects/contacts?limit=1"
        try:
            resp = self.transport.get(test_url, headers=headers, allow_redirects=False, timeout=10.0)
            if resp.status_code == 401:
                raise HubSpotAuthError("HubSpot authentication failed: Invalid token.")
            if resp.status_code >= 400:
                raise HubSpotError(f"HubSpot API returned status {resp.status_code}: {resp.text}")
        except SSRFSecurityException as e:
            raise HubSpotError(f"SSRF violation: {e}") from e
        return connection_config

    def find_contact(self, connection_config: Dict[str, Any], phone: str) -> Optional[Dict[str, Any]]:
        """Find contact by phone via HubSpot search endpoint."""
        default_region = connection_config.get("default_phone_region", "US")
        norm_phone = normalize_phone_to_e164(phone, default_region)
        headers = self._get_headers(connection_config)
        search_url = f"{self.base_url}/crm/v3/objects/contacts/search"

        payload = {
            "filterGroups": [
                {
                    "filters": [
                        {
                            "propertyName": "phone",
                            "operator": "EQ",
                            "value": norm_phone,
                        }
                    ]
                }
            ],
            "limit": 1,
        }

        try:
            resp = self.transport.post(search_url, json=payload, headers=headers, allow_redirects=False, timeout=10.0)
            if resp.status_code == 200:
                results = resp.json().get("results", [])
                return results[0] if results else None
            elif resp.status_code == 401:
                raise HubSpotAuthError("HubSpot authentication failed")
        except Exception as e:
            logger.warning("Error searching HubSpot contact: %s", e)
        return None

    def create_lead(self, connection_config: Dict[str, Any], lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create deal / lead in HubSpot."""
        CRMProviderBase.check_management_allowed(connection_config, action_name="create_lead")
        headers = self._get_headers(connection_config)
        url = f"{self.base_url}/crm/v3/objects/deals"

        name = lead_data.get("name", "Client")
        title = lead_data.get("title") or f"Lead from Chat: {name}"
        price = lead_data.get("price", 0)

        properties = {
            "dealname": title,
            "pipeline": connection_config.get("pipeline_id", "default"),
            "dealstage": connection_config.get("dealstage", "appointmentscheduled"),
            "description": lead_data.get("note", ""),
        }
        if price:
            properties["amount"] = str(price)

        resp = self.transport.post(url, json={"properties": properties}, headers=headers, allow_redirects=False, timeout=10.0)
        if resp.status_code in (200, 201):
            data = resp.json()
            return {
                "crm_type": "hubspot",
                "lead_id": str(data.get("id", "")),
                "status": "success",
            }
        elif resp.status_code == 401:
            raise HubSpotAuthError("HubSpot authentication failed")
        raise HubSpotError(f"Failed to create HubSpot deal: {resp.text}")

    def check_stock(self, connection_config: Dict[str, Any], item_query: str) -> Dict[str, Any]:
        return {
            "supported": False,
            "message": "HubSpot provider does not support inventory or stock balance checks. Use 1C:Enterprise provider.",
        }

    def query_records(
        self,
        connection_config: Dict[str, Any],
        entity: str,
        query: str = "",
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Query HubSpot CRM records (deals, contacts, companies, products)."""
        headers = self._get_headers(connection_config)
        limit = max(1, min(limit, 50))

        entity_clean = entity.lower().strip().rstrip("s")
        entity_map = {
            "deal": "deals",
            "lead": "deals",
            "contact": "contacts",
            "company": "companies",
            "product": "products",
        }
        obj_type = entity_map.get(entity_clean, "deals")

        url = f"{self.base_url}/crm/v3/objects/{obj_type}/search"
        payload: Dict[str, Any] = {"limit": limit}

        if query:
            payload["query"] = query.strip()

        filter_groups = []
        if filters:
            sub_filters = []
            for k, v in filters.items():
                if k in ("stage", "status"):
                    prop = "dealstage" if obj_type == "deals" else "status"
                    sub_filters.append({"propertyName": prop, "operator": "EQ", "value": str(v)})
                elif k in ("pipeline", "pipeline_id"):
                    sub_filters.append({"propertyName": "pipeline", "operator": "EQ", "value": str(v)})
            if sub_filters:
                filter_groups.append({"filters": sub_filters})

        if filter_groups:
            payload["filterGroups"] = filter_groups

        resp = self.transport.post(url, json=payload, headers=headers, allow_redirects=False, timeout=15.0)
        if resp.status_code == 200:
            raw_results = resp.json().get("results", [])
            normalized = []
            for item in raw_results:
                props = item.get("properties", {})
                rec = {
                    "id": str(item.get("id", "")),
                    "entity": entity_clean,
                    "title": props.get("dealname") or props.get("name") or props.get("firstname", "") + " " + props.get("lastname", ""),
                    "status": props.get("dealstage") or props.get("lifecyclestage", ""),
                    "price": props.get("amount") or props.get("price", ""),
                    "phone": props.get("phone") or props.get("mobilephone", ""),
                    "email": props.get("email", ""),
                    "created_at": item.get("createdAt", ""),
                    "updated_at": item.get("updatedAt", ""),
                    "raw": props,
                }
                normalized.append(rec)
            return normalized
        elif resp.status_code == 401:
            raise HubSpotAuthError("HubSpot authentication failed (HTTP 401)")
        raise HubSpotError(f"HubSpot search failed (HTTP {resp.status_code}): {resp.text}")
