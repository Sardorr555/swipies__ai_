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
"""1C:Enterprise Catalog Profiler & Metadata Discovery Engine.

Responsibilities:
1. Warehouse Discovery & Classification:
   - Identifies commercial (saleable) warehouses vs excluded technical warehouses
     (defects, returns, transit, quarantine, write-off, archive).
2. Price Category Discovery & Security:
   - Identifies customer-facing price categories (Retail, Dealer / Wholesale with VAT).
   - Strictly enforces confidentiality rules: internal purchase/cost prices
     (Закупочная, Себестоимость, Плановая) are blacklisted and never exposed.
3. Category Taxonomy & Breadcrumbs:
   - Analyzes hierarchical product folders (Catalog_Номенклатура: IsFolder eq true).
   - Generates complete breadcrumb paths (e.g. 'Электроника / Аудио / Наушники')
     for enrichment of RAG BM25 search indices.
4. Profile Caching:
   - Maintains memory-safe TTL cache for catalog metadata snapshots.
"""

import logging
import re
import time
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import quote

logger = logging.getLogger("CRM.1C.CatalogProfiler")

# Default keywords marking non-saleable / technical warehouses
DEFAULT_EXCLUDED_WAREHOUSE_KEYWORDS = (
    "брак",
    "дефект",
    "рекламац",
    "карантин",
    "транзит",
    "списан",
    "архив",
    "утиль",
    "возврат",
    "виртуал",
    "резерв",
    "ремонт",
    "некондиц",
    "defect",
    "quarantine",
    "transit",
    "scrap",
    "return",
)

# Strict blacklist of confidential internal price types (cost/purchase)
CONFIDENTIAL_PRICE_KEYWORDS = (
    "закуп",
    "себестоим",
    "планов",
    "входящ",
    "учетн",
    "внутрен",
    "базов_закуп",
    "cost",
    "purchase",
    "internal",
    "prime_cost",
)

# Heuristic patterns for commercial price categories
RETAIL_PRICE_KEYWORDS = (
    "рознич",
    "клиент",
    "магазин",
    "сайт",
    "site",
    "web",
    "retail",
    "онлайн",
    "интернет",
    "consumer",
)

DEALER_PRICE_KEYWORDS = (
    "дилер",
    "опт",
    "партнер",
    "мелкоопт",
    "b2b",
    "wholesale",
    "dealer",
    "партнёр",
    "дистриб",
)

# Profile cache: tenant/connection_hash -> (timestamp, profile_dict)
_PROFILER_CACHE: Dict[str, Tuple[float, Dict[str, Any]]] = {}
_PROFILER_CACHE_TTL = 3600.0  # 1 hour


class OneCCatalogProfiler:
    """Catalog profiling and metadata discovery utility for 1C:Enterprise."""

    @staticmethod
    def is_warehouse_excluded(
        warehouse_name: str,
        custom_excluded_keywords: Optional[List[str]] = None,
    ) -> bool:
        """Check if warehouse name indicates a defective/technical/quarantine location."""
        if not warehouse_name:
            return False
        clean_name = warehouse_name.strip().lower()
        keywords = custom_excluded_keywords or DEFAULT_EXCLUDED_WAREHOUSE_KEYWORDS
        for kw in keywords:
            if kw in clean_name:
                return True
        return False

    @staticmethod
    def is_price_confidential(price_type_name: str) -> bool:
        """Check if price type name matches internal confidential cost/purchase prices."""
        if not price_type_name:
            return False
        clean = price_type_name.strip().lower()
        for kw in CONFIDENTIAL_PRICE_KEYWORDS:
            if kw in clean:
                return True
        return False

    @staticmethod
    def classify_price_type(price_type_name: str) -> str:
        """Classify price category into: confidential, retail, dealer, or general."""
        if not price_type_name:
            return "general"
        clean = price_type_name.strip().lower()
        if OneCCatalogProfiler.is_price_confidential(clean):
            return "confidential"
        for kw in RETAIL_PRICE_KEYWORDS:
            if kw in clean:
                return "retail"
        for kw in DEALER_PRICE_KEYWORDS:
            if kw in clean:
                return "dealer"
        return "general"

    @classmethod
    def discover_warehouses(
        cls,
        client: Any,
        connection_config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Query 1C Catalog_Склады to discover active commercial vs excluded warehouses."""
        base_url = (connection_config.get("odata_url") or connection_config.get("base_url") or "").rstrip("/")
        if not base_url:
            return cls._fallback_warehouses(connection_config)

        configured_excluded = connection_config.get("excluded_warehouses") or []
        configured_commercial = connection_config.get("commercial_warehouses") or []

        url = f"{base_url}/Catalog_Склады?$format=json&$select=Ref_Key,Code,Description,ПометкаУдаления&$top=100"
        headers = client._get_auth_headers(connection_config)

        try:
            res = client._execute_get(url, headers=headers, timeout=5.0)
            items = res.get("value") if isinstance(res, dict) else (res if isinstance(res, list) else [])
        except Exception as e:
            logger.warning("Failed to discover warehouses via 1C OData: %s. Using configured or default warehouses.", e)
            return cls._fallback_warehouses(connection_config)

        commercial_list: List[Dict[str, Any]] = []
        excluded_list: List[Dict[str, Any]] = []

        for item in items:
            if not isinstance(item, dict):
                continue
            if item.get("ПометкаУдаления") is True:
                continue

            ref_key = str(item.get("Ref_Key") or "")
            code = str(item.get("Code") or "")
            desc = str(item.get("Description") or item.get("Наименование") or f"Warehouse-{code}").strip()

            entry = {"id": ref_key, "code": code, "name": desc}

            # Check explicit configuration first
            if configured_excluded and any(ex.lower() in desc.lower() for ex in configured_excluded):
                entry["reason"] = "configured_excluded"
                excluded_list.append(entry)
            elif configured_commercial and any(cm.lower() in desc.lower() for cm in configured_commercial):
                entry["reason"] = "configured_commercial"
                commercial_list.append(entry)
            elif cls.is_warehouse_excluded(desc):
                entry["reason"] = "heuristic_defective_or_transit"
                excluded_list.append(entry)
            else:
                entry["reason"] = "commercial_saleable"
                commercial_list.append(entry)

        # Determine default warehouse (prefer 'основной', 'главный', 'центральный' or first commercial)
        default_wh = ""
        for wh in commercial_list:
            n = wh["name"].lower()
            if any(k in n for k in ("основн", "главн", "центральн", "main", "central")):
                default_wh = wh["name"]
                break
        if not default_wh and commercial_list:
            default_wh = commercial_list[0]["name"]

        return {
            "commercial_warehouses": commercial_list,
            "commercial_names": [w["name"] for w in commercial_list],
            "excluded_warehouses": excluded_list,
            "excluded_names": [w["name"] for w in excluded_list],
            "default_warehouse": default_wh,
        }

    @classmethod
    def _fallback_warehouses(cls, connection_config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate warehouse profile from connection config or standard defaults."""
        comm_names = connection_config.get("commercial_warehouses") or ["Основной склад"]
        if isinstance(comm_names, str):
            comm_names = [w.strip() for w in comm_names.split(",") if w.strip()]

        excl_names = connection_config.get("excluded_warehouses") or ["Склад брака", "Брак", "Карантин"]
        if isinstance(excl_names, str):
            excl_names = [w.strip() for w in excl_names.split(",") if w.strip()]

        comm_list = [{"id": "", "code": "", "name": n, "reason": "config"} for n in comm_names]
        excl_list = [{"id": "", "code": "", "name": n, "reason": "config"} for n in excl_names]

        return {
            "commercial_warehouses": comm_list,
            "commercial_names": comm_names,
            "excluded_warehouses": excl_list,
            "excluded_names": excl_names,
            "default_warehouse": comm_names[0] if comm_names else "",
        }

    @classmethod
    def discover_price_types(
        cls,
        client: Any,
        connection_config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Query 1C Catalog_ВидыЦен to discover price categories and filter confidential ones."""
        base_url = (connection_config.get("odata_url") or connection_config.get("base_url") or "").rstrip("/")
        configured_default_price = connection_config.get("default_price_type") or ""

        if not base_url:
            return cls._fallback_price_types(connection_config)

        url = f"{base_url}/Catalog_ВидыЦен?$format=json&$select=Ref_Key,Code,Description,ПометкаУдаления&$top=50"
        headers = client._get_auth_headers(connection_config)

        try:
            res = client._execute_get(url, headers=headers, timeout=5.0)
            items = res.get("value") if isinstance(res, dict) else (res if isinstance(res, list) else [])
        except Exception as e:
            logger.warning("Failed to discover price types via 1C OData: %s. Using configured or default price types.", e)
            return cls._fallback_price_types(connection_config)

        allowed_list: List[Dict[str, Any]] = []
        confidential_list: List[Dict[str, Any]] = []
        retail_list: List[Dict[str, Any]] = []
        dealer_list: List[Dict[str, Any]] = []

        for item in items:
            if not isinstance(item, dict):
                continue
            if item.get("ПометкаУдаления") is True:
                continue

            ref_key = str(item.get("Ref_Key") or "")
            code = str(item.get("Code") or "")
            desc = str(item.get("Description") or item.get("Наименование") or f"PriceType-{code}").strip()

            classification = cls.classify_price_type(desc)
            entry = {"id": ref_key, "code": code, "name": desc, "category": classification}

            if classification == "confidential":
                confidential_list.append(entry)
            else:
                allowed_list.append(entry)
                if classification == "retail":
                    retail_list.append(entry)
                elif classification == "dealer":
                    dealer_list.append(entry)

        # Resolve default price type
        default_pt = configured_default_price
        if not default_pt:
            # Prefer retail if available, else dealer, else first allowed
            if retail_list:
                default_pt = retail_list[0]["name"]
            elif dealer_list:
                default_pt = dealer_list[0]["name"]
            elif allowed_list:
                default_pt = allowed_list[0]["name"]
            else:
                default_pt = "Розничная"

        return {
            "allowed_price_types": allowed_list,
            "allowed_names": [p["name"] for p in allowed_list],
            "confidential_price_types": confidential_list,
            "confidential_names": [p["name"] for p in confidential_list],
            "retail_price_types": [p["name"] for p in retail_list],
            "dealer_price_types": [p["name"] for p in dealer_list],
            "default_price_type": default_pt,
        }

    @classmethod
    def _fallback_price_types(cls, connection_config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate price types from configuration or standard defaults."""
        default_pt = connection_config.get("default_price_type") or "Розничная"
        allowed_names = connection_config.get("allowed_price_types") or [default_pt, "Дилер с НДС", "Оптовая"]
        if isinstance(allowed_names, str):
            allowed_names = [p.strip() for p in allowed_names.split(",") if p.strip()]

        return {
            "allowed_price_types": [{"id": "", "code": "", "name": n, "category": cls.classify_price_type(n)} for n in allowed_names],
            "allowed_names": allowed_names,
            "confidential_price_types": [{"id": "", "code": "", "name": "Закупочная", "category": "confidential"}],
            "confidential_names": ["Закупочная", "Себестоимость"],
            "retail_price_types": [n for n in allowed_names if cls.classify_price_type(n) == "retail"],
            "dealer_price_types": [n for n in allowed_names if cls.classify_price_type(n) == "dealer"],
            "default_price_type": default_pt,
        }

    @classmethod
    def discover_category_tree(
        cls,
        client: Any,
        connection_config: Dict[str, Any],
    ) -> Dict[str, str]:
        """Build folder taxonomy map: Ref_Key -> Full Breadcrumb Path (e.g. 'Электроника / Аудио / Наушники')."""
        base_url = (connection_config.get("odata_url") or connection_config.get("base_url") or "").rstrip("/")
        if not base_url:
            return {}

        url = f"{base_url}/Catalog_Номенклатура?$format=json&$filter=IsFolder eq true and ПометкаУдаления eq false&$select=Ref_Key,Parent_Key,Description,Code&$top=500"
        headers = client._get_auth_headers(connection_config)

        try:
            res = client._execute_get(url, headers=headers, timeout=5.0)
            items = res.get("value") if isinstance(res, dict) else (res if isinstance(res, list) else [])
        except Exception as e:
            logger.warning("Failed to build 1C category taxonomy tree: %s", e)
            return {}

        nodes: Dict[str, Dict[str, Any]] = {}
        for item in items:
            if not isinstance(item, dict):
                continue
            ref = str(item.get("Ref_Key") or "")
            parent = str(item.get("Parent_Key") or "")
            name = str(item.get("Description") or item.get("Наименование") or "").strip()
            if ref and name:
                nodes[ref] = {"name": name, "parent": parent}

        # Resolve paths
        paths: Dict[str, str] = {}

        def get_path(ref_key: str, visited: Set[str]) -> str:
            if not ref_key or ref_key not in nodes or ref_key in visited:
                return ""
            visited.add(ref_key)
            node = nodes[ref_key]
            parent_key = node["parent"]
            parent_path = get_path(parent_key, visited) if parent_key and parent_key in nodes else ""
            if parent_path:
                return f"{parent_path} / {node['name']}"
            return node["name"]

        for ref_key in nodes:
            paths[ref_key] = get_path(ref_key, set())

        return paths

    @classmethod
    def get_catalog_profile(
        cls,
        client: Any,
        connection_config: Dict[str, Any],
        force_refresh: bool = False,
    ) -> Dict[str, Any]:
        """Retrieve cached catalog profile snapshot or execute fresh discovery."""
        base_url = (connection_config.get("odata_url") or connection_config.get("base_url") or "").rstrip("/")
        cache_key = f"{base_url}:{connection_config.get('username', '')}"

        now = time.time()
        if not force_refresh and cache_key in _PROFILER_CACHE:
            ts, profile = _PROFILER_CACHE[cache_key]
            if now - ts < _PROFILER_CACHE_TTL:
                return profile

        # Run discovery
        warehouses = cls.discover_warehouses(client, connection_config)
        price_types = cls.discover_price_types(client, connection_config)
        category_tree = cls.discover_category_tree(client, connection_config)

        profile = {
            "warehouses": warehouses,
            "price_types": price_types,
            "category_tree": category_tree,
            "profiled_at": now,
        }

        _PROFILER_CACHE[cache_key] = (now, profile)
        return profile
