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
import sys
import unittest
import warnings
from unittest.mock import MagicMock, patch

sys.modules.setdefault("api.db.services.dialog_service", MagicMock())
sys.modules.setdefault("xgboost", MagicMock())
sys.modules.setdefault("pypdf", MagicMock())
sys.modules.setdefault("api.db.services.file_service", MagicMock())
sys.modules.setdefault("api.db.services.task_service", MagicMock())

warnings.filterwarnings("ignore", message=".*doesn't match a supported version.*")
warnings.filterwarnings("ignore", category=ResourceWarning)

from peewee import SqliteDatabase
from api.db.db_models import DB

DB.connection_context = lambda: (lambda fn: fn)
DB.connect = lambda *a, **kw: True
DB.close = lambda *a, **kw: None
DB.is_closed = lambda: False

from api.db.crm_models import CRMConnection, CRMOutbox
from api.db.services.crm_service import CRMConnectionService
from api.crm.base import CRMProviderRegistry
from api.crm.clients.bitrix24 import Bitrix24Client
from api.crm.clients.amocrm import AmoCRMClient
from api.crm.clients.one_c import OneCClient
from api.crm.clients.hubspot import HubSpotClient
from agent.tools.query_crm_records import (
    QueryCRMRecords,
    QueryCRMRecordsParam,
    parse_sql_crm_query,
)


from agent.canvas import Canvas

class DummyMockCanvas(Canvas):
    def __init__(self, tenant_id: str, channel: str = "web", custom_header=None):
        self._tenant_id = tenant_id
        self._canvas_owner_tenant = tenant_id
        self._channel = channel
        self.custom_header = custom_header or {}
        self.task_id = "test-task-id"
        self.dsl = {"components": {}, "history": [], "path": []}
        self.components = {}
        self.history = []

    def is_canceled(self):
        return False

    def get_tenant_id(self):
        return self._tenant_id

    def get_canvas_owner_tenant(self):
        return self._tenant_id

    def get_channel(self):
        return self._channel

    def add_user_message(self, msg):
        self.history.append({"role": "user", "content": msg})


class TestQueryCRMRecordsTool(unittest.TestCase):
    def setUp(self):
        warnings.filterwarnings("ignore", message=".*doesn't match a supported version.*")
        warnings.filterwarnings("ignore", category=ResourceWarning)
        self.test_db = SqliteDatabase("file:crm_query_tool_mem?mode=memory&cache=shared", uri=True)
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

        self.tenant_id = "tenant-crm-query-test"
        self.secret = "crm-super-secret-key-32bytes-ok!"
        os.environ["RAGFLOW_SECRET_KEY"] = self.secret

        # Create active CRM connection for tests
        self.connection = CRMConnectionService.save_connection(
            tenant_id=self.tenant_id,
            name="Primary Bitrix24",
            crm_type="bitrix24",
            auth_type="webhook",
            config={
                "base_url": "https://company.bitrix24.com/rest/1/testsecret",
            },
        )

    def tearDown(self):
        CRMConnection._meta.database = self._orig_db_conn
        CRMOutbox._meta.database = self._orig_db_outbox
        DB.atomic = self._orig_db_atomic
        if not self.test_db.is_closed():
            self.test_db.close()
        CRMProviderRegistry.clear()

    def test_sql_parser_extracts_entity_and_filters(self):
        """Verify natural SQL queries map to CRM entities and filters."""
        # Standard English deal query
        p1 = parse_sql_crm_query("SELECT * FROM deals WHERE status = 'WON' LIMIT 15;")
        self.assertEqual(p1["entity"], "deal")
        self.assertEqual(p1["status"], "WON")
        self.assertEqual(p1["limit"], 15)

        # Contact lookup by phone
        p2 = parse_sql_crm_query("SELECT id, name, phone FROM contacts WHERE phone = '+1234567890'")
        self.assertEqual(p2["entity"], "contact")
        self.assertEqual(p2["query"], "+1234567890")

        # Product query with like
        p3 = parse_sql_crm_query("SELECT * FROM products WHERE name LIKE '%Laptop%'")
        self.assertEqual(p3["entity"], "product")
        self.assertEqual(p3["query"], "Laptop")

        # Russian keyword query
        p4 = parse_sql_crm_query("SELECT * FROM сделки WHERE статус = 'Оплачено' LIMIT 8")
        self.assertEqual(p4["entity"], "deal")
        self.assertEqual(p4["status"], "Оплачено")
        self.assertEqual(p4["limit"], 8)

    def test_param_metadata_and_form(self):
        """Verify QueryCRMRecordsParam metadata and form schema."""
        param = QueryCRMRecordsParam()
        self.assertEqual(param.meta["name"], "query_crm_records")
        self.assertIn("entity", param.meta["parameters"])
        self.assertIn("query", param.meta["parameters"])
        self.assertIn("sql", param.meta["parameters"])

        form = param.get_input_form()
        self.assertIn("entity", form)
        self.assertIn("query", form)
        self.assertIn("sql", form)

    def test_bitrix24_query_records_deals(self):
        """Verify Bitrix24Client.query_records formats deals cleanly."""
        client = Bitrix24Client()
        mock_response = {
            "result": [
                {
                    "ID": "101",
                    "TITLE": "Sale of CRM License",
                    "STAGE_ID": "WON",
                    "OPPORTUNITY": 50000.0,
                    "CURRENCY_ID": "USD",
                    "DATE_MODIFY": "2026-10-04 10:00:00",
                },
                {
                    "ID": "102",
                    "TITLE": "Support Contract",
                    "STAGE_ID": "IN_PROCESS",
                    "OPPORTUNITY": 12000.0,
                    "CURRENCY_ID": "USD",
                    "DATE_MODIFY": "2026-10-03 15:30:00",
                }
            ]
        }
        with patch.object(client, "_execute_api_call", return_value=mock_response):
            results = client.query_records(
                connection_config={"base_url": "https://company.bitrix24.com/rest/1/secret"},
                entity="deal",
                query="License",
                filters={"status": "WON"},
                limit=10,
            )
            self.assertEqual(len(results), 2)
            self.assertEqual(results[0]["id"], "101")
            self.assertEqual(results[0]["title"], "Sale of CRM License")
            self.assertEqual(results[0]["status"], "WON")
            self.assertEqual(results[0]["price"], 50000.0)

    def test_amocrm_query_records_contacts(self):
        """Verify AmoCRMClient.query_records normalizes contacts."""
        client = AmoCRMClient()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "_embedded": {
                "contacts": [
                    {
                        "id": 555,
                        "name": "Alex Smith",
                        "updated_at": 1728000000,
                        "custom_fields_values": [
                            {"field_code": "PHONE", "values": [{"value": "+14155552671"}]},
                            {"field_code": "EMAIL", "values": [{"value": "alex@example.com"}]},
                        ],
                    }
                ]
            }
        }
        with patch.object(client.transport, "get", return_value=mock_resp):
            results = client.query_records(
                connection_config={"base_url": "https://sales.amocrm.ru", "access_token": "token123"},
                entity="contact",
                query="Alex",
                limit=5,
            )
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["id"], "555")
            self.assertEqual(results[0]["title"], "Alex Smith")
            self.assertEqual(results[0]["phone"], "+14155552671")
            self.assertEqual(results[0]["email"], "alex@example.com")

    def test_onec_query_records_nomenclature(self):
        """Verify OneCClient.query_records queries OData catalog."""
        client = OneCClient()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "value": [
                {
                    "Ref_Key": "000001",
                    "Code": "ART-99",
                    "Description": "Industrial Server Unit",
                    "Цена": 350000,
                    "Статус": "В наличии",
                }
            ]
        }
        with patch.object(client, "_execute_get", return_value=mock_resp):
            results = client.query_records(
                connection_config={"base_url": "https://1c.example.com/demo/odata/standard.odata", "token": "tok"},
                entity="product",
                query="Server",
                limit=5,
            )
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["id"], "000001")
            self.assertEqual(results[0]["title"], "Industrial Server Unit")
            self.assertEqual(results[0]["price"], 350000)

    def test_hubspot_query_records(self):
        """Verify HubSpotClient.query_records parses search results."""
        client = HubSpotClient()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "results": [
                {
                    "id": "hb-deal-1",
                    "properties": {
                        "dealname": "Enterprise Cloud Package",
                        "dealstage": "contractsent",
                        "amount": "25000",
                    },
                    "createdAt": "2026-10-01T00:00:00Z",
                }
            ]
        }
        with patch.object(client.transport, "post", return_value=mock_resp):
            results = client.query_records(
                connection_config={"access_token": "hb-token"},
                entity="deal",
                query="Enterprise",
                limit=5,
            )
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["id"], "hb-deal-1")
            self.assertEqual(results[0]["title"], "Enterprise Cloud Package")
            self.assertEqual(results[0]["status"], "contractsent")
            self.assertEqual(results[0]["price"], "25000")

    def test_query_crm_records_tool_success_markdown_and_json(self):
        """Verify full execution of QueryCRMRecords tool outputs Markdown and JSON."""
        canvas = DummyMockCanvas(self.tenant_id, channel="web")
        param = QueryCRMRecordsParam()
        param.connection_id = self.connection.id

        tool = QueryCRMRecords(canvas=canvas, id="test-node-query", param=param)

        mock_records = [
            {
                "id": "1",
                "entity": "deal",
                "title": "Deal Alpha",
                "status": "WON",
                "price": 10000,
                "phone": "+1234567890",
                "email": "alpha@example.com",
                "updated_at": "2026-10-04",
            }
        ]
        with patch.object(Bitrix24Client, "query_records", return_value=mock_records):
            output = tool._invoke(entity="deal", query="Alpha")
            self.assertIn("Deal Alpha", output)
            self.assertIn("WON", output)

            # Check tool outputs
            json_out = tool.output("json")
            self.assertEqual(len(json_out), 1)
            self.assertEqual(json_out[0]["title"], "Deal Alpha")

    def test_query_crm_records_tool_with_sql_input(self):
        """Verify tool executes seamlessly when natural SQL query is passed."""
        canvas = DummyMockCanvas(self.tenant_id, channel="web")
        param = QueryCRMRecordsParam()
        param.connection_id = self.connection.id

        tool = QueryCRMRecords(canvas=canvas, id="test-node-query-sql", param=param)

        mock_records = [
            {
                "id": "2",
                "entity": "deal",
                "title": "Important Contract",
                "status": "WON",
                "price": 50000,
                "phone": "",
                "email": "",
                "updated_at": "2026-10-04",
            }
        ]
        with patch.object(Bitrix24Client, "query_records", return_value=mock_records) as mock_q:
            tool._invoke(sql="SELECT * FROM deals WHERE status = 'WON'")
            mock_q.assert_called_once()
            args, kwargs = mock_q.call_args
            self.assertEqual(kwargs.get("entity"), "deal")
            self.assertEqual(kwargs.get("filters"), {"status": "WON"})

    def test_anonymous_access_controls(self):
        """Verify public embed/webhook channels reject execution unless allow_anonymous=True."""
        canvas = DummyMockCanvas(self.tenant_id, channel="embed")

        # allow_anonymous=False (default) -> must raise PermissionError
        param = QueryCRMRecordsParam()
        param.allow_anonymous = False
        tool = QueryCRMRecords(canvas=canvas, id="anon-check", param=param)

        with self.assertRaises(PermissionError):
            tool._invoke(entity="deal", query="test")

        # allow_anonymous=True -> must be allowed
        param.allow_anonymous = True
        tool2 = QueryCRMRecords(canvas=canvas, id="anon-check-ok", param=param)
        with patch.object(Bitrix24Client, "query_records", return_value=[]):
            res = tool2._invoke(entity="deal", query="test")
            self.assertIn("No deal records found", res)

    def test_sql_count_aggregation(self):
        """Verify COUNT(*) aggregate via SQL."""
        canvas = DummyMockCanvas(self.tenant_id, channel="web")
        param = QueryCRMRecordsParam()
        param.connection_id = self.connection.id
        tool = QueryCRMRecords(canvas=canvas, id="agg-count", param=param)

        mock_records = [
            {"id": "1", "entity": "deal", "title": "D1", "price": 100},
            {"id": "2", "entity": "deal", "title": "D2", "price": 200},
            {"id": "3", "entity": "deal", "title": "D3", "price": 300},
        ]
        with patch.object(Bitrix24Client, "query_records", return_value=mock_records):
            out = tool._invoke(sql="SELECT COUNT(*) FROM deals")
            self.assertIn("Count", out)
            self.assertIn("3", out)
            self.assertEqual(tool.output("json"), [{"count": 3}])

    def test_sql_sum_aggregation(self):
        """Verify SUM(price) aggregate via SQL."""
        canvas = DummyMockCanvas(self.tenant_id, channel="web")
        param = QueryCRMRecordsParam()
        param.connection_id = self.connection.id
        tool = QueryCRMRecords(canvas=canvas, id="agg-sum", param=param)

        mock_records = [
            {"id": "1", "entity": "deal", "title": "D1", "price": 1000.0, "currency": "USD"},
            {"id": "2", "entity": "deal", "title": "D2", "price": 2500.0, "currency": "USD"},
        ]
        with patch.object(Bitrix24Client, "query_records", return_value=mock_records):
            out = tool._invoke(sql="SELECT SUM(price) FROM deals")
            self.assertIn("SUM (USD)", out)
            self.assertIn("3500", out)
            self.assertEqual(tool.output("json"), [{"sum": 3500.0, "currency": "USD"}])

    def test_sql_column_projection(self):
        """Verify column projection only outputs selected columns."""
        canvas = DummyMockCanvas(self.tenant_id, channel="web")
        param = QueryCRMRecordsParam()
        param.connection_id = self.connection.id
        tool = QueryCRMRecords(canvas=canvas, id="proj-col", param=param)

        mock_records = [
            {"id": "1", "entity": "deal", "title": "D1", "price": 1000.0, "phone": "+1234567890", "status": "WON"},
        ]
        with patch.object(Bitrix24Client, "query_records", return_value=mock_records):
            out = tool._invoke(sql="SELECT title, price FROM deals")
            self.assertIn("Title / Name", out)
            self.assertIn("Price", out)
            # phone should not be in the projected markdown columns
            self.assertNotIn("Phone", out)


if __name__ == "__main__":
    unittest.main()

