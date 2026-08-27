#
#  Copyright 2026 The InfiniFlow & Swipies AI Authors. All Rights Reserved.
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
import asyncio
import os
import sys
import types
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Stub out heavy/optional drivers if not present
from sqlalchemy.types import TypeEngine

class _ArrayClass(TypeEngine):
    def __init__(self, *args, **kwargs):
        super().__init__()

class _VectorClass(TypeEngine):
    def __init__(self, *args, **kwargs):
        super().__init__()

pyob = types.ModuleType("pyobvector")
pyob.ARRAY = _ArrayClass
pyob.VECTOR = _VectorClass
pyob.ObVecClient = MagicMock()
pyob.FtsIndexParam = MagicMock()
pyob.FtsParser = MagicMock()
sys.modules["pyobvector"] = pyob

valkey_mod = types.ModuleType("valkey")
valkey_mod.__path__ = []
valkey_mod.Redis = MagicMock()
valkey_mod.StrictRedis = MagicMock()
valkey_mod.ConnectionPool = MagicMock()
valkey_lock = types.ModuleType("valkey.lock")
valkey_lock.Lock = MagicMock()
valkey_mod.lock = valkey_lock
sys.modules["valkey"] = valkey_mod
sys.modules["valkey.lock"] = valkey_lock

redis_mod = types.ModuleType("redis")
redis_mod.__path__ = []
redis_mod.Redis = MagicMock()
redis_mod.StrictRedis = MagicMock()
redis_mod.ConnectionPool = MagicMock()
redis_lock = types.ModuleType("redis.lock")
redis_lock.Lock = MagicMock()
redis_mod.lock = redis_lock
sys.modules["redis"] = redis_mod
sys.modules["redis.lock"] = redis_lock

langfuse_mod = types.ModuleType("langfuse")
langfuse_mod.Langfuse = MagicMock()
langfuse_mod.propagate_attributes = MagicMock()
sys.modules["langfuse"] = langfuse_mod

from peewee import SqliteDatabase

TEST_ENFORCE_DB_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_wipe_temp.db"))
test_db = SqliteDatabase(TEST_ENFORCE_DB_FILE)

from api.db.db_models import (
    DB,
    DataBaseModel,
    AIProvider,
    AIModel,
    SubscriptionPlan,
    SubscriptionAIPolicy,
    UserTokenLimit,
    TokenUsageLog,
    User,
    Tenant,
    TenantLLM,
)
from api.db.services.ai_policy_service import AIPolicyManager
from common.ai_gateway.gateway import ai_gateway
from common.ai_gateway.credential_resolver import CredentialResolver
from common.ai_gateway.types import (
    ProviderType,
    GatewayChatRequest,
    GatewayChatResponse,
    GatewayMessage,
    TokenUsage,
)
from common.ai_gateway.errors import ModelGloballyDisabledError


class TestProviderWipeCascadeAndReactivation(unittest.IsolatedAsyncioTestCase):
    """
    Automated Test for Provider Wipe Cascade and Auto-Reactivation (TASK-08):
    1. Active Provider -> Models Enabled -> Requests OK.
    2. Wipe Key -> Provider status 'unconfigured' -> All Models cascaded to 'unconfigured_provider' / disabled=True.
    3. Level 2 Gate Interception -> Blocked with ModelGloballyDisabledError (403/GLOBALLY_DISABLED).
    4. Re-enter Key -> Provider status 'verified' -> All Models auto-reactivated to 'active' / enabled=True.
    5. Level 2 Gate Passed -> Requests OK.
    """

    @classmethod
    def setUpClass(cls):
        DB.connection_context = test_db.connection_context
        DB.atomic = test_db.atomic
        DB.transaction = test_db.transaction
        DB.connect = test_db.connect
        DB.close = test_db.close
        DB.is_closed = test_db.is_closed
        DB.execute_sql = test_db.execute_sql

        cls.models = [
            AIProvider,
            AIModel,
            SubscriptionPlan,
            SubscriptionAIPolicy,
            UserTokenLimit,
            TokenUsageLog,
            User,
            Tenant,
            TenantLLM,
        ]
        test_db.bind(cls.models, bind_refs=False, bind_backrefs=False)
        test_db.connect(reuse_if_open=True)
        test_db.drop_tables(cls.models, safe=True)
        test_db.create_tables(cls.models)

        # Clear memory store
        CredentialResolver._memory_store.clear()

        # Seed User & Tenant (PRO plan)
        Tenant.create(
            id="tenant_wipe_test",
            name="Wipe Test Tenant",
            plan_type="pro",
            llm_id="test_provider/model-alpha",
            embd_id="",
            asr_id="",
            img2txt_id="",
            rerank_id="",
            parser_ids="naive",
        )
        User.create(id="user_wipe_test", nickname="WipeTester", email="wipe@test.com", is_superuser=False)

        # Seed PRO Plan
        SubscriptionPlan.create(
            id="pro",
            name="PRO",
            monthly_token_limit=50000000,
            daily_token_limit=2000000,
            daily_request_limit=20000,
            monthly_request_limit=500000,
            allow_byok=True,
            max_byok_models=10,
            status="1",
        )

        # 1. Seed Active Provider
        AIProvider.create(
            id="test_provider",
            provider_name="test_provider",
            display_name="Test Provider",
            api_key="sk-initial-valid-key-12345",
            status="verified",
            is_global=True,
            extra={"excluded_models": []},
        )

        # 2. Seed Models for this provider
        AIModel.create(
            id="test_provider/model-alpha",
            provider="test_provider",
            model_name="model-alpha",
            model_type="CHAT",
            enabled=True,
            status="active",
            is_global=True,
            is_custom=False,
            extra={"allowed_plans": ["pro", "plus", "free"]},
        )
        AIModel.create(
            id="test_provider/model-beta",
            provider="test_provider",
            model_name="model-beta",
            model_type="CHAT",
            enabled=True,
            status="active",
            is_global=True,
            is_custom=False,
            extra={"allowed_plans": ["pro", "plus", "free"]},
        )

    @classmethod
    def tearDownClass(cls):
        test_db.drop_tables(cls.models, safe=True)
        test_db.close()
        if os.path.exists(TEST_ENFORCE_DB_FILE):
            try:
                os.remove(TEST_ENFORCE_DB_FILE)
            except Exception:
                pass

    async def test_full_wipe_cascade_and_autoreactivation_lifecycle(self):
        """
        Comprehensive test of the Wipe Cascade lifecycle:
        Active -> Wipe -> Cascade Disabled -> Blocked at Level 2 -> Restore Key -> Auto-Reactivated -> Allowed.
        """
        # =====================================================================
        # Phase 1: INITIAL STATE (Provider has valid key & models are active)
        # =====================================================================
        prov = AIProvider.get(AIProvider.provider_name == "test_provider")
        self.assertEqual(prov.status, "verified")
        self.assertEqual(prov.api_key, "sk-initial-valid-key-12345")

        models = list(AIModel.select().where(AIModel.provider == "test_provider"))
        self.assertEqual(len(models), 2)
        for m in models:
            self.assertTrue(m.enabled)
            self.assertEqual(m.status, "active")

        # Level 2 check must pass (200 OK)
        allowed, msg, status_code, err_code = AIPolicyManager.check_model_access_extended(
            tenant_id="tenant_wipe_test",
            model_name="test_provider/model-alpha",
            user_id="user_wipe_test",
        )
        self.assertTrue(allowed, f"Expected allowed in initial state, got: {msg}")
        self.assertEqual(status_code, 200)
        self.assertEqual(err_code, "OK")
        print("\n  [PASS] Step 1: Initial state verified - Provider 'test_provider' is active, models are enabled and accessible (200 OK).")

        # =====================================================================
        # Phase 2: WIPE API KEY (Admin wipes provider key)
        # =====================================================================
        wipe_result = CredentialResolver.wipe_provider_api_key("test_provider")
        self.assertTrue(wipe_result.get("wiped"))
        self.assertEqual(wipe_result.get("status"), "unconfigured")
        self.assertEqual(wipe_result.get("models_disabled_count"), 2)

        # Verify AIProvider in DB
        prov_after_wipe = AIProvider.get(AIProvider.provider_name == "test_provider")
        self.assertIsNone(prov_after_wipe.api_key)
        self.assertEqual(prov_after_wipe.status, "unconfigured")

        # Verify AIModel Cascade Disable
        models_after_wipe = list(AIModel.select().where(AIModel.provider == "test_provider"))
        self.assertEqual(len(models_after_wipe), 2)
        for m in models_after_wipe:
            self.assertFalse(m.enabled, f"Model {m.id} should be disabled after wipe")
            self.assertEqual(m.status, "unconfigured_provider", f"Model {m.id} status should be 'unconfigured_provider'")
        print("  [PASS] Step 2: Wipe Cascade executed - AIProvider api_key=None, status='unconfigured'; 2 AIModels cascaded to status='unconfigured_provider', enabled=False.")

        # =====================================================================
        # Phase 3: LEVEL 2 PRE-FLIGHT INTERCEPTION UNDER WIPED STATE
        # =====================================================================
        allowed, msg, status_code, err_code = AIPolicyManager.check_model_access_extended(
            tenant_id="tenant_wipe_test",
            model_name="test_provider/model-alpha",
            user_id="user_wipe_test",
        )
        self.assertFalse(allowed)
        self.assertEqual(status_code, 403)
        self.assertEqual(err_code, "GLOBALLY_DISABLED")
        self.assertIn("unavailable because provider 'test_provider' has no configured API key", msg)

        # Also verify through Gateway call
        mock_provider_impl = AsyncMock()
        with patch.object(ai_gateway, "get_provider", return_value=mock_provider_impl):
            req = GatewayChatRequest(
                messages=[GatewayMessage(role="user", content="Test")],
                model="test_provider/model-alpha",
                tenant_id="tenant_wipe_test",
                user_id="user_wipe_test",
            )
            with self.assertRaises(ModelGloballyDisabledError) as ctx:
                await ai_gateway.chat(req)
            self.assertEqual(ctx.exception.status_code, 403)
            self.assertEqual(ctx.exception.error_code, "GLOBALLY_DISABLED")

        print("  [PASS] Step 3: Level 2 Pre-flight Gate successfully intercepted request with ModelGloballyDisabledError (403/GLOBALLY_DISABLED).")

        # =====================================================================
        # Phase 4: AUTO-REACTIVATION CASCADE (Admin enters a new valid API key)
        # =====================================================================
        saved_rec = CredentialResolver.save_provider_credentials(
            provider_type="test_provider",
            api_key="sk-new-reactivated-key-99999",
            is_active=True,
        )
        self.assertTrue(saved_rec.is_configured)
        self.assertTrue(saved_rec.masked_api_key.startswith("sk-") and saved_rec.masked_api_key.endswith("9999"))

        # Verify AIProvider in DB
        prov_reactivated = AIProvider.get(AIProvider.provider_name == "test_provider")
        self.assertEqual(prov_reactivated.status, "verified")
        self.assertEqual(prov_reactivated.api_key, "sk-new-reactivated-key-99999")

        # Verify AIModel Auto-Reactivation
        models_reactivated = list(AIModel.select().where(AIModel.provider == "test_provider"))
        self.assertEqual(len(models_reactivated), 2)
        for m in models_reactivated:
            self.assertTrue(m.enabled, f"Model {m.id} should be re-enabled after key restore")
            self.assertEqual(m.status, "active", f"Model {m.id} status should be 'active'")
        print("  [PASS] Step 4: Auto-Reactivation Cascade executed - AIProvider status='verified'; all 2 AIModels restored to status='active', enabled=True.")

        # =====================================================================
        # Phase 5: LEVEL 2 PRE-FLIGHT CHECK UNDER RESTORED STATE
        # =====================================================================
        allowed, msg, status_code, err_code = AIPolicyManager.check_model_access_extended(
            tenant_id="tenant_wipe_test",
            model_name="test_provider/model-alpha",
            user_id="user_wipe_test",
        )
        self.assertTrue(allowed, f"Expected allowed after reactivation, got: {msg}")
        self.assertEqual(status_code, 200)
        self.assertEqual(err_code, "OK")

        # Verify Gateway execution
        mock_provider_impl = AsyncMock()
        mock_provider_impl.chat_complete.return_value = GatewayChatResponse(
            id="resp_reactivated_01",
            provider="test_provider",
            model="test_provider/model-alpha",
            content="Hello from restored model!",
            usage=TokenUsage(prompt_tokens=5, completion_tokens=5, total_tokens=10),
        )
        with patch.object(ai_gateway, "get_provider", return_value=mock_provider_impl):
            req = GatewayChatRequest(
                messages=[GatewayMessage(role="user", content="Hello")],
                model="test_provider/model-alpha",
                tenant_id="tenant_wipe_test",
                user_id="user_wipe_test",
            )
            resp = await ai_gateway.chat(req)
            self.assertEqual(resp.content, "Hello from restored model!")

        print("  [PASS] Step 5: Level 2 Pre-flight Gate and AI Gateway request successfully completed (200 OK) with the restored key.\n")


if __name__ == "__main__":
    unittest.main()
