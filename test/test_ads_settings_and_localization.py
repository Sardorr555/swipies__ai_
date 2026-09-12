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
from unittest.mock import MagicMock
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

TEST_DB_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_ads_settings_temp.db"))
test_db = SqliteDatabase(TEST_DB_FILE)

from api.db.db_models import (
    DB,
    Advertiser,
    AdvertiserNotificationSettings,
    AdSettings,
    User,
    Tenant,
)

# Override DB connection context with test_db
DB.connection_context = test_db.connection_context
DB.atomic = test_db.atomic
DB.transaction = test_db.transaction
DB.connect = test_db.connect
DB.close = test_db.close
DB.is_closed = test_db.is_closed
DB.execute_sql = test_db.execute_sql

# Bind models to test_db
MODELS = [
    Advertiser,
    AdvertiserNotificationSettings,
    AdSettings,
    User,
    Tenant,
]
for model in MODELS:
    model._meta.database = test_db

from api.db.services.ad_engine_service import (
    AdvertiserService,
    AdSettingsService,
    AdvertiserNotificationService,
)
from common.time_utils import current_timestamp


class TestAdsSettingsAndLocalization(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        test_db.connect()
        test_db.create_tables(MODELS, safe=True)

    @classmethod
    def tearDownClass(cls):
        test_db.drop_tables(MODELS, safe=True)
        test_db.close()
        if os.path.exists(TEST_DB_FILE):
            try:
                os.remove(TEST_DB_FILE)
            except Exception:
                pass

    def setUp(self):
        self.user_id = f"usr_{uuid.uuid4().hex[:12]}"
        self.tenant_id = f"tnt_{uuid.uuid4().hex[:12]}"
        self.user = User.create(
            id=self.user_id,
            email=f"{self.user_id}@example.com",
            nickname="Test Advertiser",
            create_time=current_timestamp(),
        )

    def tearDown(self):
        for model in MODELS:
            model.delete().execute()

    def test_advertiser_creation_and_defaults(self):
        adv = AdvertiserService.get_or_create_for_user(self.user_id, self.tenant_id)
        self.assertIsNotNone(adv)
        self.assertEqual(adv.user_id, self.user_id)
        self.assertEqual(adv.tenant_id, self.tenant_id)
        self.assertEqual(adv.currency, "USD")
        self.assertEqual(adv.status, "active")
        self.assertTrue(adv.pixel_id.startswith("px_"))

    def test_ad_settings_service_key_value_persistence(self):
        adv = AdvertiserService.get_or_create_for_user(self.user_id, self.tenant_id)
        key = f"adv_settings_{adv.id}"

        # Initially empty
        initial = AdSettingsService.get_setting(key, default_val={})
        self.assertEqual(initial, {})

        # Save preferences with multi-language
        payload = {
            "language": "uz",
            "default_regions": ["UZ", "KZ"],
            "default_models": ["gpt-4o", "deepseek-v3"],
            "daily_spend_ceiling": 750.0,
            "default_frequency_cap": 4,
            "auto_pause_low_ctr": True,
            "low_ctr_threshold": 0.8,
            "timezone": "Asia/Tashkent",
        }
        AdSettingsService.set_setting(key, payload, description=f"Settings for {adv.id}")

        # Retrieve and verify
        retrieved = AdSettingsService.get_setting(key)
        self.assertIsInstance(retrieved, dict)
        self.assertEqual(retrieved["language"], "uz")
        self.assertIn("UZ", retrieved["default_regions"])
        self.assertEqual(retrieved["daily_spend_ceiling"], 750.0)
        self.assertEqual(retrieved["default_frequency_cap"], 4)
        self.assertTrue(retrieved["auto_pause_low_ctr"])
        self.assertEqual(retrieved["low_ctr_threshold"], 0.8)
        self.assertEqual(retrieved["timezone"], "Asia/Tashkent")

    def test_multi_language_switching(self):
        adv = AdvertiserService.get_or_create_for_user(self.user_id, self.tenant_id)
        key = f"adv_settings_{adv.id}"

        # Support RU, EN, UZ
        for lang in ["ru", "en", "uz"]:
            AdSettingsService.set_setting(key, {"language": lang})
            prefs = AdSettingsService.get_setting(key)
            self.assertEqual(prefs.get("language"), lang)

    def test_advertiser_profile_update(self):
        adv = AdvertiserService.get_or_create_for_user(self.user_id, self.tenant_id)

        # Update profile fields
        adv.company_name = "Tech Innovations Tashkent"
        adv.contact_email = "business@techinnovations.uz"
        adv.website_url = "https://techinnovations.uz"
        adv.currency = "UZS"
        adv.save()

        refreshed = Advertiser.get_by_id(adv.id)
        self.assertEqual(refreshed.company_name, "Tech Innovations Tashkent")
        self.assertEqual(refreshed.contact_email, "business@techinnovations.uz")
        self.assertEqual(refreshed.website_url, "https://techinnovations.uz")
        self.assertEqual(refreshed.currency, "UZS")

    def test_advertiser_notification_settings(self):
        adv = AdvertiserService.get_or_create_for_user(self.user_id, self.tenant_id)
        notifs = AdvertiserNotificationService.get_or_create_settings(adv.id)
        self.assertIsNotNone(notifs)
        self.assertTrue(notifs["notify_low_balance"])

        # Update notifications
        updated = AdvertiserNotificationService.update_settings(
            adv.id,
            {
                "telegram_alerts_enabled": True,
                "telegram_chat_id": "998901234567",
                "email_alerts_enabled": True,
                "email_target": "alerts@mybrand.uz",
                "webhook_url": "https://mybrand.uz/webhook",
                "low_balance_threshold": 25.0,
            },
        )
        self.assertTrue(updated["telegram_alerts_enabled"])
        self.assertEqual(updated["telegram_chat_id"], "998901234567")
        self.assertEqual(updated["email_target"], "alerts@mybrand.uz")
        self.assertEqual(updated["webhook_url"], "https://mybrand.uz/webhook")
        self.assertEqual(updated["low_balance_threshold"], 25.0)

    def test_safety_spend_caps_and_frequency_cap_sanitization(self):
        adv = AdvertiserService.get_or_create_for_user(self.user_id, self.tenant_id)
        key = f"adv_settings_{adv.id}"

        # Test valid numbers
        AdSettingsService.set_setting(
            key,
            {
                "daily_spend_ceiling": 1000.0,
                "default_frequency_cap": 5,
                "auto_pause_low_ctr": False,
                "low_ctr_threshold": 0.3,
            },
        )
        data = AdSettingsService.get_setting(key)
        self.assertEqual(data["daily_spend_ceiling"], 1000.0)
        self.assertEqual(data["default_frequency_cap"], 5)
        self.assertFalse(data["auto_pause_low_ctr"])
        self.assertEqual(data["low_ctr_threshold"], 0.3)


if __name__ == "__main__":
    unittest.main()
