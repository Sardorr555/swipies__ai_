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
import csv
import io
import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from quart import Blueprint, redirect, request, g, Response

from api.apps import current_user, login_required
from api.db.db_models import (
    DB,
    Advertiser,
    AdCampaign,
    AdVariant,
    AdImpression,
    AdClick,
    AdTransaction,
    AdSettings,
    PromoCode,
    PromoCodeUsage,
    User,
)
from api.db.services.ad_engine_service import (
    AdvertiserService,
    AdCampaignService,
    AdVariantService,
    AdImpressionService,
    AdClickService,
    AdTransactionService,
    AdSettingsService,
    AdEngineService,
    AttributionService,
)
from api.db.services.ad_policy_service import AdPolicyService
from api.db.services.promo_code_service import PromoCodeService
from api.db.services.telegram_notification_service import TelegramNotificationService
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
                "negative_keywords": getattr(c, "negative_keywords", []) or [],
                "target_languages": c.target_languages or [],
                "target_models": c.target_models or [],
                "target_countries": c.target_countries or [],
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


@manager.route("/campaigns/generate-copy", methods=["POST"])
@login_required
async def generate_campaign_copy():
    """AI Assistant to create high-converting ad copy and keywords from product info."""
    req = await get_request_json() or {}
    product_name = req.get("product_name", "").strip()
    landing_url = req.get("landing_url", "").strip()
    description = req.get("description", "").strip()
    lang = req.get("lang", "ru").lower().strip()

    if not product_name:
        return get_json_result(data=False, message="product_name is required", code=RetCode.ARGUMENT_ERROR)

    if lang == "uz":
        variations = [
            f"{product_name} — Biznesingiz uchun tezkor va ishonchli yechim. Hoziroq sinab koring!",
            f"30 kunlik bepul sinov muddati {product_name} bilan! 1 daqiqada ulanish.",
            f"{product_name} yordamida vaqtingizni va byudjetingizni tejang. Tafsilotlar saytda.",
        ]
        keywords = ["biznes", "avtomatlashtirish", "xizmat", "dastur", "toshkent", "onlayn", "tezkor", "qulay"]
        negatives = ["bepul skachat", "kod", "torrent", "vzlom"]
        categories = ["software", "business", "services"]
    elif lang == "en":
        variations = [
            f"Supercharge your workflow with {product_name}. Start your 14-day free trial today!",
            f"Looking for the best {product_name}? Get started with instant setup and 24/7 support.",
            f"Scale faster with {product_name}. Trusted by leading teams worldwide.",
        ]
        keywords = ["saas", "software", "productivity", "automation", "cloud", "platform", "business", "tools"]
        negatives = ["free download", "crack", "torrent", "open source github"]
        categories = ["saas", "software", "business"]
    else:  # Russian default
        variations = [
            f"{product_name} — Простое и эффективное решение для вашего бизнеса. Попробуйте прямо сейчас!",
            f"Получите 30 дней бесплатного доступа к {product_name}. Мгновенное подключение без карты.",
            f"Автоматизируйте рутину с помощью {product_name}. Увеличьте продажи и сэкономьте время!",
        ]
        keywords = ["бизнес", "автоматизация", "сервис", "онлайн", "crm", "рост продаж", "эффективность", "инструмент"]
        negatives = ["скачать бесплатно", "взлом", "кряк", "торрент", "слив"]
        categories = ["software", "business", "services"]

    return get_json_result(data={
        "ad_copy_variations": variations,
        "recommended_keywords": keywords,
        "recommended_negative_keywords": negatives,
        "recommended_categories": categories,
        "recommended_bid": 0.20,
    })


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
            negative_keywords=req.get("negative_keywords", []),
            target_languages=req.get("target_languages", []),
            target_models=req.get("target_models", []),
            target_countries=req.get("target_countries", []),
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

        # Dispatch real-time Telegram notification to admin
        TelegramNotificationService.notify_admin_new_campaign(cmp, advertiser_name=adv.company_name)

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
        if "negative_keywords" in req:
            cmp.negative_keywords = req["negative_keywords"]
        if "target_languages" in req:
            cmp.target_languages = req["target_languages"]
        if "target_models" in req:
            cmp.target_models = req["target_models"]
        if "target_countries" in req:
            cmp.target_countries = req["target_countries"]
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


@manager.route("/analytics/timeline", methods=["GET"])
@login_required
async def get_advertiser_timeline():
    try:
        user_id = current_user.id
        tenant_id = getattr(current_user, "tenant_id", "") or user_id
        days = int(request.args.get("days", 14))
        data = AdEngineService.get_advertiser_timeline_analytics(user_id=user_id, tenant_id=tenant_id, days=days)
        return get_json_result(data=data)
    except Exception as e:
        logger.exception(f"Error fetching advertiser timeline analytics: {e}")
        return get_data_error_result(message=str(e))


@manager.route("/campaigns/<campaign_id>/analytics/detailed", methods=["GET"])
@login_required
async def get_campaign_analytics_detailed(campaign_id):
    try:
        user_id = current_user.id
        tenant_id = getattr(current_user, "tenant_id", "") or user_id
        adv = AdvertiserService.get_or_create_for_user(user_id, tenant_id)
        days = int(request.args.get("days", 14))
        data = AdEngineService.get_campaign_analytics_detailed(campaign_id=campaign_id, advertiser_id=adv.id, days=days)
        return get_json_result(data=data)
    except Exception as e:
        logger.exception(f"Error fetching detailed campaign analytics: {e}")
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


@manager.route("/r/ref/<user_id>", methods=["GET"])
async def attribution_redirect(user_id):
    """
    Public redirect handler for AI response watermark links.
    Tracks which user account the traffic came from and redirects to landing page with UTM tags.
    """
    try:
        client_ip = request.headers.get("X-Forwarded-For", request.remote_addr or "")
        user_agent = request.headers.get("User-Agent", "")
        utm_source = request.args.get("utm_source", "chat_watermark")
        utm_medium = request.args.get("utm_medium", "ai_response")
        utm_campaign = request.args.get("utm_campaign", "share_attribution")
        utm_content = request.args.get("utm_content", "")

        AttributionService.record_attribution_visit(
            referrer_id=user_id,
            utm_source=utm_source,
            utm_medium=utm_medium,
            utm_campaign=utm_campaign,
            utm_content=utm_content,
            ip=client_ip,
            user_agent=user_agent,
        )

        target_url = AdPolicyService.build_attribution_url(user_id=user_id)
        return redirect(target_url, code=302)
    except Exception as e:
        logger.warning(f"Attribution redirect error: {e}")
        return redirect("https://swipies.app", code=302)


@manager.route("/attribution/stats", methods=["GET"])
@login_required
async def get_my_attribution_stats():
    """Returns UTM attribution and chat watermark analytics for the current user."""
    try:
        data = AttributionService.get_attribution_analytics(user_id=current_user.id)
        return get_json_result(data=data)
    except Exception as e:
        logger.exception(f"Error fetching attribution analytics: {e}")
        return get_data_error_result(message=str(e))


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
            "target_languages": c.target_languages or [],
            "target_models": c.target_models or [],
            "target_countries": c.target_countries or [],
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

        # Send Telegram notification
        TelegramNotificationService.notify_admin_campaign_moderated(cmp.name, "approved")

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

        # Send Telegram notification
        TelegramNotificationService.notify_admin_campaign_moderated(cmp.name, "rejected", note=note)

        return get_json_result(data={"id": cmp.id, "moderation_status": cmp.moderation_status, "note": note})
    except Exception as e:
        logger.exception(f"Error rejecting campaign: {e}")
        return get_data_error_result(message=str(e))


@manager.route("/admin/analytics/overview-timeline", methods=["GET"])
@login_required
async def get_admin_analytics_timeline():
    auth_err = require_superuser()
    if auth_err:
        return auth_err
    try:
        days = int(request.args.get("days", 14))
        data = AdEngineService.get_admin_network_timeline(days=days)
        return get_json_result(data=data)
    except Exception as e:
        logger.exception(f"Error fetching admin timeline analytics: {e}")
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


# ==========================================
# 5. Promo Codes Management & Validation
# ==========================================

@manager.route("/promo/validate", methods=["POST"])
@login_required
async def validate_promo_code():
    req = await get_request_json() or {}
    code = req.get("code", "").strip()
    purpose = req.get("purpose", "subscription_upgrade").strip()
    amount_usd = float(req.get("amount_usd", 10.0))
    plan_id = req.get("plan_id", "").strip()

    valid, msg, details = PromoCodeService.validate_and_apply_promo(
        code=code,
        user_id=current_user.id,
        purpose=purpose,
        original_amount_usd=amount_usd,
        plan_id=plan_id,
    )

    if not valid:
        return get_json_result(data=False, message=msg, code=RetCode.DATA_ERROR)

    return get_json_result(data=details, message=msg)


@manager.route("/admin/promo-codes", methods=["GET"])
@login_required
async def admin_list_promo_codes():
    auth_err = require_superuser()
    if auth_err:
        return auth_err

    try:
        codes = PromoCodeService.list_promo_codes()
        return get_json_result(data=codes)
    except Exception as e:
        logger.exception(f"Error listing promo codes: {e}")
        return get_data_error_result(message=str(e))


@manager.route("/admin/promo-codes", methods=["POST"])
@login_required
async def admin_create_promo_code():
    auth_err = require_superuser()
    if auth_err:
        return auth_err

    req = await get_request_json() or {}
    code = req.get("code", "").strip()
    if not code:
        return get_json_result(data=False, message="code is required", code=RetCode.ARGUMENT_ERROR)

    try:
        promo = PromoCodeService.create_promo_code(
            code=code,
            discount_type=req.get("discount_type", "percent"),
            discount_value=float(req.get("discount_value", 20.0)),
            applies_to=req.get("applies_to", "all"),
            plan_id=req.get("plan_id", ""),
            max_uses=int(req.get("max_uses", 100)),
            expires_days=int(req.get("expires_days", 30)) if req.get("expires_days") else None,
        )
        return get_json_result(data={"id": promo.id, "code": promo.code})
    except Exception as e:
        logger.exception(f"Error creating promo code: {e}")
        return get_data_error_result(message=str(e))


@manager.route("/admin/promo-codes/<promo_id>/toggle", methods=["PUT"])
@login_required
async def admin_toggle_promo_code(promo_id):
    auth_err = require_superuser()
    if auth_err:
        return auth_err

    try:
        promo = PromoCodeService.toggle_promo_code(promo_id)
        if not promo:
            return get_json_result(data=False, message="Promo code not found", code=RetCode.NOT_FOUND)
        return get_json_result(data={"id": promo.id, "is_active": promo.is_active})
    except Exception as e:
        logger.exception(f"Error toggling promo code: {e}")
        return get_data_error_result(message=str(e))


@manager.route("/admin/promo-codes/<promo_id>", methods=["DELETE"])
@login_required
async def admin_delete_promo_code(promo_id):
    auth_err = require_superuser()
    if auth_err:
        return auth_err

    try:
        deleted = PromoCodeService.delete_promo_code(promo_id)
        return get_json_result(data=deleted)
    except Exception as e:
        logger.exception(f"Error deleting promo code: {e}")
        return get_data_error_result(message=str(e))


# ==========================================
# 6. CSV & Report Data Export
# ==========================================

@manager.route("/export/transactions", methods=["GET"])
@login_required
async def export_transactions_csv():
    try:
        user_id = current_user.id
        tenant_id = getattr(current_user, "tenant_id", "") or user_id
        adv = AdvertiserService.get_or_create_for_user(user_id, tenant_id)

        txs = list(
            AdTransaction.select()
            .where(AdTransaction.advertiser_id == adv.id)
            .order_by(AdTransaction.create_time.desc())
            .limit(1000)
        )

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Transaction ID", "Type", "Amount (USD)", "Description", "Date"])

        for t in txs:
            dt_str = datetime.fromtimestamp(t.create_time / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S") if t.create_time else ""
            writer.writerow([t.id, t.type, f"{t.amount:.2f}", t.description or "", dt_str])

        csv_content = output.getvalue()
        return Response(
            csv_content,
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment; filename=swipies_transactions_{adv.id[:8]}.csv"},
        )
    except Exception as e:
        logger.exception(f"Error exporting transactions: {e}")
        return get_data_error_result(message=str(e))


@manager.route("/export/campaigns", methods=["GET"])
@login_required
async def export_campaigns_csv():
    try:
        user_id = current_user.id
        tenant_id = getattr(current_user, "tenant_id", "") or user_id
        adv = AdvertiserService.get_or_create_for_user(user_id, tenant_id)

        cmps = list(
            AdCampaign.select()
            .where(AdCampaign.advertiser_id == adv.id)
            .order_by(AdCampaign.create_time.desc())
        )

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Campaign ID",
            "Campaign Name",
            "Product",
            "Status",
            "Pricing Model",
            "Bid Amount",
            "Daily Budget",
            "Total Budget",
            "Total Spent",
            "Impressions",
            "Clicks",
            "CTR (%)",
            "Landing URL",
        ])

        for c in cmps:
            c_imps = AdImpression.select().where(AdImpression.campaign_id == c.id).count()
            c_clicks = AdClick.select().where(AdClick.campaign_id == c.id).count()
            c_ctr = (c_clicks / c_imps * 100.0) if c_imps > 0 else 0.0

            writer.writerow([
                c.id,
                c.name,
                c.product_name,
                c.status,
                c.pricing_model,
                f"{c.bid_amount:.2f}",
                f"{c.daily_budget:.2f}",
                f"{c.total_budget:.2f}",
                f"{c.total_spent:.2f}",
                c_imps,
                c_clicks,
                f"{c_ctr:.2f}",
                c.landing_url,
            ])

        csv_content = output.getvalue()
        return Response(
            csv_content,
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment; filename=swipies_campaigns_{adv.id[:8]}.csv"},
        )
    except Exception as e:
        logger.exception(f"Error exporting campaigns: {e}")
        return get_data_error_result(message=str(e))


# ------------------------------------------------------------------
# A/B Testing & Ad Variants
# ------------------------------------------------------------------


@manager.route("/campaigns/<campaign_id>/variants", methods=["GET"])
@login_required
def get_campaign_variants(campaign_id):
    try:
        adv = AdvertiserService.get_or_create_for_user(current_user.id, current_user.tenant_id)
        variants = AdVariantService.list_variants(campaign_id=campaign_id, advertiser_id=adv.id)
        return get_json_result(data=variants)
    except Exception as e:
        logger.exception(f"Error fetching campaign variants: {e}")
        return get_data_error_result(message=str(e))


@manager.route("/campaigns/<campaign_id>/variants", methods=["POST"])
@login_required
def create_campaign_variant(campaign_id):
    try:
        adv = AdvertiserService.get_or_create_for_user(current_user.id, current_user.tenant_id)
        cmp = AdCampaign.get_or_none(AdCampaign.id == campaign_id, AdCampaign.advertiser_id == adv.id)
        if not cmp:
            return get_data_error_result(message="Campaign not found")

        req = get_request_json() or {}
        adv_text = req.get("advertisement_text", "").strip()
        if not adv_text:
            return get_data_error_result(message="Advertisement text is required for variant")

        created = AdVariantService.create_variant(
            campaign_id=campaign_id,
            advertiser_id=adv.id,
            data=req,
        )
        return get_json_result(data=created)
    except Exception as e:
        logger.exception(f"Error creating campaign variant: {e}")
        return get_data_error_result(message=str(e))


@manager.route("/campaigns/<campaign_id>/variants/<variant_id>", methods=["PUT"])
@login_required
def update_campaign_variant(campaign_id, variant_id):
    try:
        adv = AdvertiserService.get_or_create_for_user(current_user.id, current_user.tenant_id)
        req = get_request_json() or {}
        updated = AdVariantService.update_variant(
            variant_id=variant_id,
            advertiser_id=adv.id,
            data=req,
        )
        if not updated:
            return get_data_error_result(message="Variant not found")
        return get_json_result(data=updated)
    except Exception as e:
        logger.exception(f"Error updating campaign variant: {e}")
        return get_data_error_result(message=str(e))


@manager.route("/campaigns/<campaign_id>/variants/<variant_id>/toggle", methods=["PUT"])
@login_required
def toggle_campaign_variant(campaign_id, variant_id):
    try:
        adv = AdvertiserService.get_or_create_for_user(current_user.id, current_user.tenant_id)
        toggled = AdVariantService.toggle_variant(
            variant_id=variant_id,
            advertiser_id=adv.id,
        )
        if not toggled:
            return get_data_error_result(message="Variant not found")
        return get_json_result(data=toggled)
    except Exception as e:
        logger.exception(f"Error toggling campaign variant: {e}")
        return get_data_error_result(message=str(e))


@manager.route("/campaigns/<campaign_id>/variants/<variant_id>", methods=["DELETE"])
@login_required
def delete_campaign_variant(campaign_id, variant_id):
    try:
        adv = AdvertiserService.get_or_create_for_user(current_user.id, current_user.tenant_id)
        success = AdVariantService.delete_variant(
            variant_id=variant_id,
            advertiser_id=adv.id,
        )
        if not success:
            return get_data_error_result(message="Variant not found")
        return get_json_result(data={"deleted": True})
    except Exception as e:
        logger.exception(f"Error deleting campaign variant: {e}")
        return get_data_error_result(message=str(e))


# ------------------------------------------------------------------
# Recurring Subscriptions & Saved Cards
# ------------------------------------------------------------------


@manager.route("/billing/subscription", methods=["GET"])
@login_required
def get_user_subscription():
    try:
        from api.db.services.recurring_subscription_service import RecurringSubscriptionService
        sub = RecurringSubscriptionService.get_user_subscription(current_user.id, current_user.tenant_id)
        return get_json_result(data=sub)
    except Exception as e:
        logger.exception(f"Error fetching subscription: {e}")
        return get_data_error_result(message=str(e))


@manager.route("/billing/subscription/cancel", methods=["POST"])
@login_required
def cancel_user_subscription():
    try:
        from api.db.services.recurring_subscription_service import RecurringSubscriptionService
        req = get_request_json() or {}
        immediate = bool(req.get("immediate", False))
        res = RecurringSubscriptionService.cancel_subscription(
            user_id=current_user.id,
            tenant_id=current_user.tenant_id,
            cancel_immediately=immediate,
        )
        return get_json_result(data=res)
    except Exception as e:
        logger.exception(f"Error canceling subscription: {e}")
        return get_data_error_result(message=str(e))


@manager.route("/billing/subscription/resume", methods=["POST"])
@login_required
def resume_user_subscription():
    try:
        from api.db.services.recurring_subscription_service import RecurringSubscriptionService
        res = RecurringSubscriptionService.resume_subscription(
            user_id=current_user.id,
            tenant_id=current_user.tenant_id,
        )
        return get_json_result(data=res)
    except Exception as e:
        logger.exception(f"Error resuming subscription: {e}")
        return get_data_error_result(message=str(e))


@manager.route("/billing/payment-methods", methods=["GET"])
@login_required
def get_user_payment_methods():
    try:
        from api.db.services.recurring_subscription_service import SavedPaymentMethodService
        cards = SavedPaymentMethodService.list_user_cards(current_user.id, current_user.tenant_id)
        return get_json_result(data=cards)
    except Exception as e:
        logger.exception(f"Error listing payment methods: {e}")
        return get_data_error_result(message=str(e))


@manager.route("/billing/payment-methods/<card_id>", methods=["DELETE"])
@login_required
def delete_user_payment_method(card_id):
    try:
        from api.db.services.recurring_subscription_service import SavedPaymentMethodService
        success = SavedPaymentMethodService.delete_card(card_id, current_user.id)
        if not success:
            return get_data_error_result(message="Card not found")
        return get_json_result(data={"deleted": True})
    except Exception as e:
        logger.exception(f"Error deleting payment method: {e}")
        return get_data_error_result(message=str(e))


@manager.route("/admin/subscriptions/process-renewals", methods=["POST"])
@login_required
def admin_process_subscription_renewals():
    try:
        from api.db.services.recurring_subscription_service import RecurringSubscriptionService
        res = RecurringSubscriptionService.process_subscription_renewals()
        return get_json_result(data=res)
    except Exception as e:
        logger.exception(f"Error processing subscription renewals: {e}")
        return get_data_error_result(message=str(e))


