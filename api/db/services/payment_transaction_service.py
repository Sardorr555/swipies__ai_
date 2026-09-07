#
#  Copyright 2024 The InfiniFlow Authors. All Rights Reserved.
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
from datetime import datetime, timedelta
import logging
import peewee
from peewee import fn

from api.db.db_models import DB, PaymentTransaction, Tenant, User
from api.db.services.common_service import CommonService
from common.misc_utils import get_uuid
from common.time_utils import current_timestamp, datetime_format


class PaymentTransactionService(CommonService):
    """Service class for managing financial payment transactions and audit ledger.

    IMPORTANT CONCURRENCY NOTE:
    Methods that transition a transaction to PAID and trigger tenant provisioning
    (e.g., mark_paid / finalize_provisioning) MUST be executed within a distributed
    database lock context (e.g. MysqlDatabaseLock("swipies_pay_<tx_id>") in Phase 2.2)
    to prevent race conditions between concurrent user apply and Atmos webhooks.
    """
    model = PaymentTransaction

    @classmethod
    def calculate_expected_amount_uzs(cls, plan_type: str, months: int = 1) -> int:
        """Calculate the official minimum expected price in UZS for a plan/period."""
        p = (plan_type or "").lower().strip()
        m = max(1, int(months or 1))

        if p == "license":
            if m == 6:
                return 2470000
            if m >= 12:
                return 4500000
            return m * 450000

        if p == "free":
            return 0

        # Dynamically read pricing configured in the Admin Panel (system_settings table)
        from api.db.services.system_settings_service import SystemSettingsService
        monthly_price = 199000.0
        try:
            var_name = f"pricing.{p}.uzs"
            objs = SystemSettingsService.get_by_name(var_name)
            if objs and objs[0].value:
                monthly_price = float(objs[0].value)
            elif p == "pro":
                monthly_price = 400000.0
            else:
                monthly_price = 199000.0
        except Exception as ex:
            import logging
            logging.warning(f"[PaymentTransactionService] Failed to load dynamic pricing from SystemSettingsService for {p}: {ex}")
            monthly_price = 400000.0 if p == "pro" else 199000.0

        discount = 0.0
        if m == 6:
            discount = 0.10
        elif m >= 12:
            discount = 0.20

        total = (monthly_price * m) * (1.0 - discount)
        return int(round(total))

    @classmethod
    @DB.connection_context()
    def get_by_tx_id(cls, transaction_id: str):
        """Retrieve a transaction record by its gateway transaction_id."""
        if not transaction_id:
            return None
        return cls.model.get_or_none(cls.model.transaction_id == str(transaction_id))

    @classmethod
    @DB.connection_context()
    def create_pending(
        cls,
        transaction_id: str,
        user_id: str,
        tenant_id: str,
        account_email: str,
        plan_type: str,
        duration_months: int = 1,
        expected_amount_uzs: int = None,
        payment_method: str = "atmos_uzcard_humo",
    ):
        """Idempotently create or retrieve an initiated PENDING transaction record.

        If a transaction with the same transaction_id already exists, returns the
        existing record without error (idempotent init).
        """
        if not transaction_id or not account_email:
            raise ValueError("transaction_id and account_email are required")

        existing = cls.get_by_tx_id(transaction_id)
        if existing:
            return existing, False

        if expected_amount_uzs is None or expected_amount_uzs <= 0:
            expected_amount_uzs = cls.calculate_expected_amount_uzs(plan_type, duration_months)

        tx_dict = {
            "id": get_uuid(),
            "transaction_id": str(transaction_id),
            "user_id": str(user_id or ""),
            "tenant_id": str(tenant_id or ""),
            "account_email": str(account_email).strip().lower(),
            "plan_type": str(plan_type or "plus").lower(),
            "duration_months": max(1, int(duration_months or 1)),
            "expected_amount_uzs": int(expected_amount_uzs),
            "paid_amount_uzs": None,
            "status": "PENDING",
            "payment_method": str(payment_method or "atmos_uzcard_humo"),
            "is_provisioned": False,
            "provisioned_at": None,
            "create_time": current_timestamp(),
            "create_date": datetime_format(datetime.now()),
            "update_time": current_timestamp(),
            "update_date": datetime_format(datetime.now()),
        }

        try:
            created = cls.model.create(**tx_dict)
            return created, True
        except peewee.IntegrityError:
            # Race condition during concurrent creation
            existing = cls.get_by_tx_id(transaction_id)
            if existing:
                return existing, False
            raise

    @classmethod
    @DB.connection_context()
    def mark_paid(
        cls,
        transaction_id: str,
        paid_amount_uzs: int,
        gateway_response: dict = None,
        audit_note: str = None,
    ):
        """Mark transaction as PAID and store the actual verified amount and gateway payload.

        CRITICAL: paid_amount_uzs must be the ACTUAL amount confirmed by Atmos gateway
        (tiyins / 100), ensuring financial analytics reflect real settled revenue.
        """
        tx = cls.get_by_tx_id(transaction_id)
        if not tx:
            raise ValueError(f"Transaction not found: {transaction_id}")

        now = datetime.now()
        update_fields = {
            "status": "PAID",
            "paid_amount_uzs": int(paid_amount_uzs) if paid_amount_uzs is not None else tx.expected_amount_uzs,
            "is_provisioned": True,
            "provisioned_at": now,
            "update_time": current_timestamp(),
            "update_date": datetime_format(now),
        }
        if gateway_response is not None:
            update_fields["gateway_response"] = gateway_response
        if audit_note:
            update_fields["audit_note"] = audit_note

        cls.model.update(**update_fields).where(cls.model.id == tx.id).execute()
        return cls.get_by_tx_id(transaction_id)

    @classmethod
    @DB.connection_context()
    def mark_failed(
        cls,
        transaction_id: str,
        error_code: str = None,
        error_message: str = None,
        gateway_response: dict = None,
        audit_note: str = None,
    ):
        """Mark transaction as FAILED with rejection details."""
        tx = cls.get_by_tx_id(transaction_id)
        if not tx:
            return None

        now = datetime.now()
        update_fields = {
            "status": "FAILED",
            "error_code": str(error_code) if error_code else None,
            "error_message": str(error_message) if error_message else None,
            "update_time": current_timestamp(),
            "update_date": datetime_format(now),
        }
        if gateway_response is not None:
            update_fields["gateway_response"] = gateway_response
        if audit_note:
            update_fields["audit_note"] = audit_note

        cls.model.update(**update_fields).where(cls.model.id == tx.id).execute()
        return cls.get_by_tx_id(transaction_id)

    @classmethod
    @DB.connection_context()
    def cleanup_expired_pending(cls, expiry_minutes: int = 30) -> int:
        """Transition stale PENDING transactions older than expiry_minutes to EXPIRED status."""
        cutoff = datetime.now() - timedelta(minutes=expiry_minutes)
        updated_count = (
            cls.model.update(
                status="EXPIRED",
                error_message=f"Payment session expired after {expiry_minutes}m of inactivity",
                update_time=current_timestamp(),
                update_date=datetime_format(datetime.now()),
            )
            .where(
                (cls.model.status == "PENDING")
                & (cls.model.create_date < cutoff)
            )
            .execute()
        )
        return updated_count

    @classmethod
    @DB.connection_context()
    def get_transactions_paginated(
        cls,
        page: int = 1,
        page_size: int = 20,
        status: str = None,
        plan_type: str = None,
        email: str = None,
        search: str = None,
        date_from: str = None,
        date_to: str = None,
    ):
        """Query transactions with pagination and multi-field filters."""
        # Auto-expire abandoned PENDING sessions older than 30m
        try:
            cls.cleanup_expired_pending(expiry_minutes=30)
        except Exception:
            pass

        query = cls.model.select()

        if status:
            query = query.where(cls.model.status == str(status).upper())
        if plan_type:
            query = query.where(cls.model.plan_type == str(plan_type).lower())
        if email:
            query = query.where(cls.model.account_email == str(email).lower().strip())
        if search:
            s = f"%{search.strip()}%"
            query = query.where(
                (cls.model.account_email.contains(search))
                | (cls.model.transaction_id.contains(search))
            )
        if date_from:
            query = query.where(cls.model.create_date >= date_from)
        if date_to:
            query = query.where(cls.model.create_date <= date_to)

        total = query.count()
        p = max(1, int(page or 1))
        ps = max(1, min(100, int(page_size or 20)))
        records = query.order_by(cls.model.create_date.desc()).paginate(p, ps)

        return {
            "total": total,
            "page": p,
            "page_size": ps,
            "transactions": [r.to_dict() for r in records],
        }

    @classmethod
    @DB.connection_context()
    def get_analytics_summary(cls):
        """Calculate comprehensive financial KPIs and conversion analytics.

        Conversion includes ALL initiated transactions in the denominator (PAID, FAILED,
        EXPIRED, CANCELLED, PENDING) so abandoned checkouts properly register as drop-offs.
        """
        # Auto-expire abandoned PENDING sessions older than 30m
        try:
            cls.cleanup_expired_pending(expiry_minutes=30)
        except Exception:
            pass

        # 1. Total revenue and counts
        paid_records = list(
            cls.model.select(cls.model.paid_amount_uzs, cls.model.plan_type, cls.model.create_date)
            .where(cls.model.status == "PAID")
        )

        total_revenue_uzs = sum(r.paid_amount_uzs or 0 for r in paid_records)
        paid_count = len(paid_records)

        # 2. MRR (Revenue in the last 30 days)
        thirty_days_ago = datetime.now() - timedelta(days=30)
        mrr_uzs = sum(
            r.paid_amount_uzs or 0
            for r in paid_records
            if r.create_date and r.create_date >= thirty_days_ago
        )

        # 3. Overall conversion metrics across all sessions
        status_counts = dict(
            cls.model.select(cls.model.status, fn.COUNT(cls.model.id).alias("cnt"))
            .group_by(cls.model.status)
            .tuples()
        )
        total_initiated = sum(status_counts.values()) or 0
        conversion_rate_pct = round((paid_count / total_initiated * 100.0), 1) if total_initiated > 0 else 0.0

        # 4. Plan breakdown (Count + Revenue per plan)
        plan_breakdown = {}
        for r in paid_records:
            pt = (r.plan_type or "other").lower()
            if pt not in plan_breakdown:
                plan_breakdown[pt] = {"count": 0, "revenue_uzs": 0}
            plan_breakdown[pt]["count"] += 1
            plan_breakdown[pt]["revenue_uzs"] += int(r.paid_amount_uzs or 0)

        return {
            "total_revenue_uzs": total_revenue_uzs,
            "mrr_uzs": mrr_uzs,
            "total_initiated_count": total_initiated,
            "total_paid_count": paid_count,
            "conversion_rate_pct": conversion_rate_pct,
            "status_distribution": status_counts,
            "plan_breakdown": plan_breakdown,
        }
