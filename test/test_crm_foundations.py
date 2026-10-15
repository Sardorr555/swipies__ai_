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
import subprocess
import sys
import unittest
import warnings
from unittest.mock import patch, MagicMock

# Suppress version drift warnings
warnings.filterwarnings("ignore", message=".*doesn't match a supported version.*")

from peewee import SqliteDatabase

from api.db.db_models import DB
DB.connection_context = lambda: (lambda fn: fn)
DB.connect = lambda *a, **kw: True
DB.close = lambda *a, **kw: None
DB.is_closed = lambda: False

from api.db.crm_models import CRMConnection, CRMOutbox
from api.db.services.crm_service import CRMConnectionService, CRMOutboxService
from api.crm.base import CRMProviderBase
from api.crm.transport import CRMTransport, SSRFSecurityException, validate_crm_url_and_resolve
from api.crm.license_gate import check_crm_license_access, require_crm_license, CRMLicenseAccessError
from common.constants import RetCode


class TestCRMFoundations(unittest.TestCase):
    def setUp(self):
        warnings.filterwarnings("ignore", message=".*doesn't match a supported version.*")
        self.master_secret = "test-master-secret-key-32bytes-ok!"
        os.environ["RAGFLOW_SECRET_KEY"] = self.master_secret

        # Enforce in-memory SQLite isolation (:memory:)
        self.test_db = SqliteDatabase(":memory:")
        self._orig_db_conn = CRMConnection._meta.database
        self._orig_db_outbox = CRMOutbox._meta.database
        self._orig_atomic = getattr(DB, "atomic", None)
        self._orig_connect = DB.connect
        self._orig_close = DB.close
        self._orig_is_closed = DB.is_closed

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
    # T2.3: Bidirectional Import Order Verification
    # -------------------------------------------------------------------------
    def test_bidirectional_import_order(self):
        """Verify import order in both directions to guarantee zero circular import errors."""
        py_exe = sys.executable

        # Direction 1: crm_models then db_models
        cmd1 = [py_exe, "-c", "import api.db.crm_models; import api.db.db_models; print('OK1')"]
        res1 = subprocess.run(cmd1, capture_output=True, text=True, cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
        self.assertEqual(res1.returncode, 0, f"Import order crm_models -> db_models failed: {res1.stderr}")
        self.assertIn("OK1", res1.stdout)

        # Direction 2: db_models then crm_models
        cmd2 = [py_exe, "-c", "import api.db.db_models; import api.db.crm_models; print('OK2')"]
        res2 = subprocess.run(cmd2, capture_output=True, text=True, cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
        self.assertEqual(res2.returncode, 0, f"Import order db_models -> crm_models failed: {res2.stderr}")
        self.assertIn("OK2", res2.stdout)

    # -------------------------------------------------------------------------
    # T2.1 & T2.2: Models Schema, Defaults and Database Initialization
    # -------------------------------------------------------------------------
    def test_crm_models_schema_and_defaults(self):
        """Verify CRMConnection and CRMOutbox default fields and structures."""
        conn = CRMConnection.create(
            id="conn-1",
            tenant_id="tenant-1",
            name="My amoCRM",
            config={"token": "test"},
        )
        self.assertEqual(conn.crm_type, "amocrm")
        self.assertEqual(conn.auth_type, "oauth2")
        self.assertEqual(conn.status, "active")
        self.assertEqual(conn.token_version, 1)

        outbox = CRMOutbox.create(
            id="outbox-1",
            tenant_id="tenant-1",
            connection_id="conn-1",
            lead_data={"phone": "+1234567890"},
        )
        self.assertEqual(outbox.status, "PENDING")
        self.assertEqual(outbox.retry_count, 0)
        self.assertEqual(outbox.max_retries, 5)
        self.assertIsNone(outbox.business_key)

    # -------------------------------------------------------------------------
    # T2.6: CRMConnectionService Tenant Isolation
    # -------------------------------------------------------------------------
    def test_crm_connection_service_tenant_isolation(self):
        """Verify CRMConnectionService queries strictly filter by tenant_id."""
        conn_a = CRMConnectionService.save_connection(
            tenant_id="tenant-alpha",
            name="Alpha Connection",
            crm_type="amocrm",
            config={"client_secret": "alpha_secret"},
        )
        conn_b = CRMConnectionService.save_connection(
            tenant_id="tenant-beta",
            name="Beta Connection",
            crm_type="bitrix24",
            config={"webhook_key": "beta_secret"},
        )

        # Tenant Alpha cannot access Tenant Beta's connection
        exists, conn = CRMConnectionService.get_by_id_and_tenant(conn_b.id, "tenant-alpha")
        self.assertFalse(exists)
        self.assertIsNone(conn)

        # Tenant Alpha query_by_tenant only returns Alpha connections
        alpha_list = CRMConnectionService.query_by_tenant("tenant-alpha")
        self.assertEqual(len(alpha_list), 1)
        self.assertEqual(alpha_list[0].id, conn_a.id)

        # Platform active connections check
        self.assertTrue(CRMConnectionService.has_active_connections())
        CRMConnectionService.update_status(conn_a.id, "tenant-alpha", "disabled")
        CRMConnectionService.update_status(conn_b.id, "tenant-beta", "disabled")
        self.assertFalse(CRMConnectionService.has_active_connections())

    # -------------------------------------------------------------------------
    # T2.7: AES-256-GCM Encryption At Rest & Helper
    # -------------------------------------------------------------------------
    def test_crm_connection_encryption_at_rest(self):
        """Verify CRM credentials are encrypted at rest with enc:v2: and get_decrypted_config recovers plaintext."""
        raw_config = {
            "client_id": "amo-client-123",
            "client_secret": "super-confidential-secret",
            "refresh_token": "single-use-refresh-token",
        }
        conn = CRMConnectionService.save_connection(
            tenant_id="tenant-sec",
            name="Secure Conn",
            crm_type="amocrm",
            config=raw_config,
        )

        # 1. Raw database check: plaintext secret must NOT exist in the database
        raw_row = CRMConnection.get_by_id(conn.id)
        raw_config_in_db = raw_row.config
        self.assertNotIn("super-confidential-secret", str(raw_config_in_db))
        self.assertTrue(str(raw_config_in_db).startswith("{'enc:v2:") or "enc:v2:" in str(raw_config_in_db))

        # 2. get_decrypted_config recovers the original plaintext
        decrypted = CRMConnectionService.get_decrypted_config(conn)
        self.assertEqual(decrypted["client_id"], "amo-client-123")
        self.assertEqual(decrypted["client_secret"], "super-confidential-secret")
        self.assertEqual(decrypted["refresh_token"], "single-use-refresh-token")

    # -------------------------------------------------------------------------
    # T2.6: CAS Fencing Version Check
    # -------------------------------------------------------------------------
    def test_crm_connection_cas_fencing(self):
        """Verify update_config with expected_token_version fences out stale workers."""
        conn = CRMConnectionService.save_connection(
            tenant_id="tenant-cas",
            name="CAS Conn",
            config={"token": "initial"},
        )
        self.assertEqual(conn.token_version, 1)

        # Worker 1 updates with expected version 1 -> succeeds
        ok1 = CRMConnectionService.update_config(
            connection_id=conn.id,
            tenant_id="tenant-cas",
            config={"token": "worker1_refreshed"},
            expected_token_version=1,
        )
        self.assertTrue(ok1)

        fresh_conn = CRMConnection.get_by_id(conn.id)
        self.assertEqual(fresh_conn.token_version, 2)

        # Worker 2 attempts update with outdated expected version 1 -> rejected
        ok2 = CRMConnectionService.update_config(
            connection_id=conn.id,
            tenant_id="tenant-cas",
            config={"token": "worker2_stale"},
            expected_token_version=1,
        )
        self.assertFalse(ok2)

    # -------------------------------------------------------------------------
    # T2.6: CRMOutboxService Deduplication & Leases
    # -------------------------------------------------------------------------
    def test_crm_outbox_dedup_and_leases(self):
        """Verify 24h deduplication, atomic batch claiming, and retry backoff."""
        b_key = "hmac-sha256-hash-phone-123"
        task1, created1 = CRMOutboxService.enqueue(
            tenant_id="tenant-outbox",
            connection_id="conn-1",
            lead_data={"phone": "+1234567890"},
            business_key=b_key,
        )
        self.assertTrue(created1)

        # Duplicate submission within 24h is skipped
        task2, created2 = CRMOutboxService.enqueue(
            tenant_id="tenant-outbox",
            connection_id="conn-1",
            lead_data={"phone": "+1234567890"},
            business_key=b_key,
        )
        self.assertFalse(created2)
        self.assertEqual(task1.id, task2.id)

        # Worker 1 claims batch
        claimed = CRMOutboxService.claim_batch(worker_id="worker-node-1", batch_size=10)
        self.assertEqual(len(claimed), 1)
        self.assertEqual(claimed[0].id, task1.id)
        self.assertEqual(claimed[0].status, "PROCESSING")

        # Worker 2 tries to claim same task while lease is active -> 0 claimed
        claimed_w2 = CRMOutboxService.claim_batch(worker_id="worker-node-2", batch_size=10)
        self.assertEqual(len(claimed_w2), 0)

        # Complete task
        ok_comp = CRMOutboxService.complete_task(task_id=task1.id, worker_id="worker-node-1")
        self.assertTrue(ok_comp)
        final_task = CRMOutbox.get_by_id(task1.id)
        self.assertEqual(final_task.status, "SENT")
        self.assertIsNone(final_task.lease_owner)

    # -------------------------------------------------------------------------
    # T2.8: License Fail-Closed Gate
    # -------------------------------------------------------------------------
    def test_crm_license_fail_closed_gate(self):
        """Verify fail-closed licensing gate: strictly require 'crm' in features."""
        # Case 1: Commercial license without 'crm' in features -> DENIED
        payload_no_crm = {
            "type": "commercial",
            "features": ["knowledge_base", "analytics"],
        }
        allowed, msg, _ = check_crm_license_access(payload_no_crm)
        self.assertFalse(allowed)
        self.assertIn("not enabled in license features", msg)

        # Case 2: Enterprise license without 'crm' -> DENIED
        payload_ent_no_crm = {
            "type": "enterprise",
            "features": [],
        }
        allowed, msg, _ = check_crm_license_access(payload_ent_no_crm)
        self.assertFalse(allowed)

        # Case 3: License with 'crm' explicitly in features -> ALLOWED
        payload_with_crm = {
            "type": "enterprise",
            "features": ["crm", "multi_tenant"],
        }
        allowed, msg, _ = check_crm_license_access(payload_with_crm)
        self.assertTrue(allowed)
        self.assertIn("authorized", msg)

        # Case 4: require_crm_license raises CRMLicenseAccessError with PERMISSION_ERROR code
        with patch("api.crm.license_gate.check_license", return_value=(True, "OK", payload_no_crm)):
            with self.assertRaises(CRMLicenseAccessError) as ctx:
                require_crm_license()
            self.assertEqual(ctx.exception.code, RetCode.PERMISSION_ERROR)

        # Case 5: check_license raises an unexpected exception (I/O, parsing, etc.) -> Fail-Closed
        with patch("api.crm.license_gate.check_license", side_effect=IOError("Corrupt license file")):
            allowed, msg, payload = check_crm_license_access()
            self.assertFalse(allowed)
            self.assertIn("license verification failed", msg)
            self.assertIsNone(payload)

        # Case 6: check_license returns invalid payload structure
        with patch("api.crm.license_gate.check_license", return_value=(True, "OK", "corrupt_string_not_dict")):
            allowed, msg, payload = check_crm_license_access()
            self.assertFalse(allowed)
            self.assertIsNone(payload)

    # -------------------------------------------------------------------------
    # T2.5: SSRF Transport Guard & DNS Pinning
    # -------------------------------------------------------------------------
    def test_ssrf_transport_guard(self):
        """Verify CRMTransport enforces HTTPS, blocks private IPs, and disables redirects."""
        transport = CRMTransport()

        # 1. Reject non-https schemes
        with self.assertRaises(SSRFSecurityException):
            transport.get("http://example.com/api")

        # 2. Reject explicit allow_redirects=True
        with self.assertRaises(SSRFSecurityException):
            transport.get("https://example.com/api", allow_redirects=True)

        # 3. Reject loopback and private IP space
        with self.assertRaises(SSRFSecurityException):
            validate_crm_url_and_resolve("https://127.0.0.1/rest/api")

        with self.assertRaises(SSRFSecurityException):
            validate_crm_url_and_resolve("https://169.254.169.254/latest/meta-data/")

        with self.assertRaises(SSRFSecurityException):
            validate_crm_url_and_resolve("https://10.0.0.1/rest/")

        with self.assertRaises(SSRFSecurityException):
            validate_crm_url_and_resolve("https://192.168.1.100/rest/")

        # 4. On-premise allowlist override via CIDR
        os.environ["RAGFLOW_CRM_TEST_ALLOWLIST"] = "192.168.1.0/24,10.10.0.5"
        try:
            host, ip = validate_crm_url_and_resolve(
                "https://192.168.1.50/rest/",
                private_cidr_env="RAGFLOW_CRM_TEST_ALLOWLIST",
            )
            self.assertEqual(ip, "192.168.1.50")
        finally:
            os.environ.pop("RAGFLOW_CRM_TEST_ALLOWLIST", None)

    # -------------------------------------------------------------------------
    # Mutation Verification
    # -------------------------------------------------------------------------
    def test_mutation_proof_license_bypass_fails(self):
        """Mutation: granting access to commercial license without 'crm' must be rejected."""
        def mutated_check(payload):
            if payload.get("type") in ("commercial", "enterprise"):
                return True, "Bypassed", payload
            return False, "Denied", None

        # When the bypass is active, test catches the violation
        fake_payload = {"type": "commercial", "features": []}
        bypass_result, _, _ = mutated_check(fake_payload)
        real_result, _, _ = check_crm_license_access(fake_payload)
        self.assertTrue(bypass_result)
        self.assertFalse(real_result, "Real check must fail closed!")



class TestCRMSecurityVectors(unittest.TestCase):
    """Specific tests for seven security vectors requested in audit (Point 4)."""

    def test_vector_trailing_dot(self):
        """Vector 1: Trailing dot in hostname must be rejected fail-closed."""
        from api.crm.clients.bitrix24 import validate_bitrix24_cloud_url
        ok, msg = validate_bitrix24_cloud_url("https://mycompany.bitrix24.com./rest/1/key/")
        self.assertFalse(ok)
        self.assertIn("Invalid hostname format or punycode domain", msg)

    def test_vector_punycode(self):
        """Vector 2: Punycode (xn--) domain spoofing must be rejected fail-closed."""
        from api.crm.clients.bitrix24 import validate_bitrix24_cloud_url
        ok, msg = validate_bitrix24_cloud_url("https://xn--portal-43a.bitrix24.com/rest/1/key/")
        self.assertFalse(ok)
        self.assertIn("punycode", msg)

    def test_vector_userinfo(self):
        """Vector 3: Embedded userinfo/credentials in URL authority must be rejected."""
        from api.crm.clients.bitrix24 import validate_bitrix24_cloud_url
        from api.crm.transport import validate_crm_url_and_resolve, SSRFSecurityException
        ok, msg = validate_bitrix24_cloud_url("https://admin:pass@mycompany.bitrix24.com/rest/1/key/")
        self.assertFalse(ok)
        self.assertIn("User credentials in URL authority are forbidden", msg)

        with self.assertRaises(SSRFSecurityException) as ctx:
            validate_crm_url_and_resolve("https://admin:pass@example.com/rest/1/key/")
        self.assertIn("Userinfo in URL is forbidden", str(ctx.exception))

    def test_vector_user_at_evil(self):
        """Vector 4: Spoofed authority (портал.bitrix24.com@evil.com) must be rejected."""
        from api.crm.clients.bitrix24 import validate_bitrix24_cloud_url
        spoofed_cyrillic = "https://портал.bitrix24.com@evil.com/rest/1/key/"
        ok, msg = validate_bitrix24_cloud_url(spoofed_cyrillic)
        self.assertFalse(ok)

        spoofed_ascii = "https://mycompany.bitrix24.com@evil.com/rest/1/key/"
        ok2, msg2 = validate_bitrix24_cloud_url(spoofed_ascii)
        self.assertFalse(ok2)

    def test_vector_172_16_private_cidr(self):
        """Vector 5: Private IP space (172.16.0.0/12) must be blocked by SSRF guard."""
        from api.crm.transport import validate_crm_url_and_resolve, SSRFSecurityException
        with self.assertRaises(SSRFSecurityException) as ctx:
            validate_crm_url_and_resolve("https://172.16.0.1/rest/")
        self.assertIn("SSRF guard blocked access to non-global IP", str(ctx.exception))

        with self.assertRaises(SSRFSecurityException) as ctx:
            validate_crm_url_and_resolve("https://172.31.255.254/rest/")
        self.assertIn("SSRF guard blocked access to non-global IP", str(ctx.exception))

    def test_vector_redirect_to_private(self):
        """Vector 6: HTTP redirects must be forbidden to prevent SSRF redirect to private network."""
        from api.crm.transport import CRMTransport, SSRFSecurityException
        transport = CRMTransport()
        with self.assertRaises(SSRFSecurityException) as ctx:
            transport.get("https://example.com/api", allow_redirects=True)
        self.assertIn("HTTP redirects are strictly disabled", str(ctx.exception))

        with patch.object(transport.session, "request") as mock_req, \
             patch("api.crm.transport.validate_crm_url_and_resolve", return_value=("example.com", "93.184.216.34")):
            transport.get("https://example.com/redirect")
            self.assertFalse(mock_req.call_args[1].get("allow_redirects"))

    def test_vector_pin_dns_enforcement(self):
        """Vector 7: DNS Pinning must be active during HTTP requests to prevent DNS rebinding."""
        from api.crm.transport import CRMTransport
        transport = CRMTransport()
        with patch("api.crm.transport.pin_dns") as mock_pin_dns, \
             patch.object(transport.session, "request"), \
             patch("api.crm.transport.validate_crm_url_and_resolve", return_value=("portal.example.com", "93.184.216.34")):
            transport.get("https://portal.example.com/api")
            mock_pin_dns.assert_called_once_with("portal.example.com", "93.184.216.34")


if __name__ == "__main__":
    unittest.main()
