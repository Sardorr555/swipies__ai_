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
import os
import sys
import types
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock
from sqlalchemy.types import TypeEngine

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Stub out heavy C-extensions/optional database driver dependencies if not present on host
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

from peewee import SqliteDatabase

# Create temporary SQLite database file for tests
TEST_DB_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_atmos_temp.db"))
test_db = SqliteDatabase(TEST_DB_FILE)

from api.db.db_models import (
    DB,
    User,
    Tenant,
    UserTenant,
    Advertiser,
    AdCampaign,
    AdImpression,
    AdClick,
    AdTransaction,
    AdSettings,
    PaymentOrder,
    SubscriptionPlan,
    UserOnboarding,
)
from api.db.services.ad_engine_service import AdEngineService
from api.db.services.ad_policy_service import AdPolicyService
from api.db.services.payment_service import AtmosService, PaymentOrderService
from common.time_utils import current_timestamp


def create_test_tenant(tenant_id: str, name: str = "Test Tenant", plan_type: str = "free", plan_expiry_date = None):
    return Tenant.create(
        id=tenant_id,
        name=name,
        llm_id="",
        embd_id="",
        asr_id="",
        img2txt_id="",
        rerank_id="",
        parser_ids="",
        plan_type=plan_type,
        plan_expiry_date=plan_expiry_date,
        create_time=current_timestamp(),
    )


def create_test_user(user_id: str, nickname: str = "Test User", email: str = "user@swipies.app"):
    return User.create(
        id=user_id,
        nickname=nickname,
        email=email,
        create_time=current_timestamp(),
    )


def create_test_user_tenant(user_id: str, tenant_id: str, role: str = "owner"):
    return UserTenant.create(
        id=uuid.uuid4().hex[:32],
        user_id=user_id,
        tenant_id=tenant_id,
        role=role,
        invited_by=user_id,
        create_time=current_timestamp(),
    )


class TestAtmosPaymentSystem(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Override DB connection context with test_db
        DB.connection_context = test_db.connection_context
        DB.atomic = test_db.atomic
        DB.transaction = test_db.transaction
        DB.connect = test_db.connect
        DB.close = test_db.close
        DB.is_closed = test_db.is_closed
        DB.execute_sql = test_db.execute_sql

        models = [
            User,
            Tenant,
            UserTenant,
            Advertiser,
            AdCampaign,
            AdImpression,
            AdClick,
            AdTransaction,
            AdSettings,
            PaymentOrder,
            SubscriptionPlan,
            UserOnboarding,
        ]
        for m in models:
            m._meta.database = test_db

        test_db.connect(reuse_if_open=True)
        test_db.create_tables(models, safe=True)

        SubscriptionPlan.create(
            id="free",
            name="Free",
            daily_token_limit=50000,
            monthly_token_limit=1000000,
        )
        SubscriptionPlan.create(
            id="plus",
            name="Plus",
            daily_token_limit=200000,
            monthly_token_limit=5000000,
        )
        SubscriptionPlan.create(
            id="pro",
            name="Pro",
            daily_token_limit=1000000,
            monthly_token_limit=20000000,
        )

    @classmethod
    def tearDownClass(cls):
        models = [
            User,
            Tenant,
            UserTenant,
            Advertiser,
            AdCampaign,
            AdImpression,
            AdClick,
            AdTransaction,
            AdSettings,
            PaymentOrder,
            SubscriptionPlan,
            UserOnboarding,
        ]
        test_db.drop_tables(models, safe=True)
        test_db.close()
        if os.path.exists(TEST_DB_FILE):
            try:
                os.remove(TEST_DB_FILE)
            except Exception:
                pass

    def setUp(self):
        # Configure mock mode for testing
        os.environ["ATMOS_MOCK_MODE"] = "true"
        os.environ["USD_TO_UZS_RATE"] = "12800.0"

    def test_01_card_normalization_and_masking(self):
        """Test card masking, expiry normalization, and Atmos error parsing."""
        # 1. Masking
        self.assertEqual(AtmosService.mask_card("8600123456789012"), "8600 12** **** 9012")
        self.assertEqual(AtmosService.mask_card("9860012345678901"), "9860 01** **** 8901")

        # 2. Expiry normalization (MMYY -> YYMM)
        self.assertEqual(AtmosService.normalize_expiry("12/28"), "2812")
        self.assertEqual(AtmosService.normalize_expiry("1228"), "2812")
        self.assertEqual(AtmosService.normalize_expiry("2812"), "2812")

        # 3. Error analysis for Code 102
        err102 = AtmosService.analyze_atmos_error({"result": {"code": 102, "description": "SMS not sent"}})
        self.assertTrue(err102["is102"])
        self.assertIn("СМС", err102["message_ru"])

        err_ok = AtmosService.analyze_atmos_error({"result": {"code": "OK", "description": "Success"}})
        self.assertFalse(err_ok["is102"])

    def test_02_advertiser_balance_deposit_flow(self):
        """Test advertiser wallet deposit via Atmos card payment and OTP verification."""
        user_id = f"adv_usr_{uuid.uuid4().hex[:8]}"
        tenant_id = f"adv_ten_{uuid.uuid4().hex[:8]}"

        # Create user & advertiser
        create_test_user(user_id=user_id, nickname="Advertiser User", email="advertiser@swipies.app")
        create_test_tenant(tenant_id=tenant_id, name="Test Advertiser Co", plan_type="free")
        create_test_user_tenant(user_id=user_id, tenant_id=tenant_id)

        adv = Advertiser.create(
            id=f"adv_{uuid.uuid4().hex[:8]}",
            user_id=user_id,
            tenant_id=tenant_id,
            company_name="Innovatech LLC",
            balance=0.0,
            currency="USD",
            created_at=current_timestamp(),
        )

        # 1. Create payment order for $50.00
        success, msg, data = AtmosService.create_payment_order(
            user_id=user_id,
            tenant_id=tenant_id,
            purpose="advertiser_deposit",
            amount_usd=50.0,
            advertiser_id=adv.id,
            account_email="advertiser@swipies.app",
        )
        self.assertTrue(success, f"Failed to create order: {msg}")
        self.assertIsNotNone(data)
        order_id = data["order_id"]
        self.assertEqual(data["amount_usd"], 50.0)
        self.assertEqual(data["amount_uzs"], 640000)  # 50 * 12800

        # 2. Pre-apply card
        pre_ok, pre_msg, pre_data = AtmosService.pre_apply_card(
            order_id=order_id,
            card_number="8600 1234 5678 9012",
            expiry="12/28",
            user_id=user_id,
        )
        self.assertTrue(pre_ok, f"Pre-apply failed: {pre_msg}")
        self.assertEqual(pre_data["status"], "waiting_otp")

        # 3. Apply OTP
        apply_ok, apply_msg, apply_data = AtmosService.apply_otp(
            order_id=order_id,
            otp="123456",
            user_id=user_id,
        )
        self.assertTrue(apply_ok, f"Apply OTP failed: {apply_msg}")
        self.assertEqual(apply_data["status"], "paid")

        # 4. Verify advertiser balance in DB
        adv_refreshed = Advertiser.get_by_id(adv.id)
        self.assertEqual(adv_refreshed.balance, 50.0)

        # 5. Verify AdTransaction record
        tx = AdTransaction.get_or_none(AdTransaction.advertiser_id == adv.id)
        self.assertIsNotNone(tx)
        self.assertEqual(tx.amount, 50.0)
        self.assertEqual(tx.type, "deposit")

    def test_03_subscription_upgrade_to_plus_flow(self):
        """Test user subscribing to Plus plan via Atmos: plan update, expiry extension, and 100% ad removal."""
        user_id = f"plus_usr_{uuid.uuid4().hex[:8]}"
        tenant_id = f"plus_ten_{uuid.uuid4().hex[:8]}"

        create_test_user(user_id=user_id, nickname="Plus User", email="plus_user@swipies.app")
        tenant = create_test_tenant(tenant_id=tenant_id, name="Plus User Workspace", plan_type="free")
        create_test_user_tenant(user_id=user_id, tenant_id=tenant_id)

        # Initially, free user is NOT ad exempt
        self.assertFalse(AdPolicyService.is_ad_exempt(tenant_id, user_id))

        # 1. Create order for Plus plan
        success, msg, data = AtmosService.create_payment_order(
            user_id=user_id,
            tenant_id=tenant_id,
            purpose="subscription_upgrade",
            plan_id="plus",
            account_email="plus_user@swipies.app",
        )
        self.assertTrue(success)
        order_id = data["order_id"]
        self.assertEqual(data["plan_id"], "plus")
        self.assertEqual(data["amount_usd"], 9.99)

        # 2. Pre-apply & Apply OTP
        AtmosService.pre_apply_card(order_id, "9860 0123 4567 8901", "08/29", user_id)
        apply_ok, _, apply_data = AtmosService.apply_otp(order_id, "999888", user_id)
        self.assertTrue(apply_ok)
        self.assertEqual(apply_data["status"], "paid")

        # 3. Check Tenant in DB
        tenant_refreshed = Tenant.get_by_id(tenant_id)
        self.assertEqual(tenant_refreshed.plan_type, "plus")
        self.assertIsNotNone(tenant_refreshed.plan_expiry_date)
        if isinstance(tenant_refreshed.plan_expiry_date, str):
            exp_dt = datetime.fromisoformat(tenant_refreshed.plan_expiry_date)
        else:
            exp_dt = tenant_refreshed.plan_expiry_date
        self.assertIsNotNone(exp_dt)

        # 4. Verify user is now 100% ad exempt
        self.assertTrue(AdPolicyService.is_ad_exempt(tenant_id, user_id))

        # 5. Verify system prompt is 100% untouched (0 ad tokens)
        effective_prompt = AdPolicyService.build_effective_system_prompt(
            tenant_id=tenant_id,
            base_system_prompt="You are an AI assistant.",
            user_query="Can you recommend a project management tool?",
            user_id=user_id,
        )
        self.assertEqual(effective_prompt, "You are an AI assistant.", "Plus plan user must receive 100% clean prompt without ads")

    def test_04_subscription_upgrade_to_pro_flow(self):
        """Test user subscribing to Pro plan via Atmos with instant model unlocking and full ad exemption."""
        user_id = f"pro_usr_{uuid.uuid4().hex[:8]}"
        tenant_id = f"pro_ten_{uuid.uuid4().hex[:8]}"

        create_test_user(user_id=user_id, nickname="Pro User", email="pro_user@swipies.app")
        create_test_tenant(tenant_id=tenant_id, name="Pro Workspace", plan_type="free")
        create_test_user_tenant(user_id=user_id, tenant_id=tenant_id)

        # 1. Create order for Pro plan
        success, msg, data = AtmosService.create_payment_order(
            user_id=user_id,
            tenant_id=tenant_id,
            purpose="subscription_upgrade",
            plan_id="pro",
        )
        self.assertTrue(success)
        order_id = data["order_id"]
        self.assertEqual(data["plan_id"], "pro")
        self.assertEqual(data["amount_usd"], 29.99)

        # 2. Complete payment
        AtmosService.pre_apply_card(order_id, "8600 5555 4444 3333", "11/27", user_id)
        apply_ok, _, apply_data = AtmosService.apply_otp(order_id, "654321", user_id)
        self.assertTrue(apply_ok)

        # 3. Check Tenant status
        tenant_refreshed = Tenant.get_by_id(tenant_id)
        self.assertEqual(tenant_refreshed.plan_type, "pro")

        # 4. Verify 100% Ad exemption
        self.assertTrue(AdPolicyService.is_ad_exempt(tenant_id, user_id))
        effective_prompt = AdPolicyService.build_effective_system_prompt(
            tenant_id=tenant_id,
            base_system_prompt="You are a Pro assistant.",
            user_query="best laptops 2026",
            user_id=user_id,
        )
        self.assertEqual(effective_prompt, "You are a Pro assistant.", "Pro plan user must receive 100% clean prompt without ads")

    def test_05_idempotent_otp_apply_safety(self):
        """Test applying OTP twice to the same order is idempotent and does not double-credit."""
        user_id = f"idem_usr_{uuid.uuid4().hex[:8]}"
        tenant_id = f"idem_ten_{uuid.uuid4().hex[:8]}"

        create_test_user(user_id=user_id, nickname="Idem User", email="idem@swipies.app")
        create_test_tenant(tenant_id=tenant_id, name="Idempotent Workspace", plan_type="free")

        adv = Advertiser.create(
            id=f"adv_{uuid.uuid4().hex[:8]}",
            user_id=user_id,
            tenant_id=tenant_id,
            company_name="Safe Payments Inc",
            balance=100.0,
            currency="USD",
            created_at=current_timestamp(),
        )

        _, _, data = AtmosService.create_payment_order(
            user_id=user_id,
            tenant_id=tenant_id,
            purpose="advertiser_deposit",
            amount_usd=25.0,
            advertiser_id=adv.id,
        )
        order_id = data["order_id"]

        AtmosService.pre_apply_card(order_id, "8600 0000 1111 2222", "01/30", user_id)

        # First apply
        ok1, _, _ = AtmosService.apply_otp(order_id, "111222", user_id)
        self.assertTrue(ok1)
        self.assertEqual(Advertiser.get_by_id(adv.id).balance, 125.0)

        # Second apply (replay attempt)
        ok2, _, _ = AtmosService.apply_otp(order_id, "111222", user_id)
        self.assertTrue(ok2)
        # Balance must REMAIN 125.0, NOT 150.0
        self.assertEqual(Advertiser.get_by_id(adv.id).balance, 125.0)

    def test_06_validation_failure_handling(self):
        """Test validation error cases on invalid cards, invalid expiries, and mismatched users."""
        user_id = f"val_usr_{uuid.uuid4().hex[:8]}"
        tenant_id = f"val_ten_{uuid.uuid4().hex[:8]}"
        create_test_user(user_id=user_id, nickname="Val User", email="val@swipies.app")
        create_test_tenant(tenant_id=tenant_id, name="Val Workspace", plan_type="free")

        # Create valid order
        _, _, data = AtmosService.create_payment_order(
            user_id=user_id,
            tenant_id=tenant_id,
            purpose="advertiser_deposit",
            amount_usd=10.0,
        )
        self.assertIsNotNone(data)
        order_id = data["order_id"]

        # Invalid card length
        pre_bad_card, msg_bad_card, _ = AtmosService.pre_apply_card(order_id, "1234", "12/28", user_id=user_id)
        self.assertFalse(pre_bad_card)
        self.assertIn("16 цифр", msg_bad_card)

        # Invalid expiry
        pre_bad_exp, msg_bad_exp, _ = AtmosService.pre_apply_card(order_id, "8600123456789012", "999", user_id=user_id)
        self.assertFalse(pre_bad_exp)
        self.assertIn("срок действия", msg_bad_exp)

        # User mismatch security check
        pre_mismatch, msg_mismatch, _ = AtmosService.pre_apply_card(
            order_id, "8600123456789012", "12/28", user_id="intruder_user"
        )
        self.assertFalse(pre_mismatch)
        self.assertIn("Доступ запрещен", msg_mismatch)

    def test_07_payment_order_history(self):
        """Test querying user payment orders."""
        user_id = f"hist_usr_{uuid.uuid4().hex[:8]}"
        tenant_id = f"hist_ten_{uuid.uuid4().hex[:8]}"

        create_test_user(user_id=user_id, nickname="History User", email="history@swipies.app")
        create_test_tenant(tenant_id=tenant_id, name="History Workspace", plan_type="free")

        # Create 2 orders
        AtmosService.create_payment_order(user_id, tenant_id, "subscription_upgrade", plan_id="plus")
        AtmosService.create_payment_order(user_id, tenant_id, "subscription_upgrade", plan_id="pro")

        orders = AtmosService.get_user_orders(user_id, tenant_id)
        self.assertEqual(len(orders), 2)
        plans = [o["plan_id"] for o in orders]
        self.assertIn("plus", plans)
        self.assertIn("pro", plans)


if __name__ == "__main__":
    unittest.main()
