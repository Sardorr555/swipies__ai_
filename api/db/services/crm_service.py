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
    ) -> bool:
        """Update connection configuration with encryption and monotonic fencing check.
        
        If expected_token_version is provided, performs atomic compare-and-swap (CAS).
        """
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
    def update_status(cls, connection_id: str, tenant_id: str, status: str) -> bool:
        """Update status of a CRM connection."""
        rows = (
            cls.model.update(status=status)
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
        # PENDING or FAILED ready for retry, OR PROCESSING whose lease expired
        candidates = (
            cls.model.select()
            .where(
                (
                    (cls.model.status << ["PENDING", "FAILED"])
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
                        (cls.model.status << ["PENDING", "FAILED"])
                        | (cls.model.status == "PROCESSING")
                    )
                    & ((cls.model.lease_expires_at.is_null()) | (cls.model.lease_expires_at < now))
                )
                .execute()
            )
            if rows > 0:
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
            new_status = "FAILED"
            delay_ms = (2 ** task.retry_count) * backoff_base_seconds * 1000
            next_retry = now + delay_ms

        error_data = task.error_log or {}
        error_data[f"retry_{new_retry_count}"] = {
            "timestamp": now,
            "error": str(error_msg)[:500],
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
    def purge_expired_pii(cls, days: int = 30) -> int:
        """Purge customer PII (lead_data) and null out business_key for records older than 30 days (T5.8)."""
        now = current_timestamp()
        cutoff = now - (days * 24 * 3600 * 1000)
        rows = (
            cls.model.update(
                lead_data={},
                business_key=None,
            )
            .where(
                (cls.model.create_time < cutoff)
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



def compute_lead_business_key(tenant_id: str, connection_id: str, phone: str, secret: Optional[str] = None) -> str:
    """Compute deterministic HMAC-SHA256 business key for 24-hour sliding deduplication (T5.5)."""
    import hashlib
    import hmac
    sec = (secret or os.environ.get("RAGFLOW_SECRET_KEY", "ragflow_crm_default_salt")).encode("utf-8")
    norm_phone = re.sub(r"[^\d+]", "", str(phone).strip())
    msg = f"{tenant_id}:{connection_id}:{norm_phone}".encode("utf-8")
    return hmac.new(sec, msg, hashlib.sha256).hexdigest()

