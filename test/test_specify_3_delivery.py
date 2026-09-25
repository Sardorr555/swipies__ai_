#
#  Test Suite for Specify-3: Swipies Ad Delivery & Tracking Engine
#
import os
import sys
import unittest
import uuid
import time
from datetime import datetime, timezone
from peewee import SqliteDatabase

# Ensure project root in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Create temporary SQLite database file for tests
TEST_DB_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_sp3_temp.db"))
test_db = SqliteDatabase(TEST_DB_FILE)

from api.db.db_models import (
    DB,
    User,
    Tenant,
    Advertiser,
    AdCampaign,
    AdImpression,
    AdClick,
    AdConversion,
    AdTransaction,
    AdSettings,
    AdAudienceSegment,
    AdAudienceMember,
    AdVariant,
    SubscriptionPlan,
    AdIpBlacklist,
    AdFraudLog,
    AdJourneyTouchpoint,
    AdConversionAttribution,
    AdBiddingLog,
)
from api.db.services.ad_engine_service import AdEngineService, AdSettingsService
from api.db.services.ad_policy_service import AdPolicyService
from api.db.services.llm_service import LLMBundle


class TestSpecify3DeliveryAndTracking(unittest.TestCase):
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

        cls.models = [
            User,
            Tenant,
            Advertiser,
            AdCampaign,
            AdImpression,
            AdClick,
            AdConversion,
            AdTransaction,
            AdSettings,
            AdAudienceSegment,
            AdAudienceMember,
            AdVariant,
            SubscriptionPlan,
            AdIpBlacklist,
            AdFraudLog,
            AdJourneyTouchpoint,
            AdConversionAttribution,
            AdBiddingLog,
        ]
        for m in cls.models:
            m._meta.database = test_db
        test_db.connect(reuse_if_open=True)
        test_db.create_tables(cls.models, safe=True)

        SubscriptionPlan.get_or_create(
            id="free",
            defaults={"name": "Free", "daily_token_limit": 50000, "monthly_token_limit": 1000000}
        )

    @classmethod
    def tearDownClass(cls):
        test_db.close()
        if os.path.exists(TEST_DB_FILE):
            try:
                os.remove(TEST_DB_FILE)
            except Exception:
                pass

    def setUp(self):
        self.ts = int(time.time() * 1000)
        self.test_prefix = f"sp3_{uuid.uuid4().hex[:8]}"

        # Create advertiser
        self.advertiser = Advertiser.create(
            id=f"adv_{self.test_prefix}",
            user_id=f"usr_adv_{self.test_prefix}",
            tenant_id=f"tnt_adv_{self.test_prefix}",
            company_name="Acme AI Analytics",
            contact_email="test@acmeanalytics.io",
            balance=100.0,
            status="active",
            create_time=self.ts,
            update_time=self.ts,
        )

        # Create active approved campaign A
        self.campaign_a = AdCampaign.create(
            id=f"cmp_a_{self.test_prefix}",
            advertiser_id=self.advertiser.id,
            name="AI Analytics Suite",
            product_name="Acme Analytics Pro",
            description="Enterprise predictive AI analytics for modern SaaS.",
            advertisement_text="Transform your business with predictive AI analytics.",
            landing_url="https://acmeanalytics.io/signup",
            keywords=["analytics", "predictive", "metrics", "dashboard"],
            target_categories=["saas", "developer_tools"],
            target_languages=["en", "ru"],
            target_models=["gpt-4o", "claude-3-5-sonnet"],
            pricing_model="cpc",
            bid_amount=0.50,
            daily_budget=50.0,
            total_budget=500.0,
            spent_today=0.0,
            total_spent=0.0,
            frequency_cap_impressions=2,
            frequency_cap_hours=24,
            priority=5,
            status="active",
            moderation_status="approved",
            create_time=self.ts,
            update_time=self.ts,
        )

        # Create active approved campaign B
        self.campaign_b = AdCampaign.create(
            id=f"cmp_b_{self.test_prefix}",
            advertiser_id=self.advertiser.id,
            name="AI Cloud Database",
            product_name="Acme Cloud DB",
            description="Ultra fast vector database for LLM apps.",
            advertisement_text="Ultra fast vector storage for high performance LLMs.",
            landing_url="https://acmeanalytics.io/clouddb",
            keywords=["database", "vector", "storage", "analytics"],
            target_categories=["saas", "infrastructure"],
            pricing_model="cpc",
            bid_amount=0.40,
            daily_budget=50.0,
            total_budget=500.0,
            spent_today=0.0,
            total_spent=0.0,
            frequency_cap_impressions=5,
            frequency_cap_hours=24,
            priority=4,
            status="active",
            moderation_status="approved",
            create_time=self.ts,
            update_time=self.ts,
        )

    def tearDown(self):
        # Clean up records created for this test run
        with DB.connection_context():
            AdClick.delete().where(AdClick.advertiser_id == self.advertiser.id).execute()
            AdImpression.delete().where(AdImpression.advertiser_id == self.advertiser.id).execute()
            AdTransaction.delete().where(AdTransaction.advertiser_id == self.advertiser.id).execute()
            AdAudienceMember.delete().where(AdAudienceMember.user_id.startswith(f"usr_{self.test_prefix}")).execute()
            AdCampaign.delete().where(AdCampaign.advertiser_id == self.advertiser.id).execute()
            self.advertiser.delete_instance()

    def test_campaign_matching_and_scoring(self):
        """Test keyword intent matching, language/model bonus, and negative keywords."""
        # 1. Matching query
        matched = AdEngineService.match_campaign_for_query(
            user_id=f"usr_{self.test_prefix}_1",
            tenant_id=f"tnt_{self.test_prefix}_1",
            user_query="Which analytics tool should I use for predictive metrics?",
            model_name="gpt-4o",
            lang="en",
        )
        self.assertIsNotNone(matched)
        self.assertEqual(matched["id"], self.campaign_a.id)
        self.assertIn("tracking_url", matched)
        self.assertTrue(matched["tracking_url"].startswith("/v1/ads/r/"))

        # 2. Negative keywords gate
        self.campaign_a.negative_keywords = ["cheap", "free", "crack"]
        self.campaign_a.save()

        blocked = AdEngineService.match_campaign_for_query(
            user_id=f"usr_{self.test_prefix}_2",
            tenant_id=f"tnt_{self.test_prefix}_2",
            user_query="Download free crack analytics software",
            model_name="gpt-4o",
            lang="en",
        )
        # Should not match campaign_a because of negative keyword 'free'/'crack'
        if blocked:
            self.assertNotEqual(blocked["id"], self.campaign_a.id)

    def test_frequency_capping_campaign_and_global(self):
        """Test both campaign-specific and global daily frequency capping."""
        user_id = f"usr_{self.test_prefix}_freq"
        tenant_id = f"tnt_{self.test_prefix}_freq"

        # Campaign A has frequency_cap_impressions = 2
        # 1st impression
        match_1 = AdEngineService.match_campaign_for_query(
            user_id=user_id,
            tenant_id=tenant_id,
            user_query="Need predictive analytics dashboard",
        )
        self.assertIsNotNone(match_1)
        self.assertEqual(match_1["id"], self.campaign_a.id)

        # 2nd impression
        match_2 = AdEngineService.match_campaign_for_query(
            user_id=user_id,
            tenant_id=tenant_id,
            user_query="Need predictive analytics dashboard",
        )
        self.assertIsNotNone(match_2)
        self.assertEqual(match_2["id"], self.campaign_a.id)

        # Configure global daily impressions cap = 3
        AdSettingsService.set_setting("max_impressions_per_user_day", 3)

        # 3rd query: Campaign A cap reached (2 imps). Falls back to Campaign B
        match_3 = AdEngineService.match_campaign_for_query(
            user_id=user_id,
            tenant_id=tenant_id,
            user_query="Need predictive analytics dashboard",
        )
        self.assertIsNotNone(match_3)
        self.assertEqual(match_3["id"], self.campaign_b.id, "Campaign A capped, should fallback to Campaign B")

        # 4th query: User has now reached global daily cap of 3 (2 on A + 1 on B).
        # Any subsequent queries must be blocked by global cap
        match_4 = AdEngineService.match_campaign_for_query(
            user_id=user_id,
            tenant_id=tenant_id,
            user_query="Recommend a cloud database for storage",
        )
        self.assertIsNone(match_4, "User should be blocked by global daily impressions cap")

    def test_llm_bundle_user_id_propagation(self):
        """Test that LLMBundle._prepare_effective_system_prompt resolves user_id and passes to AdPolicyService."""
        user_id = f"usr_{self.test_prefix}_bundle"
        tenant_id = f"tnt_{self.test_prefix}_bundle"

        class DummyBundle:
            def __init__(self, t_id, u_id):
                self.tenant_id = t_id
                self.user_id = u_id
                self.langfuse_session_id = "test_session_123"
                self.lang = "en"
                self.llm_name = "gpt-4o"
                self.mdl = "gpt-4o"

        dummy = DummyBundle(t_id=tenant_id, u_id=user_id)
        history = [
            {"role": "user", "content": "What analytics tool do you recommend for SaaS metrics?"}
        ]

        system_prompt = LLMBundle._prepare_effective_system_prompt(dummy, "Base instructions.", history)
        self.assertIn("tracking_url", system_prompt)
        self.assertIn(f"ref={user_id}", system_prompt, "Watermark link must carry user_id ref parameter")

    def test_audience_segment_targeting(self):
        """Test audience segment inclusion and exclusion."""
        segment_vip = AdAudienceSegment.create(
            id=f"seg_vip_{self.test_prefix}",
            advertiser_id=self.advertiser.id,
            name="VIP Users",
            type="custom",
            create_time=self.ts,
            update_time=self.ts,
        )
        self.campaign_a.target_audience_segment_ids = [segment_vip.id]
        self.campaign_a.save()

        user_target = f"usr_{self.test_prefix}_target"
        user_other = f"usr_{self.test_prefix}_other"

        # Add user_target to VIP segment
        AdAudienceMember.create(
            id=uuid.uuid4().hex[:32],
            segment_id=segment_vip.id,
            user_id=user_target,
            create_time=self.ts,
        )

        # user_target should match
        match_target = AdEngineService.match_campaign_for_query(
            user_id=user_target,
            tenant_id=f"tnt_{self.test_prefix}",
            user_query="Need analytics metrics",
        )
        self.assertIsNotNone(match_target)
        self.assertEqual(match_target["id"], self.campaign_a.id)

        # user_other should NOT match campaign A
        match_other = AdEngineService.match_campaign_for_query(
            user_id=user_other,
            tenant_id=f"tnt_{self.test_prefix}",
            user_query="Need analytics metrics",
        )
        if match_other:
            self.assertNotEqual(match_other["id"], self.campaign_a.id)

        # Clean up segment
        segment_vip.delete_instance()

    def test_tracking_url_in_ad_policy_and_llm_prompt(self):
        """Test that tracking_url is injected into LLM prompt and points to /v1/ads/r/."""
        user_id = f"usr_{self.test_prefix}_prompt"
        tenant_id = f"tnt_{self.test_prefix}_prompt"

        prompt = AdPolicyService.build_effective_system_prompt(
            tenant_id=tenant_id,
            base_system_prompt="You are a helpful AI assistant.",
            user_query="What analytics tool do you recommend for SaaS metrics?",
            user_id=user_id,
            model_name="gpt-4o",
            lang="en",
        )

        self.assertIn("[COMMERCIAL GUIDELINES & SPONSORED CONTENT POLICY]", prompt)
        self.assertIn("tracking_url", prompt, "Prompt context must supply tracking_url for click attribution")
        self.assertIn("/v1/ads/r/", prompt, "Tracking URL must lead to /v1/ads/r/ redirect")
        self.assertIn(self.campaign_a.product_name, prompt)

    def test_click_tracking_billing_and_deduplication(self):
        """Test CPC click tracking, atomic balance deduction, and 1-hour deduplication."""
        user_id = f"usr_{self.test_prefix}_clk"
        tenant_id = f"tnt_{self.test_prefix}_clk"

        matched = AdEngineService.match_campaign_for_query(
            user_id=user_id,
            tenant_id=tenant_id,
            user_query="Need predictive analytics metrics",
        )
        self.assertIsNotNone(matched)
        token = matched["tracking_url"].replace("/v1/ads/r/", "")

        initial_balance = self.advertiser.balance
        cpc_bid = float(self.campaign_a.bid_amount)  # 0.50

        # First click: valid
        dest_url = AdEngineService.track_click(
            click_token=token,
            user_id=user_id,
            ip_hash="test_ip_hash_1",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            raw_ip="127.0.0.1",
        )
        self.assertEqual(dest_url, self.campaign_a.landing_url)

        # Reload advertiser & campaign
        adv_after = Advertiser.get_by_id(self.advertiser.id)
        cmp_after = AdCampaign.get_by_id(self.campaign_a.id)

        self.assertAlmostEqual(adv_after.balance, initial_balance - cpc_bid, places=2)
        self.assertAlmostEqual(cmp_after.spent_today, cpc_bid, places=2)

        # Second click within 1 hour: should be deduplicated (no second charge)
        dest_url_2 = AdEngineService.track_click(
            click_token=token,
            user_id=user_id,
            ip_hash="test_ip_hash_1",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            raw_ip="127.0.0.1",
        )
        self.assertEqual(dest_url_2, self.campaign_a.landing_url)

        adv_after_2 = Advertiser.get_by_id(self.advertiser.id)
        self.assertAlmostEqual(adv_after_2.balance, adv_after.balance, places=2, msg="Duplicate click must not double charge")


if __name__ == "__main__":
    unittest.main()
