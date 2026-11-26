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
from api.crm.catalog_profiler import (
    OneCCatalogProfiler,
    DEFAULT_EXCLUDED_WAREHOUSE_KEYWORDS,
    CONFIDENTIAL_PRICE_KEYWORDS,
)
from api.crm.clients.one_c import (
    OneCClient,
    OneCError,
    OneCAuthError,
    OneCConnectionError,
    OneCMethodNotAllowedError,
    ALLOWLIST_CIDR_ENV,
    DEFAULT_TIMEOUT_SECONDS,
)
from common.data_source.onec_connector import OneCConnector
from agent.component.agent_with_tools import Agent, AgentParam
from agent.tools.check_stock import CheckStock, CheckStockParam
from agent.tools.query_crm_records import parse_sql_crm_query
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


# =============================================================================
# 1. Tests for 1C Catalog Profiler & Metadata Discovery Engine
# =============================================================================

class TestOneCCatalogProfiler(unittest.TestCase):
    def test_warehouse_classification_commercial_vs_excluded(self):
        """Verify warehouse classification correctly distinguishes commercial vs defective/technical."""
        # Commercial warehouses
        self.assertFalse(OneCCatalogProfiler.is_warehouse_excluded("Основной склад"))
        self.assertFalse(OneCCatalogProfiler.is_warehouse_excluded("Центральный склад (Москва)"))
        self.assertFalse(OneCCatalogProfiler.is_warehouse_excluded("Торговый зал"))
        self.assertFalse(OneCCatalogProfiler.is_warehouse_excluded("Склад готовой продукции"))
        self.assertFalse(OneCCatalogProfiler.is_warehouse_excluded("Розничный магазин №1"))

        # Excluded / defective / technical warehouses
        self.assertTrue(OneCCatalogProfiler.is_warehouse_excluded("Склад брака"))
        self.assertTrue(OneCCatalogProfiler.is_warehouse_excluded("Отдел рекламаций и возвратов"))
        self.assertTrue(OneCCatalogProfiler.is_warehouse_excluded("Карантинная зона"))
        self.assertTrue(OneCCatalogProfiler.is_warehouse_excluded("Транзитный склад СПБ"))
        self.assertTrue(OneCCatalogProfiler.is_warehouse_excluded("Склад списания"))
        self.assertTrue(OneCCatalogProfiler.is_warehouse_excluded("Defective items storage"))

    def test_price_type_classification_and_confidentiality(self):
        """Verify price type classification and strict blocking of confidential cost prices."""
        # Confidential internal cost prices
        self.assertTrue(OneCCatalogProfiler.is_price_confidential("Закупочная цена"))
        self.assertTrue(OneCCatalogProfiler.is_price_confidential("Себестоимость плановая"))
        self.assertTrue(OneCCatalogProfiler.is_price_confidential("Учетная цена"))
        self.assertTrue(OneCCatalogProfiler.is_price_confidential("Входящая цена поставщика"))
        self.assertEqual(OneCCatalogProfiler.classify_price_type("Закупочная"), "confidential")

        # Customer-facing commercial prices
        self.assertFalse(OneCCatalogProfiler.is_price_confidential("Розничная"))
        self.assertEqual(OneCCatalogProfiler.classify_price_type("Розничная цена"), "retail")
        self.assertEqual(OneCCatalogProfiler.classify_price_type("Интернет-магазин"), "retail")

        self.assertFalse(OneCCatalogProfiler.is_price_confidential("Дилер с НДС"))
        self.assertEqual(OneCCatalogProfiler.classify_price_type("Дилер с НДС"), "dealer")
        self.assertEqual(OneCCatalogProfiler.classify_price_type("Оптовая (крупный опт)"), "dealer")

    def test_discover_warehouses_via_odata(self):
        """Verify warehouse discovery from 1C Catalog_Склады."""
        client = MagicMock()
        client._execute_get.return_value = {
            "value": [
                {"Ref_Key": "wh-01", "Code": "001", "Description": "Основной склад", "ПометкаУдаления": False},
                {"Ref_Key": "wh-02", "Code": "002", "Description": "Склад брака и дефектов", "ПометкаУдаления": False},
                {"Ref_Key": "wh-03", "Code": "003", "Description": "Филиал Ташкент Центр", "ПометкаУдаления": False},
                {"Ref_Key": "wh-04", "Code": "004", "Description": "Архивный склад 2020", "ПометкаУдаления": True},  # Deleted
            ]
        }
        config = {"odata_url": "https://1c.test/odata/standard.odata"}
        wh_info = OneCCatalogProfiler.discover_warehouses(client, config)

        self.assertEqual(len(wh_info["commercial_warehouses"]), 2)
        self.assertIn("Основной склад", wh_info["commercial_names"])
        self.assertIn("Филиал Ташкент Центр", wh_info["commercial_names"])

        self.assertEqual(len(wh_info["excluded_warehouses"]), 1)
        self.assertIn("Склад брака и дефектов", wh_info["excluded_names"])
        self.assertEqual(wh_info["default_warehouse"], "Основной склад")

    def test_discover_price_types_via_odata(self):
        """Verify price types discovery and confidential filtering from 1C Catalog_ВидыЦен."""
        client = MagicMock()
        client._execute_get.return_value = {
            "value": [
                {"Ref_Key": "pt-01", "Code": "P01", "Description": "Закупочная цена", "ПометкаУдаления": False},
                {"Ref_Key": "pt-02", "Code": "P02", "Description": "Себестоимость", "ПометкаУдаления": False},
                {"Ref_Key": "pt-03", "Code": "P03", "Description": "Розничная", "ПометкаУдаления": False},
                {"Ref_Key": "pt-04", "Code": "P04", "Description": "Дилер с НДС", "ПометкаУдаления": False},
            ]
        }
        config = {"odata_url": "https://1c.test/odata/standard.odata"}
        pt_info = OneCCatalogProfiler.discover_price_types(client, config)

        self.assertEqual(len(pt_info["confidential_price_types"]), 2)
        self.assertIn("Закупочная цена", pt_info["confidential_names"])
        self.assertIn("Себестоимость", pt_info["confidential_names"])

        self.assertEqual(len(pt_info["allowed_price_types"]), 2)
        self.assertIn("Розничная", pt_info["allowed_names"])
        self.assertIn("Дилер с НДС", pt_info["allowed_names"])
        self.assertEqual(pt_info["default_price_type"], "Розничная")

    def test_discover_category_tree_hierarchy(self):
        """Verify building category breadcrumbs from Catalog_Номенклатура folder structure."""
        client = MagicMock()
        client._execute_get.return_value = {
            "value": [
                {"Ref_Key": "cat-root", "Parent_Key": "", "Description": "Электроника", "ПометкаУдаления": False},
                {"Ref_Key": "cat-sub", "Parent_Key": "cat-root", "Description": "Аудиотехника", "ПометкаУдаления": False},
                {"Ref_Key": "cat-leaf", "Parent_Key": "cat-sub", "Description": "Беспроводные наушники", "ПометкаУдаления": False},
            ]
        }
        config = {"odata_url": "https://1c.test/odata/standard.odata"}
        tree = OneCCatalogProfiler.discover_category_tree(client, config)

        self.assertEqual(tree["cat-root"], "Электроника")
        self.assertEqual(tree["cat-sub"], "Электроника / Аудиотехника")
        self.assertEqual(tree["cat-leaf"], "Электроника / Аудиотехника / Беспроводные наушники")


# =============================================================================
# 2. Tests for Hardened 1C Client with Warehouse & Price Resolution
# =============================================================================

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
            "filter_fields": ["Номенклатура/Description", "Номенклатура/Code", "Номенклатура/Артикул"],
            "currency": "UZS",
        }

    def tearDown(self):
        os.environ.pop(ALLOWLIST_CIDR_ENV, None)

    # -------------------------------------------------------------------------
    # T6.2: Restrict HTTP methods strictly to GET
    # -------------------------------------------------------------------------
    def test_strict_get_method_enforced_and_mutations_rejected(self):
        """Verify client uses strictly GET and rejects mutation attempts (POST, PUT, DELETE)."""
        for mutating_method in ("POST", "PUT", "PATCH", "DELETE"):
            with self.assertRaises(OneCMethodNotAllowedError) as ctx:
                self.client.execute_mutating_request(mutating_method)
            self.assertIn("strictly prohibited", str(ctx.exception))
            self.assertIn(mutating_method, str(ctx.exception))

        self.mock_transport.get.return_value = DummyResponse(200, json_data={"value": []})
        self.client.check_stock(self.valid_config, "SKU-1001")
        self.assertEqual(self.mock_transport.get.call_count, 1)

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
    # Commercial vs Defective Warehouse Separation
    # -------------------------------------------------------------------------
    def test_check_stock_separates_commercial_and_defective_warehouses(self):
        """Verify check_stock aggregates commercial stock and separates out defective warehouses."""
        mock_odata_response = {
            "value": [
                {
                    "SKU": "ART-8899",
                    "Description": "Wireless Mechanical Keyboard",
                    "Warehouse": "Основной склад",
                    "Quantity": 15.0,
                    "Price": 4500.0,
                },
                {
                    "SKU": "ART-8899",
                    "Description": "Wireless Mechanical Keyboard",
                    "Warehouse": "Филиал Петербург",
                    "Quantity": 7.0,
                    "Price": 4500.0,
                },
                {
                    "SKU": "ART-8899",
                    "Description": "Wireless Mechanical Keyboard",
                    "Warehouse": "Склад Брака и Дефектов",
                    "Quantity": 3.0,
                    "Price": 4500.0,
                },
            ],
        }
        self.mock_transport.get.return_value = DummyResponse(200, json_data=mock_odata_response)

        res = self.client.check_stock(self.valid_config, "ART-8899")
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["query"], "ART-8899")
        # Commercial stock must sum ONLY commercial warehouses (15 + 7 = 22)
        self.assertEqual(res["commercial_stock"], 22.0)
        self.assertEqual(res["total_stock"], 22.0)
        # Excluded defective stock must be captured separately (3.0)
        self.assertEqual(res["excluded_stock"], 3.0)
        self.assertTrue(res["is_available"])

        breakdown = res["warehouses_breakdown"]
        self.assertEqual(len(breakdown), 3)
        self.assertTrue(breakdown[0]["is_commercial"])
        self.assertTrue(breakdown[1]["is_commercial"])
        self.assertFalse(breakdown[2]["is_commercial"])
        self.assertIn("excluded", breakdown[2]["status"])

    # -------------------------------------------------------------------------
    # Real-Time Price Resolution & Confidential Price Blocking
    # -------------------------------------------------------------------------
    def test_check_stock_resolves_price_from_price_register_when_zero(self):
        """Verify check_stock resolves price from InformationRegister_ЦеныНоменклатурыСрезПоследних."""
        # Stock balance register returns 0 price (standard 1C behavior)
        stock_resp = DummyResponse(200, json_data={
            "value": [
                {
                    "SKU": "IPHONE-15-PRO",
                    "Description": "iPhone 15 Pro",
                    "Warehouse": "Центральный склад",
                    "Quantity": 42.0,
                    "Price": 0.0,
                }
            ]
        })
        # Price register returns resolved price for target price type
        price_resp = DummyResponse(200, json_data={
            "value": [
                {
                    "Номенклатура/Description": "iPhone 15 Pro",
                    "ВидЦены/Description": "Розничная",
                    "Цена": 14500000.0,
                    "Валюта/Description": "UZS",
                }
            ]
        })

        self.mock_transport.get.side_effect = [stock_resp, price_resp]

        res = self.client.check_stock(self.valid_config, "IPHONE-15-PRO", price_type="Розничная")
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["commercial_stock"], 42.0)
        self.assertEqual(res["price"], 14500000.0)
        self.assertEqual(res["currency"], "UZS")
        self.assertEqual(res["price_type"], "Розничная")

    def test_check_stock_strictly_blocks_confidential_price_types(self):
        """Verify check_stock rejects confidential purchase/cost price types."""
        with self.assertRaises(OneCError) as ctx:
            self.client.check_stock(self.valid_config, "IPHONE-15-PRO", price_type="Закупочная")
        self.assertIn("confidential internal cost data", str(ctx.exception))

        with self.assertRaises(OneCError) as ctx:
            self.client.check_stock(self.valid_config, "IPHONE-15-PRO", price_type="Себестоимость")
        self.assertIn("confidential internal cost data", str(ctx.exception))

    def test_query_records_product_excludes_deleted_and_folders(self):
        """Verify query_records for products excludes deleted items and folders."""
        from urllib.parse import unquote
        self.mock_transport.get.return_value = DummyResponse(200, json_data={"value": []})
        self.client.query_records(self.valid_config, entity="product", query="MacBook")

        sent_url = unquote(self.mock_transport.get.call_args[0][0])
        self.assertIn("Catalog_Номенклатура", sent_url)
        self.assertIn("ПометкаУдаления eq false", sent_url)
        self.assertIn("IsFolder eq false", sent_url)

    def test_query_records_rejects_confidential_price_type_in_filters(self):
        """Verify query_records rejects confidential price type filter."""
        with self.assertRaises(OneCError) as ctx:
            self.client.query_records(
                self.valid_config,
                entity="product",
                filters={"price_type": "Закупочная"},
            )
        self.assertIn("confidential internal cost data", str(ctx.exception))

    def test_check_stock_empty_results(self):
        """Verify response when item has zero stock or is not found in 1C."""
        self.mock_transport.get.return_value = DummyResponse(200, json_data={"value": []})

        res = self.client.check_stock(self.valid_config, "NON-EXISTENT-SKU")
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["total_stock"], 0.0)
        self.assertEqual(res["commercial_stock"], 0.0)
        self.assertFalse(res["is_available"])
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


# =============================================================================
# 3. Tests for CheckStock Tool Component
# =============================================================================

class TestCheckStockTool(unittest.TestCase):
    def setUp(self):
        warnings.filterwarnings("ignore", category=ResourceWarning)
        self.test_db = SqliteDatabase("file:crm_1c_tool_mem?mode=memory&cache=shared", uri=True)
        self._orig_db_conn = CRMConnection._meta.database
        self._orig_db_outbox = CRMOutbox._meta.database
        self._orig_db_atomic = DB.atomic
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

        conn = CRMConnectionService.save_connection(
            tenant_id=self.tenant_id,
            name="Primary 1C ERP",
            crm_type="1c_odata",
            auth_type="basic",
            config={
                "odata_url": "https://1c.company.local/trade/odata/standard.odata",
                "username": "stock_bot",
                "password": "bot_password",
                "filter_fields": ["Номенклатура/Description", "Номенклатура/Code"],
            },
        )
        self.connection = conn
        self.valid_config = {
            "odata_url": "https://1c.company.local/trade/odata/standard.odata",
            "username": "stock_bot",
            "password": "bot_password",
            "filter_fields": ["Номенклатура/Description", "Номенклатура/Code"],
        }

    def tearDown(self):
        CRMConnection._meta.database = self._orig_db_conn
        CRMOutbox._meta.database = self._orig_db_outbox
        DB.atomic = self._orig_db_atomic
        if not self.test_db.is_closed():
            self.test_db.close()

    def _create_tool(self, canvas, allow_anonymous=False, connection_id=None, enable_experimental=True):
        param = CheckStockParam()
        param.allow_anonymous = allow_anonymous
        param.connection_id = self.connection.id if connection_id is None else connection_id
        param.enable_1c_experimental = enable_experimental

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
        self.assertIn("warehouse", meta["function"]["parameters"]["properties"])
        self.assertIn("price_type", meta["function"]["parameters"]["properties"])

        form = param.get_input_form()
        self.assertIn("query", form)
        self.assertIn("warehouse", form)
        self.assertIn("price_type", form)

    def test_check_stock_tool_invokes_with_price_type_and_warehouse(self):
        """Verify CheckStock tool passes warehouse and price_type to OneCClient."""
        canvas = DummyMockCanvas(tenant_id=self.tenant_id, channel="chat")
        tool = self._create_tool(canvas)

        mock_stock_res = {
            "status": "success",
            "query": "iPhone 15 Pro",
            "warehouse": "Ташкент Склад 1",
            "total_stock": 42.0,
            "commercial_stock": 42.0,
            "excluded_stock": 0.0,
            "price": 14500000.0,
            "currency": "UZS",
            "price_type": "Дилер с НДС",
            "is_available": True,
            "items": [],
        }

        with patch.object(OneCClient, "check_stock", return_value=mock_stock_res) as mock_cs:
            res = tool._invoke(query="iPhone 15 Pro", warehouse="Ташкент Склад 1", price_type="Дилер с НДС")
            self.assertEqual(res["status"], "success")
            self.assertEqual(res["commercial_stock"], 42.0)
            self.assertEqual(res["price"], 14500000.0)
            mock_cs.assert_called_once()
            call_kwargs = mock_cs.call_args[1]
            self.assertEqual(call_kwargs.get("warehouse"), "Ташкент Склад 1")
            self.assertEqual(call_kwargs.get("price_type"), "Дилер с НДС")


# =============================================================================
# 4. Tests for OneCConnector RAG Knowledge Base Indexing
# =============================================================================

class TestOneCConnector(unittest.TestCase):
    def test_onec_connector_formats_markdown_with_category_breadcrumbs(self):
        """Verify OneCConnector formats catalog markdown with category breadcrumbs without volatile prices."""
        conn = OneCConnector(
            base_url="https://1c.example.com/trade/odata/standard.odata",
            username="sync_user",
            password="sync_password",
        )
        item = {
            "Ref_Key": "prod-1001",
            "Code": "APL-15P",
            "Артикул": "A2848",
            "Description": "iPhone 15 Pro 256GB",
            "Единица": "шт",
            "Цена": 14500000,          # Volatile - should be omitted from static KB doc
            "КоличествоОстаток": 42,   # Volatile - should be omitted from static KB doc
        }
        category_breadcrumb = "Смартфоны / Apple / iPhone"

        md = conn._format_item_text("Catalog_Номенклатура", item, category_breadcrumb=category_breadcrumb)
        self.assertIn("# 1С Catalog_Номенклатура: iPhone 15 Pro 256GB", md)
        self.assertIn("- **Категория**: Смартфоны / Apple / iPhone", md)
        self.assertIn("- **Артикул/Код**: A2848", md)
        # Verify static KB doc omits raw volatile price/stock and includes API notice
        self.assertNotIn("- **Цена**", md)
        self.assertNotIn("- **КоличествоОстаток**", md)
        self.assertIn("Остатки на складах и актуальные цены запрашиваются в реальном времени через 1C API", md)


# =============================================================================
# 5. Tests for QueryCRMRecords SQL Parser Warehouse and Price Type
# =============================================================================

class TestQueryCRMRecordsParser(unittest.TestCase):
    def test_sql_parser_extracts_warehouse_and_price_type(self):
        """Verify parse_sql_crm_query extracts warehouse and price_type filters from SQL."""
        sql = "SELECT id, title, price FROM product WHERE warehouse = 'Основной склад' AND price_type = 'Дилер с НДС' AND price >= 1000000 LIMIT 5;"
        parsed = parse_sql_crm_query(sql)

        self.assertEqual(parsed["entity"], "product")
        self.assertEqual(parsed["warehouse"], "Основной склад")
        self.assertEqual(parsed["price_type"], "Дилер с НДС")
        self.assertEqual(parsed["min_price"], 1000000.0)
        self.assertEqual(parsed["limit"], 5)


if __name__ == "__main__":
    unittest.main()
