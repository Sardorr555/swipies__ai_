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
from datetime import datetime
from peewee import SqliteDatabase

warnings.filterwarnings("ignore", message=".*doesn't match a supported version.*")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Global test DB
test_db = SqliteDatabase(":memory:")

from api.db.db_models import DB
DB.connection_context = lambda: (lambda fn: fn)
DB.connect = lambda *a, **kw: True
DB.close = lambda *a, **kw: None
DB.is_closed = lambda: False
DB.atomic = lambda *args, **kwargs: test_db.atomic()

from api.db.db_models import User
from api.db.telemetry_models import UserActivityEvent
from api.db.services.telemetry_service import TelemetryService


class TestUserActivityTelemetry(unittest.TestCase):
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

    def test_01_sanitization_strips_sensitive_data(self):
        """Verify that password, secrets, and auth headers are completely stripped from metadata."""
        dirty_meta = {
            "browser": "Chrome 128",
            "screen_width": 1920,
            "password": "my_super_secret_password_123",
            "bearer_token": "eyJh...fake_token",
            "api_key": "sk-12345678",
            "normal_prop": "search_button_click",
        }
        clean = TelemetryService.sanitize_metadata(dirty_meta)
        self.assertIn("browser", clean)
        self.assertIn("screen_width", clean)
        self.assertIn("normal_prop", clean)
        self.assertNotIn("password", clean)
        self.assertNotIn("bearer_token", clean)
        self.assertNotIn("api_key", clean)

    def test_02_record_batch_events_and_overview(self):
        """Test recording a batch of events and aggregating overview metrics."""
        events = [
            {
                "session_id": "sess_001",
                "event_type": "page_view",
                "module": "chat",
                "page_route": "/chats",
                "action_category": "navigation",
                "action_name": "view_chat",
                "duration_seconds": 45.0,
            },
            {
                "session_id": "sess_001",
                "event_type": "click",
                "module": "chat",
                "page_route": "/chats",
                "action_category": "interaction",
                "action_name": "send_chat_message",
                "element_tag": "button",
                "element_id": "btn-send-message",
                "element_label": "Yuborish (Send)",
                "duration_seconds": 1.5,
            },
            {
                "session_id": "sess_001",
                "event_type": "page_view",
                "module": "datasets",
                "page_route": "/datasets",
                "action_category": "navigation",
                "action_name": "view_datasets",
                "duration_seconds": 120.0,
            },
            {
                "session_id": "sess_002",
                "event_type": "click",
                "module": "datasets",
                "page_route": "/dataset/files",
                "action_category": "interaction",
                "action_name": "upload_file",
                "element_tag": "button",
                "element_id": "btn-upload-file",
                "element_label": "Fayl Yuklash",
                "duration_seconds": 5.0,
            },
        ]

        inserted = TelemetryService.record_batch_events(
            events=events,
            user_id="user_test_101",
            tenant_id="tenant_test_101",
            ip="192.168.1.50",
            user_agent="Mozilla/5.0 Test",
        )
        self.assertEqual(inserted, 4)

        overview = TelemetryService.get_overview(days=7)
        self.assertEqual(overview["total_actions"], 4)
        self.assertEqual(overview["total_clicks"], 2)
        self.assertEqual(overview["total_page_views"], 2)
        self.assertEqual(overview["dau"], 1)
        self.assertEqual(overview["active_users_period"], 1)
        self.assertAlmostEqual(overview["total_time_spent_seconds"], 171.5, places=1)
        self.assertEqual(overview["top_module"], "datasets")

    def test_03_module_breakdown(self):
        """Test calculation of visits, dwell time, and attention share across modules."""
        events_chat = [
            {"session_id": "s1", "event_type": "page_view", "module": "chat", "page_route": "/chats", "duration_seconds": 100.0},
            {"session_id": "s1", "event_type": "click", "module": "chat", "page_route": "/chats", "element_label": "Send", "duration_seconds": 0.0},
        ]
        events_agent = [
            {"session_id": "s2", "event_type": "page_view", "module": "agent_canvas", "page_route": "/agents", "duration_seconds": 300.0},
        ]
        TelemetryService.record_batch_events(events_chat, user_id="u1")
        TelemetryService.record_batch_events(events_agent, user_id="u2")

        breakdown = TelemetryService.get_module_breakdown(days=7)
        modules_map = {b["module"]: b for b in breakdown}

        self.assertIn("agent_canvas", modules_map)
        self.assertIn("chat", modules_map)
        self.assertEqual(modules_map["agent_canvas"]["total_time_seconds"], 300.0)
        self.assertEqual(modules_map["chat"]["total_time_seconds"], 100.0)
        self.assertEqual(modules_map["chat"]["clicks"], 1)
        self.assertEqual(modules_map["chat"]["page_views"], 1)
        self.assertGreater(modules_map["agent_canvas"]["share_percentage"], 50.0)

    def test_04_top_clicks_ranking(self):
        """Test ranking of most clicked buttons and UI controls."""
        events = [
            {"session_id": "s1", "event_type": "click", "module": "chat", "element_label": "Qayta yaratish", "element_id": "btn-regen"},
            {"session_id": "s2", "event_type": "click", "module": "chat", "element_label": "Qayta yaratish", "element_id": "btn-regen"},
            {"session_id": "s3", "event_type": "click", "module": "chat", "element_label": "Qayta yaratish", "element_id": "btn-regen"},
            {"session_id": "s1", "event_type": "click", "module": "crm", "element_label": "1C Sinxronizatsiya", "element_id": "btn-sync-1c"},
        ]
        TelemetryService.record_batch_events(events, user_id="u_clicker")

        top_clicks = TelemetryService.get_top_clicks(days=7, limit=10)
        self.assertTrue(len(top_clicks) >= 2)
        first = top_clicks[0]
        self.assertEqual(first["label"], "Qayta yaratish")
        self.assertEqual(first["click_count"], 3)
        self.assertEqual(first["element_id"], "btn-regen")

    def test_05_hourly_timeline(self):
        """Test 24-hour activity distribution calculation."""
        events = [
            {"session_id": "s1", "event_type": "click", "module": "search", "duration_seconds": 10.0},
        ]
        TelemetryService.record_batch_events(events, user_id="u_hourly")
        timeline = TelemetryService.get_hourly_activity_timeline(days=7)
        self.assertEqual(len(timeline), 24)
        current_hour = datetime.now().hour
        self.assertGreaterEqual(timeline[current_hour]["actions"], 1)

    def test_features_usage_matrix(self):
        events = [
            {
                "session_id": "s_f1",
                "event_type": "action",
                "module": "chat",
                "action_category": "feature_usage",
                "action_name": "AI Chat Xabar Generatsiyasi",
                "element_id": "/v1/conversation/completion",
            },
            {
                "session_id": "s_f2",
                "event_type": "action",
                "module": "chat",
                "action_category": "feature_usage",
                "action_name": "AI Chat Xabar Generatsiyasi",
                "element_id": "/v1/conversation/completion",
            },
            {
                "session_id": "s_f3",
                "event_type": "action",
                "module": "datasets",
                "action_category": "feature_usage",
                "action_name": "Hujjat Yuklash (Upload)",
                "element_id": "/v1/document/upload",
            },
        ]
        TelemetryService.record_batch_events(events, user_id="u_feat")
        features = TelemetryService.get_features_usage_matrix(days=7)
        self.assertGreaterEqual(len(features), 2)
        top_feature = features[0]
        self.assertEqual(top_feature["feature_name"], "AI Chat Xabar Generatsiyasi")
        self.assertEqual(top_feature["invocations"], 2)


if __name__ == "__main__":
    unittest.main()

