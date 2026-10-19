#
#  Copyright 2026 The InfiniFlow & Swipies AI Authors. All Rights Reserved.
#
import os
import sys
import types
import unittest
from unittest.mock import MagicMock, AsyncMock
from peewee import SqliteDatabase
from sqlalchemy.types import TypeEngine

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Stubs for heavy dependencies
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

TEST_DB_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_admin_limits_temp.db"))
test_db = SqliteDatabase(TEST_DB_FILE)

from api.db.db_models import (
    DB,
    User,
    Tenant,
    SubscriptionPlan,
    Knowledgebase,
    Dialog,
    UserCanvas,
    SystemSettings,
)

# Bind test sqlite database
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
    SubscriptionPlan,
    Knowledgebase,
    Dialog,
    UserCanvas,
    SystemSettings,
]

for model in MODELS:
    model._meta.database = test_db

test_db.connect(reuse_if_open=True)
test_db.create_tables(MODELS, safe=True)

from api.db.services.system_settings_service import SystemSettingsService
from api.db.services.ai_policy_service import SubscriptionPlanService
from api.db.services.user_service import TenantLimitService, TenantService


class TestAdminPlanLimitsManagement(unittest.TestCase):
    @classmethod
    def tearDownClass(cls):
        test_db.close()
        if os.path.exists(TEST_DB_FILE):
            try:
                os.remove(TEST_DB_FILE)
            except Exception:
                pass

    def test_01_tenant_limit_service_uses_system_settings_and_db(self):
        """Verify TenantLimitService prioritizes SystemSettings then SubscriptionPlan."""
        SystemSettings.delete().where(SystemSettings.name.in_([
            "plan.test_plan.datasets_limit",
            "plan.test_plan.apps_limit",
            "plan.test_plan.storage_gb"
        ])).execute()

        SubscriptionPlan.delete().where(SubscriptionPlan.id == "test_plan").execute()
        SubscriptionPlan.create(
            id="test_plan",
            name="Test Plan",
            monthly_token_limit=100000,
            max_datasets=8,
            max_agents=12,
            max_storage_gb=2.5,
            status="1"
        )

        # 1. Without SystemSettings, should fetch from SubscriptionPlan
        limit_ds = TenantLimitService.get_plan_limit("test_plan", "datasets_limit", 5)
        self.assertEqual(limit_ds, 8.0)

        limit_apps = TenantLimitService.get_plan_limit("test_plan", "apps_limit", -1)
        self.assertEqual(limit_apps, 12.0)

        limit_storage = TenantLimitService.get_plan_limit("test_plan", "storage_gb", 0.5)
        self.assertEqual(limit_storage, 2.5)

        # 2. When admin updates SystemSettings, SystemSettings takes immediate precedence
        SystemSettingsService.save(
            name="plan.test_plan.datasets_limit",
            value="15",
            source="variable",
            data_type="string",
            create_time=0,
            create_date="2026-10-20",
            update_time=0,
            update_date="2026-10-20"
        )
        limit_ds_updated = TenantLimitService.get_plan_limit("test_plan", "datasets_limit", 5)
        self.assertEqual(limit_ds_updated, 15.0)

        # Clean up
        SystemSettings.delete().where(SystemSettings.name == "plan.test_plan.datasets_limit").execute()
        SubscriptionPlan.delete().where(SubscriptionPlan.id == "test_plan").execute()

    tenant_defaults = {
        "llm_id": "default_llm",
        "embd_id": "default_embd",
        "asr_id": "default_asr",
        "img2txt_id": "default_img2txt",
        "rerank_id": "default_rerank",
        "parser_ids": "1",
    }

    def test_02_datasets_limit_enforcement(self):
        """Verify check_datasets_limit enforces limit strictly."""
        tenant_id = "test_tenant_limits_123"
        Tenant.delete().where(Tenant.id == tenant_id).execute()
        Tenant.create(
            id=tenant_id,
            name="Test Limits Tenant",
            plan_type="test_tier",
            **self.tenant_defaults
        )

        # Set limit to 2 datasets
        SystemSettings.delete().where(SystemSettings.name == "plan.test_tier.datasets_limit").execute()
        SystemSettingsService.save(
            name="plan.test_tier.datasets_limit",
            value="2",
            source="variable",
            data_type="string",
            create_time=0,
            create_date="2026-10-20",
            update_time=0,
            update_date="2026-10-20"
        )

        Knowledgebase.delete().where(Knowledgebase.tenant_id == tenant_id).execute()

        # 0 datasets -> OK
        ok, msg = TenantLimitService.check_datasets_limit(tenant_id)
        self.assertTrue(ok)
        self.assertIsNone(msg)

        # Add 1 dataset -> OK
        kb1 = Knowledgebase.create(
            id="kb_test_1",
            name="KB 1",
            tenant_id=tenant_id,
            created_by=tenant_id,
            embd_id="default_embd",
            status="1"
        )
        ok, msg = TenantLimitService.check_datasets_limit(tenant_id)
        self.assertTrue(ok)

        # Add 2nd dataset -> Reached limit
        kb2 = Knowledgebase.create(
            id="kb_test_2",
            name="KB 2",
            tenant_id=tenant_id,
            created_by=tenant_id,
            embd_id="default_embd",
            status="1"
        )
        ok, msg = TenantLimitService.check_datasets_limit(tenant_id)
        self.assertFalse(ok)
        self.assertIn("maximum limit of 2 datasets", msg)

        # Admin increases limit to 5 datasets -> Immediately allowed again!
        SystemSettingsService.update_by_name("plan.test_tier.datasets_limit", {"value": "5"})
        ok, msg = TenantLimitService.check_datasets_limit(tenant_id)
        self.assertTrue(ok)
        self.assertIsNone(msg)

        # Clean up
        Knowledgebase.delete().where(Knowledgebase.tenant_id == tenant_id).execute()
        Tenant.delete().where(Tenant.id == tenant_id).execute()
        SystemSettings.delete().where(SystemSettings.name == "plan.test_tier.datasets_limit").execute()

    def test_03_apps_limit_enforcement_and_unlimited(self):
        """Verify check_apps_limit allows unlimited (-1) and enforces numerical limits."""
        tenant_id = "test_tenant_apps_123"
        Tenant.delete().where(Tenant.id == tenant_id).execute()
        Tenant.create(
            id=tenant_id,
            name="Test Apps Tenant",
            plan_type="free",
            **self.tenant_defaults
        )

        # Free tier is unlimited by default (-1)
        ok, msg = TenantLimitService.check_apps_limit(tenant_id)
        self.assertTrue(ok)

        # Admin sets a strict limit of 1 agent/app on free plan
        SystemSettings.delete().where(SystemSettings.name == "plan.free.apps_limit").execute()
        SystemSettingsService.save(
            name="plan.free.apps_limit",
            value="1",
            source="variable",
            data_type="string",
            create_time=0,
            create_date="2026-10-20",
            update_time=0,
            update_date="2026-10-20"
        )

        Dialog.delete().where(Dialog.tenant_id == tenant_id).execute()
        UserCanvas.delete().where(UserCanvas.user_id == tenant_id).execute()

        # 0 apps -> OK
        ok, msg = TenantLimitService.check_apps_limit(tenant_id)
        self.assertTrue(ok)

        # Create 1 dialog -> reaches limit 1
        d1 = Dialog.create(
            id="dlg_test_1",
            name="Chat 1",
            tenant_id=tenant_id,
            llm_id="default_llm",
            rerank_id="default_rerank",
            kb_ids=[],
            status="1"
        )
        ok, msg = TenantLimitService.check_apps_limit(tenant_id)
        self.assertFalse(ok)
        self.assertIn("maximum limit of 1 apps", msg)

        # Admin sets back to -1 (unlimited) -> allowed!
        SystemSettingsService.update_by_name("plan.free.apps_limit", {"value": "-1"})
        ok, msg = TenantLimitService.check_apps_limit(tenant_id)
        self.assertTrue(ok)

        # Clean up
        Dialog.delete().where(Dialog.tenant_id == tenant_id).execute()
        Tenant.delete().where(Tenant.id == tenant_id).execute()
        SystemSettings.delete().where(SystemSettings.name == "plan.free.apps_limit").execute()


if __name__ == "__main__":
    unittest.main()
