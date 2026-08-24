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
import base64
import json
import logging
import os
import re
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple
import requests

from common.time_utils import current_timestamp
from api.db.db_models import (
    DB,
    PaymentOrder,
    Tenant,
    User,
    Advertiser,
    SubscriptionPlan,
)
from api.db.services.common_service import CommonService
from api.db.services.ad_engine_service import AdEngineService
from api.db.services.ai_policy_service import AIPolicyManager

logger = logging.getLogger(__name__)


class PaymentOrderService(CommonService):
    model = PaymentOrder


class AtmosService:
    """
    Atmos Payment Gateway Service for Uzcard, Humo, Visa, and Mastercard.
    Handles:
      1. OAuth2 client credential token acquisition & caching.
      2. Card transaction creation (tiyins).
      3. Pre-apply / SMS OTP dispatch.
      4. Apply / OTP verification.
      5. Instant fulfillment (Subscription upgrade with ad-free perk OR Advertiser balance top-up).
    """

    _cached_token: Optional[str] = None
    _token_expiry_ts: float = 0.0

    @classmethod
    def _get_config(cls) -> Dict[str, Any]:
        from common import settings
        mock_env = os.getenv("ATMOS_MOCK_MODE", "").lower() in ["true", "1", "yes"]
        return {
            "key": os.getenv("ATMOS_KEY", getattr(settings, "ATMOS_KEY", "TpLRLagJ1SXiZ0dT_om5BT_I3Nga")),
            "secret": os.getenv("ATMOS_SECRET", getattr(settings, "ATMOS_SECRET", "bMH7gjat2EgI3fTXoLJX7CRUcbAa")),
            "store_id": str(os.getenv("ATMOS_STORE_ID", getattr(settings, "ATMOS_STORE_ID", "100506"))),
            "base_url": os.getenv("ATMOS_BASE_URL", getattr(settings, "ATMOS_BASE_URL", "https://apigw.atmos.uz")).rstrip("/"),
            "mock_mode": mock_env or getattr(settings, "ATMOS_MOCK_MODE", False),
            "usd_to_uzs_rate": float(os.getenv("USD_TO_UZS_RATE", getattr(settings, "USD_TO_UZS_RATE", 12800.0))),
        }

    @classmethod
    def mask_card(cls, card_number: str) -> str:
        if not card_number:
            return "****"
        clean = re.sub(r"\s+", "", str(card_number))
        if len(clean) < 10:
            return "****"
        return f"{clean[:4]} {clean[4:6]}** **** {clean[-4:]}"

    @classmethod
    def normalize_expiry(cls, expiry: str) -> str:
        """
        Normalizes card expiry string into YYMM format expected by Atmos API.
        Accepts MM/YY, MMYY, YY/MM, YYMM.
        """
        if not expiry:
            return ""
        clean = re.sub(r"[^0-9]", "", str(expiry))
        if len(clean) == 4:
            first_two = int(clean[:2])
            last_two = int(clean[2:])
            # If MMYY format (e.g. 1228 where 12 <= 12 and 28 > 12) -> convert to YYMM (2812)
            if 1 <= first_two <= 12 and last_two > 12:
                return f"{clean[2:4]}{clean[:2]}"
        return clean

    @classmethod
    def analyze_atmos_error(cls, data: dict) -> dict:
        if not data:
            return {"is102": False, "message": "Unknown error", "message_ru": "Неизвестная ошибка платежного шлюза."}

        code = data.get("result", {}).get("code") or data.get("code")
        hint = data.get("hint")
        desc = data.get("result", {}).get("description") or data.get("message") or data.get("description") or ""

        is_102 = (
            code == 102
            or hint == 102
            or "102" in str(code)
            or "102" in str(hint)
            or "102" in str(desc)
        )

        if is_102:
            return {
                "is102": True,
                "code": 102,
                "hint": hint or 102,
                "message": "SMS gateway error (code 102): SMS was not sent. Ensure SMS notification service is active on the Uzcard/Humo card in bank app or ATM.",
                "message_ru": "Ошибка СМС-шлюза (код 102): СМС с кодом подтверждения не отправлено. Убедитесь, что на карте Uzcard/Humo подключена услуга СМС-информирования (в мобильном приложении банка или банкомате).",
            }

        return {
            "is102": False,
            "code": code,
            "hint": hint,
            "message": desc or "Atmos gateway error.",
            "message_ru": desc or "Ошибка проведения платежа через Atmos.",
        }

    @classmethod
    def get_atmos_token(cls) -> str:
        """Fetch and cache Atmos OAuth2 bearer token."""
        conf = cls._get_config()
        if conf["mock_mode"]:
            return "mock-atmos-token"

        now = time.time()
        if cls._cached_token and now < cls._token_expiry_ts:
            return cls._cached_token

        key = conf["key"]
        secret = conf["secret"]
        auth_header = base64.b64encode(f"{key}:{secret}".encode("utf-8")).decode("utf-8")

        token_url = f"{conf['base_url']}/token"
        logger.info(f"[Atmos Auth] Requesting token from {token_url}")

        try:
            resp = requests.post(
                token_url,
                headers={
                    "Authorization": f"Basic {auth_header}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data="grant_type=client_credentials",
                timeout=15,
            )
            if resp.status_code != 200:
                logger.error(f"[Atmos Auth Failed] Status: {resp.status_code}, Body: {resp.text}")
                raise Exception(f"Atmos auth failed with status {resp.status_code}: {resp.text}")

            data = resp.json()
            token = data.get("access_token")
            expires_in = int(data.get("expires_in", 3600))

            cls._cached_token = token
            # Refresh 5 minutes before expiration
            cls._token_expiry_ts = now + max(60, expires_in - 300)
            logger.info(f"[Atmos Auth Success] Token obtained (valid for {expires_in}s)")
            return token
        except Exception as e:
            logger.exception(f"[Atmos Auth Exception] {e}")
            raise

    @classmethod
    @DB.connection_context()
    def create_payment_order(
        cls,
        user_id: str,
        tenant_id: str,
        purpose: str,  # "subscription_upgrade" or "advertiser_deposit"
        amount_uzs: Optional[int] = None,
        amount_usd: Optional[float] = None,
        plan_id: Optional[str] = None,
        advertiser_id: Optional[str] = None,
        account_email: Optional[str] = None,
        lang: str = "ru",
        promo_code: Optional[str] = None,
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Initializes an Atmos payment order for subscription upgrade or advertiser wallet top-up.
        Supports promo codes for discounts and bonus credits.
        """
        conf = cls._get_config()
        rate = conf["usd_to_uzs_rate"]

        # Calculate amounts
        if amount_uzs is not None and amount_uzs > 0:
            final_uzs = int(amount_uzs)
            final_usd = round(float(amount_uzs) / rate, 2) if amount_usd is None else float(amount_usd)
        elif amount_usd is not None and amount_usd > 0:
            final_usd = float(amount_usd)
            final_uzs = int(round(float(amount_usd) * rate))
        else:
            # If subscription upgrade, check predefined plan pricing
            if purpose == "subscription_upgrade" and plan_id:
                norm_plan = plan_id.lower().strip()
                if norm_plan == "plus":
                    final_usd = 9.99
                elif norm_plan == "pro":
                    final_usd = 29.99
                elif norm_plan == "enterprise":
                    final_usd = 99.00
                else:
                    final_usd = 9.99
                final_uzs = int(round(final_usd * rate))
            else:
                return False, "Сумма платежа не указана или некорректна.", None

        # Apply Promo Code if provided
        promo_info = None
        if promo_code and promo_code.strip():
            try:
                from api.db.services.promo_code_service import PromoCodeService
                valid, msg, p_details = PromoCodeService.validate_and_apply_promo(
                    code=promo_code,
                    user_id=user_id,
                    purpose=purpose,
                    original_amount_usd=final_usd,
                    plan_id=plan_id or "",
                )
                if not valid:
                    return False, f"Ошибка применения промокода: {msg}", None
                promo_info = p_details
                final_usd = p_details["final_amount_usd"]
                final_uzs = int(round(final_usd * rate))
            except Exception as e:
                logger.warning(f"Promo code application error: {e}")

        # Resolve user email for account field
        resolved_email = account_email
        if not resolved_email:
            u = User.get_or_none(User.id == user_id)
            if u and u.email:
                resolved_email = u.email
            else:
                resolved_email = f"user_{user_id[:8]}@swipies.app"

        order_id = uuid.uuid4().hex[:32]
        now_ts = current_timestamp()

        # Call Atmos create transaction API
        external_tx_id = None
        if conf["mock_mode"]:
            external_tx_id = f"mock-tx-{order_id[:10]}"
        else:
            try:
                token = cls.get_atmos_token()
                create_payload = {
                    "amount": final_uzs * 100,  # Atmos requires amount in tiyins (1 UZS = 100 tiyins)
                    "account": resolved_email,
                    "store_id": str(conf["store_id"]),
                    "lang": lang,
                }
                logger.info(f"[Atmos Pay Create Payload] {create_payload}")

                resp = requests.post(
                    f"{conf['base_url']}/merchant/pay/create",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                    json=create_payload,
                    timeout=20,
                )
                data = resp.json()
                logger.info(f"[Atmos Pay Create Response] status={resp.status_code} body={data}")

                err_info = cls.analyze_atmos_error(data)
                tx_id = data.get("transaction_id")

                if not tx_id:
                    error_msg = err_info.get("message_ru") or "Не удалось создать транзакцию в Atmos."
                    return False, error_msg, {"detail": data}

                external_tx_id = str(tx_id)
            except Exception as e:
                logger.exception(f"[Atmos Create Order Exception] {e}")
                return False, f"Ошибка соединения с платежным шлюзом Atmos: {e}", None

        # Create PaymentOrder in database
        try:
            order = PaymentOrder.create(
                id=order_id,
                user_id=user_id,
                tenant_id=tenant_id,
                gateway="atmos",
                external_transaction_id=external_tx_id,
                purpose=purpose,
                plan_id=plan_id,
                advertiser_id=advertiser_id,
                amount_uzs=final_uzs,
                amount_usd=final_usd,
                currency="UZS",
                status="pending",
                metadata={
                    "account_email": resolved_email,
                    "store_id": conf["store_id"],
                    "exchange_rate": rate,
                    "promo_info": promo_info,
                },
                create_time=now_ts,
                update_time=now_ts,
            )
            return True, "Транзакция успешно создана.", {
                "order_id": order.id,
                "transaction_id": external_tx_id,
                "amount_uzs": final_uzs,
                "amount_usd": final_usd,
                "purpose": purpose,
                "plan_id": plan_id,
                "advertiser_id": advertiser_id,
                "currency": "UZS",
                "status": "pending",
            }
        except Exception as e:
            logger.exception(f"[PaymentOrder DB Insert Error] {e}")
            return False, f"Ошибка сохранения заказа в БД: {e}", None

    @classmethod
    @DB.connection_context()
    def pre_apply_card(
        cls,
        order_id: str,
        card_number: str,
        expiry: str,
        user_id: str = "",
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Sends card details to Atmos to request SMS OTP verification code.
        """
        order = PaymentOrder.get_or_none(PaymentOrder.id == order_id)
        if not order:
            return False, "Заказ на оплату не найден.", None

        if order.status == "paid":
            return False, "Заказ уже оплачен.", None

        if user_id and order.user_id != user_id:
            return False, "Доступ запрещен: этот заказ принадлежит другому пользователю.", None

        conf = cls._get_config()
        clean_card = re.sub(r"\s+", "", str(card_number))
        norm_expiry = cls.normalize_expiry(expiry)

        if len(clean_card) < 16:
            return False, "Некорректный номер карты (должно быть 16 цифр).", None
        if len(norm_expiry) != 4:
            return False, "Некорректный срок действия карты (формат MM/YY).", None

        masked = cls.mask_card(clean_card)

        if conf["mock_mode"] or (order.external_transaction_id and order.external_transaction_id.startswith("mock-tx-")):
            order.status = "waiting_otp"
            order.card_masked = masked
            order.phone_masked = "+998 90 *** ** 99"
            order.update_time = current_timestamp()
            order.save()
            return True, "Код подтверждения отправлен по СМС.", {
                "order_id": order.id,
                "status": "waiting_otp",
                "phone_masked": "+998 90 *** ** 99",
                "card_masked": masked,
            }

        try:
            token = cls.get_atmos_token()
            payload = {
                "transaction_id": int(order.external_transaction_id),
                "card_number": clean_card,
                "expiry": norm_expiry,
                "store_id": str(conf["store_id"]),
            }
            logger.info(f"[Atmos Pre-Apply Request] order_id={order.id} card={masked} expiry={norm_expiry}")

            resp = requests.post(
                f"{conf['base_url']}/merchant/pay/pre-apply",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=25,
            )
            data = resp.json()
            logger.info(f"[Atmos Pre-Apply Response] status={resp.status_code} body={data}")

            err_info = cls.analyze_atmos_error(data)
            res_code = data.get("result", {}).get("code") or data.get("code")
            is_success = (
                res_code in ["OK", 1, "1", 0, "0"]
                or data.get("status") == "waiting_otp"
                or (resp.status_code == 200 and not err_info.get("is102") and not res_code)
            )

            if not is_success or err_info.get("is102"):
                error_msg = err_info.get("message_ru") or "Не удалось отправить СМС-код для карты."
                order.error_message = error_msg
                order.save()
                return False, error_msg, {"detail": data, "hint": data.get("hint")}

            phone = data.get("phone") or data.get("phone_number") or ""
            order.status = "waiting_otp"
            order.card_masked = masked
            order.phone_masked = phone
            order.update_time = current_timestamp()
            order.save()

            return True, "Код подтверждения отправлен по СМС.", {
                "order_id": order.id,
                "status": "waiting_otp",
                "phone_masked": phone,
                "card_masked": masked,
            }
        except Exception as e:
            logger.exception(f"[Atmos Pre-Apply Exception] {e}")
            return False, f"Ошибка при отправке СМС через Atmos: {e}", None

    @classmethod
    @DB.connection_context()
    def apply_otp(
        cls,
        order_id: str,
        otp: str,
        user_id: str = "",
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Confirms SMS OTP with Atmos, completes payment, and triggers instant fulfillment
        (Subscription upgrade to Plus/Pro with ad-free perk OR Advertiser balance credit).
        """
        order = PaymentOrder.get_or_none(PaymentOrder.id == order_id)
        if not order:
            return False, "Заказ на оплату не найден.", None

        if order.status == "paid":
            return True, "Заказ уже успешно оплачен и активирован.", order.to_dict()

        if user_id and order.user_id != user_id:
            return False, "Доступ запрещен: этот заказ принадлежит другому пользователю.", None

        clean_otp = str(otp).strip()
        if not re.match(r"^\d{4,8}$", clean_otp):
            return False, "Код подтверждения должен состоять из цифр.", None

        conf = cls._get_config()

        if conf["mock_mode"] or (order.external_transaction_id and order.external_transaction_id.startswith("mock-tx-")):
            order.status = "paid"
            order.update_time = current_timestamp()
            order.save()
            fulfillment_res = cls._fulfill_paid_order(order)
            return True, "Оплата успешно завершена.", {
                "order_id": order.id,
                "status": "paid",
                "purpose": order.purpose,
                "plan_id": order.plan_id,
                "amount_usd": order.amount_usd,
                "amount_uzs": order.amount_uzs,
                "fulfillment": fulfillment_res,
            }

        try:
            token = cls.get_atmos_token()
            payload = {
                "transaction_id": int(order.external_transaction_id),
                "otp": clean_otp,
                "store_id": str(conf["store_id"]),
            }
            logger.info(f"[Atmos Apply Request] order_id={order.id} tx_id={order.external_transaction_id}")

            resp = requests.post(
                f"{conf['base_url']}/merchant/pay/apply",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=25,
            )
            data = resp.json()
            logger.info(f"[Atmos Apply Response] status={resp.status_code} body={data}")

            err_info = cls.analyze_atmos_error(data)
            res_code = data.get("result", {}).get("code") or data.get("code")
            is_success = res_code in ["OK", 1, "1", 0, "0"] or (resp.status_code == 200 and not res_code and not err_info.get("is102"))

            if not is_success:
                error_msg = err_info.get("message_ru") or "Неверный СМС-код или ошибка списания."
                order.error_message = error_msg
                order.save()
                return False, error_msg, {"detail": data}

            order.status = "paid"
            order.update_time = current_timestamp()
            order.save()

            fulfillment_res = cls._fulfill_paid_order(order)

            return True, "Оплата успешно подтверждена и обработана.", {
                "order_id": order.id,
                "status": "paid",
                "purpose": order.purpose,
                "plan_id": order.plan_id,
                "amount_usd": order.amount_usd,
                "amount_uzs": order.amount_uzs,
                "fulfillment": fulfillment_res,
            }
        except Exception as e:
            logger.exception(f"[Atmos Apply Exception] {e}")
            return False, f"Ошибка при подтверждении платежа в Atmos: {e}", None

    @classmethod
    @DB.connection_context()
    def _fulfill_paid_order(cls, order: PaymentOrder) -> Dict[str, Any]:
        """
        Executes immediate business logic for a paid order:
        - Subscription Upgrade: activates Plus / Pro plan for 30 days & removes all ads.
        - Advertiser Deposit: credits advertiser USD wallet balance and logs transaction.
        """
        logger.info(f"[Fulfill Payment Order] id={order.id} purpose={order.purpose} plan={order.plan_id}")

        result: Dict[str, Any] = {"success": True}

        if order.purpose == "subscription_upgrade":
            plan_name = (order.plan_id or "plus").lower().strip()
            tenant = Tenant.get_or_none(Tenant.id == order.tenant_id)
            if tenant:
                tenant.plan_type = plan_name
                now_dt = datetime.now(timezone.utc)
                # If existing plan is still active in future, extend by 30 days; otherwise now + 30 days
                if tenant.plan_expiry_date and tenant.plan_expiry_date > now_dt:
                    tenant.plan_expiry_date = tenant.plan_expiry_date + timedelta(days=30)
                else:
                    tenant.plan_expiry_date = now_dt + timedelta(days=30)
                tenant.save()

                # Reactivate BYOK models if upgraded to pro
                try:
                    AIPolicyManager.handle_subscription_upgrade(order.user_id, plan_name)
                except Exception as ex:
                    logger.warning(f"Error calling handle_subscription_upgrade: {ex}")

                result["plan_type"] = plan_name
                result["plan_expiry_date"] = tenant.plan_expiry_date.isoformat()
                result["message"] = f"Подписка {plan_name.upper()} успешно активирована. Реклама и брендинг отключены на 100%."
                logger.info(f"[Subscription Upgraded] Tenant {tenant.id} -> {plan_name}")
            else:
                logger.error(f"[Fulfill Error] Tenant {order.tenant_id} not found for order {order.id}")
                result["success"] = False
                result["error"] = "Tenant not found"

        elif order.purpose == "advertiser_deposit":
            adv_id = order.advertiser_id
            if not adv_id:
                # Find advertiser by tenant_id or user_id
                adv = Advertiser.get_or_none(Advertiser.tenant_id == order.tenant_id)
                if adv:
                    adv_id = adv.id

            if adv_id:
                deposit_usd = float(order.amount_usd or 0.0)
                desc = f"Пополнение через Atmos (Заказ #{order.id[:8]}, {order.amount_uzs:,} UZS)"
                deposit_ok = AdEngineService.deposit_balance(adv_id, deposit_usd, desc)
                result["advertiser_id"] = adv_id
                result["deposit_amount_usd"] = deposit_usd
                result["deposit_success"] = deposit_ok
                logger.info(f"[Advertiser Deposit Completed] adv={adv_id} +${deposit_usd}")
            else:
                logger.error(f"[Fulfill Error] Advertiser account not found for order {order.id}")
                result["success"] = False
                result["error"] = "Advertiser not found"

        # Process promo code bonus & redemption record
        promo_info = (order.metadata or {}).get("promo_info") if order.metadata else None
        if promo_info:
            try:
                from api.db.services.promo_code_service import PromoCodeService
                p_code_id = promo_info.get("promo_code_id")
                disc_applied = float(promo_info.get("discount_usd", 0.0))
                bonus_usd = float(promo_info.get("bonus_usd", 0.0))

                if p_code_id:
                    PromoCodeService.record_promo_usage(
                        promo_code_id=p_code_id,
                        user_id=order.user_id,
                        order_id=order.id,
                        discount_applied=disc_applied,
                    )

                if bonus_usd > 0 and order.purpose == "advertiser_deposit":
                    adv_id = result.get("advertiser_id")
                    if adv_id:
                        bonus_desc = f"Бонус по промокоду {promo_info.get('code', '')} (+${bonus_usd:.2f})"
                        AdEngineService.deposit_balance(adv_id, bonus_usd, bonus_desc)
                        logger.info(f"[Promo Bonus Credited] adv={adv_id} +${bonus_usd}")
            except Exception as e:
                logger.warning(f"Error executing promo code fulfillment: {e}")

        # Dispatch real-time Telegram notification to admin
        try:
            from api.db.services.telegram_notification_service import TelegramNotificationService
            TelegramNotificationService.notify_admin_payment_received({
                "order_id": order.id,
                "user_id": order.user_id,
                "amount_usd": order.amount_usd,
                "amount_uzs": order.amount_uzs,
                "purpose": order.purpose,
                "plan_id": order.plan_id or "",
                "card_masked": order.card_masked or "••••",
            })
        except Exception as e:
            logger.warning(f"Failed to dispatch Telegram payment notification: {e}")

        return result

    @classmethod
    @DB.connection_context()
    def get_order_details(cls, order_id: str, user_id: str = "") -> Optional[Dict[str, Any]]:
        order = PaymentOrder.get_or_none(PaymentOrder.id == order_id)
        if not order:
            return None
        if user_id and order.user_id != user_id:
            return None
        return order.to_dict()

    @classmethod
    @DB.connection_context()
    def get_user_orders(cls, user_id: str, tenant_id: str = "") -> list[Dict[str, Any]]:
        query = PaymentOrder.select().where(
            (PaymentOrder.user_id == user_id) | (PaymentOrder.tenant_id == tenant_id)
        ).order_by(PaymentOrder.create_time.desc()).limit(50)
        return [o.to_dict() for o in query]
