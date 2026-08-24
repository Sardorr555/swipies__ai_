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

# Create temporary SQLite database file for tests
TEST_DB_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_ads_temp.db"))
test_db = SqliteDatabase(TEST_DB_FILE)

from api.db.db_models import (
    DB,
    Advertiser,
    AdCampaign,
    AdVariant,
    AdImpression,
    AdClick,
    AdConversion,
    AdTransaction,
    AdSettings,
    PromoCode,
    PromoCodeUsage,
    User,
    Tenant,
    SubscriptionPlan,
    UserOnboarding,
    PaymentOrder,
    SavedPaymentMethod,
    UserSubscription,
)
from api.db.services.ad_engine_service import (
    AdvertiserService,
    AdCampaignService,
    AdVariantService,
    AdImpressionService,
    AdClickService,
    AdConversion,
    ConversionTrackingService,
    AdOptimizerService,
    AdExportService,
    AdTransactionService,
    AdSettingsService,
    AdEngineService,
)
from api.db.services.recurring_subscription_service import (
    RecurringSubscriptionService,
    SavedPaymentMethodService,
)
from api.db.services.ad_policy_service import AdPolicyService, SWIPIES_ADVERTISING_RULES
from common.time_utils import current_timestamp


class TestSwipiesAdsSystem(unittest.TestCase):
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
            Advertiser,
            AdCampaign,
            AdVariant,
            AdImpression,
            AdClick,
            AdConversion,
            AdTransaction,
            AdSettings,
            PromoCode,
            PromoCodeUsage,
            User,
            Tenant,
            SubscriptionPlan,
            UserOnboarding,
            PaymentOrder,
            SavedPaymentMethod,
            UserSubscription,
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
        test_db.drop_tables([
            Advertiser,
            AdCampaign,
            AdImpression,
            AdClick,
            AdTransaction,
            AdSettings,
            User,
            Tenant,
            SubscriptionPlan,
            UserOnboarding,
        ])
        test_db.close()
        if os.path.exists(TEST_DB_FILE):
            try:
                os.remove(TEST_DB_FILE)
            except Exception:
                pass

    def setUp(self):
        AdClick.delete().execute()
        AdImpression.delete().execute()
        AdCampaign.delete().execute()
        AdTransaction.delete().execute()
        Advertiser.delete().execute()
        AdSettings.delete().execute()
        Tenant.delete().execute()
        User.delete().execute()

    def test_01_free_tier_ad_prompt_injection_and_matching(self):
        """Test 1: Free tier user prompt injection with matching campaign and attribution."""
        adv = Advertiser.create(
            id="adv_test_01",
            tenant_id="tenant_adv_01",
            user_id="user_adv_01",
            company_name="CloudCRM Inc",
            balance=50.0,
            status="active",
            create_time=current_timestamp(),
        )

        cmp = AdCampaign.create(
            id="cmp_crm_01",
            advertiser_id=adv.id,
            name="CRM Growth 2026",
            product_name="CloudCRM Pro",
            description="All-in-one sales CRM with email automation",
            advertisement_text="Get 14 days free trial, no credit card required.",
            landing_url="https://cloudcrm.example.com/trial",
            target_categories=["crm", "sales", "marketing"],
            keywords=["crm", "pipeline", "leads", "sales"],
            daily_budget=20.0,
            total_budget=100.0,
            spent_today=0.0,
            total_spent=0.0,
            pricing_model="cpc",
            bid_amount=0.25,
            priority=5,
            status="active",
            moderation_status="approved",
            create_time=current_timestamp(),
        )

        base_system = "You are a helpful AI assistant."
        user_query = "What is the best CRM software for managing sales leads?"

        effective_prompt = AdPolicyService.build_effective_system_prompt(
            tenant_id="free_tenant_123",
            base_system_prompt=base_system,
            user_query=user_query,
            user_id="free_user_123",
        )

        self.assertIn("You are a helpful AI assistant.", effective_prompt)
        self.assertIn("COMMERCIAL GUIDELINES & SPONSORED CONTENT POLICY", effective_prompt)
        self.assertIn("[Sponsored]", effective_prompt)
        self.assertIn("CloudCRM Pro", effective_prompt)
        self.assertIn("https://cloudcrm.example.com/trial", effective_prompt)
        self.assertIn("https://swipies.app", effective_prompt)
        self.assertIn("Generated by", effective_prompt)

    def test_02_plus_pro_100_percent_ad_free_guarantee(self):
        """Test 2: Plus/Pro users receive 100% untouched system prompt with zero ad tokens."""
        adv = Advertiser.create(
            id="adv_test_02",
            tenant_id="tenant_adv_02",
            user_id="user_adv_02",
            company_name="CloudCRM Inc",
            balance=100.0,
            status="active",
            create_time=current_timestamp(),
        )
        AdCampaign.create(
            id="cmp_crm_02",
            advertiser_id=adv.id,
            name="CRM Growth",
            product_name="CloudCRM Pro",
            advertisement_text="Get 14 days free trial.",
            landing_url="https://cloudcrm.example.com",
            target_categories=["crm"],
            keywords=["crm"],
            daily_budget=20.0,
            total_budget=100.0,
            bid_amount=0.25,
            status="active",
            moderation_status="approved",
            create_time=current_timestamp(),
        )

        Tenant.create(
            id="tenant_plus_user",
            name="Plus User",
            plan_type="plus",
            llm_id="default_llm",
            embd_id="default_embd",
            asr_id="default_asr",
            img2txt_id="default_img2txt",
            rerank_id="default_rerank",
            parser_ids="1",
        )
        Tenant.create(
            id="tenant_pro_user",
            name="Pro User",
            plan_type="pro",
            llm_id="default_llm",
            embd_id="default_embd",
            asr_id="default_asr",
            img2txt_id="default_img2txt",
            rerank_id="default_rerank",
            parser_ids="1",
        )

        base_system = "Strict system prompt for professional analysis."
        user_query = "Recommend a top crm software solution."

        plus_prompt = AdPolicyService.build_effective_system_prompt(
            tenant_id="tenant_plus_user",
            base_system_prompt=base_system,
            user_query=user_query,
        )
        self.assertEqual(plus_prompt, base_system)
        self.assertNotIn("Sponsored", plus_prompt)
        self.assertNotIn("CloudCRM", plus_prompt)
        self.assertNotIn("https://swipies.app", plus_prompt)

        pro_prompt = AdPolicyService.build_effective_system_prompt(
            tenant_id="tenant_pro_user",
            base_system_prompt=base_system,
            user_query=user_query,
        )
        self.assertEqual(pro_prompt, base_system)
        self.assertNotIn("Sponsored", pro_prompt)

    def test_03_frequency_capping_enforcement(self):
        """Test 3: Frequency capping prevents spamming user past max daily impressions."""
        adv = Advertiser.create(
            id="adv_test_03",
            tenant_id="tenant_adv_03",
            user_id="user_adv_03",
            company_name="Analytics Tool",
            balance=50.0,
            status="active",
            create_time=current_timestamp(),
        )

        cmp = AdCampaign.create(
            id="cmp_analytics_03",
            advertiser_id=adv.id,
            name="Analytics Campaign",
            product_name="SuperAnalytics",
            advertisement_text="Realtime dashboards.",
            landing_url="https://analytics.example.com",
            target_categories=["analytics"],
            keywords=["analytics", "dashboard"],
            daily_budget=50.0,
            total_budget=500.0,
            bid_amount=0.10,
            status="active",
            moderation_status="approved",
            create_time=current_timestamp(),
        )

        user_id = "frequent_user_456"
        for i in range(3):
            matched = AdEngineService.match_campaign_for_query(
                tenant_id="tenant_free_456",
                user_id=user_id,
                user_query="Need analytics dashboard tool",
            )
            self.assertIsNotNone(matched, f"Impression {i+1} should match")
            self.assertEqual(matched["id"], cmp.id)

        matched_4th = AdEngineService.match_campaign_for_query(
            tenant_id="tenant_free_456",
            user_id=user_id,
            user_query="Need analytics dashboard tool",
        )
        self.assertIsNone(matched_4th, "4th query on same day must be blocked by frequency cap")

    def test_04_budget_and_balance_exhaustion(self):
        """Test 4: Campaign is not matched when advertiser balance or daily budget is zero."""
        adv = Advertiser.create(
            id="adv_test_04",
            tenant_id="tenant_adv_04",
            user_id="user_adv_04",
            company_name="Zero Balance Co",
            balance=0.05,  # Less than bid amount
            status="active",
            create_time=current_timestamp(),
        )

        cmp = AdCampaign.create(
            id="cmp_zerobal_04",
            advertiser_id=adv.id,
            name="No Balance Campaign",
            product_name="EmptyWallet Pro",
            advertisement_text="Test ad.",
            landing_url="https://empty.example.com",
            keywords=["hosting"],
            daily_budget=10.0,
            total_budget=50.0,
            bid_amount=0.50,
            status="active",
            moderation_status="approved",
            create_time=current_timestamp(),
        )

        matched = AdEngineService.match_campaign_for_query(
            tenant_id="tenant_free_789",
            user_id="user_789",
            user_query="Best hosting server provider",
        )
        self.assertIsNone(matched, "Campaign with insufficient balance must not participate in auction")

    def test_05_click_tracking_and_balance_deduction(self):
        """Test 5: Click tracking records AdClick, deducts CPC bid, and returns landing URL."""
        adv = Advertiser.create(
            id="adv_test_05",
            tenant_id="tenant_adv_05",
            user_id="user_adv_05",
            company_name="ClickTrack Inc",
            balance=10.0,
            status="active",
            create_time=current_timestamp(),
        )

        cmp = AdCampaign.create(
            id="cmp_click_05",
            advertiser_id=adv.id,
            name="Click Test Campaign",
            product_name="ClickSpeed",
            advertisement_text="Try now.",
            landing_url="https://clickspeed.example.com/dest",
            keywords=["vpn"],
            daily_budget=10.0,
            total_budget=100.0,
            bid_amount=0.50,
            status="active",
            moderation_status="approved",
            create_time=current_timestamp(),
        )

        click_token = f"{cmp.id}_imp999_user999"
        dest_url = AdEngineService.track_click(click_token=click_token, user_id="user999", ip_hash="test_ip")

        self.assertEqual(dest_url, "https://clickspeed.example.com/dest")

        adv = Advertiser.get_by_id(adv.id)
        self.assertEqual(adv.balance, 9.50)

        tx = AdTransaction.get_or_none(AdTransaction.advertiser_id == adv.id)
        self.assertIsNotNone(tx)
        self.assertEqual(tx.amount, -0.50)
        self.assertEqual(tx.type, "spend_cpc")

    def test_06_admin_moderation_queue(self):
        """Test 6: Admin network overview and campaign moderation status."""
        adv = Advertiser.create(
            id="adv_test_06",
            tenant_id="tenant_adv_06",
            user_id="user_adv_06",
            company_name="Moderation Corp",
            balance=20.0,
            status="active",
            create_time=current_timestamp(),
        )

        cmp = AdCampaign.create(
            id="cmp_mod_06",
            advertiser_id=adv.id,
            name="Pending Campaign",
            product_name="ModProduct",
            advertisement_text="Under review.",
            landing_url="https://mod.example.com",
            keywords=["security"],
            daily_budget=10.0,
            total_budget=100.0,
            bid_amount=0.20,
            status="active",
            moderation_status="pending",
            create_time=current_timestamp(),
        )

        matched = AdEngineService.match_campaign_for_query(
            tenant_id="tenant_free_111",
            user_id="user_111",
            user_query="Need security software",
        )
        self.assertIsNone(matched, "Pending moderation campaign must not be served")

        cmp.moderation_status = "approved"
        cmp.save()

        matched_after_approval = AdEngineService.match_campaign_for_query(
            tenant_id="tenant_free_111",
            user_id="user_111",
            user_query="Need security software",
        )
        self.assertIsNotNone(matched_after_approval, "Approved campaign must match")

    def test_07_wallet_deposit(self):
        """Test 7: Top-up deposit credits advertiser balance and creates ledger entry."""
        adv = Advertiser.create(
            id="adv_test_07",
            tenant_id="tenant_adv_07",
            user_id="user_adv_07",
            company_name="TopUp Corp",
            balance=5.0,
            status="active",
            create_time=current_timestamp(),
        )

        success = AdEngineService.deposit_balance(adv.id, 50.0, "Credit Card Top-Up")
        self.assertTrue(success)

        adv = Advertiser.get_by_id(adv.id)
        self.assertEqual(adv.balance, 55.0)

        tx = AdTransaction.get(AdTransaction.advertiser_id == adv.id, AdTransaction.type == "deposit")
        self.assertEqual(tx.amount, 50.0)

    def test_08_language_and_model_targeting(self):
        """Test 8: Language-aware and model-level ad targeting."""
        adv = Advertiser.create(
            id="adv_test_08",
            tenant_id="tenant_adv_08",
            user_id="user_adv_08",
            company_name="Targeting Pro",
            balance=20.0,
            status="active",
            create_time=current_timestamp(),
        )

        # Campaign 1: targeted only to Uzbek language ('uz') and DeepSeek models
        cmp_uz = AdCampaign.create(
            id="cmp_uz_deepseek",
            advertiser_id=adv.id,
            name="Uzbek Logistics",
            product_name="YetkazibBerish AI",
            advertisement_text="Toshkent boylab tez yetkazib berish xizmati.",
            landing_url="https://yetkazib.uz",
            keywords=["dostavka", "yetkazib", "logistika"],
            target_languages=["uz"],
            target_models=["deepseek"],
            daily_budget=10.0,
            total_budget=100.0,
            bid_amount=0.30,
            status="active",
            moderation_status="approved",
            create_time=current_timestamp(),
        )

        # Campaign 2: targeted only to Russian language ('ru') and GPT-4o
        cmp_ru = AdCampaign.create(
            id="cmp_ru_gpt",
            advertiser_id=adv.id,
            name="Russian Delivery",
            product_name="БыстраяДоставка РФ",
            advertisement_text="Курьерская доставка для бизнеса.",
            landing_url="https://dostavka.ru",
            keywords=["dostavka", "доставка", "курьер"],
            target_languages=["ru"],
            target_models=["gpt-4o"],
            daily_budget=10.0,
            total_budget=100.0,
            bid_amount=0.30,
            status="active",
            moderation_status="approved",
            create_time=current_timestamp(),
        )

        # Query in Uzbek asking with DeepSeek model
        match_uz = AdEngineService.match_campaign_for_query(
            tenant_id="tenant_uz_user",
            user_id="user_uz_1",
            user_query="Menga toshkentda tez yetkazib berish va logistika kerak",
            lang="uz",
            model_name="deepseek-r1",
        )
        self.assertIsNotNone(match_uz)
        self.assertEqual(match_uz["campaign_id"], cmp_uz.id)

        # Query in Russian with DeepSeek model - should not match cmp_ru because model is deepseek not gpt-4o, and shouldn't match cmp_uz because language is ru
        match_ru_mismatch = AdEngineService.match_campaign_for_query(
            tenant_id="tenant_ru_user",
            user_id="user_ru_1",
            user_query="Мне нужна срочная доставка и логистика",
            lang="ru",
            model_name="claude-3-5-sonnet",
        )
        self.assertIsNone(match_ru_mismatch, "Should reject when model does not match campaign targeting")

        # Query in Russian with GPT-4o model - should match cmp_ru
        match_ru_correct = AdEngineService.match_campaign_for_query(
            tenant_id="tenant_ru_user",
            user_id="user_ru_1",
            user_query="Мне нужна срочная доставка и курьер",
            lang="ru",
            model_name="gpt-4o",
        )
        self.assertIsNotNone(match_ru_correct)
        self.assertEqual(match_ru_correct["campaign_id"], cmp_ru.id)

    def test_09_telegram_notification_service(self):
        """Test 9: Telegram notification dispatcher formatting and resilience."""
        from api.db.services.telegram_notification_service import TelegramNotificationService
        from unittest.mock import patch

        cmp_mock = AdCampaign(
            id="cmp_mock_tg",
            name="Mock Promo",
            product_name="Mock AI",
            advertisement_text="Special offer 50% off",
            landing_url="https://mock.ai",
            daily_budget=25.0,
            bid_amount=0.20,
            target_languages=["uz", "ru"],
            target_models=["deepseek"],
        )

        with patch("api.db.services.telegram_notification_service.requests.post") as mock_post:
            mock_post.return_value.status_code = 200

            # Test admin new campaign alert
            res_cmp = TelegramNotificationService.notify_admin_new_campaign(cmp_mock, advertiser_name="Global Tech")
            # If TELEGRAM_NOTIFICATIONS_ENABLED is True but token is empty, returns False safely
            self.assertIsInstance(res_cmp, bool)

            # Test admin payment notification
            res_pay = TelegramNotificationService.notify_admin_payment_received({
                "order_id": "ord_12345",
                "amount_usd": 50.0,
                "amount_uzs": 640000,
                "purpose": "advertiser_deposit",
                "card_masked": "8600 •••• •••• 1234",
            })
            self.assertIsInstance(res_pay, bool)

    def test_10_negative_keywords_filtering(self):
        """Test 10: Negative keywords block campaign matching even on matched positive keywords."""
        adv = AdvertiserService.get_or_create_for_user("user_neg", "tenant_neg", "Cloud Soft")
        adv.balance = 100.0
        adv.save()

        cmp_safe = AdCampaign.create(
            id="cmp_safe_1",
            advertiser_id=adv.id,
            name="Safe Software",
            product_name="Pro Accounting Suite",
            description="Leading accounting software",
            advertisement_text="Get 14 days trial for Pro Accounting",
            landing_url="https://proaccounting.uz",
            target_categories=["accounting", "software"],
            keywords=["бухгалтерия", "1с", "учет", "налоги"],
            negative_keywords=["бесплатно", "скачать", "взлом", "crack", "torrent"],
            daily_budget=20.0,
            total_budget=100.0,
            pricing_model="cpc",
            bid_amount=0.50,
            status="active",
            moderation_status="approved",
            create_time=current_timestamp(),
            update_time=current_timestamp(),
        )

        # 1. Query with positive match and NO negative keyword -> MATCHES
        match_clean = AdEngineService.match_campaign_for_query(
            tenant_id="tenant_neg_user",
            user_id="user_neg_1",
            user_query="Как вести налоговый учет и бухгалтерия для компании?",
            lang="ru",
        )
        self.assertIsNotNone(match_clean)
        self.assertEqual(match_clean["campaign_id"], cmp_safe.id)

        # 2. Query with positive match BUT contains negative keyword ('бесплатно') -> BLOCKED
        match_negative = AdEngineService.match_campaign_for_query(
            tenant_id="tenant_neg_user",
            user_id="user_neg_2",
            user_query="Где скачать бухгалтерия бесплатно без смс?",
            lang="ru",
        )
        self.assertIsNone(match_negative)

        # 3. Query with positive match BUT contains negative keyword ('crack') -> BLOCKED
        match_crack = AdEngineService.match_campaign_for_query(
            tenant_id="tenant_neg_user",
            user_id="user_neg_3",
            user_query="1с учет crack license key generator",
            lang="ru",
        )
        self.assertIsNone(match_crack)

    def test_11_promo_code_service_discounts_and_validation(self):
        """Test 11: PromoCodeService discount computation, usage tracking, and multi-tier limits."""
        from api.db.services.promo_code_service import PromoCodeService

        # 1. Percentage discount: 20% off
        promo_pct = PromoCodeService.create_promo_code(
            code="SUMMER20",
            discount_type="percent",
            discount_value=20.0,
            applies_to="all",
            max_uses=2,
        )
        self.assertIsNotNone(promo_pct)
        self.assertEqual(promo_pct.code, "SUMMER20")

        # Validate on $29.99
        valid, msg, res = PromoCodeService.validate_and_apply_promo(
            code="summer20",  # Case insensitive
            user_id="user_promo_1",
            purpose="subscription_upgrade",
            original_amount_usd=29.99,
        )
        self.assertTrue(valid)
        self.assertAlmostEqual(res["discount_usd"], 6.00, places=2)
        self.assertAlmostEqual(res["final_amount_usd"], 23.99, places=2)

        # Record usage for user 1
        PromoCodeService.record_promo_usage(promo_pct.id, "user_promo_1", "ord_1", res["discount_usd"])

        # Try reusing by user 1 -> Should be rejected (one use per user)
        valid_reuse, msg_reuse, _ = PromoCodeService.validate_and_apply_promo(
            code="SUMMER20",
            user_id="user_promo_1",
            purpose="subscription_upgrade",
            original_amount_usd=29.99,
        )
        self.assertFalse(valid_reuse)
        self.assertIn("уже использовали", msg_reuse.lower())

        # User 2 uses it -> Should succeed (used 2/2)
        valid_u2, _, res_u2 = PromoCodeService.validate_and_apply_promo(
            code="SUMMER20",
            user_id="user_promo_2",
            purpose="subscription_upgrade",
            original_amount_usd=29.99,
        )
        self.assertTrue(valid_u2)
        PromoCodeService.record_promo_usage(promo_pct.id, "user_promo_2", "ord_2", res_u2["discount_usd"])

        # User 3 tries -> Max uses reached
        valid_u3, msg_u3, _ = PromoCodeService.validate_and_apply_promo(
            code="SUMMER20",
            user_id="user_promo_3",
            purpose="subscription_upgrade",
            original_amount_usd=29.99,
        )
        self.assertFalse(valid_u3)
        self.assertIn("исчерпан", msg_u3.lower())

        # 2. Fixed USD discount: $10 off
        promo_fix = PromoCodeService.create_promo_code(
            code="PROMO10",
            discount_type="fixed_usd",
            discount_value=10.0,
            applies_to="subscription",
            plan_id="pro",
        )
        valid_fix, _, res_fix = PromoCodeService.validate_and_apply_promo(
            code="PROMO10",
            user_id="user_fix_1",
            purpose="subscription_upgrade",
            original_amount_usd=29.99,
            plan_id="pro",
        )
        self.assertTrue(valid_fix)
        self.assertAlmostEqual(res_fix["discount_usd"], 10.0, places=2)
        self.assertAlmostEqual(res_fix["final_amount_usd"], 19.99, places=2)

        # Reject if plan doesn't match ('plus' instead of 'pro')
        valid_plan_mismatch, msg_mismatch, _ = PromoCodeService.validate_and_apply_promo(
            code="PROMO10",
            user_id="user_fix_2",
            purpose="subscription_upgrade",
            original_amount_usd=9.99,
            plan_id="plus",
        )
        self.assertFalse(valid_plan_mismatch)

        # 3. Advertiser bonus funds promo
        promo_bonus = PromoCodeService.create_promo_code(
            code="BONUS50",
            discount_type="advertiser_bonus_usd",
            discount_value=25.0,
            applies_to="advertiser_deposit",
        )
        valid_bonus, _, res_bonus = PromoCodeService.validate_and_apply_promo(
            code="BONUS50",
            user_id="user_adv_bonus",
            purpose="advertiser_deposit",
            original_amount_usd=50.0,
        )
        self.assertTrue(valid_bonus)
        self.assertEqual(res_bonus["bonus_usd"], 25.0)
        self.assertEqual(res_bonus["final_amount_usd"], 50.0)

    def test_12_timeline_analytics_and_demographic_breakdowns(self):
        """Test 12: Daily timeline aggregation, CTR calculations, and language/model/device breakdowns."""
        user_id = "user_timeline_12"
        tenant_id = "tenant_timeline_12"
        adv = Advertiser.create(
            id="adv_timeline_12",
            tenant_id=tenant_id,
            user_id=user_id,
            company_name="Timeline Analytics Corp",
            balance=200.0,
            status="active",
            create_time=current_timestamp(),
        )

        cmp = AdCampaign.create(
            id="cmp_timeline_12",
            advertiser_id=adv.id,
            name="Cloud ERP",
            product_name="Swipies ERP",
            advertisement_text="All-in-one ERP system.",
            landing_url="https://erp.example.com",
            target_categories=["erp", "business"],
            keywords=["erp", "crm"],
            pricing_model="cpc",
            bid_amount=0.50,
            status="active",
            moderation_status="approved",
            create_time=current_timestamp(),
        )

        now_ts = current_timestamp()
        day_ms = 86400 * 1000

        # Create impressions across different days, languages, models, and devices
        # Day 0 (today): 3 impressions (2 RU, 1 UZ; 2 gpt-4o, 1 deepseek-r1; 2 desktop, 1 mobile)
        imp1 = AdImpression.create(
            id="imp_t1",
            campaign_id=cmp.id,
            advertiser_id=adv.id,
            user_id="u1",
            language="ru",
            model_name="gpt-4o",
            device_type="desktop",
            cost=0.0,
            query_intent="лучшая erp система",
            create_time=now_ts,
        )
        imp2 = AdImpression.create(
            id="imp_t2",
            campaign_id=cmp.id,
            advertiser_id=adv.id,
            user_id="u2",
            language="ru",
            model_name="gpt-4o",
            device_type="desktop",
            cost=0.0,
            query_intent="автоматизация бизнеса",
            create_time=now_ts,
        )
        imp3 = AdImpression.create(
            id="imp_t3",
            campaign_id=cmp.id,
            advertiser_id=adv.id,
            user_id="u3",
            language="uz",
            model_name="deepseek-r1",
            device_type="mobile",
            cost=0.0,
            query_intent="biznes uchun erp dasturi",
            create_time=now_ts,
        )

        # Day 1 ago: 2 impressions (1 EN, 1 UZ; 1 claude-3-5, 1 gpt-4o; 1 mobile, 1 tablet)
        imp4 = AdImpression.create(
            id="imp_t4",
            campaign_id=cmp.id,
            advertiser_id=adv.id,
            user_id="u4",
            language="en",
            model_name="claude-3-5-sonnet",
            device_type="mobile",
            cost=0.0,
            query_intent="cloud erp solution",
            create_time=now_ts - day_ms,
        )
        imp5 = AdImpression.create(
            id="imp_t5",
            campaign_id=cmp.id,
            advertiser_id=adv.id,
            user_id="u5",
            language="uz",
            model_name="gpt-4o",
            device_type="tablet",
            cost=0.0,
            query_intent="ombor hisobi dasturi",
            create_time=now_ts - day_ms,
        )

        # Clicks: 1 click on Day 0 (imp1) and 1 click on Day 1 (imp4)
        AdClick.create(
            id="clk_t1",
            campaign_id=cmp.id,
            impression_id=imp1.id,
            advertiser_id=adv.id,
            user_id="u1",
            cost=0.50,
            language="ru",
            model_name="gpt-4o",
            device_type="desktop",
            create_time=now_ts,
        )
        AdClick.create(
            id="clk_t2",
            campaign_id=cmp.id,
            impression_id=imp4.id,
            advertiser_id=adv.id,
            user_id="u4",
            cost=0.50,
            language="en",
            model_name="claude-3-5-sonnet",
            device_type="mobile",
            create_time=now_ts - day_ms,
        )

        # 1. Test Advertiser Timeline Analytics
        timeline_res = AdEngineService.get_advertiser_timeline_analytics(
            user_id=user_id,
            tenant_id=tenant_id,
            days=14,
        )
        self.assertEqual(timeline_res["days"], 14)
        self.assertEqual(timeline_res["total_impressions"], 5)
        self.assertEqual(timeline_res["total_clicks"], 2)
        self.assertEqual(timeline_res["total_spend"], 1.00)
        self.assertAlmostEqual(timeline_res["ctr"], 40.0, places=1)
        self.assertEqual(len(timeline_res["timeline"]), 14)

        # Verify language counts: RU=2, UZ=2, EN=1
        self.assertEqual(timeline_res["languages"]["ru"], 2)
        self.assertEqual(timeline_res["languages"]["uz"], 2)
        self.assertEqual(timeline_res["languages"]["en"], 1)

        # Verify models counts: gpt-4o=3, deepseek=1, claude=1
        self.assertEqual(timeline_res["models"]["gpt-4o"], 3)
        self.assertEqual(timeline_res["models"]["deepseek"], 1)
        self.assertEqual(timeline_res["models"]["claude"], 1)

        # Verify devices: desktop=2, mobile=2, tablet=1
        self.assertEqual(timeline_res["devices"]["desktop"], 2)
        self.assertEqual(timeline_res["devices"]["mobile"], 2)
        self.assertEqual(timeline_res["devices"]["tablet"], 1)

        # 2. Test Campaign Detailed Analytics
        camp_res = AdEngineService.get_campaign_analytics_detailed(
            campaign_id=cmp.id,
            advertiser_id=adv.id,
            days=7,
        )
        self.assertEqual(camp_res["campaign_id"], cmp.id)
        self.assertEqual(camp_res["total_impressions"], 5)
        self.assertEqual(camp_res["total_clicks"], 2)
        self.assertEqual(len(camp_res["timeline"]), 7)

        # 3. Test Admin Global Timeline
        admin_res = AdEngineService.get_admin_network_timeline(days=14)
        self.assertEqual(admin_res["days"], 14)
        self.assertGreaterEqual(admin_res["total_network_impressions"], 5)
        self.assertGreaterEqual(admin_res["total_network_clicks"], 2)
        self.assertGreaterEqual(admin_res["total_network_revenue"], 1.00)

    def test_13_ab_testing_variant_rotation_and_bandit_optimization(self):
        """Test 13: A/B testing copy variants, impression/click metrics, and Multi-Armed Bandit CTR optimization."""
        user_id = "user_ab_test_13"
        tenant_id = "tenant_ab_test_13"
        adv = Advertiser.create(
            id="adv_ab_13",
            tenant_id=tenant_id,
            user_id=user_id,
            company_name="AB Test Corp",
            balance=300.0,
            status="active",
            create_time=current_timestamp(),
        )

        cmp = AdCampaign.create(
            id="cmp_ab_13",
            advertiser_id=adv.id,
            name="SaaS Analytics AB",
            product_name="PulseMetrics",
            advertisement_text="Default Copy: Monitor your metrics.",
            landing_url="https://pulse.example.com",
            target_categories=["analytics"],
            keywords=["metrics", "analytics", "dashboard", "дашборд", "метрик"],
            pricing_model="cpc",
            bid_amount=0.40,
            status="active",
            moderation_status="approved",
            create_time=current_timestamp(),
        )

        # 1. Create 2 Variants for A/B Testing
        var_a = AdVariantService.create_variant(
            campaign_id=cmp.id,
            advertiser_id=adv.id,
            data={
                "name": "Вариант A (Прямой оффер)",
                "advertisement_text": "Оффер A: Увеличьте конверсию на 40% с PulseMetrics.",
                "landing_url": "https://pulse.example.com/offer-a",
                "weight": 1.0,
                "is_active": True,
            },
        )
        self.assertTrue(var_a["id"])
        self.assertEqual(var_a["name"], "Вариант A (Прямой оффер)")

        var_b = AdVariantService.create_variant(
            campaign_id=cmp.id,
            advertiser_id=adv.id,
            data={
                "name": "Вариант B (Скидка 20%)",
                "advertisement_text": "Оффер B: Получите скидку 20% на PulseMetrics.",
                "landing_url": "https://pulse.example.com/offer-b",
                "weight": 1.0,
                "is_active": True,
            },
        )
        self.assertTrue(var_b["id"])

        # 2. List variants
        variants = AdVariantService.list_variants(campaign_id=cmp.id, advertiser_id=adv.id)
        self.assertEqual(len(variants), 2)

        # 3. Match query and verify variant selection
        match = AdEngineService.match_campaign_for_query(
            user_query="какой лучший дашборд для метрик бизнеса?",
            user_id="user_query_13",
            tenant_id="free_tenant_ab",
            detected_lang="ru",
            model_name="gpt-4o",
        )
        self.assertIsNotNone(match)
        self.assertIn(match["variant_id"], [var_a["id"], var_b["id"]])
        self.assertIn("PulseMetrics", match["advertisement_text"])
        self.assertIn(match["variant_id"], match["tracking_url"])

        # Check that the chosen variant incremented impressions
        v_chosen = AdVariant.get_by_id(match["variant_id"])
        self.assertGreaterEqual(v_chosen.impressions, 1)

        # 4. Click tracking on the chosen variant
        token = match["tracking_url"].replace("/v1/ads/r/", "")
        dest_url = AdEngineService.track_click(click_token=token, user_id="user_query_13")
        self.assertIn(dest_url, ["https://pulse.example.com/offer-a", "https://pulse.example.com/offer-b"])

        # Verify click recorded on variant
        v_clicked = AdVariant.get_by_id(match["variant_id"])
        self.assertGreaterEqual(v_clicked.clicks, 1)
        self.assertGreater(v_clicked.clicks / v_clicked.impressions, 0.0)

        # 5. Multi-Armed Bandit CTR optimization test:
        # Give Variant B very high CTR (10 clicks out of 10 impressions = 100%)
        # Give Variant A low CTR (1 click out of 10 impressions = 10%)
        var_a_obj = AdVariant.get_by_id(var_a["id"])
        var_a_obj.impressions = 10
        var_a_obj.clicks = 1
        var_a_obj.save()

        var_b_obj = AdVariant.get_by_id(var_b["id"])
        var_b_obj.impressions = 10
        var_b_obj.clicks = 10
        var_b_obj.save()

        # Run 50 selections: Bandit should exploit Variant B (highest CTR) for majority of selections
        b_count = 0
        for _ in range(50):
            sel_var, _, _ = AdVariantService.select_variant_for_impression(cmp)
            if sel_var and sel_var.id == var_b["id"]:
                b_count += 1

        # With 80% exploitation + random share in exploration, Variant B should win >= 35 times out of 50 (>= 70%)
        self.assertGreaterEqual(b_count, 35, f"Variant B should be exploited by bandit (won {b_count}/50)")

        # 6. Test Variant toggle and deletion
        toggle_res = AdVariantService.toggle_variant(var_a["id"], adv.id)
        self.assertFalse(toggle_res["is_active"])

        del_res = AdVariantService.delete_variant(var_a["id"], adv.id)
        self.assertTrue(del_res)
        self.assertEqual(len(AdVariantService.list_variants(cmp.id, adv.id)), 1)

    def test_14_auto_recurring_subscription_and_renewal_engine(self):
        """Test 14: Card tokenization, automatic subscription renewal, cancellation, and retry downgrade."""
        user_id = "user_rec_14"
        tenant_id = "tenant_rec_14"

        tenant = Tenant.create(
            id=tenant_id,
            name="Recurring Test Org",
            llm_id="",
            embd_id="",
            asr_id="",
            img2txt_id="",
            rerank_id="",
            parser_ids="",
            credit=0,
            plan_type="free",
            create_time=current_timestamp(),
        )

        # 1. Save Card Payment Method
        card = SavedPaymentMethodService.save_card(
            user_id=user_id,
            tenant_id=tenant_id,
            card_pan_masked="8600 06** **** 5555",
            card_expiry="08/29",
            card_token="tok_uzcard_test_14",
            card_type="uzcard",
            set_default=True,
        )
        self.assertTrue(card.id)
        self.assertEqual(card.card_pan_masked, "8600 06** **** 5555")

        cards = SavedPaymentMethodService.list_user_cards(user_id=user_id)
        self.assertEqual(len(cards), 1)

        # 2. Activate Plus Subscription with auto_renew=True
        sub = RecurringSubscriptionService.create_or_activate_subscription(
            user_id=user_id,
            tenant_id=tenant_id,
            plan_id="plus",
            payment_method_id=card.id,
            price_usd=9.99,
            auto_renew=True,
        )
        self.assertEqual(sub.plan_id, "plus")
        self.assertEqual(sub.status, "active")
        self.assertTrue(sub.auto_renew)
        self.assertEqual(sub.price_usd, 9.99)
        self.assertIsNotNone(sub.next_billing_time)

        # Check tenant plan updated
        t_ref = Tenant.get_by_id(tenant_id)
        self.assertEqual(t_ref.plan_type, "plus")

        # 3. Get Subscription API response
        sub_info = RecurringSubscriptionService.get_user_subscription(user_id=user_id, tenant_id=tenant_id)
        self.assertEqual(sub_info["plan_id"], "plus")
        self.assertEqual(sub_info["status"], "active")
        self.assertIsNotNone(sub_info["card"])
        self.assertEqual(sub_info["card"]["card_pan_masked"], "8600 06** **** 5555")

        # 4. Test Cancellation (Grace Period until period end)
        cancel_res = RecurringSubscriptionService.cancel_subscription(user_id=user_id, tenant_id=tenant_id, cancel_immediately=False)
        self.assertTrue(cancel_res["success"])
        self.assertTrue(cancel_res["cancel_at_period_end"])

        sub_canceled = UserSubscription.get_by_id(sub.id)
        self.assertFalse(sub_canceled.auto_renew)
        self.assertIsNone(sub_canceled.next_billing_time)

        # 5. Test Resume Subscription
        resume_res = RecurringSubscriptionService.resume_subscription(user_id=user_id, tenant_id=tenant_id)
        self.assertTrue(resume_res["success"])
        self.assertTrue(resume_res["auto_renew"])

        sub_resumed = UserSubscription.get_by_id(sub.id)
        self.assertTrue(sub_resumed.auto_renew)
        self.assertIsNotNone(sub_resumed.next_billing_time)

        # 6. Test Automated Renewal Worker Execution
        # Set next_billing_time in past to simulate due renewal
        now_ts = current_timestamp()
        sub_resumed.next_billing_time = now_ts - 5000
        sub_resumed.save()

        renewal_report = RecurringSubscriptionService.process_subscription_renewals()
        self.assertGreaterEqual(renewal_report["processed"], 1)
        self.assertGreaterEqual(renewal_report["renewed"], 1)

        # Verify subscription was extended by 30 days
        sub_after = UserSubscription.get_by_id(sub.id)
        self.assertGreater(sub_after.current_period_end, now_ts)
        self.assertEqual(sub_after.retry_count, 0)
        self.assertEqual(sub_after.status, "active")

        # 7. Test Payment Failure Retries & Downgrade on Repeated Failure
        # Mark card as deleted
        SavedPaymentMethodService.delete_card(card.id, user_id=user_id)

        # Force due renewal with no valid card
        sub_after.next_billing_time = now_ts - 5000
        sub_after.retry_count = 2  # Already failed twice
        sub_after.save()

        fail_report = RecurringSubscriptionService.process_subscription_renewals()
        self.assertGreaterEqual(fail_report["failed"], 1)

        sub_failed = UserSubscription.get_by_id(sub.id)
        self.assertEqual(sub_failed.status, "past_due")
        self.assertEqual(sub_failed.retry_count, 3)

        # Verify tenant was automatically downgraded to free
        t_downgraded = Tenant.get_by_id(tenant_id)
        self.assertEqual(t_downgraded.plan_type, "free")

    def test_15_geo_ip_targeting_and_regional_auction_matching(self):
        """Test 15: Geo IP targeting, regional auction matching and telemetry breakdown."""
        from api.db.services.ad_engine_service import GeoIPService

        # 1. Test GeoIPService
        regions = GeoIPService.list_supported_regions()
        self.assertGreaterEqual(len(regions), 10)
        self.assertTrue(any(r["id"] == "tashkent" for r in regions))
        self.assertTrue(any(r["id"] == "samarkand" for r in regions))

        # Resolution by header and IP
        loc_header = GeoIPService.resolve_location(headers={"x-region-code": "samarkand", "x-city": "Samarkand"})
        self.assertEqual(loc_header["region"], "samarkand")
        self.assertEqual(loc_header["city"], "Samarkand")

        loc_local = GeoIPService.resolve_location(ip="127.0.0.1")
        self.assertEqual(loc_local["region"], "tashkent")

        # 2. Setup Advertiser and Campaigns with Region Constraints
        adv = Advertiser.create(
            id="adv_geo_15",
            tenant_id="tenant_geo_15",
            user_id="user_geo_15",
            company_name="Geo Logistics Samarkand",
            balance=50.0,
            status="active",
            create_time=current_timestamp(),
        )

        cmp_samarkand = AdCampaign.create(
            id="cmp_geo_samarkand",
            advertiser_id=adv.id,
            name="Samarkand Delivery",
            product_name="Samarkand Express",
            advertisement_text="Fast express delivery in Samarkand!",
            landing_url="https://samarkand.example.com",
            keywords=["delivery", "express", "courier"],
            target_regions=["samarkand"],
            daily_budget=20.0,
            total_budget=100.0,
            bid_amount=0.50,
            pricing_model="cpc",
            priority=5,
            status="active",
            moderation_status="approved",
            create_time=current_timestamp(),
        )

        cmp_tashkent = AdCampaign.create(
            id="cmp_geo_tashkent",
            advertiser_id=adv.id,
            name="Tashkent Delivery",
            product_name="Tashkent Express",
            advertisement_text="Fast express delivery in Tashkent City!",
            landing_url="https://tashkent.example.com",
            keywords=["delivery", "express", "courier"],
            target_regions=["tashkent"],
            daily_budget=20.0,
            total_budget=100.0,
            bid_amount=0.50,
            pricing_model="cpc",
            priority=5,
            status="active",
            moderation_status="approved",
            create_time=current_timestamp(),
        )

        cmp_all = AdCampaign.create(
            id="cmp_geo_all",
            advertiser_id=adv.id,
            name="National Delivery",
            product_name="Uzbekistan Post",
            advertisement_text="Delivery across all regions of Uzbekistan!",
            landing_url="https://alluz.example.com",
            keywords=["delivery", "express", "courier"],
            target_regions=["all"],
            daily_budget=20.0,
            total_budget=100.0,
            bid_amount=0.20,
            pricing_model="cpc",
            priority=1,
            status="active",
            moderation_status="approved",
            create_time=current_timestamp(),
        )

        # 3. Test Regional Auction Isolation
        # Case A: User from Samarkand searches for delivery -> Should match cmp_samarkand (higher bid than cmp_all)
        match_samarkand = AdEngineService.match_campaign_for_query(
            tenant_id="tenant_geo_15",
            user_id="user_sam_1",
            user_query="Need express delivery courier",
            user_region="samarkand",
        )
        self.assertIsNotNone(match_samarkand)
        self.assertEqual(match_samarkand["campaign_id"], cmp_samarkand.id)

        # Case B: User from Tashkent searches for delivery -> Should match cmp_tashkent
        match_tashkent = AdEngineService.match_campaign_for_query(
            tenant_id="tenant_geo_15",
            user_id="user_tsh_1",
            user_query="Need express delivery courier",
            user_region="tashkent",
        )
        self.assertIsNotNone(match_tashkent)
        self.assertEqual(match_tashkent["campaign_id"], cmp_tashkent.id)

        # Case C: User from Bukhara searches for delivery -> cmp_samarkand & cmp_tashkent are filtered out, cmp_all wins
        match_bukhara = AdEngineService.match_campaign_for_query(
            tenant_id="tenant_geo_15",
            user_id="user_bkh_1",
            user_query="Need express delivery courier",
            user_region="bukhara",
        )
        self.assertIsNotNone(match_bukhara)
        self.assertEqual(match_bukhara["campaign_id"], cmp_all.id)

        # 4. Verify Impression Recorded Geo Location
        imp_sam = AdImpression.get_or_none(AdImpression.campaign_id == cmp_samarkand.id)
        self.assertIsNotNone(imp_sam)
        self.assertEqual(imp_sam.region, "samarkand")
        self.assertEqual(imp_sam.country, "UZ")

        # 5. Verify Click Tracking Propagates Geo Telemetry
        click_token = f"{cmp_samarkand.id}_{imp_sam.id}_user_sam_1"
        dest = AdEngineService.track_click(click_token=click_token, user_id="user_sam_1")
        self.assertEqual(dest, "https://samarkand.example.com")

        clk = AdClick.get_or_none(AdClick.impression_id == imp_sam.id)
        self.assertIsNotNone(clk)
        self.assertEqual(clk.region, "samarkand")
        self.assertEqual(clk.country, "UZ")

        # 6. Verify Timeline Analytics Regional Breakdown
        timeline = AdEngineService.get_advertiser_timeline_analytics(user_id="user_geo_15", tenant_id="tenant_geo_15", days=7)
        self.assertIn("regions", timeline)
        self.assertGreaterEqual(timeline["regions"].get("samarkand", 0), 1)

        admin_timeline = AdEngineService.get_admin_network_timeline(days=7)
        self.assertIn("regions", admin_timeline)
        self.assertGreaterEqual(admin_timeline["regions"].get("samarkand", 0), 1)

    def test_16_cpa_conversions_smart_bidding_and_pixel_engine(self):
        """
        Phase 14 Test:
        - Verify Advertiser Pixel ID generation & JS snippet creation
        - Verify Smart Auto-Bidding formula in match_campaign_for_query (eCPC = Target CPA * CVR)
        - Record impression and click
        - Record conversion with order ID and value
        - Verify CPA fee deduction from balance upon conversion
        - Verify campaign CVR & total_conversion_value metrics update
        - Verify duplicate conversion protection
        """
        adv = AdvertiserService.get_or_create_for_user(user_id="user_cpa_16", tenant_id="tenant_cpa_16")
        adv.balance = 100.0
        adv.save()

        # 1. Verify Pixel ID & Snippet
        pixel_id = ConversionTrackingService.get_or_create_pixel_id(adv.id)
        self.assertTrue(pixel_id.startswith("px_"))

        snippet_data = ConversionTrackingService.generate_pixel_snippet(pixel_id=pixel_id, host="https://swipies.app")
        self.assertIn(pixel_id, snippet_data["snippet"])
        self.assertIn("swipiesTrack", snippet_data["snippet"])

        # 2. Create CPA Campaign with Target CPA $4.00 and 5% initial CVR
        cmp_cpa = AdCampaign.create(
            id="cmp_cpa_16",
            advertiser_id=adv.id,
            name="NordVPN Security Offer",
            product_name="NordVPN High Speed",
            description="Ultra secure private browsing with fast encryption",
            advertisement_text="Get NordVPN with 70% off - Secure your AI workflows",
            landing_url="https://nordvpn.example.com/ai-offer",
            target_categories=["security", "software"],
            keywords=["vpn", "security", "privacy"],
            pricing_model="cpa",
            bid_amount=0.20,
            target_cpa=4.00,
            conversions_count=1,
            conversion_rate=5.0,  # 5.0% CVR -> eCPC = 4.00 * 0.05 = 0.20
            total_conversion_value=49.99,
            daily_budget=20.0,
            total_budget=200.0,
            spent_today=0.0,
            total_spent=0.0,
            status="active",
            moderation_status="approved",
            create_time=current_timestamp(),
            update_time=current_timestamp(),
        )

        # 3. Match CPA Campaign in Auction
        match = AdEngineService.match_campaign_for_query(
            tenant_id="tenant_cpa_16",
            user_id="user_buyer_16",
            user_query="I need the best vpn security tool for my laptop",
        )
        self.assertIsNotNone(match)
        self.assertEqual(match["campaign_id"], cmp_cpa.id)
        self.assertEqual(match["pricing_model"], "cpa")

        # 4. Record Click
        click_token = f"{cmp_cpa.id}_{match['impression_id']}_user_buyer_16"
        dest_url = AdEngineService.track_click(click_token=click_token, user_id="user_buyer_16")
        self.assertEqual(dest_url, "https://nordvpn.example.com/ai-offer")

        # Verify Click was recorded
        clk = AdClick.get_or_none(AdClick.impression_id == match["impression_id"])
        self.assertIsNotNone(clk)

        # Advertiser balance should NOT be charged yet on impression or click for CPA pricing
        adv_fresh = Advertiser.get_by_id(adv.id)
        self.assertEqual(adv_fresh.balance, 100.0)

        # 5. Record Conversion Event from Advertiser Pixel
        conv_res = ConversionTrackingService.record_conversion(
            pixel_id=pixel_id,
            event="purchase",
            value=79.99,
            currency="USD",
            order_id="ORD-NORD-8812",
            click_token=click_token,
            ip="185.139.137.10",
            user_id="user_buyer_16",
        )
        self.assertTrue(conv_res["success"])
        self.assertEqual(conv_res["cost"], 4.00)

        # 6. Verify Database State
        conv_record = AdConversion.get_or_none(AdConversion.order_id == "ORD-NORD-8812")
        self.assertIsNotNone(conv_record)
        self.assertEqual(conv_record.campaign_id, cmp_cpa.id)
        self.assertEqual(conv_record.conversion_value, 79.99)
        self.assertEqual(conv_record.cost, 4.00)
        self.assertEqual(conv_record.status, "confirmed")

        # Verify CPA Fee was billed to advertiser
        adv_billed = Advertiser.get_by_id(adv.id)
        self.assertEqual(adv_billed.balance, 96.00)

        # Verify Campaign Metrics Updated
        cmp_updated = AdCampaign.get_by_id(cmp_cpa.id)
        self.assertEqual(cmp_updated.conversions_count, 2)
        self.assertAlmostEqual(cmp_updated.total_conversion_value, 129.98, places=2)
        self.assertEqual(cmp_updated.total_spent, 4.00)

        # 7. Verify Duplicate Conversion Protection
        dup_res = ConversionTrackingService.record_conversion(
            pixel_id=pixel_id,
            event="purchase",
            value=79.99,
            currency="USD",
            order_id="ORD-NORD-8812",
            click_token=click_token,
        )
        self.assertTrue(dup_res["success"])
        self.assertTrue(dup_res.get("duplicate"))

        # Balance remains 96.00 (not charged twice)
        adv_dup = Advertiser.get_by_id(adv.id)
        self.assertEqual(adv_dup.balance, 96.00)

    def test_17_ai_campaign_insights_and_auto_optimizer(self):
        """
        Phase 15 Test:
        - Create a sub-optimal campaign (low CTR, no negative keywords, few keywords, no A/B variants)
        - Generate campaign & advertiser level insights
        - Verify identified improvement opportunities
        - Apply negative keywords insight via 1-click
        - Apply keyword expansion insight via 1-click
        - Apply A/B testing bandit variant creation via 1-click
        - Apply ad copy refresh via 1-click
        - Verify database state updates correctly
        - Verify optimizer score recalculates
        """
        adv = AdvertiserService.get_or_create_for_user(user_id="user_opt_17", tenant_id="tenant_opt_17")
        adv.balance = 50.0
        adv.save()

        cmp = AdCampaign.create(
            id="cmp_opt_17",
            advertiser_id=adv.id,
            name="Cloud Storage Pro",
            product_name="CloudStorage",
            description="Online cloud file backup storage",
            advertisement_text="Store files safely on the cloud",
            landing_url="https://cloud.example.com",
            target_categories=["cloud"],
            keywords=["cloud", "storage"],
            negative_keywords=[],  # Empty -> triggers negative_keywords insight
            pricing_model="cpc",
            bid_amount=0.15,
            daily_budget=10.0,
            total_budget=100.0,
            spent_today=0.0,
            total_spent=0.0,
            status="active",
            moderation_status="approved",
            create_time=current_timestamp(),
            update_time=current_timestamp(),
        )

        # Simulate 25 impressions and 0 clicks (CTR = 0.0% -> triggers ad_copy_refresh insight)
        for i in range(25):
            AdImpression.create(
                id=uuid.uuid4().hex[:32],
                campaign_id=cmp.id,
                advertiser_id=adv.id,
                user_id="u_test",
                query_intent="cloud storage online",
                cost=0.0,
                create_time=current_timestamp(),
            )

        # 1. Generate Campaign Insights
        insights = AdOptimizerService.generate_campaign_insights(cmp.id)
        insight_types = [ins["type"] for ins in insights]

        self.assertIn("ad_copy_refresh", insight_types)
        self.assertIn("keyword_expansion", insight_types)
        self.assertIn("negative_keywords", insight_types)
        self.assertIn("ab_test_recommendation", insight_types)

        # 2. Generate Advertiser Score
        adv_insights = AdOptimizerService.generate_advertiser_insights(adv.id)
        self.assertGreaterEqual(adv_insights["total_insights"], 4)
        self.assertLess(adv_insights["score"], 100)

        # 3. Apply Negative Keywords Insight
        neg_ins = next(ins for ins in insights if ins["type"] == "negative_keywords")
        res_neg = AdOptimizerService.apply_insight(
            campaign_id=cmp.id,
            advertiser_id=adv.id,
            insight_type="negative_keywords",
            action_payload=neg_ins["action_payload"],
        )
        self.assertTrue(res_neg["success"])

        # Verify negative keywords applied to campaign
        cmp_refreshed = AdCampaign.get_by_id(cmp.id)
        self.assertGreaterEqual(len(cmp_refreshed.negative_keywords or []), 2)
        self.assertIn("бесплатно", cmp_refreshed.negative_keywords)

        # 4. Apply Keyword Expansion Insight
        kw_ins = next(ins for ins in insights if ins["type"] == "keyword_expansion")
        res_kw = AdOptimizerService.apply_insight(
            campaign_id=cmp.id,
            advertiser_id=adv.id,
            insight_type="keyword_expansion",
            action_payload=kw_ins["action_payload"],
        )
        self.assertTrue(res_kw["success"])

        cmp_refreshed = AdCampaign.get_by_id(cmp.id)
        self.assertGreaterEqual(len(cmp_refreshed.keywords or []), 4)

        # 5. Apply A/B Test Variant Creation Insight
        ab_ins = next(ins for ins in insights if ins["type"] == "ab_test_recommendation")
        res_ab = AdOptimizerService.apply_insight(
            campaign_id=cmp.id,
            advertiser_id=adv.id,
            insight_type="ab_test_recommendation",
            action_payload=ab_ins["action_payload"],
        )
        self.assertTrue(res_ab["success"])

        # Verify variant was created in database
        variants = AdVariant.select().where(AdVariant.campaign_id == cmp.id)
        self.assertGreaterEqual(variants.count(), 1)

        # 6. Apply Ad Copy Refresh Insight
        copy_ins = next(ins for ins in insights if ins["type"] == "ad_copy_refresh")
        res_copy = AdOptimizerService.apply_insight(
            campaign_id=cmp.id,
            advertiser_id=adv.id,
            insight_type="ad_copy_refresh",
            action_payload=copy_ins["action_payload"],
        )
        self.assertTrue(res_copy["success"])

        cmp_refreshed = AdCampaign.get_by_id(cmp.id)
        self.assertIn("Спецпредложение", cmp_refreshed.advertisement_text)

    def test_18_export_reports_and_analytics_generation(self):
        """
        Phase 16 Test:
        - Verify CSV campaigns export formatting & header contents
        - Verify CSV transactions export formatting & header contents
        - Verify CSV timeline analytics export
        - Verify executive printable HTML report generation
        """
        adv = AdvertiserService.get_or_create_for_user(user_id="user_exp_18", tenant_id="tenant_exp_18")
        adv.company_name = "Global Logistics Ltd"
        adv.save()

        cmp = AdCampaign.create(
            id="cmp_exp_18",
            advertiser_id=adv.id,
            name="Air Cargo Express",
            product_name="AirCargo",
            description="Fast cargo delivery across CIS",
            advertisement_text="Reliable air freight services",
            landing_url="https://cargo.example.com",
            target_categories=["logistics"],
            keywords=["cargo", "freight", "delivery"],
            negative_keywords=["free"],
            pricing_model="cpc",
            bid_amount=0.25,
            daily_budget=20.0,
            total_budget=200.0,
            spent_today=15.0,
            total_spent=145.50,
            status="active",
            moderation_status="approved",
            create_time=current_timestamp(),
            update_time=current_timestamp(),
        )

        AdTransaction.create(
            id="tx_exp_18_1",
            advertiser_id=adv.id,
            amount=200.0,
            type="deposit",
            description="Bank card deposit",
            reference_id="ref_18",
            create_time=current_timestamp(),
        )

        # 1. Test Campaigns CSV Export
        campaigns_csv = AdExportService.export_campaigns_csv(advertiser_id=adv.id)
        self.assertIn("Campaign ID,Campaign Name,Product Name", campaigns_csv)
        self.assertIn("Air Cargo Express", campaigns_csv)
        self.assertIn("0.25", campaigns_csv)

        # 2. Test Transactions CSV Export
        tx_csv = AdExportService.export_transactions_csv(advertiser_id=adv.id)
        self.assertIn("Transaction ID,Date (UTC),Type,Amount ($)", tx_csv)
        self.assertIn("Bank card deposit", tx_csv)
        self.assertIn("200.0", tx_csv)

        # 3. Test Timeline Analytics CSV Export
        timeline_csv = AdExportService.export_analytics_timeline_csv(
            user_id="user_exp_18", tenant_id="tenant_exp_18", days=7
        )
        self.assertIn("Date,Impressions,Clicks,CTR (%),Spend / Revenue ($)", timeline_csv)

        # 4. Test Executive HTML Report Generation
        html_report = AdExportService.generate_executive_html_report(advertiser_id=adv.id, days=30)
        self.assertIn("Executive Report", html_report)
        self.assertIn("Global Logistics Ltd", html_report)
        self.assertIn("Air Cargo Express", html_report)
        self.assertIn("$145.50", html_report)
        self.assertIn("window.print()", html_report)


if __name__ == "__main__":
    unittest.main()



