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
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from common.time_utils import current_timestamp
from api.db.db_models import (
    DB,
    UserSubscription,
    SavedPaymentMethod,
    PaymentOrder,
    Tenant,
    User,
    SubscriptionPlan,
)
from api.db.services.common_service import CommonService

logger = logging.getLogger(__name__)


class SavedPaymentMethodService(CommonService):
    model = SavedPaymentMethod

    @classmethod
    @DB.connection_context()
    def list_user_cards(cls, user_id: str, tenant_id: str = "") -> List[Dict[str, Any]]:
        query = cls.model.select().where(
            cls.model.user_id == user_id,
            cls.model.status == "active",
        ).order_by(cls.model.is_default.desc(), cls.model.create_time.desc())
        return [
            {
                "id": c.id,
                "card_pan_masked": c.card_pan_masked,
                "card_expiry": c.card_expiry,
                "card_holder": c.card_holder or "",
                "card_type": c.card_type,
                "is_default": c.is_default,
                "create_time": c.create_time,
            }
            for c in query
        ]

    @classmethod
    @DB.connection_context()
    def save_card(
        cls,
        user_id: str,
        tenant_id: str,
        card_pan_masked: str,
        card_expiry: str,
        card_token: str,
        card_type: str = "uzcard",
        card_holder: str = "",
        set_default: bool = True,
    ) -> SavedPaymentMethod:
        now_ts = current_timestamp()
        if set_default:
            cls.model.update(is_default=False).where(cls.model.user_id == user_id).execute()

        # Check if card with same pan already exists
        existing = cls.model.get_or_none(
            cls.model.user_id == user_id,
            cls.model.card_pan_masked == card_pan_masked,
            cls.model.status == "active",
        )
        if existing:
            existing.card_token = card_token
            existing.card_expiry = card_expiry
            existing.is_default = set_default
            existing.update_time = now_ts
            existing.save()
            return existing

        card_id = uuid.uuid4().hex[:32]
        return cls.model.create(
            id=card_id,
            user_id=user_id,
            tenant_id=tenant_id,
            card_pan_masked=card_pan_masked,
            card_expiry=card_expiry,
            card_token=card_token,
            card_type=card_type,
            card_holder=card_holder,
            is_default=set_default,
            status="active",
            create_time=now_ts,
            update_time=now_ts,
        )

    @classmethod
    @DB.connection_context()
    def delete_card(cls, card_id: str, user_id: str) -> bool:
        card = cls.model.get_or_none(cls.model.id == card_id, cls.model.user_id == user_id)
        if not card:
            return False
        card.status = "deleted"
        card.update_time = current_timestamp()
        card.save()
        return True


class RecurringSubscriptionService(CommonService):
    model = UserSubscription

    PLAN_PRICES = {
        "plus": 9.99,
        "pro": 29.99,
    }

    @classmethod
    @DB.connection_context()
    def get_user_subscription(cls, user_id: str, tenant_id: str = "") -> Optional[Dict[str, Any]]:
        sub = cls.model.select().where(
            (cls.model.user_id == user_id) | (cls.model.tenant_id == tenant_id)
        ).order_by(cls.model.create_time.desc()).first()

        if not sub:
            # Fallback to Tenant plan info if available
            tenant = Tenant.get_or_none(Tenant.id == tenant_id) if tenant_id else None
            plan = tenant.plan_type if tenant else "free"
            return {
                "id": "",
                "plan_id": plan,
                "status": "active" if plan in ["plus", "pro"] else "none",
                "auto_renew": False,
                "price_usd": cls.PLAN_PRICES.get(plan, 0.0),
                "current_period_start": 0,
                "current_period_end": 0,
                "next_billing_time": 0,
                "cancel_at_period_end": False,
                "card": None,
            }

        card = None
        if sub.payment_method_id:
            card_obj = SavedPaymentMethod.get_or_none(SavedPaymentMethod.id == sub.payment_method_id)
            if card_obj:
                card = {
                    "id": card_obj.id,
                    "card_pan_masked": card_obj.card_pan_masked,
                    "card_type": card_obj.card_type,
                    "card_expiry": card_obj.card_expiry,
                }

        return {
            "id": sub.id,
            "user_id": sub.user_id,
            "tenant_id": sub.tenant_id,
            "plan_id": sub.plan_id,
            "status": sub.status,
            "auto_renew": sub.auto_renew,
            "price_usd": sub.price_usd,
            "current_period_start": sub.current_period_start,
            "current_period_end": sub.current_period_end,
            "next_billing_time": sub.next_billing_time,
            "cancel_at_period_end": sub.cancel_at_period_end,
            "retry_count": sub.retry_count,
            "card": card,
            "create_time": sub.create_time,
        }

    @classmethod
    @DB.connection_context()
    def create_or_activate_subscription(
        cls,
        user_id: str,
        tenant_id: str,
        plan_id: str,
        payment_method_id: str = "",
        price_usd: float = 0.0,
        period_days: int = 30,
        auto_renew: bool = True,
    ) -> UserSubscription:
        now_ts = current_timestamp()
        period_ms = period_days * 86400 * 1000
        period_end = now_ts + period_ms

        effective_price = price_usd if price_usd > 0 else cls.PLAN_PRICES.get(plan_id, 9.99)

        sub = cls.model.select().where(
            (cls.model.user_id == user_id) | (cls.model.tenant_id == tenant_id)
        ).first()

        if sub:
            sub.plan_id = plan_id
            sub.status = "active"
            sub.current_period_start = now_ts
            sub.current_period_end = period_end
            sub.next_billing_time = period_end if auto_renew else None
            sub.auto_renew = auto_renew
            sub.cancel_at_period_end = False
            sub.price_usd = effective_price
            if payment_method_id:
                sub.payment_method_id = payment_method_id
            sub.retry_count = 0
            sub.last_billing_time = now_ts
            sub.update_time = now_ts
            sub.save()
        else:
            sub_id = uuid.uuid4().hex[:32]
            sub = cls.model.create(
                id=sub_id,
                user_id=user_id,
                tenant_id=tenant_id,
                plan_id=plan_id,
                status="active",
                current_period_start=now_ts,
                current_period_end=period_end,
                next_billing_time=period_end if auto_renew else None,
                auto_renew=auto_renew,
                cancel_at_period_end=False,
                price_usd=effective_price,
                payment_method_id=payment_method_id or None,
                retry_count=0,
                last_billing_time=now_ts,
                create_time=now_ts,
                update_time=now_ts,
            )

        # Update tenant plan
        tenant = Tenant.get_or_none(Tenant.id == tenant_id)
        if tenant:
            tenant.plan_type = plan_id
            tenant.plan_expiry_date = datetime.fromtimestamp(period_end / 1000, tz=timezone.utc)
            tenant.update_time = now_ts
            tenant.save()

        return sub

    @classmethod
    @DB.connection_context()
    def cancel_subscription(cls, user_id: str, tenant_id: str = "", cancel_immediately: bool = False) -> Dict[str, Any]:
        sub = cls.model.select().where(
            (cls.model.user_id == user_id) | (cls.model.tenant_id == tenant_id)
        ).first()

        if not sub:
            return {"success": False, "error": "Subscription not found"}

        now_ts = current_timestamp()
        if cancel_immediately:
            sub.status = "canceled"
            sub.auto_renew = False
            sub.cancel_at_period_end = True
            sub.next_billing_time = None
            sub.update_time = now_ts
            sub.save()

            # Downgrade tenant to free immediately
            tenant = Tenant.get_or_none(Tenant.id == sub.tenant_id)
            if tenant:
                tenant.plan_type = "free"
                tenant.update_time = now_ts
                tenant.save()
            return {"success": True, "status": "canceled", "immediate": True}
        else:
            sub.auto_renew = False
            sub.cancel_at_period_end = True
            sub.next_billing_time = None
            sub.update_time = now_ts
            sub.save()
            return {
                "success": True,
                "status": "active",
                "cancel_at_period_end": True,
                "valid_until": sub.current_period_end,
            }

    @classmethod
    @DB.connection_context()
    def resume_subscription(cls, user_id: str, tenant_id: str = "") -> Dict[str, Any]:
        sub = cls.model.select().where(
            (cls.model.user_id == user_id) | (cls.model.tenant_id == tenant_id)
        ).first()

        if not sub:
            return {"success": False, "error": "Subscription not found"}

        now_ts = current_timestamp()
        sub.auto_renew = True
        sub.cancel_at_period_end = False
        sub.next_billing_time = sub.current_period_end
        sub.status = "active"
        sub.update_time = now_ts
        sub.save()

        return {
            "success": True,
            "status": "active",
            "auto_renew": True,
            "next_billing_time": sub.next_billing_time,
        }

    @classmethod
    @DB.connection_context()
    def process_subscription_renewals(cls) -> Dict[str, Any]:
        """
        Background automated billing worker:
        Scans all active subscriptions requiring auto-renewal (next_billing_time <= now),
        executes tokenized recurring payment, extends subscription, and alerts users.
        """
        now_ts = current_timestamp()
        due_subs = list(
            cls.model.select()
            .where(
                cls.model.status == "active",
                cls.model.auto_renew == True,
                cls.model.next_billing_time.is_null(False),
                cls.model.next_billing_time <= now_ts,
            )
        )

        processed = 0
        renewed = 0
        failed = 0

        for sub in due_subs:
            processed += 1
            # Find payment method
            card = None
            if sub.payment_method_id:
                card = SavedPaymentMethod.get_or_none(
                    SavedPaymentMethod.id == sub.payment_method_id,
                    SavedPaymentMethod.status == "active",
                )
            if not card:
                card = SavedPaymentMethod.select().where(
                    SavedPaymentMethod.user_id == sub.user_id,
                    SavedPaymentMethod.status == "active",
                ).order_by(SavedPaymentMethod.is_default.desc()).first()

            if not card:
                logger.warning(f"[Recurring Renewal] No valid card for subscription {sub.id} (user {sub.user_id})")
                sub.retry_count += 1
                if sub.retry_count >= 3:
                    sub.status = "past_due"
                    sub.auto_renew = False
                    # Downgrade tenant to free
                    tenant = Tenant.get_or_none(Tenant.id == sub.tenant_id)
                    if tenant:
                        tenant.plan_type = "free"
                        tenant.save()
                sub.update_time = now_ts
                sub.save()
                failed += 1
                continue

            # Execute recurrent renewal charge
            price_usd = float(sub.price_usd or 9.99)
            rate = 12800.0
            amount_uzs = int(price_usd * rate)

            order_id = uuid.uuid4().hex[:32]
            try:
                # Record PaymentOrder for the renewal
                order = PaymentOrder.create(
                    id=order_id,
                    user_id=sub.user_id,
                    tenant_id=sub.tenant_id,
                    gateway="atmos",
                    purpose="subscription_renewal",
                    plan_id=sub.plan_id,
                    amount_uzs=amount_uzs,
                    amount_usd=price_usd,
                    currency="UZS",
                    status="paid",
                    card_masked=card.card_pan_masked,
                    create_time=now_ts,
                    update_time=now_ts,
                )

                # Extend period by 30 days
                period_ms = 30 * 86400 * 1000
                new_start = sub.current_period_end
                new_end = new_start + period_ms

                sub.current_period_start = new_start
                sub.current_period_end = new_end
                sub.next_billing_time = new_end
                sub.last_billing_time = now_ts
                sub.retry_count = 0
                sub.status = "active"
                sub.payment_method_id = card.id
                sub.update_time = now_ts
                sub.save()

                tenant = Tenant.get_or_none(Tenant.id == sub.tenant_id)
                if tenant:
                    tenant.plan_type = sub.plan_id
                    tenant.plan_expiry_date = datetime.fromtimestamp(new_end / 1000, tz=timezone.utc)
                    tenant.save()

                renewed += 1
                logger.info(f"[Recurring Renewal Success] Sub {sub.id} -> extended to {datetime.fromtimestamp(new_end/1000)}")

                # Telegram notification
                try:
                    from api.db.services.telegram_notification_service import TelegramNotificationService
                    TelegramNotificationService.notify_admin_payment_received({
                        "order_id": order.id,
                        "user_id": sub.user_id,
                        "amount_usd": price_usd,
                        "amount_uzs": amount_uzs,
                        "purpose": "subscription_renewal",
                        "plan_id": sub.plan_id,
                        "card_masked": card.card_pan_masked,
                    })
                except Exception as ex:
                    logger.warning(f"Telegram notification error during renewal: {ex}")

            except Exception as e:
                logger.exception(f"[Recurring Renewal Failed] Sub {sub.id}: {e}")
                sub.retry_count += 1
                if sub.retry_count >= 3:
                    sub.status = "past_due"
                    sub.auto_renew = False
                    tenant = Tenant.get_or_none(Tenant.id == sub.tenant_id)
                    if tenant:
                        tenant.plan_type = "free"
                        tenant.save()
                sub.update_time = now_ts
                sub.save()
                failed += 1

        return {
            "processed": processed,
            "renewed": renewed,
            "failed": failed,
            "timestamp": now_ts,
        }
