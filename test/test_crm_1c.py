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
import os
import socket
import sys
import unittest
import warnings
from typing import Any, Dict
from unittest.mock import MagicMock, patch

# Suppress version drift warnings and in-memory SQLite resource warnings
warnings.filterwarnings("ignore", message=".*doesn't match a supported version.*")
warnings.filterwarnings("ignore", category=ResourceWarning)

# Pre-mock heavy modules for clean import without ML dependencies
sys.modules.setdefault("api.db.services.dialog_service", MagicMock())
sys.modules.setdefault("xgboost", MagicMock())
sys.modules.setdefault("pypdf", MagicMock())
sys.modules.setdefault("api.db.services.file_service", MagicMock())
sys.modules.setdefault("api.db.services.task_service", MagicMock())

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from common import settings
settings.init_settings = lambda *a, **kw: None

from peewee import SqliteDatabase
from api.db.db_models import DB
from api.db.crm_models import CRMConnection, CRMOutbox

DB.connection_context = lambda: (lambda fn: fn)
DB.connect = lambda *a, **kw: True
DB.close = lambda *a, **kw: None
DB.is_closed = lambda: False

from api.db.services.crm_service import CRMConnectionService
from api.crm.base import CRMProviderRegistry
from api.crm.transport import CRMTransport, SSRFSecurityException
from api.crm.clients.one_c import (
    OneCClient,
    OneCError,
    OneCAuthError,
    OneCConnectionError,
    OneCMethodNotAllowedError,
    ALLOWLIST_CIDR_ENV,
    DEFAULT_TIMEOUT_SECONDS,
)
from agent.component.agent_with_tools import Agent, AgentParam
from agent.tools.check_stock import CheckStock, CheckStockParam
from agent.canvas import Canvas


class DummyResponse:
    """Mock HTTP response object."""
    def __init__(self, status_code: int = 200, json_data: Any = None, text: str = ""):
        self.status_code = status_code
        self._json_data = json_data
        self.text = text or (str(json_data) if json_data is not None else "")

    def json(self):
        if self._json_data is not None:
            return self._json_data
        raise ValueError("Invalid JSON in response")


class DummyMockCanvas(Canvas):
    """Mock Canvas context satisfying ToolBase protocol."""
    def __init__(self, tenant_id="tenant-test-1c", channel=None, custom_header=None):
        self._tenant_id = tenant_id
        self._canvas_owner_tenant = tenant_id
        self._channel = channel
        self.custom_header = custom_header or {}
        self.task_id = "test-1c-task-id"
        self.dsl = {"components": {}, "history": [], "path": []}
        self.components = {}

    def is_canceled(self):
        return False

    def get_tenant_id(self):
        return self._tenant_id

    def get_canvas_owner_tenant(self):
        return self._tenant_id

    def get_channel(self):
        return self._channel


class TestOneCClient(unittest.TestCase):
    def setUp(self):
        warnings.filterwarnings("ignore", category=ResourceWarning)
        self.mock_transport = MagicMock(spec=CRMTransport)
        self.client = OneCClient(transport=self.mock_transport)
        self.valid_config = {
            "odata_url": "https://1c.enterprise.local/trade/odata/standard.odata",
            "username": "api_user",
            "password": "api_password",
            "entity_path": "AccumulationRegister_ТоварыНаСкладах/Balance",
        }

    def tearDown(self):
        os.environ.pop(ALLOWLIST_CIDR_ENV, None)

    # -------------------------------------------------------------------------
    # T6.2: Restrict HTTP methods strictly to GET
    # -------------------------------------------------------------------------
    def test_strict_get_method_enforced_and_mutations_rejected(self):
        """Verify client uses strictly GET and rejects mutation attempts (POST, PUT, DELETE)."""
        # Calling execute_mutating_request with POST must raise OneCMethodNotAllowedError
        for mutating_method in ("POST", "PUT", "PATCH", "DELETE"):
            with self.assertRaises(OneCMethodNotAllowedError) as ctx:
                self.client.execute_mutating_request(mutating_method)
            self.assertIn("strictly prohibited", str(ctx.exception))
            self.assertIn(mutating_method, str(ctx.exception))

        # Normal check_stock only calls transport.get
        self.mock_transport.get.return_value = DummyResponse(200, json_data={"value": []})
        self.client.check_stock(self.valid_config, "SKU-1001")
        self.assertEqual(self.mock_transport.get.call_count, 1)
        self.assertEqual(self.mock_transport.post.call_count, 0)
        self.assertEqual(self.mock_transport.put.call_count, 0)
        self.assertEqual(self.mock_transport.delete.call_count, 0)

    # -------------------------------------------------------------------------
    # T6.3: Strict 5-second timeout and SSRF guard with private CIDR allowlist
    # -------------------------------------------------------------------------
    def test_default_timeout_is_5_seconds(self):
        """Verify strict 5-second timeout enforcement."""
        self.assertEqual(DEFAULT_TIMEOUT_SECONDS, 5.0)
        default_client = OneCClient()
        self.assertEqual(default_client.transport.default_timeout, 5.0)

    def test_ssrf_private_ips_blocked_fail_closed_by_default(self):
        """Verify private and reserved IPs fail closed without allowlist."""
        real_transport = CRMTransport(
            private_cidr_allowlist_env=ALLOWLIST_CIDR_ENV,
            allowed_schemes=frozenset({"http", "https"}),
            default_timeout=5.0,
        )
        real_client = OneCClient(transport=real_transport)

        private_urls = [
            "https://127.0.0.1/odata/standard.odata/",
            "https://10.0.0.1/odata/standard.odata/",
            "https://192.168.1.100/odata/standard.odata/",
            "https://172.16.0.5/odata/standard.odata/",
            "https://169.254.169.254/odata/standard.odata/",
        ]
        for url in private_urls:
            cfg = dict(self.valid_config, odata_url=url)
            with self.assertRaises(SSRFSecurityException) as ctx:
                real_client.check_stock(cfg, "SKU-1001")
            self.assertIn("SSRF guard blocked access", str(ctx.exception))

    def test_ssrf_private_ip_allowed_when_in_platform_admin_allowlist(self):
        """Verify private IP is permitted when present in RAGFLOW_CRM_1C_ALLOWLIST_CIDR."""
        os.environ[ALLOWLIST_CIDR_ENV] = "192.168.1.0/24, 10.50.0.0/16"
        real_transport = CRMTransport(
            private_cidr_allowlist_env=ALLOWLIST_CIDR_ENV,
            allowed_schemes=frozenset({"http", "https"}),
            default_timeout=5.0,
        )

        with patch("socket.getaddrinfo") as mock_dns, patch.object(real_transport.session, "request") as mock_req:
            # Simulate DNS resolving 1c-internal.local to 192.168.1.55
            mock_dns.return_value = [
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.168.1.55", 0))
            ]
            mock_req.return_value = DummyResponse(200, json_data={"value": []})

            client = OneCClient(transport=real_transport)
            cfg = dict(self.valid_config, odata_url="https://1c-internal.local/trade/odata/standard.odata")
            res = client.check_stock(cfg, "SKU-1001")
            self.assertEqual(res["status"], "success")
            self.assertEqual(res["total_stock"], 0.0)

    # -------------------------------------------------------------------------
    # T6.5: Unit tests for stock checking with mock 1C OData responses
    # -------------------------------------------------------------------------
    def test_check_stock_successful_response_parsing(self):
        """Verify parsing 1C OData JSON response with multiple items and warehouses."""
        mock_odata_response = {
            "odata.metadata": "https://1c.enterprise.local/trade/odata/standard.odata/$metadata#AccumulationRegister_ТоварыНаСкладах/Balance",
            "value": [
                {
                    "SKU": "ART-8899",
                    "Description": "Wireless Mechanical Keyboard",
                    "Warehouse": "Moscow Central",
                    "Quantity": "15.0",
                    "Price": "4500.0",
                },
                {
                    "Артикул": "ART-8899",
                    "Наименование": "Wireless Mechanical Keyboard",
                    "Склад": "St. Petersburg Branch",
                    "КоличествоОстаток": 7.0,
                    "Цена": 4500.0,
                },
            ],
        }
        self.mock_transport.get.return_value = DummyResponse(200, json_data=mock_odata_response)

        res = self.client.check_stock(self.valid_config, "ART-8899", warehouse="Moscow")
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["query"], "ART-8899")
        self.assertEqual(res["warehouse"], "Moscow")
        self.assertEqual(res["total_stock"], 22.0)
        self.assertEqual(res["item_count"], 2)
        self.assertEqual(res["items"][0]["warehouse"], "Moscow Central")
        self.assertEqual(res["items"][0]["quantity"], 15.0)
        self.assertEqual(res["items"][1]["warehouse"], "St. Petersburg Branch")
        self.assertEqual(res["items"][1]["quantity"], 7.0)

    def test_check_stock_empty_results(self):
        """Verify response when item has zero stock or is not found in 1C."""
        self.mock_transport.get.return_value = DummyResponse(200, json_data={"value": []})

        res = self.client.check_stock(self.valid_config, "NON-EXISTENT-SKU")
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["total_stock"], 0.0)
        self.assertEqual(res["item_count"], 0)
        self.assertEqual(res["items"], [])

    def test_check_stock_401_auth_error(self):
        """Verify HTTP 401 raises OneCAuthError."""
        self.mock_transport.get.return_value = DummyResponse(401, text="Unauthorized: invalid credentials")

        with self.assertRaises(OneCAuthError) as ctx:
            self.client.check_stock(self.valid_config, "SKU-01")
        self.assertIn("authentication failed", str(ctx.exception))

    def test_check_stock_server_error_500(self):
        """Verify HTTP 500 raises OneCError."""
        self.mock_transport.get.return_value = DummyResponse(500, text="Internal Server Error in 1C module")

        with self.assertRaises(OneCError) as ctx:
            self.client.check_stock(self.valid_config, "SKU-01")
        self.assertIn("HTTP 500", str(ctx.exception))

    def test_check_stock_invalid_json(self):
        """Verify malformed non-JSON response raises OneCError."""
        self.mock_transport.get.return_value = DummyResponse(200, json_data=None, text="<html>502 Bad Gateway</html>")

        with self.assertRaises(OneCError) as ctx:
            self.client.check_stock(self.valid_config, "SKU-01")
        self.assertIn("Invalid JSON", str(ctx.exception))

    def test_create_lead_and_find_contact_contract(self):
        """Verify 1C provider contract defaults for lead and contact methods."""
        res_lead = self.client.create_lead(self.valid_config, {"name": "Bob"})
        self.assertFalse(res_lead["supported"])
        self.assertIn("does not support create_lead", res_lead["message"])

        res_contact = self.client.find_contact(self.valid_config, "+14155552671")
        self.assertIsNone(res_contact)

    def test_refresh_auth_validates_metadata(self):
        """Verify refresh_auth validates 1C credentials against $metadata endpoint."""
        self.mock_transport.get.return_value = DummyResponse(200, text="<edmx:Edmx>...</edmx:Edmx>")
        conf = self.client.refresh_auth(self.valid_config)
        self.assertEqual(conf, self.valid_config)

        # 401 on metadata check raises OneCAuthError
        self.mock_transport.get.return_value = DummyResponse(401, text="Unauthorized")
        with self.assertRaises(OneCAuthError):
            self.client.refresh_auth(self.valid_config)

    def test_registry_resolution_for_1c(self):
        """Verify CRMProviderRegistry correctly resolves '1c' and '1c_odata'."""
        CRMProviderRegistry.clear()
        provider_1c = CRMProviderRegistry.get("1c_odata")
        self.assertIsInstance(provider_1c, OneCClient)

        provider_1c_alias = CRMProviderRegistry.get("1c")
        self.assertIsInstance(provider_1c_alias, OneCClient)


class TestCheckStockTool(unittest.TestCase):
    def setUp(self):
        warnings.filterwarnings("ignore", category=ResourceWarning)
        self.test_db = SqliteDatabase("file:crm_1c_tool_mem?mode=memory&cache=shared", uri=True)
        self._orig_db_conn = CRMConnection._meta.database
        self._orig_db_outbox = CRMOutbox._meta.database
        CRMConnection._meta.database = self.test_db
        CRMOutbox._meta.database = self.test_db
        DB.atomic = lambda *args, **kwargs: self.test_db.atomic()
        self.test_db.bind([CRMConnection, CRMOutbox])

        self.test_db.connect()
        self.test_db.create_tables([CRMConnection, CRMOutbox], safe=True)
        CRMConnection.delete().execute()
        CRMOutbox.delete().execute()

        self.tenant_id = "tenant-1c-sales-01"
        self.secret = "crm-super-secret-key-32bytes-ok!"
        os.environ["RAGFLOW_SECRET_KEY"] = self.secret

        # Create active 1C connection
        conn = CRMConnectionService.save_connection(
            tenant_id=self.tenant_id,
            name="Primary 1C ERP",
            crm_type="1c_odata",
            auth_type="basic",
            config={
                "odata_url": "https://1c.company.local/trade/odata/standard.odata",
                "username": "stock_bot",
                "password": "bot_password",
            },
        )
        self.connection = conn

    def tearDown(self):
        CRMConnection._meta.database = self._orig_db_conn
        CRMOutbox._meta.database = self._orig_db_outbox
        if not self.test_db.is_closed():
            self.test_db.close()

    def _create_tool(self, canvas, allow_anonymous=False, connection_id=None):
        param = CheckStockParam()
        param.allow_anonymous = allow_anonymous
        param.connection_id = self.connection.id if connection_id is None else connection_id

        tool = CheckStock(
            canvas=canvas,
            id="tool_stock_01",
            param=param,
        )
        return tool

    def test_param_metadata_and_form(self):
        param = CheckStockParam()
        meta = param.get_meta()
        self.assertEqual(meta["type"], "function")
        self.assertEqual(meta["function"]["name"], "check_stock")
        self.assertIn("query", meta["function"]["parameters"]["properties"])

        form = param.get_input_form()
        self.assertIn("query", form)
        self.assertIn("warehouse", form)

    def test_missing_query_rejected(self):
        canvas = DummyMockCanvas(tenant_id=self.tenant_id, channel="chat")
        tool = self._create_tool(canvas)

        with self.assertRaises(ValueError) as ctx:
            tool._invoke(query="")
        self.assertIn("Missing required parameter 'query'", str(ctx.exception))

    # -------------------------------------------------------------------------
    # T6.4: Least privilege: accessible from anonymous channels only when allowed
    # -------------------------------------------------------------------------
    def test_scoped_anonymous_access_rejected_when_not_allowed(self):
        """Anonymous channels (webhook, embed, beta) are blocked when allow_anonymous=False."""
        anonymous_channels = ["webhook", "embed", "beta", "auth_beta", "anonymous"]

        for chan in anonymous_channels:
            canvas = DummyMockCanvas(tenant_id=self.tenant_id, channel=chan)
            tool = self._create_tool(canvas, allow_anonymous=False)

            with self.assertRaises(PermissionError) as ctx:
                tool._invoke(query="SKU-1001")
            self.assertIn("Stock checking from anonymous/public channels is forbidden", str(ctx.exception))

    def test_scoped_anonymous_access_allowed_when_configured(self):
        """Anonymous channels succeed when allow_anonymous=True."""
        canvas = DummyMockCanvas(tenant_id=self.tenant_id, channel="webhook")
        tool = self._create_tool(canvas, allow_anonymous=True)

        mock_stock_res = {
            "status": "success",
            "query": "SKU-1001",
            "warehouse": "",
            "total_stock": 50.0,
            "item_count": 1,
            "items": [{"sku": "SKU-1001", "name": "Test Item", "warehouse": "Main", "quantity": 50.0, "price": 100.0}],
        }
        with patch.object(OneCClient, "check_stock", return_value=mock_stock_res):
            res = tool._invoke(query="SKU-1001")
            self.assertEqual(res["status"], "success")
            self.assertEqual(res["total_stock"], 50.0)

    def test_authenticated_access_always_allowed(self):
        """Authenticated chat sessions always succeed regardless of allow_anonymous."""
        canvas = DummyMockCanvas(tenant_id=self.tenant_id, channel="chat")
        tool = self._create_tool(canvas, allow_anonymous=False)

        mock_stock_res = {
            "status": "success",
            "query": "SKU-2002",
            "warehouse": "Depot",
            "total_stock": 10.0,
            "item_count": 1,
            "items": [{"sku": "SKU-2002", "name": "Widget", "warehouse": "Depot", "quantity": 10.0, "price": 20.0}],
        }
        with patch.object(OneCClient, "check_stock", return_value=mock_stock_res):
            res = tool._invoke(query="SKU-2002", warehouse="Depot")
            self.assertEqual(res["status"], "success")
            self.assertEqual(res["total_stock"], 10.0)

    def test_connection_resolution_auto_and_explicit(self):
        """Tool resolves connection explicitly or automatically finds tenant active 1c_odata."""
        canvas = DummyMockCanvas(tenant_id=self.tenant_id, channel="chat")

        # 1. Auto-resolution without connection_id
        tool_auto = self._create_tool(canvas, connection_id="")
        with patch.object(OneCClient, "check_stock", return_value={"status": "success", "total_stock": 5.0}) as mock_cs:
            res = tool_auto._invoke(query="SKU-AUTO")
            self.assertEqual(res["status"], "success")
            self.assertEqual(mock_cs.call_count, 1)

        # 2. Non-existent connection ID raises ValueError
        tool_bad_id = self._create_tool(canvas, connection_id="invalid-conn-id")
        with self.assertRaises(ValueError) as ctx:
            tool_bad_id._invoke(query="SKU-1001")
        self.assertIn("Configured 1C connection 'invalid-conn-id' was not found", str(ctx.exception))

        # 3. No active connections raises ValueError
        CRMConnection.delete().execute()
        tool_empty = self._create_tool(canvas, connection_id="")
        with self.assertRaises(ValueError) as ctx:
            tool_empty._invoke(query="SKU-1001")
        self.assertIn("No active 1C:Enterprise connection found for tenant", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
