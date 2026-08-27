#
#  Copyright 2026 The InfiniFlow Authors. All Rights Reserved.
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
import time
import types
import unittest
import uuid
from datetime import datetime, timezone
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

from peewee import SqliteDatabase

# Create temporary SQLite database file for enforcement tests
TEST_ENFORCE_DB_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_enforce_temp.db"))
test_db = SqliteDatabase(TEST_ENFORCE_DB_FILE)

from api.db.db_models import (
    DB,
    User,
    Tenant,
    SubscriptionPlan,
    AIProvider,
    AIModel,
    SubscriptionAIPolicy,
    UserTokenLimit,
    TokenUsageLog,
    GlobalRagflowInstance,
    TenantLLM,
)
from api.db.services.ai_policy_service import (
    AIPolicyManager,
    SubscriptionPlanService,
    SubscriptionAIPolicyService,
    UserTokenLimitService,
)
from common.ai_gateway.gateway import ai_gateway
from common.ai_gateway.types import (
    ProviderType,
    GatewayChatRequest,
    GatewayChatResponse,
    GatewayStreamChunk,
    GatewayMessage,
    TokenUsage,
)
from common.ai_gateway.errors import (
    AIGatewayPolicyError,
    ModelExcludedFromProviderError,
    ModelGloballyDisabledError,
    UserModelForbiddenError,
    SubscriptionModelNotAllowedError,
    SubscriptionTokenLimitReachedError,
)
from rag.llm.chat_model import Base


class TestSubscriptionEnforcement(unittest.IsolatedAsyncioTestCase):
    """
    Comprehensive Automated Test Suite for 5-Tier AI Gateway Policy Enforcement (TDD Gate).
    Validates:
    - 5 Strict Evaluation Tiers & Correct Priority Hierarchy
    - Safe Fallback Bypass Immunity (Zero fallback to legacy client on policy rejections)
    - BYOK Plan Gating & Quota Exemptions
    - Individual Admin User Token Limit Overrides Priority over Tenant Plans
    - Streaming Pre-Flight Failure Handshake
    - Superuser & System Bypass
    """

    @classmethod
    def setUpClass(cls):
        # Bind models to test SQLite DB
        DB.connection_context = test_db.connection_context
        DB.atomic = test_db.atomic
        DB.transaction = test_db.transaction
        DB.connect = test_db.connect
        DB.close = test_db.close
        DB.is_closed = test_db.is_closed
        DB.execute_sql = test_db.execute_sql

        cls.models = [
            User,
            Tenant,
            SubscriptionPlan,
            AIProvider,
            AIModel,
            SubscriptionAIPolicy,
            UserTokenLimit,
            TokenUsageLog,
            GlobalRagflowInstance,
            TenantLLM,
        ]

        test_db.bind(cls.models, bind_refs=False, bind_backrefs=False)
        test_db.connect(reuse_if_open=True)
        test_db.drop_tables(cls.models, safe=True)
        test_db.create_tables(cls.models)

        # 1. Seed Subscription Plans
        SubscriptionPlan.create(
            id="free",
            name="FREE",
            monthly_token_limit=1000000,
            daily_token_limit=50000,
            daily_request_limit=500,
            monthly_request_limit=10000,
            allow_byok=False,
            max_byok_models=0,
            status="1",
        )
        SubscriptionPlan.create(
            id="plus",
            name="PLUS",
            monthly_token_limit=10000000,
            daily_token_limit=500000,
            daily_request_limit=5000,
            monthly_request_limit=100000,
            allow_byok=False,
            max_byok_models=0,
            status="1",
        )
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

        # 2. Seed Providers
        AIProvider.create(
            id="openai",
            provider_name="openai",
            display_name="OpenAI",
            api_key="sk-test-openai-key-12345",
            status="verified",
            is_active=True,
            extra={"excluded_models": []},
        )
        AIProvider.create(
            id="anthropic",
            provider_name="anthropic",
            display_name="Anthropic",
            api_key="sk-test-anthropic-key-12345",
            status="verified",
            is_active=True,
            extra={"excluded_models": ["claude-3-5-haiku-20241022"]},
        )
        AIProvider.create(
            id="unconfigured_prov",
            provider_name="unconfigured_prov",
            display_name="Unconfigured Provider",
            api_key="",
            status="unconfigured",
            is_active=False,
            extra={},
        )

        # 3. Seed AI Models
        AIModel.create(
            id="openai/gpt-4o-mini",
            provider="openai",
            model_name="gpt-4o-mini",
            model_type="CHAT",
            enabled=True,
            status="active",
            is_custom=False,
            extra={"allowed_plans": ["free", "plus", "pro"]},
        )
        AIModel.create(
            id="openai/gpt-4o",
            provider="openai",
            model_name="gpt-4o",
            model_type="CHAT",
            enabled=True,
            status="active",
            is_custom=False,
            extra={"allowed_plans": ["plus", "pro"]},
        )
        AIModel.create(
            id="openai/disabled-model",
            provider="openai",
            model_name="disabled-model",
            model_type="CHAT",
            enabled=False,
            status="disabled",
            is_custom=False,
            extra={"allowed_plans": ["free", "plus", "pro"]},
        )
        AIModel.create(
            id="anthropic/claude-3-5-haiku-20241022",
            provider="anthropic",
            model_name="claude-3-5-haiku-20241022",
            model_type="CHAT",
            enabled=True,
            status="active",
            is_custom=False,
            extra={"allowed_plans": ["free", "plus", "pro"]},
        )
        AIModel.create(
            id="unconfigured_prov/orphan-model",
            provider="unconfigured_prov",
            model_name="orphan-model",
            model_type="CHAT",
            enabled=False,
            status="unconfigured_provider",
            is_custom=False,
            extra={"allowed_plans": ["free", "plus", "pro"]},
        )
        AIModel.create(
            id="custom/my-byok-llama",
            provider="custom",
            model_name="my-byok-llama",
            model_type="CHAT",
            enabled=True,
            status="active",
            is_custom=True,
            owner_user_id="user_pro_01",
            owner_tenant_id="tenant_pro_01",
            extra={"allowed_plans": ["pro"]},
        )

        # Seed SubscriptionAIPolicy
        SubscriptionAIPolicy.create(
            id="pol_free_gpt4o_mini",
            plan_id="free",
            model_id="openai/gpt-4o-mini",
            enabled=True,
        )
        SubscriptionAIPolicy.create(
            id="pol_free_haiku",
            plan_id="free",
            model_id="anthropic/claude-3-5-haiku-20241022",
            enabled=True,
        )
        SubscriptionAIPolicy.create(
            id="pol_plus_gpt4o",
            plan_id="plus",
            model_id="openai/gpt-4o",
            enabled=True,
        )
        SubscriptionAIPolicy.create(
            id="pol_pro_gpt4o",
            plan_id="pro",
            model_id="openai/gpt-4o",
            enabled=True,
        )

        # 4. Seed Users and Tenants
        def _create_tenant(tid, name, plan):
            return Tenant.create(
                id=tid,
                name=name,
                plan_type=plan,
                llm_id="openai/gpt-4o-mini",
                embd_id="openai/text-embedding-3-small",
                asr_id="",
                img2txt_id="",
                rerank_id="",
                parser_ids="naive",
            )

        def _create_user(uid, email, is_superuser=False):
            return User.create(
                id=uid,
                nickname=uid,
                email=email,
                is_superuser=is_superuser,
            )

        _create_tenant("tenant_free_01", "Free Tenant", "free")
        _create_user("user_free_01", "free_user@example.com")

        _create_tenant("tenant_plus_01", "Plus Tenant", "plus")
        _create_user("user_plus_01", "plus_user@example.com")

        _create_tenant("tenant_pro_01", "Pro Tenant", "pro")
        _create_user("user_pro_01", "pro_user@example.com")

        _create_tenant("tenant_admin_01", "Admin Tenant", "free")
        _create_user("user_admin_01", "admin_user@example.com", is_superuser=True)

        # User with explicit DENY
        _create_tenant("tenant_deny_01", "Deny Tenant", "pro")
        _create_user("user_deny_01", "deny_user@example.com")
        UserTokenLimit.create(
            user_id="user_deny_01",
            monthly_token_limit=0,
            enabled=True,
            extra={"model_overrides": {"gpt-4o": {"access_type": "DENY", "enabled": True}}},
        )

        # User with explicit ALLOW (on Free plan)
        _create_tenant("tenant_allow_01", "Allow Tenant", "free")
        _create_user("user_allow_01", "allow_user@example.com")
        UserTokenLimit.create(
            user_id="user_allow_01",
            monthly_token_limit=0,
            enabled=True,
            extra={"model_overrides": {"gpt-4o": {"access_type": "ALLOW", "enabled": True}}},
        )

    @classmethod
    def tearDownClass(cls):
        test_db.close()
        if os.path.exists(TEST_ENFORCE_DB_FILE):
            try:
                os.remove(TEST_ENFORCE_DB_FILE)
            except Exception:
                pass

    def setUp(self):
        from common.ai_gateway.providers.openai_provider import OpenAIProvider
        from common.ai_gateway.providers.anthropic_provider import AnthropicProvider
        from common.ai_gateway.types import TokenUsage

        fake_resp = GatewayChatResponse(
            id="chatcmpl-enforce-001",
            model="gpt-4o",
            provider=ProviderType.OPENAI,
            content="Hello from AI Gateway Verified Test!",
            role="assistant",
            usage=TokenUsage(prompt_tokens=10, completion_tokens=15, total_tokens=25),
            finish_reason="stop",
            created_at=int(time.time()),
        )

        self._openai_chat_patch = patch.object(OpenAIProvider, "chat_complete", AsyncMock(return_value=fake_resp))
        self._openai_chat_patch.start()

        self._anthropic_chat_patch = patch.object(AnthropicProvider, "chat_complete", AsyncMock(return_value=fake_resp))
        self._anthropic_chat_patch.start()

        async def _fake_stream_gen(self_p, req):
            yield GatewayStreamChunk(id="c1", delta="Chunk 1", finish_reason=None)
            yield GatewayStreamChunk(id="c2", delta=" Chunk 2", finish_reason="stop")

        self._openai_stream_patch = patch.object(OpenAIProvider, "chat_stream", _fake_stream_gen)
        self._openai_stream_patch.start()

        self._anthropic_stream_patch = patch.object(AnthropicProvider, "chat_stream", _fake_stream_gen)
        self._anthropic_stream_patch.start()

    def tearDown(self):
        patch.stopall()

    # -------------------------------------------------------------------------
    # Scenario 1: Level 1 Provider Exclusion blocks request & takes highest priority
    # -------------------------------------------------------------------------
    async def test_01_level1_provider_exclusion_blocks_request_and_takes_priority(self):
        """
        Scenario 1: Model is in AIProvider.extra['excluded_models'].
        Even if user has Level 3 explicit ALLOW and PRO plan, Level 1 exclusion MUST block request first!
        Expected: ModelExcludedFromProviderError (403, PROVIDER_EXCLUDED).
        """
        # User has PRO plan and explicit ALLOW, but model is excluded from Anthropic provider
        req = GatewayChatRequest(
            messages=[GatewayMessage(role="user", content="Hi")],
            model="claude-3-5-haiku-20241022",
            tenant_id="tenant_pro_01",
            user_id="user_pro_01",
        )

        with self.assertRaises(ModelExcludedFromProviderError) as ctx:
            await ai_gateway.chat(req)

        self.assertEqual(ctx.exception.status_code, 403)
        self.assertEqual(ctx.exception.error_code, "PROVIDER_EXCLUDED")
        self.assertIn("excluded from provider", str(ctx.exception).lower())
        print("  [PASS] Scenario 1: Level 1 Provider Exclusion blocks request with ModelExcludedFromProviderError (403/PROVIDER_EXCLUDED)")

    # -------------------------------------------------------------------------
    # Scenario 2: Level 2 Global Kill-Switch blocks request
    # -------------------------------------------------------------------------
    async def test_02_level2_global_kill_switch_blocks_request(self):
        """
        Scenario 2: Model has AIModel.enabled = False (globally disabled by admin).
        Expected: ModelGloballyDisabledError (403, GLOBALLY_DISABLED).
        """
        req = GatewayChatRequest(
            messages=[GatewayMessage(role="user", content="Hi")],
            model="disabled-model",
            tenant_id="tenant_pro_01",
            user_id="user_pro_01",
        )

        with self.assertRaises(ModelGloballyDisabledError) as ctx:
            await ai_gateway.chat(req)

        self.assertEqual(ctx.exception.status_code, 403)
        self.assertEqual(ctx.exception.error_code, "GLOBALLY_DISABLED")
        self.assertIn("disabled globally", str(ctx.exception).lower())
        print("  [PASS] Scenario 2: Level 2 Global Kill-Switch blocks request with ModelGloballyDisabledError (403/GLOBALLY_DISABLED)")

    # -------------------------------------------------------------------------
    # Scenario 3: Level 2 Unconfigured Provider Cascade blocks request
    # -------------------------------------------------------------------------
    async def test_03_level2_unconfigured_provider_cascade_blocks_request(self):
        """
        Scenario 3: Model belongs to an unconfigured provider (wiped API key / status='unconfigured_provider').
        Expected: ModelGloballyDisabledError (403, GLOBALLY_DISABLED) with 'no configured API key' message.
        """
        req = GatewayChatRequest(
            messages=[GatewayMessage(role="user", content="Hi")],
            model="orphan-model",
            tenant_id="tenant_pro_01",
            user_id="user_pro_01",
        )

        with self.assertRaises(ModelGloballyDisabledError) as ctx:
            await ai_gateway.chat(req)

        self.assertEqual(ctx.exception.status_code, 403)
        self.assertEqual(ctx.exception.error_code, "GLOBALLY_DISABLED")
        self.assertIn("no configured api key", str(ctx.exception).lower())
        print("  [PASS] Scenario 3: Level 2 Unconfigured Provider Cascade blocks request with ModelGloballyDisabledError (403/GLOBALLY_DISABLED)")

    # -------------------------------------------------------------------------
    # Scenario 4: Level 3 Per-User Explicit DENY blocks request
    # -------------------------------------------------------------------------
    async def test_04_level3_per_user_explicit_deny_blocks_request(self):
        """
        Scenario 4: User account has explicit DENY override for 'gpt-4o' despite being on PRO plan.
        Expected: UserModelForbiddenError (403, USER_RESTRICTED).
        """
        req = GatewayChatRequest(
            messages=[GatewayMessage(role="user", content="Hi")],
            model="gpt-4o",
            tenant_id="tenant_deny_01",
            user_id="user_deny_01",
        )

        with self.assertRaises(UserModelForbiddenError) as ctx:
            await ai_gateway.chat(req)

        self.assertEqual(ctx.exception.status_code, 403)
        self.assertEqual(ctx.exception.error_code, "USER_RESTRICTED")
        self.assertIn("explicitly restricted for your user account", str(ctx.exception).lower())
        print("  [PASS] Scenario 4: Level 3 Per-User Explicit DENY blocks request with UserModelForbiddenError (403/USER_RESTRICTED)")

    # -------------------------------------------------------------------------
    # Scenario 5: Level 3 Per-User Explicit ALLOW bypasses Plan Tier (Level 4)
    # -------------------------------------------------------------------------
    async def test_05_level3_per_user_explicit_allow_bypasses_plan_tier(self):
        """
        Scenario 5: User is on FREE plan (which normally forbids 'gpt-4o'), but has explicit ALLOW override.
        Expected: Request is permitted (HTTP 200 OK), successfully bypassing Level 4 plan restriction.
        """
        req = GatewayChatRequest(
            messages=[GatewayMessage(role="user", content="Hello")],
            model="gpt-4o",
            tenant_id="tenant_allow_01",
            user_id="user_allow_01",
        )

        resp = await ai_gateway.chat(req)
        self.assertIsNotNone(resp)
        self.assertEqual(resp.content, "Hello from AI Gateway Verified Test!")
        print("  [PASS] Scenario 5: Level 3 Per-User Explicit ALLOW successfully bypasses Level 4 plan restriction (200 OK)")

    # -------------------------------------------------------------------------
    # Scenario 6: Level 3 Per-User Explicit ALLOW CANNOT bypass Level 1 or Level 2
    # -------------------------------------------------------------------------
    async def test_06_level3_per_user_allow_cannot_bypass_level1_or_2(self):
        """
        Scenario 6: User has explicit ALLOW for 'disabled-model', but the model is globally disabled (Level 2).
        Expected: Rejection at Level 2 with ModelGloballyDisabledError. Explicit user ALLOW cannot bypass Level 1/2.
        """
        # Add override for disabled-model to user_allow_01
        utl = UserTokenLimit.get_or_none(UserTokenLimit.user_id == "user_allow_01")
        extra = dict(utl.extra or {}) if utl else {}
        extra.setdefault("model_overrides", {})["disabled-model"] = {"access_type": "ALLOW", "enabled": True}
        if utl:
            UserTokenLimit.update(extra=extra).where(UserTokenLimit.user_id == "user_allow_01").execute()
        else:
            UserTokenLimit.create(user_id="user_allow_01", monthly_token_limit=0, enabled=True, extra=extra)

        req = GatewayChatRequest(
            messages=[GatewayMessage(role="user", content="Hello")],
            model="disabled-model",
            tenant_id="tenant_allow_01",
            user_id="user_allow_01",
        )

        with self.assertRaises(ModelGloballyDisabledError) as ctx:
            await ai_gateway.chat(req)

        self.assertEqual(ctx.exception.status_code, 403)
        self.assertEqual(ctx.exception.error_code, "GLOBALLY_DISABLED")
        print("  [PASS] Scenario 6: Level 3 Per-User ALLOW strictly cannot bypass Level 1/2 admin disablement (403/GLOBALLY_DISABLED)")

    # -------------------------------------------------------------------------
    # Scenario 7: Level 4 Subscription Plan Tier Gating blocks restricted model
    # -------------------------------------------------------------------------
    async def test_07_level4_free_plan_restricted_model_blocks_request(self):
        """
        Scenario 7: Free plan user requests 'gpt-4o' (configured for 'plus', 'pro' plans only).
        Expected: SubscriptionModelNotAllowedError (403, PLAN_RESTRICTED).
        """
        req = GatewayChatRequest(
            messages=[GatewayMessage(role="user", content="Hello")],
            model="gpt-4o",
            tenant_id="tenant_free_01",
            user_id="user_free_01",
        )

        with self.assertRaises(SubscriptionModelNotAllowedError) as ctx:
            await ai_gateway.chat(req)

        self.assertEqual(ctx.exception.status_code, 403)
        self.assertEqual(ctx.exception.error_code, "PLAN_RESTRICTED")
        self.assertIn("not included in your free subscription plan", str(ctx.exception).lower())
        print("  [PASS] Scenario 7: Level 4 Free Plan Restricted Model blocks request with SubscriptionModelNotAllowedError (403/PLAN_RESTRICTED)")

    # -------------------------------------------------------------------------
    # Scenario 8: Level 5 Token Quota Exhaustion blocks request with 429
    # -------------------------------------------------------------------------
    async def test_08_level5_token_quota_exhaustion_blocks_request(self):
        """
        Scenario 8: Free plan user requests allowed model 'gpt-4o-mini', but monthly token limit (1,000,000) is exhausted.
        Expected: SubscriptionTokenLimitReachedError (429, QUOTA_EXCEEDED).
        """
        # Seed usage exceeding 1,000,000 limit
        current_period = AIPolicyManager.get_current_period()
        current_date = AIPolicyManager.get_current_date_str()
        TokenUsageLog.create(
            id="log_test_08_quota",
            tenant_id="tenant_free_01",
            user_id="user_free_01",
            model_id="openai/gpt-4o-mini",
            model_type="CHAT",
            input_tokens=500000,
            output_tokens=600000,
            total_tokens=1100000,
            billing_period=current_period,
            date_str=current_date,
            status="SUCCESS",
        )

        req = GatewayChatRequest(
            messages=[GatewayMessage(role="user", content="Hello")],
            model="gpt-4o-mini",
            tenant_id="tenant_free_01",
            user_id="user_free_01",
        )

        with self.assertRaises(SubscriptionTokenLimitReachedError) as ctx:
            await ai_gateway.chat(req)

        self.assertEqual(ctx.exception.status_code, 429)
        self.assertEqual(ctx.exception.error_code, "QUOTA_EXCEEDED")
        self.assertIn("monthly ai token limit reached", str(ctx.exception).lower())
        print("  [PASS] Scenario 8: Level 5 Token Quota Exhaustion blocks request with SubscriptionTokenLimitReachedError (429/QUOTA_EXCEEDED)")

    # -------------------------------------------------------------------------
    # Scenario 9: Streaming Request blocked before SSE Handshake / Chunks
    # -------------------------------------------------------------------------
    async def test_09_streaming_request_blocked_before_sse_handshake(self):
        """
        Scenario 9: stream_chat() must perform pre-flight policy evaluation BEFORE opening stream or yielding chunks.
        Expected: Fails fast with SubscriptionModelNotAllowedError upon generator entry.
        """
        req = GatewayChatRequest(
            messages=[GatewayMessage(role="user", content="Stream me")],
            model="gpt-4o",
            tenant_id="tenant_free_01",
            user_id="user_free_01",
        )

        stream = ai_gateway.stream_chat(req)
        chunks = []
        with self.assertRaises(SubscriptionModelNotAllowedError):
            async for chunk in stream:
                chunks.append(chunk)

        self.assertEqual(len(chunks), 0)
        print("  [PASS] Scenario 9: Streaming Request blocked before SSE handshake with zero chunks yielded (403/PLAN_RESTRICTED)")

    # -------------------------------------------------------------------------
    # Scenario 10: Safe Fallback Immunity strictly prevents legacy client fallback
    # -------------------------------------------------------------------------
    async def test_10_safe_fallback_immunity_does_not_call_legacy_client(self):
        """
        Scenario 10: In chat_model.py, Base.async_chat and async_chat_streamly must re-raise AIGatewayPolicyError
        without falling back to self.async_client.chat.completions.create.
        Explicit verification: Legacy client mock MUST NOT be called (assert_not_called()).
        """
        base_chat = Base("test-key-mock", "gpt-4o", "https://api.openai.com/v1")
        base_chat.tenant_id = "tenant_free_01"
        base_chat.user_id = "user_free_01"

        # Mock legacy client
        mock_legacy_create = AsyncMock()
        base_chat.async_client = MagicMock()
        base_chat.async_client.chat = MagicMock()
        base_chat.async_client.chat.completions = MagicMock()
        base_chat.async_client.chat.completions.create = mock_legacy_create

        # 1. Non-streaming call
        with self.assertRaises(SubscriptionModelNotAllowedError):
            await base_chat.async_chat("System", [{"role": "user", "content": "Hello"}])

        # CRITICAL ASSERTION: Legacy client was NOT called
        mock_legacy_create.assert_not_called()

        # 2. Streaming call
        mock_legacy_create.reset_mock()
        with self.assertRaises(SubscriptionModelNotAllowedError):
            async for _ in base_chat.async_chat_streamly("System", [{"role": "user", "content": "Hello"}], {}):
                pass

        # CRITICAL ASSERTION: Legacy client was NOT called during streaming either
        mock_legacy_create.assert_not_called()
        print("  [PASS] Scenario 10: Safe Fallback Immunity verified: Legacy client was NOT called (mock_legacy_create.assert_not_called() PASS)")

    # -------------------------------------------------------------------------
    # Scenario 11: Superuser and System Tenant Full Bypass
    # -------------------------------------------------------------------------
    async def test_11_superuser_and_system_bypass(self):
        """
        Scenario 11: Superuser (is_superuser=True) and system internal requests (tenant_id='system')
        must bypass all plan tier restrictions, quotas, and user overrides.
        Expected: HTTP 200 OK.
        """
        # 1. Superuser requesting restricted model
        req_admin = GatewayChatRequest(
            messages=[GatewayMessage(role="user", content="Admin prompt")],
            model="gpt-4o",
            tenant_id="tenant_admin_01",
            user_id="user_admin_01",
        )
        resp_admin = await ai_gateway.chat(req_admin)
        self.assertIsNotNone(resp_admin)
        self.assertEqual(resp_admin.content, "Hello from AI Gateway Verified Test!")

        # 2. System internal call (tenant_id='system')
        req_sys = GatewayChatRequest(
            messages=[GatewayMessage(role="user", content="System RAG indexing")],
            model="gpt-4o",
            tenant_id="system",
            user_id=None,
        )
        resp_sys = await ai_gateway.chat(req_sys)
        self.assertIsNotNone(resp_sys)
        self.assertEqual(resp_sys.content, "Hello from AI Gateway Verified Test!")
        print("  [PASS] Scenario 11: Superuser & System Tenant successfully bypass all policy restrictions (200 OK)")

    # -------------------------------------------------------------------------
    # Scenario 12: BYOK Model Plan Gating & Token Quota Exemption
    # -------------------------------------------------------------------------
    async def test_12_byok_model_quota_exemption_and_plan_check(self):
        """
        Scenario 12: Custom BYOK Model rules:
        - FREE user requesting BYOK model -> BLOCKED (403, PLAN_RESTRICTED: 'BYOK_NOT_AVAILABLE').
        - PRO user requesting BYOK model -> ALLOWED (200 OK) even if tenant has exhausted token quota (exempt from Level 5).
        """
        # 1. FREE user calling BYOK model
        allowed, msg, status, code = AIPolicyManager.check_model_access_extended(
            tenant_id="tenant_free_01",
            model_name="my-byok-llama",
            model_type="CHAT",
            user_id="user_free_01",
        )
        self.assertFalse(allowed)
        self.assertEqual(status, 403)
        self.assertEqual(code, "PLAN_RESTRICTED")
        self.assertIn("connect your own ai is available only with the pro subscription", msg.lower())

        # 2. PRO user calling BYOK model (exhaust PRO tenant tokens to test quota exemption)
        current_period = AIPolicyManager.get_current_period()
        current_date = AIPolicyManager.get_current_date_str()
        TokenUsageLog.create(
            id="log_test_12_byok_quota",
            tenant_id="tenant_pro_01",
            user_id="user_pro_01",
            model_id="custom/my-byok-llama",
            model_type="CHAT",
            input_tokens=30000000,
            output_tokens=30000000,
            total_tokens=60000000,  # Exceeds PRO 50M limit
            billing_period=current_period,
            date_str=current_date,
            status="SUCCESS",
        )

        allowed_pro, msg_pro, status_pro, code_pro = AIPolicyManager.check_model_access_extended(
            tenant_id="tenant_pro_01",
            model_name="my-byok-llama",
            model_type="CHAT",
            user_id="user_pro_01",
        )
        self.assertTrue(allowed_pro)
        self.assertEqual(status_pro, 200)
        self.assertEqual(code_pro, "OK")
        print("  [PASS] Scenario 12: BYOK Model requires PRO plan (403 for Free) & is strictly exempt from Token Quotas for PRO (200 OK)")

    # -------------------------------------------------------------------------
    # Scenario 13: Individual Admin Override (user_id) takes precedence over Tenant Plan
    # -------------------------------------------------------------------------
    async def test_13_user_override_limit_takes_precedence_over_tenant_limit(self):
        """
        Scenario 13: Individual Admin Limit Override (user_id) priority:
        - Plus Tenant has 10,000,000 token limit (tenant usage is only 100,000 tokens).
        - Admin set UserTokenLimit for user_plus_01 with monthly_token_limit = 50,000 tokens.
        - User has used 60,000 tokens.
        Expected: Request is BLOCKED with 429 QUOTA_EXCEEDED because individual user limit is enforced.
        """
        # Create or update UserTokenLimit override for user_plus_01
        UserTokenLimit.delete().where(UserTokenLimit.user_id == "user_plus_01").execute()
        UserTokenLimit.create(
            user_id="user_plus_01",
            monthly_token_limit=50000,
            enabled=True,
            extra={},
        )

        # Seed 60,000 tokens used by tenant_plus_01 (under tenant 10M limit, but over user 50k limit)
        current_period = AIPolicyManager.get_current_period()
        current_date = AIPolicyManager.get_current_date_str()
        TokenUsageLog.create(
            id="log_test_13_user_override",
            tenant_id="tenant_plus_01",
            user_id="user_plus_01",
            model_id="openai/gpt-4o-mini",
            model_type="CHAT",
            input_tokens=30000,
            output_tokens=30000,
            total_tokens=60000,
            billing_period=current_period,
            date_str=current_date,
            status="SUCCESS",
        )

        req = GatewayChatRequest(
            messages=[GatewayMessage(role="user", content="Hello")],
            model="gpt-4o-mini",
            tenant_id="tenant_plus_01",
            user_id="user_plus_01",
        )

        with self.assertRaises(SubscriptionTokenLimitReachedError) as ctx:
            await ai_gateway.chat(req)

        self.assertEqual(ctx.exception.status_code, 429)
        self.assertEqual(ctx.exception.error_code, "QUOTA_EXCEEDED")
        self.assertIn("monthly ai token limit reached", str(ctx.exception).lower())
        print("  [PASS] Scenario 13: Individual Admin User Token Limit (50,000) correctly took precedence over Tenant Plan limit (10,000,000) -> 429 QUOTA_EXCEEDED")


if __name__ == "__main__":
    unittest.main()
