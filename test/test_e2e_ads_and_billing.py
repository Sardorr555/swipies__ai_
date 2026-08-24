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
from datetime import datetime, timezone
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

# Create temporary SQLite database file for E2E tests
E2E_DB_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_e2e_temp.db"))
test_db = SqliteDatabase(E2E_DB_FILE)

from api.db.db_models import (
    DB,
    User,
    Tenant,
    UserTenant,
    Advertiser,
    AdvertiserTeamMember,
    AdvertiserNotificationSettings,
    AdvertiserNotification,
    AdAudienceSegment,
    AdAudienceMember,
    AdCampaign,
    AdVariant,
    AdImpression,
    AdClick,
    AdConversion,
    AdTransaction,
    AdSettings,
    AdAttributionVisit,
    AdPublisher,
    AdPlacement,
    AdPublisherPayout,
    PaymentOrder,
    PromoCode,
    PromoCodeUsage,
    SubscriptionPlan,
    UserOnboarding,
    SavedPaymentMethod,
    UserSubscription,
)
from api.db.services.ad_engine_service import (
    AdEngineService,
    AdvertiserService,
    AdCampaignService,
    AdVariantService,
    AdSettingsService,
    AttributionService,
    ConversionTrackingService,
)
from api.db.services.recurring_subscription_service import (
    RecurringSubscriptionService,
    SavedPaymentMethodService,
)
from api.db.services.ad_policy_service import AdPolicyService
from api.db.services.payment_service import AtmosService, PaymentOrderService
from common.time_utils import current_timestamp


def create_tenant(tenant_id: str, name: str = "Test Org", plan_type: str = "free"):
    return Tenant.create(
        id=tenant_id,
        name=name,
        llm_id="",
        embd_id="",
        asr_id="",
        img2txt_id="",
        rerank_id="",
        parser_ids="",
        credit=0,
        plan_type=plan_type,
        create_time=current_timestamp(),
    )


def create_user(user_id: str, nickname: str = "John Doe", email: str = "user@swipies.app", is_superuser: bool = False):
    return User.create(
        id=user_id,
        nickname=nickname,
        email=email,
        password="hashed_secret_password",
        is_superuser=is_superuser,
        status="1",
        create_time=current_timestamp(),
        update_time=current_timestamp(),
    )


def create_user_tenant(user_id: str, tenant_id: str, role: str = "owner"):
    return UserTenant.create(
        id=f"ut_{user_id}_{tenant_id}"[:32],
        user_id=user_id,
        tenant_id=tenant_id,
        role=role,
        invited_by=user_id,
        create_time=current_timestamp(),
    )


class TestE2EAdsAndMonetization(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
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
            AdvertiserTeamMember,
            AdvertiserNotificationSettings,
            AdvertiserNotification,
            AdAudienceSegment,
            AdAudienceMember,
            AdCampaign,
            AdVariant,
            AdImpression,
            AdClick,
            AdConversion,
            AdTransaction,
            AdSettings,
            AdAttributionVisit,
            AdPublisher,
            AdPlacement,
            AdPublisherPayout,
            PaymentOrder,
            PromoCode,
            PromoCodeUsage,
            SubscriptionPlan,
            UserOnboarding,
            SavedPaymentMethod,
            UserSubscription,
        ]
        for m in models:
            m._meta.database = test_db

        test_db.connect(reuse_if_open=True)
        test_db.create_tables(models, safe=True)

        SubscriptionPlan.create(id="free", name="Free", daily_token_limit=50000, monthly_token_limit=1000000)
        SubscriptionPlan.create(id="plus", name="Plus", daily_token_limit=200000, monthly_token_limit=5000000)
        SubscriptionPlan.create(id="pro", name="Pro", daily_token_limit=1000000, monthly_token_limit=20000000)

    @classmethod
    def tearDownClass(cls):
        models = [
            User,
            Tenant,
            UserTenant,
            Advertiser,
            AdvertiserTeamMember,
            AdvertiserNotificationSettings,
            AdvertiserNotification,
            AdAudienceSegment,
            AdAudienceMember,
            AdCampaign,
            AdVariant,
            AdImpression,
            AdClick,
            AdConversion,
            AdTransaction,
            AdSettings,
            AdAttributionVisit,
            AdPublisher,
            AdPlacement,
            AdPublisherPayout,
            PaymentOrder,
            PromoCode,
            PromoCodeUsage,
            SubscriptionPlan,
            UserOnboarding,
            SavedPaymentMethod,
            UserSubscription,
        ]
        test_db.drop_tables(models, safe=True)
        test_db.close()
        if os.path.exists(E2E_DB_FILE):
            try:
                os.remove(E2E_DB_FILE)
            except Exception:
                pass

    def setUp(self):
        os.environ["ATMOS_MOCK_MODE"] = "true"
        os.environ["USD_TO_UZS_RATE"] = "12800.0"

    def test_complete_end_to_end_monetization_lifecycle(self):
        """
        Complete E2E Lifecycle:
        1. Advertiser registers and creates a CRM campaign.
        2. Admin moderates and approves the campaign.
        3. Advertiser tops up balance with $100.00 via Atmos gateway.
        4. Free user queries AI for CRM -> prompt receives matched campaign & Swipies watermark.
        5. User clicks redirect link -> click tracked, CPC debited from advertiser balance.
        6. Free user upgrades to Pro via Atmos -> completes SMS OTP -> instant upgrade.
        7. Now Pro user queries AI for CRM -> prompt is 100% clean (0 ad tokens, zero branding).
        """
        # --- STEP 1: Advertiser Registration & Campaign Creation ---
        adv_user_id = f"adv_u_{uuid.uuid4().hex[:6]}"
        adv_tenant_id = f"adv_t_{uuid.uuid4().hex[:6]}"
        create_user(user_id=adv_user_id, nickname="SaaS Advertiser", email="sales@cloudcrm.io")
        create_tenant(tenant_id=adv_tenant_id, name="CloudCRM Corp", plan_type="free")
        create_user_tenant(user_id=adv_user_id, tenant_id=adv_tenant_id)

        adv = AdvertiserService.get_or_create_for_user(adv_user_id, adv_tenant_id)
        adv.company_name = "CloudCRM Corp"
        adv.save()

        cmp = AdCampaign.create(
            id=f"cmp_{uuid.uuid4().hex[:8]}",
            advertiser_id=adv.id,
            name="CloudCRM Global Push",
            product_name="CloudCRM Pro",
            description="Leading AI-powered sales CRM",
            advertisement_text="Try CloudCRM Pro free for 14 days with zero commitment.",
            landing_url="https://cloudcrm.io/free-trial",
            target_categories=["crm", "sales", "marketing"],
            keywords=["crm", "pipeline", "leads", "sales", "management"],
            daily_budget=50.0,
            total_budget=500.0,
            spent_today=0.0,
            total_spent=0.0,
            pricing_model="cpc",
            bid_amount=0.50,
            priority=10,
            status="active",
            moderation_status="pending",  # initially pending
            create_time=current_timestamp(),
        )
        self.assertEqual(cmp.moderation_status, "pending")

        # --- STEP 2: Admin Moderation ---
        # Before approval, campaign cannot match
        matched_unapproved = AdEngineService.match_campaign_for_query(
            tenant_id="any_tenant",
            user_id="any_user",
            user_query="best crm for sales leads",
        )
        self.assertIsNone(matched_unapproved, "Pending campaigns must NEVER be served to users")

        # Admin approves
        cmp.moderation_status = "approved"
        cmp.moderation_note = "Approved by Admin QA"
        cmp.save()
        self.assertEqual(AdCampaign.get_by_id(cmp.id).moderation_status, "approved")

        # --- STEP 3: Advertiser Tops Up Wallet via Atmos ($100.00) ---
        create_ok, _, order_data = AtmosService.create_payment_order(
            user_id=adv_user_id,
            tenant_id=adv_tenant_id,
            purpose="advertiser_deposit",
            amount_usd=100.0,
            advertiser_id=adv.id,
        )
        self.assertTrue(create_ok)
        order_id = order_data["order_id"]

        AtmosService.pre_apply_card(order_id, "8600 1111 2222 3333", "12/28", adv_user_id)
        apply_ok, _, apply_data = AtmosService.apply_otp(order_id, "654321", adv_user_id)
        self.assertTrue(apply_ok)
        self.assertEqual(apply_data["status"], "paid")

        adv_refreshed = Advertiser.get_by_id(adv.id)
        self.assertEqual(adv_refreshed.balance, 100.0)

        # --- STEP 4: Free User AI Prompt Injection ---
        free_user_id = f"free_u_{uuid.uuid4().hex[:6]}"
        free_tenant_id = f"free_t_{uuid.uuid4().hex[:6]}"
        create_user(user_id=free_user_id, nickname="Free Starter", email="starter@swipies.app")
        create_tenant(tenant_id=free_tenant_id, name="Starter Workspace", plan_type="free")
        create_user_tenant(user_id=free_user_id, tenant_id=free_tenant_id)

        # Confirm free user is ad-eligible
        self.assertTrue(AdPolicyService.is_ad_eligible_user(free_tenant_id))

        base_prompt = "You are a versatile AI assistant."
        effective_prompt = AdPolicyService.build_effective_system_prompt(
            tenant_id=free_tenant_id,
            base_system_prompt=base_prompt,
            user_query="Can you suggest a good CRM tool for managing sales pipeline?",
            user_id=free_user_id,
            conversation_id="conv_e2e_1",
        )

        # Assertions on prompt
        self.assertIn("[COMMERCIAL GUIDELINES & SPONSORED CONTENT POLICY]", effective_prompt)
        self.assertIn("CloudCRM Pro", effective_prompt)
        self.assertIn("https://cloudcrm.io/free-trial", effective_prompt)
        self.assertIn("https://swipies.app", effective_prompt)
        self.assertIn("⚡ Generated by", effective_prompt)
        self.assertIn(f"ref={free_user_id}", effective_prompt)
        self.assertIn("utm_source=swipies_ai", effective_prompt)
        self.assertIn("utm_medium=chat_watermark", effective_prompt)
        self.assertIn("utm_campaign=share_attribution", effective_prompt)

        # Verify impression was recorded
        imp_count = AdImpression.select().where(AdImpression.campaign_id == cmp.id).count()
        self.assertGreaterEqual(imp_count, 1)

        # --- STEP 5: Click Tracking & Balance Deduction ---
        imp = AdImpression.select().where(AdImpression.campaign_id == cmp.id).order_by(AdImpression.create_time.desc()).first()
        self.assertIsNotNone(imp)

        target_redirect = AdEngineService.track_click(click_token=imp.id, ip_hash="test_ip_hash_123")
        self.assertEqual(target_redirect, "https://cloudcrm.io/free-trial")

        # Verify advertiser balance deducted by CPC ($0.50)
        adv_after_click = Advertiser.get_by_id(adv.id)
        self.assertEqual(adv_after_click.balance, 99.50)

        # Verify AdClick record
        click_count = AdClick.select().where(AdClick.campaign_id == cmp.id).count()
        self.assertEqual(click_count, 1)

        # --- STEP 5.1: Attribution Visits & Conversion Tracking ---
        AttributionService.record_attribution_visit(
            referrer_id=free_user_id,
            tenant_id=free_tenant_id,
            ip="192.168.1.100",
            user_agent="Mozilla/5.0",
        )
        AttributionService.record_attribution_visit(
            referrer_id=free_user_id,
            tenant_id=free_tenant_id,
            ip="192.168.1.101",
            user_agent="Mozilla/5.0",
        )

        attr_stats = AttributionService.get_attribution_analytics(user_id=free_user_id)
        self.assertEqual(attr_stats["total_visits"], 2)
        self.assertEqual(attr_stats["unique_visitors"], 2)
        self.assertIn(f"ref={free_user_id}", attr_stats["utm_link"])

        # Simulate a visitor who converts and signs up
        referred_new_user_id = f"new_u_{uuid.uuid4().hex[:6]}"
        new_u = create_user(user_id=referred_new_user_id, nickname="Converted Friend", email="friend@swipies.app")
        new_u.referred_by_id = free_user_id
        new_u.save()

        attr_stats_after = AttributionService.get_attribution_analytics(user_id=free_user_id)
        self.assertEqual(attr_stats_after["total_signups"], 1)
        self.assertEqual(attr_stats_after["conversion_rate"], 50.0)

        # --- STEP 6: User Upgrades to Pro via Atmos ---
        upgrade_ok, _, up_order = AtmosService.create_payment_order(
            user_id=free_user_id,
            tenant_id=free_tenant_id,
            purpose="subscription_upgrade",
            plan_id="pro",
        )
        self.assertTrue(upgrade_ok)
        up_order_id = up_order["order_id"]

        AtmosService.pre_apply_card(up_order_id, "9860 7777 8888 9999", "05/29", free_user_id)
        up_applied, _, _ = AtmosService.apply_otp(up_order_id, "123456", free_user_id)
        self.assertTrue(up_applied)

        tenant_now_pro = Tenant.get_by_id(free_tenant_id)
        self.assertEqual(tenant_now_pro.plan_type, "pro")
        self.assertIsNotNone(tenant_now_pro.plan_expiry_date)

        # --- STEP 7: Pro User Prompt is 100% Clean & Untouched ---
        self.assertFalse(AdPolicyService.is_ad_eligible_user(free_tenant_id))
        self.assertTrue(AdPolicyService.is_ad_exempt(free_tenant_id, free_user_id))

        clean_prompt = AdPolicyService.build_effective_system_prompt(
            tenant_id=free_tenant_id,
            base_system_prompt="You are a versatile AI assistant.",
            user_query="Can you suggest a good CRM tool for managing sales pipeline?",
            user_id=free_user_id,
            conversation_id="conv_e2e_2",
        )
        self.assertEqual(
            clean_prompt,
            "You are a versatile AI assistant.",
            "Pro plan subscriber must receive 100% pristine prompt with 0 ad tokens and zero branding",
        )

    def test_e2e_promo_code_and_advertiser_bonus_fulfillment(self):
        """Test E2E: Promo code discount on Plus upgrade and Advertiser bonus credit top-up via Atmos."""
        from api.db.services.promo_code_service import PromoCodeService

        # 1. Create discount promo code for Plus plan (50% off)
        promo_half = PromoCodeService.create_promo_code(
            code="PLUS50",
            discount_type="percent",
            discount_value=50.0,
            applies_to="subscription",
            plan_id="plus",
            max_uses=10,
        )

        user_plus_id = "user_plus_promo"
        tenant_plus_id = "tenant_plus_promo"
        create_user(user_plus_id, nickname="Plus Seeker", email="seeker@swipies.app")
        create_tenant(tenant_plus_id, name="Seeker Org", plan_type="free")
        create_user_tenant(user_plus_id, tenant_plus_id)

        # 2. Checkout Plus plan with promo code PLUS50 (Original $9.99 -> $5.00)
        order_ok, _, order_data = AtmosService.create_payment_order(
            user_id=user_plus_id,
            tenant_id=tenant_plus_id,
            purpose="subscription_upgrade",
            plan_id="plus",
            promo_code="PLUS50",
        )
        self.assertTrue(order_ok)
        self.assertAlmostEqual(order_data["amount_usd"], 5.00, delta=0.05)

        # Pre-apply card & apply OTP
        ord_id = order_data["order_id"]
        AtmosService.pre_apply_card(ord_id, "8600 1234 5678 9999", "12/28", user_plus_id)
        paid_ok, _, res_pay = AtmosService.apply_otp(ord_id, "123456", user_plus_id)
        self.assertTrue(paid_ok)

        # Verify tenant upgraded to Plus
        tenant_obj = Tenant.get_by_id(tenant_plus_id)
        self.assertEqual(tenant_obj.plan_type, "plus")

        # Verify promo code usage was recorded
        usages = list(PromoCodeUsage.select().where(PromoCodeUsage.promo_code_id == promo_half.id))
        self.assertEqual(len(usages), 1)
        self.assertEqual(usages[0].user_id, user_plus_id)

        # 3. Create Advertiser bonus promo code ($30 bonus on deposit)
        promo_adv_bonus = PromoCodeService.create_promo_code(
            code="BOOST30",
            discount_type="advertiser_bonus_usd",
            discount_value=30.0,
            applies_to="advertiser_deposit",
            max_uses=5,
        )

        adv_user_id = "adv_user_promo"
        adv_tenant_id = "adv_tenant_promo"
        create_user(adv_user_id, nickname="Marketing Pro", email="mkt@swipies.app")
        create_tenant(adv_tenant_id, name="Marketing Org", plan_type="free")
        create_user_tenant(adv_user_id, adv_tenant_id)
        adv_obj = AdvertiserService.get_or_create_for_user(adv_user_id, adv_tenant_id, "Targeting AI")
        adv_obj.balance = 0.0
        adv_obj.save()

        # Create deposit order for $50 with promo code BOOST30
        dep_ok, _, dep_data = AtmosService.create_payment_order(
            user_id=adv_user_id,
            tenant_id=adv_tenant_id,
            purpose="advertiser_deposit",
            advertiser_id=adv_obj.id,
            amount_usd=50.0,
            promo_code="BOOST30",
        )
        self.assertTrue(dep_ok)
        self.assertEqual(dep_data["amount_usd"], 50.0)

        dep_ord_id = dep_data["order_id"]
        AtmosService.pre_apply_card(dep_ord_id, "9860 0000 1111 2222", "11/27", adv_user_id)
        dep_paid_ok, _, dep_res = AtmosService.apply_otp(dep_ord_id, "123456", adv_user_id)
        self.assertTrue(dep_paid_ok)

        # Verify Advertiser balance received both base deposit ($50) + promo bonus ($30) = $80
        adv_refreshed = Advertiser.get_by_id(adv_obj.id)
        self.assertAlmostEqual(adv_refreshed.balance, 80.0, places=2)


if __name__ == "__main__":
    unittest.main()
