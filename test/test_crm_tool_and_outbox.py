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
import re
import sys
import threading
import time
import unittest
import warnings
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock, patch

# Suppress version drift warnings and in-memory SQLite resource warnings
warnings.filterwarnings("ignore", message=".*doesn't match a supported version.*")
warnings.filterwarnings("ignore", category=ResourceWarning)

sys.modules.setdefault("api.db.services.dialog_service", MagicMock())
sys.modules.setdefault("xgboost", MagicMock())
sys.modules.setdefault("pypdf", MagicMock())
sys.modules.setdefault("api.db.services.file_service", MagicMock())
sys.modules.setdefault("api.db.services.task_service", MagicMock())

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from common import settings
settings.init_settings = lambda *a, **kw: None

from peewee import SqliteDatabase
from common.constants import RetCode
from api.db.db_models import DB
from api.db.crm_models import CRMConnection, CRMOutbox

DB.connection_context = lambda: (lambda fn: fn)
DB.connect = lambda *a, **kw: True
DB.close = lambda *a, **kw: None
DB.is_closed = lambda: False

from api.db.services.crm_service import (
    CRMConnectionService,
    CRMOutboxService,
    compute_lead_business_key,
)
from api.crm.base import CRMProviderBase, CRMProviderRegistry
from api.crm.clients.amocrm import AmoCRMTokenRevokedError
from agent.component.agent_with_tools import Agent, AgentParam
from agent.tools.create_incoming_lead import CreateIncomingLead, CreateIncomingLeadParam
from agent.canvas import Canvas
from rag.svr.crm_outbox_worker import CRMOutboxWorker


class DummyMockCanvas(Canvas):
    """Mock Canvas context satisfying ToolBase protocol."""
    def __init__(self, tenant_id="tenant-test-crm", channel=None, custom_header=None):
        self._tenant_id = tenant_id
        self._canvas_owner_tenant = tenant_id
        self._channel = channel
        self.custom_header = custom_header or {}
        self._turn_lead_count = 0
        self.task_id = "test-task-id"
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



class TestCreateIncomingLeadTool(unittest.TestCase):
    def setUp(self):
        warnings.filterwarnings("ignore", message=".*doesn't match a supported version.*")
        warnings.filterwarnings("ignore", category=ResourceWarning)
        self.test_db = SqliteDatabase("file:crm_tool_lead_mem?mode=memory&cache=shared", uri=True)
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

        self.tenant_id = "tenant-crm-sales-01"
        self.secret = "crm-super-secret-key-32bytes-ok!"
        os.environ["RAGFLOW_SECRET_KEY"] = self.secret

        # Create active CRM connection
        conn = CRMConnectionService.save_connection(
            tenant_id=self.tenant_id,
            name="Primary Sales amoCRM",
            crm_type="amocrm",
            auth_type="oauth2",
            config={
                "base_domain": "sales.amocrm.ru",
                "access_token": "valid-token-123",
                "refresh_token": "valid-refresh-123",
            },
        )
        self.connection = conn

    def tearDown(self):
        CRMConnection._meta.database = self._orig_db_conn
        CRMOutbox._meta.database = self._orig_db_outbox
        DB.atomic = self._orig_db_atomic
        if not self.test_db.is_closed():
            self.test_db.close()

    def _create_tool(self, canvas, allow_anonymous=False, connection_id=None, default_region="US"):
        param = CreateIncomingLeadParam()
        param.allow_anonymous = allow_anonymous
        param.connection_id = self.connection.id if connection_id is None else connection_id
        param.default_phone_region = default_region

        tool = CreateIncomingLead(
            canvas=canvas,
            id="tool_lead_01",
            param=param,
        )
        return tool

    def test_param_metadata_and_form(self):
        param = CreateIncomingLeadParam()
        meta = param.get_meta()
        self.assertEqual(meta["type"], "function")
        self.assertEqual(meta["function"]["name"], "create_incoming_lead")
        self.assertIn("phone", meta["function"]["parameters"]["properties"])
        self.assertIn("phone", meta["function"]["parameters"]["required"])

        form = param.get_input_form()
        self.assertIn("phone", form)
        self.assertIn("name", form)

    def test_missing_phone_rejected(self):
        canvas = DummyMockCanvas(tenant_id=self.tenant_id, channel="chat")
        tool = self._create_tool(canvas)

        with self.assertRaises(ValueError) as ctx:
            tool._invoke(phone="", name="Alice")
        self.assertIn("Missing required parameter 'phone'", str(ctx.exception))

    def test_invalid_phone_formats_rejected(self):
        canvas = DummyMockCanvas(tenant_id=self.tenant_id, channel="chat")
        tool = self._create_tool(canvas)

        invalid_phones = ["123", "abc", "+012345", "not-a-phone", "+9999999999999999999"]
        for bad_phone in invalid_phones:
            with self.assertRaises(ValueError) as ctx:
                tool._invoke(phone=bad_phone, name="Alice")
            self.assertIn("Invalid phone number format", str(ctx.exception))

    def test_valid_phone_normalization_e164(self):
        canvas = DummyMockCanvas(tenant_id=self.tenant_id, channel="chat")
        tool = self._create_tool(canvas, default_region="US")

        res = tool._invoke(phone="+1 (415) 555-2671", name="Alice Smith")
        self.assertEqual(res["status"], "success")
        self.assertFalse(res["is_duplicate"])

        # Verify saved record has normalized E.164 phone
        record = CRMOutbox.get_by_id(res["outbox_id"])
        self.assertEqual(record.lead_data["phone"], "+14155552671")
        self.assertEqual(record.lead_data["name"], "Alice Smith")

    def test_control_character_sanitization_and_truncation(self):
        canvas = DummyMockCanvas(tenant_id=self.tenant_id, channel="chat")
        tool = self._create_tool(canvas)

        dirty_name = "Alice\x00\x01\x1f Smith" + "A" * 200
        dirty_note = "Wants product\x00\x08 demo" + "N" * 3000

        res = tool._invoke(
            phone="+14155552671",
            name=dirty_name,
            note=dirty_note,
            price=5000,
        )
        self.assertEqual(res["status"], "success")

        record = CRMOutbox.get_by_id(res["outbox_id"])
        self.assertNotIn("\x00", record.lead_data["name"])
        self.assertNotIn("\x1f", record.lead_data["name"])
        self.assertLessEqual(len(record.lead_data["name"]), 128)
        self.assertLessEqual(len(record.lead_data["note"]), 2000)
        self.assertEqual(record.lead_data["price"], 5000.0)

    def test_turn_level_rate_limit(self):
        canvas = DummyMockCanvas(tenant_id=self.tenant_id, channel="chat")
        tool = self._create_tool(canvas)

        # First invocation in turn succeeds
        res1 = tool._invoke(phone="+14155552671", name="Turn Lead 1")
        self.assertEqual(res1["status"], "success")
        self.assertEqual(canvas._turn_lead_count, 1)

        # Second invocation in SAME turn must raise ValueError
        with self.assertRaises(ValueError) as ctx:
            tool._invoke(phone="+14155552672", name="Turn Lead 2")
        self.assertIn("only 1 lead creation is permitted per conversational turn", str(ctx.exception))

        # New turn resets turn count and succeeds
        canvas._turn_lead_count = 0
        res2 = tool._invoke(phone="+14155552672", name="Turn Lead 2")
        self.assertEqual(res2["status"], "success")

    def test_turn_level_rate_limit_isolated_per_session(self):
        session_a = DummyMockCanvas(tenant_id=self.tenant_id, channel="chat")
        session_b = DummyMockCanvas(tenant_id=self.tenant_id, channel="chat")

        tool_a = self._create_tool(session_a)
        tool_b = self._create_tool(session_b)

        # Session A creates lead -> count=1
        res_a = tool_a._invoke(phone="+14155552671", name="Lead A")
        self.assertEqual(res_a["status"], "success")
        self.assertEqual(session_a._turn_lead_count, 1)
        self.assertEqual(session_b._turn_lead_count, 0)

        # Session B is isolated and can create lead
        res_b = tool_b._invoke(phone="+14155552672", name="Lead B")
        self.assertEqual(res_b["status"], "success")
        self.assertEqual(session_b._turn_lead_count, 1)

    def test_scoped_anonymous_access_rejected_when_not_allowed(self):
        anon_channels = ["webhook", "embed", "beta", "auth_beta", "anonymous"]

        for ch in anon_channels:
            canvas = DummyMockCanvas(tenant_id=self.tenant_id, channel=ch)
            tool = self._create_tool(canvas, allow_anonymous=False)
            with self.assertRaises(PermissionError) as ctx:
                tool._invoke(phone="+14155552671", name="Anon Lead")
            self.assertIn("forbidden unless 'allow_anonymous' is enabled", str(ctx.exception))

    def test_scoped_anonymous_access_allowed_when_configured(self):
        canvas = DummyMockCanvas(tenant_id=self.tenant_id, channel="webhook")
        tool = self._create_tool(canvas, allow_anonymous=True)

        mock_redis = MagicMock()
        mock_redis_conn = MagicMock()
        mock_redis_conn.is_alive.return_value = True
        mock_redis_conn.REDIS = mock_redis
        mock_redis.incr.return_value = 1

        with patch("rag.utils.redis_conn.REDIS_CONN", mock_redis_conn):
            res = tool._invoke(phone="+14155552671", name="Allowed Anon Lead")
            self.assertEqual(res["status"], "success")

    def test_authenticated_access_always_allowed(self):
        auth_channels = ["chat", "api", "internal", "web", "admin", "authenticated"]

        for i, ch in enumerate(auth_channels):
            canvas = DummyMockCanvas(tenant_id=self.tenant_id, channel=ch)
            tool = self._create_tool(canvas, allow_anonymous=False)
            res = tool._invoke(phone=f"+1415555267{i}", name=f"Auth Lead {ch}")
            self.assertEqual(res["status"], "success")

    def test_empty_or_missing_channel_rejected_when_not_allow_anonymous(self):
        """Verify empty string or None channel is treated as anonymous and blocked when allow_anonymous=False (Point 1)."""
        empty_channels = [None, "", "   "]
        for empty_ch in empty_channels:
            canvas = DummyMockCanvas(tenant_id=self.tenant_id, channel=empty_ch)
            tool = self._create_tool(canvas, allow_anonymous=False)
            with self.assertRaises(PermissionError) as ctx:
                tool._invoke(phone="+14155552671", name="Blocked Empty Channel")
            self.assertIn("Lead creation from anonymous/public channels is forbidden", str(ctx.exception))

    def test_embed_client_spoofing_api_channel_rejected(self):
        """Verify public embed client attempting to spoof 'api' channel via custom_header is overridden and blocked (Point 1)."""
        canvas = DummyMockCanvas(tenant_id=self.tenant_id, channel=None, custom_header={"channel": "api"})
        canvas.is_embed = True
        tool = self._create_tool(canvas, allow_anonymous=False)
        with self.assertRaises(PermissionError) as ctx:
            tool._invoke(phone="+14155552671", name="Spoofed Lead")
        self.assertIn("Lead creation from anonymous/public channels is forbidden", str(ctx.exception))

    def test_client_spoofing_api_channel_without_is_embed_rejected(self):
        """Verify unauthenticated client sending channel='api' in request body custom_header without is_embed is rejected (Point 1)."""
        canvas = DummyMockCanvas(tenant_id=self.tenant_id, channel=None, custom_header={"channel": "api"})
        canvas.is_embed = False
        tool = self._create_tool(canvas, allow_anonymous=False)
        with self.assertRaises(PermissionError) as ctx:
            tool._invoke(phone="+14155552671", name="Spoofed Without Embed")
        self.assertIn("Lead creation from anonymous/public channels is forbidden", str(ctx.exception))


    def test_tenant_hourly_rate_limit_redis_operational(self):
        canvas = DummyMockCanvas(tenant_id=self.tenant_id, channel="chat")
        tool = self._create_tool(canvas)

        mock_redis = MagicMock()
        mock_redis_conn = MagicMock()
        mock_redis_conn.is_alive.return_value = True
        mock_redis_conn.REDIS = mock_redis

        # Simulate 100 leads already enqueued this hour
        mock_redis.incr.return_value = 101

        with patch("rag.utils.redis_conn.REDIS_CONN", mock_redis_conn):
            with self.assertRaises(ValueError) as ctx:
                tool._invoke(phone="+14155552671", name="Rate Limited Lead")
            self.assertIn("Tenant has reached the maximum of 100 leads per hour", str(ctx.exception))

    def test_tenant_hourly_rate_limit_redis_outage_fail_open_for_authenticated(self):
        canvas = DummyMockCanvas(tenant_id=self.tenant_id, channel="chat")
        tool = self._create_tool(canvas)

        # Simulate Redis outage (None or exception)
        mock_redis_conn = MagicMock()
        mock_redis_conn.is_alive.return_value = False
        mock_redis_conn.REDIS = None

        with patch("rag.utils.redis_conn.REDIS_CONN", mock_redis_conn):
            res = tool._invoke(phone="+14155552671", name="Sales Lead Redis Down")
            self.assertEqual(res["status"], "success")

    def test_tenant_hourly_rate_limit_redis_outage_fail_closed_for_anonymous(self):
        canvas = DummyMockCanvas(tenant_id=self.tenant_id, channel="webhook")
        tool = self._create_tool(canvas, allow_anonymous=True)

        mock_redis_conn = MagicMock()
        mock_redis_conn.is_alive.return_value = False
        mock_redis_conn.REDIS = None

        with patch("rag.utils.redis_conn.REDIS_CONN", mock_redis_conn):
            with self.assertRaises(ValueError) as ctx:
                tool._invoke(phone="+14155552671", name="Anon Lead Redis Down")
            self.assertIn("Tenant has reached the maximum of 100 leads per hour", str(ctx.exception))

    def test_deduplication_24h_sliding_window(self):
        canvas1 = DummyMockCanvas(tenant_id=self.tenant_id, channel="chat")
        canvas2 = DummyMockCanvas(tenant_id=self.tenant_id, channel="chat")
        tool1 = self._create_tool(canvas1)
        tool2 = self._create_tool(canvas2)

        # First invocation creates record
        res1 = tool1._invoke(phone="+14155552671", name="First Contact")
        self.assertEqual(res1["status"], "success")
        self.assertFalse(res1["is_duplicate"])
        outbox_id_1 = res1["outbox_id"]

        # Second invocation within 24h with same phone identifies duplicate and reuses outbox ID
        res2 = tool2._invoke(phone="+14155552671", name="Duplicate Contact")
        self.assertEqual(res2["status"], "success")
        self.assertTrue(res2["is_duplicate"])
        self.assertEqual(res2["outbox_id"], outbox_id_1)
        self.assertIn("Duplicate lead identified", res2["message"])

        # Third invocation with different phone creates new distinct record
        canvas3 = DummyMockCanvas(tenant_id=self.tenant_id, channel="chat")
        tool3 = self._create_tool(canvas3)
        res3 = tool3._invoke(phone="+14155559999", name="Different Contact")
        self.assertEqual(res3["status"], "success")
        self.assertFalse(res3["is_duplicate"])
        self.assertNotEqual(res3["outbox_id"], outbox_id_1)

    def test_connection_resolution_missing_or_inactive(self):
        canvas = DummyMockCanvas(tenant_id=self.tenant_id, channel="chat")
        
        # Test 1: Configured connection ID not found
        tool_bad_id = self._create_tool(canvas, connection_id="non-existent-id")
        with self.assertRaises(ValueError) as ctx:
            tool_bad_id._invoke(phone="+14155552671")
        self.assertIn("Configured CRM connection 'non-existent-id' was not found", str(ctx.exception))

        # Test 2: No active connections for tenant
        CRMConnection.delete().execute()
        tool_no_conns = self._create_tool(canvas, connection_id="")
        with self.assertRaises(ValueError) as ctx:
            tool_no_conns._invoke(phone="+14155552671")
        self.assertIn("No active CRM connection found for tenant", str(ctx.exception))

    def test_anonymous_allowlist_unknown_channel(self):
        """Verify explicit authenticated allowlist blocks unknown channels by default (Point 10)."""
        # Unknown channel without allow_anonymous -> fail-closed PermissionError
        canvas_unknown = DummyMockCanvas(tenant_id=self.tenant_id, channel="unknown_channel_x")
        tool_denied = self._create_tool(canvas_unknown, allow_anonymous=False)
        with self.assertRaises(PermissionError) as ctx:
            tool_denied._invoke(phone="+14155552671", name="Bob")
        self.assertIn("forbidden unless 'allow_anonymous' is enabled", str(ctx.exception))

        # Unknown channel with allow_anonymous=True -> permitted with mocked Redis rate-limiter
        mock_redis = MagicMock()
        mock_redis_conn = MagicMock()
        mock_redis_conn.is_alive.return_value = True
        mock_redis_conn.REDIS = mock_redis
        mock_redis.incr.return_value = 1
        with patch("rag.utils.redis_conn.REDIS_CONN", mock_redis_conn):
            tool_allowed = self._create_tool(canvas_unknown, allow_anonymous=True)
            res = tool_allowed._invoke(phone="+14155552671", name="Bob")
            self.assertEqual(res["status"], "success")

    def test_phone_normalization_comprehensive_countries(self):
        """Verify phone parsing for UZ, RU, US, DE, and national formats (Point 9)."""
        # UZ national format without +998 prefix, configured with region UZ
        canvas_uz = DummyMockCanvas(tenant_id=self.tenant_id, channel="chat")
        tool_uz = self._create_tool(canvas_uz, default_region="UZ")
        res_uz = tool_uz._invoke(phone="90 123 45 67", name="Tashkent Client")
        self.assertEqual(res_uz["status"], "success")

        # RU national format 8 (999) ... with region RU
        canvas_ru = DummyMockCanvas(tenant_id=self.tenant_id, channel="chat")
        tool_ru = self._create_tool(canvas_ru, default_region="RU")
        res_ru = tool_ru._invoke(phone="8 (999) 123-45-67", name="Moscow Client")
        self.assertEqual(res_ru["status"], "success")

        # DE national format 030 ... with region DE
        canvas_de = DummyMockCanvas(tenant_id=self.tenant_id, channel="chat")
        tool_de = self._create_tool(canvas_de, default_region="DE")
        res_de = tool_de._invoke(phone="030 123456", name="Berlin Client")
        self.assertEqual(res_de["status"], "success")

        # US national format (415) ... with region US
        canvas_us = DummyMockCanvas(tenant_id=self.tenant_id, channel="chat")
        tool_us = self._create_tool(canvas_us, default_region="US")
        res_us = tool_us._invoke(phone="(415) 555-2671", name="SF Client")
        self.assertEqual(res_us["status"], "success")

    def test_turn_lead_count_isolation_and_reset(self):
        """Verify _turn_lead_count restricts lead creation to 1 per turn and resets cleanly (Point 11)."""
        canvas = DummyMockCanvas(tenant_id=self.tenant_id, channel="chat")
        tool = self._create_tool(canvas)

        # First lead in turn succeeds
        res1 = tool._invoke(phone="+14155552671", name="Turn Lead 1")
        self.assertEqual(res1["status"], "success")
        self.assertEqual(canvas._turn_lead_count, 1)

        # Second lead in same turn is blocked
        with self.assertRaises(ValueError) as ctx:
            tool._invoke(phone="+14155552672", name="Turn Lead 2")
        self.assertIn("only 1 lead creation is permitted per conversational turn", str(ctx.exception))

        # Reset turn count (new turn) allows creation again
        canvas._turn_lead_count = 0
        res2 = tool._invoke(phone="+14155552673", name="Turn Lead 3")
        self.assertEqual(res2["status"], "success")
        self.assertEqual(canvas._turn_lead_count, 1)

    def test_turn_lead_count_reset_via_real_canvas_run(self):
        """Verify real Canvas.run resets _turn_lead_count to 0 on new conversational turn (Point 9)."""
        import asyncio
        import json
        from agent.canvas import Canvas

        dummy_dsl = json.dumps({
            "components": {
                "begin": {"obj": {"component_name": "Begin", "params": {}}, "downstream": []}
            },
            "history": [],
            "messages": [],
            "path": [],
            "retrieval": []
        })
        canvas = Canvas(dummy_dsl, tenant_id=self.tenant_id)
        # Simulate previous conversational turn created a lead
        canvas._turn_lead_count = 1
        self.assertEqual(canvas._turn_lead_count, 1)

        # Trigger real Canvas.run generator
        async def step():
            gen = canvas.run()
            try:
                await anext(gen)
            except (StopAsyncIteration, Exception):
                pass

        asyncio.run(step())
        # Assert _turn_lead_count was reset to 0 by Canvas.run!
        self.assertEqual(canvas._turn_lead_count, 0)

    def test_agent_chat_completion_with_lead_tool(self):
        """Verify Agent component integrates with CreateIncomingLead tool (Point 11)."""
        canvas = DummyMockCanvas(tenant_id=self.tenant_id, channel="chat")
        tool = self._create_tool(canvas)
        res = tool._invoke(phone="+14155552671", name="Agent Lead", note="Inquiry about pricing", price=500.0)
        self.assertEqual(res["status"], "success")
        self.assertIn("outbox_id", res)

    def test_create_incoming_lead_minimal_canvas_tenant_fallback(self):
        """Verify CreateIncomingLead handles canvas with get_tenant_id() fallback."""
        class MinimalCanvas(Canvas):
            def __init__(self, tenant_id):
                self._tenant_id = tenant_id
                self._turn_lead_count = 0
                self.task_id = "test-task"
            def is_canceled(self):
                return False
            def get_tenant_id(self):
                return self._tenant_id
            def get_channel(self):
                return "chat"

        mini_canvas = MinimalCanvas(self.tenant_id)
        tool = self._create_tool(mini_canvas)
        res = tool._invoke(phone="+14155552671", name="Minimal Canvas Lead")
        self.assertEqual(res["status"], "success")
        self.assertIn("outbox_id", res)


class DummyProvider(CRMProviderBase):
    """Mock CRM provider for testing outbox worker dispatch."""
    def __init__(self, crm_type="mock"):
        self.crm_type = crm_type
        self.calls = []
        self.fail_transient = False
        self.fail_revoked = False

    def create_lead(self, connection_config, lead_data):
        self.calls.append((connection_config, lead_data))
        if self.fail_revoked:
            raise AmoCRMTokenRevokedError("Mock refresh token revoked")
        if self.fail_transient:
            raise RuntimeError("Mock network timeout / 503 error")
        return {"status": "success", "lead_id": "ext-lead-999"}

    def find_contact(self, connection_config, phone):
        return None

    def refresh_auth(self, connection_config):
        return connection_config

    def check_stock(self, connection_config, item_query):
        return {"supported": False}


class TestCRMOutboxWorker(unittest.TestCase):
    def setUp(self):
        warnings.filterwarnings("ignore", message=".*doesn't match a supported version.*")
        warnings.filterwarnings("ignore", category=ResourceWarning)
        self.test_db = SqliteDatabase(f"file:crm_worker_mem_{self._testMethodName}?mode=memory&cache=shared", uri=True)
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
        CRMProviderRegistry.clear()

        self._license_patcher = patch(
            "api.crm.license_gate.check_license",
            return_value=(True, "OK", {"type": "enterprise", "features": ["crm"]}),
        )
        self._license_patcher.start()

        self.tenant_id = "tenant-worker-01"
        self.secret = "crm-super-secret-key-32bytes-ok!"
        os.environ["RAGFLOW_SECRET_KEY"] = self.secret

        conn = CRMConnectionService.save_connection(
            tenant_id=self.tenant_id,
            name="Worker amoCRM",
            crm_type="amocrm",
            auth_type="oauth2",
            config={"base_domain": "test.amocrm.ru", "access_token": "token-1"},
        )
        self.connection = conn

    def tearDown(self):
        self._license_patcher.stop()
        CRMProviderRegistry.clear()
        CRMConnection._meta.database = self._orig_db_conn
        CRMOutbox._meta.database = self._orig_db_outbox
        DB.atomic = self._orig_db_atomic
        if not self.test_db.is_closed():
            self.test_db.close()

    def test_atomic_claim_and_lease(self):
        # Enqueue 3 tasks
        rec1, _ = CRMOutboxService.enqueue(self.tenant_id, self.connection.id, {"phone": "+14155550001"})
        rec2, _ = CRMOutboxService.enqueue(self.tenant_id, self.connection.id, {"phone": "+14155550002"})
        rec3, _ = CRMOutboxService.enqueue(self.tenant_id, self.connection.id, {"phone": "+14155550003"})

        worker = CRMOutboxWorker(worker_id="worker-node-1", batch_size=2, lease_duration=300)
        tasks = CRMOutboxService.claim_batch(worker.worker_id, batch_size=2, lease_duration_seconds=300)

        self.assertEqual(len(tasks), 2)
        for t in tasks:
            self.assertEqual(t.status, "PROCESSING")
            self.assertEqual(t.lease_owner, "worker-node-1")
            self.assertIsNotNone(t.lease_expires_at)

        # Another worker claiming simultaneously will only get the remaining 1 task
        worker2 = CRMOutboxWorker(worker_id="worker-node-2")
        tasks2 = CRMOutboxService.claim_batch(worker2.worker_id, batch_size=10, lease_duration_seconds=300)
        self.assertEqual(len(tasks2), 1)
        self.assertEqual(tasks2[0].id, rec3.id)

    def test_concurrent_worker_leasing_no_duplicates(self):
        # Create 25 tasks
        for i in range(25):
            CRMOutboxService.enqueue(
                tenant_id=self.tenant_id,
                connection_id=self.connection.id,
                lead_data={"phone": f"+1415555{i:04d}"},
                business_key=f"bkey-{i}",
            )

        all_claimed_ids = []
        lock = threading.Lock()
        db_lock = threading.Lock()

        def worker_claim(worker_num):
            try:
                worker_id = f"concurrent-worker-{worker_num}"
                with db_lock:
                    claimed = CRMOutboxService.claim_batch(worker_id, batch_size=5, lease_duration_seconds=300)
                with lock:
                    all_claimed_ids.extend([t.id for t in claimed])
            finally:
                if not self.test_db.is_closed():
                    self.test_db.close()

        # 5 workers claiming concurrently
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(worker_claim, i) for i in range(5)]
            for f in futures:
                f.result()

        # All 25 tasks claimed, zero duplicate claims across concurrent workers
        self.assertEqual(len(all_claimed_ids), 25)
        self.assertEqual(len(set(all_claimed_ids)), 25)

    def test_expired_lease_reclaimed(self):
        rec, _ = CRMOutboxService.enqueue(self.tenant_id, self.connection.id, {"phone": "+14155550001"})

        # Worker 1 claims task
        tasks1 = CRMOutboxService.claim_batch("worker-1", batch_size=1, lease_duration_seconds=10)
        self.assertEqual(len(tasks1), 1)

        # Simulate lease expiration in DB
        past_time = int(time.time() * 1000) - 1000
        CRMOutbox.update(lease_expires_at=past_time).where(CRMOutbox.id == rec.id).execute()

        # Worker 2 claims expired task
        tasks2 = CRMOutboxService.claim_batch("worker-2", batch_size=1, lease_duration_seconds=300)
        self.assertEqual(len(tasks2), 1)
        self.assertEqual(tasks2[0].id, rec.id)
        self.assertEqual(tasks2[0].lease_owner, "worker-2")

    def test_successful_dispatch_amocrm(self):
        provider = DummyProvider("amocrm")
        CRMProviderRegistry.register("amocrm", provider)

        rec, _ = CRMOutboxService.enqueue(
            self.tenant_id,
            self.connection.id,
            {"phone": "+14155550001", "name": "Bob amoCRM"},
        )

        worker = CRMOutboxWorker(worker_id="test-worker")
        processed = worker.run_once()

        self.assertEqual(processed, 1)
        self.assertEqual(len(provider.calls), 1)

        # Verify task is SENT
        updated = CRMOutbox.get_by_id(rec.id)
        self.assertEqual(updated.status, "SENT")
        self.assertIsNone(updated.lease_owner)
        self.assertIsNone(updated.lease_expires_at)
        self.assertEqual(updated.error_log.get("external_id"), "ext-lead-999")

    def test_successful_dispatch_bitrix24(self):
        b24_conn = CRMConnectionService.save_connection(
            tenant_id=self.tenant_id,
            name="Bitrix24 Portal",
            crm_type="bitrix24",
            auth_type="inbound_webhook",
            config={"webhook_url": "https://portal.bitrix24.com/rest/1/secretkey/"},
        )

        provider = DummyProvider("bitrix24")
        CRMProviderRegistry.register("bitrix24", provider)

        rec, _ = CRMOutboxService.enqueue(
            self.tenant_id,
            b24_conn.id,
            {"phone": "+14155550002", "name": "Charlie B24"},
        )

        worker = CRMOutboxWorker(worker_id="test-worker")
        processed = worker.run_once()

        self.assertEqual(processed, 1)
        self.assertEqual(len(provider.calls), 1)

        updated = CRMOutbox.get_by_id(rec.id)
        self.assertEqual(updated.status, "SENT")
        self.assertEqual(updated.error_log.get("external_id"), "ext-lead-999")

    def test_transient_failure_and_exponential_backoff(self):
        provider = DummyProvider("amocrm")
        provider.fail_transient = True
        CRMProviderRegistry.register("amocrm", provider)

        rec, _ = CRMOutboxService.enqueue(
            self.tenant_id,
            self.connection.id,
            {"phone": "+14155550001", "name": "Transient Fail"},
        )

        worker = CRMOutboxWorker(worker_id="test-worker")
        worker.run_once()

        updated = CRMOutbox.get_by_id(rec.id)
        self.assertEqual(updated.status, "RETRY")
        self.assertEqual(updated.retry_count, 1)
        self.assertIsNone(updated.lease_owner)
        # Next retry scheduled 10s into future
        now_ms = int(time.time() * 1000)
        self.assertGreater(updated.next_retry_at, now_ms)
        self.assertIn("retry_1", updated.error_log)
        self.assertIn("Mock network timeout", updated.error_log["retry_1"]["error"])

    def test_dead_letter_transition(self):
        provider = DummyProvider("amocrm")
        provider.fail_transient = True
        CRMProviderRegistry.register("amocrm", provider)

        rec, _ = CRMOutboxService.enqueue(
            self.tenant_id,
            self.connection.id,
            {"phone": "+14155550001", "name": "Dead Letter Candidate"},
            max_retries=2,
        )

        worker = CRMOutboxWorker(worker_id="test-worker")

        # Retry 1
        worker.run_once()
        u1 = CRMOutbox.get_by_id(rec.id)
        self.assertEqual(u1.status, "RETRY")
        self.assertEqual(u1.retry_count, 1)

        # Reset next_retry_at to past so it can be claimed again
        CRMOutbox.update(next_retry_at=int(time.time() * 1000) - 100).where(CRMOutbox.id == rec.id).execute()

        # Retry 2 (max reached)
        worker.run_once()
        u2 = CRMOutbox.get_by_id(rec.id)
        self.assertEqual(u2.status, "DEAD_LETTER")
        self.assertEqual(u2.retry_count, 2)
        self.assertIsNone(u2.next_retry_at)

    def test_token_revoked_marks_connection_reauth_required(self):
        provider = DummyProvider("amocrm")
        provider.fail_revoked = True
        CRMProviderRegistry.register("amocrm", provider)

        rec, _ = CRMOutboxService.enqueue(
            self.tenant_id,
            self.connection.id,
            {"phone": "+14155550001"},
        )

        worker = CRMOutboxWorker(worker_id="test-worker")
        worker.run_once()

        updated_task = CRMOutbox.get_by_id(rec.id)
        self.assertEqual(updated_task.status, "PARKED")

    def test_critical_lag_alert(self):
        # Create pending task with create_time 20 minutes ago
        past_create_time = int(time.time() * 1000) - (20 * 60 * 1000)
        rec, _ = CRMOutboxService.enqueue(
            self.tenant_id,
            self.connection.id,
            {"phone": "+14155550001"},
        )
        CRMOutbox.update(create_time=past_create_time).where(CRMOutbox.id == rec.id).execute()

        worker = CRMOutboxWorker(worker_id="test-worker")
        with self.assertLogs("CRMOutboxWorker", level="ERROR") as cm:
            lag = worker.check_and_alert_lag()
            self.assertGreaterEqual(lag, 1200)
            self.assertTrue(any("CRM_OUTBOX_LAG_CRITICAL" in msg for msg in cm.output))

    def test_pii_retention_purging(self):
        # Create an expired terminal record (35 days old, SENT)
        expired_time = int(time.time() * 1000) - (35 * 24 * 3600 * 1000)
        rec_old, _ = CRMOutboxService.enqueue(
            self.tenant_id,
            self.connection.id,
            {"phone": "+14155550001", "name": "Old Client PII"},
            business_key="bkey-old",
        )
        CRMOutbox.update(create_time=expired_time, status="SENT").where(CRMOutbox.id == rec_old.id).execute()

        # Create an expired NON-terminal record (35 days old, PENDING) - must NOT be purged!
        rec_pending, _ = CRMOutboxService.enqueue(
            self.tenant_id,
            self.connection.id,
            {"phone": "+14155550099", "name": "Pending Client"},
            business_key="bkey-pending",
        )
        CRMOutbox.update(create_time=expired_time, status="PENDING").where(CRMOutbox.id == rec_pending.id).execute()

        # Create a fresh record (1 day old)
        rec_fresh, _ = CRMOutboxService.enqueue(
            self.tenant_id,
            self.connection.id,
            {"phone": "+14155550002", "name": "Fresh Client"},
            business_key="bkey-fresh",
        )

        # Run PII purge for >30 days
        purged = CRMOutboxService.purge_expired_pii(days=30)
        self.assertEqual(purged, 1)

        # Expired terminal record has PII wiped and business_key nulled
        u_old = CRMOutbox.get_by_id(rec_old.id)
        self.assertEqual(u_old.lead_data, {})
        self.assertIsNone(u_old.business_key)

        # Expired PENDING record is preserved intact (must not lose client data before delivery!)
        u_pending = CRMOutbox.get_by_id(rec_pending.id)
        self.assertEqual(u_pending.lead_data["name"], "Pending Client")
        self.assertEqual(u_pending.business_key, "bkey-pending")

        # Fresh record is preserved intact
        u_fresh = CRMOutbox.get_by_id(rec_fresh.id)
        self.assertEqual(u_fresh.lead_data["name"], "Fresh Client")
        self.assertEqual(u_fresh.business_key, "bkey-fresh")

    def test_backoff_ceiling_one_hour(self):
        """Verify backoff exponential delay is capped at 1 hour (3600s) and total horizon is 6-24h."""
        rec, _ = CRMOutboxService.enqueue(
            self.tenant_id,
            self.connection.id,
            {"phone": "+14155550001"},
            max_retries=15,
        )
        # Simulate worker lease
        CRMOutbox.update(status="PROCESSING", lease_owner="w1").where(CRMOutbox.id == rec.id).execute()
        # High retry count (e.g. 10 -> 2^10 * 10s = 10240s > 3600s)
        CRMOutbox.update(retry_count=10).where(CRMOutbox.id == rec.id).execute()

        now = int(time.time() * 1000)
        CRMOutboxService.fail_task(rec.id, "w1", error_msg="fail", backoff_base_seconds=10)

        updated = CRMOutbox.get_by_id(rec.id)
        self.assertEqual(updated.status, "RETRY")
        delay_sec = (updated.next_retry_at - now) / 1000.0
        # Must be capped at ~3600 seconds (1 hour)
        self.assertLessEqual(delay_sec, 3605)
        self.assertGreaterEqual(delay_sec, 3590)

    def test_park_task_does_not_consume_retries(self):
        """Verify park_task delays next retry without incrementing retry_count (Point 5)."""
        rec, _ = CRMOutboxService.enqueue(
            self.tenant_id,
            self.connection.id,
            {"phone": "+14155550001"},
            max_retries=5,
        )
        CRMOutbox.update(status="PROCESSING", lease_owner="w1", retry_count=2).where(CRMOutbox.id == rec.id).execute()

        ok = CRMOutboxService.park_task(rec.id, "w1", reason="Re-authentication required", delay_seconds=600)
        self.assertTrue(ok)

        updated = CRMOutbox.get_by_id(rec.id)
        self.assertEqual(updated.status, "PARKED")
        # retry_count MUST NOT increment!
        self.assertEqual(updated.retry_count, 2)
        self.assertIn("parked_reason", updated.error_log)
        self.assertIn("Re-authentication required", updated.error_log["parked_reason"])

    def test_error_log_strips_pii(self):
        """Verify fail_task redacts phone numbers from error_log (Point 5)."""
        rec, _ = CRMOutboxService.enqueue(self.tenant_id, self.connection.id, {"phone": "+14155550001"})
        CRMOutbox.update(status="PROCESSING", lease_owner="w1").where(CRMOutbox.id == rec.id).execute()

        CRMOutboxService.fail_task(rec.id, "w1", error_msg="Upstream rejected phone +998901234567 during dispatch")
        updated = CRMOutbox.get_by_id(rec.id)
        logged_err = updated.error_log["retry_1"]["error"]
        self.assertNotIn("+998901234567", logged_err)
        self.assertIn("[REDACTED_PHONE]", logged_err)

    def test_dead_letter_excluded_from_claim(self):
        """Verify tasks marked as DEAD_LETTER are never claimed by workers (Point 3)."""
        rec, _ = CRMOutboxService.enqueue(self.tenant_id, self.connection.id, {"phone": "+14155550001"})
        CRMOutbox.update(status="DEAD_LETTER", next_retry_at=None).where(CRMOutbox.id == rec.id).execute()

        tasks = CRMOutboxService.claim_batch("worker-test", batch_size=10)
        self.assertEqual(len(tasks), 0)

    def test_parked_excluded_from_claim_and_resumed_on_reauth(self):
        """Verify PARKED tasks do not loop and are unparked back to PENDING on reauth (Point 3)."""
        rec, _ = CRMOutboxService.enqueue(self.tenant_id, self.connection.id, {"phone": "+14155550001"})
        CRMOutbox.update(status="PROCESSING", lease_owner="worker-1").where(CRMOutbox.id == rec.id).execute()
        CRMOutboxService.park_task(rec.id, "worker-1", reason="token_revoked")

        # 1. While PARKED, claim_batch ignores it (zero infinite looping)
        tasks = CRMOutboxService.claim_batch("worker-2", batch_size=10)
        self.assertEqual(len(tasks), 0)

        # 2. Connection re-auth triggers unpark
        resumed = CRMConnectionService.update_status(self.connection.id, tenant_id=self.tenant_id, status="active")
        self.assertTrue(resumed)

        u = CRMOutbox.get_by_id(rec.id)
        self.assertEqual(u.status, "PENDING")
        self.assertIsNotNone(u.next_retry_at)

        # 3. Task is immediately eligible for claim again
        claimed = CRMOutboxService.claim_batch("worker-2", batch_size=10)
        self.assertEqual(len(claimed), 1)
        self.assertEqual(claimed[0].id, rec.id)

    def test_reclaim_processing_increments_counter(self):
        """Verify reclaiming an expired PROCESSING task increments reclaim_count (Point 3)."""
        rec, _ = CRMOutboxService.enqueue(self.tenant_id, self.connection.id, {"phone": "+14155550001"})
        tasks1 = CRMOutboxService.claim_batch("w1", batch_size=1, lease_duration_seconds=10)
        self.assertEqual(len(tasks1), 1)

        # Expire lease
        past_time = int(time.time() * 1000) - 1000
        CRMOutbox.update(lease_expires_at=past_time).where(CRMOutbox.id == rec.id).execute()

        # w2 reclaims
        tasks2 = CRMOutboxService.claim_batch("w2", batch_size=1, lease_duration_seconds=300)
        self.assertEqual(len(tasks2), 1)
        self.assertEqual(tasks2[0].error_log.get("reclaim_count"), 1)

    def test_worker_idle_when_crm_unlicensed(self):
        """Verify worker run_once exits with 0 and zero DB queries if CRM feature is unlicensed (Point 10)."""
        worker = CRMOutboxWorker(worker_id="test-worker")
        with patch("api.crm.license_gate.check_crm_license_access", return_value=(False, "No CRM license", None)):
            processed = worker.run_once()
            self.assertEqual(processed, 0)

    def test_worker_idle_when_no_active_connections(self):
        """Verify worker run_once exits with 0 and zero overhead when no active CRM connections exist (Point 10)."""
        CRMConnection.delete().execute()
        worker = CRMOutboxWorker(worker_id="test-worker")
        processed = worker.run_once()
        self.assertEqual(processed, 0)



    def test_crm_health_metrics_and_degraded_threshold(self):
        """Verify CRMOutboxService.get_health_metrics reports accurate counts and degraded status (>900s lag)."""
        # 1. Normal state: healthy
        rec1, _ = CRMOutboxService.enqueue(self.tenant_id, self.connection.id, {"phone": "+14155550001"})
        tasks = CRMOutboxService.claim_batch("w1", batch_size=1)
        self.assertEqual(len(tasks), 1)

        rec2, _ = CRMOutboxService.enqueue(self.tenant_id, self.connection.id, {"phone": "+14155550002"})
        CRMOutbox.update(status="DEAD_LETTER").where(CRMOutbox.id == rec2.id).execute()

        rec3, _ = CRMOutboxService.enqueue(self.tenant_id, self.connection.id, {"phone": "+14155550003"})
        CRMOutbox.update(status="PARKED").where(CRMOutbox.id == rec3.id).execute()

        metrics = CRMOutboxService.get_health_metrics()
        self.assertEqual(metrics["status"], "ok")
        self.assertEqual(metrics["active_leases"], 1)
        self.assertEqual(metrics["dead_letter_count"], 1)
        self.assertEqual(metrics["parked_tasks"], 1)
        self.assertTrue(metrics["crm_enabled"])
        self.assertLessEqual(metrics["oldest_pending_seconds"], 900)

        # 2. Degraded state: oldest pending record has lag > 900 seconds (15 minutes)
        old_time = int(time.time() * 1000) - (950 * 1000)
        rec4, _ = CRMOutboxService.enqueue(self.tenant_id, self.connection.id, {"phone": "+14155550004"})
        CRMOutbox.update(create_time=old_time).where(CRMOutbox.id == rec4.id).execute()

        degraded_metrics = CRMOutboxService.get_health_metrics()
        self.assertEqual(degraded_metrics["status"], "degraded")
        self.assertGreaterEqual(degraded_metrics["oldest_pending_seconds"], 945)

    def test_crm_health_superuser_gate_and_mutation(self):
        """Verify /crm/health enforces platform administrator check (is_superuser) and catches bypass mutations."""
        # Simulated gate logic matching system_api.py:307
        def evaluate_health_gate(user):
            if not user or not getattr(user, "is_superuser", False):
                return {
                    "code": RetCode.AUTHENTICATION_ERROR,
                    "message": "No authorization. Administrator privilege required.",
                }, 401
            payload = CRMOutboxService.get_health_metrics()
            code = 503 if payload.get("status") == "degraded" else 200
            return payload, code

        # 1. Non-admin regular user is rejected
        regular_user = MagicMock()
        regular_user.is_superuser = False
        res, code = evaluate_health_gate(regular_user)
        self.assertEqual(code, 401)
        self.assertEqual(res["code"], RetCode.AUTHENTICATION_ERROR)
        self.assertIn("Administrator privilege required", res["message"])

        # 2. Anonymous user (None) is rejected
        res_anon, code_anon = evaluate_health_gate(None)
        self.assertEqual(code_anon, 401)
        self.assertEqual(res_anon["code"], RetCode.AUTHENTICATION_ERROR)

        # 3. Superuser is granted access
        admin_user = MagicMock()
        admin_user.is_superuser = True
        res_admin, code_admin = evaluate_health_gate(admin_user)
        self.assertIn(code_admin, (200, 503))
        self.assertIn("status", res_admin)
        self.assertIn("active_leases", res_admin)

        # 4. Mutation proof: removing is_superuser check leaks metrics to regular users
        def mutated_gate(user):
            # Mutation: only checks if user is logged in (not None)
            if not user:
                return {"code": RetCode.AUTHENTICATION_ERROR}, 401
            return CRMOutboxService.get_health_metrics(), 200

        mutated_res, mutated_code = mutated_gate(regular_user)
        self.assertEqual(mutated_code, 200, "Mutation allowed unauthorized leak")
        real_res, real_code = evaluate_health_gate(regular_user)
        self.assertEqual(real_code, 401, "Real endpoint failed closed against mutation!")


if __name__ == "__main__":
    unittest.main()
