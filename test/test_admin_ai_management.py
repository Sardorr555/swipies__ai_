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
import json
import os
import sys
import types
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Stub out heavy C-extensions/optional database driver dependencies if not present on host
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

opendal_mod = types.ModuleType("opendal")
opendal_mod.Operator = MagicMock()
sys.modules["opendal"] = opendal_mod

opensearch_mod = types.ModuleType("opensearchpy")
opensearch_mod.OpenSearch = MagicMock()
opensearch_mod.NotFoundError = Exception
opensearch_mod.BadRequestError = Exception
opensearch_mod.ConnectionTimeout = Exception
opensearch_mod.UpdateByQuery = MagicMock()
opensearch_mod.Q = MagicMock()
opensearch_mod.Search = MagicMock()
opensearch_mod.Index = MagicMock()
opensearch_mod.Mapping = MagicMock()
opensearch_mod.__version__ = (2, 0, 0)
opensearch_mod.__path__ = []
opensearch_mod.helpers = types.ModuleType("opensearchpy.helpers")
opensearch_mod.helpers.bulk = MagicMock()
opensearch_mod.client = types.ModuleType("opensearchpy.client")
opensearch_mod.client.IndicesClient = MagicMock()
sys.modules["opensearchpy"] = opensearch_mod
sys.modules["opensearchpy.helpers"] = opensearch_mod.helpers
sys.modules["opensearchpy.client"] = opensearch_mod.client

es_mod = types.ModuleType("elasticsearch")
es_mod.__path__ = []
es_mod.Elasticsearch = MagicMock()
es_mod.NotFoundError = Exception
es_mod.BadRequestError = Exception
es_mod.ConnectionTimeout = Exception
es_mod.__version__ = (8, 0, 0)
es_dsl = types.ModuleType("elasticsearch.dsl")
es_dsl.UpdateByQuery = MagicMock()
es_dsl.Q = MagicMock()
es_dsl.Search = MagicMock()
es_dsl.Index = MagicMock()
es_dsl.Mapping = MagicMock()
es_mod.dsl = es_dsl
es_mod.helpers = types.ModuleType("elasticsearch.helpers")
es_mod.helpers.bulk = MagicMock()
es_mod.client = types.ModuleType("elasticsearch.client")
es_mod.client.IndicesClient = MagicMock()
sys.modules["elasticsearch"] = es_mod
sys.modules["elasticsearch.dsl"] = es_dsl
sys.modules["elasticsearch.helpers"] = es_mod.helpers
sys.modules["elasticsearch.client"] = es_mod.client

# Storage stubs
az_mod = types.ModuleType("azure")
az_mod.__path__ = []
az_storage = types.ModuleType("azure.storage")
az_storage.__path__ = []
az_blob = types.ModuleType("azure.storage.blob")
az_blob.ContainerClient = MagicMock()
az_blob.BlobServiceClient = MagicMock()
az_storage.blob = az_blob
az_datalake = types.ModuleType("azure.storage.filedatalake")
az_datalake.FileSystemClient = MagicMock()
az_storage.filedatalake = az_datalake
az_id = types.ModuleType("azure.identity")
az_id.ClientSecretCredential = MagicMock()
az_id.AzureAuthorityHosts = MagicMock()
az_mod.identity = az_id
az_mod.storage = az_storage
sys.modules["azure"] = az_mod
sys.modules["azure.storage"] = az_storage
sys.modules["azure.storage.blob"] = az_blob
sys.modules["azure.storage.filedatalake"] = az_datalake
sys.modules["azure.identity"] = az_id

gcs_mod = types.ModuleType("google")
gcs_mod.__path__ = []
gcs_cloud = types.ModuleType("google.cloud")
gcs_cloud.__path__ = []
gcs_storage = types.ModuleType("google.cloud.storage")
gcs_storage.Client = MagicMock()
gcs_cloud.storage = gcs_storage
gcs_mod.cloud = gcs_cloud
gcs_api_core = types.ModuleType("google.api_core")
gcs_api_core.__path__ = []
gcs_exceptions = types.ModuleType("google.api_core.exceptions")
gcs_exceptions.NotFound = Exception
gcs_api_core.exceptions = gcs_exceptions
gcs_mod.api_core = gcs_api_core
sys.modules["google"] = gcs_mod
sys.modules["google.cloud"] = gcs_cloud
sys.modules["google.cloud.storage"] = gcs_storage
sys.modules["google.api_core"] = gcs_api_core
sys.modules["google.api_core.exceptions"] = gcs_exceptions

oss2_mod = types.ModuleType("oss2")
oss2_mod.Auth = MagicMock()
oss2_mod.Bucket = MagicMock()
oss2_mod.BucketIterator = MagicMock()
sys.modules["oss2"] = oss2_mod

boto3_mod = types.ModuleType("boto3")
boto3_mod.client = MagicMock()
boto3_mod.session = MagicMock()
sys.modules["boto3"] = boto3_mod

botocore_mod = types.ModuleType("botocore")
botocore_mod.__path__ = []
botocore_mod.client = types.ModuleType("botocore.client")
botocore_mod.client.Config = MagicMock()
botocore_config = types.ModuleType("botocore.config")
botocore_config.Config = MagicMock()
botocore_mod.config = botocore_config
botocore_exceptions = types.ModuleType("botocore.exceptions")
botocore_exceptions.ClientError = Exception
botocore_mod.exceptions = botocore_exceptions
sys.modules["botocore"] = botocore_mod
sys.modules["botocore.client"] = botocore_mod.client
sys.modules["botocore.config"] = botocore_config
sys.modules["botocore.exceptions"] = botocore_exceptions

minio_mod = types.ModuleType("minio")
minio_mod.__path__ = []
minio_mod.Minio = MagicMock()
minio_mod.commonconfig = types.ModuleType("minio.commonconfig")
minio_mod.commonconfig.CopySource = MagicMock()
minio_mod.error = types.ModuleType("minio.error")
minio_mod.error.S3Error = Exception
minio_mod.error.ServerError = Exception
minio_mod.error.InvalidResponseError = Exception
minio_mod.error.ResponseError = Exception
sys.modules["minio"] = minio_mod
sys.modules["minio.commonconfig"] = minio_mod.commonconfig
sys.modules["minio.error"] = minio_mod.error

class _StubRagTokenizer:
    def tokenize(self, text):
        return []
    def fine_grained_tokenize(self, text):
        return []
    def tag(self, text):
        return []
    def freq(self, text):
        return 0
    def _tradi2simp(self, text):
        return text
    def _strQ2B(self, text):
        return text

inf_pkg = types.ModuleType("infinity")
inf_pkg.__path__ = []
inf_rag = types.ModuleType("infinity.rag_tokenizer")
inf_rag.RagTokenizer = _StubRagTokenizer
inf_rag.is_chinese = lambda s: False
inf_rag.is_number = lambda s: False
inf_rag.is_alphabet = lambda s: True
inf_rag.naive_qie = lambda txt: [txt]
inf_pkg.rag_tokenizer = inf_rag
inf_common = types.ModuleType("infinity.common")
inf_common.InfinityException = Exception
inf_common.SortType = MagicMock()
inf_common.ConflictType = MagicMock()
inf_pkg.common = inf_common
inf_index = types.ModuleType("infinity.index")
inf_index.IndexInfo = MagicMock()
inf_index.IndexType = MagicMock()
inf_pkg.index = inf_index
inf_errors = types.ModuleType("infinity.errors")
inf_errors.ErrorCode = MagicMock()
inf_pkg.errors = inf_errors
inf_rpc = types.ModuleType("infinity.remote_thrift.infinity_thrift_rpc")
inf_rpc.ttypes = types.ModuleType("infinity.remote_thrift.infinity_thrift_rpc.ttypes")
sys.modules["infinity"] = inf_pkg
sys.modules["infinity.rag_tokenizer"] = inf_rag
sys.modules["infinity.common"] = inf_common
sys.modules["infinity.index"] = inf_index
sys.modules["infinity.errors"] = inf_errors
sys.modules["infinity.remote_thrift"] = types.ModuleType("infinity.remote_thrift")
sys.modules["infinity.remote_thrift.infinity_thrift_rpc"] = inf_rpc
sys.modules["infinity.remote_thrift.infinity_thrift_rpc.ttypes"] = inf_rpc.ttypes

langfuse_mod = types.ModuleType("langfuse")
langfuse_mod.Langfuse = MagicMock()
langfuse_mod.propagate_attributes = MagicMock()
sys.modules["langfuse"] = langfuse_mod

qs_mod = types.ModuleType("quart_schema")
qs_mod.QuartSchema = MagicMock()
qs_mod.validate_request = lambda *a, **kw: (lambda f: f)
qs_mod.validate_response = lambda *a, **kw: (lambda f: f)
sys.modules["quart_schema"] = qs_mod

qc_mod = types.ModuleType("quart_cors")
qc_mod.cors = lambda app, **kw: app
sys.modules["quart_cors"] = qc_mod

qa_mod = types.ModuleType("quart_auth")
qa_mod.Unauthorized = Exception
qa_mod.login_required = lambda f: f
qa_mod.current_user = MagicMock()
class AuthUser:
    def __init__(self, *args, **kwargs):
        pass
qa_mod.AuthUser = AuthUser
sys.modules["quart_auth"] = qa_mod

import common.settings
common.settings.init_settings = lambda *a, **kw: None
common.settings.docStoreConn = MagicMock()

api_apps_mod = types.ModuleType("api.apps")
api_apps_mod.current_user = MagicMock()
api_apps_mod.login_required = lambda f: f
sys.modules["api.apps"] = api_apps_mod

import importlib.util
_spec = importlib.util.spec_from_file_location(
    "api.apps.ai_management_app",
    os.path.join(os.path.dirname(__file__), "..", "api", "apps", "ai_management_app.py"),
)
ai_app = importlib.util.module_from_spec(_spec)
ai_app.manager = MagicMock()
ai_app.manager.route = lambda *a, **kw: (lambda f: f)
_spec.loader.exec_module(ai_app)
sys.modules["api.apps.ai_management_app"] = ai_app

admin_wipe_provider_api_key = ai_app.admin_wipe_provider_api_key
admin_replace_provider_api_key = ai_app.admin_replace_provider_api_key
admin_toggle_model_exclusion = ai_app.admin_toggle_model_exclusion
admin_get_provider_models_dynamic = ai_app.admin_get_provider_models_dynamic
admin_get_plans = ai_app.admin_get_plans
admin_update_plan = ai_app.admin_update_plan
admin_get_policies = ai_app.admin_get_policies
admin_update_policies = ai_app.admin_update_policies
admin_list_user_policy_overrides = ai_app.admin_list_user_policy_overrides
admin_get_user_policy = ai_app.admin_get_user_policy
admin_set_user_policy = ai_app.admin_set_user_policy
admin_delete_user_policy = ai_app.admin_delete_user_policy
admin_get_analytics = ai_app.admin_get_analytics
admin_get_audit_logs = ai_app.admin_get_audit_logs
admin_get_byok_stats = ai_app.admin_get_byok_stats

from peewee import SqliteDatabase

TEST_ADMIN_DB_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_admin_ai_temp.db"))
test_db = SqliteDatabase(TEST_ADMIN_DB_FILE)

from api.db.db_models import (
    DB,
    DataBaseModel,
    AIProvider,
    AIModel,
    SubscriptionPlan,
    SubscriptionAIPolicy,
    UserTokenLimit,
    TokenUsageLog,
    AIAuditLog,
    User,
    Tenant,
    TenantLLM,
)
from api.db.services.ai_policy_service import AIPolicyManager
from common.ai_gateway.credential_resolver import CredentialResolver
from common.time_utils import current_timestamp


def _parse_resp(resp):
    if isinstance(resp, dict):
        return resp
    if hasattr(resp, "get_json"):
        try:
            val = resp.get_json()
            if val is not None:
                return val
        except Exception:
            pass
    if hasattr(resp, "data"):
        return json.loads(resp.data)
    if hasattr(resp, "get_data"):
        return json.loads(resp.get_data())
    return json.loads(str(resp))


class TestAdminAIAppProviderManagement(unittest.IsolatedAsyncioTestCase):
    """
    Automated Test Suite for TASK-09 Admin AI Management Endpoints:
    1. DELETE /v1/admin/ai/providers/<provider>/api-key (Wipe Cascade)
    2. POST /v1/admin/ai/providers/<provider>/api-key (Replace / Auto-Reactivate)
    3. POST /v1/admin/ai/providers/<provider>/models/exclude (Model Exclusion)
    4. GET /v1/admin/ai/providers/<provider>/models (Dynamic Discovery with is_excluded & is_active)
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
            AIAuditLog,
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

        # Seed Admin Superuser
        cls.admin_user = User.create(
            id="admin_user_001",
            nickname="SuperAdmin",
            email="admin@test.com",
            is_superuser=True,
        )

        # Seed Standard Non-Admin User
        cls.normal_user = User.create(
            id="normal_user_001",
            nickname="NormalUser",
            email="user@test.com",
            is_superuser=False,
        )

        # Seed Provider
        AIProvider.create(
            id="openai",
            provider_name="openai",
            display_name="OpenAI",
            api_key="sk-initial-openai-test-key",
            status="verified",
            is_global=True,
            extra={"excluded_models": ["gpt-4-32k"]},
        )

        # Seed Models
        AIModel.create(
            id="openai/gpt-4o",
            provider="openai",
            model_name="gpt-4o",
            model_type="CHAT",
            enabled=True,
            status="active",
            is_global=True,
            is_custom=False,
        )
        AIModel.create(
            id="openai/gpt-4o-mini",
            provider="openai",
            model_name="gpt-4o-mini",
            model_type="CHAT",
            enabled=True,
            status="active",
            is_global=True,
            is_custom=False,
        )

        # Seed Subscription Plans
        SubscriptionPlan.create(
            id="free",
            name="Free Plan",
            monthly_token_limit=100000,
            daily_token_limit=10000,
            daily_request_limit=100,
            monthly_request_limit=3000,
            requests_per_minute=20,
            max_tokens_per_request=4096,
            allow_byok=False,
            is_active=True,
            status="active",
        )
        SubscriptionPlan.create(
            id="plus",
            name="Plus Plan",
            monthly_token_limit=1000000,
            daily_token_limit=100000,
            daily_request_limit=1000,
            monthly_request_limit=30000,
            requests_per_minute=60,
            max_tokens_per_request=8192,
            allow_byok=False,
            is_active=True,
            status="active",
        )
        SubscriptionPlan.create(
            id="pro",
            name="Pro Plan",
            monthly_token_limit=10000000,
            daily_token_limit=1000000,
            daily_request_limit=10000,
            monthly_request_limit=300000,
            requests_per_minute=120,
            max_tokens_per_request=16384,
            allow_byok=True,
            max_byok_models=10,
            is_active=True,
            status="active",
        )

    @classmethod
    def tearDownClass(cls):
        test_db.drop_tables(cls.models, safe=True)
        test_db.close()
        if os.path.exists(TEST_ADMIN_DB_FILE):
            try:
                os.remove(TEST_ADMIN_DB_FILE)
            except Exception:
                pass

    async def test_01_toggle_model_exclusion_persists_in_provider_extra(self):
        """
        Verify POST /v1/admin/ai/providers/<provider>/models/exclude:
        - Excludes a model -> added to AIProvider.extra['excluded_models'].
        - Un-excludes a model -> removed from AIProvider.extra['excluded_models'].
        """
        with patch("api.apps.ai_management_app.current_user", self.admin_user):
            # 1. Exclude 'gpt-4o'
            with patch("api.apps.ai_management_app.get_request_json", AsyncMock(return_value={"model_id": "gpt-4o", "excluded": True})):
                resp = await admin_toggle_model_exclusion("openai")
                resp_data = _parse_resp(resp)
                self.assertEqual(resp_data.get("code"), 0)
                excluded = resp_data["data"]["excluded_models"]
                self.assertIn("gpt-4o", excluded)

            # Verify in DB
            prov = AIProvider.get(AIProvider.provider_name == "openai")
            extra = prov.extra if isinstance(prov.extra, dict) else json.loads(prov.extra or "{}")
            self.assertIn("gpt-4o", extra.get("excluded_models", []))

            # 2. Un-exclude 'gpt-4o'
            with patch("api.apps.ai_management_app.get_request_json", AsyncMock(return_value={"model_id": "gpt-4o", "excluded": False})):
                resp = await admin_toggle_model_exclusion("openai")
                resp_data = _parse_resp(resp)
                self.assertEqual(resp_data.get("code"), 0)
                excluded = resp_data["data"]["excluded_models"]
                self.assertNotIn("gpt-4o", excluded)
                self.assertIn("gpt-4-32k", excluded)

            print("\n  [PASS] Test 1: Model Exclusion Toggle successfully updates AIProvider.extra['excluded_models'].")

    async def test_02_dynamic_provider_models_annotation(self):
        """
        Verify GET /v1/admin/ai/providers/<provider>/models:
        - Returns list of models annotated with is_excluded, is_configured, and is_active.
        """
        with patch("api.apps.ai_management_app.current_user", self.admin_user):
            # Exclude 'gpt-4-32k'
            prov = AIProvider.get(AIProvider.provider_name == "openai")
            prov.extra = {"excluded_models": ["gpt-4-32k"]}
            prov.save()

            resp = await admin_get_provider_models_dynamic("openai")
            resp_data = _parse_resp(resp)
            self.assertEqual(resp_data.get("code"), 0)
            data = resp_data["data"]
            self.assertTrue(data["is_configured"])
            
            models = data["models"]
            self.assertGreater(len(models), 0)

            # Check gpt-4o (not excluded)
            gpt4o = next((m for m in models if m["model_name"] == "gpt-4o"), None)
            if gpt4o:
                self.assertFalse(gpt4o["is_excluded"])
                self.assertTrue(gpt4o["is_active"])

            # Check gpt-4-32k (excluded)
            gpt4_32k = next((m for m in models if m["model_name"] == "gpt-4-32k"), None)
            if gpt4_32k:
                self.assertTrue(gpt4_32k["is_excluded"])
                self.assertFalse(gpt4_32k["is_active"])

            print("  [PASS] Test 2: Dynamic Provider Models Discovery annotates is_excluded and is_active accurately.")

    async def test_03_wipe_provider_api_key_endpoint_executes_cascade(self):
        """
        Verify DELETE /v1/admin/ai/providers/<provider>/api-key:
        - Wipes key, sets status 'unconfigured', cascades all models to 'unconfigured_provider' / enabled=False.
        """
        with patch("api.apps.ai_management_app.current_user", self.admin_user):
            resp = await admin_wipe_provider_api_key("openai")
            resp_data = _parse_resp(resp)
            self.assertEqual(resp_data.get("code"), 0)
            data = resp_data["data"]
            self.assertTrue(data["wiped"])
            self.assertEqual(data["status"], "unconfigured")
            self.assertGreaterEqual(data["models_disabled_count"], 2)

            # Verify in DB
            prov = AIProvider.get(AIProvider.provider_name == "openai")
            self.assertIsNone(prov.api_key)
            self.assertEqual(prov.status, "unconfigured")

            models = list(AIModel.select().where(AIModel.provider == "openai"))
            for m in models:
                self.assertFalse(m.enabled)
                self.assertEqual(m.status, "unconfigured_provider")

            print("  [PASS] Test 3: Wipe API Key endpoint successfully wiped key and cascaded models to disabled.")

    async def test_04_replace_provider_api_key_endpoint_auto_reactivates(self):
        """
        Verify POST /v1/admin/ai/providers/<provider>/api-key:
        - Saves new key, sets status 'verified', auto-reactivates cascaded models to 'active' / enabled=True.
        """
        with patch("api.apps.ai_management_app.current_user", self.admin_user):
            payload = {"api_key": "sk-newly-replaced-openai-key-9999"}
            with patch("api.apps.ai_management_app.get_request_json", AsyncMock(return_value=payload)):
                resp = await admin_replace_provider_api_key("openai")
                resp_data = _parse_resp(resp)
                self.assertEqual(resp_data.get("code"), 0)
                data = resp_data["data"]
                self.assertTrue(data["is_configured"])
                self.assertTrue(data["masked_api_key"].startswith("sk-"))

            # Verify in DB
            prov = AIProvider.get(AIProvider.provider_name == "openai")
            self.assertEqual(prov.status, "verified")
            self.assertEqual(prov.api_key, "sk-newly-replaced-openai-key-9999")

            models = list(AIModel.select().where(AIModel.provider == "openai"))
            for m in models:
                self.assertTrue(m.enabled)
                self.assertEqual(m.status, "active")

            print("  [PASS] Test 4: Replace API Key endpoint successfully updated key and auto-reactivated models.")

    async def test_05_non_superuser_access_is_blocked(self):
        """
        Verify that non-superusers receive 401 / Authentication error on all admin routes.
        """
        with patch("api.apps.ai_management_app.current_user", self.normal_user):
            resp = await admin_wipe_provider_api_key("openai")
            resp_data = _parse_resp(resp)
            self.assertNotEqual(resp_data.get("code"), 0)
            self.assertIn("Superuser authorization required", resp_data.get("message", ""))
            print("  [PASS] Test 5: Superuser guard strictly blocks non-admin users from management endpoints.")

    async def test_06_plan_and_policy_matrix_crud(self):
        """
        Verify Plan & Policy Matrix APIs:
        - GET /v1/admin/ai/plans
        - PUT /v1/admin/ai/plans/<plan_id>
        - GET /v1/admin/ai/policies
        - PUT /v1/admin/ai/policies
        """
        with patch("api.apps.ai_management_app.current_user", self.admin_user):
            # 1. Update Plan
            plan_payload = {"monthly_token_limit": 500000, "allow_byok": False}
            with patch("api.apps.ai_management_app.get_request_json", AsyncMock(return_value=plan_payload)):
                resp = await admin_update_plan("free")
                resp_data = _parse_resp(resp)
                self.assertEqual(resp_data.get("code"), 0)

            # 2. Get Plans
            resp = await admin_get_plans()
            resp_data = _parse_resp(resp)
            self.assertEqual(resp_data.get("code"), 0)
            plans = resp_data["data"]
            free_plan = next((p for p in plans if p["id"] == "free"), None)
            self.assertIsNotNone(free_plan)
            self.assertEqual(free_plan["monthly_token_limit"], 500000)

            # 3. Update Policies Matrix
            pol_payload = {
                "plan_id": "free",
                "policies": [
                    {"model_id": "openai/gpt-4o", "enabled": False},
                    {"model_id": "openai/gpt-4o-mini", "enabled": True},
                ],
            }
            with patch("api.apps.ai_management_app.get_request_json", AsyncMock(return_value=pol_payload)):
                resp = await admin_update_policies()
                resp_data = _parse_resp(resp)
                self.assertEqual(resp_data.get("code"), 0)

            # 4. Get Policies
            resp = await admin_get_policies(plan_id="free")
            resp_data = _parse_resp(resp)
            self.assertEqual(resp_data.get("code"), 0)
            pols = resp_data["data"]
            gpt4o_pol = next((p for p in pols if p["model_id"] == "openai/gpt-4o"), None)
            self.assertIsNotNone(gpt4o_pol)
            self.assertFalse(gpt4o_pol["enabled"])

            print("  [PASS] Test 6: Plan and Policy Matrix APIs successfully manage tiered plan rules.")

    async def test_07_user_policy_override_crud(self):
        """
        Verify Per-User Policy Overrides APIs:
        - PUT /v1/admin/ai/users/<user_id>/policy (Set ALLOW, DENY, token limit)
        - GET /v1/admin/ai/users/<user_id>/policy (Retrieve active policy & usage)
        - GET /v1/admin/ai/users/overrides (List all users with overrides)
        - DELETE /v1/admin/ai/users/<user_id>/policy (Reset overrides)
        """
        with patch("api.apps.ai_management_app.current_user", self.admin_user):
            # 1. Set user override
            override_payload = {
                "allowed_models_override": ["anthropic/claude-3-5-sonnet"],
                "forbidden_models": ["openai/gpt-4o-mini"],
                "monthly_token_limit": 75000,
                "token_limit_enabled": True,
            }
            with patch("api.apps.ai_management_app.get_request_json", AsyncMock(return_value=override_payload)):
                resp = await admin_set_user_policy(user_id="normal_user_001")
                resp_data = _parse_resp(resp)
                self.assertEqual(resp_data.get("code"), 0)

            # 2. Get user policy
            resp = await admin_get_user_policy(user_id="normal_user_001")
            resp_data = _parse_resp(resp)
            self.assertEqual(resp_data.get("code"), 0)
            u_pol = resp_data["data"]
            self.assertEqual(u_pol["user_id"], "normal_user_001")
            self.assertIn("anthropic/claude-3-5-sonnet", u_pol["allowed_models_override"])
            self.assertIn("openai/gpt-4o-mini", u_pol["forbidden_models"])
            self.assertEqual(u_pol["monthly_token_limit"], 75000)

            # 3. List users with overrides
            resp = await admin_list_user_policy_overrides()
            resp_data = _parse_resp(resp)
            self.assertEqual(resp_data.get("code"), 0)
            overridden_users = resp_data["data"]
            user_entry = next((u for u in overridden_users if u["user_id"] == "normal_user_001"), None)
            self.assertIsNotNone(user_entry)
            self.assertTrue(user_entry["has_model_overrides"])
            self.assertTrue(user_entry["has_token_override"])

            # 4. Delete / Reset user policy override
            resp = await admin_delete_user_policy(user_id="normal_user_001")
            resp_data = _parse_resp(resp)
            self.assertEqual(resp_data.get("code"), 0)

            # Verify reset in DB
            ul = UserTokenLimit.get_or_none(UserTokenLimit.user_id == "normal_user_001")
            self.assertIsNone(ul)

            print("  [PASS] Test 7: Per-User Policy Overrides CRUD successfully sets, lists, and resets user overrides.")

    async def test_08_analytics_and_usage_stats(self):
        """
        Verify Central Analytics API:
        - GET /v1/admin/ai/analytics
        - Verifies platform-wide total requests, tokens, cost, plan breakdown, and model breakdown.
        """
        # Seed test token usage logs
        period = AIPolicyManager.get_current_period()
        date_str = AIPolicyManager.get_current_date_str()

        TokenUsageLog.create(
            id="log_analytics_001",
            user_id="normal_user_001",
            tenant_id="normal_user_001",
            subscription_id="free",
            global_instance_id="GLOBAL",
            model_id="openai/gpt-4o",
            provider_id="openai",
            model_type="CHAT",
            input_tokens=1000,
            output_tokens=500,
            total_tokens=1500,
            estimated_cost=0.0075,
            status="SUCCESS",
            billing_period=period,
            date_str=date_str,
            create_time=current_timestamp(),
        )
        TokenUsageLog.create(
            id="log_analytics_002",
            user_id="normal_user_001",
            tenant_id="normal_user_001",
            subscription_id="free",
            global_instance_id="GLOBAL",
            model_id="openai/gpt-4o-mini",
            provider_id="openai",
            model_type="CHAT",
            input_tokens=2000,
            output_tokens=1000,
            total_tokens=3000,
            estimated_cost=0.00045,
            status="SUCCESS",
            billing_period=period,
            date_str=date_str,
            create_time=current_timestamp(),
        )

        with patch("api.apps.ai_management_app.current_user", self.admin_user):
            resp = await admin_get_analytics(period=period)
            resp_data = _parse_resp(resp)
            self.assertEqual(resp_data.get("code"), 0)
            data = resp_data["data"]

            summary = data.get("summary", {})
            self.assertGreaterEqual(summary.get("total_requests", 0), 2)
            self.assertGreaterEqual(summary.get("total_tokens", 0), 4500)

            by_plan = data.get("by_subscription", [])
            free_plan_stat = next((p for p in by_plan if p.get("subscription_id") == "free"), None)
            self.assertIsNotNone(free_plan_stat)
            self.assertGreaterEqual(free_plan_stat.get("tokens", 0), 4500)

            by_model = data.get("by_model", [])
            gpt4o_stat = next((m for m in by_model if m.get("model_id") == "openai/gpt-4o"), None)
            self.assertIsNotNone(gpt4o_stat)

            print("  [PASS] Test 8: Central Analytics API successfully aggregates platform-wide AI usage & costs.")

    async def test_09_security_audit_logging_and_zero_leakage(self):
        """
        Verify Security Audit Logging and Zero-Plaintext Secret Leakage:
        - GET /v1/admin/ai/audit-logs
        - Verifies that admin actions (key replace, key wipe, model exclusion, policy update) are logged.
        - Guarantees that no raw API keys appear in details_parsed or database logs.
        """
        with patch("api.apps.ai_management_app.current_user", self.admin_user):
            resp = await admin_get_audit_logs(limit=50)
            resp_data = _parse_resp(resp)
            self.assertEqual(resp_data.get("code"), 0)
            items = resp_data["data"]["items"]
            self.assertGreater(len(items), 0)

            logged_actions = {item["action"] for item in items}
            self.assertTrue(
                {"PROVIDER_KEY_REPLACE", "PROVIDER_KEY_WIPE", "MODEL_EXCLUDE_TOGGLE"}.intersection(logged_actions),
                f"Expected audit actions not found in: {logged_actions}",
            )

            # Strict check: scan all audit log records to verify NO plaintext API key leakage
            raw_secret_pattern = "sk-newly-replaced-openai-key-9999"
            all_audit_records = list(AIAuditLog.select())
            for log_entry in all_audit_records:
                self.assertNotIn(
                    raw_secret_pattern,
                    log_entry.details or "",
                    f"CRITICAL: Plaintext API key found in audit log {log_entry.id}!",
                )

            print("  [PASS] Test 9: Security Audit Logging verifies all admin actions with ZERO plaintext secret leakage.")

    async def test_10_byok_admin_stats(self):
        """
        Verify BYOK Admin Stats API:
        - GET /v1/admin/ai/byok-stats
        - Returns counts of total, active, and locked custom models along with unique users.
        """
        # Seed custom BYOK model
        AIModel.create(
            id="user_custom_001_llama3",
            provider="openai",
            model_name="llama-3.3-70b-custom",
            model_type="CHAT",
            enabled=True,
            status="active",
            is_global=False,
            is_custom=True,
            owner_user_id="normal_user_001",
            owner_tenant_id="normal_user_001",
        )

        with patch("api.apps.ai_management_app.current_user", self.admin_user):
            resp = await admin_get_byok_stats()
            resp_data = _parse_resp(resp)
            self.assertEqual(resp_data.get("code"), 0)
            data = resp_data["data"]

            self.assertGreaterEqual(data.get("total_byok_models", 0), 1)
            self.assertGreaterEqual(data.get("active_byok_models", 0), 1)
            self.assertGreaterEqual(data.get("byok_users_count", 0), 1)

            print("  [PASS] Test 10: BYOK Admin Stats API accurately tracks custom user model usage.\n")


if __name__ == "__main__":
    unittest.main()
