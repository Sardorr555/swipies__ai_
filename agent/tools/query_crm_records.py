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
from abc import ABC
from typing import Any, Dict, List, Optional

import pandas as pd

from agent.tools.base import ToolParamBase, ToolBase, ToolMeta
from common.connection_utils import timeout
from api.db.crm_models import CRMConnection
from api.db.services.crm_service import CRMConnectionService
from api.crm.base import CRMProviderRegistry

logger = logging.getLogger("QueryCRMRecords")


def parse_sql_crm_query(sql: str) -> Dict[str, Any]:
    """Parse a natural SQL query into CRM entity, query string, status, and limit."""
    parsed: Dict[str, Any] = {
        "entity": "deal",
        "query": "",
        "status": "",
        "limit": 10,
    }
    if not sql or not isinstance(sql, str):
        return parsed

    clean_sql = sql.strip().rstrip(";")
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

    limit_match = re.search(r"\bLIMIT\s+(\d+)", clean_sql, re.IGNORECASE)
    if limit_match:
        try:
            parsed["limit"] = int(limit_match.group(1))
        except Exception:
            pass

    # Extract status / stage
    status_match = re.search(r"(?:status|stage|статус|состояние)\s*(?:=|is|like)\s*['\"]([^'\"]+)['\"]", clean_sql, re.IGNORECASE)
    if status_match:
        parsed["status"] = status_match.group(1).strip()

    # Extract general search term / name / query / phone
    q_match = re.search(r"(?:name|title|query|phone|description|наименование|название|телефон)\s*(?:=|like)\s*['\"]%?([^'\"%]+)%?['\"]", clean_sql, re.IGNORECASE)
    if q_match:
        parsed["query"] = q_match.group(1).strip()
    elif not parsed["status"]:
        # Check where clause content
        where_match = re.search(r"\bWHERE\s+(.+)$", clean_sql, re.IGNORECASE)
        if where_match:
            raw_where = where_match.group(1)
            raw_text = re.sub(r"[=><'\"]", " ", raw_where)
            tokens = [t.strip() for t in raw_text.split() if len(t.strip()) > 2 and t.lower() not in ("and", "or", "not", "where", "like", "is", "null", "limit")]
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
                    "description": "Optional natural SQL-style query (e.g. \"SELECT * FROM deals WHERE status = 'WON'\"). If supplied, table name and filters are extracted automatically.",
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

        # 5. Execute query via provider registry
        provider = CRMProviderRegistry.get(crm_type)
        filters: Dict[str, Any] = {}
        if status:
            filters["status"] = status

        records = provider.query_records(
            connection_config=decrypted_config,
            entity=str(entity),
            query=str(query or ""),
            filters=filters,
            limit=limit,
        )

        if not records:
            empty_msg = f"No {entity} records found in {crm_type} matching query '{query}'."
            self.set_output("json", [])
            self.set_output("formalized_content", empty_msg)
            return self.output("formalized_content")

        # 6. Format Markdown output and structured JSON
        display_columns = ["id", "title", "status", "price", "phone", "email", "updated_at"]
        clean_rows = []
        for r in records:
            row = {}
            for col in display_columns:
                row[col] = r.get(col, "")
            clean_rows.append(row)

        df = pd.DataFrame(clean_rows)
        # Rename columns for clear display
        rename_map = {
            "id": "ID",
            "title": "Title / Name",
            "status": "Status / Stage",
            "price": "Price",
            "phone": "Phone",
            "email": "Email",
            "updated_at": "Updated At",
        }
        df.rename(columns=rename_map, inplace=True)
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
