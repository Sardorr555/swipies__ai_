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
from urllib.parse import urlencode, quote, urlsplit

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
        parsed = urlsplit(url)
        if parsed.scheme.lower() == "http":
            from api.crm.transport import is_ip_allowed_by_cidr_list
            import socket
            cidr_list = os.environ.get(ALLOWLIST_CIDR_ENV, "")
            if not cidr_list.strip():
                raise SSRFSecurityException(
                    f"1C HTTP connection to '{parsed.hostname}' is forbidden: HTTP scheme is prohibited unless addresses are explicitly listed in {ALLOWLIST_CIDR_ENV}."
                )
            try:
                addr_info = socket.getaddrinfo(parsed.hostname, None, proto=socket.IPPROTO_TCP)
                ips = [e[4][0] for e in addr_info] if addr_info else []
            except Exception as e:
                raise SSRFSecurityException(f"Cannot resolve 1C host '{parsed.hostname}': {e}") from e
            if not ips or not any(is_ip_allowed_by_cidr_list(ip, ALLOWLIST_CIDR_ENV) for ip in ips):
                raise SSRFSecurityException(
                    f"1C HTTP connection to '{parsed.hostname}' ({ips}) is forbidden: host IP is not within configured CIDR allowlist ({ALLOWLIST_CIDR_ENV})."
                )

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

        # Validate entity_path against path traversal and dangerous injection (Point 4)
        if not re.match(r"^[a-zA-Z0-9_\u0400-\u04FF/()]+$", entity_path) or ".." in entity_path or entity_path.startswith("/"):
            raise ValueError(f"Invalid 1C entity_path '{entity_path}': unsafe characters or path traversal detected.")

        # Sanitize item query and escape single quotes per OData specification (RFC/OData: ' -> '')
        clean_item = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", str(item_query).strip()).replace("'", "''")
        if not clean_item:
            raise ValueError("Empty or invalid item query.")

        # Explicitly configured search filter fields without mixed fallback defaults (Point 7)
        filter_fields = connection_config.get("filter_fields")
        if not filter_fields:
            raise ValueError(
                "1C connection configuration is missing 'filter_fields'. Search fields must be explicitly configured in connection settings."
            )
        if isinstance(filter_fields, str):
            filter_fields = [f.strip() for f in filter_fields.split(",") if f.strip()]

        for field in filter_fields:
            if not re.match(r"^[a-zA-Z0-9_\u0400-\u04FF/]+$", field) or ".." in field:
                raise ValueError(f"Invalid 1C filter field name '{field}': must be a valid identifier.")

        field_clauses = []
        for field in filter_fields:
            field_clauses.append(f"substringof('{clean_item}', {field})")
            field_clauses.append(f"{field} eq '{clean_item}'")
        odata_filter = f"({' or '.join(field_clauses)})"

        warehouse_field = connection_config.get("warehouse_field") or "Warehouse"
        if not re.match(r"^[a-zA-Z0-9_\u0400-\u04FF/]+$", warehouse_field) or ".." in warehouse_field:
            raise ValueError(f"Invalid 1C warehouse field name '{warehouse_field}'.")

        if warehouse:
            clean_wh = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", str(warehouse).strip()).replace("'", "''")
            if clean_wh:
                odata_filter += f" and (substringof('{clean_wh}', {warehouse_field}) or {warehouse_field} eq '{clean_wh}')"

        # Configurable $top with safety ceiling of 100
        top = min(max(1, int(connection_config.get("top") or 50)), 100)

        params = {
            "$format": "json",
            "$filter": odata_filter,
            "$top": str(top),
        }
        url = f"{clean_base}/{entity_path}?{urlencode(params)}"
        headers = self._get_auth_headers(connection_config)

        # Configurable timeout with 10.0s safety ceiling
        cfg_timeout = connection_config.get("timeout")
        timeout = min(float(cfg_timeout), 10.0) if cfg_timeout else DEFAULT_TIMEOUT_SECONDS

        # Enforce strictly GET request
        data = self._execute_get(url, headers=headers, timeout=timeout)

        # Parse standard 1C OData response format: {"value": [...]} or list
        raw_items = data.get("value") if isinstance(data, dict) else (data if isinstance(data, list) else [])
        parsed_items: List[Dict[str, Any]] = []
        total_quantity = 0.0

        for entry in raw_items:
            if len(parsed_items) >= 100:
                break
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

    def query_records(
        self,
        connection_config: Dict[str, Any],
        entity: str,
        query: str = "",
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Query 1C:Enterprise catalog or document records via OData."""
        base_url = (connection_config.get("base_url") or connection_config.get("odata_url", "")).rstrip("/")
        if not base_url:
            raise OneCError("Missing base_url / odata_url in 1C connection configuration")

        entity_clean = entity.strip()
        if entity_clean.lower() in ("product", "nomenclature", "item"):
            odata_entity = "Catalog_Номенклатура"
        elif entity_clean.lower() in ("contact", "company", "counterparty", "client"):
            odata_entity = "Catalog_Контрагенты"
        elif entity_clean.lower() in ("deal", "order"):
            odata_entity = "Document_ЗаказПокупателя"
        elif entity_clean.startswith("Catalog_") or entity_clean.startswith("Document_") or entity_clean.startswith("InformationRegister_"):
            odata_entity = entity_clean
        else:
            odata_entity = "Catalog_Номенклатура"

        headers = self._get_auth_headers(connection_config)
        max_limit = max(1, min(limit, 50))
        params: List[str] = ["$format=json", f"$top={max_limit}"]

        if query:
            clean_q = query.replace("'", "''").strip()
            # 1C OData supports substringof or contains depending on compatibility version
            filter_expr = f"substringof('{clean_q}', Description) or substringof('{clean_q}', Code)"
            params.append(f"$filter={quote(filter_expr)}")

        query_url = f"{base_url}/{quote(odata_entity, safe='_')}?" + "&".join(params)
        logger.info("Executing 1C query_records url=%s", query_url)

        resp = self._execute_get(query_url, headers)
        if resp.status_code == 401:
            raise OneCAuthError("1C OData authentication failed (HTTP 401)")
        if resp.status_code == 403:
            raise OneCAuthError("1C OData access forbidden (HTTP 403)")
        if resp.status_code >= 400:
            raise OneCError(f"1C OData query returned HTTP {resp.status_code}: {resp.text}")

        try:
            data = resp.json()
        except Exception as e:
            raise OneCError(f"Failed to parse 1C OData JSON response: {e}")

        raw_items = data.get("value", [])
        if not isinstance(raw_items, list):
            raw_items = []

        records = []
        for item in raw_items:
            ref_key = item.get("Ref_Key") or item.get("Code") or ""
            desc = item.get("Description") or item.get("Наименование") or item.get("Description_standard") or ""
            price = item.get("Цена") or item.get("СуммаДокумента") or item.get("Price") or 0
            status = item.get("Статус") or item.get("Status") or item.get("Состояние") or ""
            phone = item.get("Телефон") or item.get("Phone") or ""
            email = item.get("Email") or ""

            rec = {
                "id": str(ref_key),
                "entity": entity_clean,
                "title": str(desc),
                "status": str(status),
                "price": price,
                "currency": "RUB",
                "phone": str(phone),
                "email": str(email),
                "updated_at": item.get("Date") or item.get("Дата") or "",
                "raw": item,
            }
            records.append(rec)
        return records
