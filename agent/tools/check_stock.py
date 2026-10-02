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
import os
import re
from abc import ABC
from typing import Any, Dict

from agent.tools.base import ToolParamBase, ToolBase, ToolMeta
from common.connection_utils import timeout
from api.db.services.crm_service import CRMConnectionService
from api.db.crm_models import CRMConnection
from api.crm.clients.one_c import OneCClient

logger = logging.getLogger("CheckStock")


class CheckStockParam(ToolParamBase):
    """Configuration parameters for CheckStock tool component."""

    def __init__(self):
        self.meta: ToolMeta = {
            "name": "check_stock",
            "description": "Queries product inventory balances and stock levels across warehouses from 1C:Enterprise over OData. Invoke this tool when a customer asks about product availability, stock count, or warehouse balances.",
            "parameters": {
                "query": {
                    "type": "string",
                    "description": "Product SKU, article code, or item name to check availability for.",
                    "default": "{sys.query}",
                    "required": True,
                },
                "warehouse": {
                    "type": "string",
                    "description": "Optional specific warehouse name or code to filter balances.",
                    "default": "",
                    "required": False,
                },
            },
        }
        super().__init__()
        self.connection_id = ""
        self.allow_anonymous = False

    def check(self):
        pass

    def get_input_form(self) -> dict[str, dict]:
        return {
            "query": {"name": "Product SKU or Name", "type": "line"},
            "warehouse": {"name": "Warehouse", "type": "line"},
        }


class CheckStock(ToolBase, ABC):
    component_name = "CheckStock"

    @timeout(int(os.environ.get("COMPONENT_EXEC_TIMEOUT", 10)))
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
        if self.check_if_canceled("CheckStock processing"):
            return {"status": "canceled"}

        # 1. Scoped anonymous access enforcement (T6.4)
        channel = getattr(self._canvas, "get_channel", lambda: None)()
        if not channel and hasattr(self._canvas, "custom_header") and isinstance(self._canvas.custom_header, dict):
            channel = self._canvas.custom_header.get("channel") or self._canvas.custom_header.get("auth_type")
        is_anon = str(channel).lower() in ("webhook", "embed", "beta", "auth_beta", "anonymous")
        if is_anon and not getattr(self._param, "allow_anonymous", False):
            raise PermissionError(
                "Access denied: Stock checking from anonymous/public channels is forbidden unless 'allow_anonymous' is enabled in tool configuration."
            )

        # 2. Parameter validation and sanitization
        raw_query = kwargs.get("query") or kwargs.get("sku") or kwargs.get("item") or ""
        clean_query = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", str(raw_query).strip())[:128]
        if not clean_query:
            raise ValueError("Missing required parameter 'query' (product SKU, article code, or item name).")

        raw_wh = kwargs.get("warehouse") or ""
        clean_wh = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", str(raw_wh).strip())[:128]

        # 3. Connection resolution
        tenant_id = getattr(self._canvas, "get_tenant_id", lambda: None)()
        if not tenant_id and hasattr(self._canvas, "get_canvas_owner_tenant"):
            tenant_id = self._canvas.get_canvas_owner_tenant()
        if not tenant_id:
            raise ValueError("Canvas context missing valid tenant ID.")

        conn_id = getattr(self._param, "connection_id", "") or kwargs.get("connection_id") or ""
        conn = None
        if conn_id:
            ok, conn = CRMConnectionService.get_by_id_and_tenant(conn_id, tenant_id)
            if not ok or not conn:
                raise ValueError(f"Configured 1C connection '{conn_id}' was not found or belongs to another tenant.")
        else:
            connections = CRMConnectionService.query_by_tenant(tenant_id, status="active")
            for c in connections:
                if c.crm_type in ("1c", "1c_odata"):
                    conn = c
                    break

        if not conn:
            raise ValueError("No active 1C:Enterprise connection found for tenant.")
        if conn.status != "active":
            raise ValueError(f"1C:Enterprise connection '{conn.id}' is inactive (status={conn.status}).")

        # 4. Decrypt config and execute read-only stock query
        config = CRMConnectionService.get_decrypted_config(conn.id, tenant_id)
        client = OneCClient()
        result = client.check_stock(config, clean_query, clean_wh or None)
        return result
