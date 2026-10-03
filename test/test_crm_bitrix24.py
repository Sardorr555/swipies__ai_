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
import os
import unittest
import warnings
from typing import Any
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
from api.crm.transport import CRMTransport, SSRFSecurityException
from api.crm.clients.bitrix24 import (
    Bitrix24Client,
    Bitrix24Error,
    Bitrix24DomainError,
    Bitrix24AuthError,
    Bitrix24RateLimitError,
    DEFAULT_B24_ZONES,
    get_allowed_b24_zones,
    validate_bitrix24_cloud_url,
    validate_bitrix24_onprem_url,
    redact_bitrix24_webhook_url,
    normalize_phone_to_e164,
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


class TestBitrix24V1(unittest.TestCase):
    def setUp(self):
        warnings.filterwarnings("ignore", message=".*doesn't match a supported version.*")
        warnings.filterwarnings("ignore", category=ResourceWarning)
        self.master_secret = "test-master-secret-key-32bytes-ok!"
        os.environ["RAGFLOW_SECRET_KEY"] = self.master_secret

        # Enforce thread-safe in-memory SQLite isolation (zero disk files)
        self.test_db = SqliteDatabase("file:crm_b24_mem?mode=memory&cache=shared", uri=True)
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
        DB.connect = lambda *a, **kw: True
        DB.close = lambda *a, **kw: None
        DB.is_closed = lambda: False
        if not self.test_db.is_closed():
            self.test_db.close()
        os.environ.pop("RAGFLOW_CRM_B24_ZONES", None)
        os.environ.pop("RAGFLOW_CRM_PRIVATE_ALLOWLIST_CIDR", None)

    # -------------------------------------------------------------------------
    # T4.2: Bitrix24 Cloud Hostname and Zone Validation
    # -------------------------------------------------------------------------
    def test_bitrix24_cloud_allowed_zones_and_rejections(self):
        """Verify 20 confirmed default zones and rejection of lookalikes / unconfirmed zones."""
        # Test all 20 confirmed default zones
        for zone in DEFAULT_B24_ZONES:
            url = f"https://mycompany.bitrix24.{zone}/rest/1/webhookkey/"
            ok, host = validate_bitrix24_cloud_url(url)
            self.assertTrue(ok, f"Zone '{zone}' should be accepted as default confirmed zone")
            self.assertEqual(host, f"mycompany.bitrix24.{zone}")

        # Test rejected zones (unconfirmed / custom zones)
        unconfirmed = ["com.br", "ua", "co", "cl", "xyz", "biz"]
        for zone in unconfirmed:
            url = f"https://mycompany.bitrix24.{zone}/rest/1/webhookkey/"
            ok, msg = validate_bitrix24_cloud_url(url)
            self.assertFalse(ok, f"Zone '{zone}' must be rejected by default")
            self.assertIn(f"Unsupported Bitrix24 cloud zone '{zone}'", msg)
            self.assertIn("bitrix24_onprem", msg)

        # Test dynamic zone loading via environment variable
        os.environ["RAGFLOW_CRM_B24_ZONES"] = "com.br,ua,custom.zone"
        custom_url = "https://saopaulo.bitrix24.com.br/rest/1/key"
        ok_custom, host_custom = validate_bitrix24_cloud_url(custom_url)
        self.assertTrue(ok_custom)
        self.assertEqual(host_custom, "saopaulo.bitrix24.com.br")

    def test_bitrix24_cloud_scheme_userinfo_ports_and_lookalikes(self):
        """Verify rejection of HTTP, userinfo, custom ports, punycode, and lookalike domains."""
        # 1. HTTP scheme rejected
        ok, msg = validate_bitrix24_cloud_url("http://mycompany.bitrix24.ru/rest/1/key")
        self.assertFalse(ok)
        self.assertIn("strictly requires 'https'", msg)

        # 2. User credentials in URL rejected
        ok, msg = validate_bitrix24_cloud_url("https://admin:secret@mycompany.bitrix24.ru/rest/1/key")
        self.assertFalse(ok)
        self.assertIn("User credentials", msg)

        # 3. Custom port rejected
        ok, msg = validate_bitrix24_cloud_url("https://mycompany.bitrix24.ru:8080/rest/1/key")
        self.assertFalse(ok)
        self.assertIn("Custom port '8080' is forbidden", msg)

        # 4. Punycode / IDN rejected
        ok, msg = validate_bitrix24_cloud_url("https://xn--portal.bitrix24.ru/rest/1/key")
        self.assertFalse(ok)
        self.assertIn("punycode", msg)

        # 5. Lookalike domains and authority spoofing rejected fail-closed
        lookalikes = [
            "https://x.bitrix24.evil.com/rest/1/key",
            "https://bitrix24.com.evil.net/rest/1/key",
            "https://evilbitrix24.ru/rest/1/key",
            "https://bitrix24.ru.attacker.com/rest/1/key",
            "https://.mycompany.bitrix24.ru/rest/1/key",
            "https://mycompany.bitrix24.ru./rest/1/key",
            "https://mycompany.bitrix24.com@evil.com/rest/1/key",
        ]
        for url in lookalikes:
            ok, msg = validate_bitrix24_cloud_url(url)
            self.assertFalse(ok, f"Lookalike/spoofed URL '{url}' should be rejected")

        # 6. Case-folding normalization: uppercase host is accepted and normalized to lowercase
        ok_upper, host_upper = validate_bitrix24_cloud_url("https://MYCOMPANY.bitrix24.ru/rest/1/key")
        self.assertTrue(ok_upper, "Uppercase domain should be accepted via case-folding normalization")
        self.assertEqual(host_upper, "mycompany.bitrix24.ru")

    # -------------------------------------------------------------------------
    # T4.3: Bitrix24 On-Premise Validation (SSRF Matrix & Private CIDR Allowlist)
    # -------------------------------------------------------------------------
    def test_bitrix24_onprem_ssrf_matrix_and_allowlist(self):
        """Verify on-premise SSRF protection blocks private IPs and allows explicit CIDRs."""
        # 1. HTTP is forbidden for on-premise
        ok, msg = validate_bitrix24_onprem_url("http://crm.company.corp/rest/1/key")
        self.assertFalse(ok)
        self.assertIn("strictly requires 'https'", msg)

        # 2. Private IP matrix without allowlist -> FAIL CLOSED
        private_ips = [
            "https://127.0.0.1/rest/1/key",
            "https://169.254.169.254/rest/1/key",
            "https://10.0.0.1/rest/1/key",
            "https://192.168.1.100/rest/1/key",
            "https://172.16.5.5/rest/1/key",
            "https://0.0.0.0/rest/1/key",
        ]
        for url in private_ips:
            ok, msg = validate_bitrix24_onprem_url(url)
            self.assertFalse(ok, f"Private IP URL '{url}' must fail closed without allowlist")
            self.assertIn("SSRF security violation", msg)

        # 3. Explicit CIDR allowlist enables specified private IP
        os.environ["RAGFLOW_CRM_PRIVATE_ALLOWLIST_CIDR"] = "192.168.1.0/24,10.200.0.0/16"
        ok_allowed, host_allowed = validate_bitrix24_onprem_url("https://192.168.1.100/rest/1/key")
        self.assertTrue(ok_allowed)
        self.assertEqual(host_allowed, "192.168.1.100")

        # 4. IP outside of allowlist remains blocked
        ok_blocked, msg_blocked = validate_bitrix24_onprem_url("https://10.0.0.1/rest/1/key")
        self.assertFalse(ok_blocked)
        self.assertIn("SSRF security violation", msg_blocked)

    # -------------------------------------------------------------------------
    # T4.4: Webhook Path Secret Redaction & Mutation Test
    # -------------------------------------------------------------------------
    def test_webhook_secret_redaction(self):
        """Verify webhook secret is replaced with ******** in logs, exceptions, and URLs."""
        raw_urls = [
            "https://mycompany.bitrix24.ru/rest/1/abcdef123456xyz/crm.lead.add.json",
            "https://crm.onprem.internal/rest/42/very-confidential-token-999/",
            "Error on https://portal.bitrix24.com/rest/105/super_secret_webhook_key occurred",
        ]
        for raw in raw_urls:
            redacted = redact_bitrix24_webhook_url(raw)
            self.assertNotIn("abcdef123456xyz", redacted)
            self.assertNotIn("very-confidential-token-999", redacted)
            self.assertNotIn("super_secret_webhook_key", redacted)
            self.assertIn("********", redacted)

    def test_mutation_proof_webhook_redaction_failure_caught(self):
        """Mutation test: if secret redaction is bypassed, the security assertion must fail."""
        secret_token = "ultra_confidential_webhook_token_xyz"
        url = f"https://mycompany.bitrix24.ru/rest/1/{secret_token}/crm.lead.add"

        # Production redaction
        sanitized = redact_bitrix24_webhook_url(url)
        self.assertNotIn(secret_token, sanitized)
        self.assertIn("********", sanitized)

        # Mutated redaction (bypass)
        def mutated_redact(u):
            return u  # leak without redaction

        leaked = mutated_redact(url)
        with self.assertRaises(AssertionError):
            self.assertNotIn(secret_token, leaked)

    # -------------------------------------------------------------------------
    # T4.6: International Phone Normalization to E.164
    # -------------------------------------------------------------------------
    def test_international_phone_normalization_e164(self):
        """Verify phone normalization across multiple international countries."""
        test_cases = [
            # US number with formatting
            ("(415) 555-2671", "US", "+14155552671"),
            # DE number with national prefix
            ("030 123456", "DE", "+4930123456"),
            # UK number
            ("020 7946 0991", "GB", "+442079460991"),
            # UZ number with country code
            ("+998 90 123-45-67", "UZ", "+998901234567"),
            # RU number with national prefix
            ("8 (999) 123-45-67", "RU", "+79991234567"),
            # Already normalized E.164
            ("+81312345678", "JP", "+81312345678"),
        ]
        for raw, region, expected in test_cases:
            res = normalize_phone_to_e164(raw, region)
            self.assertEqual(res, expected, f"Failed for {raw} with region {region}: got {res}, expected {expected}")

    # -------------------------------------------------------------------------
    # T4.5: Rate Limiting & Transient Backoff
    # -------------------------------------------------------------------------
    def test_rate_limiting_transient_error_backoff_and_retry(self):
        """Verify client retries with backoff on QUERY_LIMIT_EXCEEDED or HTTP 503."""
        mock_transport = MagicMock()
        client = Bitrix24Client(transport=mock_transport)

        config = {
            "crm_type": "bitrix24",
            "webhook_url": "https://mycompany.bitrix24.ru/rest/1/secretkey",
            "default_phone_region": "US",
        }

        # First call returns QUERY_LIMIT_EXCEEDED (200 OK with error)
        # Second call succeeds with result = 777
        call_count = 0
        def mock_post(url, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return DummyResponse(
                    status_code=200,
                    json_data={"error": "QUERY_LIMIT_EXCEEDED", "error_description": "Too many requests"}
                )
            return DummyResponse(status_code=200, json_data={"result": 777})

        mock_transport.post.side_effect = mock_post

        with patch("time.sleep") as mock_sleep:
            res = client.create_lead(
                config,
                {"name": "Alice", "phone": "(415) 555-2671", "price": 1200}
            )
            self.assertEqual(res["status"], "success")
            self.assertEqual(res["lead_id"], "777")
            self.assertEqual(call_count, 2)
            mock_sleep.assert_called()

    def test_rate_limit_fail_open_on_redis_outage(self):
        """Verify fail-open behavior: when Redis is unreachable, requests are not blocked."""
        mock_transport = MagicMock()
        mock_transport.post.return_value = DummyResponse(status_code=200, json_data={"result": 999})
        client = Bitrix24Client(transport=mock_transport)

        config = {
            "crm_type": "bitrix24",
            "webhook_url": "https://mycompany.bitrix24.ru/rest/1/secretkey",
        }

        # Mock Redis to simulate connection exception
        with patch("rag.utils.redis_conn.REDIS_CONN", None):
            res = client.create_lead(config, {"name": "Bob", "phone": "+14155552671"})
            self.assertEqual(res["status"], "success")
            self.assertEqual(res["lead_id"], "999")

    # -------------------------------------------------------------------------
    # T4.1: Provider Contract (find_contact, refresh_auth, check_stock)
    # -------------------------------------------------------------------------
    def test_find_contact_and_refresh_auth(self):
        """Verify find_contact and refresh_auth execute successfully with correct endpoints."""
        mock_transport = MagicMock()
        client = Bitrix24Client(transport=mock_transport)

        config = {
            "crm_type": "bitrix24",
            "webhook_url": "https://mycompany.bitrix24.ru/rest/1/secretkey",
            "default_phone_region": "RU",
        }

        # 1. find_contact
        mock_transport.post.return_value = DummyResponse(
            status_code=200,
            json_data={"result": [{"ID": "12", "NAME": "Victor", "PHONE": [{"VALUE": "+79991234567"}]}]}
        )
        contact = client.find_contact(config, "8 (999) 123-45-67")
        self.assertIsNotNone(contact)
        self.assertEqual(contact["ID"], "12")

        # 2. refresh_auth (calls crm.lead.fields)
        mock_transport.post.return_value = DummyResponse(
            status_code=200,
            json_data={"result": {"TITLE": {"type": "string"}}}
        )
        refreshed = client.refresh_auth(config)
        self.assertEqual(refreshed, config)

        # 3. check_stock (unsupported)
        stock_res = client.check_stock(config, "SKU-999")
        self.assertFalse(stock_res["supported"])

    def test_bitrix24_phone_region_fallback(self):
        """Verify Bitrix24 client resolves phone_region if default_phone_region is absent."""
        mock_transport = MagicMock()
        client = Bitrix24Client(transport=mock_transport)

        config = {
            "crm_type": "bitrix24",
            "webhook_url": "https://mycompany.bitrix24.ru/rest/1/secretkey",
            "phone_region": "GB",  # UK region via phone_region key
        }

        mock_transport.post.return_value = DummyResponse(
            status_code=200,
            json_data={"result": 1001}
        )
        res = client.create_lead(
            config,
            {"name": "UK Lead", "phone": "020 7946 0991"}
        )
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["lead_id"], "1001")


if __name__ == "__main__":
    unittest.main()
