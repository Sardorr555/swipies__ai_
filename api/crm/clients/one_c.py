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
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode, quote, urlsplit

from api.crm.base import CRMProviderBase
from api.crm.catalog_profiler import OneCCatalogProfiler
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
    - Warehouse Profiling: Separates commercial/saleable warehouses from technical/defective warehouses.
    - Price Category Profiling & Security: Strictly blocks internal cost/purchase prices and resolves
      configured/target commercial price types.
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

        if hasattr(resp, "status_code"):
            if resp.status_code in (401, 403):
                raise OneCAuthError(f"1C:Enterprise authentication failed (HTTP {resp.status_code})")
            if resp.status_code >= 400:
                raise OneCError(f"1C:Enterprise OData returned HTTP {resp.status_code}: {getattr(resp, 'text', '')[:300]}")

        if hasattr(resp, "json") and callable(resp.json):
            try:
                return resp.json()
            except Exception as e:
                raise OneCError(f"Invalid JSON returned by 1C:Enterprise OData: {e}") from e
        elif isinstance(resp, (dict, list)):
            return resp
        return {}

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
        CRMProviderBase.check_management_allowed(connection_config, action_name="create_lead")
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
            if hasattr(resp, "status_code") and resp.status_code in (401, 403):
                raise OneCAuthError(f"1C credential check failed with HTTP {resp.status_code}")
        except SSRFSecurityException:
            raise
        except OneCAuthError:
            raise
        except Exception as e:
            raise OneCConnectionError(f"1C credential check connection error: {e}") from e

        return connection_config

    def resolve_price(
        self,
        connection_config: Dict[str, Any],
        product_identifier: str,
        price_type: Optional[str] = None,
    ) -> Tuple[float, str, str]:
        """Query 1C InformationRegister_ЦеныНоменклатурыСрезПоследних for real-time prices.
        
        Args:
            connection_config: Connection credentials and settings.
            product_identifier: Product Description, SKU, Code or Ref_Key.
            price_type: Target price category (e.g. 'Розничная', 'Дилер с НДС').
            
        Returns:
            Tuple of (price_value: float, currency: str, price_type_name: str).
        """
        base_url = (connection_config.get("odata_url") or connection_config.get("base_url") or "").rstrip("/")
        default_cur = connection_config.get("currency") or "UZS"
        target_pt = price_type or connection_config.get("default_price_type") or "Розничная"

        # Security check: Bar confidential internal purchase/cost prices
        if OneCCatalogProfiler.is_price_confidential(target_pt):
            raise OneCError(f"Access denied: price type '{target_pt}' is confidential internal cost data.")

        if not base_url or not product_identifier:
            return 0.0, default_cur, target_pt

        clean_id = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", str(product_identifier).strip()).replace("'", "''")
        clean_pt = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", str(target_pt).strip()).replace("'", "''")

        price_entity = connection_config.get("price_entity") or "InformationRegister_ЦеныНоменклатурыСрезПоследних"
        price_entity = price_entity.strip("/")

        # Format OData filter
        pt_filter = f"(substringof('{clean_pt}', ВидЦены/Description) or ВидЦены/Code eq '{clean_pt}')"
        if len(clean_id) == 36 and "-" in clean_id:
            prod_filter = f"(Номенклатура_Key eq guid'{clean_id}' or substringof('{clean_id}', Номенклатура/Description))"
        else:
            prod_filter = f"(substringof('{clean_id}', Номенклатура/Description) or Номенклатура/Code eq '{clean_id}')"

        full_filter = f"{prod_filter} and {pt_filter}"
        query_url = f"{base_url}/{price_entity}?$format=json&$filter={quote(full_filter)}&$top=5"
        headers = self._get_auth_headers(connection_config)

        try:
            data = self._execute_get(query_url, headers=headers, timeout=DEFAULT_TIMEOUT_SECONDS)
            items = data.get("value") if isinstance(data, dict) else (data if isinstance(data, list) else [])
            for item in items:
                if not isinstance(item, dict):
                    continue
                raw_price = item.get("Цена") or item.get("Price") or item.get("Сумма") or 0.0
                try:
                    price_val = float(raw_price)
                except (ValueError, TypeError):
                    price_val = 0.0

                cur = (
                    item.get("Валюта/Description")
                    or item.get("Currency")
                    or item.get("Валюта")
                    or default_cur
                )
                pt_desc = str(item.get("ВидЦены/Description") or target_pt)
                return price_val, str(cur), pt_desc
        except Exception as e:
            logger.warning("Price lookup in 1C %s failed: %s", price_entity, e)

        return 0.0, default_cur, target_pt

    def check_stock(
        self,
        connection_config: Dict[str, Any],
        item_query: str,
        warehouse: Optional[str] = None,
        price_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Query inventory balances over 1C OData REST interface with warehouse and price profiling.
        
        Args:
            connection_config: Decrypted connection configuration.
            item_query: Product SKU, article code, or item name query.
            warehouse: Optional specific warehouse name or code filter.
            price_type: Optional specific price category (e.g. 'Розничная', 'Дилер с НДС').
            
        Returns:
            Dict containing query results, commercial available stock, excluded stock, and resolved price.
        """
        base_url = connection_config.get("odata_url") or connection_config.get("base_url") or ""
        if not base_url:
            raise ValueError("1C connection configuration is missing 'odata_url'")

        clean_base = base_url.rstrip("/")
        entity_path = connection_config.get("entity_path") or "AccumulationRegister_ТоварыНаСкладах/Balance"
        entity_path = entity_path.strip("/")

        # Validate entity_path against path traversal and injection
        if not re.match(r"^[a-zA-Z0-9_\u0400-\u04FF/()]+$", entity_path) or ".." in entity_path or entity_path.startswith("/"):
            raise ValueError(f"Invalid 1C entity_path '{entity_path}': unsafe characters or path traversal detected.")

        # Sanitize item query
        clean_item = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", str(item_query).strip()).replace("'", "''")
        if not clean_item:
            raise ValueError("Empty or invalid item query.")

        # Security check: Check confidential price types
        target_pt = price_type or connection_config.get("default_price_type") or "Розничная"
        if OneCCatalogProfiler.is_price_confidential(target_pt):
            raise OneCError(f"Access denied: price type '{target_pt}' is confidential internal cost data.")

        # Explicitly configured search filter fields without mixed fallback defaults
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

        # Warehouse filter
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

        cfg_timeout = connection_config.get("timeout")
        timeout = min(float(cfg_timeout), 10.0) if cfg_timeout else DEFAULT_TIMEOUT_SECONDS

        # Enforce strictly GET request
        data = self._execute_get(url, headers=headers, timeout=timeout)

        # Parse standard 1C OData response format
        raw_items = data.get("value") if isinstance(data, dict) else (data if isinstance(data, list) else [])
        parsed_items: List[Dict[str, Any]] = []
        commercial_stock = 0.0
        excluded_stock = 0.0
        warehouses_breakdown: List[Dict[str, Any]] = []

        configured_excluded = connection_config.get("excluded_warehouses") or []
        configured_commercial = connection_config.get("commercial_warehouses") or []

        resolved_sku = ""
        resolved_name = ""
        item_ref_key = ""

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
                or entry.get("Склад/Description")
                or "Main Warehouse"
            )
            wh_str = str(wh).strip()
            raw_qty = (
                entry.get("Quantity")
                or entry.get("Количество")
                or entry.get("КоличествоОстаток")
                or entry.get("ВНаличииОстаток")
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

            if not resolved_sku and sku:
                resolved_sku = str(sku)
            if not resolved_name and name:
                resolved_name = str(name)
            if not item_ref_key and entry.get("Номенклатура_Key"):
                item_ref_key = str(entry["Номенклатура_Key"])

            # Determine if this warehouse is commercial (saleable) or excluded (defect, transit, etc.)
            is_comm = True
            reason = "commercial"
            if configured_excluded and any(ex.lower() in wh_str.lower() for ex in configured_excluded):
                is_comm = False
                reason = "configured_excluded"
            elif configured_commercial and any(cm.lower() in wh_str.lower() for cm in configured_commercial):
                is_comm = True
                reason = "configured_commercial"
            elif OneCCatalogProfiler.is_warehouse_excluded(wh_str):
                is_comm = False
                reason = "defective_or_transit"

            if is_comm:
                commercial_stock += quantity
            else:
                excluded_stock += quantity

            item_dict = {
                "sku": str(sku),
                "name": str(name),
                "warehouse": wh_str,
                "quantity": quantity,
                "price": price,
                "is_commercial": is_comm,
            }
            parsed_items.append(item_dict)

            warehouses_breakdown.append({
                "warehouse": wh_str,
                "quantity": quantity,
                "is_commercial": is_comm,
                "status": "saleable" if is_comm else f"excluded ({reason})",
            })

        # Price resolution: If price is 0 (as standard in AccumulationRegister), resolve from price register
        resolved_price = 0.0
        resolved_currency = connection_config.get("currency") or "UZS"
        resolved_pt_name = target_pt

        for item in parsed_items:
            if item.get("price", 0.0) > 0:
                resolved_price = item["price"]
                break

        if parsed_items and resolved_price == 0.0 and (item_ref_key or clean_item):
            lookup_key = item_ref_key or clean_item
            p_val, p_cur, pt_n = self.resolve_price(connection_config, lookup_key, target_pt)
            if p_val > 0:
                resolved_price = p_val
                resolved_currency = p_cur
                resolved_pt_name = pt_n
                for item in parsed_items:
                    if item["price"] == 0.0:
                        item["price"] = resolved_price

        return {
            "status": "success",
            "query": clean_item,
            "sku": resolved_sku or clean_item,
            "name": resolved_name or clean_item,
            "warehouse": warehouse or "all_commercial",
            "total_stock": commercial_stock,
            "commercial_stock": commercial_stock,
            "excluded_stock": excluded_stock,
            "is_available": commercial_stock > 0,
            "price": resolved_price,
            "currency": resolved_currency,
            "price_type": resolved_pt_name,
            "warehouses_breakdown": warehouses_breakdown,
            "item_count": len(parsed_items),
            "items": parsed_items,
        }

    def query_records(
        self,
        connection_config: Dict[str, Any],
        entity: str = "deal",
        query: str = "",
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Query 1C:Enterprise catalog or document records via OData."""
        base_url = (connection_config.get("base_url") or connection_config.get("odata_url", "")).rstrip("/")
        if not base_url:
            raise OneCError("Missing base_url / odata_url in 1C connection configuration")

        filters = filters or {}
        # Security check: Bar confidential price types
        pt_filter = filters.get("price_type") or filters.get("вид_цены")
        if pt_filter and OneCCatalogProfiler.is_price_confidential(str(pt_filter)):
            raise OneCError(f"Access denied: price type '{pt_filter}' is confidential internal cost data.")

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

        filter_clauses: List[str] = []

        # If querying product catalog, automatically exclude deleted items and folders
        if odata_entity == "Catalog_Номенклатура":
            filter_clauses.append("ПометкаУдаления eq false")
            filter_clauses.append("IsFolder eq false")

        if query:
            clean_q = query.replace("'", "''").strip()
            filter_clauses.append(f"(substringof('{clean_q}', Description) or substringof('{clean_q}', Code))")

        # Warehouse filter
        wh_filter = filters.get("warehouse") or filters.get("склад")
        if wh_filter:
            clean_wh = str(wh_filter).replace("'", "''").strip()
            filter_clauses.append(f"(substringof('{clean_wh}', Warehouse) or substringof('{clean_wh}', Склад))")

        if filter_clauses:
            params.append(f"$filter={quote(' and '.join(filter_clauses))}")

        query_url = f"{base_url}/{quote(odata_entity, safe='_')}?" + "&".join(params)
        logger.info("Executing 1C query_records url=%s", query_url)

        resp = self._execute_get(query_url, headers)

        if hasattr(resp, "status_code"):
            if resp.status_code in (401, 403):
                raise OneCAuthError(f"1C OData authentication failed (HTTP {resp.status_code})")
            if resp.status_code >= 400:
                text_snippet = getattr(resp, "text", "")
                raise OneCError(f"1C OData query returned HTTP {resp.status_code}: {text_snippet}")

        if hasattr(resp, "json") and callable(resp.json):
            try:
                data = resp.json()
            except Exception as e:
                raise OneCError(f"Failed to parse 1C OData JSON response: {e}")
        elif isinstance(resp, (dict, list)):
            data = resp
        else:
            data = {}

        raw_items = []
        if isinstance(data, dict):
            if "value" in data and isinstance(data["value"], list):
                raw_items = data["value"]
            elif "d" in data:
                d_val = data["d"]
                if isinstance(d_val, dict) and "results" in d_val and isinstance(d_val["results"], list):
                    raw_items = d_val["results"]
                elif isinstance(d_val, list):
                    raw_items = d_val
                elif isinstance(d_val, dict):
                    raw_items = [d_val]
            elif "Ref_Key" in data or "Code" in data or "Description" in data:
                raw_items = [data]
        elif isinstance(data, list):
            raw_items = data

        currency = connection_config.get("currency") or "UZS"
        records = []
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            ref_key = item.get("Ref_Key") or item.get("Code") or item.get("Код") or item.get("ID") or ""
            desc = item.get("Description") or item.get("Наименование") or item.get("Description_standard") or item.get("Name") or ""
            raw_price = item.get("Цена") or item.get("СуммаДокумента") or item.get("Price") or item.get("Сумма") or 0
            try:
                price = float(raw_price)
            except (ValueError, TypeError):
                price = 0.0

            status = item.get("Статус") or item.get("Status") or item.get("Состояние") or ""
            phone = item.get("Телефон") or item.get("Phone") or item.get("КонтактныйТелефон") or ""
            email = item.get("Email") or item.get("ЭлектроннаяПочта") or ""
            item_currency = item.get("Валюта") or item.get("Currency") or currency

            rec = {
                "id": str(ref_key),
                "entity": entity_clean,
                "title": str(desc),
                "status": str(status),
                "price": price,
                "currency": str(item_currency),
                "phone": str(phone),
                "email": str(email),
                "updated_at": str(item.get("Date") or item.get("Дата") or item.get("Period") or ""),
                "raw": item,
            }
            records.append(rec)
        return records
