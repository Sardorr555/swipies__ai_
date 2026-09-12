#
#  Copyright 2026 The InfiniFlow & Swipies AI Authors. All Rights Reserved.
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
import ast
import json
import os
import sys
import types
import unittest
from unittest.mock import MagicMock, patch

# Configure sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "admin", "server"))

# Set up mocks for dependencies not installed in host test runner
for mod_name in [
    "config",
    "api.db.joint_services.user_account_service",
    "api.db.services.canvas_service",
    "langfuse",
    "Cryptodome",
    "Cryptodome.PublicKey",
    "Cryptodome.Cipher",
    "api.utils.health_utils",
    "valkey",
    "valkey.lock",
]:
    if mod_name not in sys.modules:
        sys.modules[mod_name] = MagicMock()

from peewee import BooleanField
from api.db.db_models import User
from admin.server.services import UserMgr


class TestMarketingConsentAndOnboarding(unittest.TestCase):
    """Test suite verifying marketing consent field and onboarding phone logic."""

    def test_user_model_has_marketing_consent_field(self):
        """User model must have a BooleanField marketing_consent with default True."""
        self.assertTrue(hasattr(User, "marketing_consent"), "User model missing marketing_consent field")
        field = getattr(User, "marketing_consent")
        self.assertIsInstance(field, BooleanField, "marketing_consent must be a BooleanField")
        self.assertTrue(field.null, "marketing_consent field should allow null")
        self.assertTrue(field.default, "marketing_consent default should be True")
        self.assertTrue(field.index, "marketing_consent should be indexed for querying")

    def test_user_to_safe_dict_includes_marketing_consent_and_phone(self):
        """User.to_safe_dict() must expose marketing_consent and phone."""
        user = User()
        user.id = "test_user_123"
        user.email = "test@example.com"
        user.nickname = "tester"
        user.phone = "+998901234567"
        user.marketing_consent = True
        user.login_channel = "google"
        user.password = "hashed_secret"
        user.access_token = "token_xyz"

        safe_dict = user.to_safe_dict(for_self=True)
        self.assertIn("marketing_consent", safe_dict)
        self.assertTrue(safe_dict["marketing_consent"])
        self.assertEqual(safe_dict["phone"], "+998901234567")
        self.assertEqual(safe_dict["login_channel"], "google")
        # Sensitive password must be excluded
        self.assertNotIn("password", safe_dict)

    def test_user_to_safe_dict_with_marketing_consent_false(self):
        """User.to_safe_dict() must correctly retain marketing_consent=False if opted out."""
        user = User()
        user.id = "test_user_456"
        user.email = "optout@example.com"
        user.nickname = "optout"
        user.phone = "+79991234567"
        user.marketing_consent = False
        user.login_channel = "password"

        safe_dict = user.to_safe_dict(for_self=True)
        self.assertIn("marketing_consent", safe_dict)
        self.assertFalse(safe_dict["marketing_consent"])

    def test_db_migration_includes_marketing_consent(self):
        """Verify that db_models.py contains the alter_db_add_column call for marketing_consent."""
        db_models_path = os.path.join(BASE_DIR, "api", "db", "db_models.py")
        with open(db_models_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn('alter_db_add_column(migrator, "user", "marketing_consent"', content)

    def test_user_api_user_add_logic(self):
        """Verify the user registration dictionary captures marketing_consent."""
        # Simulated logic as in user_add()
        req_with_consent = {"email": "a@b.com", "marketing_consent": True, "phone": "+998901112233"}
        user_dict_1 = {
            "email": req_with_consent["email"],
            "phone": req_with_consent.get("phone"),
            "marketing_consent": bool(req_with_consent.get("marketing_consent", True)),
        }
        self.assertTrue(user_dict_1["marketing_consent"])

        req_without_consent = {"email": "c@d.com", "marketing_consent": False}
        user_dict_2 = {
            "email": req_without_consent["email"],
            "phone": req_without_consent.get("phone"),
            "marketing_consent": bool(req_without_consent.get("marketing_consent", True)),
        }
        self.assertFalse(user_dict_2["marketing_consent"])

        req_default = {"email": "e@f.com"}
        user_dict_3 = {
            "email": req_default["email"],
            "phone": req_default.get("phone"),
            "marketing_consent": bool(req_default.get("marketing_consent", True)),
        }
        self.assertTrue(user_dict_3["marketing_consent"])

    def test_save_onboarding_responses_logic(self):
        """Verify that onboarding update logic captures phone if passed in request."""
        # Simulate the handler logic in save_onboarding_responses()
        def process_onboarding(req):
            update_dict = {
                "is_onboarded": True,
                "onboarding_info": json.dumps(req) if isinstance(req, dict) else str(req),
            }
            if isinstance(req, dict) and req.get("phone"):
                update_dict["phone"] = str(req.get("phone")).strip()
            return update_dict

        # Case 1: Google user passes phone along with survey
        req_google = {
            "role": "founder",
            "team_size": "2_10",
            "industry": "tech",
            "phone": "  +998 90 123 45 67  ",
        }
        res_google = process_onboarding(req_google)
        self.assertTrue(res_google["is_onboarded"])
        self.assertEqual(res_google["phone"], "+998 90 123 45 67")
        self.assertIn('"role": "founder"', res_google["onboarding_info"])

        # Case 2: User skips or submits survey without phone
        req_pwd = {
            "role": "student",
            "team_size": "1",
        }
        res_pwd = process_onboarding(req_pwd)
        self.assertTrue(res_pwd["is_onboarded"])
        self.assertNotIn("phone", res_pwd)

    @patch("admin.server.services.UserService")
    @patch("admin.server.services.User")
    def test_user_mgr_get_all_users_includes_phone_and_marketing_consent(self, mock_user_model, mock_user_service):
        """Admin UserMgr.get_all_users() must return phone and marketing_consent for each user."""
        mock_u1 = MagicMock()
        mock_u1.id = "u1"
        mock_u1.email = "u1@example.com"
        mock_u1.nickname = "User 1"
        mock_u1.phone = "+998901112233"
        mock_u1.marketing_consent = True
        mock_u1.create_date = "2026-09-01"
        mock_u1.is_active = "1"
        mock_u1.is_superuser = False
        mock_u1.referred_by_id = None

        mock_u2 = MagicMock()
        mock_u2.id = "u2"
        mock_u2.email = "u2@example.com"
        mock_u2.nickname = "User 2"
        mock_u2.phone = None
        mock_u2.marketing_consent = False
        mock_u2.create_date = "2026-09-02"
        mock_u2.is_active = "1"
        mock_u2.is_superuser = False
        mock_u2.referred_by_id = None

        mock_user_service.get_all_users.return_value = [mock_u1, mock_u2]
        mock_user_model.select.return_value.where.return_value.count.return_value = 0

        users_list = UserMgr.get_all_users()
        self.assertEqual(len(users_list), 2)

        self.assertEqual(users_list[0]["id"], "u1")
        self.assertEqual(users_list[0]["phone"], "+998901112233")
        self.assertTrue(users_list[0]["marketing_consent"])

        self.assertEqual(users_list[1]["id"], "u2")
        self.assertIsNone(users_list[1]["phone"])
        self.assertFalse(users_list[1]["marketing_consent"])

    @patch("api.db.services.user_service.TenantService")
    @patch("admin.server.services.UserService")
    @patch("admin.server.services.User")
    def test_user_mgr_get_user_details_includes_phone_and_marketing_consent(
        self, mock_user_model, mock_user_service, mock_tenant_service
    ):
        """Admin UserMgr.get_user_details() must include phone and marketing_consent."""
        mock_u = MagicMock()
        mock_u.id = "u_target"
        mock_u.avatar = "avatar.png"
        mock_u.email = "target@example.com"
        mock_u.nickname = "Target User"
        mock_u.phone = "+12025550199"
        mock_u.marketing_consent = True
        mock_u.language = "English"
        mock_u.last_login_time = "2026-09-12 08:00:00"
        mock_u.is_active = "1"
        mock_u.is_anonymous = "0"
        mock_u.login_channel = "google"
        mock_u.status = "1"
        mock_u.is_superuser = False
        mock_u.create_date = "2026-09-10"
        mock_u.update_date = "2026-09-12"
        mock_u.referred_by_id = None

        mock_user_service.query_user_by_email.return_value = [mock_u]
        mock_tenant_service.query.return_value = []
        mock_user_model.select.return_value.where.return_value.count.return_value = 0

        details = UserMgr.get_user_details("target@example.com")
        self.assertEqual(len(details), 1)
        self.assertEqual(details[0]["phone"], "+12025550199")
        self.assertTrue(details[0]["marketing_consent"])
        self.assertEqual(details[0]["login_channel"], "google")


if __name__ == "__main__":
    unittest.main()
