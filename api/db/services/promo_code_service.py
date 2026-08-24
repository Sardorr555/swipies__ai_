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
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from api.db.db_models import DB, PromoCode, PromoCodeUsage
from common.time_utils import current_timestamp

logger = logging.getLogger(__name__)


class PromoCodeService:
    """Service handling promo code creation, validation, discounts calculation, and usage auditing."""

    @classmethod
    @DB.connection_context()
    def validate_and_apply_promo(
        cls,
        code: str,
        user_id: str,
        purpose: str,
        original_amount_usd: float,
        plan_id: str = "",
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Validates promo code eligibility and calculates discount or bonus credit.
        Returns (is_valid, message, details_dict).
        """
        clean_code = (code or "").strip().upper()
        if not clean_code:
            return False, "Промокод не указан.", {}

        promo = PromoCode.get_or_none(PromoCode.code == clean_code)
        if not promo:
            return False, "Неверный промокод или срок действия истек.", {}

        if not promo.is_active:
            return False, "Этот промокод деактивирован.", {}

        now_ts = current_timestamp()
        if promo.expires_at and promo.expires_at < now_ts:
            return False, "Срок действия промокода истек.", {}

        if promo.max_uses > 0 and promo.used_count >= promo.max_uses:
            return False, "Лимит использований данного промокода исчерпан.", {}

        # Check if user already used this promo
        if user_id:
            used = PromoCodeUsage.select().where(
                PromoCodeUsage.promo_code_id == promo.id,
                PromoCodeUsage.user_id == user_id,
            ).exists()
            if used:
                return False, "Вы уже использовали этот промокод.", {}

        # Purpose check
        clean_purpose = purpose.lower().strip()
        if promo.applies_to != "all":
            if promo.applies_to == "subscription" and clean_purpose != "subscription_upgrade":
                return False, "Этот промокод применим только для покупки подписок Plus/Pro.", {}
            if promo.applies_to == "advertiser_deposit" and clean_purpose != "advertiser_deposit":
                return False, "Этот промокод применим только для пополнения баланса рекламодателя.", {}

        # Plan check if specific plan required
        if promo.plan_id and plan_id:
            if promo.plan_id.lower().strip() != plan_id.lower().strip():
                return False, f"Этот промокод действует только для тарифа {promo.plan_id.upper()}.", {}

        # Calculate discount
        discount_usd = 0.0
        bonus_usd = 0.0
        final_amount_usd = float(original_amount_usd)

        if promo.discount_type == "percent":
            discount_usd = round(original_amount_usd * (promo.discount_value / 100.0), 2)
            final_amount_usd = max(0.50, original_amount_usd - discount_usd)
        elif promo.discount_type == "fixed_usd":
            discount_usd = min(promo.discount_value, original_amount_usd - 0.50)
            discount_usd = max(0.0, discount_usd)
            final_amount_usd = max(0.50, original_amount_usd - discount_usd)
        elif promo.discount_type == "advertiser_bonus_usd":
            bonus_usd = promo.discount_value
            final_amount_usd = original_amount_usd

        return True, "Промокод успешно применен!", {
            "promo_code_id": promo.id,
            "code": promo.code,
            "discount_type": promo.discount_type,
            "discount_value": promo.discount_value,
            "discount_usd": discount_usd,
            "bonus_usd": bonus_usd,
            "original_amount_usd": original_amount_usd,
            "final_amount_usd": round(final_amount_usd, 2),
        }

    @classmethod
    @DB.connection_context()
    def record_promo_usage(cls, promo_code_id: str, user_id: str, order_id: str, discount_applied: float = 0.0):
        """Records promo code redemption in the audit ledger and increments counter."""
        try:
            promo = PromoCode.get_or_none(PromoCode.id == promo_code_id)
            if promo:
                promo.used_count += 1
                promo.update_time = current_timestamp()
                promo.save()

                PromoCodeUsage.create(
                    id=uuid.uuid4().hex[:32],
                    promo_code_id=promo.id,
                    user_id=user_id,
                    order_id=order_id,
                    discount_applied=discount_applied,
                    create_time=current_timestamp(),
                )
        except Exception as e:
            logger.warning(f"Error recording promo code usage: {e}")

    @classmethod
    @DB.connection_context()
    def create_promo_code(
        cls,
        code: str,
        discount_type: str = "percent",
        discount_value: float = 20.0,
        applies_to: str = "all",
        plan_id: str = "",
        max_uses: int = 100,
        expires_days: Optional[int] = 30,
    ) -> PromoCode:
        """Create a new promotional code."""
        clean_code = code.strip().upper()
        now_ts = current_timestamp()
        expires_at = (now_ts + (expires_days * 86400 * 1000)) if expires_days else None

        return PromoCode.create(
            id=uuid.uuid4().hex[:32],
            code=clean_code,
            discount_type=discount_type,
            discount_value=float(discount_value),
            applies_to=applies_to,
            plan_id=plan_id.lower().strip() if plan_id else None,
            max_uses=int(max_uses),
            used_count=0,
            is_active=True,
            expires_at=expires_at,
            create_time=now_ts,
            update_time=now_ts,
        )

    @classmethod
    @DB.connection_context()
    def list_promo_codes(cls) -> List[Dict[str, Any]]:
        """List all promo codes with stats for admin overview."""
        codes = list(PromoCode.select().order_by(PromoCode.create_time.desc()).limit(100))
        return [{
            "id": p.id,
            "code": p.code,
            "discount_type": p.discount_type,
            "discount_value": p.discount_value,
            "applies_to": p.applies_to,
            "plan_id": p.plan_id or "all",
            "max_uses": p.max_uses,
            "used_count": p.used_count,
            "is_active": p.is_active,
            "expires_at": p.expires_at,
            "created_at": p.create_time,
        } for p in codes]

    @classmethod
    @DB.connection_context()
    def toggle_promo_code(cls, promo_id: str) -> Optional[PromoCode]:
        promo = PromoCode.get_or_none(PromoCode.id == promo_id)
        if promo:
            promo.is_active = not promo.is_active
            promo.update_time = current_timestamp()
            promo.save()
        return promo

    @classmethod
    @DB.connection_context()
    def delete_promo_code(cls, promo_id: str) -> bool:
        promo = PromoCode.get_or_none(PromoCode.id == promo_id)
        if promo:
            promo.delete_instance()
            return True
        return False
