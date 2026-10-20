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
import os
import sys
import types
import unittest
import uuid
from unittest.mock import MagicMock, AsyncMock
from sqlalchemy.types import TypeEngine

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Stub out heavy external dependencies
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

from peewee import SqliteDatabase

TEST_DB_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_watermark_keywords_temp.db"))
test_db = SqliteDatabase(TEST_DB_FILE)

from api.db.db_models import (
    DB,
    User,
    Tenant,
    Advertiser,
    AdCampaign,
    AdVariant,
    AdImpression,
    AdClick,
    AdConversion,
    AdTransaction,
    AdDcoLog,
    AdBiddingLog,
    AdSettings,
    AIModel,
    AIProvider,
    SubscriptionPlan,
    Knowledgebase,
    Dialog,
    UserCanvas,
    SystemSettings,
    UserSubscription,
    PaymentOrder,
)

# Override DB connection context with test_db
DB.connection_context = lambda: (lambda fn: fn)
DB.atomic = test_db.atomic
DB.transaction = test_db.transaction
DB.connect = test_db.connect
DB.close = test_db.close
DB.is_closed = test_db.is_closed
DB.execute_sql = test_db.execute_sql

MODELS = [
    User,
    Tenant,
    Advertiser,
    AdCampaign,
    AdVariant,
    AdImpression,
    AdClick,
    AdConversion,
    AdTransaction,
    AdDcoLog,
    AdBiddingLog,
    AdSettings,
    AIModel,
    AIProvider,
    SubscriptionPlan,
    Knowledgebase,
    Dialog,
    UserCanvas,
    SystemSettings,
    UserSubscription,
    PaymentOrder,
]
for model in MODELS:
    model._meta.database = test_db

from api.db.services.ai_policy_service import AIPolicyManager
from api.db.services.ad_policy_service import AdPolicyService
from api.db.services.ad_engine_service import AdEngineService, AdDcoEngineService
from api.db.services.llm_service import LLMBundle
from api.db.services.user_service import TenantLimitService
from api.db.services.payment_service import AtmosService
from api.db.services.recurring_subscription_service import RecurringSubscriptionService
from crawler.extractor import MetadataExtractor
from crawler.metadata import MetadataBuilder
from crawler.preview import WebsitePreviewAnalyzer


class TestSwipiesAdsWatermarkAndCrawlerKeywords(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            if not test_db.is_closed():
                test_db.close()
            if os.path.exists(TEST_DB_FILE):
                os.remove(TEST_DB_FILE)
        except Exception:
            pass
        os.environ["ATMOS_MOCK_MODE"] = "true"
        for model in MODELS:
            model._meta.database = test_db
        test_db.connect(reuse_if_open=True)
        test_db.create_tables(MODELS, safe=True)

        from api.db.services.tenant_llm_service import TenantLLMService
        from api.db.services.langfuse_service import TenantLangfuseService
        cls._orig_check_model_access = AIPolicyManager.check_model_access
        AIPolicyManager.check_model_access = classmethod(lambda cls, *args, **kwargs: (True, "", 200))
        cls._orig_record_token_usage = getattr(AIPolicyManager, "record_token_usage", None)
        AIPolicyManager.record_token_usage = classmethod(lambda cls, *args, **kwargs: None)
        cls._orig_model_instance = TenantLLMService.model_instance
        TenantLLMService.model_instance = classmethod(lambda cls, *args, **kwargs: MagicMock())
        cls._orig_filter_by_tenant = TenantLangfuseService.filter_by_tenant
        TenantLangfuseService.filter_by_tenant = classmethod(lambda cls, *args, **kwargs: None)

        # Setup test users & tenants
        cls.tenant_defaults = {
            "llm_id": "default_llm",
            "embd_id": "default_embd",
            "asr_id": "default_asr",
            "img2txt_id": "default_img2txt",
            "rerank_id": "default_rerank",
            "parser_ids": "1",
        }
        tenant_defaults = cls.tenant_defaults
        user_defaults = {"nickname": "TestUser", "password": "hashed_pw", "is_superuser": False}
        cls.free_tenant_id = "tenant_free_" + uuid.uuid4().hex[:8]
        cls.free_user_id = cls.free_tenant_id
        Tenant.create(id=cls.free_tenant_id, name="Free Workspace", plan_type="free", **tenant_defaults)
        User.create(id=cls.free_user_id, email=f"free_{uuid.uuid4().hex[:6]}@swipies.app", **user_defaults)

        cls.plus_tenant_id = "tenant_plus_" + uuid.uuid4().hex[:8]
        cls.plus_user_id = cls.plus_tenant_id
        Tenant.create(id=cls.plus_tenant_id, name="Plus Workspace", plan_type="plus", **tenant_defaults)
        User.create(id=cls.plus_user_id, email=f"plus_{uuid.uuid4().hex[:6]}@swipies.app", **user_defaults)

        cls.pro_tenant_id = "tenant_pro_" + uuid.uuid4().hex[:8]
        cls.pro_user_id = cls.pro_tenant_id
        Tenant.create(id=cls.pro_tenant_id, name="Pro Workspace", plan_type="pro", **tenant_defaults)
        User.create(id=cls.pro_user_id, email=f"pro_{uuid.uuid4().hex[:6]}@swipies.app", **user_defaults)

        # Setup Advertiser & Campaign for Keywords / DKI testing
        cls.adv_id = "adv_" + uuid.uuid4().hex[:8]
        Advertiser.create(
            id=cls.adv_id,
            user_id="adv_owner_" + uuid.uuid4().hex[:8],
            tenant_id=cls.free_tenant_id,
            company_name="CRM Pro Ltd",
            balance=100.0,
            status="active",
        )
        cls.cmp_id = "cmp_crm_" + uuid.uuid4().hex[:8]
        AdCampaign.create(
            id=cls.cmp_id,
            advertiser_id=cls.adv_id,
            name="CRM Campaign",
            product_name="Cloud CRM System",
            description="Best CRM for small business",
            advertisement_text="Try our {keyword} with 20% discount!",
            landing_url="https://crmpro.example.com",
            status="active",
            pricing_model="cpc",
            bid_amount=0.50,
            daily_budget=20.0,
            total_budget=500.0,
            dco_enabled=True,
            keywords=["crm", "sales", "crm system", "автоматизация"],
            negative_keywords=["free download", "crack", "torrent", "бесплатно"],
        )

    @classmethod
    def tearDownClass(cls):
        from api.db.services.tenant_llm_service import TenantLLMService
        from api.db.services.langfuse_service import TenantLangfuseService
        TenantLLMService.model_instance = cls._orig_model_instance
        TenantLangfuseService.filter_by_tenant = cls._orig_filter_by_tenant
        AIPolicyManager.check_model_access = cls._orig_check_model_access
        if cls._orig_record_token_usage:
            AIPolicyManager.record_token_usage = cls._orig_record_token_usage
        test_db.drop_tables(MODELS, safe=True)
        test_db.close()
        if os.path.exists(TEST_DB_FILE):
            try:
                os.remove(TEST_DB_FILE)
            except Exception:
                pass

    # -------------------------------------------------------------
    # 1. Swipies Ads Platform Branding / Watermark Unit Tests
    # -------------------------------------------------------------
    def test_01_watermark_generation_ru(self):
        """Free user response in Russian MUST contain Swipies AI platform marking."""
        raw_text = "Вот пример кода для Python."
        branded = AdPolicyService.ensure_platform_branding(
            text=raw_text,
            tenant_id=self.free_tenant_id,
            user_id=self.free_user_id,
            lang="ru",
        )
        self.assertIn("Swipies AI", branded)
        self.assertIn("Сообщение отправлено через платформу Swipies AI", branded)
        self.assertIn("https://swipies.app", branded)
        self.assertTrue(branded.startswith(raw_text))

    def test_02_watermark_generation_en(self):
        """Free user response in English MUST contain Swipies AI platform marking."""
        raw_text = "Here is the architectural overview."
        branded = AdPolicyService.ensure_platform_branding(
            text=raw_text,
            tenant_id=self.free_tenant_id,
            user_id=self.free_user_id,
            lang="en",
        )
        self.assertIn("Swipies AI", branded)
        self.assertIn("Sent via Swipies AI Platform", branded)
        self.assertIn("https://swipies.app", branded)

    def test_03_watermark_generation_uz(self):
        """Free user response in Uzbek MUST contain Swipies AI platform marking."""
        raw_text = "Savolingizga javob quyidagicha."
        branded = AdPolicyService.ensure_platform_branding(
            text=raw_text,
            tenant_id=self.free_tenant_id,
            user_id=self.free_user_id,
            lang="uz",
        )
        self.assertIn("Swipies AI", branded)
        self.assertIn("Xabar Swipies AI platformasi orqali yuborildi", branded)
        self.assertIn("https://swipies.app", branded)

    def test_04_no_duplicate_watermark(self):
        """If the response already contains Swipies AI marking at the end, do not duplicate it."""
        already_branded = (
            "Привет! Ответ готов.\n\n---\n⚡ Ответ подготовлен с помощью [Swipies AI](https://swipies.app) — Сообщение отправлено через платформу Swipies AI"
        )
        rechecked = AdPolicyService.ensure_platform_branding(
            text=already_branded,
            tenant_id=self.free_tenant_id,
            user_id=self.free_user_id,
            lang="ru",
        )
        self.assertEqual(already_branded, rechecked)

    def test_05_paid_users_never_get_watermark(self):
        """Plus and Pro tier users MUST get 100% clean white-label responses without any watermark."""
        raw_text = "Enterprise analytical report."
        
        # Test Plus tier
        plus_res = AdPolicyService.ensure_platform_branding(
            text=raw_text,
            tenant_id=self.plus_tenant_id,
            user_id=self.plus_user_id,
            lang="ru",
        )
        self.assertEqual(raw_text, plus_res)
        self.assertNotIn("Swipies AI", plus_res)

        # Test Pro tier
        pro_res = AdPolicyService.ensure_platform_branding(
            text=raw_text,
            tenant_id=self.pro_tenant_id,
            user_id=self.pro_user_id,
            lang="en",
        )
        self.assertEqual(raw_text, pro_res)
        self.assertNotIn("Swipies AI", pro_res)

    # -------------------------------------------------------------
    # 2. LLMBundle Integration Tests (Async Chat & Streaming)
    # -------------------------------------------------------------
    def test_06_llm_bundle_async_chat_watermark(self):
        """LLMBundle.async_chat ensures watermark on free tier and omits on paid tier."""
        class MockModel:
            is_tools = False
            last_usage = {"prompt_tokens": 10, "completion_tokens": 15, "total_tokens": 25}
            async def async_chat(self, system, history, gen_conf, **kwargs):
                return "Mocked model response", 25

        # Free tier bundle
        free_bundle = LLMBundle(
            tenant_id=self.free_tenant_id,
            model_config={"llm_name": "deepseek-v4-pro", "model_type": "chat", "llm_factory": "deepseek", "api_key": "sk-test"},
            lang="ru",
        )
        free_bundle.mdl = MockModel()
        free_res = asyncio.run(free_bundle.async_chat("sys", [{"role": "user", "content": "test"}]))
        self.assertIn("Mocked model response", free_res)
        self.assertIn("Сообщение отправлено через платформу Swipies AI", free_res)

        # Pro tier bundle
        pro_bundle = LLMBundle(
            tenant_id=self.pro_tenant_id,
            model_config={"llm_name": "deepseek-v4-pro", "model_type": "chat", "llm_factory": "deepseek", "api_key": "sk-test"},
            lang="ru",
        )
        pro_bundle.mdl = MockModel()
        pro_res = asyncio.run(pro_bundle.async_chat("sys", [{"role": "user", "content": "test"}]))
        self.assertEqual("Mocked model response", pro_res)
        self.assertNotIn("Swipies AI", pro_res)

    def test_07_llm_bundle_streamly_watermark(self):
        """LLMBundle.async_chat_streamly yields branded final message on free tier."""
        class MockStreamModel:
            is_tools = False
            last_usage = {"prompt_tokens": 5, "completion_tokens": 10, "total_tokens": 15}
            async def async_chat_streamly(self, system, history, gen_conf, **kwargs):
                yield "Chunk 1 "
                yield "Chunk 2"
                yield 15

        free_bundle = LLMBundle(
            tenant_id=self.free_tenant_id,
            model_config={"llm_name": "gpt-4o", "model_type": "chat", "llm_factory": "openai", "api_key": "sk-test"},
            lang="en",
        )
        free_bundle.mdl = MockStreamModel()

        async def collect_stream():
            chunks = []
            async for chunk in free_bundle.async_chat_streamly("sys", [{"role": "user", "content": "hi"}]):
                chunks.append(chunk)
            return chunks

        chunks = asyncio.run(collect_stream())
        self.assertTrue(len(chunks) >= 2)
        final_chunk = chunks[-1]
        self.assertIn("Chunk 1 Chunk 2", final_chunk)
        self.assertIn("Sent via Swipies AI Platform", final_chunk)

    def test_08_llm_bundle_streamly_delta_watermark(self):
        """LLMBundle.async_chat_streamly_delta yields watermark suffix as the final delta."""
        class MockDeltaModel:
            is_tools = False
            last_usage = {"prompt_tokens": 5, "completion_tokens": 5, "total_tokens": 10}
            async def async_chat_streamly(self, system, history, gen_conf, **kwargs):
                yield "Hello "
                yield "World"
                yield 10

        free_bundle = LLMBundle(
            tenant_id=self.free_tenant_id,
            model_config={"llm_name": "gpt-4o", "model_type": "chat", "llm_factory": "openai", "api_key": "sk-test"},
            lang="ru",
        )
        free_bundle.mdl = MockDeltaModel()

        async def collect_deltas():
            deltas = []
            async for d in free_bundle.async_chat_streamly_delta("sys", [{"role": "user", "content": "hi"}]):
                deltas.append(d)
            return deltas

        deltas = asyncio.run(collect_deltas())
        # First delta "Hello ", second delta "World", final delta contains the watermark line
        self.assertIn("Hello ", deltas)
        self.assertIn("World", deltas)
        self.assertTrue(any("Сообщение отправлено через платформу Swipies AI" in d for d in deltas))

    # -------------------------------------------------------------
    # 3. Website Parser & Crawler Keywords Extraction Tests
    # -------------------------------------------------------------
    def test_09_crawler_metadata_keywords_extraction(self):
        """MetadataExtractor correctly parses <meta name='keywords'> and <meta name='news_keywords'>."""
        html = """
        <!DOCTYPE html>
        <html lang="ru">
        <head>
            <title>Тестовый Сайт Инноваций</title>
            <meta name="description" content="Платформа искусственного интеллекта">
            <meta name="keywords" content="AI, Machine Learning, RAG, Swipies, нейросети; NLP">
            <meta name="author" content="Tech Lab">
        </head>
        <body>
            <h1>Главная страница</h1>
            <p>Контент страницы</p>
        </body>
        </html>
        """
        extractor = MetadataExtractor("https://example.com")
        meta = extractor.extract(html, "https://example.com/page1")

        self.assertEqual("Тестовый Сайт Инноваций", meta["title"])
        self.assertEqual("Платформа искусственного интеллекта", meta["description"])
        self.assertIn("keywords", meta)
        expected_keywords = ["AI", "Machine Learning", "RAG", "Swipies", "нейросети", "NLP"]
        self.assertEqual(expected_keywords, meta["keywords"])

    def test_10_chunk_metadata_includes_keywords(self):
        """MetadataBuilder.build_chunk_metadata includes keywords in the chunk metadata object."""
        extracted = {
            "title": "Документация Swipies",
            "language": "ru",
            "description": "База знаний",
            "keywords": ["rag", "llm", "search"],
            "headings": [{"level": 1, "text": "Введение"}],
            "publish_date": "2026-01-01",
        }
        chunk_meta = MetadataBuilder.build_chunk_metadata(
            dataset_id="kb_123",
            source_url="https://swipies.app/docs",
            extracted_meta=extracted,
            chunk_index=0,
            total_chunks=1,
            depth=0,
        )
        self.assertEqual(chunk_meta["keywords"], ["rag", "llm", "search"])
        self.assertEqual(chunk_meta["dataset_id"], "kb_123")
        self.assertEqual(chunk_meta["title"], "Документация Swipies")

    # -------------------------------------------------------------
    # 4. Swipies Ads Keywords Matching, Negative Keywords & DKI Tests
    # -------------------------------------------------------------
    def test_11_ad_keywords_matching_and_negative_keywords_gate(self):
        """Test keyword targeting and negative keywords brand-safety gate."""
        # Query containing target keyword "crm"
        matched = AdEngineService.match_campaign_for_query(
            tenant_id=self.free_tenant_id,
            user_query="Посоветуй мне хорошую CRM систему для отдела продаж",
            conversation_id="conv_1",
            user_id=self.free_user_id,
            lang="ru",
        )
        self.assertIsNotNone(matched)
        self.assertEqual(matched["id"], self.cmp_id)

        # Query containing negative keyword "crack" -> must be blocked by negative keyword gate!
        blocked = AdEngineService.match_campaign_for_query(
            tenant_id=self.free_tenant_id,
            user_query="Где скачать crack CRM бесплатно торрент?",
            conversation_id="conv_2",
            user_id=self.free_user_id,
            lang="ru",
        )
        self.assertIsNone(blocked)

    def test_12_dynamic_keyword_insertion_dki(self):
        """Dynamic Keyword Insertion replaces {keyword} placeholder with matching query term."""
        rendered = AdDcoEngineService.render_dco_copy(
            campaign=AdCampaign.get_by_id(self.cmp_id),
            query="Нужна CRM для малого бизнеса",
            base_text="Try our {keyword} with 20% discount!",
            base_url="https://crmpro.example.com",
            lang="ru",
            log_decision=False,
        )
        self.assertNotIn("{keyword}", rendered["rendered_text"])
        self.assertIn("CRM", rendered["rendered_text"])

    # -------------------------------------------------------------
    # 5. Dataset Limits & Unlimited Agents Verification
    # -------------------------------------------------------------
    def test_13_dataset_limit_free_tier(self):
        """Free tier allows up to 5 datasets, and blocks the 6th dataset creation."""
        # Create a dedicated tenant for testing
        test_t_id = f"t_kb_limit_{uuid.uuid4().hex[:8]}"
        Tenant.create(
            id=test_t_id,
            name="KB Limit Test Tenant",
            plan_type="free",
            **self.tenant_defaults,
        )

        # 0 to 4 datasets -> check_datasets_limit must pass
        for i in range(5):
            allowed, msg = TenantLimitService.check_datasets_limit(test_t_id)
            self.assertTrue(allowed, f"Dataset creation #{i+1} should be allowed on Free tier")
            self.assertIsNone(msg)
            # Create knowledgebase in db
            Knowledgebase.create(
                id=f"kb_{test_t_id}_{i}",
                tenant_id=test_t_id,
                name=f"Dataset {i+1}",
                created_by="tester",
                status="1",
                embd_id="default_embd",
            )

        # 6th dataset attempt -> check_datasets_limit must fail
        allowed, msg = TenantLimitService.check_datasets_limit(test_t_id)
        self.assertFalse(allowed, "6th dataset creation must be blocked on Free tier")
        self.assertIn("maximum limit of 5 datasets", msg)

    def test_14_unlimited_agents_all_plans(self):
        """All plans (free, plus, pro) have unlimited agents & chat apps."""
        # Free tenant with 10 existing dialogs/agents
        test_free_t = f"t_apps_free_{uuid.uuid4().hex[:8]}"
        Tenant.create(id=test_free_t, name="Free Apps Test", plan_type="free", **self.tenant_defaults)
        for i in range(10):
            Dialog.create(
                id=f"dlg_free_{test_free_t}_{i}",
                tenant_id=test_free_t,
                name=f"Chat {i+1}",
                status="1",
                llm_id="default_llm",
                rerank_id="default_rerank",
            )
        allowed, msg = TenantLimitService.check_apps_limit(test_free_t)
        self.assertTrue(allowed, "Free plan must allow unlimited agents/apps")
        self.assertIsNone(msg)

        # Plus tenant
        test_plus_t = f"t_apps_plus_{uuid.uuid4().hex[:8]}"
        Tenant.create(id=test_plus_t, name="Plus Apps Test", plan_type="plus", **self.tenant_defaults)
        allowed, msg = TenantLimitService.check_apps_limit(test_plus_t)
        self.assertTrue(allowed, "Plus plan must allow unlimited agents/apps")

        # Pro tenant
        test_pro_t = f"t_apps_pro_{uuid.uuid4().hex[:8]}"
        Tenant.create(id=test_pro_t, name="Pro Apps Test", plan_type="pro", **self.tenant_defaults)
        allowed, msg = TenantLimitService.check_apps_limit(test_pro_t)
        self.assertTrue(allowed, "Pro plan must allow unlimited agents/apps")

    # -------------------------------------------------------------
    # 6. Pricing Verification ($20 Plus, $40 Pro) & Ad Exemption
    # -------------------------------------------------------------
    def test_15_subscription_pricing_and_ad_exemption(self):
        """Subscription checkout prices are $20 for Plus and $40 for Pro, with full ad exemption."""
        # 1. Plus checkout pricing
        ok_plus, _, data_plus = AtmosService.create_payment_order(
            user_id="user_p1",
            tenant_id=self.plus_tenant_id,
            purpose="subscription_upgrade",
            plan_id="plus",
        )
        self.assertTrue(ok_plus)
        self.assertEqual(data_plus["amount_usd"], 20.00, "Plus plan must be priced at $20.00")

        # 2. Pro checkout pricing
        ok_pro, _, data_pro = AtmosService.create_payment_order(
            user_id="user_pr1",
            tenant_id=self.pro_tenant_id,
            purpose="subscription_upgrade",
            plan_id="pro",
        )
        self.assertTrue(ok_pro)
        self.assertEqual(data_pro["amount_usd"], 40.00, "Pro plan must be priced at $40.00")

        # 3. Recurring subscription service prices dictionary
        self.assertEqual(RecurringSubscriptionService.PLAN_PRICES.get("plus"), 20.00)
        self.assertEqual(RecurringSubscriptionService.PLAN_PRICES.get("pro"), 40.00)

        # 4. Ad exemption & white-label watermark verification
        self.assertFalse(AdPolicyService.is_ad_exempt(self.free_tenant_id, self.free_user_id))
        self.assertTrue(AdPolicyService.is_ad_exempt(self.plus_tenant_id, self.plus_user_id))
        self.assertTrue(AdPolicyService.is_ad_exempt(self.pro_tenant_id, self.pro_user_id))

        # Plus and Pro must have empty watermark suffix
        self.assertEqual(AdPolicyService.get_platform_branding_suffix(self.plus_tenant_id, self.plus_user_id), "")
        self.assertEqual(AdPolicyService.get_platform_branding_suffix(self.pro_tenant_id, self.pro_user_id), "")

        # Free tier must have watermark branding
        suffix = AdPolicyService.get_platform_branding_suffix(self.free_tenant_id, self.free_user_id)
        self.assertIn("swipies.app", suffix)
        self.assertIn("Swipies AI", suffix)


if __name__ == "__main__":
    unittest.main()
