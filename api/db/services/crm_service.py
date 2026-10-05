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
import re
import time
from typing import Optional, Tuple, List, Dict, Any

from api.db.db_models import DB
from api.db.crm_models import CRMConnection, CRMOutbox
from api.db.services.common_service import CommonService
from api.utils.key_crypto import (
    encrypt_connector_config,
    decrypt_connector_config,
)
from common.misc_utils import get_uuid
from common.time_utils import current_timestamp

logger = logging.getLogger(__name__)


class CRMConnectionService(CommonService):
    model = CRMConnection

    @classmethod
    @DB.connection_context()
    def get_by_id_and_tenant(cls, connection_id: str, tenant_id: str) -> Tuple[bool, Optional[CRMConnection]]:
        """Strictly retrieve a CRM connection by its ID and tenant_id."""
        if not connection_id or not tenant_id:
            return False, None
        records = cls.model.select().where(
            (cls.model.id == connection_id) & (cls.model.tenant_id == tenant_id)
        )
        if records:
            return True, records[0]
        return False, None

    @classmethod
    @DB.connection_context()
    def query_by_tenant(cls, tenant_id: str, status: Optional[str] = None) -> List[CRMConnection]:
        """List all CRM connections belonging to a tenant, optionally filtered by status."""
        if not tenant_id:
            return []
        query = cls.model.select().where(cls.model.tenant_id == tenant_id)
        if status:
            query = query.where(cls.model.status == status)
        return list(query.order_by(cls.model.create_time.desc()))

    @classmethod
    @DB.connection_context()
    def resolve_active_connection(cls, tenant_id: str, connection_id: Optional[str] = None) -> Tuple[bool, Optional[CRMConnection]]:
        """Resolve active CRM connection for tenant by explicit ID or first active connection."""
        if not tenant_id:
            return False, None
        if connection_id:
            ok, conn = cls.get_by_id_and_tenant(connection_id, tenant_id)
            if ok and conn and conn.status == "active":
                return True, conn
            return False, None
        conns = cls.query_by_tenant(tenant_id, status="active")
        if conns:
            return True, conns[0]
        return False, None

    @classmethod
    @DB.connection_context()
    def has_active_connections(cls) -> bool:
        """Check if any active CRM connections exist in the platform."""
        return cls.model.select(cls.model.id).where(cls.model.status == "active").first() is not None

    @classmethod
    @DB.connection_context()
    def save_connection(
        cls,
        tenant_id: str,
        name: str,
        crm_type: str = "amocrm",
        auth_type: str = "oauth2",
        config: Optional[Dict[str, Any]] = None,
        status: str = "active",
        connection_id: Optional[str] = None,
    ) -> CRMConnection:
        """Create a new CRM connection with credentials encrypted at rest."""
        raw_config = config or {}
        enc_config = encrypt_connector_config(raw_config)

        conn_id = connection_id or get_uuid()
        record = cls.model.create(
            id=conn_id,
            tenant_id=tenant_id,
            name=name,
            crm_type=crm_type,
            auth_type=auth_type,
            status=status,
            token_version=1,
            config=enc_config,
        )
        return record

    @classmethod
    @DB.connection_context()
    def update_config(
        cls,
        connection_id: str,
        tenant_id: str,
        config: Dict[str, Any],
        expected_token_version: Optional[int] = None,
        merge: bool = True,
    ) -> bool:
        """Update connection configuration with encryption and monotonic fencing check.
        
        If expected_token_version is provided, performs atomic compare-and-swap (CAS).
        """
        if merge:
            ok, conn = cls.get_by_id_and_tenant(connection_id, tenant_id)
            if ok and conn:
                try:
                    existing_cfg = cls.get_decrypted_config(conn)
                    merged = dict(existing_cfg)
                    merged.update(config)
                    config = merged
                except Exception:
                    pass

        enc_config = encrypt_connector_config(config)
        where_cond = (cls.model.id == connection_id) & (cls.model.tenant_id == tenant_id)

        if expected_token_version is not None:
            where_cond = where_cond & (cls.model.token_version == expected_token_version)

        rows = (
            cls.model.update(
                config=enc_config,
                token_version=cls.model.token_version + 1,
            )
            .where(where_cond)
            .execute()
        )
        return rows > 0

    @classmethod
    @DB.connection_context()
    def set_management_enabled(cls, connection_id: str, tenant_id: str, enabled: bool) -> bool:
        """Enable or disable management (write/actions) for a CRM connection.
        
        When re-enabled, automatically unparks any queued outbox tasks for this connection.
        """
        res = cls.update_config(
            connection_id=connection_id,
            tenant_id=tenant_id,
            config={"management_enabled": bool(enabled)},
            merge=True,
        )
        if res and enabled:
            CRMOutboxService.unpark_tasks_for_connection(connection_id)
        return res

    @classmethod
    def is_management_enabled(cls, conn: CRMConnection) -> bool:
        """Check if CRM write/management operations are enabled for this connection or connector."""
        if not conn:
            return False
        # 1. Check direct config on connection
        try:
            cfg = cls.get_decrypted_config(conn)
            for key in ("management_enabled", "enable_management", "allow_write", "allow_crm_actions"):
                if key in cfg:
                    return bool(cfg[key])
        except Exception:
            pass

        # 2. Check if linked to a Connector in ConnectorService
        try:
            from api.db.services.connector_service import ConnectorService
            ok, connector = ConnectorService.get_by_id(conn.id)
            if ok and connector and connector.config:
                c_cfg = connector.config if isinstance(connector.config, dict) else {}
                for key in ("management_enabled", "enable_management", "allow_write", "allow_crm_actions"):
                    if key in c_cfg:
                        return bool(c_cfg[key])
        except Exception:
            pass

        return True

    @classmethod
    @DB.connection_context()
    def update_status(cls, connection_id: str, tenant_id: str, status: str) -> bool:
        """Update status of a CRM connection."""
        rows = (
            cls.model.update(status=status)
            .where((cls.model.id == connection_id) & (cls.model.tenant_id == tenant_id))
            .execute()
        )
        if rows > 0 and status == "active":
            CRMOutboxService.unpark_tasks_for_connection(connection_id)
        return rows > 0

    @classmethod
    @DB.connection_context()
    def delete_by_id_and_tenant(cls, connection_id: str, tenant_id: str) -> bool:
        """Delete a CRM connection owned by the given tenant."""
        rows = (
            cls.model.delete()
            .where((cls.model.id == connection_id) & (cls.model.tenant_id == tenant_id))
            .execute()
        )
        return rows > 0

    @classmethod
    def get_decrypted_config(cls, connection_or_id: Any, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        """Extract and decrypt credentials for a given connection."""
        if isinstance(connection_or_id, str):
            if not tenant_id:
                raise ValueError("tenant_id is required when fetching connection by ID")
            exists, conn = cls.get_by_id_and_tenant(connection_or_id, tenant_id)
            if not exists or not conn:
                return {}
            cfg = getattr(conn, "config", {}) or {}
        elif hasattr(connection_or_id, "config"):
            cfg = getattr(connection_or_id, "config", {}) or {}
        elif isinstance(connection_or_id, dict):
            cfg = connection_or_id
        else:
            return {}

        return decrypt_connector_config(cfg)


class CRMOutboxService(CommonService):
    model = CRMOutbox

    @classmethod
    @DB.connection_context()
    def enqueue(
        cls,
        tenant_id: str,
        connection_id: str,
        lead_data: Dict[str, Any],
        business_key: Optional[str] = None,
        max_retries: int = 5,
    ) -> Tuple[CRMOutbox, bool]:
        """Enqueue an outbound lead task with sliding 24-hour deduplication.
        
        Returns:
            (record, was_created): was_created is False if a duplicate was found within 24h.
        """
        # Enforce CRM management permission check
        ok, conn = CRMConnectionService.get_by_id_and_tenant(connection_id, tenant_id)
        if ok and conn and not CRMConnectionService.is_management_enabled(conn):
            raise PermissionError(
                f"CRM management is disabled for connection '{connection_id}'. Write operations are blocked while data extraction remains active."
            )

        now = current_timestamp()

        # Sliding 24-hour deduplication check
        if business_key:
            window_start = now - (24 * 3600 * 1000)
            existing = (
                cls.model.select()
                .where(
                    (cls.model.tenant_id == tenant_id)
                    & (cls.model.business_key == business_key)
                    & (cls.model.create_time >= window_start)
                )
                .order_by(cls.model.create_time.desc())
                .first()
            )
            if existing:
                logger.info(
                    "Duplicate lead skipped: tenant=%s business_key=%s existing_id=%s",
                    tenant_id,
                    business_key,
                    existing.id,
                )
                return existing, False

        new_id = get_uuid()
        record = cls.model.create(
            id=new_id,
            tenant_id=tenant_id,
            connection_id=connection_id,
            business_key=business_key,
            status="PENDING",
            retry_count=0,
            max_retries=max_retries,
            next_retry_at=now,
            lead_data=lead_data,
            error_log={},
        )
        return record, True

    @classmethod
    @DB.connection_context()
    def claim_batch(
        cls,
        worker_id: str,
        batch_size: int = 50,
        lease_duration_seconds: int = 300,
    ) -> List[CRMOutbox]:
        """Atomically claim a batch of pending/failed/expired outbox tasks for processing."""
        now = current_timestamp()
        lease_expires = now + (lease_duration_seconds * 1000)

        # Candidates eligible for processing:
        # PENDING or RETRY/FAILED ready for retry, OR PROCESSING whose lease expired.
        # Excludes DEAD_LETTER and PARKED.
        candidates = (
            cls.model.select()
            .where(
                (
                    (cls.model.status << ["PENDING", "RETRY"])
                    | (cls.model.status == "PROCESSING")
                )
                & ((cls.model.lease_expires_at.is_null()) | (cls.model.lease_expires_at < now))
                & ((cls.model.next_retry_at.is_null()) | (cls.model.next_retry_at <= now))
            )
            .order_by(cls.model.create_time.asc())
            .limit(batch_size)
        )

        claimed = []
        for task in candidates:
            # Atomic compare-and-swap lease acquisition per task
            rows = (
                cls.model.update(
                    status="PROCESSING",
                    lease_owner=worker_id,
                    lease_expires_at=lease_expires,
                )
                .where(
                    (cls.model.id == task.id)
                    & (
                        (cls.model.status << ["PENDING", "RETRY"])
                        | (cls.model.status == "PROCESSING")
                    )
                    & ((cls.model.lease_expires_at.is_null()) | (cls.model.lease_expires_at < now))
                )
                .execute()
            )
            if rows > 0:
                # Increment reclaim counter if recovering an expired PROCESSING task (Point 3)
                if task.status == "PROCESSING":
                    err_data = task.error_log or {}
                    reclaim_cnt = err_data.get("reclaim_count", 0) + 1
                    err_data["reclaim_count"] = reclaim_cnt
                    MAX_RECLAIM_CEILING = 5
                    if reclaim_cnt >= MAX_RECLAIM_CEILING:
                        err_data["dead_letter_reason"] = f"Exceeded maximum reclaim ceiling ({MAX_RECLAIM_CEILING} uncompleted leases)"
                        cls.model.update(
                            status="DEAD_LETTER",
                            error_log=err_data,
                            lease_owner=None,
                            lease_expires_at=None,
                        ).where(cls.model.id == task.id).execute()
                        continue
                    cls.model.update(error_log=err_data).where(cls.model.id == task.id).execute()
                    task.error_log = err_data
                task.status = "PROCESSING"
                task.lease_owner = worker_id
                task.lease_expires_at = lease_expires
                claimed.append(task)

        return claimed

    @classmethod
    @DB.connection_context()
    def complete_task(cls, task_id: str, worker_id: str, external_id: Optional[str] = None) -> bool:
        """Mark a claimed outbox task as successfully dispatched (SENT)."""
        task = cls.model.select().where((cls.model.id == task_id) & (cls.model.lease_owner == worker_id)).first()
        if not task:
            return False

        error_data = task.error_log or {}
        if external_id:
            error_data["external_id"] = str(external_id)

        rows = (
            cls.model.update(
                status="SENT",
                error_log=error_data,
                lease_owner=None,
                lease_expires_at=None,
            )
            .where((cls.model.id == task_id) & (cls.model.lease_owner == worker_id))
            .execute()
        )
        return rows > 0

    @classmethod
    @DB.connection_context()
    def fail_task(
        cls,
        task_id: str,
        worker_id: str,
        error_msg: str,
        backoff_base_seconds: int = 10,
        max_delay_seconds: int = 3600,
    ) -> bool:
        """Handle outbox task failure with exponential backoff and dead-letter transition."""
        now = current_timestamp()
        task = cls.model.select().where((cls.model.id == task_id) & (cls.model.lease_owner == worker_id)).first()
        if not task:
            return False

        new_retry_count = task.retry_count + 1
        if new_retry_count >= task.max_retries:
            new_status = "DEAD_LETTER"
            next_retry = None
        else:
            new_status = "RETRY"
            # Exponential backoff in 6-24 hours horizon (capped at 1 hour = 3600s ceiling)
            delay_seconds = min((2 ** task.retry_count) * backoff_base_seconds, max_delay_seconds)
            next_retry = now + (delay_seconds * 1000)

        # Sanitize error message to ensure no PII (phone numbers, tokens) is stored in error_log
        clean_error = re.sub(r"\+?[1-9]\d{6,14}", "[REDACTED_PHONE]", str(error_msg)[:500])

        error_data = task.error_log or {}
        error_data[f"retry_{new_retry_count}"] = {
            "timestamp": now,
            "error": clean_error,
        }

        rows = (
            cls.model.update(
                status=new_status,
                retry_count=new_retry_count,
                next_retry_at=next_retry,
                error_log=error_data,
                lease_owner=None,
                lease_expires_at=None,
            )
            .where((cls.model.id == task_id) & (cls.model.lease_owner == worker_id))
            .execute()
        )
        return rows > 0

    @classmethod
    @DB.connection_context()
    def park_task(
        cls,
        task_id: str,
        worker_id: str,
        reason: str,
        delay_seconds: int = 300,
    ) -> bool:
        """Park an outbox task without consuming retry attempts (e.g. for reauth_required) (Point 3).
        
        Status becomes 'PARKED'. It will NOT be claimed or retried in loop until unparked on reauth.
        """
        now = current_timestamp()
        task = cls.model.select().where((cls.model.id == task_id) & (cls.model.lease_owner == worker_id)).first()
        if not task:
            return False

        clean_reason = re.sub(r"\+?[1-9]\d{6,14}", "[REDACTED_PHONE]", str(reason)[:500])
        error_data = task.error_log or {}
        error_data["parked_at"] = now
        error_data["parked_reason"] = clean_reason

        rows = (
            cls.model.update(
                status="PARKED",
                next_retry_at=None,
                error_log=error_data,
                lease_owner=None,
                lease_expires_at=None,
            )
            .where((cls.model.id == task_id) & (cls.model.lease_owner == worker_id))
            .execute()
        )
        return rows > 0

    @classmethod
    @DB.connection_context()
    def unpark_tasks_for_connection(cls, connection_id: str) -> int:
        """Resume PARKED outbox tasks when CRM connection is re-authenticated (Point 3)."""
        now = current_timestamp()
        return (
            cls.model.update(
                status="PENDING",
                next_retry_at=now,
            )
            .where((cls.model.connection_id == connection_id) & (cls.model.status == "PARKED"))
            .execute()
        )

    @classmethod
    @DB.connection_context()
    def purge_expired_pii(cls, days: int = 30) -> int:
        """Purge customer PII (lead_data) and null out business_key for TERMINAL records older than 30 days (T5.8)."""
        now = current_timestamp()
        cutoff = now - (days * 24 * 3600 * 1000)
        rows = (
            cls.model.update(
                lead_data={},
                business_key=None,
            )
            .where(
                (cls.model.create_time < cutoff)
                & (cls.model.status << ["SENT", "DEAD_LETTER"])
                & ((cls.model.business_key.is_null(False)) | (cls.model.lead_data != {}))
            )
            .execute()
        )
        return rows

    @classmethod
    @DB.connection_context()
    def get_oldest_pending_lag_seconds(cls) -> int:
        """Calculate lag in seconds for the oldest pending outbox record (T5.7)."""
        now = current_timestamp()
        oldest = (
            cls.model.select(cls.model.create_time)
            .where(cls.model.status == "PENDING")
            .order_by(cls.model.create_time.asc())
            .first()
        )
        if not oldest or not oldest.create_time:
            return 0
        lag_ms = max(0, now - oldest.create_time)
        return int(lag_ms // 1000)

    @classmethod
    @DB.connection_context()
    def get_health_metrics(cls) -> Dict[str, Any]:
        """Return operational health metrics for the CRM outbox subsystem (spec.md:299)."""
        from api.crm.license_gate import CRMLicenseGate

        is_licensed = CRMLicenseGate.is_crm_enabled()
        lag = cls.get_oldest_pending_lag_seconds()
        active_leases = cls.model.select().where(cls.model.status == "PROCESSING").count()
        dead_letters = cls.model.select().where(cls.model.status == "DEAD_LETTER").count()
        parked = cls.model.select().where(cls.model.status == "PARKED").count()

        is_degraded = lag > 900  # 15 minutes lag threshold
        return {
            "status": "degraded" if is_degraded else "ok",
            "crm_enabled": is_licensed,
            "oldest_pending_seconds": lag,
            "active_leases": active_leases,
            "parked_tasks": parked,
            "dead_letter_count": dead_letters,
        }



def compute_lead_business_key(tenant_id: str, connection_id: str, phone: str, secret: Optional[str] = None) -> str:
    """Compute deterministic HMAC-SHA256 business key for 24-hour sliding deduplication (T5.5)."""
    import hashlib
    import hmac
    sec = (secret or os.environ.get("RAGFLOW_SECRET_KEY", "ragflow_crm_default_salt")).encode("utf-8")
    norm_phone = re.sub(r"[^\d+]", "", str(phone).strip())
    msg = f"{tenant_id}:{connection_id}:{norm_phone}".encode("utf-8")
    return hmac.new(sec, msg, hashlib.sha256).hexdigest()

