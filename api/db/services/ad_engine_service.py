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
import json
import logging
import re
import time
import uuid
from datetime import datetime, timezone
from peewee import fn

from common.time_utils import current_timestamp
from api.db.db_models import (
    DB,
    Advertiser,
    AdCampaign,
    AdImpression,
    AdClick,
    AdTransaction,
    AdSettings,
    User,
    Tenant,
)
from api.db.services.common_service import CommonService

logger = logging.getLogger(__name__)


class AdvertiserService(CommonService):
    model = Advertiser

    @classmethod
    @DB.connection_context()
    def get_or_create_for_user(cls, user_id: str, tenant_id: str, company_name: str = "", contact_email: str = "") -> Advertiser:
        adv = cls.model.get_or_none(cls.model.user_id == user_id)
        if not adv:
            adv_id = uuid.uuid4().hex[:32]
            adv = cls.model.create(
                id=adv_id,
                tenant_id=tenant_id,
                user_id=user_id,
                company_name=company_name or f"Advertiser {user_id[:6]}",
                contact_email=contact_email,
                balance=0.0,
                currency="USD",
                status="active",
                create_time=current_timestamp(),
                update_time=current_timestamp(),
            )
        return adv


class AdCampaignService(CommonService):
    model = AdCampaign


class AdImpressionService(CommonService):
    model = AdImpression


class AdClickService(CommonService):
    model = AdClick


class AdTransactionService(CommonService):
    model = AdTransaction


class AdSettingsService(CommonService):
    model = AdSettings

    @classmethod
    @DB.connection_context()
    def get_setting(cls, key: str, default_val=None):
        record = cls.model.get_or_none(cls.model.key == key)
        if record:
            try:
                return json.loads(record.value)
            except Exception:
                return record.value
        return default_val

    @classmethod
    @DB.connection_context()
    def set_setting(cls, key: str, value, description: str = ""):
        val_str = json.dumps(value) if not isinstance(value, str) else value
        record = cls.model.get_or_none(cls.model.key == key)
        if record:
            record.value = val_str
            if description:
                record.description = description
            record.update_time = current_timestamp()
            record.save()
        else:
            cls.model.create(
                id=uuid.uuid4().hex[:32],
                key=key,
                value=val_str,
                description=description,
                update_time=current_timestamp(),
            )


class AdEngineService:
    """Core Swipies Ads Matching, Auction, Tracking, and Analytics Engine."""

    # Default frequency capping: maximum impressions per user per day per campaign
    DEFAULT_MAX_IMPRESSIONS_PER_USER_DAY = 3
    MIN_RELEVANCE_SCORE_THRESHOLD = 0.25

    @classmethod
    @DB.connection_context()
    def match_campaign_for_query(
        cls,
        tenant_id: str,
        user_id: str,
        user_query: str,
        conversation_id: str = "",
        message_id: str = "",
    ) -> dict | None:
        """
        Evaluate candidate ad campaigns for an incoming user prompt.
        Applies intent analysis, status/moderation checks, budget & balance verification,
        and frequency capping before ranking candidates.
        """
        if not user_query or not user_query.strip():
            return None

        # Check global feature flag from settings or DB
        from common.settings import ADS_ENABLED, ADS_TARGETING_ENABLED
        if not ADS_ENABLED or not ADS_TARGETING_ENABLED:
            return None

        clean_query = user_query.strip().lower()
        query_words = set(re.findall(r"\b\w{3,}\b", clean_query))

        now_dt = datetime.now(timezone.utc)
        now_ts = current_timestamp()
        day_start_ts = int(time.time() - (time.time() % 86400)) * 1000

        # Query all active, approved campaigns
        active_campaigns = list(
            AdCampaign.select(AdCampaign, Advertiser)
            .join(Advertiser, on=(AdCampaign.advertiser_id == Advertiser.id))
            .where(
                AdCampaign.status == "active",
                AdCampaign.moderation_status == "approved",
                Advertiser.status == "active",
            )
        )

        if not active_campaigns:
            return None

        candidates = []
        max_impressions = int(AdSettingsService.get_setting("max_impressions_per_user_day", cls.DEFAULT_MAX_IMPRESSIONS_PER_USER_DAY))

        for cmp in active_campaigns:
            adv = cmp.advertiser

            # 1. Budget and Balance Gate
            cost_per_event = float(cmp.bid_amount or 0.10)
            if adv.balance < cost_per_event:
                continue

            if cmp.total_budget > 0 and cmp.total_spent + cost_per_event > cmp.total_budget:
                continue

            if cmp.daily_budget > 0 and cmp.spent_today + cost_per_event > cmp.daily_budget:
                continue

            # 2. Date Range Gate
            if cmp.start_date and cmp.start_date.replace(tzinfo=timezone.utc) > now_dt:
                continue
            if cmp.end_date and cmp.end_date.replace(tzinfo=timezone.utc) < now_dt:
                continue

            # 3. Frequency Capping Gate (per user per day)
            if user_id:
                user_impressions_today = (
                    AdImpression.select()
                    .where(
                        AdImpression.campaign_id == cmp.id,
                        AdImpression.user_id == user_id,
                        AdImpression.create_time >= day_start_ts,
                    )
                    .count()
                )
                if user_impressions_today >= max_impressions:
                    continue

            # 4. Relevance & Intent Match
            keywords = [k.lower().strip() for k in (cmp.keywords or []) if k]
            categories = [c.lower().strip() for c in (cmp.target_categories or []) if c]
            target_terms = set(keywords + categories)

            # Keyword / Category overlap
            overlap_count = 0
            for term in target_terms:
                if term in clean_query:
                    overlap_count += 2
                elif any(word in term or term in word for word in query_words):
                    overlap_count += 1

            # Description / Product relevance
            desc_text = f"{cmp.product_name} {cmp.description or ''}".lower()
            for qw in query_words:
                if qw in desc_text:
                    overlap_count += 0.5

            if overlap_count <= 0:
                continue

            # Compute normalized score
            relevance_score = min(1.0, overlap_count / 3.0)
            normalized_bid = min(1.0, cost_per_event / 2.0)
            priority_score = min(1.0, cmp.priority / 10.0) if cmp.priority else 0.0

            total_score = (relevance_score * 0.50) + (normalized_bid * 0.30) + (priority_score * 0.20)

            if total_score >= cls.MIN_RELEVANCE_SCORE_THRESHOLD:
                candidates.append((total_score, cmp, cost_per_event))

        if not candidates:
            return None

        # Sort candidates descending by total score
        candidates.sort(key=lambda x: x[0], reverse=True)
        winner_score, winner_campaign, cost = candidates[0]

        # Record Impression
        impression_id = uuid.uuid4().hex[:32]
        try:
            AdImpression.create(
                id=impression_id,
                campaign_id=winner_campaign.id,
                advertiser_id=winner_campaign.advertiser_id,
                user_id=user_id or "",
                tenant_id=tenant_id or "",
                conversation_id=conversation_id or "",
                message_id=message_id or "",
                cost=(cost if winner_campaign.pricing_model == "cpm" else 0.0),
                query_intent=clean_query[:250],
                create_time=now_ts,
            )

            # Deduct balance if CPM model
            if winner_campaign.pricing_model == "cpm":
                winner_campaign.spent_today += cost
                winner_campaign.total_spent += cost
                winner_campaign.save()

                adv = winner_campaign.advertiser
                adv.balance = max(0.0, adv.balance - cost)
                adv.save()

                AdTransaction.create(
                    id=uuid.uuid4().hex[:32],
                    advertiser_id=adv.id,
                    amount=-cost,
                    type="spend_cpm",
                    description=f"CPM Impression on campaign {winner_campaign.name}",
                    reference_id=impression_id,
                    create_time=now_ts,
                )
        except Exception as e:
            logger.warning(f"Failed to record AdImpression: {e}")

        # Build clean campaign context with click tracking token
        click_token = f"{winner_campaign.id}_{impression_id}_{user_id or 'anon'}"
        tracking_url = f"/v1/ads/r/{click_token}"

        return {
            "id": winner_campaign.id,
            "impression_id": impression_id,
            "advertiser": winner_campaign.advertiser.company_name or "Verified Sponsor",
            "product": winner_campaign.product_name,
            "description": winner_campaign.description or "",
            "advertisement_text": winner_campaign.advertisement_text,
            "landing_url": winner_campaign.landing_url,
            "tracking_url": tracking_url,
            "target_categories": winner_campaign.target_categories or [],
        }

    @classmethod
    @DB.connection_context()
    def track_click(cls, click_token: str, user_id: str = "", ip_hash: str = "") -> str:
        """
        Record unique click for campaign, deduct CPC bid from advertiser balance,
        and return destination landing URL.
        """
        if not click_token:
            return "https://swipies.app"

        campaign = None
        impression = AdImpression.get_or_none(AdImpression.id == click_token)
        if impression:
            campaign = AdCampaign.get_or_none(AdCampaign.id == impression.campaign_id)
            campaign_id = impression.campaign_id
            impression_id = impression.id
            token_user_id = impression.user_id
        else:
            campaign = AdCampaign.get_or_none(AdCampaign.id == click_token)
            if campaign:
                campaign_id = campaign.id
                impression_id = ""
                token_user_id = user_id
            elif "_" in click_token:
                parts = click_token.rsplit("_", 2)
                if len(parts) == 3:
                    campaign_id, impression_id, token_user_id = parts
                elif len(parts) == 2:
                    campaign_id, impression_id = parts
                    token_user_id = user_id
                else:
                    campaign_id = parts[0]
                    impression_id = ""
                    token_user_id = user_id
                campaign = AdCampaign.get_or_none(AdCampaign.id == campaign_id)
            else:
                campaign_id = click_token
                impression_id = ""
                token_user_id = user_id
                campaign = AdCampaign.get_or_none(AdCampaign.id == campaign_id)

        if not campaign:
            return "https://swipies.app"

        now_ts = current_timestamp()
        cost = float(campaign.bid_amount or 0.10) if campaign.pricing_model == "cpc" else 0.0

        # Check deduplication within 1 hour
        one_hour_ago = now_ts - (3600 * 1000)
        recent_click = AdClick.select().where(
            AdClick.campaign_id == campaign.id,
            AdClick.impression_id == impression_id,
            AdClick.create_time >= one_hour_ago,
        ).first()

        if not recent_click:
            click_id = uuid.uuid4().hex[:32]
            AdClick.create(
                id=click_id,
                campaign_id=campaign.id,
                impression_id=impression_id,
                advertiser_id=campaign.advertiser_id,
                user_id=token_user_id or "",
                cost=cost,
                ip_hash=ip_hash[:64] if ip_hash else "",
                create_time=now_ts,
            )

            if cost > 0:
                campaign.spent_today += cost
                campaign.total_spent += cost
                campaign.save()

                adv = Advertiser.get_or_none(Advertiser.id == campaign.advertiser_id)
                if adv:
                    adv.balance = max(0.0, adv.balance - cost)
                    adv.save()

                    AdTransaction.create(
                        id=uuid.uuid4().hex[:32],
                        advertiser_id=adv.id,
                        amount=-cost,
                        type="spend_cpc",
                        description=f"CPC Click on campaign '{campaign.name}'",
                        reference_id=click_id,
                        create_time=now_ts,
                    )

        return campaign.landing_url or "https://swipies.app"

    @classmethod
    @DB.connection_context()
    def get_advertiser_dashboard(cls, user_id: str, tenant_id: str) -> dict:
        """Fetch summary metrics and active campaigns for advertiser portal."""
        adv = AdvertiserService.get_or_create_for_user(user_id, tenant_id)

        campaigns = list(
            AdCampaign.select()
            .where(AdCampaign.advertiser_id == adv.id)
            .order_by(AdCampaign.create_time.desc())
        )

        total_campaigns = len(campaigns)
        active_campaigns = sum(1 for c in campaigns if c.status == "active" and c.moderation_status == "approved")

        # Aggregate total impressions and clicks
        impressions_count = AdImpression.select().where(AdImpression.advertiser_id == adv.id).count()
        clicks_count = AdClick.select().where(AdClick.advertiser_id == adv.id).count()
        total_spend = sum(c.total_spent for c in campaigns)
        ctr = (clicks_count / impressions_count * 100.0) if impressions_count > 0 else 0.0

        # Build campaign objects
        campaign_list = []
        for c in campaigns:
            c_imps = AdImpression.select().where(AdImpression.campaign_id == c.id).count()
            c_clicks = AdClick.select().where(AdClick.campaign_id == c.id).count()
            c_ctr = (c_clicks / c_imps * 100.0) if c_imps > 0 else 0.0

            campaign_list.append({
                "id": c.id,
                "name": c.name,
                "product_name": c.product_name,
                "description": c.description,
                "advertisement_text": c.advertisement_text,
                "landing_url": c.landing_url,
                "keywords": c.keywords or [],
                "target_categories": c.target_categories or [],
                "daily_budget": c.daily_budget,
                "total_budget": c.total_budget,
                "spent_today": c.spent_today,
                "total_spent": c.total_spent,
                "pricing_model": c.pricing_model,
                "bid_amount": c.bid_amount,
                "status": c.status,
                "moderation_status": c.moderation_status,
                "moderation_note": c.moderation_note or "",
                "impressions": c_imps,
                "clicks": c_clicks,
                "ctr": round(c_ctr, 2),
                "created_at": c.create_time,
            })

        return {
            "advertiser_id": adv.id,
            "company_name": adv.company_name,
            "balance": round(adv.balance, 2),
            "currency": adv.currency,
            "active_campaigns": active_campaigns,
            "total_campaigns": total_campaigns,
            "total_impressions": impressions_count,
            "total_clicks": clicks_count,
            "total_spent": round(total_spend, 2),
            "ctr": round(ctr, 2),
            "campaigns": campaign_list,
        }

    @classmethod
    @DB.connection_context()
    def deposit_balance(cls, advertiser_id: str, amount: float, description: str = "Balance Top-Up") -> bool:
        """Credit funds to advertiser balance."""
        if amount <= 0:
            return False
        adv = Advertiser.get_or_none(Advertiser.id == advertiser_id)
        if not adv:
            return False

        adv.balance += amount
        adv.update_time = current_timestamp()
        adv.save()

        AdTransaction.create(
            id=uuid.uuid4().hex[:32],
            advertiser_id=adv.id,
            amount=amount,
            type="deposit",
            description=description,
            reference_id="",
            create_time=current_timestamp(),
        )
        return True

    @classmethod
    @DB.connection_context()
    def get_network_overview(cls) -> dict:
        """Network-wide analytics for admin panel."""
        total_advertisers = Advertiser.select().count()
        total_campaigns = AdCampaign.select().count()
        active_campaigns = AdCampaign.select().where(AdCampaign.status == "active", AdCampaign.moderation_status == "approved").count()
        pending_moderation = AdCampaign.select().where(AdCampaign.moderation_status == "pending").count()
        total_impressions = AdImpression.select().count()
        total_clicks = AdClick.select().count()
        total_revenue = sum(c.total_spent for c in AdCampaign.select())
        ctr = (total_clicks / total_impressions * 100.0) if total_impressions > 0 else 0.0

        return {
            "total_advertisers": total_advertisers,
            "total_campaigns": total_campaigns,
            "active_campaigns": active_campaigns,
            "pending_moderation": pending_moderation,
            "total_impressions": total_impressions,
            "total_clicks": total_clicks,
            "total_revenue": round(total_revenue, 2),
            "network_ctr": round(ctr, 2),
        }
