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
import unittest
import warnings
from peewee import SqliteDatabase

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Isolated test DB
test_db = SqliteDatabase(":memory:")

from api.db.db_models import DB
DB.connection_context = lambda: (lambda fn: fn)
DB.connect = lambda *a, **kw: True
DB.close = lambda *a, **kw: None
DB.is_closed = lambda: False
DB.atomic = lambda *args, **kwargs: test_db.atomic()

from api.db.db_models import User
from api.db.telemetry_models import UserActivityEvent


class TestUtmCampaignAttribution(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        UserActivityEvent._meta.database = test_db
        User._meta.database = test_db
        test_db.bind([UserActivityEvent, User])
        test_db.connect()
        test_db.create_tables([UserActivityEvent, User], safe=True)

    def setUp(self):
        UserActivityEvent.delete().execute()
        User.delete().execute()

    def test_01_user_model_has_utm_and_visitor_fields(self):
        """Verify User model stores visitor_id, session_id and all 5 UTM parameters."""
        u = User.create(
            id="usr_test_utm_1",
            email="lead1@swipies.app",
            nickname="LeadOne",
            password="hashed_password",
            visitor_id="v_landing_98765",
            session_id="s_landing_54321",
            utm_source="telegram",
            utm_medium="channel",
            utm_campaign="spring_rag_2026",
            utm_term="ai_search",
            utm_content="top_cta",
            is_active="1"
        )
        self.assertIsNotNone(u)
        fetched = User.get_by_id("usr_test_utm_1")
        self.assertEqual(fetched.visitor_id, "v_landing_98765")
        self.assertEqual(fetched.session_id, "s_landing_54321")
        self.assertEqual(fetched.utm_source, "telegram")
        self.assertEqual(fetched.utm_medium, "channel")
        self.assertEqual(fetched.utm_campaign, "spring_rag_2026")
        self.assertEqual(fetched.utm_term, "ai_search")
        self.assertEqual(fetched.utm_content, "top_cta")

    def test_02_utm_conversions_aggregation(self):
        """Verify grouping of registered users across UTM campaigns for admin analytics."""
        # Create 2 users from campaign A
        User.create(
            id="usr_a1", email="a1@fintech.uz", nickname="UserA1",
            utm_source="telegram", utm_medium="channel", utm_campaign="spring_rag_2026", is_active="1"
        )
        User.create(
            id="usr_a2", email="a2@fintech.uz", nickname="UserA2",
            utm_source="telegram", utm_medium="channel", utm_campaign="spring_rag_2026", is_active="1"
        )
        # Create 1 user from campaign B
        User.create(
            id="usr_b1", email="b1@bank.uz", nickname="UserB1",
            utm_source="google", utm_medium="cpc", utm_campaign="enterprise_search", is_active="1"
        )

        users = list(User.select().where(
            (User.utm_source.is_null(False) & (User.utm_source != "")) |
            (User.utm_campaign.is_null(False) & (User.utm_campaign != ""))
        ).dicts())

        campaigns = {}
        for u in users:
            src = (u.get("utm_source") or "direct").strip()
            med = (u.get("utm_medium") or "none").strip()
            cmp = (u.get("utm_campaign") or "unnamed").strip()
            key = f"{src.lower()}::{med.lower()}::{cmp.lower()}"
            if key not in campaigns:
                campaigns[key] = {
                    "source": src,
                    "medium": med,
                    "campaign": cmp,
                    "registrations": 0,
                    "users": []
                }
            campaigns[key]["registrations"] += 1
            campaigns[key]["users"].append(u["email"])

        self.assertEqual(len(campaigns), 2)
        tg_key = "telegram::channel::spring_rag_2026"
        self.assertIn(tg_key, campaigns)
        self.assertEqual(campaigns[tg_key]["registrations"], 2)
        self.assertIn("a1@fintech.uz", campaigns[tg_key]["users"])
        self.assertIn("a2@fintech.uz", campaigns[tg_key]["users"])

        google_key = "google::cpc::enterprise_search"
        self.assertIn(google_key, campaigns)
        self.assertEqual(campaigns[google_key]["registrations"], 1)

    def test_03_telemetry_event_logging(self):
        """Verify UserActivityEvent can record the registration action with full UTM metadata."""
        event = UserActivityEvent.create_event(
            user_id="usr_reg_01",
            session_id="s_telemetry_123",
            event_type="action",
            module="auth",
            page_route="/register",
            action_category="account",
            action_name="user_registered",
            metadata={
                "email": "telemetry_test@swipies.app",
                "utm_source": "yandex",
                "utm_campaign": "direct_search",
                "visitor_id": "v_test_777"
            }
        )
        self.assertIsNotNone(event)
        self.assertEqual(event.event_type, "action")
        self.assertEqual(event.module, "auth")
        self.assertEqual(event.metadata.get("utm_source"), "yandex")
        self.assertEqual(event.metadata.get("visitor_id"), "v_test_777")


if __name__ == '__main__':
    unittest.main()
