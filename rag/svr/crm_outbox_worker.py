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
import logging
import os
import signal
import sys
import threading
import time
import uuid
from typing import Any, Dict, List, Optional

from api.db.services.crm_service import CRMConnectionService, CRMOutboxService
from api.db.crm_models import CRMConnection, CRMOutbox
from api.crm.base import CRMProviderRegistry
from api.crm.clients.amocrm import AmoCRMTokenRevokedError
from api.crm.license_gate import check_crm_license_access, CRMLicenseGate

logger = logging.getLogger("CRMOutboxWorker")

POLL_INTERVAL_SECONDS = float(os.environ.get("RAGFLOW_CRM_WORKER_POLL_INTERVAL", 2.0))
BATCH_SIZE = int(os.environ.get("RAGFLOW_CRM_WORKER_BATCH_SIZE", 50))
LEASE_DURATION_SECONDS = int(os.environ.get("RAGFLOW_CRM_WORKER_LEASE_SECONDS", 300))  # 5 minutes
CRITICAL_LAG_SECONDS = int(os.environ.get("RAGFLOW_CRM_WORKER_LAG_THRESHOLD", 900))   # 15 minutes
PII_PURGE_INTERVAL_SECONDS = int(os.environ.get("RAGFLOW_CRM_PII_PURGE_INTERVAL", 3600))  # 1 hour


class CRMOutboxWorker:
    """Dedicated background daemon leasing and dispatching CRM outbox leads."""

    def __init__(
        self,
        worker_id: Optional[str] = None,
        batch_size: int = BATCH_SIZE,
        lease_duration: int = LEASE_DURATION_SECONDS,
        poll_interval: float = POLL_INTERVAL_SECONDS,
        pii_purge_interval: int = PII_PURGE_INTERVAL_SECONDS,
    ):
        self.worker_id = worker_id or f"crm_outbox_{os.getpid()}_{uuid.uuid4().hex[:8]}"
        self.batch_size = batch_size
        self.lease_duration = lease_duration
        self.poll_interval = poll_interval
        self.pii_purge_interval = pii_purge_interval

        self._stop_event = threading.Event()
        self._last_pii_purge_time = 0.0
        self.processed_count = 0
        self.failed_count = 0

        self._self_check_dependencies()

    def _self_check_dependencies(self) -> None:
        """Startup self-check verifying required dependencies like phonenumbers (Point 5)."""
        try:
            import phonenumbers
        except ImportError as e:
            raise RuntimeError(
                "CRM Outbox Worker startup self-check failed: 'phonenumbers' package is missing. "
                "Install 'phonenumbers>=9.0.24' into runtime environment."
            ) from e

    def check_and_alert_lag(self) -> int:
        """Query oldest pending task age and emit high-priority structured alert if lag > 15m (T5.7)."""
        lag = CRMOutboxService.get_oldest_pending_lag_seconds()
        if lag > CRITICAL_LAG_SECONDS:
            logger.error("CRM_OUTBOX_LAG_CRITICAL: oldest_pending_seconds=%d threshold=%d", lag, CRITICAL_LAG_SECONDS)
        return lag

    def process_task(self, task: CRMOutbox) -> bool:
        """Process a single leased outbox task."""
        ok, conn = CRMConnectionService.get_by_id_and_tenant(task.connection_id, task.tenant_id)
        if not ok or not conn:
            err_msg = f"CRM connection '{task.connection_id}' not found for tenant '{task.tenant_id}'"
            logger.error("%s. Failing task %s.", err_msg, task.id)
            CRMOutboxService.fail_task(task.id, self.worker_id, error_msg=err_msg, backoff_base_seconds=10)
            self.failed_count += 1
            return False

        if conn.status == "reauth_required":
            err_msg = f"CRM connection '{conn.id}' requires re-authentication (status=reauth_required)"
            logger.warning("%s. Parking task %s without consuming retries.", err_msg, task.id)
            CRMOutboxService.park_task(task.id, self.worker_id, reason=err_msg, delay_seconds=300)
            self.failed_count += 1
            return False

        if conn.status != "active":
            err_msg = f"CRM connection '{conn.id}' is not active (status={conn.status})"
            logger.warning("%s. Delaying task %s.", err_msg, task.id)
            CRMOutboxService.fail_task(task.id, self.worker_id, error_msg=err_msg, backoff_base_seconds=10)
            self.failed_count += 1
            return False

        try:
            config = CRMConnectionService.get_decrypted_config(conn)
            config["id"] = conn.id
            config["connection_id"] = conn.id
            config["tenant_id"] = conn.tenant_id
            config["token_version"] = conn.token_version

            provider = CRMProviderRegistry.get(conn.crm_type)
            result = provider.create_lead(connection_config=config, lead_data=task.lead_data)

            external_lead_id = result.get("lead_id") if isinstance(result, dict) else None
            CRMOutboxService.complete_task(task.id, self.worker_id, external_id=external_lead_id)
            logger.info(
                "CRM outbox task %s successfully dispatched to %s (external_id=%s)",
                task.id,
                conn.crm_type,
                external_lead_id,
            )
            self.processed_count += 1
            return True

        except AmoCRMTokenRevokedError as e:
            logger.error("AmoCRM token revoked for connection %s: %s. Parking task %s.", conn.id, e, task.id)
            CRMOutboxService.park_task(task.id, self.worker_id, reason=f"AmoCRM token revoked: {e}", delay_seconds=300)
            self.failed_count += 1
            return False

        except Exception as e:
            logger.warning("CRM outbox task %s dispatch failed (will retry): %s", task.id, e)
            CRMOutboxService.fail_task(task.id, self.worker_id, error_msg=str(e), backoff_base_seconds=10)
            self.failed_count += 1
            return False

    def _maybe_purge_pii(self) -> None:
        """Periodically purge customer PII older than 30 days (T5.8)."""
        now = time.time()
        if (now - self._last_pii_purge_time) >= self.pii_purge_interval:
            try:
                purged = CRMOutboxService.purge_expired_pii(days=30)
                if purged > 0:
                    logger.info("PII retention cleaner purged %d expired outbox records (>30 days).", purged)
                self._last_pii_purge_time = now
            except Exception as e:
                logger.warning("Error running periodic PII retention cleanup: %s", e)

    def run_once(self) -> int:
        """Execute a single processing cycle: claim batch, process tasks, check lag, purge PII."""
        # 1. License check (Point 10): zero overhead when CRM subsystem is unlicensed
        if not CRMLicenseGate.is_crm_enabled():
            return 0

        # Periodic PII retention cleanup (runs even if connections are deactivated)
        self._maybe_purge_pii()

        # 2. Connection check (Point 10): zero overhead if no active CRM connections exist
        has_active_conns = CRMConnectionService.has_active_connections()
        if not has_active_conns:
            return 0

        tasks = CRMOutboxService.claim_batch(
            worker_id=self.worker_id,
            batch_size=self.batch_size,
            lease_duration_seconds=self.lease_duration,
        )
        for task in tasks:
            self.process_task(task)

        self.check_and_alert_lag()
        return len(tasks)

    def start(self) -> None:
        """Start the outbox worker polling loop with signal handling."""
        if threading.current_thread() is threading.main_thread():
            try:
                signal.signal(signal.SIGINT, lambda s, f: self.stop())
                if hasattr(signal, "SIGTERM"):
                    signal.signal(signal.SIGTERM, lambda s, f: self.stop())
            except (ValueError, AttributeError):
                pass

        logger.info(
            "CRM Outbox Worker started: worker_id=%s batch_size=%d lease_duration=%ds",
            self.worker_id,
            self.batch_size,
            self.lease_duration,
        )

        while not self._stop_event.is_set():
            try:
                claimed = self.run_once()
                if claimed == 0:
                    self._stop_event.wait(self.poll_interval)
            except Exception as e:
                logger.error("Unexpected error in CRM Outbox Worker loop: %s", e, exc_info=True)
                self._stop_event.wait(self.poll_interval)

        logger.info("CRM Outbox Worker stopped gracefully: worker_id=%s", self.worker_id)

    def stop(self) -> None:
        """Signal the outbox worker loop to stop gracefully."""
        logger.info("Stopping CRM Outbox Worker: worker_id=%s", self.worker_id)
        self._stop_event.set()


if __name__ == "__main__":
    from common.log_utils import init_root_logger
    init_root_logger("crm_outbox_worker")

    worker = CRMOutboxWorker()
    worker.start()
