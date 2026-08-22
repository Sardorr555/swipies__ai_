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
import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from quart import Blueprint, redirect, request, g

from api.apps import current_user, login_required
from api.db.db_models import (
    DB,
    Advertiser,
    AdCampaign,
    AdImpression,
    AdClick,
    AdTransaction,
    AdSettings,
    User,
)
from api.db.services.ad_engine_service import (
    AdvertiserService,
    AdCampaignService,
    AdImpressionService,
    AdClickService,
    AdTransactionService,
    AdSettingsService,
    AdEngineService,
)
from api.utils.api_utils import (
    get_data_error_result,
    get_json_result,
    get_request_json,
)
from common.constants import RetCode
from common.time_utils import current_timestamp

logger = logging.getLogger(__name__)

# Mount blueprint at /v1/ads
page_name = "ads"


def require_superuser():
    if not getattr(current_user, "is_superuser", False):
        return get_json_result(
            data=False,
            message="Superuser authorization required.",
            code=RetCode.AUTHENTICATION_ERROR,
        )
    return None


# ==========================================
# 1. Advertiser Portal Endpoints
# ==========================================

@manager.route("/dashboard", methods=["GET"])
@login_required
async def get_dashboard():
    try:
        user_id = current_user.id
        tenant_id = getattr(current_user, "tenant_id", "") or user_id
        stats = AdEngineService.get_advertiser_dashboard(user_id=user_id, tenant_id=tenant_id)
        return get_json_result(data=stats)
    except Exception as e:
        logger.exception(f"Error fetching advertiser dashboard: {e}")
        return get_data_error_result(message=str(e))


@manager.route("/campaigns", methods=["GET"])
@login_required
async def list_campaigns():
    try:
        user_id = current_user.id
        tenant_id = getattr(current_user, "tenant_id", "") or user_id
        adv = AdvertiserService.get_or_create_for_user(user_id, tenant_id)

        campaigns = list(
            AdCampaign.select()
            .where(AdCampaign.advertiser_id == adv.id)
            .order_by(AdCampaign.create_time.desc())
        )

        result = []
        for c in campaigns:
            c_imps = AdImpression.select().where(AdImpression.campaign_id == c.id).count()
            c_clicks = AdClick.select().where(AdClick.campaign_id == c.id).count()
            c_ctr = (c_clicks / c_imps * 100.0) if c_imps > 0 else 0.0

            result.append({
                "id": c.id,
                "name": c.name,
                "product_name": c.product_name,
                "description": c.description or "",
                "advertisement_text": c.advertisement_text,
                "landing_url": c.landing_url,
                "target_categories": c.target_categories or [],
                "keywords": c.keywords or [],
                "daily_budget": c.daily_budget,
                "total_budget": c.total_budget,
                "spent_today": c.spent_today,
                "total_spent": c.total_spent,
                "pricing_model": c.pricing_model,
                "bid_amount": c.bid_amount,
                "priority": c.priority,
                "status": c.status,
                "moderation_status": c.moderation_status,
                "moderation_note": c.moderation_note or "",
                "impressions": c_imps,
                "clicks": c_clicks,
                "ctr": round(c_ctr, 2),
                "created_at": c.create_time,
            })
        return get_json_result(data=result)
    except Exception as e:
        logger.exception(f"Error listing campaigns: {e}")
        return get_data_error_result(message=str(e))


@manager.route("/campaigns", methods=["POST"])
@login_required
async def create_campaign():
    req = await get_request_json()
    if not req:
        return get_json_result(data=False, message="Empty payload", code=RetCode.ARGUMENT_ERROR)

    name = req.get("name", "").strip()
    product_name = req.get("product_name", "").strip()
    advertisement_text = req.get("advertisement_text", "").strip()
    landing_url = req.get("landing_url", "").strip()

    if not name or not product_name or not advertisement_text or not landing_url:
        return get_json_result(
            data=False,
            message="name, product_name, advertisement_text, and landing_url are required.",
            code=RetCode.ARGUMENT_ERROR,
        )

    try:
        user_id = current_user.id
        tenant_id = getattr(current_user, "tenant_id", "") or user_id
        adv = AdvertiserService.get_or_create_for_user(user_id, tenant_id)

        campaign_id = uuid.uuid4().hex[:32]
        cmp = AdCampaign.create(
            id=campaign_id,
            advertiser_id=adv.id,
            name=name,
            product_name=product_name,
            description=req.get("description", ""),
            advertisement_text=advertisement_text,
            landing_url=landing_url,
            target_categories=req.get("target_categories", []),
            keywords=req.get("keywords", []),
            daily_budget=float(req.get("daily_budget", 10.0)),
            total_budget=float(req.get("total_budget", 100.0)),
            spent_today=0.0,
            total_spent=0.0,
            pricing_model=req.get("pricing_model", "cpc"),
            bid_amount=float(req.get("bid_amount", 0.10)),
            priority=int(req.get("priority", 0)),
            status="active",
            moderation_status="approved",  # Auto-approve for seamless self-serve demo; admin can reject
            create_time=current_timestamp(),
            update_time=current_timestamp(),
        )

        return get_json_result(data={"id": cmp.id, "name": cmp.name, "status": cmp.status})
    except Exception as e:
        logger.exception(f"Error creating campaign: {e}")
        return get_data_error_result(message=str(e))


@manager.route("/campaigns/<campaign_id>", methods=["PUT"])
@login_required
async def update_campaign(campaign_id):
    req = await get_request_json()
    if not req:
        return get_json_result(data=False, message="Empty payload", code=RetCode.ARGUMENT_ERROR)

    try:
        user_id = current_user.id
        tenant_id = getattr(current_user, "tenant_id", "") or user_id
        adv = AdvertiserService.get_or_create_for_user(user_id, tenant_id)

        cmp = AdCampaign.get_or_none(AdCampaign.id == campaign_id, AdCampaign.advertiser_id == adv.id)
        if not cmp:
            return get_json_result(data=False, message="Campaign not found", code=RetCode.NOT_FOUND)

        for field in ["name", "product_name", "description", "advertisement_text", "landing_url", "pricing_model"]:
            if field in req:
                setattr(cmp, field, req[field])

        if "target_categories" in req:
            cmp.target_categories = req["target_categories"]
        if "keywords" in req:
            cmp.keywords = req["keywords"]
        if "daily_budget" in req:
            cmp.daily_budget = float(req["daily_budget"])
        if "total_budget" in req:
            cmp.total_budget = float(req["total_budget"])
        if "bid_amount" in req:
            cmp.bid_amount = float(req["bid_amount"])
        if "status" in req and req["status"] in ["active", "paused", "archived"]:
            cmp.status = req["status"]

        cmp.update_time = current_timestamp()
        cmp.save()

        return get_json_result(data={"id": cmp.id, "name": cmp.name, "status": cmp.status})
    except Exception as e:
        logger.exception(f"Error updating campaign: {e}")
        return get_data_error_result(message=str(e))


@manager.route("/campaigns/<campaign_id>/toggle_status", methods=["POST"])
@login_required
async def toggle_campaign_status(campaign_id):
    try:
        user_id = current_user.id
        tenant_id = getattr(current_user, "tenant_id", "") or user_id
        adv = AdvertiserService.get_or_create_for_user(user_id, tenant_id)

        cmp = AdCampaign.get_or_none(AdCampaign.id == campaign_id, AdCampaign.advertiser_id == adv.id)
        if not cmp:
            return get_json_result(data=False, message="Campaign not found", code=RetCode.NOT_FOUND)

        cmp.status = "paused" if cmp.status == "active" else "active"
        cmp.update_time = current_timestamp()
        cmp.save()

        return get_json_result(data={"id": cmp.id, "status": cmp.status})
    except Exception as e:
        logger.exception(f"Error toggling campaign status: {e}")
        return get_data_error_result(message=str(e))


@manager.route("/campaigns/<campaign_id>", methods=["DELETE"])
@login_required
async def delete_campaign(campaign_id):
    try:
        user_id = current_user.id
        tenant_id = getattr(current_user, "tenant_id", "") or user_id
        adv = AdvertiserService.get_or_create_for_user(user_id, tenant_id)

        cmp = AdCampaign.get_or_none(AdCampaign.id == campaign_id, AdCampaign.advertiser_id == adv.id)
        if not cmp:
            return get_json_result(data=False, message="Campaign not found", code=RetCode.NOT_FOUND)

        cmp.status = "archived"
        cmp.update_time = current_timestamp()
        cmp.save()

        return get_json_result(data=True)
    except Exception as e:
        logger.exception(f"Error deleting campaign: {e}")
        return get_data_error_result(message=str(e))


@manager.route("/campaigns/<campaign_id>/analytics", methods=["GET"])
@login_required
async def get_campaign_analytics(campaign_id):
    try:
        user_id = current_user.id
        tenant_id = getattr(current_user, "tenant_id", "") or user_id
        adv = AdvertiserService.get_or_create_for_user(user_id, tenant_id)

        cmp = AdCampaign.get_or_none(AdCampaign.id == campaign_id, AdCampaign.advertiser_id == adv.id)
        if not cmp:
            return get_json_result(data=False, message="Campaign not found", code=RetCode.NOT_FOUND)

        impressions = list(AdImpression.select().where(AdImpression.campaign_id == cmp.id).order_by(AdImpression.create_time.desc()).limit(50))
        clicks = list(AdClick.select().where(AdClick.campaign_id == cmp.id).order_by(AdClick.create_time.desc()).limit(50))

        return get_json_result(data={
            "campaign_id": cmp.id,
            "name": cmp.name,
            "total_impressions": len(impressions),
            "total_clicks": len(clicks),
            "total_spent": cmp.total_spent,
            "recent_impressions": [{"id": i.id, "query_intent": i.query_intent, "cost": i.cost, "time": i.create_time} for i in impressions[:10]],
            "recent_clicks": [{"id": c.id, "cost": c.cost, "time": c.create_time} for c in clicks[:10]],
        })
    except Exception as e:
        logger.exception(f"Error fetching campaign analytics: {e}")
        return get_data_error_result(message=str(e))


# ==========================================
# 2. Billing & Wallet Endpoints
# ==========================================

@manager.route("/billing/deposit", methods=["POST"])
@login_required
async def deposit_funds():
    req = await get_request_json()
    if not req:
        return get_json_result(data=False, message="Empty payload", code=RetCode.ARGUMENT_ERROR)

    amount = float(req.get("amount", 0.0))
    if amount <= 0:
        return get_json_result(data=False, message="Deposit amount must be greater than 0.", code=RetCode.ARGUMENT_ERROR)

    try:
        user_id = current_user.id
        tenant_id = getattr(current_user, "tenant_id", "") or user_id
        adv = AdvertiserService.get_or_create_for_user(user_id, tenant_id)

        success = AdEngineService.deposit_balance(
            advertiser_id=adv.id,
            amount=amount,
            description=req.get("description", "Top-Up Deposit"),
        )
        if success:
            adv.reload()
            return get_json_result(data={"balance": round(adv.balance, 2), "currency": adv.currency})
        return get_data_error_result(message="Deposit failed")
    except Exception as e:
        logger.exception(f"Error depositing funds: {e}")
        return get_data_error_result(message=str(e))


@manager.route("/billing/transactions", methods=["GET"])
@login_required
async def list_transactions():
    try:
        user_id = current_user.id
        tenant_id = getattr(current_user, "tenant_id", "") or user_id
        adv = AdvertiserService.get_or_create_for_user(user_id, tenant_id)

        txs = list(
            AdTransaction.select()
            .where(AdTransaction.advertiser_id == adv.id)
            .order_by(AdTransaction.create_time.desc())
            .limit(100)
        )

        result = [{
            "id": t.id,
            "amount": t.amount,
            "type": t.type,
            "description": t.description or "",
            "reference_id": t.reference_id or "",
            "created_at": t.create_time,
        } for t in txs]

        return get_json_result(data=result)
    except Exception as e:
        logger.exception(f"Error listing transactions: {e}")
        return get_data_error_result(message=str(e))


# ==========================================
# 3. Public Click Tracking & Redirect
# ==========================================

@manager.route("/r/<click_token>", methods=["GET"])
async def click_redirect(click_token):
    """Public redirect handler that tracks click metrics and forwards to sponsor URL."""
    try:
        client_ip = request.headers.get("X-Forwarded-For", request.remote_addr or "")
        ip_hash = hashlib.sha256(client_ip.encode("utf-8")).hexdigest()[:32] if client_ip else ""

        target_url = AdEngineService.track_click(
            click_token=click_token,
            ip_hash=ip_hash,
        )
        return redirect(target_url, code=302)
    except Exception as e:
        logger.warning(f"Click redirect error: {e}")
        return redirect("https://swipies.app", code=302)


# ==========================================
# 4. Admin Network Moderation & Controls
# ==========================================

@manager.route("/admin/overview", methods=["GET"])
@login_required
async def admin_overview():
    auth_err = require_superuser()
    if auth_err:
        return auth_err

    try:
        overview = AdEngineService.get_network_overview()
        return get_json_result(data=overview)
    except Exception as e:
        logger.exception(f"Error fetching admin overview: {e}")
        return get_data_error_result(message=str(e))


@manager.route("/admin/moderation", methods=["GET"])
@login_required
async def admin_moderation_queue():
    auth_err = require_superuser()
    if auth_err:
        return auth_err

    try:
        campaigns = list(
            AdCampaign.select(AdCampaign, Advertiser)
            .join(Advertiser, on=(AdCampaign.advertiser_id == Advertiser.id))
            .order_by(AdCampaign.create_time.desc())
            .limit(100)
        )

        result = [{
            "id": c.id,
            "advertiser_id": c.advertiser_id,
            "company_name": c.advertiser.company_name,
            "name": c.name,
            "product_name": c.product_name,
            "description": c.description or "",
            "advertisement_text": c.advertisement_text,
            "landing_url": c.landing_url,
            "status": c.status,
            "moderation_status": c.moderation_status,
            "moderation_note": c.moderation_note or "",
            "created_at": c.create_time,
        } for c in campaigns]

        return get_json_result(data=result)
    except Exception as e:
        logger.exception(f"Error fetching moderation queue: {e}")
        return get_data_error_result(message=str(e))


@manager.route("/admin/moderation/<campaign_id>/approve", methods=["POST"])
@login_required
async def admin_approve_campaign(campaign_id):
    auth_err = require_superuser()
    if auth_err:
        return auth_err

    try:
        cmp = AdCampaign.get_or_none(AdCampaign.id == campaign_id)
        if not cmp:
            return get_json_result(data=False, message="Campaign not found", code=RetCode.NOT_FOUND)

        cmp.moderation_status = "approved"
        cmp.moderation_note = "Approved by Administrator"
        cmp.update_time = current_timestamp()
        cmp.save()

        return get_json_result(data={"id": cmp.id, "moderation_status": cmp.moderation_status})
    except Exception as e:
        logger.exception(f"Error approving campaign: {e}")
        return get_data_error_result(message=str(e))


@manager.route("/admin/moderation/<campaign_id>/reject", methods=["POST"])
@login_required
async def admin_reject_campaign(campaign_id):
    auth_err = require_superuser()
    if auth_err:
        return auth_err

    req = await get_request_json() or {}
    note = req.get("note", "Rejected by Administrator due to policy non-compliance.")

    try:
        cmp = AdCampaign.get_or_none(AdCampaign.id == campaign_id)
        if not cmp:
            return get_json_result(data=False, message="Campaign not found", code=RetCode.NOT_FOUND)

        cmp.moderation_status = "rejected"
        cmp.moderation_note = note
        cmp.status = "paused"
        cmp.update_time = current_timestamp()
        cmp.save()

        return get_json_result(data={"id": cmp.id, "moderation_status": cmp.moderation_status, "note": note})
    except Exception as e:
        logger.exception(f"Error rejecting campaign: {e}")
        return get_data_error_result(message=str(e))


@manager.route("/admin/settings", methods=["GET"])
@login_required
async def get_admin_settings():
    auth_err = require_superuser()
    if auth_err:
        return auth_err

    try:
        from common.settings import (
            ADS_ENABLED,
            ADS_FOR_FREE_USERS,
            ADS_PLATFORM_BRANDING_ENABLED,
            ADS_LLM_PROMPT_ENABLED,
            ADS_TARGETING_ENABLED,
            ADS_BILLING_ENABLED,
            SWIPIES_APP_URL,
            SWIPIES_BRAND_NAME,
        )
        data = {
            "ads_enabled": ADS_ENABLED,
            "ads_for_free_users": ADS_FOR_FREE_USERS,
            "platform_branding_enabled": ADS_PLATFORM_BRANDING_ENABLED,
            "llm_prompt_enabled": ADS_LLM_PROMPT_ENABLED,
            "targeting_enabled": ADS_TARGETING_ENABLED,
            "billing_enabled": ADS_BILLING_ENABLED,
            "app_url": SWIPIES_APP_URL,
            "brand_name": SWIPIES_BRAND_NAME,
            "max_impressions_per_user_day": AdSettingsService.get_setting("max_impressions_per_user_day", 3),
        }
        return get_json_result(data=data)
    except Exception as e:
        logger.exception(f"Error fetching admin settings: {e}")
        return get_data_error_result(message=str(e))


@manager.route("/admin/settings", methods=["POST"])
@login_required
async def update_admin_settings():
    auth_err = require_superuser()
    if auth_err:
        return auth_err

    req = await get_request_json() or {}
    try:
        if "max_impressions_per_user_day" in req:
            AdSettingsService.set_setting(
                "max_impressions_per_user_day",
                int(req["max_impressions_per_user_day"]),
                "Maximum daily sponsor impressions per user",
            )
        return get_json_result(data=True)
    except Exception as e:
        logger.exception(f"Error updating admin settings: {e}")
        return get_data_error_result(message=str(e))
