#
# Integration test for Subscription Expiration (30 days / 1 month lifecycle)
#
import os
import sys
import unittest
from datetime import datetime, timedelta
from peewee import SqliteDatabase

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import mock loader from test_ai_infrastructure
import test.test_ai_infrastructure  # noqa: F401

from api.db.db_models import DB, User, Tenant, UserTenant, Dialog, UserCanvas
from api.db.services.user_service import TenantService
from common.constants import StatusEnum
from api.db import UserTenantRole

# Passthrough connection_context for SQLite testing
DB.connection_context = lambda: (lambda fn: fn)


def create_test_tenant(**kwargs):
    defaults = {
        "name": "Test Tenant",
        "llm_id": "deepseek-chat",
        "embd_id": "text-embedding-3-small",
        "rerank_id": "",
        "asr_id": "",
        "img2txt_id": "",
        "tts_id": "",
        "parser_ids": "",
        "plan_type": "free",
        "credit": 512,
        "status": StatusEnum.VALID.value,
    }
    defaults.update(kwargs)
    return Tenant.create(**defaults)


class TestSubscriptionExpiry(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_db = SqliteDatabase(":memory:")
        models = [User, Tenant, UserTenant, Dialog, UserCanvas]
        for m in models:
            m._meta.database = cls.test_db
        cls.test_db.bind(models)
        cls.test_db.connect()
        cls.test_db.create_tables(models)

    def test_01_is_subscription_expired_helper(self):
        """Test timestamp comparison across multiple formats."""
        now = datetime.now()

        # None / empty is not expired
        self.assertFalse(TenantService.is_subscription_expired(None))
        self.assertFalse(TenantService.is_subscription_expired(""))

        # Future datetime is active (+30 days)
        future_dt = now + timedelta(days=30)
        self.assertFalse(TenantService.is_subscription_expired(future_dt))

        # Past datetime is expired (-1 day)
        past_dt = now - timedelta(days=1)
        self.assertTrue(TenantService.is_subscription_expired(past_dt))

        # Future string format
        future_str = (now + timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
        self.assertFalse(TenantService.is_subscription_expired(future_str))

        # Past string format
        past_str = (now - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")
        self.assertTrue(TenantService.is_subscription_expired(past_str))

    def test_02_expire_due_subscriptions_batch(self):
        """Test that expire_due_subscriptions downgrades expired tenants and keeps active ones."""
        now = datetime.now()

        # 1. Create active tenant (Plus plan valid for 30 days)
        active_tenant = create_test_tenant(
            id="tenant_active_30d",
            name="Active User",
            plan_type="plus",
            plan_expiry_date=now + timedelta(days=28),
            credit=5000,
        )

        # 2. Create expired tenant (Plus plan expired 2 days ago)
        expired_tenant = create_test_tenant(
            id="tenant_expired_30d",
            name="Expired User",
            plan_type="plus",
            plan_expiry_date=now - timedelta(days=2),
            credit=5000,
        )

        # Run batch expiration
        expired_count = TenantService.expire_due_subscriptions()
        self.assertEqual(expired_count, 1, "Should have expired exactly 1 tenant")

        # Verify active tenant is STILL PLUS
        refreshed_active = Tenant.get_by_id("tenant_active_30d")
        self.assertEqual(refreshed_active.plan_type, "plus")
        self.assertIsNotNone(refreshed_active.plan_expiry_date)
        self.assertEqual(refreshed_active.credit, 5000)

        # Verify expired tenant was DOWNGRADED TO FREE
        refreshed_expired = Tenant.get_by_id("tenant_expired_30d")
        self.assertEqual(refreshed_expired.plan_type, "free")
        self.assertIsNone(refreshed_expired.plan_expiry_date)
        self.assertEqual(refreshed_expired.credit, 512)

    def test_03_get_info_by_auto_downgrades_on_access(self):
        """Test that get_info_by automatically detects and downgrades an expired subscription on login/load."""
        now = datetime.now()

        user = User.create(
            id="usr_auto_expire",
            nickname="Auto Expire",
            email="auto_expire@swipies.app",
            status=StatusEnum.VALID.value,
        )
        tenant = create_test_tenant(
            id="usr_auto_expire",
            name="Auto Expire",
            plan_type="pro",
            plan_expiry_date=now - timedelta(hours=3),  # Expired 3 hours ago
            credit=10000,
        )
        UserTenant.create(
            id="ut_auto_expire",
            user_id=user.id,
            tenant_id=tenant.id,
            role=UserTenantRole.OWNER,
            invited_by=user.id,
            status=StatusEnum.VALID.value,
        )

        # When user info is fetched
        info_list = TenantService.get_info_by(user.id)
        self.assertTrue(len(info_list) > 0)
        info = info_list[0]

        # Plan must be downgraded to free
        self.assertEqual(info["plan_type"], "free")
        self.assertIsNone(info["plan_expiry_date"])
        self.assertEqual(info["credit"], 512)

        # In DB, record should also be free
        db_tenant = Tenant.get_by_id(user.id)
        self.assertEqual(db_tenant.plan_type, "free")
        self.assertIsNone(db_tenant.plan_expiry_date)

    def test_04_transaction_validity_window(self):
        """Test transaction age check against duration_months."""
        now = datetime.now()
        tx_created = now - timedelta(days=15)
        tx_expiry = tx_created + timedelta(days=1 * 30)
        self.assertFalse(now > tx_expiry, "15-day-old 1-month transaction is not expired")

        old_tx_created = now - timedelta(days=32)
        old_tx_expiry = old_tx_created + timedelta(days=1 * 30)
        self.assertTrue(now > old_tx_expiry, "32-day-old 1-month transaction is expired")

    def test_05_limit_checks_auto_downgrade_expired_tenant(self):
        """Test that calling check_apps_limit auto-downgrades an expired tenant."""
        now = datetime.now()
        t = create_test_tenant(
            id="tenant_limits_expired",
            name="Limits Expired",
            plan_type="pro",
            plan_expiry_date=now - timedelta(days=1),
            credit=10000,
        )
        self.assertEqual(t.plan_type, "pro")

        from api.db.services.user_service import TenantLimitService
        TenantLimitService.check_apps_limit(t.id)

        refreshed = Tenant.get_by_id(t.id)
        self.assertEqual(refreshed.plan_type, "free", "Tenant must be downgraded to free upon limit check")
        self.assertIsNone(refreshed.plan_expiry_date)
        self.assertEqual(refreshed.credit, 512)


if __name__ == "__main__":
    unittest.main()
