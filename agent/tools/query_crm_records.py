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
import json
import logging
import os
import re
import time
from abc import ABC
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from agent.tools.base import ToolParamBase, ToolBase, ToolMeta
from common.connection_utils import timeout
from api.db.crm_models import CRMConnection
from api.db.services.crm_service import CRMConnectionService
from api.crm.base import CRMProviderRegistry

logger = logging.getLogger("QueryCRMRecords")

# Lightweight short-term query cache to avoid hitting external CRM rate limits
_QUERY_CACHE: Dict[str, Tuple[float, List[Dict[str, Any]]]] = {}
_CACHE_TTL_SECONDS = 10.0


def parse_sql_crm_query(sql: str) -> Dict[str, Any]:
    """Parse a natural SQL query into CRM entity, columns, filters, aggregations, order, and limit."""
    parsed: Dict[str, Any] = {
        "entity": "deal",
        "columns": [],
        "query": "",
        "status": "",
        "min_price": None,
        "max_price": None,
        "aggregate": "",  # "count", "sum", "avg", "min", "max"
        "aggregate_column": "",
        "order_by": "",
        "order_direction": "desc",
        "limit": 10,
    }
    if not sql or not isinstance(sql, str):
        return parsed

    clean_sql = sql.strip().rstrip(";")

    # 1. Parse entity from FROM clause
    from_match = re.search(r"\bFROM\s+([a-zA-Z0-9_\u0400-\u04FF]+)", clean_sql, re.IGNORECASE)
    if from_match:
        tbl = from_match.group(1).lower().rstrip("s")
        tbl_map = {
            "deal": "deal",
            "lead": "lead",
            "contact": "contact",
            "company": "company",
            "product": "product",
            "order": "order",
            "сделк": "deal",
            "сделка": "deal",
            "сделки": "deal",
            "лид": "lead",
            "лиды": "lead",
            "контакт": "contact",
            "контакты": "contact",
            "товар": "product",
            "товары": "product",
            "номенклатур": "product",
            "номенклатура": "product",
            "заказ": "order",
            "заказы": "order",
        }
        parsed["entity"] = tbl_map.get(tbl, tbl)

    # 2. Parse SELECT columns and aggregates
    select_match = re.search(r"\bSELECT\s+(.+?)\s+\bFROM\b", clean_sql, re.IGNORECASE | re.DOTALL)
    if select_match:
        raw_select = select_match.group(1).strip()
        agg_match = re.search(r"\b(COUNT|SUM|AVG|MIN|MAX)\s*\(\s*([a-zA-Z0-9_\*]+)\s*\)", raw_select, re.IGNORECASE)
        if agg_match:
            parsed["aggregate"] = agg_match.group(1).lower()
            parsed["aggregate_column"] = agg_match.group(2).lower()
        elif raw_select != "*":
            cols = [c.strip().lower() for c in raw_select.split(",") if c.strip()]
            parsed["columns"] = cols

    # 3. Parse LIMIT
    limit_match = re.search(r"\bLIMIT\s+(\d+)", clean_sql, re.IGNORECASE)
    if limit_match:
        try:
            parsed["limit"] = int(limit_match.group(1))
        except Exception:
            pass

    # 4. Parse ORDER BY
    order_match = re.search(r"\bORDER\s+BY\s+([a-zA-Z0-9_]+)(?:\s+(ASC|DESC))?", clean_sql, re.IGNORECASE)
    if order_match:
        parsed["order_by"] = order_match.group(1).lower()
        if order_match.group(2):
            parsed["order_direction"] = order_match.group(2).lower()

    # 5. Parse Status / Stage
    status_match = re.search(r"(?:status|stage|статус|состояние)\s*(?:=|is|like)\s*['\"]([^'\"]+)['\"]", clean_sql, re.IGNORECASE)
    if status_match:
        parsed["status"] = status_match.group(1).strip()

    # 6. Parse numeric price/opportunity comparisons
    min_price_match = re.search(r"(?:price|opportunity|сумма|цена|amount)\s*(?:>=|>)\s*(\d+(?:\.\d+)?)", clean_sql, re.IGNORECASE)
    if min_price_match:
        try:
            parsed["min_price"] = float(min_price_match.group(1))
        except Exception:
            pass

    max_price_match = re.search(r"(?:price|opportunity|сумма|цена|amount)\s*(?:<=|<)\s*(\d+(?:\.\d+)?)", clean_sql, re.IGNORECASE)
    if max_price_match:
        try:
            parsed["max_price"] = float(max_price_match.group(1))
        except Exception:
            pass

    # 7. Extract general search term / name / query / phone
    q_match = re.search(r"(?:name|title|query|phone|description|наименование|название|телефон)\s*(?:=|like)\s*['\"]%?([^'\"%]+)%?['\"]", clean_sql, re.IGNORECASE)
    if q_match:
        parsed["query"] = q_match.group(1).strip()
    elif not parsed["status"]:
        where_match = re.search(r"\bWHERE\s+(.+?)(?:\s+\b(?:ORDER|LIMIT)\b|$)", clean_sql, re.IGNORECASE)
        if where_match:
            raw_where = where_match.group(1)
            raw_text = re.sub(r"[=><'\"]", " ", raw_where)
            tokens = [
                t.strip()
                for t in raw_text.split()
                if len(t.strip()) > 2 and t.lower() not in (
                    "and", "or", "not", "where", "like", "is", "null", "limit",
                    "status", "stage", "price", "amount", "order", "by", "desc", "asc"
                )
            ]
            if tokens:
                parsed["query"] = " ".join(tokens)

    return parsed


class QueryCRMRecordsParam(ToolParamBase):
    """Configuration parameters for QueryCRMRecords tool component."""

    def __init__(self):
        self.meta: ToolMeta = {
            "name": "query_crm_records",
            "description": "Queries real-time live records (deals, leads, contacts, companies, products, orders) from connected CRM/ERP systems (Bitrix24, amoCRM, Kommo, HubSpot, 1C:Enterprise). Use this tool to look up existing records, check deal status, or search catalogs dynamically without waiting for background RAG synchronization.",
            "parameters": {
                "entity": {
                    "type": "string",
                    "description": "Type of CRM entity to query: 'deal', 'lead', 'contact', 'company', 'product', or 'order'. Default is 'deal'.",
                    "default": "deal",
                    "required": False,
                },
                "query": {
                    "type": "string",
                    "description": "Search keyword: client name, company name, phone (+...), email, deal title, or record ID.",
                    "default": "{sys.query}",
                    "required": False,
                },
                "status": {
                    "type": "string",
                    "description": "Optional stage or status filter (e.g. 'WON', 'NEW', 'IN_PROGRESS', or status ID).",
                    "default": "",
                    "required": False,
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of records to return (1 to 50). Default is 5.",
                    "default": 5,
                    "required": False,
                },
                "sql": {
                    "type": "string",
                    "description": "Optional natural SQL-style query (e.g. \"SELECT title, price FROM deals WHERE status = 'WON'\" or \"SELECT COUNT(*) FROM deals\"). If supplied, table name, columns, and filters are extracted automatically.",
                    "default": "",
                    "required": False,
                },
            },
        }
        super().__init__()
        self.connection_id = ""
        self.allow_anonymous = False
        self.limit = 5

    def check(self):
        if hasattr(self, "limit"):
            try:
                self.limit = max(1, min(int(self.limit), 50))
            except Exception:
                self.limit = 5

    def get_input_form(self) -> dict[str, dict]:
        return {
            "entity": {
                "name": "Entity",
                "type": "select",
                "options": ["deal", "lead", "contact", "company", "product", "order"],
            },
            "query": {"name": "Search Query", "type": "line"},
            "status": {"name": "Status / Stage Filter", "type": "line", "optional": True},
            "limit": {"name": "Limit (1-50)", "type": "line", "optional": True},
            "sql": {"name": "SQL Query (Optional)", "type": "line", "optional": True},
        }


class QueryCRMRecords(ToolBase, ABC):
    """Canvas tool to query, filter, and inspect CRM entities in real-time."""

    component_name = "QueryCRMRecords"

    @timeout(int(os.environ.get("COMPONENT_EXEC_TIMEOUT", 30)))
    def _invoke(self, **kwargs) -> Dict[str, Any]:
        try:
            return self._do_invoke(**kwargs)
        finally:
            try:
                db = getattr(CRMConnection._meta, "database", None)
                if db and not db.is_closed():
                    db.close()
            except Exception:
                pass

    def _do_invoke(self, **kwargs) -> Dict[str, Any]:
        if self.check_if_canceled("QueryCRMRecords processing"):
            return {"status": "canceled"}

        # 1. Channel check for public/embed channels
        server_channel = getattr(self._canvas, "get_channel", lambda: None)()
        allow_anon = getattr(self._param, "allow_anonymous", False)
        if server_channel in ("webhook", "embed") and not allow_anon:
            raise PermissionError(
                f"CRM live query tool execution rejected on unauthenticated public channel '{server_channel}'. "
                "Set allow_anonymous=True in tool parameters if anonymous lookups are explicitly intended."
            )

        # 2. Check if SQL query was supplied
        sql_input = kwargs.get("sql") or getattr(self._param, "sql", "") or ""
        parsed_sql = parse_sql_crm_query(sql_input) if sql_input else {}

        # 3. Resolve parameters with SQL fallback
        entity = kwargs.get("entity") or parsed_sql.get("entity") or getattr(self._param, "entity", "deal") or "deal"
        query = kwargs.get("query")
        if query is None or query == "{sys.query}":
            query = parsed_sql.get("query") or ""
        status = kwargs.get("status") or parsed_sql.get("status") or getattr(self._param, "status", "") or ""

        limit_val = kwargs.get("limit") or parsed_sql.get("limit") or getattr(self._param, "limit", 5) or 5
        try:
            limit = max(1, min(int(limit_val), 50))
        except (ValueError, TypeError):
            limit = 5

        # 4. Resolve active CRM connection for tenant
        tenant_id = getattr(self._canvas, "get_tenant_id", lambda: None)()
        if not tenant_id and hasattr(self._canvas, "_tenant_id"):
            tenant_id = self._canvas._tenant_id
        if not tenant_id:
            raise ValueError("Canvas context missing tenant_id: cannot resolve CRM connection.")

        conn_id = (
            kwargs.get("connection_id")
            or getattr(self._param, "connection_id", "")
            or None
        )
        ok, connection = CRMConnectionService.resolve_active_connection(tenant_id, conn_id)
        if not ok or not connection:
            err_msg = f"No active CRM connection found for tenant '{tenant_id}'."
            self.set_output("formalized_content", err_msg)
            self.set_output("json", [])
            return {"status": "error", "message": err_msg}

        decrypted_config = CRMConnectionService.get_decrypted_config(connection)
        crm_type = connection.crm_type
        logger.info(
            "QueryCRMRecords invoking provider: crm_type=%s, entity=%s, query='%s', status='%s', limit=%d",
            crm_type, entity, query, status, limit
        )

        # 5. Check in-memory short-term cache
        cache_key = f"{tenant_id}:{connection.id}:{entity}:{query}:{status}:{limit}"
        now = time.time()
        if cache_key in _QUERY_CACHE:
            ts, cached_records = _QUERY_CACHE[cache_key]
            if now - ts < _CACHE_TTL_SECONDS:
                logger.debug("Serving CRM query from short-term cache: key=%s", cache_key)
                records = cached_records
            else:
                records = None
        else:
            records = None

        if records is None:
            provider = CRMProviderRegistry.get(crm_type)
            filters: Dict[str, Any] = {}
            if status:
                filters["status"] = status
            if parsed_sql.get("min_price") is not None:
                filters["min_price"] = parsed_sql["min_price"]
            if parsed_sql.get("max_price") is not None:
                filters["max_price"] = parsed_sql["max_price"]

            records = provider.query_records(
                connection_config=decrypted_config,
                entity=str(entity),
                query=str(query or ""),
                filters=filters,
                limit=limit,
            )
            # Store in cache
            _QUERY_CACHE[cache_key] = (now, records)

        if not records:
            empty_msg = f"No {entity} records found in {crm_type} matching query '{query}'."
            self.set_output("json", [])
            self.set_output("formalized_content", empty_msg)
            return self.output("formalized_content")

        # 6. Apply in-memory sorting if requested by SQL ORDER BY
        order_col = parsed_sql.get("order_by")
        if order_col:
            reverse = parsed_sql.get("order_direction", "desc") == "desc"
            try:
                records = sorted(
                    records,
                    key=lambda r: (r.get(order_col) is None, r.get(order_col) or 0),
                    reverse=reverse,
                )
            except Exception:
                pass

        # 7. Handle SQL Aggregate queries (COUNT, SUM, AVG, MIN, MAX)
        aggregate = parsed_sql.get("aggregate")
        if aggregate:
            if aggregate == "count":
                count_val = len(records)
                agg_df = pd.DataFrame([{"Count": count_val}])
                agg_markdown = agg_df.to_markdown(index=False)
                self.set_output("json", [{"count": count_val}])
                self.set_output("formalized_content", agg_markdown)
                return self.output("formalized_content")

            elif aggregate in ("sum", "avg", "min", "max"):
                # Extract numeric prices
                prices = []
                currency = "RUB"
                for r in records:
                    p = r.get("price")
                    if p is not None:
                        try:
                            prices.append(float(p))
                            if r.get("currency"):
                                currency = r["currency"]
                        except (ValueError, TypeError):
                            pass
                if not prices:
                    res_val = 0.0
                elif aggregate == "sum":
                    res_val = sum(prices)
                elif aggregate == "avg":
                    res_val = sum(prices) / len(prices)
                elif aggregate == "min":
                    res_val = min(prices)
                elif aggregate == "max":
                    res_val = max(prices)

                agg_col_name = f"{aggregate.upper()} ({currency})"
                agg_df = pd.DataFrame([{agg_col_name: round(res_val, 2)}])
                agg_markdown = agg_df.to_markdown(index=False)
                self.set_output("json", [{aggregate: res_val, "currency": currency}])
                self.set_output("formalized_content", agg_markdown)
                return self.output("formalized_content")

        # 8. Format Markdown output and structured JSON with column projections
        display_columns = ["id", "title", "status", "price", "phone", "email", "updated_at"]
        req_columns = parsed_sql.get("columns", [])
        if req_columns:
            # Map requested columns
            selected_display_cols = [c for c in req_columns if c in display_columns]
            if selected_display_cols:
                display_columns = selected_display_cols

        clean_rows = []
        for r in records:
            row = {}
            for col in display_columns:
                row[col] = r.get(col, "")
            clean_rows.append(row)

        df = pd.DataFrame(clean_rows)
        rename_map = {
            "id": "ID",
            "title": "Title / Name",
            "status": "Status / Stage",
            "price": "Price",
            "phone": "Phone",
            "email": "Email",
            "updated_at": "Updated At",
        }
        df.rename(columns={k: rename_map[k] for k in display_columns if k in rename_map}, inplace=True)
        # Drop columns that are completely empty
        cols_to_keep = [col for col in df.columns if not (df[col] == "").all() and not df[col].isna().all()]
        if cols_to_keep:
            df = df[cols_to_keep]

        formalized_markdown = df.to_markdown(index=False)
        self.set_output("json", records)
        self.set_output("formalized_content", formalized_markdown)
        return self.output("formalized_content")

    def thoughts(self) -> str:
        return "Querying live CRM records..."
