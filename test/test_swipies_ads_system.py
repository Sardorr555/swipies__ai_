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
    PromoCode,
    PromoCodeUsage,
    User,
    Tenant,
    SubscriptionPlan,
    UserOnboarding,
    PaymentOrder,
    SavedPaymentMethod,
    UserSubscription,
    AdPublisher,
    AdPlacement,
    AdPublisherPayout,
    AdFraudLog,
    AdIpBlacklist,
    AdBiddingLog,
    AdDcoLog,
    AdAutomatedRule,
    AdRuleExecutionLog,
    AdJourneyTouchpoint,
    AdConversionAttribution,
    AdAudienceLookalike,
    AdCustomerLtvProfile,
    AdProductFeed,
    AdProductItem,
    AdCreativeMatrixAsset,
    AdAgencyWorkspace,
    AdAgencyClient,
    AdAgencyMember,
    AdAgencyReportTemplate,
)
from api.db.services.ad_engine_service import (
    AdvertiserService,
    AdvertiserTeamService,
    AdvertiserNotificationService,
    AdAudienceService,
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
    AdPublisherService,
    AdAntiFraudService,
    AdSmartBiddingService,
    AdDcoEngineService,
    AdBudgetPacingService,
    AdAutomatedRulesService,
    AdMultiTouchAttributionService,
    AdLookalikeLtvService,
    AdProductFeedService,
    AdCreativeStudioService,
    AdAgencyService,
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
            PromoCode,
            PromoCodeUsage,
            User,
            Tenant,
            SubscriptionPlan,
            UserOnboarding,
            PaymentOrder,
            SavedPaymentMethod,
            UserSubscription,
            AdPublisher,
            AdPlacement,
            AdPublisherPayout,
            AdFraudLog,
            AdIpBlacklist,
            AdBiddingLog,
            AdDcoLog,
            AdAutomatedRule,
            AdRuleExecutionLog,
            AdJourneyTouchpoint,
            AdConversionAttribution,
            AdAudienceLookalike,
            AdCustomerLtvProfile,
            AdProductFeed,
            AdProductItem,
            AdCreativeMatrixAsset,
            AdAgencyWorkspace,
            AdAgencyClient,
            AdAgencyMember,
            AdAgencyReportTemplate,
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
            daily_token_limit=300000,
            monthly_token_limit=6000000,
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
            PromoCode,
            PromoCodeUsage,
            User,
            Tenant,
            SubscriptionPlan,
            UserOnboarding,
            PaymentOrder,
            SavedPaymentMethod,
            UserSubscription,
            AdPublisher,
            AdPlacement,
            AdPublisherPayout,
            AdFraudLog,
            AdIpBlacklist,
            AdBiddingLog,
            AdDcoLog,
            AdAutomatedRule,
            AdRuleExecutionLog,
            AdJourneyTouchpoint,
            AdConversionAttribution,
            AdAudienceLookalike,
            AdCustomerLtvProfile,
            AdProductFeed,
            AdProductItem,
            AdCreativeMatrixAsset,
            AdAgencyWorkspace,
            AdAgencyClient,
            AdAgencyMember,
            AdAgencyReportTemplate,
        ])
        test_db.close()
        if os.path.exists(TEST_DB_FILE):
            try:
                os.remove(TEST_DB_FILE)
            except Exception:
                pass

    def setUp(self):
        AdFraudLog.delete().execute()
        AdIpBlacklist.delete().execute()
        AdPublisherPayout.delete().execute()
        AdPlacement.delete().execute()
        AdPublisher.delete().execute()
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

    def test_19_advertiser_team_collaboration_and_role_permissions(self):
        """
        Phase 17 Test:
        - Invite team members with various roles (manager, analyst, billing, admin)
        - Validate granular permissions matrix for each role
        - Update member role and verify updated permission access
        - Remove member and verify revoked access
        """
        owner = User.create(id="user_owner_19", email="owner@agency.com", nickname="Owner", create_time=current_timestamp())
        marketer_user = User.create(id="user_marketer_19", email="marketer@agency.com", nickname="Marketer", create_time=current_timestamp())
        analyst_user = User.create(id="user_analyst_19", email="analyst@agency.com", nickname="Analyst", create_time=current_timestamp())

        adv = AdvertiserService.get_or_create_for_user(user_id=owner.id, tenant_id="tenant_team_19")
        adv.company_name = "Digital Growth Agency"
        adv.save()

        # 1. Invite team members
        m_marketer = AdvertiserTeamService.invite_member(
            advertiser_id=adv.id,
            email="marketer@agency.com",
            role="manager",
            inviter_user_id=owner.id,
        )
        self.assertEqual(m_marketer["role"], "manager")
        self.assertEqual(m_marketer["user_id"], marketer_user.id)

        m_analyst = AdvertiserTeamService.invite_member(
            advertiser_id=adv.id,
            email="analyst@agency.com",
            role="analyst",
            inviter_user_id=owner.id,
        )
        self.assertEqual(m_analyst["role"], "analyst")

        m_billing = AdvertiserTeamService.invite_member(
            advertiser_id=adv.id,
            email="finance@agency.com",
            role="billing",
            inviter_user_id=owner.id,
        )
        self.assertEqual(m_billing["role"], "billing")

        # 2. Check team listing
        members = AdvertiserTeamService.get_team_members(advertiser_id=adv.id)
        self.assertEqual(len(members), 3)

        # 3. Check Granular Permissions
        # Owner has full access
        self.assertTrue(AdvertiserTeamService.has_permission(owner.id, adv.id, "manage_campaigns"))
        self.assertTrue(AdvertiserTeamService.has_permission(owner.id, adv.id, "manage_billing"))
        self.assertTrue(AdvertiserTeamService.has_permission(owner.id, adv.id, "manage_team"))

        # Marketer has manage_campaigns, but NOT manage_billing or manage_team
        self.assertTrue(AdvertiserTeamService.has_permission(marketer_user.id, adv.id, "manage_campaigns"))
        self.assertTrue(AdvertiserTeamService.has_permission(marketer_user.id, adv.id, "view_analytics"))
        self.assertFalse(AdvertiserTeamService.has_permission(marketer_user.id, adv.id, "manage_billing"))
        self.assertFalse(AdvertiserTeamService.has_permission(marketer_user.id, adv.id, "manage_team"))

        # Analyst has view_analytics, but NOT manage_campaigns or manage_billing
        self.assertTrue(AdvertiserTeamService.has_permission(analyst_user.id, adv.id, "view_analytics"))
        self.assertFalse(AdvertiserTeamService.has_permission(analyst_user.id, adv.id, "manage_campaigns"))
        self.assertFalse(AdvertiserTeamService.has_permission(analyst_user.id, adv.id, "manage_billing"))

        # 4. Promote Marketer to Admin
        updated_m = AdvertiserTeamService.update_member_role(
            member_id=m_marketer["id"],
            advertiser_id=adv.id,
            new_role="admin",
        )
        self.assertEqual(updated_m["role"], "admin")
        self.assertTrue(AdvertiserTeamService.has_permission(marketer_user.id, adv.id, "manage_billing"))
        self.assertTrue(AdvertiserTeamService.has_permission(marketer_user.id, adv.id, "manage_team"))

        # 5. Remove member
        del_res = AdvertiserTeamService.remove_member(member_id=m_billing["id"], advertiser_id=adv.id)
        self.assertTrue(del_res)
        members_after = AdvertiserTeamService.get_team_members(advertiser_id=adv.id)
        self.assertEqual(len(members_after), 2)

    def test_20_advertiser_notifications_and_alert_channels(self):
        """
        Phase 18 Test:
        - Get and update alert settings (Telegram, Webhook, Email, threshold)
        - Create notifications with varying severity (warning, info, success)
        - Retrieve unread notification counts and feed list
        - Mark notifications as read individually and in bulk
        - Dispatch test channel alerts
        """
        user = User.create(id="user_notif_20", email="notif@corp.com", nickname="NotifUser", create_time=current_timestamp())
        adv = AdvertiserService.get_or_create_for_user(user_id=user.id, tenant_id="tenant_notif_20")

        # 1. Default settings
        settings = AdvertiserNotificationService.get_or_create_settings(advertiser_id=adv.id)
        self.assertEqual(settings["low_balance_threshold"], 10.0)
        self.assertFalse(settings["telegram_alerts_enabled"])

        # 2. Update settings
        updated_settings = AdvertiserNotificationService.update_settings(
            advertiser_id=adv.id,
            payload={
                "telegram_alerts_enabled": True,
                "telegram_chat_id": "987654321",
                "webhook_url": "https://hooks.mycorp.com/swipies-ads",
                "low_balance_threshold": 30.0,
                "notify_low_balance": True,
            }
        )
        self.assertTrue(updated_settings["telegram_alerts_enabled"])
        self.assertEqual(updated_settings["telegram_chat_id"], "987654321")
        self.assertEqual(updated_settings["low_balance_threshold"], 30.0)

        # 3. Create notifications
        n1 = AdvertiserNotificationService.create_notification(
            advertiser_id=adv.id,
            type="low_balance",
            title="Низкий баланс рекламодателя",
            message="Остаток средств составляет $5.00, пополните счет во избежание остановки аукционов.",
            severity="warning",
            data={"balance": 5.0, "threshold": 30.0},
        )
        self.assertEqual(n1["severity"], "warning")
        self.assertFalse(n1["is_read"])

        n2 = AdvertiserNotificationService.create_notification(
            advertiser_id=adv.id,
            type="budget_reached",
            title="Дневной бюджет исчерпан",
            message="Кампания 'Summer Sale' израсходовала суточный лимит $100.00.",
            severity="info",
        )

        n3 = AdvertiserNotificationService.send_test_alert(advertiser_id=adv.id, channel="telegram")
        self.assertEqual(n3["severity"], "success")

        # 4. Check feed & unread count
        feed = AdvertiserNotificationService.get_notifications(advertiser_id=adv.id)
        self.assertEqual(feed["unread_count"], 3)
        self.assertEqual(len(feed["notifications"]), 3)

        # 5. Mark single notification as read
        AdvertiserNotificationService.mark_as_read(advertiser_id=adv.id, notification_id=n1["id"])
        feed_after_one = AdvertiserNotificationService.get_notifications(advertiser_id=adv.id)
        self.assertEqual(feed_after_one["unread_count"], 2)

        # 6. Mark all as read
        AdvertiserNotificationService.mark_as_read(advertiser_id=adv.id, all_unread=True)
        feed_after_all = AdvertiserNotificationService.get_notifications(advertiser_id=adv.id)
        self.assertEqual(feed_after_all["unread_count"], 0)

    def test_21_frequency_capping_and_retargeting_audiences(self):
        """Test Phase 19: Frequency Capping & Audience Retargeting Pixels."""
        adv = Advertiser.create(
            id=uuid.uuid4().hex[:32],
            user_id="user_freq_adv",
            tenant_id="tenant_freq_adv",
            company_name="Retargeting Corp",
            balance=100.0,
            status="active",
            create_time=current_timestamp(),
            update_time=current_timestamp(),
        )

        # 1. Create Audience Segments
        seg_buyers = AdAudienceService.create_segment(
            advertiser_id=adv.id,
            name="Recent Purchasers",
            description="Users who completed purchase",
            rule_type="pixel_event",
            rule_config={"event_type": "purchase"},
        )
        self.assertEqual(seg_buyers["name"], "Recent Purchasers")
        self.assertEqual(seg_buyers["member_count"], 0)

        seg_leads = AdAudienceService.create_segment(
            advertiser_id=adv.id,
            name="Warm Leads",
            description="Users who registered or left lead",
            rule_type="pixel_event",
            rule_config={"event_type": "lead"},
        )

        # 2. Add manual member to buyers segment
        m1 = AdAudienceService.add_member(
            segment_id=seg_buyers["id"],
            user_id="buyer_user_1",
            source_event="manual",
        )
        self.assertEqual(m1["user_id"], "buyer_user_1")

        # Verify member count updated
        segs = AdAudienceService.list_segments(advertiser_id=adv.id)
        buyer_seg_db = next(s for s in segs if s["id"] == seg_buyers["id"])
        self.assertEqual(buyer_seg_db["member_count"], 1)

        # 3. Test Auto Sync Pixel Conversion to Segments
        AdAudienceService.sync_pixel_conversion_to_segments(
            advertiser_id=adv.id,
            event_type="purchase",
            user_id="pixel_purchaser_2",
            anonymous_id="anon_ip_hash",
        )
        segs_after_sync = AdAudienceService.list_segments(advertiser_id=adv.id)
        buyer_seg_after_sync = next(s for s in segs_after_sync if s["id"] == seg_buyers["id"])
        self.assertEqual(buyer_seg_after_sync["member_count"], 2)

        # 4. Test Frequency Capping in AdEngineService
        cmp_capped = AdCampaign.create(
            id=uuid.uuid4().hex[:32],
            advertiser_id=adv.id,
            name="Frequency Capped Campaign",
            product_name="Limited Gadget",
            advertisement_text="Buy Limited Gadget!",
            landing_url="https://gadget.com",
            target_categories=["gadgets"],
            keywords=["gadget", "phone"],
            daily_budget=50.0,
            total_budget=500.0,
            bid_amount=0.5,
            pricing_model="cpc",
            frequency_cap_impressions=2,
            frequency_cap_hours=24,
            status="active",
            moderation_status="approved",
            create_time=current_timestamp(),
            update_time=current_timestamp(),
        )

        # 1st Query -> Under cap (limit is 2) -> Matches & records 1st impression
        cands_1 = AdEngineService.match_campaign_for_query(
            user_query="buy gadget now",
            user_id="freq_capped_user",
        )
        self.assertIsNotNone(cands_1)
        self.assertEqual(cands_1["campaign_id"], cmp_capped.id)

        # 2nd Query -> Under cap (limit is 2) -> Matches & records 2nd impression
        cands_2 = AdEngineService.match_campaign_for_query(
            user_query="buy gadget now",
            user_id="freq_capped_user",
        )
        self.assertIsNotNone(cands_2)
        self.assertEqual(cands_2["campaign_id"], cmp_capped.id)

        # 3rd Query -> REACHED CAP (2 impressions already recorded) -> Excluded!
        cands_3 = AdEngineService.match_campaign_for_query(
            user_query="buy gadget now",
            user_id="freq_capped_user",
        )
        self.assertIsNone(cands_3)

        # Another user without impressions should still see it
        cands_other = AdEngineService.match_campaign_for_query(
            user_query="buy gadget now",
            user_id="fresh_other_user",
        )
        self.assertIsNotNone(cands_other)
        self.assertEqual(cands_other["campaign_id"], cmp_capped.id)

        # 5. Test Audience Inclusion Targeting
        cmp_retarget = AdCampaign.create(
            id=uuid.uuid4().hex[:32],
            advertiser_id=adv.id,
            name="Buyers Only Upsell",
            product_name="Gadget VIP Warranty",
            advertisement_text="Get VIP Warranty for your gadget!",
            landing_url="https://gadget.com/vip",
            target_categories=["protection_plans"],
            keywords=["warranty"],
            daily_budget=50.0,
            total_budget=500.0,
            bid_amount=0.8,
            pricing_model="cpc",
            target_audience_segment_ids=[seg_buyers["id"]],
            status="active",
            moderation_status="approved",
            create_time=current_timestamp(),
            update_time=current_timestamp(),
        )

        # Buyer user in segment -> matches
        cands_buyer = AdEngineService.match_campaign_for_query(
            user_query="need warranty protection plan",
            user_id="buyer_user_1",
        )
        self.assertIsNotNone(cands_buyer)
        self.assertEqual(cands_buyer["campaign_id"], cmp_retarget.id)

        # Non-buyer user -> excluded from targeting
        cands_non_buyer = AdEngineService.match_campaign_for_query(
            user_query="need warranty protection plan",
            user_id="unknown_random_user",
        )
        self.assertIsNone(cands_non_buyer)

        # 6. Test Audience Exclusion Gate
        cmp_prospecting = AdCampaign.create(
            id=uuid.uuid4().hex[:32],
            advertiser_id=adv.id,
            name="New Customer Acquisition",
            product_name="New Customer Intro",
            advertisement_text="Get your first gadget with 20% off!",
            landing_url="https://gadget.com/first",
            target_categories=["coupons"],
            keywords=["promo_voucher"],
            daily_budget=50.0,
            total_budget=500.0,
            bid_amount=0.6,
            pricing_model="cpc",
            exclude_audience_segment_ids=[seg_buyers["id"]],
            status="active",
            moderation_status="approved",
            create_time=current_timestamp(),
            update_time=current_timestamp(),
        )

        # Buyer user -> EXCLUDED from new customer acquisition
        cands_buyer_prospecting = AdEngineService.match_campaign_for_query(
            user_query="obtain promo_voucher coupon",
            user_id="buyer_user_1",
        )
        self.assertIsNone(cands_buyer_prospecting)

        # Non-buyer user -> INCLUDED
        cands_new_user = AdEngineService.match_campaign_for_query(
            user_query="obtain promo_voucher coupon",
            user_id="fresh_prospect_user",
        )
        self.assertIsNotNone(cands_new_user)
        self.assertEqual(cands_new_user["campaign_id"], cmp_prospecting.id)

        # 7. Delete Segment
        del_res = AdAudienceService.delete_segment(segment_id=seg_leads["id"], advertiser_id=adv.id)
        self.assertTrue(del_res)
        segs_after_del = AdAudienceService.list_segments(advertiser_id=adv.id)
        self.assertFalse(any(s["id"] == seg_leads["id"] for s in segs_after_del))

    def test_22_publisher_monetization_and_partner_sdk(self):
        """Test 22: Publisher Monetization, Placements, Partner SDK Ad Serving, RevShare & Payouts."""
        # 1. Register / Get Publisher Account
        pub = AdPublisherService.get_or_create_publisher(
            user_id="publisher_user_01",
            tenant_id="publisher_tenant_01",
            name="Telegram Bot Developer",
        )
        self.assertIsNotNone(pub.id)
        self.assertTrue(pub.api_key.startswith("sw_pub_live_"))
        self.assertEqual(pub.balance, 0.0)
        self.assertEqual(pub.default_rev_share, 0.70)

        # Verify auto-created default placement
        placements = AdPublisherService.list_placements(publisher_id=pub.id)
        self.assertGreaterEqual(len(placements), 1)

        # 2. Key Regeneration
        old_key = pub.api_key
        new_key = AdPublisherService.regenerate_api_key(publisher_id=pub.id, user_id="publisher_user_01")
        self.assertNotEqual(old_key, new_key)
        self.assertTrue(new_key.startswith("sw_pub_live_"))

        # 3. Create Custom Placement
        plc = AdPublisherService.create_placement(
            publisher_id=pub.id,
            name="AI Assistant Bot",
            placement_type="telegram_bot",
            domain_or_bot="@ai_tashkent_bot",
            rev_share_rate=0.75,
        )
        self.assertIsNotNone(plc["id"])
        self.assertEqual(plc["placement_type"], "telegram_bot")
        self.assertEqual(plc["rev_share_rate"], 0.75)

        # 4. Create Advertiser & Campaign to participate in auction
        adv = Advertiser.create(
            id="adv_partner_sdk_test",
            tenant_id="tenant_adv_sdk",
            user_id="user_adv_sdk",
            company_name="FinTech Solutions",
            balance=100.0,
            status="active",
            create_time=current_timestamp(),
        )
        cmp = AdCampaign.create(
            id="cmp_partner_sdk_1",
            advertiser_id=adv.id,
            name="Fintech Pro Ad",
            product_name="Fintech Master",
            description="Best billing app",
            advertisement_text="Try Fintech Master for rapid invoicing!",
            landing_url="https://fintech.uz/master",
            target_categories=["finance", "accounting"],
            keywords=["invoicing", "accounting_software"],
            daily_budget=20.0,
            total_budget=200.0,
            bid_amount=0.40,
            pricing_model="cpc",
            status="active",
            moderation_status="approved",
            create_time=current_timestamp(),
            update_time=current_timestamp(),
        )

        # 5. Serve Partner Ad via SDK
        # Invalid API key
        err_res = AdPublisherService.serve_partner_ad(
            api_key="invalid_key",
            query="best accounting_software for company",
        )
        self.assertIn("error", err_res)
        self.assertFalse(err_res["matched"])

        # Valid API key & matching query
        res = AdPublisherService.serve_partner_ad(
            api_key=new_key,
            query="best accounting_software for company",
            placement_id=plc["id"],
            lang="ru",
            user_ip="185.139.137.10",
        )
        self.assertTrue(res["matched"])
        self.assertIsNotNone(res["ad"])
        self.assertEqual(res["ad"]["product"], "Fintech Master")
        self.assertTrue("tracking_url" in res["ad"])
        self.assertGreater(res["publisher_earnings"], 0)
        self.assertEqual(res["rev_share_rate"], 0.75)

        # Verify Publisher balance accrued
        pub_refreshed = AdPublisher.get_by_id(pub.id)
        self.assertEqual(pub_refreshed.balance, res["publisher_earnings"])
        self.assertEqual(pub_refreshed.total_earned, res["publisher_earnings"])

        # Verify Placement stats incremented
        plc_refreshed = AdPlacement.get_by_id(plc["id"])
        self.assertEqual(plc_refreshed.impressions, 1)
        self.assertEqual(plc_refreshed.earnings, res["publisher_earnings"])

        # 6. Payout Request
        # Test insufficient balance error
        with self.assertRaises(ValueError):
            AdPublisherService.request_payout(
                publisher_id=pub.id,
                amount=999.0,
                destination_card="8600 0000 0000 1234",
            )

        # Valid payout
        payout_amt = round(res["publisher_earnings"] / 2, 4)
        payout_res = AdPublisherService.request_payout(
            publisher_id=pub.id,
            amount=payout_amt,
            destination_card="8600 0000 0000 1234",
            destination_holder="TEST PUBLISHER",
        )
        self.assertEqual(payout_res["status"], "pending")
        self.assertEqual(payout_res["amount"], payout_amt)

        # Check balance reduced
        pub_after_payout = AdPublisher.get_by_id(pub.id)
        self.assertAlmostEqual(pub_after_payout.balance, res["publisher_earnings"] - payout_amt, places=3)
        self.assertAlmostEqual(pub_after_payout.total_withdrawn, payout_amt, places=3)

        # 7. List Payouts
        payouts_list = AdPublisherService.list_payouts(publisher_id=pub.id)
        self.assertEqual(len(payouts_list), 1)
        self.assertEqual(payouts_list[0]["id"], payout_res["id"])
        self.assertEqual(payouts_list[0]["status"], "pending")

        # 8. Delete Placement
        del_ok = AdPublisherService.delete_placement(placement_id=plc["id"], publisher_id=pub.id)
        self.assertTrue(del_ok)
        placements_after_del = AdPublisherService.list_placements(publisher_id=pub.id)
        self.assertFalse(any(p["id"] == plc["id"] for p in placements_after_del))

    def test_23_anti_fraud_and_invalid_traffic_protection(self):
        """Phase 21: Test Click Fraud Detection, Bot Filtering, IP Blacklist & Automated Fraud Protection."""
        # 1. Advertiser and Campaign Setup
        adv = Advertiser.create(
            id=uuid.uuid4().hex[:32],
            user_id="u_antifraud_test",
            tenant_id="t_antifraud_test",
            company_name="SafeAds Corp",
            balance=100.0,
            currency="USD",
            create_time=current_timestamp(),
        )

        cmp = AdCampaign.create(
            id=uuid.uuid4().hex[:32],
            advertiser_id=adv.id,
            name="Anti-Fraud Protected Campaign",
            product_name="Secure VPN Cloud",
            advertisement_text="Secure your cloud traffic.",
            landing_url="https://vpn.example.com/promo",
            target_categories=["security", "vpn"],
            keywords=["vpn", "security", "protect"],
            daily_budget=50.0,
            total_budget=500.0,
            spent_today=0.0,
            total_spent=0.0,
            pricing_model="cpc",
            bid_amount=0.50,
            priority=5,
            status="active",
            moderation_status="approved",
            create_time=current_timestamp(),
        )

        # 2. Test Bot User-Agent Detection
        self.assertTrue(AdAntiFraudService.is_bot_user_agent("python-requests/2.31.0"))
        self.assertTrue(AdAntiFraudService.is_bot_user_agent("curl/7.68.0"))
        self.assertTrue(AdAntiFraudService.is_bot_user_agent("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 HeadlessChrome/118.0"))
        self.assertTrue(AdAntiFraudService.is_bot_user_agent("Scrapy/2.11.0 (+https://scrapy.org)"))
        self.assertFalse(AdAntiFraudService.is_bot_user_agent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"))

        # 3. Test IP Blacklist Management
        bl_res = AdAntiFraudService.add_to_blacklist(
            ip_address="198.51.100.25",
            advertiser_id=adv.id,
            reason="Repeated click bot attacks",
            duration_hours=48,
        )
        self.assertTrue(bl_res["success"])
        self.assertTrue(AdAntiFraudService.is_ip_blacklisted("198.51.100.25", advertiser_id=adv.id))
        self.assertFalse(AdAntiFraudService.is_ip_blacklisted("84.54.80.1", advertiser_id=adv.id))

        bl_list = AdAntiFraudService.list_blacklist(advertiser_id=adv.id)
        self.assertEqual(len(bl_list), 1)
        self.assertEqual(bl_list[0]["ip_address"], "198.51.100.25")

        # 4. Test Legitimate Human Click (Should Be Billed)
        human_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
        url1 = AdEngineService.track_click(
            click_token=cmp.id,
            user_id="user_human_1",
            ip_hash="hash_clean_human_1",
            user_agent=human_ua,
            raw_ip="84.54.80.1",
        )
        self.assertEqual(url1, "https://vpn.example.com/promo")

        adv_refreshed = Advertiser.get_by_id(adv.id)
        self.assertEqual(adv_refreshed.balance, 99.50)  # 100.0 - 0.50
        clicks_count = AdClick.select().where(AdClick.campaign_id == cmp.id).count()
        self.assertEqual(clicks_count, 1)

        # 5. Test Bot Click (Should Be Blocked and NOT Billed)
        url_bot = AdEngineService.track_click(
            click_token=cmp.id,
            user_id="bot_user",
            ip_hash="hash_bot_crawler",
            user_agent="python-requests/2.31.0",
            raw_ip="185.220.101.5",
        )
        self.assertEqual(url_bot, "https://vpn.example.com/promo")

        adv_after_bot = Advertiser.get_by_id(adv.id)
        self.assertEqual(adv_after_bot.balance, 99.50)  # Unchanged!
        self.assertEqual(AdClick.select().where(AdClick.campaign_id == cmp.id).count(), 1)  # No new billable click!

        fraud_log_bot = AdFraudLog.get_or_none(AdFraudLog.reason == "bot_user_agent", AdFraudLog.advertiser_id == adv.id)
        self.assertIsNotNone(fraud_log_bot)
        self.assertEqual(fraud_log_bot.cost_saved, 0.50)

        # 6. Test Blacklisted IP Click (Should Be Blocked)
        url_bl = AdEngineService.track_click(
            click_token=cmp.id,
            user_id="anon_hacker",
            ip_hash="hash_blacklisted_ip",
            user_agent=human_ua,
            raw_ip="198.51.100.25",  # Blacklisted above!
        )
        self.assertEqual(url_bl, "https://vpn.example.com/promo")

        adv_after_bl = Advertiser.get_by_id(adv.id)
        self.assertEqual(adv_after_bl.balance, 99.50)  # Unchanged!

        fraud_log_bl = AdFraudLog.get_or_none(AdFraudLog.reason == "blacklist_ip", AdFraudLog.advertiser_id == adv.id)
        self.assertIsNotNone(fraud_log_bl)
        self.assertEqual(fraud_log_bl.cost_saved, 0.50)

        # 7. Test Rapid Repeat Clicks Detection (Rate Limiting)
        # Create 2 clicks from same hash
        AdClick.create(
            id=uuid.uuid4().hex[:32],
            campaign_id=cmp.id,
            advertiser_id=adv.id,
            user_id="clicker_1",
            cost=0.50,
            ip_hash="rapid_hash_target",
            language="ru",
            model_name="gpt-4o",
            device_type="desktop",
            platform="web",
            region="tashkent",
            city="Tashkent",
            country="UZ",
            create_time=current_timestamp(),
        )
        AdClick.create(
            id=uuid.uuid4().hex[:32],
            campaign_id=cmp.id,
            advertiser_id=adv.id,
            user_id="clicker_2",
            cost=0.50,
            ip_hash="rapid_hash_target",
            language="ru",
            model_name="gpt-4o",
            device_type="desktop",
            platform="web",
            region="tashkent",
            city="Tashkent",
            country="UZ",
            create_time=current_timestamp(),
        )

        # 3rd click from same ip_hash within 60s should be blocked as rapid_repeat_clicks
        url_rapid = AdEngineService.track_click(
            click_token=cmp.id,
            user_id="clicker_3",
            ip_hash="rapid_hash_target",
            user_agent=human_ua,
            raw_ip="84.54.80.200",
        )
        self.assertEqual(url_rapid, "https://vpn.example.com/promo")

        fraud_log_rapid = AdFraudLog.get_or_none(AdFraudLog.reason == "rapid_repeat_clicks", AdFraudLog.advertiser_id == adv.id)
        self.assertIsNotNone(fraud_log_rapid)

        # 8. Test Fraud Overview Summary
        overview = AdAntiFraudService.get_fraud_overview(advertiser_id=adv.id)
        self.assertGreaterEqual(overview["total_blocked_clicks"], 3)
        self.assertGreaterEqual(overview["total_cost_saved"], 1.50)
        self.assertEqual(overview["bot_detections"], 1)
        self.assertEqual(overview["blacklist_blocks"], 1)
        self.assertEqual(overview["rate_limit_blocks"], 1)
        self.assertEqual(overview["active_blacklist_count"], 1)
        self.assertGreaterEqual(len(overview["recent_logs"]), 3)

        # 9. Remove from blacklist
        rev_ok = AdAntiFraudService.remove_from_blacklist(blacklist_id=bl_res["id"], advertiser_id=adv.id)
        self.assertTrue(rev_ok)
        self.assertFalse(AdAntiFraudService.is_ip_blacklisted("198.51.100.25", advertiser_id=adv.id))

    def test_24_smart_bidding_and_dayparting_schedule(self):
        """Test Phase 22: Smart Bidding (eCPC, Target CPA, Maximize Conversions) and Dayparting Schedules."""
        adv = AdvertiserService.get_or_create_for_user(user_id="adv_smart_bid_user", tenant_id="t_smart_bid")
        adv.balance = 500.0
        adv.save()

        # 1. Test strategy catalogue
        strategies = AdSmartBiddingService.list_strategies()
        strat_ids = [s["id"] for s in strategies]
        self.assertIn("manual_cpc", strat_ids)
        self.assertIn("enhanced_cpc", strat_ids)
        self.assertIn("target_cpa", strat_ids)
        self.assertIn("maximize_conversions", strat_ids)

        # 2. Test Timezone calculation helper
        # Monday 2026-08-24 10:00:00 UTC
        fixed_utc = datetime(2026, 8, 24, 10, 0, 0, tzinfo=timezone.utc)
        local_tashkent = AdSmartBiddingService.get_local_datetime(fixed_utc, "Asia/Tashkent")
        self.assertEqual(local_tashkent.hour, 15)  # 10 + 5 = 15:00
        self.assertEqual(local_tashkent.weekday(), 0)  # Monday

        local_nyc = AdSmartBiddingService.get_local_datetime(fixed_utc, "America/New_York")
        self.assertEqual(local_nyc.hour, 5)  # 10 - 5 = 05:00

        # 3. Create Campaign with Dayparting Schedule
        cmp_schedule = AdCampaign.create(
            id="cmp_sched_test",
            advertiser_id=adv.id,
            name="Work Hours Only Campaign",
            product_name="Corporate ERP",
            advertisement_text="Best ERP for enterprise businesses",
            landing_url="https://erp.example.com",
            keywords=["erp", "business", "crm", "enterprise"],
            target_categories=["business"],
            daily_budget=50.0,
            total_budget=500.0,
            pricing_model="cpc",
            bid_amount=0.50,
            bidding_strategy="manual_cpc",
            schedule_timezone="Asia/Tashkent",
            schedule_config={
                "enabled_days": [0, 1, 2, 3, 4],  # Mon-Fri
                "active_hours_start": 9,
                "active_hours_end": 18,
                "peak_hours": [14, 15, 16],
                "peak_hours_multiplier": 1.30,
            },
            status="active",
            moderation_status="approved",
            create_time=current_timestamp(),
            update_time=current_timestamp(),
        )

        # 3.1 Monday 15:00 in Tashkent (10:00 UTC) -> Active and in peak hours!
        is_active, mult = AdSmartBiddingService.is_in_schedule(cmp_schedule, fixed_utc)
        self.assertTrue(is_active)
        self.assertAlmostEqual(mult, 1.30)

        # 3.2 Monday 22:00 in Tashkent (17:00 UTC) -> Outside active hours (9-18)
        night_utc = datetime(2026, 8, 24, 17, 0, 0, tzinfo=timezone.utc)
        is_active_night, mult_night = AdSmartBiddingService.is_in_schedule(cmp_schedule, night_utc)
        self.assertFalse(is_active_night)
        self.assertEqual(mult_night, 0.0)

        # 3.3 Sunday 15:00 in Tashkent (Sunday 10:00 UTC, 2026-08-23) -> Disabled day
        sunday_utc = datetime(2026, 8, 23, 10, 0, 0, tzinfo=timezone.utc)
        is_active_sun, mult_sun = AdSmartBiddingService.is_in_schedule(cmp_schedule, sunday_utc)
        self.assertFalse(is_active_sun)

        # 4. Test Enhanced CPC (eCPC) Intent Modifiers
        cmp_ecpc = AdCampaign.create(
            id="cmp_ecpc_test",
            advertiser_id=adv.id,
            name="Smart eCPC Campaign",
            product_name="Cloud Hosting",
            advertisement_text="High performance SSD cloud servers",
            landing_url="https://cloud.example.com",
            keywords=["cloud", "hosting", "server", "vps"],
            target_categories=["tech"],
            daily_budget=100.0,
            total_budget=1000.0,
            pricing_model="cpc",
            bid_amount=0.40,
            bidding_strategy="enhanced_cpc",
            schedule_timezone="UTC",
            schedule_config={},
            status="active",
            moderation_status="approved",
            create_time=current_timestamp(),
            update_time=current_timestamp(),
        )

        # High intent query ("купить быстрый vps cloud server") -> +30% boost -> $0.40 * 1.30 = $0.52
        bid_high = AdSmartBiddingService.calculate_smart_bid(
            campaign=cmp_ecpc,
            clean_query="хочу купить быстрый vps cloud hosting",
            now_dt=fixed_utc,
        )
        self.assertTrue(bid_high["active"])
        self.assertAlmostEqual(bid_high["dynamic_bid"], 0.52, places=2)
        self.assertEqual(bid_high["cvr_multiplier"], 1.30)
        self.assertIn("commercial intent", bid_high["reason"])

        # Low intent query ("что такое cloud vps free wiki") -> -30% reduction -> $0.40 * 0.70 = $0.28
        bid_low = AdSmartBiddingService.calculate_smart_bid(
            campaign=cmp_ecpc,
            clean_query="что такое cloud hosting wiki",
            now_dt=fixed_utc,
        )
        self.assertTrue(bid_low["active"])
        self.assertAlmostEqual(bid_low["dynamic_bid"], 0.28, places=2)
        self.assertEqual(bid_low["cvr_multiplier"], 0.70)

        # 5. Test Target CPA Auto-Bidding
        cmp_tcpa = AdCampaign.create(
            id="cmp_tcpa_test",
            advertiser_id=adv.id,
            name="Target CPA Auto-Bid Campaign",
            product_name="Accounting SaaS",
            advertisement_text="Automate your taxes and accounting",
            landing_url="https://tax.example.com",
            keywords=["accounting", "tax", "audit", "saas"],
            target_categories=["finance"],
            daily_budget=200.0,
            total_budget=2000.0,
            pricing_model="cpc",
            bid_amount=0.20,
            bidding_strategy="target_cpa",
            target_cpa=15.0,  # $15 CPA target
            conversion_rate=4.0,  # 4% historical CVR
            schedule_timezone="UTC",
            schedule_config={},
            status="active",
            moderation_status="approved",
            create_time=current_timestamp(),
            update_time=current_timestamp(),
        )

        # Target CPA Bid = $15 * 0.04 = $0.60
        bid_tcpa = AdSmartBiddingService.calculate_smart_bid(
            campaign=cmp_tcpa,
            clean_query="accounting software pricing",
            now_dt=fixed_utc,
        )
        self.assertTrue(bid_tcpa["active"])
        self.assertAlmostEqual(bid_tcpa["dynamic_bid"], 0.60, places=2)
        self.assertIn("Target CPA auto-bid", bid_tcpa["reason"])

        # 6. Test Maximize Conversions Strategy
        cmp_max_conv = AdCampaign.create(
            id="cmp_maxconv_test",
            advertiser_id=adv.id,
            name="Maximize Conversions Campaign",
            product_name="Design Tools",
            advertisement_text="UI/UX Pro Design Toolkit",
            landing_url="https://design.example.com",
            keywords=["design", "ui", "ux", "figma"],
            target_categories=["design"],
            daily_budget=100.0,
            total_budget=1000.0,
            spent_today=10.0,  # Low spend so far (< 60%) -> +25% boost
            pricing_model="cpc",
            bid_amount=0.80,
            bidding_strategy="maximize_conversions",
            schedule_timezone="UTC",
            schedule_config={},
            status="active",
            moderation_status="approved",
            create_time=current_timestamp(),
            update_time=current_timestamp(),
        )

        bid_max = AdSmartBiddingService.calculate_smart_bid(
            campaign=cmp_max_conv,
            clean_query="best design ui tool",
            now_dt=fixed_utc,
        )
        self.assertTrue(bid_max["active"])
        self.assertAlmostEqual(bid_max["dynamic_bid"], 1.00, places=2)  # $0.80 * 1.25 = $1.00
        self.assertEqual(bid_max["cvr_multiplier"], 1.25)

        # 7. Test Auction with Smart Bidding & Dayparting Gate in AdEngineService
        # 7.1 When time is Sunday (outside schedule of cmp_schedule), cmp_schedule is NOT recommended
        res_sun = AdEngineService.get_sponsored_recommendation(
            query="best enterprise corporate erp business software",
            user_id="test_user_sched",
            lang="en",
            now_dt=sunday_utc,
        )
        # Should not match cmp_schedule because Sunday is disabled
        if res_sun:
            self.assertNotEqual(res_sun["campaign_id"], cmp_schedule.id)

        # 7.2 When time is Monday 10:00 UTC (15:00 Tashkent), cmp_schedule is active and matched
        res_mon = AdEngineService.get_sponsored_recommendation(
            query="best enterprise corporate erp business software",
            user_id="test_user_sched_mon",
            lang="en",
            now_dt=fixed_utc,
        )
        self.assertIsNotNone(res_mon)
        self.assertEqual(res_mon["campaign_id"], cmp_schedule.id)

        # Verify AdBiddingLog was recorded for the auction win
        bid_log = AdBiddingLog.get_or_none(AdBiddingLog.campaign_id == cmp_schedule.id)
        self.assertIsNotNone(bid_log)
        self.assertEqual(bid_log.strategy, "manual_cpc")
        self.assertAlmostEqual(bid_log.schedule_multiplier, 1.30)

        # 8. Test Update and Get Campaign Bidding Info
        updated_info = AdSmartBiddingService.update_campaign_bidding(
            campaign_id=cmp_schedule.id,
            advertiser_id=adv.id,
            bidding_strategy="enhanced_cpc",
            target_cpa=25.0,
            schedule_timezone="Europe/Moscow",
            schedule_config={
                "enabled_days": [0, 1, 2, 3, 4, 5, 6],
                "active_hours_start": 8,
                "active_hours_end": 22,
                "hourly_multipliers": {"12": 1.40, "13": 1.40},
            },
        )
        self.assertEqual(updated_info["bidding_strategy"], "enhanced_cpc")
        self.assertEqual(updated_info["schedule_timezone"], "Europe/Moscow")
        self.assertEqual(updated_info["target_cpa"], 25.0)
        self.assertEqual(updated_info["schedule_config"]["active_hours_end"], 22)
        self.assertGreaterEqual(len(updated_info["recent_bids"]), 1)

    def test_25_dynamic_creative_optimization_and_dki(self):
        """
        Phase 23: Verify Dynamic Creative Optimization (DCO), Dynamic Keyword Insertion (DKI),
        localized region detection, UTM link construction, dynamic CTA/promo codes, tone formatting,
        and DCO decision logging.
        """
        # 1. Test Salient Keyword Extraction across RU, UZ, EN
        kw_ru = AdDcoEngineService.extract_salient_keyword("посоветуй мне лучшую CRM для продаж онлайн", default_fallback="CRM", lang="ru")
        self.assertIn("CRM", kw_ru)
        self.assertIn("продаж", kw_ru)

        kw_uz = AdDcoEngineService.extract_salient_keyword("qanday eng yaxshi kassa dasturi bor", default_fallback="Dastur", lang="uz")
        self.assertIn("Kassa dasturi", kw_uz)

        kw_en = AdDcoEngineService.extract_salient_keyword("where can i find the best accounting tool", default_fallback="Tool", lang="en")
        self.assertIn("Accounting tool", kw_en)

        kw_empty = AdDcoEngineService.extract_salient_keyword("как где что", default_fallback="Сервис", lang="ru")
        self.assertEqual(kw_empty, "Сервис")

        # 2. Test Region Localization
        reg_ru = AdDcoEngineService.resolve_region_label("tashkent", "лучший сервис в Ташкенте", lang="ru")
        self.assertEqual(reg_ru, "в Ташкенте")

        reg_uz = AdDcoEngineService.resolve_region_label("samarkand", "samarqandda servis", lang="uz")
        self.assertEqual(reg_uz, "Samarqandda")

        reg_en = AdDcoEngineService.resolve_region_label("bukhara", "", lang="en")
        self.assertEqual(reg_en, "in Bukhara")

        # 3. Test Macro Token Substitution
        template = "Ищете {keyword:надежное решение} {city:в Узбекистане}? Скидка {discount:10%} по промокоду {promo}. Протестировано с {model:AI}!"
        rendered = AdDcoEngineService.substitute_macro_tokens(
            template_str=template,
            keyword="CRM для бизнеса",
            city="в Ташкенте",
            model_name="DeepSeek",
            lang="ru",
            day_name="Monday",
            promo_code="SWIPIES20",
            discount_percent=20.0,
        )
        self.assertEqual(
            rendered,
            "Ищете CRM для бизнеса в Ташкенте? Скидка 20% по промокоду SWIPIES20. Протестировано с DeepSeek!"
        )

        # 4. Test Dynamic URL Construction with UTM
        dynamic_url = AdDcoEngineService.build_dynamic_url(
            base_url="https://acme-crm.com/pricing?ref=banner",
            campaign_id="cmp_dco_test_1",
            inserted_keyword="CRM для бизнеса",
            model="gpt-4o",
            region="tashkent",
            lang="ru",
            utm_auto_tagging=True,
            promo_code="SWIPIES20",
        )
        self.assertIn("ref=banner", dynamic_url)
        self.assertIn("utm_source=swipies", dynamic_url)
        self.assertIn("utm_campaign=cmp_dco_test_1", dynamic_url)
        self.assertIn("promo=SWIPIES20", dynamic_url)

        # 5. Create Test Advertiser and Campaign with DCO enabled
        user = User.create(id="user_dco_test", email="dco@test.com", password="hash", nickname="dco_user")
        adv = Advertiser.create(id="adv_dco_test", user_id=user.id, tenant_id="tenant_dco_test", company_name="DCO Auto Inc", balance=150.0)

        cmp_dco = AdCampaign.create(
            id="cmp_dco_active_1",
            advertiser_id=adv.id,
            name="DCO Smart Retail Campaign",
            product_name="Retail Cloud ERP",
            description="Enterprise ERP for retailers and warehouses",
            advertisement_text="Обычный статичный текст объявления",
            landing_url="https://retail-cloud.uz/start",
            target_categories=["retail", "erp", "warehouses", "business"],
            keywords=["retail", "erp", "склад", "магазин"],
            daily_budget=50.0,
            total_budget=500.0,
            pricing_model="cpc",
            bid_amount=0.25,
            status="active",
            moderation_status="approved",
            dco_enabled=True,
            dco_config={
                "description_template": "Лучший {keyword:облачный сервис} {city:в Узбекистане}! Получите скидку {discount:15%} с промокодом {promo}.",
                "url_template": "https://retail-cloud.uz/landing?campaign={product}",
                "utm_auto_tagging": True,
                "default_keyword": "ERP для склада",
                "cta_text": "Попробовать {keyword:бесплатно}",
                "promo_code": "RETAIL-SALE-20",
                "discount_percent": 20.0,
                "tone_style": "urgent",
            },
            create_time=current_timestamp(),
            update_time=current_timestamp(),
        )

        # 6. Test DCO Copy Rendering Engine directly
        dco_res = AdDcoEngineService.render_dco_copy(
            campaign=cmp_dco,
            query="посоветуй надежный софт для управления магазином и складом в Самарканде",
            model="deepseek-v3",
            lang="ru",
            region="samarkand",
            log_decision=True,
        )
        self.assertTrue(dco_res["dco_applied"])
        self.assertIn("⚡ Спецпредложение:", dco_res["rendered_text"])
        self.assertIn("в Самарканде", dco_res["rendered_text"])
        self.assertIn("RETAIL-SALE-20", dco_res["rendered_text"])
        self.assertIn("utm_source=swipies", dco_res["rendered_url"])
        self.assertIn("utm_region=samarkand", dco_res["rendered_url"])
        self.assertEqual(dco_res["promo_code"], "RETAIL-SALE-20")

        # Verify AdDcoLog was created
        dco_log = AdDcoLog.get_or_none(AdDcoLog.campaign_id == cmp_dco.id)
        self.assertIsNotNone(dco_log)
        self.assertEqual(dco_log.applied_city, "в Самарканде")
        self.assertEqual(dco_log.applied_model, "DeepSeek")
        self.assertEqual(dco_log.applied_promo, "RETAIL-SALE-20")

        # 7. Test Integration inside AdEngineService Recommendation Pipeline
        rec = AdEngineService.get_sponsored_recommendation(
            query="как выбрать систему для управления складом в Ташкенте",
            user_id="dco_end_user_1",
            lang="ru",
            model_name="gpt-4o",
            region="tashkent",
        )
        self.assertIsNotNone(rec)
        self.assertEqual(rec["campaign_id"], cmp_dco.id)
        self.assertTrue(rec.get("dco_applied"))
        self.assertIn("в Ташкенте", rec["advertisement_text"])
        self.assertIn("utm_source=swipies", rec["landing_url"])
        self.assertEqual(rec["promo_code"], "RETAIL-SALE-20")
        self.assertEqual(rec["discount_percent"], 20.0)

        # 8. Test Live Preview API
        preview = AdDcoEngineService.preview_dco(
            campaign_id=cmp_dco.id,
            query="qanday qilib kassa va sklad tizimini ulash mumkin",
            model="claude-3-5",
            region="tashkent",
            lang="uz",
            custom_template="Siz uchun {keyword:qulay dastur} {city:Toshkentda}! {promo} kodi bilan.",
            custom_promo="UZ-SUPER-15",
            custom_tone="friendly",
        )
        self.assertIn("💡 Tavsiya qilamiz:", preview["rendered_text"])
        self.assertIn("UZ-SUPER-15", preview["rendered_text"])
        self.assertEqual(preview["applied_model"], "Claude")

        # 9. Test Campaign DCO Info Retrieval and Update
        updated_dco = AdDcoEngineService.update_campaign_dco(
            campaign_id=cmp_dco.id,
            dco_enabled=True,
            dco_config={
                "description_template": "Обновленный шаблон {keyword} {city}",
                "url_template": "https://retail-cloud.uz/v2",
                "cta_text": "Заказать демо",
                "promo_code": "PROMO-NEW",
                "discount_percent": 25.0,
                "tone_style": "professional",
            },
        )
        self.assertTrue(updated_dco["dco_enabled"])
        self.assertEqual(updated_dco["dco_config"]["promo_code"], "PROMO-NEW")
        self.assertEqual(updated_dco["dco_config"]["discount_percent"], 25.0)
        self.assertGreaterEqual(len(updated_dco["recent_logs"]), 1)

    def test_26_automated_rules_and_budget_pacing_engine(self):
        """Phase 24: Test Automated Rules (Auto-Pilot), Stop-Loss, CPA Guard, Scale Winners, and Budget Pacing."""
        now_ts = current_timestamp()
        adv = Advertiser.create(
            id="adv_rules_pilot",
            user_id="usr_rules_pilot",
            tenant_id="ten_rules_pilot",
            company_name="AutoPilot SaaS Co",
            balance=150.0,
            currency="USD",
            status="active",
            create_time=now_ts,
            update_time=now_ts,
        )

        # 1. Test Default Rule Templates
        templates = AdAutomatedRulesService.get_default_rule_templates()
        self.assertGreaterEqual(len(templates), 4)
        template_ids = [t["template_id"] for t in templates]
        self.assertIn("stop_loss_low_ctr", template_ids)
        self.assertIn("cpa_guard_reduce_bid", template_ids)
        self.assertIn("scale_winner_budget", template_ids)
        self.assertIn("budget_burn_alert", template_ids)

        # 2. Test Budget Pacing Service & Curves
        cmp_pacing = AdCampaign.create(
            id="cmp_pacing_test",
            advertiser_id=adv.id,
            name="Pacing Cloud Campaign",
            product_name="Cloud VM",
            advertisement_text="Reliable Cloud Servers",
            landing_url="https://cloud-vm.uz",
            daily_budget=20.0,
            total_budget=200.0,
            spent_today=18.0,  # 90% spent early in the day -> should overpace
            total_spent=50.0,
            pricing_model="cpc",
            bid_amount=0.20,
            pacing_mode="standard_smooth",
            schedule_timezone="Asia/Tashkent",
            status="active",
            moderation_status="approved",
            create_time=now_ts,
            update_time=now_ts,
        )

        # Simulated 04:00 AM local time (expected curve ~0.06 = $1.20, but actual spent is $18.00 = 0.90)
        sim_morning_utc = datetime(2026, 8, 25, 23, 0, 0, tzinfo=timezone.utc)
        mult_morning = AdBudgetPacingService.calculate_pacing_multiplier(cmp_pacing, now_dt=sim_morning_utc)
        self.assertLessEqual(mult_morning, 0.90)  # Throttled / dampened

        # Test Accelerated ASAP pacing mode (no throttling)
        cmp_pacing.pacing_mode = "accelerated_asap"
        cmp_pacing.save()
        mult_asap = AdBudgetPacingService.calculate_pacing_multiplier(cmp_pacing, now_dt=sim_morning_utc)
        self.assertEqual(mult_asap, 1.0)

        # Test Pacing Forecast & Mode Update
        pacing_forecast = AdBudgetPacingService.get_campaign_pacing_forecast(cmp_pacing.id)
        self.assertEqual(pacing_forecast["campaign_id"], cmp_pacing.id)
        self.assertEqual(len(pacing_forecast["hourly_forecast"]), 24)

        updated_pacing = AdBudgetPacingService.update_campaign_pacing(cmp_pacing.id, "peak_weighted")
        self.assertEqual(updated_pacing["pacing_mode"], "peak_weighted")

        # 3. Test Automated Rules CRUD & Toggling
        rule_data = {
            "campaign_id": "all",
            "name": "🛡️ Stop Loss: Low CTR Guard",
            "description": "Auto-pause poor performing campaigns",
            "metric": "ctr",
            "operator": "<",
            "threshold_value": 0.50,
            "min_impressions": 10,
            "time_window": "today",
            "action_type": "pause_campaign",
            "action_value": 0.0,
            "is_active": True,
        }
        rule_stop_loss = AdAutomatedRulesService.create_rule(adv.id, rule_data)
        self.assertIsNotNone(rule_stop_loss["id"])
        self.assertEqual(rule_stop_loss["metric"], "ctr")

        # Toggle rule
        toggled = AdAutomatedRulesService.toggle_rule(rule_stop_loss["id"], adv.id)
        self.assertFalse(toggled["is_active"])
        toggled = AdAutomatedRulesService.toggle_rule(rule_stop_loss["id"], adv.id)
        self.assertTrue(toggled["is_active"])

        # Create Scale Winner rule
        rule_scale = AdAutomatedRulesService.create_rule(adv.id, {
            "campaign_id": "all",
            "name": "🚀 Scale Top Performer",
            "metric": "cvr",
            "operator": ">",
            "threshold_value": 3.0,
            "min_impressions": 5,
            "time_window": "today",
            "action_type": "increase_budget",
            "action_value": 30.0,
            "is_active": True,
        })

        # Create CPA Guard rule
        rule_cpa = AdAutomatedRulesService.create_rule(adv.id, {
            "campaign_id": "all",
            "name": "💰 CPA Guard",
            "metric": "cpa",
            "operator": ">",
            "threshold_value": 8.0,
            "min_impressions": 5,
            "time_window": "today",
            "action_type": "decrease_bid",
            "action_value": 20.0,
            "is_active": True,
        })

        # 4. Create campaigns to test rule execution
        # Campaign A: Low CTR (100 impressions, 0 clicks -> CTR 0.0% < 0.5%) -> Stop Loss Trigger
        cmp_a = AdCampaign.create(
            id="cmp_rule_test_a",
            advertiser_id=adv.id,
            name="Low CTR Campaign A",
            product_name="Product A",
            advertisement_text="Ad text A",
            landing_url="https://site.uz/a",
            daily_budget=10.0,
            total_budget=100.0,
            spent_today=5.0,
            total_spent=5.0,
            pricing_model="cpc",
            bid_amount=0.10,
            status="active",
            moderation_status="approved",
            create_time=now_ts,
            update_time=now_ts,
        )
        for i in range(15):
            AdImpression.create(
                id=f"imp_a_{i}",
                campaign_id=cmp_a.id,
                advertiser_id=adv.id,
                user_id=f"usr_a_{i}",
                query="test query a",
                cost=0.01,
                user_language="ru",
                model="gpt-4o",
                region="tashkent",
                create_time=now_ts,
            )

        # Campaign B: High CVR (10 clicks, 2 conversions = CVR 20.0% > 3.0%) -> Scale Winner Trigger (+30% budget)
        cmp_b = AdCampaign.create(
            id="cmp_rule_test_b",
            advertiser_id=adv.id,
            name="High CVR Campaign B",
            product_name="Product B",
            advertisement_text="Ad text B",
            landing_url="https://site.uz/b",
            daily_budget=10.0,
            total_budget=100.0,
            spent_today=4.0,
            total_spent=4.0,
            pricing_model="cpc",
            bid_amount=0.10,
            conversions_count=2,
            conversion_rate=20.0,
            status="active",
            moderation_status="approved",
            create_time=now_ts,
            update_time=now_ts,
        )
        for i in range(10):
            AdImpression.create(
                id=f"imp_b_{i}",
                campaign_id=cmp_b.id,
                advertiser_id=adv.id,
                user_id=f"usr_b_{i}",
                query="test query b",
                cost=0.01,
                user_language="ru",
                model="gpt-4o",
                region="tashkent",
                create_time=now_ts,
            )
            AdClick.create(
                id=f"clk_b_{i}",
                impression_id=f"imp_b_{i}",
                campaign_id=cmp_b.id,
                advertiser_id=adv.id,
                user_id=f"usr_b_{i}",
                cost=0.10,
                click_token=f"tok_b_{i}",
                create_time=now_ts,
            )
        AdConversion.create(
            id="conv_b_1",
            campaign_id=cmp_b.id,
            advertiser_id=adv.id,
            event_type="purchase",
            value=50.0,
            currency="USD",
            create_time=now_ts,
        )

        # Campaign C: High CPA ($12 spent / 1 conv = $12.00 > $8.00) -> CPA Guard Trigger (-20% bid from $0.20 to $0.16)
        cmp_c = AdCampaign.create(
            id="cmp_rule_test_c",
            advertiser_id=adv.id,
            name="Expensive CPA Campaign C",
            product_name="Product C",
            advertisement_text="Ad text C",
            landing_url="https://site.uz/c",
            daily_budget=20.0,
            total_budget=200.0,
            spent_today=12.0,
            total_spent=12.0,
            pricing_model="cpc",
            bid_amount=0.20,
            conversions_count=1,
            status="active",
            moderation_status="approved",
            create_time=now_ts,
            update_time=now_ts,
        )
        for i in range(10):
            AdImpression.create(
                id=f"imp_c_{i}",
                campaign_id=cmp_c.id,
                advertiser_id=adv.id,
                user_id=f"usr_c_{i}",
                query="test query c",
                cost=0.02,
                user_language="ru",
                model="gpt-4o",
                region="tashkent",
                create_time=now_ts,
            )
            AdClick.create(
                id=f"clk_c_{i}",
                impression_id=f"imp_c_{i}",
                campaign_id=cmp_c.id,
                advertiser_id=adv.id,
                user_id=f"usr_c_{i}",
                cost=1.18,
                click_token=f"tok_c_{i}",
                create_time=now_ts,
            )
        AdConversion.create(
            id="conv_c_1",
            campaign_id=cmp_c.id,
            advertiser_id=adv.id,
            event_type="lead",
            value=10.0,
            currency="USD",
            create_time=now_ts,
        )

        # 5. Run All Rules Engine
        eval_result = AdAutomatedRulesService.run_all_rules(advertiser_id=adv.id)
        self.assertGreaterEqual(eval_result["rules_evaluated"], 3)
        self.assertGreaterEqual(eval_result["actions_triggered"], 3)

        # 6. Verify automated actions on campaigns
        cmp_a = AdCampaign.get_by_id(cmp_a.id)
        self.assertEqual(cmp_a.status, "paused")  # Stop-Loss paused it!

        cmp_b = AdCampaign.get_by_id(cmp_b.id)
        self.assertEqual(cmp_b.daily_budget, 13.0)  # $10.00 + 30% = $13.00

        cmp_c = AdCampaign.get_by_id(cmp_c.id)
        self.assertEqual(cmp_c.bid_amount, 0.16)  # $0.20 - 20% = $0.16

        # 7. Verify Execution Logs
        logs = AdAutomatedRulesService.list_execution_logs(advertiser_id=adv.id)
        self.assertGreaterEqual(len(logs), 3)
        actions_logged = [l["action_taken"] for l in logs]
        self.assertIn("pause_campaign", actions_logged)
        self.assertIn("increase_budget", actions_logged)
        self.assertIn("decrease_bid", actions_logged)

    def test_27_multi_touch_attribution_and_funnel_journey(self):
        """Phase 25: Test Multi-Touch Attribution (First/Last/Linear/Decay/Position) and Funnel Analytics."""
        user = User.create(
            id="user_mta_1",
            email="mta_adv@swipies.app",
            nickname="MTA Advertiser",
            create_time=current_timestamp(),
        )
        tenant = Tenant.create(
            id="tenant_mta_1",
            name="MTA Tenant",
            llm_id="",
            embd_id="",
            asr_id="",
            img2txt_id="",
            rerank_id="",
            parser_ids="",
            credit=0,
            create_time=current_timestamp(),
        )
        adv = Advertiser.create(
            id="adv_mta_1",
            user_id=user.id,
            tenant_id=tenant.id,
            company_name="MTA Marketing Hub",
            balance=100.0,
            status="active",
            create_time=current_timestamp(),
        )

        # Create 3 multi-stage funnel campaigns
        cmp1 = AdCampaign.create(
            id="cmp_mta_top",
            advertiser_id=adv.id,
            name="1. Top Funnel AI Discovery",
            product_name="Cloud CRM Pro",
            advertisement_text="Top of funnel discovery ad",
            landing_url="https://example.com/crm",
            daily_budget=20.0,
            total_budget=200.0,
            pricing_model="cpc",
            bid_amount=0.20,
            status="active",
            moderation_status="approved",
            create_time=current_timestamp(),
        )
        cmp2 = AdCampaign.create(
            id="cmp_mta_mid",
            advertiser_id=adv.id,
            name="2. Mid Funnel Feature Demo",
            product_name="Cloud CRM Pro",
            advertisement_text="Mid funnel feature demo ad",
            landing_url="https://example.com/crm/demo",
            daily_budget=20.0,
            total_budget=200.0,
            pricing_model="cpc",
            bid_amount=0.25,
            status="active",
            moderation_status="approved",
            create_time=current_timestamp(),
        )
        cmp3 = AdCampaign.create(
            id="cmp_mta_bot",
            advertiser_id=adv.id,
            name="3. Bottom Funnel 30% Promo",
            product_name="Cloud CRM Pro",
            advertisement_text="Bottom funnel conversion ad",
            landing_url="https://example.com/crm/promo",
            daily_budget=30.0,
            total_budget=300.0,
            pricing_model="cpc",
            bid_amount=0.35,
            status="active",
            moderation_status="approved",
            create_time=current_timestamp(),
        )

        visitor_id = "visitor_journey_99"
        base_time = current_timestamp() - (5 * 86400 * 1000)

        # 1. Record 3-step User Journey Touchpoints
        tp1 = AdMultiTouchAttributionService.record_touchpoint(
            visitor_id=visitor_id,
            advertiser_id=adv.id,
            campaign_id=cmp1.id,
            touchpoint_type="impression",
            channel="ai_chat",
            model_name="deepseek-v3",
            device="mobile",
            cost=0.0,
            create_time=base_time,
        )
        self.assertEqual(tp1.touchpoint_seq, 1)

        tp2 = AdMultiTouchAttributionService.record_touchpoint(
            visitor_id=visitor_id,
            advertiser_id=adv.id,
            campaign_id=cmp2.id,
            touchpoint_type="click",
            channel="telegram_bot",
            device="desktop",
            cost=0.25,
            create_time=base_time + (2 * 86400 * 1000),
        )
        self.assertEqual(tp2.touchpoint_seq, 2)

        tp3 = AdMultiTouchAttributionService.record_touchpoint(
            visitor_id=visitor_id,
            advertiser_id=adv.id,
            campaign_id=cmp3.id,
            touchpoint_type="click",
            channel="retargeting",
            device="desktop",
            cost=0.35,
            create_time=base_time + (4 * 86400 * 1000),
        )
        self.assertEqual(tp3.touchpoint_seq, 3)

        # 2. Attribute Conversion ($150.00 purchase)
        attr = AdMultiTouchAttributionService.attribute_conversion(
            visitor_id=visitor_id,
            advertiser_id=adv.id,
            conversion_event_id="order_mta_555",
            conversion_type="purchase",
            conversion_value=150.0,
            currency="USD",
        )
        self.assertIsNotNone(attr)
        self.assertEqual(attr.total_touchpoints, 3)
        self.assertEqual(attr.first_touch_campaign_id, cmp1.id)
        self.assertEqual(attr.last_touch_campaign_id, cmp3.id)

        # Verify Position-Based / U-Shaped (40% first, 20% mid, 40% last)
        pos_weights = attr.position_based_weights
        self.assertAlmostEqual(pos_weights[cmp1.id], 0.40, delta=0.01)
        self.assertAlmostEqual(pos_weights[cmp2.id], 0.20, delta=0.01)
        self.assertAlmostEqual(pos_weights[cmp3.id], 0.40, delta=0.01)

        # Verify Linear Weights (1/3 each)
        lin_weights = attr.linear_weights
        self.assertAlmostEqual(lin_weights[cmp1.id], 0.3333, delta=0.01)
        self.assertAlmostEqual(lin_weights[cmp2.id], 0.3333, delta=0.01)
        self.assertAlmostEqual(lin_weights[cmp3.id], 0.3333, delta=0.01)

        # Verify Time-Decay Weights (Last touch has higher weight than first touch)
        td_weights = attr.time_decay_weights
        self.assertGreater(td_weights[cmp3.id], td_weights[cmp1.id])

        # 3. Attribution Summary across Models
        summary_pos = AdMultiTouchAttributionService.get_attribution_summary(
            advertiser_id=adv.id,
            model="position_based",
            days=30,
        )
        self.assertEqual(summary_pos["total_conversions"], 1)
        self.assertEqual(summary_pos["total_revenue"], 150.0)
        self.assertEqual(summary_pos["avg_touchpoints_per_conversion"], 3.0)

        # 4. Conversion Journey Paths
        paths = AdMultiTouchAttributionService.get_conversion_paths(advertiser_id=adv.id, limit=10)
        self.assertEqual(len(paths), 1)
        self.assertEqual(len(paths[0]["path_steps"]), 3)

        # 5. Full-Funnel Analytics
        funnel = AdMultiTouchAttributionService.get_funnel_analytics(advertiser_id=adv.id, days=30)
        self.assertEqual(len(funnel["stages"]), 5)
        self.assertEqual(funnel["stages"][4]["count"], 1)  # 1 conversion recorded

    def test_28_lookalike_audiences_and_predictive_ltv_rfm(self):
        """
        Phase 26: Test Lookalike Audience expansion vector modeling,
        RFM Behavioral Segmentation, and Predictive Lifetime Value (pLTV / Churn Risk).
        """
        user = User.create(id=f"user_p26_{uuid.uuid4().hex[:6]}", email=f"p26_{uuid.uuid4().hex[:6]}@example.com", nickname="Lookalike User")
        tenant = Tenant.create(
            id=f"tenant_p26_{uuid.uuid4().hex[:6]}",
            name="Lookalike Tenant",
            llm_id="",
            embd_id="",
            asr_id="",
            img2txt_id="",
            rerank_id="",
            parser_ids="",
            credit=0,
            create_time=current_timestamp(),
        )
        adv = Advertiser.create(
            id=f"adv_p26_{uuid.uuid4().hex[:6]}",
            user_id=user.id,
            tenant_id=tenant.id,
            company_name="Lookalike AI Brand",
            balance=500.0,
            status="approved",
            create_time=current_timestamp(),
        )

        # 1. Create Seed Audience Segment and Add Seed Members
        seed_seg = AdAudienceService.create_segment(
            advertiser_id=adv.id,
            name="High Value VIP Purchasers",
            description="Customers who purchased > $100",
            rule_type="pixel_event",
            rule_config={"event_type": "purchase"},
        )
        self.assertIsNotNone(seed_seg["id"])

        AdAudienceService.add_member(seed_seg["id"], "cust_seed_1", "anon_1")
        AdAudienceService.add_member(seed_seg["id"], "cust_seed_2", "anon_2")
        AdAudienceService.add_member(seed_seg["id"], "cust_seed_3", "anon_3")

        # 2. Create 1% Lookalike Audience in UZ
        lookalike_uz = AdLookalikeLtvService.create_lookalike(
            advertiser_id=adv.id,
            source_segment_id=seed_seg["id"],
            name="Lookalike (UZ, 1%) - VIP Buyers",
            similarity_ratio=1,
            country="UZ",
        )
        self.assertEqual(lookalike_uz["name"], "Lookalike (UZ, 1%) - VIP Buyers")
        self.assertEqual(lookalike_uz["similarity_ratio"], 1)
        self.assertEqual(lookalike_uz["country"], "UZ")
        self.assertEqual(lookalike_uz["seed_audience_size"], 3)
        self.assertEqual(lookalike_uz["estimated_reach"], 3500)  # 1% of 350,000
        self.assertEqual(lookalike_uz["status"], "ready")

        # 3. Create 5% Lookalike Audience Global (ALL)
        lookalike_all = AdLookalikeLtvService.create_lookalike(
            advertiser_id=adv.id,
            source_segment_id=seed_seg["id"],
            name="Lookalike (Global, 5%)",
            similarity_ratio=5,
            country="ALL",
        )
        self.assertEqual(lookalike_all["estimated_reach"], 225000)  # 5% of 4,500,000

        # 4. List Lookalikes
        all_lals = AdLookalikeLtvService.list_lookalikes(advertiser_id=adv.id)
        self.assertEqual(len(all_lals), 2)

        # 5. Test RFM Scoring & pLTV Metrics Formula
        # Champions: recent (5d), frequent (6 orders), high spend ($600)
        seg_champ, pltv_90_c, pltv_365_c, churn_c = AdLookalikeLtvService.compute_rfm_metrics(
            recency_days=5, frequency=6, monetary_val=600.0
        )
        self.assertEqual(seg_champ, "champions")
        self.assertLess(churn_c, 0.20)  # Low churn risk
        self.assertGreater(pltv_90_c, 200.0)

        # At-Risk: high frequency/monetary but inactive for 80 days
        seg_risk, pltv_90_r, pltv_365_r, churn_r = AdLookalikeLtvService.compute_rfm_metrics(
            recency_days=80, frequency=5, monetary_val=400.0
        )
        self.assertEqual(seg_risk, "at_risk")
        self.assertGreater(churn_r, 0.50)  # Elevated churn risk

        # 6. Customer Sync & Batch Ingestion
        cust_profile = AdLookalikeLtvService.sync_customer_profile(
            advertiser_id=adv.id,
            visitor_id="visitor_vip_101",
            customer_identifier="vip_john@example.com",
            order_value=250.0,
            tags=["vip", "enterprise"],
        )
        self.assertEqual(cust_profile["visitor_id"], "visitor_vip_101")
        self.assertEqual(cust_profile["rfm_monetary_val"], 250.0)

        # Ingest 2nd order for same customer
        cust_profile_2 = AdLookalikeLtvService.sync_customer_profile(
            advertiser_id=adv.id,
            visitor_id="visitor_vip_101",
            order_value=150.0,
        )
        self.assertEqual(cust_profile_2["rfm_monetary_val"], 400.0)
        self.assertEqual(cust_profile_2["total_orders"], 2)

        # Batch import historical CRM customers
        batch_res = AdLookalikeLtvService.batch_sync_customers(
            advertiser_id=adv.id,
            customer_records=[
                {"visitor_id": "v_crm_1", "email": "crm1@test.uz", "order_value": 750.0, "total_orders": 8, "recency_days": 3},
                {"visitor_id": "v_crm_2", "email": "crm2@test.uz", "order_value": 30.0, "total_orders": 1, "recency_days": 75},
            ]
        )
        self.assertEqual(batch_res["synced_count"], 2)

        # 7. LTV Overview Aggregation
        overview = AdLookalikeLtvService.get_ltv_overview(advertiser_id=adv.id)
        self.assertEqual(overview["total_customers"], 3)  # visitor_vip_101, v_crm_1, v_crm_2
        self.assertGreater(overview["total_historical_revenue"], 1000.0)
        self.assertGreater(overview["avg_predicted_ltv_90d"], 0.0)
        self.assertIn("champions", overview["segment_counts"])
        self.assertEqual(len(overview["top_customers"]), 3)

        # 8. Delete Lookalike
        del_success = AdLookalikeLtvService.delete_lookalike(adv.id, lookalike_uz["id"])
        self.assertTrue(del_success)
        remaining = AdLookalikeLtvService.list_lookalikes(adv.id)
        self.assertEqual(len(remaining), 1)

    def test_29_creative_matrix_and_product_feeds(self):
        """
        Phase 27: Test AI Multi-Format Creative Matrix (Story banners, Rich cards, Video scripts)
        and Dynamic Product Ads (DPA) catalog feeds and SKU matching.
        """
        user = User.create(id=f"user_p27_{uuid.uuid4().hex[:6]}", email=f"p27_{uuid.uuid4().hex[:6]}@example.com", nickname="Creative Studio User")
        tenant = Tenant.create(
            id=f"tenant_p27_{uuid.uuid4().hex[:6]}",
            name="Creative Tenant",
            llm_id="",
            embd_id="",
            asr_id="",
            img2txt_id="",
            rerank_id="",
            parser_ids="",
            credit=0,
            create_time=current_timestamp(),
        )
        adv = Advertiser.create(
            id=f"adv_p27_{uuid.uuid4().hex[:6]}",
            user_id=user.id,
            tenant_id=tenant.id,
            company_name="Studio & Commerce Brand",
            balance=600.0,
            status="approved",
            create_time=current_timestamp(),
        )

        # 1. Generate Multi-Format Creative Matrix
        matrix = AdCreativeStudioService.generate_creative_matrix(
            advertiser_id=adv.id,
            product_name="MacBook Pro M3 Max",
            description="Ultra-fast Apple silicon laptop for developers",
            category="Ноутбуки и Электроника",
            target_audience="Разработчики и дизайнеры",
            save_assets=True,
        )
        self.assertEqual(matrix["product_name"], "MacBook Pro M3 Max")
        self.assertEqual(matrix["overall_health_score"], 95)
        self.assertIn("text_card", matrix["formats"])
        self.assertIn("rich_interactive_card", matrix["formats"])
        self.assertIn("story_banner", matrix["formats"])
        self.assertIn("leaderboard_banner", matrix["formats"])
        self.assertIn("video_storyboard", matrix["formats"])
        self.assertEqual(len(matrix["saved_assets"]), 5)

        # 2. List saved creative matrix assets
        assets = AdCreativeStudioService.list_creative_assets(advertiser_id=adv.id)
        self.assertEqual(len(assets), 5)

        # 3. Create Product Catalog Feed (DPA) with initial SKU items
        feed = AdProductFeedService.create_feed(
            advertiser_id=adv.id,
            name="Main Electronics Catalog",
            feed_type="custom_json",
            currency="USD",
            initial_items=[
                {
                    "sku": "MBP-M3-16",
                    "title": "Apple MacBook Pro 16 M3 Max",
                    "price": 3499.0,
                    "original_price": 3899.0,
                    "product_url": "https://store.uz/macbook-pro-16",
                    "category": "Laptops",
                    "brand": "Apple",
                    "availability": "in_stock",
                },
                {
                    "sku": "IPH-15-PRO",
                    "title": "Apple iPhone 15 Pro Max 256GB",
                    "price": 1199.0,
                    "original_price": 1299.0,
                    "product_url": "https://store.uz/iphone-15-pro",
                    "category": "Smartphones",
                    "brand": "Apple",
                    "availability": "in_stock",
                }
            ]
        )
        self.assertEqual(feed["name"], "Main Electronics Catalog")
        self.assertEqual(feed["items_count"], 2)

        # 4. Add individual SKU to feed
        new_sku = AdProductFeedService.add_or_update_item(
            feed_id=feed["id"],
            advertiser_id=adv.id,
            sku="AIRPODS-MAX",
            title="Apple AirPods Max Space Gray",
            price=549.0,
            original_price=599.0,
            product_url="https://store.uz/airpods-max",
            category="Audio",
            brand="Apple",
        )
        self.assertEqual(new_sku["sku"], "AIRPODS-MAX")

        # 5. List items in feed
        items = AdProductFeedService.list_feed_items(feed_id=feed["id"])
        self.assertEqual(len(items), 3)

        # 6. Intent & Lexical matching SKU for DPA dynamic insertion
        matched_laptop = AdProductFeedService.find_matching_product(advertiser_id=adv.id, query="MacBook")
        self.assertIsNotNone(matched_laptop)
        self.assertEqual(matched_laptop["sku"], "MBP-M3-16")
        self.assertEqual(matched_laptop["discount_percent"], 10)

        # 7. Creative Health Score evaluation on Campaign
        cmp = AdCampaign.create(
            id=f"cmp_p27_{uuid.uuid4().hex[:6]}",
            advertiser_id=adv.id,
            name="DPA Dynamic Search Campaign",
            product_name="MacBook Pro",
            advertisement_text="Laptops for pros with M3 Max chips",
            landing_url="https://store.uz/macbook",
            daily_budget=50.0,
            pricing_model="cpc",
            bid_amount=0.50,
            status="active",
            dco_enabled=True,
            create_time=current_timestamp(),
        )
        AdVariant.create(
            id=f"var_1_{uuid.uuid4().hex[:6]}",
            campaign_id=cmp.id,
            advertiser_id=adv.id,
            name="Variant A - Direct Offer",
            advertisement_text="Buy MacBook M3 directly",
            landing_url="https://store.uz/macbook",
            is_active=True,
            create_time=current_timestamp(),
        )
        AdVariant.create(
            id=f"var_2_{uuid.uuid4().hex[:6]}",
            campaign_id=cmp.id,
            advertiser_id=adv.id,
            name="Variant B - Discount Focus",
            advertisement_text="Get 10% discount on MacBook M3",
            landing_url="https://store.uz/macbook",
            is_active=True,
            create_time=current_timestamp(),
        )
        AdVariant.create(
            id=f"var_3_{uuid.uuid4().hex[:6]}",
            campaign_id=cmp.id,
            advertiser_id=adv.id,
            name="Variant C - Developer Specs",
            advertisement_text="MacBook M3 Max 128GB Unified Memory",
            landing_url="https://store.uz/macbook",
            is_active=True,
            create_time=current_timestamp(),
        )

        health = AdCreativeStudioService.get_creative_health_score(campaign_id=cmp.id)
        self.assertGreaterEqual(health["score"], 80)
        self.assertEqual(health["rating"], "excellent")
        self.assertTrue(health["has_dco"])
        self.assertTrue(health["has_feeds"])
        self.assertEqual(health["variants_count"], 3)

        # 8. Delete Product Feed
        deleted = AdProductFeedService.delete_feed(feed_id=feed["id"], advertiser_id=adv.id)
        self.assertTrue(deleted)
        remaining_feeds = AdProductFeedService.list_feeds(advertiser_id=adv.id)
        self.assertEqual(len(remaining_feeds), 0)

    def test_30_agency_hub_and_whitelabel_reports(self):
        """
        Phase 28: Test Enterprise Multi-Account Agency Hub, Client Workspaces,
        Role-Based Access Control (RBAC), and White-Label Executive Reporting.
        """
        user = User.create(id=f"user_ag_{uuid.uuid4().hex[:6]}", email=f"agency_{uuid.uuid4().hex[:6]}@apexmedia.uz", nickname="Apex Media Master")
        tenant = Tenant.create(
            id=f"tenant_ag_{uuid.uuid4().hex[:6]}",
            name="Apex Media Agency Tenant",
            llm_id="",
            embd_id="",
            asr_id="",
            img2txt_id="",
            rerank_id="",
            parser_ids="",
            credit=0,
            create_time=current_timestamp(),
        )
        adv = Advertiser.create(
            id=f"adv_ag_{uuid.uuid4().hex[:6]}",
            user_id=user.id,
            tenant_id=tenant.id,
            company_name="Apex Media Digital Agency",
            balance=5000.0,
            status="approved",
            create_time=current_timestamp(),
        )

        # 1. Get or create agency workspace
        ws = AdAgencyService.get_or_create_workspace(
            advertiser_id=adv.id,
            name="Apex Global Media Group",
            logo_url="https://apexmedia.uz/logo.png",
            brand_color="#4f46e5",
            report_footer_text="Apex Group Confidential Performance Analysis",
        )
        self.assertEqual(ws["name"], "Apex Global Media Group")
        self.assertEqual(ws["owner_advertiser_id"], adv.id)
        self.assertEqual(ws["members_count"], 1)  # owner admin auto-registered

        # 2. Update workspace white-label branding
        updated_ws = AdAgencyService.update_workspace(
            workspace_id=ws["id"],
            advertiser_id=adv.id,
            name="Apex Performance Agency",
            brand_color="#6366f1",
            billing_mode="consolidated",
        )
        self.assertEqual(updated_ws["name"], "Apex Performance Agency")
        self.assertEqual(updated_ws["brand_color"], "#6366f1")

        # 3. Create 2 client sub-accounts
        client1 = AdAgencyService.create_client(
            workspace_id=ws["id"],
            owner_advertiser_id=adv.id,
            client_name="Uzum Market E-commerce",
            contact_email="marketing@uzum.uz",
            monthly_budget_cap=2500.0,
        )
        self.assertEqual(client1["client_name"], "Uzum Market E-commerce")
        self.assertEqual(client1["monthly_budget_cap"], 2500.0)

        client2 = AdAgencyService.create_client(
            workspace_id=ws["id"],
            owner_advertiser_id=adv.id,
            client_name="Payme Fintech Hub",
            contact_email="ads@payme.uz",
            monthly_budget_cap=1500.0,
        )
        self.assertEqual(client2["client_name"], "Payme Fintech Hub")

        # Create campaigns under client 1
        cmp_cli1 = AdCampaign.create(
            id=f"cmp_cli1_{uuid.uuid4().hex[:6]}",
            advertiser_id=client1["client_advertiser_id"],
            name="Uzum Mega Sale 2026",
            product_name="Uzum Marketplace App",
            advertisement_text="Skidki do 70% v Uzum Market",
            landing_url="https://uzum.uz",
            daily_budget=100.0,
            pricing_model="cpc",
            bid_amount=0.40,
            total_spent=420.0,
            conversions_count=52,
            status="active",
            create_time=current_timestamp(),
        )
        AdVariant.create(
            id=f"var_cli1_{uuid.uuid4().hex[:6]}",
            campaign_id=cmp_cli1.id,
            advertiser_id=client1["client_advertiser_id"],
            name="Variant A",
            advertisement_text="Skidki do 70% v Uzum Market",
            landing_url="https://uzum.uz",
            impressions=12000,
            clicks=480,
            is_active=True,
            create_time=current_timestamp(),
        )

        # 4. List clients & verify live metrics aggregation
        clients_list = AdAgencyService.list_clients(workspace_id=ws["id"])
        self.assertEqual(len(clients_list), 2)
        c1_item = next(c for c in clients_list if c["id"] == client1["id"])
        self.assertEqual(c1_item["total_spend"], 420.0)
        self.assertEqual(c1_item["total_clicks"], 480)
        self.assertEqual(c1_item["total_conversions"], 52)
        self.assertGreater(c1_item["avg_ctr"], 0.0)

        # 5. Invite agency collaborators with RBAC
        member_buyer = AdAgencyService.invite_member(
            workspace_id=ws["id"],
            email="buyer@apexmedia.uz",
            role="media_buyer",
            assigned_client_ids=[client1["id"]],
        )
        self.assertEqual(member_buyer["role"], "media_buyer")

        member_auditor = AdAgencyService.invite_member(
            workspace_id=ws["id"],
            email="auditor@apexmedia.uz",
            role="financial_auditor",
        )
        self.assertEqual(member_auditor["role"], "financial_auditor")

        members = AdAgencyService.list_members(workspace_id=ws["id"])
        self.assertEqual(len(members), 3)  # owner + buyer + auditor

        # 6. Generate White-Label Executive Performance Report
        report = AdAgencyService.generate_executive_report(
            workspace_id=ws["id"],
            client_id=client1["id"],
            days=30,
        )
        self.assertEqual(report["client_info"]["client_name"], "Uzum Market E-commerce")
        self.assertEqual(report["white_label"]["agency_name"], "Apex Performance Agency")
        self.assertEqual(report["kpi_summary"]["total_spend"], 420.0)
        self.assertEqual(report["kpi_summary"]["total_clicks"], 480)
        self.assertEqual(report["kpi_summary"]["total_conversions"], 52)
        self.assertGreaterEqual(report["kpi_summary"]["roas"], 1.0)
        self.assertEqual(len(report["timeline_trends"]), 30)
        self.assertEqual(len(report["channel_attribution"]), 4)
        self.assertGreaterEqual(len(report["executive_takeaways"]), 3)

        # 7. Generate CSV Export
        csv_text = AdAgencyService.generate_csv_export_data(
            workspace_id=ws["id"],
            client_id=client1["id"],
            days=30,
        )
        self.assertIn("Date,Client,Spend_USD,Clicks,Conversions,Avg_CTR_Percent,ROAS", csv_text)
        self.assertIn("Uzum Market E-commerce", csv_text)

        # 8. Create Shareable Public Report Link & Resolve It
        share_res = AdAgencyService.create_shareable_report_link(
            workspace_id=ws["id"],
            client_id=client1["id"],
            report_title="Uzum Market Q3 Executive Summary",
            days=30,
        )
        self.assertIn("share_token", share_res)
        self.assertIn("share_url", share_res)

        public_rep = AdAgencyService.get_public_report(share_token=share_res["share_token"])
        self.assertEqual(public_rep["report_title"], "Uzum Market Q3 Executive Summary")
        self.assertEqual(public_rep["client_info"]["client_name"], "Uzum Market E-commerce")

        # 9. Remove Member & Delete Client
        removed = AdAgencyService.remove_member(workspace_id=ws["id"], member_id=member_auditor["id"])
        self.assertTrue(removed)
        remaining_members = AdAgencyService.list_members(workspace_id=ws["id"])
        self.assertEqual(len(remaining_members), 2)

        deleted_cli = AdAgencyService.delete_client(workspace_id=ws["id"], client_id=client2["id"])
        self.assertTrue(deleted_cli)
        active_clients = AdAgencyService.list_clients(workspace_id=ws["id"])
        self.assertEqual(len(active_clients), 1)


if __name__ == "__main__":
    unittest.main()








