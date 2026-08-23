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
from quart import Blueprint, request

from api.apps import current_user, login_required
from api.db.services.payment_service import AtmosService, PaymentOrderService
from api.utils.api_utils import (
    get_data_error_result,
    get_json_result,
    get_request_json,
)
from common.constants import RetCode

# Define page_name so __init__.py mounts this blueprint at /v1/payment
page_name = "payment"
logger = logging.getLogger(__name__)


# ==========================================
# Atmos Card Payment Routes
# ==========================================


@manager.route("/atmos/create", methods=["POST"])  # noqa: F821
@login_required
async def create_atmos_payment():
    """
    Creates an Atmos payment order for either:
    1. Subscription Upgrade ("subscription_upgrade"): activates Plus or Pro plan with 100% ad removal.
    2. Advertiser Wallet Deposit ("advertiser_deposit"): credits advertising account balance.
    """
    req = await get_request_json()
    if not req:
        return get_data_error_result(message="Request payload is required.")

    purpose = req.get("purpose", "subscription_upgrade")
    plan_id = req.get("plan_id")
    advertiser_id = req.get("advertiser_id")
    amount_uzs = req.get("amount_uzs")
    amount_usd = req.get("amount_usd")
    lang = req.get("lang", "ru")

    if purpose not in ["subscription_upgrade", "advertiser_deposit"]:
        return get_data_error_result(message="Invalid purpose. Must be 'subscription_upgrade' or 'advertiser_deposit'.")

    if purpose == "subscription_upgrade" and not plan_id:
        return get_data_error_result(message="plan_id (e.g. 'plus' or 'pro') is required for subscription upgrade.")

    user_id = current_user.id
    tenant_id = getattr(current_user, "tenant_id", None) or user_id
    email = getattr(current_user, "email", None)

    success, msg, data = AtmosService.create_payment_order(
        user_id=user_id,
        tenant_id=tenant_id,
        purpose=purpose,
        amount_uzs=amount_uzs,
        amount_usd=amount_usd,
        plan_id=plan_id,
        advertiser_id=advertiser_id,
        account_email=email,
        lang=lang,
    )

    if not success:
        return get_data_error_result(message=msg, data=data)

    return get_json_result(data=data, message=msg)


@manager.route("/atmos/pre-apply", methods=["POST"])  # noqa: F821
@login_required
async def pre_apply_card():
    """
    Submits card number & expiry to Atmos and triggers SMS OTP dispatch to cardholder.
    """
    req = await get_request_json()
    if not req:
        return get_data_error_result(message="Request payload is required.")

    order_id = req.get("order_id")
    card_number = req.get("card_number")
    expiry = req.get("expiry")

    if not order_id or not card_number or not expiry:
        return get_data_error_result(message="order_id, card_number, and expiry (MM/YY) are required.")

    success, msg, data = AtmosService.pre_apply_card(
        order_id=order_id,
        card_number=card_number,
        expiry=expiry,
        user_id=current_user.id,
    )

    if not success:
        return get_data_error_result(message=msg, data=data)

    return get_json_result(data=data, message=msg)


@manager.route("/atmos/apply", methods=["POST"])  # noqa: F821
@login_required
async def apply_otp():
    """
    Submits SMS OTP, completes payment, and triggers instant fulfillment
    (Subscription upgrade to Plus/Pro with ad-free perk OR Advertiser balance credit).
    """
    req = await get_request_json()
    if not req:
        return get_data_error_result(message="Request payload is required.")

    order_id = req.get("order_id")
    otp = req.get("otp")

    if not order_id or not otp:
        return get_data_error_result(message="order_id and otp are required.")

    success, msg, data = AtmosService.apply_otp(
        order_id=order_id,
        otp=otp,
        user_id=current_user.id,
    )

    if not success:
        return get_data_error_result(message=msg, data=data)

    return get_json_result(data=data, message=msg)


@manager.route("/orders", methods=["GET"])  # noqa: F821
@login_required
async def list_user_payment_orders():
    """
    Returns user's payment transaction history.
    """
    user_id = current_user.id
    tenant_id = getattr(current_user, "tenant_id", None) or user_id
    orders = AtmosService.get_user_orders(user_id=user_id, tenant_id=tenant_id)
    return get_json_result(data=orders)


@manager.route("/orders/<order_id>", methods=["GET"])  # noqa: F821
@login_required
async def get_order_status(order_id: str):
    """
    Returns single payment order details.
    """
    order = AtmosService.get_order_details(order_id, user_id=current_user.id)
    if not order:
        return get_data_error_result(message="Payment order not found.", code=RetCode.NOT_FOUND)
    return get_json_result(data=order)


@manager.route("/atmos/webhook", methods=["POST"])  # noqa: F821
async def atmos_webhook():
    """
    Asynchronous callback webhook endpoint for Atmos gateway status notifications.
    """
    try:
        req = await get_request_json()
        logger.info(f"[Atmos Webhook Callback] payload={req}")
        return get_json_result(data={"received": True})
    except Exception as e:
        logger.warning(f"[Atmos Webhook Error] {e}")
        return get_json_result(data={"received": False, "error": str(e)})
