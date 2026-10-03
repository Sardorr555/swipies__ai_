#
#  Copyright 2025 The InfiniFlow Authors. All Rights Reserved.
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
import concurrent.futures
import os
import threading
import time
import unittest
import warnings
from typing import Any, Dict
from unittest.mock import MagicMock, patch

# Suppress version drift warnings
warnings.filterwarnings("ignore", message=".*doesn't match a supported version.*")
warnings.filterwarnings("ignore", category=ResourceWarning)

from peewee import SqliteDatabase

from api.db.db_models import DB
DB.connection_context = lambda: (lambda fn: fn)
DB.connect = lambda *a, **kw: True
DB.close = lambda *a, **kw: None
DB.is_closed = lambda: False

from api.db.crm_models import CRMConnection, CRMOutbox
from api.db.services.crm_service import CRMConnectionService
from api.crm.clients.amocrm import (
    AmoCRMClient,
    AmoCRMError,
    AmoCRMAuthError,
    AmoCRMTokenRevokedError,
    AmoCRMDomainError,
    is_valid_amocrm_domain,
    is_valid_amocrm_url,
    mask_phone_dynamic,
    mask_sensitive_payload,
)


class DummyResponse:
    """Mock response for CRMTransport."""
    def __init__(self, status_code: int = 200, json_data: Any = None, text: str = ""):
        self.status_code = status_code
        self._json_data = json_data
        self.text = text or (str(json_data) if json_data is not None else "")

    def json(self):
        if self._json_data is not None:
            return self._json_data
        raise ValueError("No JSON in response")


class TestAmoCRMV1(unittest.TestCase):
    def setUp(self):
        warnings.filterwarnings("ignore", message=".*doesn't match a supported version.*")
        warnings.filterwarnings("ignore", category=ResourceWarning)
        self.master_secret = "test-master-secret-key-32bytes-ok!"
        os.environ["RAGFLOW_SECRET_KEY"] = self.master_secret

        # Enforce thread-safe in-memory SQLite isolation (zero disk files)
        self.test_db = SqliteDatabase("file:crm_amocrm_mem?mode=memory&cache=shared", uri=True)
        self._orig_db_conn = CRMConnection._meta.database
        self._orig_db_outbox = CRMOutbox._meta.database
        self._orig_atomic = getattr(DB, "atomic", None)

        DB.connect = lambda *a, **kw: True
        DB.close = lambda *a, **kw: None
        DB.is_closed = lambda: False

        CRMConnection._meta.database = self.test_db
        CRMOutbox._meta.database = self.test_db
        DB.atomic = lambda *args, **kwargs: self.test_db.atomic()

        self.test_db.bind([CRMConnection, CRMOutbox])
        self.test_db.connect()
        self.test_db.create_tables([CRMConnection, CRMOutbox])

    def tearDown(self):
        CRMConnection._meta.database = self._orig_db_conn
        CRMOutbox._meta.database = self._orig_db_outbox
        if self._orig_atomic:
            DB.atomic = self._orig_atomic
        if hasattr(self, "_orig_connect"):
            DB.connect = self._orig_connect
        if hasattr(self, "_orig_close"):
            DB.close = self._orig_close
        if hasattr(self, "_orig_is_closed"):
            DB.is_closed = self._orig_is_closed
        if hasattr(self, "test_db") and not self.test_db.is_closed():
            self.test_db.close()

    # -------------------------------------------------------------------------
    # T3.2: Domain Boundary and URL Validation Tests
    # -------------------------------------------------------------------------
    def test_domain_boundary_allowlisting(self):
        """Verify strict domain boundary validation for amoCRM and Kommo."""
        # Valid domains
        valid_domains = [
            "amocrm.ru",
            "test.amocrm.ru",
            "sales-team.amocrm.ru",
            "sub.sub2.amocrm.ru",
            "company.amocrm.com",
            "app.kommo.com",
            "enterprise-crm.kommo.com",
        ]
        for d in valid_domains:
            self.assertTrue(is_valid_amocrm_domain(d), f"Domain '{d}' should be valid")

        # Invalid domains / lookalikes
        invalid_domains = [
            "evilamocrm.ru",                # lookalike prefix
            "amocrm.ru.evil.com",           # attacker domain as suffix
            "amocrm.com.attacker.org",      # attacker domain as suffix
            "kommo.com.phishing.net",       # attacker domain
            "evilkommo.com",                # lookalike
            "amocrm.org",                   # unsupported TLD
            "kommo.ru",                     # unsupported TLD
            "xn--amocrm-e1a.ru",            # punycode / IDN
            ".test.amocrm.ru",              # leading dot
            "test.amocrm.ru.",              # trailing dot
            "test..amocrm.ru",              # consecutive dots
            "test_domain.amocrm.ru",        # underscore in DNS label
        ]
        for d in invalid_domains:
            self.assertFalse(is_valid_amocrm_domain(d), f"Domain '{d}' should be rejected")

    def test_url_boundary_validation_scheme_port_userinfo(self):
        """Verify URL validation rejects HTTP, custom ports, and userinfo."""
        # Valid URLs
        ok, host = is_valid_amocrm_url("https://mycompany.amocrm.ru")
        self.assertTrue(ok)
        self.assertEqual(host, "mycompany.amocrm.ru")

        ok, host = is_valid_amocrm_url("https://client.kommo.com/api/v4")
        self.assertTrue(ok)
        self.assertEqual(host, "client.kommo.com")

        # Invalid: HTTP scheme
        ok, msg = is_valid_amocrm_url("http://mycompany.amocrm.ru")
        self.assertFalse(ok)
        self.assertIn("strictly requires 'https'", msg)

        # Invalid: Userinfo in URL
        ok, msg = is_valid_amocrm_url("https://user:password@mycompany.amocrm.ru")
        self.assertFalse(ok)
        self.assertIn("User credentials", msg)

        # Invalid: Custom port
        ok, msg = is_valid_amocrm_url("https://mycompany.amocrm.ru:8080")
        self.assertFalse(ok)
        self.assertIn("Custom port '8080' is forbidden", msg)

        # Invalid: Foreign domain
        ok, msg = is_valid_amocrm_url("https://evilamocrm.ru")
        self.assertFalse(ok)
        self.assertIn("does not match allowed amoCRM / Kommo domain boundaries", msg)

    # -------------------------------------------------------------------------
    # T3.7: Dynamic Phone Masking and Payload Sanitization
    # -------------------------------------------------------------------------
    def test_dynamic_phone_masking(self):
        """Universal dynamic length phone masking preserving prefix and last 2 digits."""
        test_cases = [
            ("+79991234567", "+79*******67"),
            ("+15551234567", "+15*******67"),
            ("+442071838750", "+44********50"),
            ("+998901234567", "+99********67"),
            ("+49170123456", "+49*******56"),
            ("88005553535", "88*******35"),
            ("1234", "****"),
        ]
        for raw, expected in test_cases:
            masked = mask_phone_dynamic(raw)
            self.assertEqual(masked, expected, f"Masking failed for {raw}: got {masked}, expected {expected}")

    def test_mask_sensitive_payload(self):
        """Mask credentials, tokens, secrets and phone numbers in nested structures."""
        data = {
            "access_token": "secret_access_abc123",
            "refresh_token": "secret_refresh_xyz789",
            "client_secret": "my_super_secret_key",
            "normal_field": "hello world",
            "user_info": {
                "phone": "+79991234567",
                "api_key": "api_key_confidential",
            },
            "contacts": [
                {"name": "Alice", "phone": "+15551234567"}
            ]
        }
        masked = mask_sensitive_payload(data)
        self.assertEqual(masked["access_token"], "********")
        self.assertEqual(masked["refresh_token"], "********")
        self.assertEqual(masked["client_secret"], "********")
        self.assertEqual(masked["normal_field"], "hello world")
        self.assertEqual(masked["user_info"]["phone"], "+79*******67")
        self.assertEqual(masked["user_info"]["api_key"], "********")
        self.assertEqual(masked["contacts"][0]["phone"], "+15*******67")

    # -------------------------------------------------------------------------
    # T3.1: Contact Search and Lead Creation
    # -------------------------------------------------------------------------
    def test_find_contact_existing_and_non_existing(self):
        """Verify find_contact handles 200 with data and 204 No Content."""
        mock_transport = MagicMock()
        client = AmoCRMClient(transport=mock_transport)

        config = {
            "subdomain": "testcompany",
            "zone": "amocrm.ru",
            "access_token": "valid_token_123",
        }

        # 1. Existing contact (HTTP 200)
        mock_transport.get.return_value = DummyResponse(
            status_code=200,
            json_data={"_embedded": {"contacts": [{"id": 101, "name": "Existing Client"}]}}
        )
        contact = client.find_contact(config, "+79991234567")
        self.assertIsNotNone(contact)
        self.assertEqual(contact["id"], 101)
        self.assertEqual(contact["name"], "Existing Client")

        # 2. Non-existing contact (HTTP 204 No Content)
        mock_transport.get.return_value = DummyResponse(status_code=204, text="")
        contact_none = client.find_contact(config, "+79997654321")
        self.assertIsNone(contact_none)

    def test_create_lead_full_flow(self):
        """Verify create_lead looks up contact, creates contact if missing, and creates lead with note."""
        mock_transport = MagicMock()
        client = AmoCRMClient(transport=mock_transport)

        config = {
            "subdomain": "testcompany",
            "zone": "amocrm.ru",
            "access_token": "valid_token_123",
            "pipeline_id": 555,
            "status_id": 777,
        }

        # Scenario: contact does not exist (204) -> create contact (201) -> create lead (201) -> add note (201)
        def mock_post(url, **kwargs):
            if "/api/v4/contacts" in url:
                return DummyResponse(status_code=201, json_data={"_embedded": {"contacts": [{"id": 202}]}})
            if "/api/v4/leads/" in url and "/notes" in url:
                return DummyResponse(status_code=201, json_data={"_embedded": {"notes": [{"id": 404}]}})
            if "/api/v4/leads" in url:
                return DummyResponse(status_code=201, json_data={"_embedded": {"leads": [{"id": 303}]}})
            return DummyResponse(status_code=404)

        mock_transport.get.return_value = DummyResponse(status_code=204)
        mock_transport.post.side_effect = mock_post

        result = client.create_lead(
            config,
            {
                "name": "Jane Doe",
                "phone": "+79991234567",
                "title": "Deal: Enterprise License",
                "price": 50000,
                "note": "Interested in 50 seats",
            }
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["lead_id"], "303")
        self.assertEqual(result["contact_id"], "202")
        self.assertEqual(result["crm_type"], "amocrm")

        # Verify stock check returns unsupported
        stock_res = client.check_stock(config, "ITEM-123")
        self.assertFalse(stock_res["supported"])

    def test_create_lead_price_pipeline_resilience(self):
        """Verify create_lead handles string prices, floats, and empty pipeline/status gracefully."""
        mock_transport = MagicMock()
        client = AmoCRMClient(transport=mock_transport)

        config = {
            "subdomain": "testcompany",
            "zone": "amocrm.ru",
            "access_token": "valid_token_123",
            "pipeline_id": "888",
            "status_id": "invalid_status_str",
        }

        created_lead_payload = []
        def mock_post(url, **kwargs):
            if "/api/v4/leads" in url and "/notes" not in url:
                created_lead_payload.extend(kwargs.get("json", []))
                return DummyResponse(status_code=201, json_data={"_embedded": {"leads": [{"id": 555}]}})
            if "/api/v4/contacts" in url:
                return DummyResponse(status_code=201, json_data={"_embedded": {"contacts": [{"id": 666}]}})
            return DummyResponse(status_code=200)

        mock_transport.get.return_value = DummyResponse(status_code=204)
        mock_transport.post.side_effect = mock_post

        result = client.create_lead(
            config,
            {
                "name": "Price Test",
                "phone": "+79991234567",
                "price": "1250.75",  # float as string
                "pipeline_id": "",     # empty string in lead_data
            }
        )
        self.assertEqual(result["status"], "success")
        self.assertEqual(created_lead_payload[0]["price"], 1250)
        self.assertEqual(created_lead_payload[0]["pipeline_id"], 888)
        self.assertNotIn("status_id", created_lead_payload[0])

    # -------------------------------------------------------------------------
    # T3.3 & T3.4 & T3.8: Distributed Lock & Double-Checked Read Concurrency
    # -------------------------------------------------------------------------
    def test_concurrent_refresh_exact_one_call_for_5_workers(self):
        """Verify that 5 concurrent workers attempting refresh execute exactly 1 external API call."""
        # Create connection in DB
        initial_config = {
            "subdomain": "testcompany",
            "zone": "amocrm.ru",
            "client_id": "client_id_123",
            "client_secret": "client_sec_123",
            "refresh_token": "initial_refresh_token_v1",
            "access_token": "expired_token",
            "access_token_expires_at": int(time.time()) - 100,  # expired
        }
        conn = CRMConnectionService.save_connection(
            tenant_id="tenant-alpha",
            name="Alpha amoCRM",
            crm_type="amocrm",
            config=initial_config,
        )

        mock_transport = MagicMock()
        api_call_count = 0
        call_lock = threading.Lock()

        def mock_post(url, **kwargs):
            nonlocal api_call_count
            with call_lock:
                api_call_count += 1
            # Simulate network latency of OAuth refresh
            time.sleep(0.05)
            return DummyResponse(
                status_code=200,
                json_data={
                    "access_token": "new_access_token_v2",
                    "refresh_token": "new_refresh_token_v2",
                    "token_type": "Bearer",
                    "expires_in": 86400,
                }
            )

        mock_transport.post.side_effect = mock_post
        client = AmoCRMClient(transport=mock_transport)

        # 5 workers simultaneously attempt refresh
        results = []
        errors = []

        def worker_task(worker_id: int):
            try:
                cfg = CRMConnectionService.get_decrypted_config(conn.id, "tenant-alpha")
                cfg["id"] = conn.id
                cfg["tenant_id"] = "tenant-alpha"
                refreshed = client.refresh_auth(cfg)
                return refreshed
            except Exception as e:
                return e
            finally:
                if not self.test_db.is_closed():
                    self.test_db.close()

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(worker_task, i) for i in range(5)]
            for f in concurrent.futures.as_completed(futures):
                res = f.result()
                if isinstance(res, Exception):
                    errors.append(res)
                else:
                    results.append(res)

        self.assertEqual(len(errors), 0, f"Workers encountered errors: {errors}")
        self.assertEqual(len(results), 5)
        # Verify exactly 1 external HTTP call was made across all 5 workers
        self.assertEqual(api_call_count, 1, f"Expected exactly 1 OAuth call, but got {api_call_count}")

        # Verify DB has been updated to v2
        ok, updated_conn = CRMConnectionService.get_by_id_and_tenant(conn.id, "tenant-alpha")
        self.assertTrue(ok)
        self.assertEqual(updated_conn.token_version, 2)
        fresh_config = CRMConnectionService.get_decrypted_config(updated_conn)
        self.assertEqual(fresh_config["access_token"], "new_access_token_v2")
        self.assertEqual(fresh_config["refresh_token"], "new_refresh_token_v2")

    # -------------------------------------------------------------------------
    # T3.5: Fencing Token CAS Validation
    # -------------------------------------------------------------------------
    def test_stale_worker_cas_fencing(self):
        """Verify that a stale worker with outdated token_version is fenced out and retrieves fresh config."""
        initial_config = {
            "subdomain": "testcompany",
            "zone": "amocrm.ru",
            "client_id": "client_id_123",
            "client_secret": "client_sec_123",
            "refresh_token": "token_v1",
        }
        conn = CRMConnectionService.save_connection(
            tenant_id="tenant-alpha",
            name="Alpha amoCRM",
            crm_type="amocrm",
            config=initial_config,
        )

        mock_transport = MagicMock()
        client = AmoCRMClient(transport=mock_transport)

        # Worker A reads version 1
        cfg_worker_a = CRMConnectionService.get_decrypted_config(conn.id, "tenant-alpha")
        cfg_worker_a["id"] = conn.id
        cfg_worker_a["tenant_id"] = "tenant-alpha"
        cfg_worker_a["token_version"] = 1

        # In the meantime, Worker B updates config to version 2
        cfg_worker_b = dict(cfg_worker_a)
        cfg_worker_b["access_token"] = "winner_worker_b_token"
        cas_b = CRMConnectionService.update_config(
            connection_id=conn.id,
            tenant_id="tenant-alpha",
            config=cfg_worker_b,
            expected_token_version=1,
        )
        self.assertTrue(cas_b)

        # Now Worker A tries to update using outdated version 1
        # Worker A should be fenced out by CAS (version mismatch)
        mock_transport.post.return_value = DummyResponse(
            status_code=200,
            json_data={"access_token": "stale_token", "refresh_token": "stale_refresh", "expires_in": 3600}
        )
        res_a = client.refresh_auth(cfg_worker_a)

        # Worker A received the winner's token (from Worker B)
        self.assertEqual(res_a["access_token"], "winner_worker_b_token")
        self.assertEqual(res_a["token_version"], 2)

    # -------------------------------------------------------------------------
    # T3.6: Recovery Read on invalid_grant / HTTP 400
    # -------------------------------------------------------------------------
    def test_invalid_grant_recovery_read_success_when_version_increased(self):
        """When refresh fails with invalid_grant, but version increased, worker recovers successfully."""
        initial_config = {
            "subdomain": "testcompany",
            "zone": "amocrm.ru",
            "client_id": "client_id_123",
            "client_secret": "client_sec_123",
            "refresh_token": "old_token",
            "access_token_expires_at": int(time.time()) - 10,
        }
        conn = CRMConnectionService.save_connection(
            tenant_id="tenant-alpha",
            name="Alpha amoCRM",
            crm_type="amocrm",
            config=initial_config,
        )

        mock_transport = MagicMock()
        client = AmoCRMClient(transport=mock_transport)

        # Worker A starts with read_version 1
        cfg_worker_a = CRMConnectionService.get_decrypted_config(conn.id, "tenant-alpha")
        cfg_worker_a["id"] = conn.id
        cfg_worker_a["tenant_id"] = "tenant-alpha"
        cfg_worker_a["token_version"] = 1

        # Simulate: Worker B refreshed first in DB to v2
        fresh_cfg = dict(cfg_worker_a)
        fresh_cfg["access_token"] = "refreshed_by_worker_b"
        CRMConnectionService.update_config(conn.id, "tenant-alpha", fresh_cfg, expected_token_version=1)

        # Worker A calls amoCRM and receives HTTP 400 (invalid_grant) because old_token was consumed
        mock_transport.post.return_value = DummyResponse(
            status_code=400,
            json_data={"error": "invalid_grant", "detail": "The refresh token is invalid."}
        )

        recovered = client.refresh_auth(cfg_worker_a)
        self.assertEqual(recovered["access_token"], "refreshed_by_worker_b")
        self.assertEqual(recovered["token_version"], 2)

    def test_invalid_grant_genuinely_revoked_transitions_to_reauth_required(self):
        """When refresh fails with invalid_grant and version is unchanged, connection transitions to reauth_required."""
        initial_config = {
            "subdomain": "testcompany",
            "zone": "amocrm.ru",
            "client_id": "client_id_123",
            "client_secret": "client_sec_123",
            "refresh_token": "revoked_token",
            "access_token_expires_at": int(time.time()) - 10,
        }
        conn = CRMConnectionService.save_connection(
            tenant_id="tenant-alpha",
            name="Alpha amoCRM",
            crm_type="amocrm",
            config=initial_config,
        )

        mock_transport = MagicMock()
        client = AmoCRMClient(transport=mock_transport)

        mock_transport.post.return_value = DummyResponse(
            status_code=400,
            json_data={"error": "invalid_grant", "detail": "The refresh token was revoked by user."}
        )

        cfg = CRMConnectionService.get_decrypted_config(conn.id, "tenant-alpha")
        cfg["id"] = conn.id
        cfg["tenant_id"] = "tenant-alpha"
        cfg["token_version"] = 1

        with self.assertRaises(AmoCRMTokenRevokedError):
            client.refresh_auth(cfg)

        # Verify DB connection status was changed to reauth_required
        ok, current_conn = CRMConnectionService.get_by_id_and_tenant(conn.id, "tenant-alpha")
        self.assertTrue(ok)
        self.assertEqual(current_conn.status, "reauth_required")


if __name__ == "__main__":
    unittest.main()
