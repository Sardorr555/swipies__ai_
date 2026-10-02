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
import base64
import logging
import os
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode, quote

from api.crm.base import CRMProviderBase
from api.crm.transport import CRMTransport, SSRFSecurityException

logger = logging.getLogger("CRM.1C")

ALLOWLIST_CIDR_ENV = "RAGFLOW_CRM_1C_ALLOWLIST_CIDR"
DEFAULT_TIMEOUT_SECONDS = 5.0


class OneCError(Exception):
    """Base exception for 1C:Enterprise OData integration errors."""
    pass


class OneCAuthError(OneCError):
    """Raised when 1C authentication fails (HTTP 401/403)."""
    pass


class OneCConnectionError(OneCError):
    """Raised when 1C server is unreachable or times out."""
    pass


class OneCMethodNotAllowedError(OneCError):
    """Raised when an attempt is made to use a non-GET HTTP method."""
    pass


class OneCClient(CRMProviderBase):
    """Hardened client for querying 1C:Enterprise OData REST interfaces.
    
    Guarantees:
    - Strictly read-only: ONLY HTTP GET requests are permitted. Any non-GET request
      is rejected fail-closed to prevent state mutation in 1C.
    - Strict 5.0-second network timeout.
    - SSRF protections via CRMTransport with platform admin allowlist
      (RAGFLOW_CRM_1C_ALLOWLIST_CIDR).
    - Basic Auth credentials masked in all logs and error traces.
    """

    def __init__(self, transport: Optional[CRMTransport] = None):
        self.transport = transport or CRMTransport(
            private_cidr_allowlist_env=ALLOWLIST_CIDR_ENV,
            allowed_schemes=frozenset({"http", "https"}),
            default_timeout=DEFAULT_TIMEOUT_SECONDS,
        )

    def _get_auth_headers(self, config: Dict[str, Any]) -> Dict[str, str]:
        headers = {
            "Accept": "application/json",
            "User-Agent": "RAGFlow-1C-StockChecker/1.0",
        }
        username = config.get("username") or ""
        password = config.get("password") or ""
        token = config.get("token") or config.get("api_key") or ""

        if token:
            headers["Authorization"] = f"Bearer {token}"
        elif username:
            user_pass = f"{username}:{password}".encode("utf-8")
            b64_auth = base64.b64encode(user_pass).decode("ascii")
            headers["Authorization"] = f"Basic {b64_auth}"
        return headers

    def _execute_get(self, url: str, headers: Dict[str, str], timeout: float = DEFAULT_TIMEOUT_SECONDS) -> Any:
        """Execute strictly GET request over CRMTransport."""
        try:
            logger.info("1C OData GET request to %s (timeout=%.1fs)", re.sub(r"://([^:@]+):[^@]+@", r"://\1:********@", url), timeout)
            resp = self.transport.get(url, headers=headers, timeout=timeout)
        except SSRFSecurityException:
            raise
        except Exception as e:
            raise OneCConnectionError(f"Network error querying 1C:Enterprise OData: {e}") from e

        if resp.status_code in (401, 403):
            raise OneCAuthError(f"1C:Enterprise authentication failed (HTTP {resp.status_code})")
        if resp.status_code >= 400:
            raise OneCError(f"1C:Enterprise OData returned HTTP {resp.status_code}: {resp.text[:300]}")

        try:
            return resp.json()
        except Exception as e:
            raise OneCError(f"Invalid JSON returned by 1C:Enterprise OData: {e}") from e

    def execute_mutating_request(self, method: str, *args, **kwargs):
        """Security guard: explicitly reject any non-GET request."""
        raise OneCMethodNotAllowedError(
            f"HTTP method '{method}' is strictly prohibited. 1C integration only permits read-only GET requests."
        )

    # -------------------------------------------------------------------------
    # CRMProviderBase Interface Implementation
    # -------------------------------------------------------------------------

    def create_lead(self, connection_config: Dict[str, Any], lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """1C is a stock/ERP provider and does not support lead creation in v1."""
        return {
            "supported": False,
            "message": "1C:Enterprise provider is read-only inventory checking and does not support create_lead.",
        }

    def find_contact(self, connection_config: Dict[str, Any], phone: str) -> Optional[Dict[str, Any]]:
        """1C does not store CRM sales contacts in v1."""
        return None

    def refresh_auth(self, connection_config: Dict[str, Any]) -> Dict[str, Any]:
        """Verify 1C credentials by querying OData root / metadata."""
        base_url = connection_config.get("odata_url") or connection_config.get("base_url") or ""
        if not base_url:
            raise ValueError("1C connection configuration is missing 'odata_url'")

        clean_url = base_url.rstrip("/") + "/$metadata"
        headers = self._get_auth_headers(connection_config)

        try:
            resp = self.transport.get(clean_url, headers=headers, timeout=DEFAULT_TIMEOUT_SECONDS)
            if resp.status_code in (401, 403):
                raise OneCAuthError(f"1C credential check failed with HTTP {resp.status_code}")
        except SSRFSecurityException:
            raise
        except OneCAuthError:
            raise
        except Exception as e:
            raise OneCConnectionError(f"1C credential check connection error: {e}") from e

        return connection_config

    def check_stock(
        self,
        connection_config: Dict[str, Any],
        item_query: str,
        warehouse: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Query inventory balances over 1C OData REST interface.
        
        Args:
            connection_config: Decrypted connection configuration.
            item_query: Product SKU, article code, or item name query.
            warehouse: Optional warehouse filter.
            
        Returns:
            Dict containing query results and total stock quantity.
        """
        base_url = connection_config.get("odata_url") or connection_config.get("base_url") or ""
        if not base_url:
            raise ValueError("1C connection configuration is missing 'odata_url'")

        clean_base = base_url.rstrip("/")
        entity_path = connection_config.get("entity_path") or "AccumulationRegister_ТоварыНаСкладах/Balance"
        entity_path = entity_path.strip("/")

        # Sanitize item query to prevent OData injection
        clean_item = re.sub(r"['\"\x00-\x1f\x7f-\x9f]", "", str(item_query).strip())
        if not clean_item:
            raise ValueError("Empty or invalid item query.")

        # Construct standard OData $filter and $format
        odata_filter = (
            f"(substringof('{clean_item}', Description) or "
            f"substringof('{clean_item}', SKU) or "
            f"SKU eq '{clean_item}' or "
            f"Code eq '{clean_item}')"
        )
        if warehouse:
            clean_wh = re.sub(r"['\"\x00-\x1f\x7f-\x9f]", "", str(warehouse).strip())
            if clean_wh:
                odata_filter += f" and (substringof('{clean_wh}', Warehouse) or Warehouse eq '{clean_wh}')"

        params = {
            "$format": "json",
            "$filter": odata_filter,
        }
        url = f"{clean_base}/{entity_path}?{urlencode(params)}"
        headers = self._get_auth_headers(connection_config)

        # Enforce strictly GET request
        data = self._execute_get(url, headers=headers, timeout=DEFAULT_TIMEOUT_SECONDS)

        # Parse standard 1C OData response format: {"value": [...]} or list
        raw_items = data.get("value") if isinstance(data, dict) else (data if isinstance(data, list) else [])
        parsed_items: List[Dict[str, Any]] = []
        total_quantity = 0.0

        for entry in raw_items:
            if not isinstance(entry, dict):
                continue
            sku = (
                entry.get("SKU")
                or entry.get("Артикул")
                or entry.get("Code")
                or entry.get("Код")
                or entry.get("sku")
                or ""
            )
            name = (
                entry.get("Description")
                or entry.get("Наименование")
                or entry.get("Номенклатура")
                or entry.get("name")
                or "Unknown Item"
            )
            wh = (
                entry.get("Warehouse")
                or entry.get("Склад")
                or entry.get("warehouse")
                or "Main Warehouse"
            )
            raw_qty = (
                entry.get("Quantity")
                or entry.get("Количество")
                or entry.get("КоличествоОстаток")
                or entry.get("Balance")
                or entry.get("count")
                or 0
            )
            try:
                quantity = float(raw_qty)
            except (ValueError, TypeError):
                quantity = 0.0

            raw_price = entry.get("Price") or entry.get("Цена") or entry.get("price") or 0
            try:
                price = float(raw_price)
            except (ValueError, TypeError):
                price = 0.0

            total_quantity += quantity
            parsed_items.append({
                "sku": str(sku),
                "name": str(name),
                "warehouse": str(wh),
                "quantity": quantity,
                "price": price,
            })

        return {
            "status": "success",
            "query": clean_item,
            "warehouse": warehouse or "",
            "total_stock": total_quantity,
            "item_count": len(parsed_items),
            "items": parsed_items,
        }
