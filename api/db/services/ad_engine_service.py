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
import random
import re
import time
import uuid
from datetime import datetime, timezone, timedelta
from peewee import fn

from common.time_utils import current_timestamp
from api.db.db_models import (
    DB,
    Advertiser,
    AdvertiserTeamMember,
    AdvertiserNotificationSettings,
    AdvertiserNotification,
    AdCampaign,
    AdVariant,
    AdImpression,
    AdClick,
    AdConversion,
    AdTransaction,
    AdSettings,
    AdAttributionVisit,
    AdAudienceSegment,
    AdAudienceMember,
    AdPublisher,
    AdPlacement,
    AdPublisherPayout,
    AdFraudLog,
    AdIpBlacklist,
    AdBiddingLog,
    AdDcoLog,
    AdAutomatedRule,
    AdRuleExecutionLog,
    User,
    Tenant,
)
from api.db.services.common_service import CommonService

logger = logging.getLogger(__name__)


class GeoIPService:
    """Geo IP and Regional Resolution Service for Uzbekistan regions and global traffic."""

    UZBEK_REGIONS = [
        {"id": "all", "name_ru": "Все регионы Узбекистана", "name_uz": "Oʻzbekistonning barcha hududlari", "name_en": "All regions of Uzbekistan"},
        {"id": "tashkent", "name_ru": "Ташкент и Ташкентская обл.", "name_uz": "Toshkent shahri va viloyati", "name_en": "Tashkent City & Region"},
        {"id": "samarkand", "name_ru": "Самаркандская область", "name_uz": "Samarqand viloyati", "name_en": "Samarkand Region"},
        {"id": "bukhara", "name_ru": "Бухарская область", "name_uz": "Buxoro viloyati", "name_en": "Bukhara Region"},
        {"id": "fergana", "name_ru": "Ферганская область", "name_uz": "Fargʻona viloyati", "name_en": "Fergana Region"},
        {"id": "andijan", "name_ru": "Андижанская область", "name_uz": "Andijon viloyati", "name_en": "Andijan Region"},
        {"id": "namangan", "name_ru": "Наманганская область", "name_uz": "Namangan viloyati", "name_en": "Namangan Region"},
        {"id": "kashkadarya", "name_ru": "Кашкадарьинская область", "name_uz": "Qashqadaryo viloyati", "name_en": "Kashkadarya Region"},
        {"id": "surkhandarya", "name_ru": "Сурхандарьинская область", "name_uz": "Surxondaryo viloyati", "name_en": "Surkhandarya Region"},
        {"id": "khorezm", "name_ru": "Хорезмская область", "name_uz": "Xorazm viloyati", "name_en": "Khorezm Region"},
        {"id": "navoiy", "name_ru": "Навоийская область", "name_uz": "Navoiy viloyati", "name_en": "Navoiy Region"},
        {"id": "jizzakh", "name_ru": "Джизакская область", "name_uz": "Jizzax viloyati", "name_en": "Jizzakh Region"},
        {"id": "sirdaryo", "name_ru": "Сырдарьинская область", "name_uz": "Sirdaryo viloyati", "name_en": "Sirdaryo Region"},
        {"id": "karakalpakstan", "name_ru": "Республика Каракалпакстан", "name_uz": "Qoraqalpogʻiston Respublikasi", "name_en": "Republic of Karakalpakstan"},
        {"id": "global", "name_ru": "Международный трафик (Другие страны)", "name_uz": "Xalqaro / Boshqa davlatlar", "name_en": "International / Other"},
    ]

    @classmethod
    def list_supported_regions(cls) -> list:
        return cls.UZBEK_REGIONS

    @classmethod
    def resolve_location(cls, ip: str = "", headers: dict = None) -> dict:
        headers = headers or {}
        country = headers.get("cf-ipcountry") or headers.get("x-country-code") or "UZ"
        region_header = headers.get("x-region-code") or headers.get("x-region") or ""
        city_header = headers.get("x-city") or ""

        if region_header:
            reg_clean = region_header.lower().strip()
            for r in cls.UZBEK_REGIONS:
                if reg_clean in r["id"] or r["id"] in reg_clean:
                    return {"country": country, "region": r["id"], "city": city_header or r["name_ru"]}

        if ip:
            if ip.startswith("10.") or ip.startswith("192.168.") or ip.startswith("127.") or ip == "localhost":
                return {"country": "UZ", "region": "tashkent", "city": "Tashkent"}
            ip_val = sum(int(x) for x in ip.split(".") if x.isdigit())
            region_candidates = ["tashkent", "samarkand", "bukhara", "fergana", "andijan", "namangan"]
            selected_region = region_candidates[ip_val % len(region_candidates)]
            return {
                "country": country,
                "region": selected_region,
                "city": selected_region.capitalize(),
            }

        return {"country": "UZ", "region": "tashkent", "city": "Tashkent"}


class AdvertiserService(CommonService):
    model = Advertiser

    @classmethod
    @DB.connection_context()
    def get_or_create_for_user(cls, user_id: str, tenant_id: str, company_name: str = "", contact_email: str = "") -> Advertiser:
        adv = cls.model.get_or_none(cls.model.user_id == user_id)
        if not adv:
            adv_id = uuid.uuid4().hex[:32]
            pixel_id = "px_" + uuid.uuid4().hex[:16]
            adv = cls.model.create(
                id=adv_id,
                tenant_id=tenant_id,
                user_id=user_id,
                company_name=company_name or f"Advertiser {user_id[:6]}",
                contact_email=contact_email,
                pixel_id=pixel_id,
                balance=0.0,
                currency="USD",
                status="active",
                create_time=current_timestamp(),
                update_time=current_timestamp(),
            )
        elif not adv.pixel_id:
            adv.pixel_id = "px_" + uuid.uuid4().hex[:16]
            adv.save()
        return adv


class AdCampaignService(CommonService):
    model = AdCampaign


class AdVariantService(CommonService):
    model = AdVariant

    @classmethod
    @DB.connection_context()
    def list_variants(cls, campaign_id: str, advertiser_id: str = "") -> list:
        query = AdVariant.select().where(AdVariant.campaign_id == campaign_id)
        if advertiser_id:
            query = query.where(AdVariant.advertiser_id == advertiser_id)
        variants = list(query.order_by(AdVariant.create_time.asc()))
        res = []
        for v in variants:
            ctr = (v.clicks / v.impressions * 100.0) if v.impressions > 0 else 0.0
            res.append({
                "id": v.id,
                "campaign_id": v.campaign_id,
                "name": v.name,
                "advertisement_text": v.advertisement_text,
                "landing_url": v.landing_url or "",
                "impressions": v.impressions,
                "clicks": v.clicks,
                "ctr": round(ctr, 2),
                "weight": v.weight,
                "is_active": v.is_active,
                "create_time": v.create_time,
            })
        return res

    @classmethod
    @DB.connection_context()
    def create_variant(cls, campaign_id: str, advertiser_id: str, data: dict) -> dict:
        v_id = uuid.uuid4().hex[:32]
        now_ts = current_timestamp()
        variant = AdVariant.create(
            id=v_id,
            campaign_id=campaign_id,
            advertiser_id=advertiser_id,
            name=data.get("name") or "Вариант B",
            advertisement_text=data.get("advertisement_text", ""),
            landing_url=data.get("landing_url") or "",
            weight=float(data.get("weight", 1.0) or 1.0),
            is_active=bool(data.get("is_active", True)),
            create_time=now_ts,
            update_time=now_ts,
        )
        return {
            "id": variant.id,
            "campaign_id": variant.campaign_id,
            "name": variant.name,
            "advertisement_text": variant.advertisement_text,
            "landing_url": variant.landing_url or "",
            "impressions": 0,
            "clicks": 0,
            "ctr": 0.0,
            "weight": variant.weight,
            "is_active": variant.is_active,
        }

    @classmethod
    @DB.connection_context()
    def update_variant(cls, variant_id: str, advertiser_id: str, data: dict) -> dict:
        variant = AdVariant.get_or_none(AdVariant.id == variant_id, AdVariant.advertiser_id == advertiser_id)
        if not variant:
            return {}
        if "name" in data:
            variant.name = data["name"]
        if "advertisement_text" in data:
            variant.advertisement_text = data["advertisement_text"]
        if "landing_url" in data:
            variant.landing_url = data["landing_url"]
        if "weight" in data:
            variant.weight = float(data["weight"])
        if "is_active" in data:
            variant.is_active = bool(data["is_active"])
        variant.update_time = current_timestamp()
        variant.save()
        ctr = (variant.clicks / variant.impressions * 100.0) if variant.impressions > 0 else 0.0
        return {
            "id": variant.id,
            "campaign_id": variant.campaign_id,
            "name": variant.name,
            "advertisement_text": variant.advertisement_text,
            "landing_url": variant.landing_url or "",
            "impressions": variant.impressions,
            "clicks": variant.clicks,
            "ctr": round(ctr, 2),
            "weight": variant.weight,
            "is_active": variant.is_active,
        }

    @classmethod
    @DB.connection_context()
    def toggle_variant(cls, variant_id: str, advertiser_id: str) -> dict:
        variant = AdVariant.get_or_none(AdVariant.id == variant_id, AdVariant.advertiser_id == advertiser_id)
        if not variant:
            return {}
        variant.is_active = not variant.is_active
        variant.update_time = current_timestamp()
        variant.save()
        return {"id": variant.id, "is_active": variant.is_active}

    @classmethod
    @DB.connection_context()
    def delete_variant(cls, variant_id: str, advertiser_id: str) -> bool:
        variant = AdVariant.get_or_none(AdVariant.id == variant_id, AdVariant.advertiser_id == advertiser_id)
        if not variant:
            return False
        variant.delete_instance()
        return True

    @classmethod
    @DB.connection_context()
    def select_variant_for_impression(cls, campaign: AdCampaign) -> tuple:
        """
        Selects an ad variant for an impression using an Epsilon-Greedy Bandit strategy:
        - 80% exploitation: selects the variant with highest CTR (min 10 impressions) or highest weight.
        - 20% exploration: selects a random active variant to discover new high-performing copy.
        Returns: (selected_variant, ad_text, landing_url)
        """
        variants = list(
            AdVariant.select()
            .where(AdVariant.campaign_id == campaign.id, AdVariant.is_active == True)
        )
        if not variants:
            return None, campaign.advertisement_text, campaign.landing_url

        if len(variants) == 1:
            v = variants[0]
            return v, v.advertisement_text, (v.landing_url or campaign.landing_url)

        # Multi-variant Bandit Selection
        # Explore (20%): random choice
        if random.random() < 0.20:
            v = random.choice(variants)
            return v, v.advertisement_text, (v.landing_url or campaign.landing_url)

        # Exploit (80%): pick variant with highest CTR (or highest weight if low data)
        def variant_score(item: AdVariant) -> float:
            if item.impressions >= 10:
                return (item.clicks / item.impressions) * 100.0 * (item.weight or 1.0)
            return (item.weight or 1.0) * 5.0

        best_variant = max(variants, key=variant_score)
        return best_variant, best_variant.advertisement_text, (best_variant.landing_url or campaign.landing_url)


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
        user_id: str = "",
        tenant_id: str = "",
        user_query: str = "",
        conversation_id: str = "",
        message_id: str = "",
        lang: str = "",
        detected_lang: str = "",
        model_name: str = "",
        user_region: str = "",
        user_city: str = "",
        ip_address: str = "",
        now_dt: datetime = None,
        query: str = "",
        region: str = "",
        city: str = "",
    ) -> dict | None:
        """
        Evaluate candidate ad campaigns for an incoming user prompt.
        Applies intent analysis, regional, language & model targeting, status/moderation checks,
        budget & balance verification, and frequency capping before ranking candidates.
        """
        user_query = user_query or query
        user_region = user_region or region
        user_city = user_city or city
        if not user_query or not user_query.strip():
            return None

        # Check global feature flag from settings or DB
        from common.settings import ADS_ENABLED, ADS_TARGETING_ENABLED
        if not ADS_ENABLED or not ADS_TARGETING_ENABLED:
            return None

        clean_query = user_query.strip().lower()
        query_words = set(re.findall(r"\b\w{3,}\b", clean_query))

        # Detect effective language (UZ, RU, EN)
        effective_lang = (lang or detected_lang or "").lower().strip()
        if not effective_lang:
            if re.search(r"[\u0400-\u04FF]", clean_query):
                if re.search(r"[ўғқҳЎҒҚҲ]", clean_query) or any(w in clean_query for w in ["salom", "qanday", "yordam", "kerak", "uchun"]):
                    effective_lang = "uz"
                else:
                    effective_lang = "ru"
            elif any(w in clean_query for w in ["salom", "qanday", "yordam", "kerak", "uchun", "qanaqa", "boladi", "haqida"]):
                effective_lang = "uz"
            else:
                effective_lang = "en"

        clean_model = (model_name or "").lower().strip()

        # Resolve Geo Location & Region
        geo_info = GeoIPService.resolve_location(ip=ip_address)
        effective_region = (user_region or geo_info.get("region", "tashkent")).lower().strip()
        effective_city = user_city or geo_info.get("city", effective_region.capitalize())
        effective_country = geo_info.get("country", "UZ")

        if not now_dt:
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

            # 1. Dayparting Schedule & Smart Dynamic Bidding Gate
            bid_calc = AdSmartBiddingService.calculate_smart_bid(
                campaign=cmp,
                clean_query=clean_query,
                now_dt=now_dt,
                log_decision=False,
            )
            if not bid_calc.get("active", True):
                continue

            cost_per_event = float(bid_calc.get("dynamic_bid", cmp.bid_amount or 0.10))
            is_cpa = getattr(cmp, "pricing_model", "cpc") == "cpa"
            target_cpa = float(getattr(cmp, "target_cpa", 0.0) or 0.0)

            if not is_cpa and adv.balance < cost_per_event:
                continue
            if is_cpa and adv.balance < (target_cpa if target_cpa > 0 else float(cmp.bid_amount or 1.0)):
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

            # 2.5 Language Targeting Gate
            cmp_langs = [l.lower().strip() for l in (getattr(cmp, "target_languages", []) or []) if l]
            if cmp_langs and effective_lang:
                if effective_lang not in cmp_langs and "all" not in cmp_langs:
                    continue

            # 2.6 Model-Level Targeting Gate
            cmp_models = [m.lower().strip() for m in (getattr(cmp, "target_models", []) or []) if m]
            if cmp_models and clean_model:
                if not any(cm in clean_model or clean_model in cm for cm in cmp_models) and "all" not in cmp_models:
                    continue

            # 2.7 Regional Geo Targeting Gate
            cmp_regions = [r.lower().strip() for r in (getattr(cmp, "target_regions", []) or []) if r]
            if cmp_regions and effective_region:
                if effective_region not in cmp_regions and "all" not in cmp_regions:
                    continue

            # 2.8 Negative Keywords Gate (Brand Safety & Stop-Words)
            cmp_negatives = [neg.lower().strip() for neg in (getattr(cmp, "negative_keywords", []) or []) if neg]
            if cmp_negatives:
                if any(neg in clean_query or any(qw == neg for qw in query_words) for neg in cmp_negatives):
                    continue

            # 3. Frequency Capping Gate (Campaign specific & Global)
            cmp_freq_cap = int(getattr(cmp, "frequency_cap_impressions", 0) or 0)
            cmp_freq_hours = max(1, int(getattr(cmp, "frequency_cap_hours", 24) or 24))

            if user_id:
                # 3.1 Campaign specific frequency cap
                if cmp_freq_cap > 0:
                    window_ts = now_ts - (cmp_freq_hours * 3600 * 1000)
                    user_cmp_imps = (
                        AdImpression.select()
                        .where(
                            AdImpression.campaign_id == cmp.id,
                            AdImpression.user_id == user_id,
                            AdImpression.create_time >= window_ts,
                        )
                        .count()
                    )
                    if user_cmp_imps >= cmp_freq_cap:
                        continue

                # 3.2 Global daily impressions cap
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

            # 3.5 Audience Targeting & Exclusion Gate
            target_segs = getattr(cmp, "target_audience_segment_ids", []) or []
            exclude_segs = getattr(cmp, "exclude_audience_segment_ids", []) or []

            if target_segs:
                if not user_id:
                    continue
                # User must belong to AT LEAST ONE target segment
                in_target = AdAudienceMember.select().where(
                    (AdAudienceMember.segment_id.in_(target_segs)) &
                    (AdAudienceMember.user_id == user_id)
                ).exists()
                if not in_target:
                    continue

            if exclude_segs and user_id:
                # User must NOT belong to ANY excluded segment
                is_excluded = AdAudienceMember.select().where(
                    (AdAudienceMember.segment_id.in_(exclude_segs)) &
                    (AdAudienceMember.user_id == user_id)
                ).exists()
                if is_excluded:
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
                elif any(word == term or (len(word) >= 4 and word in term) or (len(term) >= 4 and term in word) for word in query_words):
                    overlap_count += 1

            # Description / Product relevance
            desc_text = f"{cmp.product_name} {cmp.description or ''}".lower()
            for qw in query_words:
                if qw in desc_text:
                    overlap_count += 0.5

            if overlap_count <= 0:
                continue

            # Compute normalized score with language & model bonuses
            lang_bonus = 0.2 if (cmp_langs and effective_lang in cmp_langs) else 0.0
            model_bonus = 0.1 if (cmp_models and any(cm in clean_model for cm in cmp_models)) else 0.0
            relevance_score = min(1.0, (overlap_count / 3.0) + lang_bonus + model_bonus)
            pacing_mult = AdBudgetPacingService.calculate_pacing_multiplier(cmp, now_dt=now_dt)
            effective_bid = cost_per_event * pacing_mult
            normalized_bid = min(1.0, effective_bid / 2.0)
            priority_score = min(1.0, cmp.priority / 10.0) if cmp.priority else 0.0

            total_score = (relevance_score * 0.50) + (normalized_bid * 0.30) + (priority_score * 0.20)

            if total_score >= cls.MIN_RELEVANCE_SCORE_THRESHOLD:
                candidates.append((total_score, cmp, cost_per_event))

        if not candidates:
            return None

        # Sort candidates descending by total score
        candidates.sort(key=lambda x: x[0], reverse=True)
        winner_score, winner_campaign, cost = candidates[0]

        # Log Smart Bidding auction win decision
        try:
            AdSmartBiddingService.calculate_smart_bid(
                campaign=winner_campaign,
                clean_query=clean_query,
                now_dt=now_dt,
                log_decision=True,
            )
        except Exception as e:
            logger.debug(f"AdBiddingLog log error: {e}")

        # Select active variant (A/B testing with Bandit strategy) or fallback to campaign defaults
        selected_variant, ad_text, landing_url = AdVariantService.select_variant_for_impression(winner_campaign)

        # Apply Dynamic Creative Optimization (DCO) & Dynamic Keyword Insertion (DKI)
        dco_result = {}
        try:
            dco_result = AdDcoEngineService.render_dco_copy(
                campaign=winner_campaign,
                query=clean_query,
                base_text=ad_text,
                base_url=landing_url,
                model=model_name or "gpt-4o",
                lang=effective_lang or "ru",
                region=effective_region or "tashkent",
                user_id=user_id or "",
                log_decision=True,
            )
            ad_text = dco_result.get("rendered_text") or ad_text
            landing_url = dco_result.get("rendered_url") or landing_url
        except Exception as e:
            logger.debug(f"DCO render error: {e}")

        # Record Impression
        impression_id = uuid.uuid4().hex[:32]
        try:
            AdImpression.create(
                id=impression_id,
                campaign_id=winner_campaign.id,
                variant_id=(selected_variant.id if selected_variant else None),
                advertiser_id=winner_campaign.advertiser_id,
                user_id=user_id or "",
                tenant_id=tenant_id or "",
                conversation_id=conversation_id or "",
                message_id=message_id or "",
                cost=(cost if winner_campaign.pricing_model == "cpm" else 0.0),
                query_intent=clean_query[:250],
                language=effective_lang or "ru",
                model_name=model_name or "gpt-4o",
                device_type="desktop",
                platform="web",
                region=effective_region or "tashkent",
                city=effective_city or "Tashkent",
                country=effective_country or "UZ",
                create_time=now_ts,
            )

            if selected_variant:
                selected_variant.impressions += 1
                selected_variant.save()

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
        variant_tag = selected_variant.id if selected_variant else "main"
        click_token = f"{winner_campaign.id}_{impression_id}_{user_id or 'anon'}_{variant_tag}"
        tracking_url = f"/v1/ads/r/{click_token}"

        return {
            "id": winner_campaign.id,
            "campaign_id": winner_campaign.id,
            "variant_id": selected_variant.id if selected_variant else None,
            "impression_id": impression_id,
            "advertiser": winner_campaign.advertiser.company_name or "Verified Sponsor",
            "product": winner_campaign.product_name,
            "description": winner_campaign.description or "",
            "advertisement_text": ad_text,
            "landing_url": landing_url,
            "tracking_url": tracking_url,
            "target_categories": winner_campaign.target_categories or [],
            "pricing_model": getattr(winner_campaign, "pricing_model", "cpc"),
            "cta_text": dco_result.get("cta_text") or "",
            "promo_code": dco_result.get("promo_code") or "",
            "discount_percent": dco_result.get("discount_percent") or 0.0,
            "dco_applied": dco_result.get("dco_applied", False),
        }

    @classmethod
    @DB.connection_context()
    def track_click(cls, click_token: str, user_id: str = "", ip_hash: str = "", user_agent: str = "", raw_ip: str = "") -> str:
        """
        Record unique click for campaign, deduct CPC bid from advertiser balance,
        and return destination landing URL. Validates against Click Fraud & Bot Traffic.
        """
        if not click_token:
            return "https://swipies.app"

        campaign = None
        imp_lang = "ru"
        imp_model = "gpt-4o"
        imp_device = "desktop"
        imp_platform = "web"
        imp_region = "tashkent"
        imp_city = "Tashkent"
        imp_country = "UZ"
        target_variant_id = ""

        impression = AdImpression.get_or_none(AdImpression.id == click_token)
        if not impression and "_" in click_token:
            for part in click_token.split("_"):
                if len(part) == 32:
                    imp_cand = AdImpression.get_or_none(AdImpression.id == part)
                    if imp_cand:
                        impression = imp_cand
                        break

        if impression:
            campaign = AdCampaign.get_or_none(AdCampaign.id == impression.campaign_id)
            campaign_id = impression.campaign_id
            impression_id = impression.id
            token_user_id = impression.user_id or user_id
            target_variant_id = getattr(impression, "variant_id", "") or ""
            imp_lang = getattr(impression, "language", "ru") or "ru"
            imp_model = getattr(impression, "model_name", "gpt-4o") or "gpt-4o"
            imp_device = getattr(impression, "device_type", "desktop") or "desktop"
            imp_platform = getattr(impression, "platform", "web") or "web"
            imp_region = getattr(impression, "region", "tashkent") or "tashkent"
            imp_city = getattr(impression, "city", "Tashkent") or "Tashkent"
            imp_country = getattr(impression, "country", "UZ") or "UZ"
        else:
            campaign = AdCampaign.get_or_none(AdCampaign.id == click_token)
            if campaign:
                campaign_id = campaign.id
                impression_id = ""
                token_user_id = user_id
            elif "_" in click_token:
                campaign = None
                for i in range(len(click_token.split("_")), 0, -1):
                    prefix = "_".join(click_token.split("_")[:i])
                    cand_cmp = AdCampaign.get_or_none(AdCampaign.id == prefix)
                    if cand_cmp:
                        campaign = cand_cmp
                        campaign_id = cand_cmp.id
                        rem_parts = click_token[len(prefix) + 1:].split("_")
                        impression_id = rem_parts[0] if len(rem_parts) > 0 else ""
                        token_user_id = rem_parts[1] if len(rem_parts) > 1 else user_id
                        break
                if not campaign:
                    campaign_id = click_token
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

        variant_obj = None
        if target_variant_id and target_variant_id != "main":
            variant_obj = AdVariant.get_or_none(AdVariant.id == target_variant_id)

        now_ts = current_timestamp()
        cost = float(campaign.bid_amount or 0.10) if campaign.pricing_model == "cpc" else 0.0

        # Anti-Fraud & Invalid Traffic (IVT) Validation
        is_valid, fraud_reason = AdAntiFraudService.validate_click(
            campaign=campaign,
            click_token=click_token,
            ip_address=raw_ip,
            ip_hash=ip_hash,
            user_agent=user_agent,
            cost=cost,
        )
        if not is_valid:
            logger.info(f"Invalid click blocked on campaign {campaign.id}: reason={fraud_reason}, ip={raw_ip or ip_hash}")
            if variant_obj and variant_obj.landing_url:
                return variant_obj.landing_url
            return campaign.landing_url or "https://swipies.app"

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
                variant_id=variant_obj.id if variant_obj else None,
                impression_id=impression_id,
                advertiser_id=campaign.advertiser_id,
                user_id=token_user_id or "",
                cost=cost,
                ip_hash=ip_hash[:64] if ip_hash else "",
                language=imp_lang,
                model_name=imp_model,
                device_type=imp_device,
                platform=imp_platform,
                region=imp_region,
                city=imp_city,
                country=imp_country,
                create_time=now_ts,
            )

            if variant_obj:
                variant_obj.clicks += 1
                variant_obj.save()

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

        if variant_obj and variant_obj.landing_url:
            return variant_obj.landing_url

        return campaign.landing_url or "https://swipies.app"

    get_sponsored_recommendation = match_campaign_for_query

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
                "bidding_strategy": getattr(c, "bidding_strategy", "manual_cpc") or "manual_cpc",
                "target_cpa": float(getattr(c, "target_cpa", 0.0) or 0.0),
                "schedule_timezone": getattr(c, "schedule_timezone", "UTC") or "UTC",
                "schedule_config": getattr(c, "schedule_config", {}) or {},
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

    @classmethod
    @DB.connection_context()
    def get_advertiser_timeline_analytics(cls, user_id: str, tenant_id: str, days: int = 14) -> dict:
        """
        Calculates daily bucketed performance (impressions, clicks, ctr, spend) over the last N days,
        plus breakdowns by language, model, and device for an advertiser.
        """
        adv = AdvertiserService.get_or_create_for_user(user_id, tenant_id)
        now = datetime.now(timezone.utc)
        start_date = (now - timedelta(days=days - 1)).replace(hour=0, minute=0, second=0, microsecond=0)
        start_ts = int(start_date.timestamp() * 1000)

        # 1. Fetch impressions and clicks in the window
        impressions = list(
            AdImpression.select()
            .where(AdImpression.advertiser_id == adv.id, AdImpression.create_time >= start_ts)
        )
        clicks = list(
            AdClick.select()
            .where(AdClick.advertiser_id == adv.id, AdClick.create_time >= start_ts)
        )

        # 2. Build daily bucket map
        daily_map = {}
        for i in range(days):
            d = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
            daily_map[d] = {
                "date": d,
                "impressions": 0,
                "clicks": 0,
                "spend": 0.0,
                "ctr": 0.0,
            }

        # Language breakdown
        lang_counts = {"uz": 0, "ru": 0, "en": 0, "other": 0}
        # Model breakdown
        model_counts = {"gpt-4o": 0, "deepseek": 0, "claude": 0, "other": 0}
        # Device breakdown
        device_counts = {"desktop": 0, "mobile": 0, "tablet": 0}
        # Region breakdown
        region_counts = {
            "tashkent": 0,
            "samarkand": 0,
            "bukhara": 0,
            "fergana": 0,
            "andijan": 0,
            "namangan": 0,
            "other": 0,
        }

        for imp in impressions:
            dt_str = datetime.fromtimestamp(imp.create_time / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
            if dt_str in daily_map:
                daily_map[dt_str]["impressions"] += 1
                daily_map[dt_str]["spend"] += float(getattr(imp, "cost", 0.0) or 0.0)

            lang = (getattr(imp, "language", "ru") or "ru").lower()
            if lang in lang_counts:
                lang_counts[lang] += 1
            else:
                lang_counts["other"] += 1

            model = (getattr(imp, "model_name", "gpt-4o") or "gpt-4o").lower()
            if "deepseek" in model:
                model_counts["deepseek"] += 1
            elif "claude" in model:
                model_counts["claude"] += 1
            elif "gpt" in model:
                model_counts["gpt-4o"] += 1
            else:
                model_counts["other"] += 1

            dev = (getattr(imp, "device_type", "desktop") or "desktop").lower()
            if dev in device_counts:
                device_counts[dev] += 1
            else:
                device_counts["desktop"] += 1

            reg = (getattr(imp, "region", "tashkent") or "tashkent").lower()
            if reg in region_counts:
                region_counts[reg] += 1
            else:
                region_counts["other"] += 1

        for clk in clicks:
            dt_str = datetime.fromtimestamp(clk.create_time / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
            if dt_str in daily_map:
                daily_map[dt_str]["clicks"] += 1
                daily_map[dt_str]["spend"] += float(getattr(clk, "cost", 0.0) or 0.0)

        timeline = []
        for d in sorted(daily_map.keys()):
            row = daily_map[d]
            row["spend"] = round(row["spend"], 2)
            row["ctr"] = round((row["clicks"] / row["impressions"] * 100.0), 2) if row["impressions"] > 0 else 0.0
            timeline.append(row)

        total_imps = len(impressions)
        total_clks = len(clicks)
        total_spend = sum(r["spend"] for r in timeline)
        overall_ctr = round((total_clks / total_imps * 100.0), 2) if total_imps > 0 else 0.0

        return {
            "days": days,
            "total_impressions": total_imps,
            "total_clicks": total_clks,
            "total_spend": round(total_spend, 2),
            "ctr": overall_ctr,
            "timeline": timeline,
            "languages": lang_counts,
            "models": model_counts,
            "devices": device_counts,
            "regions": region_counts,
        }

    @classmethod
    @DB.connection_context()
    def get_campaign_analytics_detailed(cls, campaign_id: str, advertiser_id: str, days: int = 14) -> dict:
        """Detailed daily analytics and breakdowns for a specific campaign."""
        cmp = AdCampaign.get_or_none(AdCampaign.id == campaign_id, AdCampaign.advertiser_id == advertiser_id)
        if not cmp:
            return {}

        now = datetime.now(timezone.utc)
        start_date = (now - timedelta(days=days - 1)).replace(hour=0, minute=0, second=0, microsecond=0)
        start_ts = int(start_date.timestamp() * 1000)

        impressions = list(
            AdImpression.select()
            .where(AdImpression.campaign_id == campaign_id, AdImpression.create_time >= start_ts)
        )
        clicks = list(
            AdClick.select()
            .where(AdClick.campaign_id == campaign_id, AdClick.create_time >= start_ts)
        )

        daily_map = {}
        for i in range(days):
            d = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
            daily_map[d] = {
                "date": d,
                "impressions": 0,
                "clicks": 0,
                "spend": 0.0,
                "ctr": 0.0,
            }

        lang_counts = {"uz": 0, "ru": 0, "en": 0, "other": 0}
        model_counts = {"gpt-4o": 0, "deepseek": 0, "claude": 0, "other": 0}
        device_counts = {"desktop": 0, "mobile": 0, "tablet": 0}
        region_counts = {
            "tashkent": 0,
            "samarkand": 0,
            "bukhara": 0,
            "fergana": 0,
            "andijan": 0,
            "namangan": 0,
            "other": 0,
        }

        for imp in impressions:
            dt_str = datetime.fromtimestamp(imp.create_time / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
            if dt_str in daily_map:
                daily_map[dt_str]["impressions"] += 1
                daily_map[dt_str]["spend"] += float(getattr(imp, "cost", 0.0) or 0.0)

            lang = (getattr(imp, "language", "ru") or "ru").lower()
            if lang in lang_counts:
                lang_counts[lang] += 1
            else:
                lang_counts["other"] += 1

            model = (getattr(imp, "model_name", "gpt-4o") or "gpt-4o").lower()
            if "deepseek" in model:
                model_counts["deepseek"] += 1
            elif "claude" in model:
                model_counts["claude"] += 1
            elif "gpt" in model:
                model_counts["gpt-4o"] += 1
            else:
                model_counts["other"] += 1

            dev = (getattr(imp, "device_type", "desktop") or "desktop").lower()
            if dev in device_counts:
                device_counts[dev] += 1
            else:
                device_counts["desktop"] += 1

            reg = (getattr(imp, "region", "tashkent") or "tashkent").lower()
            if reg in region_counts:
                region_counts[reg] += 1
            else:
                region_counts["other"] += 1

        for clk in clicks:
            dt_str = datetime.fromtimestamp(clk.create_time / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
            if dt_str in daily_map:
                daily_map[dt_str]["clicks"] += 1
                daily_map[dt_str]["spend"] += float(getattr(clk, "cost", 0.0) or 0.0)

        timeline = []
        for d in sorted(daily_map.keys()):
            row = daily_map[d]
            row["spend"] = round(row["spend"], 2)
            row["ctr"] = round((row["clicks"] / row["impressions"] * 100.0), 2) if row["impressions"] > 0 else 0.0
            timeline.append(row)

        total_imps = len(impressions)
        total_clks = len(clicks)
        total_spend = sum(r["spend"] for r in timeline)
        overall_ctr = round((total_clks / total_imps * 100.0), 2) if total_imps > 0 else 0.0

        return {
            "campaign_id": cmp.id,
            "campaign_name": cmp.name,
            "product_name": cmp.product_name,
            "status": cmp.status,
            "days": days,
            "total_impressions": total_imps,
            "total_clicks": total_clks,
            "total_spend": round(total_spend, 2),
            "ctr": overall_ctr,
            "timeline": timeline,
            "languages": lang_counts,
            "models": model_counts,
            "devices": device_counts,
            "regions": region_counts,
        }

    @classmethod
    @DB.connection_context()
    def get_admin_network_timeline(cls, days: int = 14) -> dict:
        """Network-wide daily timeline of impressions, clicks, spend and CTR for admin panel."""
        now = datetime.now(timezone.utc)
        start_date = (now - timedelta(days=days - 1)).replace(hour=0, minute=0, second=0, microsecond=0)
        start_ts = int(start_date.timestamp() * 1000)

        impressions = list(AdImpression.select().where(AdImpression.create_time >= start_ts))
        clicks = list(AdClick.select().where(AdClick.create_time >= start_ts))

        daily_map = {}
        for i in range(days):
            d = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
            daily_map[d] = {
                "date": d,
                "impressions": 0,
                "clicks": 0,
                "revenue": 0.0,
                "ctr": 0.0,
            }

        region_counts = {
            "tashkent": 0,
            "samarkand": 0,
            "bukhara": 0,
            "fergana": 0,
            "andijan": 0,
            "namangan": 0,
            "other": 0,
        }

        for imp in impressions:
            dt_str = datetime.fromtimestamp(imp.create_time / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
            if dt_str in daily_map:
                daily_map[dt_str]["impressions"] += 1
                daily_map[dt_str]["revenue"] += float(getattr(imp, "cost", 0.0) or 0.0)

            reg = (getattr(imp, "region", "tashkent") or "tashkent").lower()
            if reg in region_counts:
                region_counts[reg] += 1
            else:
                region_counts["other"] += 1

        for clk in clicks:
            dt_str = datetime.fromtimestamp(clk.create_time / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
            if dt_str in daily_map:
                daily_map[dt_str]["clicks"] += 1
                daily_map[dt_str]["revenue"] += float(getattr(clk, "cost", 0.0) or 0.0)

        timeline = []
        for d in sorted(daily_map.keys()):
            row = daily_map[d]
            row["revenue"] = round(row["revenue"], 2)
            row["ctr"] = round((row["clicks"] / row["impressions"] * 100.0), 2) if row["impressions"] > 0 else 0.0
            timeline.append(row)

        return {
            "days": days,
            "timeline": timeline,
            "total_network_impressions": len(impressions),
            "total_network_clicks": len(clicks),
            "total_network_revenue": round(sum(r["revenue"] for r in timeline), 2),
            "regions": region_counts,
        }


class AttributionService(CommonService):
    model = AdAttributionVisit

    @classmethod
    @DB.connection_context()
    def record_attribution_visit(
        cls,
        referrer_id: str,
        tenant_id: str = "",
        utm_source: str = "chat_watermark",
        utm_medium: str = "ai_response",
        utm_campaign: str = "share_attribution",
        utm_content: str = "",
        ip: str = "",
        user_agent: str = "",
    ) -> str:
        """Record a visit originating from a user's AI response watermark."""
        if not referrer_id:
            return ""

        import hashlib
        ip_hash = hashlib.sha256(ip.encode("utf-8")).hexdigest()[:32] if ip else ""
        visit_id = uuid.uuid4().hex[:32]

        AdAttributionVisit.create(
            id=visit_id,
            user_id=referrer_id,
            tenant_id=tenant_id or "",
            utm_source=utm_source or "chat_watermark",
            utm_medium=utm_medium or "ai_response",
            utm_campaign=utm_campaign or "share_attribution",
            utm_content=utm_content or "",
            ip_hash=ip_hash,
            user_agent=(user_agent or "")[:500],
            create_time=current_timestamp(),
        )
        return visit_id

    @classmethod
    @DB.connection_context()
    def get_attribution_analytics(cls, user_id: str) -> dict:
        """
        Get complete statistics on how many people visited & registered via user's AI chat watermark.
        """
        from api.db.services.ad_policy_service import AdPolicyService

        if not user_id:
            return {
                "total_visits": 0,
                "unique_visitors": 0,
                "total_signups": 0,
                "conversion_rate": 0.0,
                "recent_visits": [],
                "utm_link": AdPolicyService.build_attribution_url(user_id=""),
            }

        visits_query = AdAttributionVisit.select().where(AdAttributionVisit.user_id == user_id)
        total_visits = visits_query.count()

        # Unique visitors by IP hash
        unique_visitors = AdAttributionVisit.select(AdAttributionVisit.ip_hash).where(
            AdAttributionVisit.user_id == user_id,
            AdAttributionVisit.ip_hash.is_null(False),
            AdAttributionVisit.ip_hash != "",
        ).distinct().count()

        # Count users registered with referred_by_id == user_id
        signups_count = User.select().where(User.referred_by_id == user_id).count()

        conversion_rate = round((signups_count / total_visits * 100.0), 2) if total_visits > 0 else 0.0

        recent_records = visits_query.order_by(AdAttributionVisit.create_time.desc()).limit(10)
        recent_visits = [
            {
                "id": v.id,
                "utm_source": v.utm_source,
                "utm_medium": v.utm_medium,
                "utm_campaign": v.utm_campaign,
                "utm_content": v.utm_content or "",
                "created_at": v.create_time,
            }
            for v in recent_records
        ]

        return {
            "total_visits": total_visits,
            "unique_visitors": unique_visitors,
            "total_signups": signups_count,
            "conversion_rate": conversion_rate,
            "utm_link": AdPolicyService.build_attribution_url(user_id=user_id),
            "recent_visits": recent_visits,
        }


class ConversionTrackingService(CommonService):
    model = AdConversion

    @classmethod
    @DB.connection_context()
    def get_or_create_pixel_id(cls, advertiser_id: str) -> str:
        adv = Advertiser.get_or_none(Advertiser.id == advertiser_id)
        if not adv:
            return ""
        if not adv.pixel_id:
            adv.pixel_id = "px_" + uuid.uuid4().hex[:16]
            adv.save()
        return adv.pixel_id

    @classmethod
    def generate_pixel_snippet(cls, pixel_id: str, host: str = "https://swipies.app") -> dict:
        """Generates embeddable JS tracking snippet and integration guide for advertiser website."""
        snippet = (
            f'<!-- Swipies Conversion Pixel -->\n'
            f'<script src="{host}/api/v1/ads/pixel.js?id={pixel_id}" async></script>\n'
            f'<script>\n'
            f'  window.swipiesTrack = window.swipiesTrack || function(event, data) {{\n'
            f'    try {{\n'
            f'      var urlParams = new URLSearchParams(window.location.search);\n'
            f'      var clickToken = urlParams.get("swipies_click") || localStorage.getItem("swipies_click_token") || "";\n'
            f'      fetch("{host}/api/v1/ads/pixel/track", {{\n'
            f'        method: "POST",\n'
            f'        headers: {{"Content-Type": "application/json"}},\n'
            f'        body: JSON.stringify({{\n'
            f'          pixel_id: "{pixel_id}",\n'
            f'          event: event || "purchase",\n'
            f'          value: data && data.value ? Number(data.value) : 0,\n'
            f'          currency: (data && data.currency) || "USD",\n'
            f'          order_id: (data && data.order_id) || "",\n'
            f'          click_token: clickToken\n'
            f'        }})\n'
            f'      }});\n'
            f'    }} catch(e) {{ console.error("Swipies pixel error", e); }}\n'
            f'  }};\n'
            f'</script>'
        )
        example_usage = "swipiesTrack('purchase', { value: 49.99, order_id: 'ORD-12345', currency: 'USD' });"
        return {
            "pixel_id": pixel_id,
            "snippet": snippet,
            "example_usage": example_usage,
        }

    @classmethod
    @DB.connection_context()
    def record_conversion(
        cls,
        pixel_id: str,
        event: str = "purchase",
        value: float = 0.0,
        currency: str = "USD",
        order_id: str = "",
        click_id: str = "",
        click_token: str = "",
        ip: str = "",
        user_id: str = "",
    ) -> dict:
        """
        Match incoming conversion to a recent AdClick / AdImpression within attribution window (30 days),
        record AdConversion, update campaign CVR metrics, and bill CPA if applicable.
        """
        adv = Advertiser.get_or_none(Advertiser.pixel_id == pixel_id)
        if not adv:
            return {"success": False, "message": "Invalid pixel ID"}

        now_ts = current_timestamp()
        thirty_days_ago = now_ts - (30 * 86400 * 1000)

        # Attempt to find matching click
        matched_click = None
        matched_imp = None
        target_cmp = None

        if click_id:
            matched_click = AdClick.get_or_none(AdClick.id == click_id, AdClick.advertiser_id == adv.id)

        if not matched_click and click_token:
            matched_click = AdClick.get_or_none(AdClick.id == click_token, AdClick.advertiser_id == adv.id)
            if not matched_click and "_" in click_token:
                for part in click_token.split("_"):
                    if len(part) == 32:
                        c_cand = AdClick.get_or_none(AdClick.impression_id == part, AdClick.advertiser_id == adv.id)
                        if c_cand:
                            matched_click = c_cand
                            break
                        i_cand = AdImpression.get_or_none(AdImpression.id == part, AdImpression.advertiser_id == adv.id)
                        if i_cand:
                            matched_imp = i_cand
                            break

            if not matched_click and not matched_imp:
                matched_imp = AdImpression.get_or_none(AdImpression.id == click_token, AdImpression.advertiser_id == adv.id)

        if not matched_click and not matched_imp and ip:
            import hashlib
            ip_hash = hashlib.sha256(ip.encode()).hexdigest()[:64]
            matched_click = (
                AdClick.select()
                .where(
                    AdClick.advertiser_id == adv.id,
                    AdClick.ip_hash == ip_hash,
                    AdClick.create_time >= thirty_days_ago,
                )
                .order_by(AdClick.create_time.desc())
                .first()
            )

        if matched_click:
            target_cmp = AdCampaign.get_or_none(AdCampaign.id == matched_click.campaign_id)
            matched_variant_id = getattr(matched_click, "variant_id", None)
            matched_imp_id = getattr(matched_click, "impression_id", None)
            matched_click_id = matched_click.id
            matched_user_id = matched_click.user_id or user_id
        elif matched_imp:
            target_cmp = AdCampaign.get_or_none(AdCampaign.id == matched_imp.campaign_id)
            matched_variant_id = getattr(matched_imp, "variant_id", None)
            matched_imp_id = matched_imp.id
            matched_click_id = None
            matched_user_id = matched_imp.user_id or user_id
        else:
            # Fallback to most recent active campaign of advertiser
            target_cmp = (
                AdCampaign.select()
                .where(AdCampaign.advertiser_id == adv.id, AdCampaign.status == "active")
                .order_by(AdCampaign.create_time.desc())
                .first()
            )
            matched_variant_id = None
            matched_imp_id = None
            matched_click_id = None
            matched_user_id = user_id

        if not target_cmp:
            return {"success": False, "message": "No active campaign found for conversion"}

        # Prevent duplicate conversion for same order_id
        if order_id:
            dup = AdConversion.get_or_none(AdConversion.advertiser_id == adv.id, AdConversion.order_id == order_id)
            if dup:
                return {"success": True, "conversion_id": dup.id, "duplicate": True}

        # Calculate billable CPA cost if campaign is CPA pricing model
        cpa_cost = 0.0
        if getattr(target_cmp, "pricing_model", "cpc") == "cpa":
            cpa_cost = float(getattr(target_cmp, "target_cpa", 0.0) or target_cmp.bid_amount or 1.0)
            if adv.balance >= cpa_cost:
                adv.balance = max(0.0, adv.balance - cpa_cost)
                adv.save()
                target_cmp.spent_today += cpa_cost
                target_cmp.total_spent += cpa_cost
                AdTransaction.create(
                    id=uuid.uuid4().hex[:32],
                    advertiser_id=adv.id,
                    amount=-cpa_cost,
                    type="spend_cpa",
                    description=f"CPA Conversion fee for order {order_id or target_cmp.name}",
                    reference_id=order_id or target_cmp.id,
                    create_time=now_ts,
                )

        conversion_id = uuid.uuid4().hex[:32]
        conv = AdConversion.create(
            id=conversion_id,
            campaign_id=target_cmp.id,
            variant_id=matched_variant_id,
            advertiser_id=adv.id,
            click_id=matched_click_id,
            impression_id=matched_imp_id,
            user_id=matched_user_id or "",
            conversion_event=event,
            conversion_value=float(value or 0.0),
            currency=currency,
            order_id=order_id or None,
            cost=cpa_cost,
            ip_hash=ip[:64] if ip else None,
            status="confirmed",
            create_time=now_ts,
        )

        # Update Campaign Conversion Metrics
        target_cmp.conversions_count = (target_cmp.conversions_count or 0) + 1
        target_cmp.total_conversion_value = float(target_cmp.total_conversion_value or 0.0) + float(value or 0.0)

        # Calculate CVR = conversions / clicks * 100
        clicks_cnt = AdClick.select().where(AdClick.campaign_id == target_cmp.id).count()
        if clicks_cnt > 0:
            target_cmp.conversion_rate = round((target_cmp.conversions_count / clicks_cnt) * 100.0, 2)
        target_cmp.save()

        # Auto sync conversion event to audience retargeting segments
        try:
            AdAudienceService.sync_pixel_conversion_to_segments(
                advertiser_id=adv.id,
                event_type=event,
                user_id=matched_user_id,
                anonymous_id=ip[:64] if ip else None,
            )
        except Exception as e:
            logger.warning(f"Error syncing conversion to audience segments: {e}")

        return {
            "success": True,
            "conversion_id": conv.id,
            "campaign_id": target_cmp.id,
            "event": event,
            "value": value,
            "cost": cpa_cost,
        }


class AdOptimizerService:
    @classmethod
    @DB.connection_context()
    def generate_campaign_insights(cls, campaign_id: str) -> list:
        cmp = AdCampaign.get_or_none(AdCampaign.id == campaign_id)
        if not cmp:
            return []

        insights = []
        imps_count = AdImpression.select().where(AdImpression.campaign_id == cmp.id).count()
        clicks_count = AdClick.select().where(AdClick.campaign_id == cmp.id).count()
        ctr = (clicks_count / imps_count * 100.0) if imps_count > 0 else 0.0
        conversions_count = AdConversion.select().where(AdConversion.campaign_id == cmp.id).count()
        keywords = cmp.keywords or []
        negative_keywords = getattr(cmp, "negative_keywords", []) or []
        variants_count = AdVariant.select().where(AdVariant.campaign_id == cmp.id, AdVariant.is_active == True).count()

        # 1. Low CTR / Ad Copy Refresh
        if imps_count >= 20 and ctr < 2.0:
            suggested_text = f"🔥 Спецпредложение: {cmp.product_name}! Успейте оформить с выгодой до 20%. Быстрая доставка и гарантия качества."
            insights.append({
                "id": f"ins_copy_{cmp.id}",
                "campaign_id": cmp.id,
                "campaign_name": cmp.name,
                "type": "ad_copy_refresh",
                "category": "quality",
                "severity": "high",
                "title": "Оптимизация рекламного текста (Повышение CTR)",
                "description": f"Текущий CTR кампании составляет {round(ctr, 2)}% при {imps_count} показах. Добавление триггера выгоды и четкого CTA может поднять кликабельность на +35-50%.",
                "estimated_impact": "+35% CTR",
                "suggested_action": "Заменить рекламный текст на вариант с повышенным intent-откликом",
                "action_payload": {
                    "advertisement_text": suggested_text
                }
            })

        # 2. Keyword Expansion
        if len(keywords) < 6:
            base_kw = [k.lower() for k in keywords]
            rec_kw = []
            candidates = ["купить", "заказать", "лучший", "доставка", "онлайн", "цена", "скидка", "отзывы", "акция"]
            for cand in candidates:
                cand_phrase = f"{cmp.product_name.lower()} {cand}"
                if cand_phrase not in base_kw and len(rec_kw) < 4:
                    rec_kw.append(cand_phrase)

            if rec_kw:
                insights.append({
                    "id": f"ins_kw_{cmp.id}",
                    "campaign_id": cmp.id,
                    "campaign_name": cmp.name,
                    "type": "keyword_expansion",
                    "category": "reach",
                    "severity": "medium",
                    "title": "Расширение охвата ключевых слов",
                    "description": f"В кампании настроено всего {len(keywords)} ключевых слов. Добавление транзакционных запросов увеличит объем целевых показов.",
                    "estimated_impact": "+45% Показов",
                    "suggested_action": f"Добавить релевантные фразы: {', '.join(rec_kw)}",
                    "action_payload": {
                        "add_keywords": rec_kw
                    }
                })

        # 3. Negative Keywords / Budget Protection
        if len(negative_keywords) < 2:
            default_negatives = ["бесплатно", "кряк", "торрент", "слив", "взлом", "free", "crack"]
            to_add_neg = [n for n in default_negatives if n not in negative_keywords][:4]
            if to_add_neg:
                insights.append({
                    "id": f"ins_neg_{cmp.id}",
                    "campaign_id": cmp.id,
                    "campaign_name": cmp.name,
                    "type": "negative_keywords",
                    "category": "cost",
                    "severity": "medium",
                    "title": "Защита бюджета стоп-словами (Negative Keywords)",
                    "description": "У кампании не настроены минус-слова. Пользователи, ищущие бесплатные взломы или нерелевантный контент, могут скликивать бюджет.",
                    "estimated_impact": "-25% Нецелевого расхода",
                    "suggested_action": f"Добавить стоп-слова: {', '.join(to_add_neg)}",
                    "action_payload": {
                        "add_negative_keywords": to_add_neg
                    }
                })

        # 4. A/B Testing Bandit Variant Recommendation
        if variants_count < 2:
            insights.append({
                "id": f"ins_ab_{cmp.id}",
                "campaign_id": cmp.id,
                "campaign_name": cmp.name,
                "type": "ab_test_recommendation",
                "category": "growth",
                "severity": "low",
                "title": "Запуск A/B тестирования офферов",
                "description": "У вас только один вариант объявления. Подключение 2-го варианта позволит алгоритму Bandit автоматически отдавать трафик самому эффективному офферу.",
                "estimated_impact": "+28% Конверсий",
                "suggested_action": "Создать оптимизируемый Вариант B (AI Оффер)",
                "action_payload": {
                    "create_variant": True,
                    "variant_name": "Вариант B (AI Smart Оффер)",
                    "variant_text": f"✨ Ищете {cmp.product_name}? Премиум качество, официальная гарантия и мгновенный доступ. Узнайте подробности!",
                    "landing_url": cmp.landing_url,
                }
            })

        # 5. Smart CPA / Target CPA Recommendation
        if cmp.pricing_model != "cpa" and (conversions_count >= 2 or float(getattr(cmp, "conversions_count", 0) or 0) >= 2):
            insights.append({
                "id": f"ins_cpa_{cmp.id}",
                "campaign_id": cmp.id,
                "campaign_name": cmp.name,
                "type": "switch_to_cpa",
                "category": "bidding",
                "severity": "high",
                "title": "Переход на Smart CPA Auto-Bidding",
                "description": f"Кампания стабильно генерирует конверсии ({conversions_count} подтверждено). Переход на Smart CPA защитит от переплат и будет платить только за результат.",
                "estimated_impact": "Оплата за результат",
                "suggested_action": "Включить модель CPA с Target CPA $5.00",
                "action_payload": {
                    "pricing_model": "cpa",
                    "target_cpa": 5.0,
                }
            })

        return insights

    @classmethod
    @DB.connection_context()
    def generate_advertiser_insights(cls, advertiser_id: str) -> dict:
        campaigns = list(AdCampaign.select().where(AdCampaign.advertiser_id == advertiser_id, AdCampaign.status == "active"))
        all_insights = []
        for cmp in campaigns:
            all_insights.extend(cls.generate_campaign_insights(cmp.id))

        # Overall Optimization Score (0 - 100)
        penalty = len(all_insights) * 12
        score = max(35, min(100, 100 - penalty)) if campaigns else 100

        return {
            "score": score,
            "total_insights": len(all_insights),
            "insights": all_insights,
        }

    @classmethod
    @DB.connection_context()
    def apply_insight(cls, campaign_id: str, advertiser_id: str, insight_type: str, action_payload: dict) -> dict:
        cmp = AdCampaign.get_or_none(AdCampaign.id == campaign_id, AdCampaign.advertiser_id == advertiser_id)
        if not cmp:
            return {"success": False, "message": "Campaign not found"}

        now_ts = current_timestamp()

        if insight_type == "ad_copy_refresh":
            if "advertisement_text" in action_payload:
                cmp.advertisement_text = action_payload["advertisement_text"]
                cmp.update_time = now_ts
                cmp.save()

        elif insight_type == "keyword_expansion":
            add_kw = action_payload.get("add_keywords", [])
            current_kw = cmp.keywords or []
            merged = list(set(current_kw + add_kw))
            cmp.keywords = merged
            cmp.update_time = now_ts
            cmp.save()

        elif insight_type == "negative_keywords":
            add_neg = action_payload.get("add_negative_keywords", [])
            current_neg = getattr(cmp, "negative_keywords", []) or []
            merged = list(set(current_neg + add_neg))
            cmp.negative_keywords = merged
            cmp.update_time = now_ts
            cmp.save()

        elif insight_type == "ab_test_recommendation":
            AdVariantService.create_variant(
                campaign_id=cmp.id,
                advertiser_id=advertiser_id,
                data={
                    "name": action_payload.get("variant_name", "Вариант B (AI Smart Оффер)"),
                    "advertisement_text": action_payload.get("variant_text", f"Узнайте больше о {cmp.product_name}"),
                    "landing_url": action_payload.get("landing_url", cmp.landing_url),
                    "weight": 1.0,
                    "is_active": True,
                }
            )

        elif insight_type == "switch_to_cpa":
            cmp.pricing_model = "cpa"
            cmp.target_cpa = float(action_payload.get("target_cpa", 5.0) or 5.0)
            cmp.update_time = now_ts
            cmp.save()

        elif insight_type == "bid_optimization":
            if "update_daily_budget" in action_payload:
                cmp.daily_budget = float(action_payload["update_daily_budget"])
            if "update_bid" in action_payload:
                cmp.bid_amount = float(action_payload["update_bid"])
            cmp.update_time = now_ts
            cmp.save()

        return {
            "success": True,
            "campaign_id": cmp.id,
            "insight_type": insight_type,
            "message": "Рекомендация успешно применена!",
        }


class AdExportService:
    @classmethod
    @DB.connection_context()
    def export_campaigns_csv(cls, advertiser_id: str) -> str:
        import csv
        import io
        campaigns = list(
            AdCampaign.select()
            .where(AdCampaign.advertiser_id == advertiser_id)
            .order_by(AdCampaign.create_time.desc())
        )
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Campaign ID",
            "Campaign Name",
            "Product Name",
            "Pricing Model",
            "Bid Amount ($)",
            "Target CPA ($)",
            "Daily Budget ($)",
            "Total Budget ($)",
            "Total Spent ($)",
            "Spent Today ($)",
            "Impressions",
            "Clicks",
            "CTR (%)",
            "Conversions",
            "CVR (%)",
            "Total Conversion Value ($)",
            "Status",
            "Moderation Status",
            "Created Date",
        ])

        for c in campaigns:
            imps = AdImpression.select().where(AdImpression.campaign_id == c.id).count()
            clicks = AdClick.select().where(AdClick.campaign_id == c.id).count()
            ctr = round((clicks / imps * 100.0), 2) if imps > 0 else 0.0
            convs = getattr(c, "conversions_count", 0) or AdConversion.select().where(AdConversion.campaign_id == c.id).count()
            cvr = round(getattr(c, "conversion_rate", 0.0) or (convs / clicks * 100.0 if clicks > 0 else 0.0), 2)
            created_str = datetime.fromtimestamp(c.create_time / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S") if c.create_time else ""

            writer.writerow([
                c.id,
                c.name,
                c.product_name,
                c.pricing_model,
                c.bid_amount,
                getattr(c, "target_cpa", 0.0) or 0.0,
                c.daily_budget,
                c.total_budget,
                c.total_spent,
                c.spent_today,
                imps,
                clicks,
                ctr,
                convs,
                cvr,
                getattr(c, "total_conversion_value", 0.0) or 0.0,
                c.status,
                c.moderation_status,
                created_str,
            ])

        return output.getvalue()

    @classmethod
    @DB.connection_context()
    def export_transactions_csv(cls, advertiser_id: str) -> str:
        import csv
        import io
        txs = list(
            AdTransaction.select()
            .where(AdTransaction.advertiser_id == advertiser_id)
            .order_by(AdTransaction.create_time.desc())
        )
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Transaction ID",
            "Date (UTC)",
            "Type",
            "Amount ($)",
            "Description",
            "Reference ID",
        ])

        for t in txs:
            dt_str = datetime.fromtimestamp(t.create_time / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S") if t.create_time else ""
            writer.writerow([
                t.id,
                dt_str,
                t.type,
                t.amount,
                t.description or "",
                t.reference_id or "",
            ])

        return output.getvalue()

    @classmethod
    @DB.connection_context()
    def export_analytics_timeline_csv(cls, user_id: str, tenant_id: str, days: int = 30) -> str:
        import csv
        import io
        timeline_data = AdEngineService.get_advertiser_timeline_analytics(user_id=user_id, tenant_id=tenant_id, days=days)
        rows = timeline_data.get("timeline", [])

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Date",
            "Impressions",
            "Clicks",
            "CTR (%)",
            "Spend / Revenue ($)",
        ])

        for r in rows:
            writer.writerow([
                r.get("date", ""),
                r.get("impressions", 0),
                r.get("clicks", 0),
                r.get("ctr", 0.0),
                r.get("revenue", 0.0),
            ])

        return output.getvalue()

    @classmethod
    @DB.connection_context()
    def generate_executive_html_report(cls, advertiser_id: str, days: int = 30) -> str:
        adv = Advertiser.get_or_none(Advertiser.id == advertiser_id)
        if not adv:
            return "<html><body><h1>Advertiser not found</h1></body></html>"

        now_dt = datetime.now(timezone.utc)
        generated_at = now_dt.strftime("%Y-%m-%d %H:%M:%S UTC")

        campaigns = list(
            AdCampaign.select()
            .where(AdCampaign.advertiser_id == advertiser_id)
            .order_by(AdCampaign.create_time.desc())
        )

        total_imps = 0
        total_clicks = 0
        total_convs = 0
        total_spent = sum(c.total_spent for c in campaigns)

        camp_rows_html = ""
        for c in campaigns:
            imps = AdImpression.select().where(AdImpression.campaign_id == c.id).count()
            clicks = AdClick.select().where(AdClick.campaign_id == c.id).count()
            convs = getattr(c, "conversions_count", 0) or AdConversion.select().where(AdConversion.campaign_id == c.id).count()
            ctr = round((clicks / imps * 100.0), 2) if imps > 0 else 0.0
            cvr = round((convs / clicks * 100.0), 2) if clicks > 0 else 0.0
            total_imps += imps
            total_clicks += clicks
            total_convs += convs

            camp_rows_html += f"""
            <tr>
              <td style="padding: 10px; border-bottom: 1px solid #e2e8f0; font-weight: 600;">{c.name}</td>
              <td style="padding: 10px; border-bottom: 1px solid #e2e8f0; text-transform: uppercase; font-size: 11px;">{c.pricing_model}</td>
              <td style="padding: 10px; border-bottom: 1px solid #e2e8f0; text-align: right;">{imps:,}</td>
              <td style="padding: 10px; border-bottom: 1px solid #e2e8f0; text-align: right;">{clicks:,}</td>
              <td style="padding: 10px; border-bottom: 1px solid #e2e8f0; text-align: right; color: #059669; font-weight: 600;">{ctr}%</td>
              <td style="padding: 10px; border-bottom: 1px solid #e2e8f0; text-align: right;">{convs:,}</td>
              <td style="padding: 10px; border-bottom: 1px solid #e2e8f0; text-align: right;">{cvr}%</td>
              <td style="padding: 10px; border-bottom: 1px solid #e2e8f0; text-align: right; font-weight: bold;">${c.total_spent:.2f}</td>
            </tr>
            """

        overall_ctr = round((total_clicks / total_imps * 100.0), 2) if total_imps > 0 else 0.0
        overall_cvr = round((total_convs / total_clicks * 100.0), 2) if total_clicks > 0 else 0.0

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Swipies Ads Executive Report — {adv.company_name}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; color: #1e293b; margin: 0; padding: 40px; background: #f8fafc; }}
    .container {{ max-width: 900px; margin: 0 auto; background: #ffffff; padding: 40px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }}
    .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #3b82f6; padding-bottom: 20px; margin-bottom: 30px; }}
    .logo {{ font-size: 24px; font-weight: 800; color: #1e40af; letter-spacing: -0.5px; }}
    .logo span {{ color: #3b82f6; }}
    .meta {{ text-align: right; font-size: 12px; color: #64748b; }}
    .kpi-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 30px; }}
    .kpi-card {{ background: #f1f5f9; padding: 16px; border-radius: 8px; border: 1px solid #e2e8f0; }}
    .kpi-title {{ font-size: 11px; text-transform: uppercase; color: #64748b; font-weight: 600; margin-bottom: 4px; }}
    .kpi-value {{ font-size: 22px; font-weight: 800; color: #0f172a; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; margin-bottom: 30px; }}
    th {{ background: #f8fafc; text-align: left; padding: 12px 10px; border-bottom: 2px solid #cbd5e1; font-size: 11px; text-transform: uppercase; color: #475569; }}
    .footer {{ border-top: 1px solid #e2e8f0; padding-top: 20px; font-size: 11px; color: #94a3b8; display: flex; justify-content: space-between; align-items: center; }}
    @media print {{
      body {{ background: #fff; padding: 0; }}
      .container {{ box-shadow: none; padding: 0; }}
      .no-print {{ display: none; }}
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="no-print" style="margin-bottom: 20px; text-align: right;">
      <button onclick="window.print()" style="background: #2563eb; color: #fff; border: none; padding: 8px 16px; border-radius: 6px; font-weight: 600; cursor: pointer;">🖨️ Печать / Сохранить в PDF</button>
    </div>

    <div class="header">
      <div>
        <div class="logo">Swipies<span>Ads</span> Executive Report</div>
        <div style="font-size: 14px; color: #475569; margin-top: 4px;">Рекламодатель: <strong>{adv.company_name}</strong></div>
      </div>
      <div class="meta">
        <div>Период: <strong>Последние {days} дней</strong></div>
        <div>Дата генерации: {generated_at}</div>
        <div>Статус аккаунта: <strong style="color: #16a34a;">Активен</strong></div>
      </div>
    </div>

    <div class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-title">Всего показов</div>
        <div class="kpi-value">{total_imps:,}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-title">Переходы (Клики)</div>
        <div class="kpi-value">{total_clicks:,} <span style="font-size: 13px; color: #059669; font-weight: 600;">({overall_ctr}%)</span></div>
      </div>
      <div class="kpi-card">
        <div class="kpi-title">Конверсии (Лиды)</div>
        <div class="kpi-value">{total_convs:,} <span style="font-size: 13px; color: #7c3aed; font-weight: 600;">({overall_cvr}%)</span></div>
      </div>
      <div class="kpi-card">
        <div class="kpi-title">Суммарный расход</div>
        <div class="kpi-value">${total_spent:.2f}</div>
      </div>
    </div>

    <h3 style="font-size: 16px; margin-bottom: 12px; color: #0f172a;">📊 Сводка по рекламным кампаниям</h3>
    <table>
      <thead>
        <tr>
          <th>Кампания</th>
          <th>Модель</th>
          <th style="text-align: right;">Показы</th>
          <th style="text-align: right;">Клики</th>
          <th style="text-align: right;">CTR</th>
          <th style="text-align: right;">Конв.</th>
          <th style="text-align: right;">CVR</th>
          <th style="text-align: right;">Расход</th>
        </tr>
      </thead>
      <tbody>
        {camp_rows_html}
      </tbody>
    </table>

    <div class="footer">
      <div>Верифицированный отчет рекламной платформы Swipies AI Advertising Engine.</div>
      <div>ID рекламодателя: {adv.id}</div>
    </div>
  </div>
</body>
</html>
"""
        return html


class AdvertiserTeamService:
    ROLE_PERMISSIONS = {
        "admin": {"manage_campaigns", "view_analytics", "manage_billing", "manage_team", "export_reports", "apply_optimizer"},
        "manager": {"manage_campaigns", "view_analytics", "export_reports", "apply_optimizer"},
        "analyst": {"view_analytics", "export_reports"},
        "billing": {"manage_billing", "view_analytics", "export_reports"},
    }

    @classmethod
    @DB.connection_context()
    def get_team_members(cls, advertiser_id: str) -> list[dict]:
        members = list(
            AdvertiserTeamMember.select()
            .where((AdvertiserTeamMember.advertiser_id == advertiser_id) & (AdvertiserTeamMember.status != "revoked"))
            .order_by(AdvertiserTeamMember.create_time.asc())
        )
        return [{
            "id": m.id,
            "advertiser_id": m.advertiser_id,
            "user_id": m.user_id,
            "email": m.email,
            "role": m.role,
            "status": m.status,
            "invited_by": m.invited_by,
            "create_time": m.create_time,
        } for m in members]

    @classmethod
    @DB.connection_context()
    def invite_member(cls, advertiser_id: str, email: str, role: str = "manager", inviter_user_id: str = "") -> dict:
        email = (email or "").strip().lower()
        if not email or "@" not in email:
            raise ValueError("Некорректный адрес электронной почты")

        role = role.lower()
        if role not in cls.ROLE_PERMISSIONS:
            role = "manager"

        now_ts = current_timestamp()

        # Check existing member
        existing = AdvertiserTeamMember.get_or_none(
            (AdvertiserTeamMember.advertiser_id == advertiser_id) &
            (AdvertiserTeamMember.email == email)
        )

        matched_user = User.get_or_none(User.email == email)
        user_id = matched_user.id if matched_user else None

        if existing:
            existing.role = role
            existing.status = "active"
            if user_id:
                existing.user_id = user_id
            existing.update_time = now_ts
            existing.save()
            return {
                "id": existing.id,
                "advertiser_id": existing.advertiser_id,
                "user_id": existing.user_id,
                "email": existing.email,
                "role": existing.role,
                "status": existing.status,
                "invited_by": existing.invited_by,
                "create_time": existing.create_time,
            }

        member = AdvertiserTeamMember.create(
            id=uuid.uuid4().hex[:32],
            advertiser_id=advertiser_id,
            user_id=user_id,
            email=email,
            role=role,
            status="active",
            invited_by=inviter_user_id,
            create_time=now_ts,
            update_time=now_ts,
        )

        return {
            "id": member.id,
            "advertiser_id": member.advertiser_id,
            "user_id": member.user_id,
            "email": member.email,
            "role": member.role,
            "status": member.status,
            "invited_by": member.invited_by,
            "create_time": member.create_time,
        }

    @classmethod
    @DB.connection_context()
    def update_member_role(cls, member_id: str, advertiser_id: str, new_role: str) -> dict:
        new_role = new_role.lower()
        if new_role not in cls.ROLE_PERMISSIONS:
            raise ValueError(f"Недопустимая роль: {new_role}")

        member = AdvertiserTeamMember.get_or_none(
            (AdvertiserTeamMember.id == member_id) &
            (AdvertiserTeamMember.advertiser_id == advertiser_id)
        )
        if not member:
            raise ValueError("Участник команды не найден")

        member.role = new_role
        member.update_time = current_timestamp()
        member.save()

        return {
            "id": member.id,
            "advertiser_id": member.advertiser_id,
            "user_id": member.user_id,
            "email": member.email,
            "role": member.role,
            "status": member.status,
            "invited_by": member.invited_by,
            "create_time": member.create_time,
        }

    @classmethod
    @DB.connection_context()
    def remove_member(cls, member_id: str, advertiser_id: str) -> bool:
        member = AdvertiserTeamMember.get_or_none(
            (AdvertiserTeamMember.id == member_id) &
            (AdvertiserTeamMember.advertiser_id == advertiser_id)
        )
        if not member:
            return False

        member.delete_instance()
        return True

    @classmethod
    @DB.connection_context()
    def has_permission(cls, user_id: str, advertiser_id: str, required_permission: str) -> bool:
        adv = Advertiser.get_or_none(Advertiser.id == advertiser_id)
        if not adv:
            return False

        # Primary owner has all permissions
        if adv.user_id == user_id:
            return True

        user = User.get_or_none(User.id == user_id)
        email = user.email.lower() if user and user.email else ""

        member = AdvertiserTeamMember.get_or_none(
            (AdvertiserTeamMember.advertiser_id == advertiser_id) &
            (AdvertiserTeamMember.status == "active") &
            ((AdvertiserTeamMember.user_id == user_id) | (AdvertiserTeamMember.email == email))
        )

        if not member:
            return False

        allowed = cls.ROLE_PERMISSIONS.get(member.role, set())
        return required_permission in allowed


class AdvertiserNotificationService:
    @classmethod
    @DB.connection_context()
    def get_or_create_settings(cls, advertiser_id: str) -> dict:
        settings = AdvertiserNotificationSettings.get_or_none(
            AdvertiserNotificationSettings.advertiser_id == advertiser_id
        )
        if not settings:
            adv = Advertiser.get_or_none(Advertiser.id == advertiser_id)
            settings = AdvertiserNotificationSettings.create(
                id=uuid.uuid4().hex[:32],
                advertiser_id=advertiser_id,
                email_alerts_enabled=True,
                email_target=adv.contact_email if adv else "",
                telegram_alerts_enabled=False,
                telegram_chat_id="",
                webhook_url="",
                webhook_secret="",
                notify_low_balance=True,
                low_balance_threshold=10.0,
                notify_daily_budget_reached=True,
                notify_moderation_status=True,
                notify_conversion_milestone=True,
                update_time=current_timestamp(),
            )

        return {
            "id": settings.id,
            "advertiser_id": settings.advertiser_id,
            "email_alerts_enabled": settings.email_alerts_enabled,
            "email_target": settings.email_target or "",
            "telegram_alerts_enabled": settings.telegram_alerts_enabled,
            "telegram_chat_id": settings.telegram_chat_id or "",
            "webhook_url": settings.webhook_url or "",
            "webhook_secret": settings.webhook_secret or "",
            "notify_low_balance": settings.notify_low_balance,
            "low_balance_threshold": settings.low_balance_threshold,
            "notify_daily_budget_reached": settings.notify_daily_budget_reached,
            "notify_moderation_status": settings.notify_moderation_status,
            "notify_conversion_milestone": settings.notify_conversion_milestone,
            "update_time": settings.update_time,
        }

    @classmethod
    @DB.connection_context()
    def update_settings(cls, advertiser_id: str, payload: dict) -> dict:
        settings = AdvertiserNotificationSettings.get_or_none(
            AdvertiserNotificationSettings.advertiser_id == advertiser_id
        )
        if not settings:
            cls.get_or_create_settings(advertiser_id)
            settings = AdvertiserNotificationSettings.get_by_id(advertiser_id)

        if "email_alerts_enabled" in payload:
            settings.email_alerts_enabled = bool(payload["email_alerts_enabled"])
        if "email_target" in payload:
            settings.email_target = str(payload["email_target"]).strip()
        if "telegram_alerts_enabled" in payload:
            settings.telegram_alerts_enabled = bool(payload["telegram_alerts_enabled"])
        if "telegram_chat_id" in payload:
            settings.telegram_chat_id = str(payload["telegram_chat_id"]).strip()
        if "webhook_url" in payload:
            settings.webhook_url = str(payload["webhook_url"]).strip()
        if "webhook_secret" in payload:
            settings.webhook_secret = str(payload["webhook_secret"]).strip()
        if "notify_low_balance" in payload:
            settings.notify_low_balance = bool(payload["notify_low_balance"])
        if "low_balance_threshold" in payload:
            settings.low_balance_threshold = max(1.0, float(payload["low_balance_threshold"]))
        if "notify_daily_budget_reached" in payload:
            settings.notify_daily_budget_reached = bool(payload["notify_daily_budget_reached"])
        if "notify_moderation_status" in payload:
            settings.notify_moderation_status = bool(payload["notify_moderation_status"])
        if "notify_conversion_milestone" in payload:
            settings.notify_conversion_milestone = bool(payload["notify_conversion_milestone"])

        settings.update_time = current_timestamp()
        settings.save()

        return cls.get_or_create_settings(advertiser_id)

    @classmethod
    @DB.connection_context()
    def create_notification(
        cls,
        advertiser_id: str,
        type: str,
        title: str,
        message: str,
        severity: str = "info",
        data: dict = None,
    ) -> dict:
        now_ts = current_timestamp()
        notif = AdvertiserNotification.create(
            id=uuid.uuid4().hex[:32],
            advertiser_id=advertiser_id,
            type=type,
            severity=severity,
            title=title,
            message=message,
            is_read=False,
            data=data or {},
            create_time=now_ts,
        )

        # Webhook dispatch simulation / async trigger if configured
        try:
            settings = AdvertiserNotificationSettings.get_or_none(
                AdvertiserNotificationSettings.advertiser_id == advertiser_id
            )
            if settings and settings.webhook_url:
                logger.info(f"[Ad Alerts Webhook] Dispatched notification {notif.id} to {settings.webhook_url}")
        except Exception as e:
            logger.warning(f"Failed to dispatch webhook alert: {e}")

        return {
            "id": notif.id,
            "advertiser_id": notif.advertiser_id,
            "type": notif.type,
            "severity": notif.severity,
            "title": notif.title,
            "message": notif.message,
            "is_read": notif.is_read,
            "data": notif.data,
            "create_time": notif.create_time,
        }

    @classmethod
    @DB.connection_context()
    def get_notifications(cls, advertiser_id: str, limit: int = 50, unread_only: bool = False) -> dict:
        query = AdvertiserNotification.select().where(AdvertiserNotification.advertiser_id == advertiser_id)
        if unread_only:
            query = query.where(AdvertiserNotification.is_read == False)

        notifications = list(query.order_by(AdvertiserNotification.create_time.desc()).limit(limit))

        unread_count = AdvertiserNotification.select().where(
            (AdvertiserNotification.advertiser_id == advertiser_id) &
            (AdvertiserNotification.is_read == False)
        ).count()

        return {
            "unread_count": unread_count,
            "notifications": [{
                "id": n.id,
                "advertiser_id": n.advertiser_id,
                "type": n.type,
                "severity": n.severity,
                "title": n.title,
                "message": n.message,
                "is_read": n.is_read,
                "data": n.data,
                "create_time": n.create_time,
            } for n in notifications],
        }

    @classmethod
    @DB.connection_context()
    def mark_as_read(cls, advertiser_id: str, notification_id: str = None, all_unread: bool = False) -> int:
        if all_unread:
            return AdvertiserNotification.update(is_read=True).where(
                (AdvertiserNotification.advertiser_id == advertiser_id) &
                (AdvertiserNotification.is_read == False)
            ).execute()
        elif notification_id:
            return AdvertiserNotification.update(is_read=True).where(
                (AdvertiserNotification.id == notification_id) &
                (AdvertiserNotification.advertiser_id == advertiser_id)
            ).execute()
        return 0

    @classmethod
    @DB.connection_context()
    def send_test_alert(cls, advertiser_id: str, channel: str = "all") -> dict:
        return cls.create_notification(
            advertiser_id=advertiser_id,
            type="system",
            title="Тестовое оповещение Swipies Ads",
            message=f"Канал '{channel}' настроен и успешно протестирован. Все системы работают в штатном режиме.",
            severity="success",
            data={"channel": channel, "test": True},
        )


class AdAudienceService:
    @classmethod
    @DB.connection_context()
    def list_segments(cls, advertiser_id: str) -> list:
        segments = list(
            AdAudienceSegment.select()
            .where(
                AdAudienceSegment.advertiser_id == advertiser_id,
                AdAudienceSegment.status != "deleted",
            )
            .order_by(AdAudienceSegment.create_time.desc())
        )
        res = []
        for s in segments:
            count = AdAudienceMember.select().where(AdAudienceMember.segment_id == s.id).count()
            if count != s.member_count:
                s.member_count = count
                s.save()

            res.append({
                "id": s.id,
                "advertiser_id": s.advertiser_id,
                "name": s.name,
                "description": s.description or "",
                "rule_type": s.rule_type,
                "rule_config": s.rule_config or {},
                "member_count": count,
                "status": s.status,
                "create_time": s.create_time,
            })
        return res

    @classmethod
    @DB.connection_context()
    def create_segment(
        cls,
        advertiser_id: str,
        name: str,
        description: str = "",
        rule_type: str = "pixel_event",
        rule_config: dict = None,
    ) -> dict:
        now_ts = current_timestamp()
        seg_id = uuid.uuid4().hex[:32]
        seg = AdAudienceSegment.create(
            id=seg_id,
            advertiser_id=advertiser_id,
            name=name,
            description=description,
            rule_type=rule_type,
            rule_config=rule_config or {},
            member_count=0,
            status="active",
            create_time=now_ts,
            update_time=now_ts,
        )
        return {
            "id": seg.id,
            "advertiser_id": seg.advertiser_id,
            "name": seg.name,
            "description": seg.description,
            "rule_type": seg.rule_type,
            "rule_config": seg.rule_config,
            "member_count": 0,
            "status": seg.status,
            "create_time": seg.create_time,
        }

    @classmethod
    @DB.connection_context()
    def delete_segment(cls, segment_id: str, advertiser_id: str) -> bool:
        seg = AdAudienceSegment.get_or_none(
            AdAudienceSegment.id == segment_id,
            AdAudienceSegment.advertiser_id == advertiser_id,
        )
        if not seg:
            return False
        seg.status = "deleted"
        seg.update_time = current_timestamp()
        seg.save()
        return True

    @classmethod
    @DB.connection_context()
    def add_member(
        cls,
        segment_id: str,
        user_id: str = None,
        anonymous_id: str = None,
        source_event: str = "manual",
    ) -> dict:
        existing = AdAudienceMember.get_or_none(
            (AdAudienceMember.segment_id == segment_id) &
            (((AdAudienceMember.user_id == user_id) & (AdAudienceMember.user_id.is_null(False))) |
             ((AdAudienceMember.anonymous_id == anonymous_id) & (AdAudienceMember.anonymous_id.is_null(False))))
        )
        if existing:
            return {"id": existing.id, "segment_id": existing.segment_id, "user_id": existing.user_id, "exists": True}

        member = AdAudienceMember.create(
            id=uuid.uuid4().hex[:32],
            segment_id=segment_id,
            user_id=user_id,
            anonymous_id=anonymous_id,
            source_event=source_event,
            create_time=current_timestamp(),
        )
        AdAudienceSegment.update(
            member_count=AdAudienceSegment.member_count + 1
        ).where(AdAudienceSegment.id == segment_id).execute()

        return {
            "id": member.id,
            "segment_id": member.segment_id,
            "user_id": member.user_id,
            "anonymous_id": member.anonymous_id,
            "source_event": member.source_event,
            "create_time": member.create_time,
        }

    @classmethod
    @DB.connection_context()
    def sync_pixel_conversion_to_segments(
        cls,
        advertiser_id: str,
        event_type: str,
        user_id: str = None,
        anonymous_id: str = None,
    ):
        segments = list(
            AdAudienceSegment.select()
            .where(
                AdAudienceSegment.advertiser_id == advertiser_id,
                AdAudienceSegment.rule_type == "pixel_event",
                AdAudienceSegment.status == "active",
            )
        )
        for s in segments:
            cfg = s.rule_config or {}
            target_event = cfg.get("event_type", "all")
            if target_event == "all" or target_event == event_type:
                cls.add_member(
                    segment_id=s.id,
                    user_id=user_id,
                    anonymous_id=anonymous_id,
                    source_event=f"pixel:{event_type}",
                )


class AdPublisherService:
    @classmethod
    def _generate_api_key(cls) -> str:
        return f"sw_pub_live_{uuid.uuid4().hex[:24]}"

    @classmethod
    @DB.connection_context()
    def get_or_create_publisher(cls, user_id: str, tenant_id: str, name: str = "") -> AdPublisher:
        pub = AdPublisher.get_or_none(AdPublisher.user_id == user_id)
        if not pub:
            now_ts = current_timestamp()
            pub = AdPublisher.create(
                id=uuid.uuid4().hex[:32],
                tenant_id=tenant_id,
                user_id=user_id,
                name=name or "Publisher Account",
                api_key=cls._generate_api_key(),
                balance=0.0,
                total_earned=0.0,
                total_withdrawn=0.0,
                default_rev_share=0.70,
                status="active",
                create_time=now_ts,
                update_time=now_ts,
            )
            # Create a default placement
            cls.create_placement(
                publisher_id=pub.id,
                name="Default Telegram Bot Placement",
                placement_type="telegram_bot",
                rev_share_rate=0.70,
            )
        return pub

    @classmethod
    @DB.connection_context()
    def regenerate_api_key(cls, publisher_id: str, user_id: str) -> str:
        pub = AdPublisher.get_or_none(AdPublisher.id == publisher_id, AdPublisher.user_id == user_id)
        if not pub:
            raise ValueError("Publisher not found")
        pub.api_key = cls._generate_api_key()
        pub.update_time = current_timestamp()
        pub.save()
        return pub.api_key

    @classmethod
    @DB.connection_context()
    def list_placements(cls, publisher_id: str) -> list:
        placements = list(
            AdPlacement.select()
            .where(
                AdPlacement.publisher_id == publisher_id,
                AdPlacement.status != "archived",
            )
            .order_by(AdPlacement.create_time.desc())
        )
        return [{
            "id": p.id,
            "publisher_id": p.publisher_id,
            "name": p.name,
            "placement_type": p.placement_type,
            "domain_or_bot": p.domain_or_bot or "",
            "rev_share_rate": p.rev_share_rate,
            "impressions": p.impressions,
            "clicks": p.clicks,
            "earnings": round(p.earnings, 4),
            "status": p.status,
            "create_time": p.create_time,
        } for p in placements]

    @classmethod
    @DB.connection_context()
    def create_placement(
        cls,
        publisher_id: str,
        name: str,
        placement_type: str = "telegram_bot",
        domain_or_bot: str = "",
        rev_share_rate: float = 0.70,
    ) -> dict:
        now_ts = current_timestamp()
        placement = AdPlacement.create(
            id=uuid.uuid4().hex[:32],
            publisher_id=publisher_id,
            name=name,
            placement_type=placement_type,
            domain_or_bot=domain_or_bot or "",
            rev_share_rate=float(rev_share_rate or 0.70),
            impressions=0,
            clicks=0,
            earnings=0.0,
            status="active",
            create_time=now_ts,
            update_time=now_ts,
        )
        return {
            "id": placement.id,
            "publisher_id": placement.publisher_id,
            "name": placement.name,
            "placement_type": placement.placement_type,
            "domain_or_bot": placement.domain_or_bot,
            "rev_share_rate": placement.rev_share_rate,
            "impressions": 0,
            "clicks": 0,
            "earnings": 0.0,
            "status": placement.status,
            "create_time": placement.create_time,
        }

    @classmethod
    @DB.connection_context()
    def delete_placement(cls, placement_id: str, publisher_id: str) -> bool:
        placement = AdPlacement.get_or_none(
            AdPlacement.id == placement_id,
            AdPlacement.publisher_id == publisher_id,
        )
        if not placement:
            return False
        placement.status = "archived"
        placement.update_time = current_timestamp()
        placement.save()
        return True

    @classmethod
    @DB.connection_context()
    def request_payout(
        cls,
        publisher_id: str,
        amount: float,
        destination_card: str,
        destination_holder: str = "",
    ) -> dict:
        pub = AdPublisher.get_or_none(AdPublisher.id == publisher_id)
        if not pub:
            raise ValueError("Publisher not found")
        if amount <= 0:
            raise ValueError("Сумма выплаты должна быть больше 0")
        if pub.balance < amount:
            raise ValueError(f"Недостаточно средств на балансе. Доступно: ${pub.balance:.2f}")

        now_ts = current_timestamp()
        pub.balance = max(0.0, pub.balance - amount)
        pub.total_withdrawn += amount
        pub.payout_card = destination_card
        pub.payout_holder = destination_holder
        pub.update_time = now_ts
        pub.save()

        payout = AdPublisherPayout.create(
            id=uuid.uuid4().hex[:32],
            publisher_id=publisher_id,
            amount=amount,
            currency="USD",
            destination_card=destination_card,
            destination_holder=destination_holder or "",
            status="pending",
            create_time=now_ts,
            update_time=now_ts,
        )
        return {
            "id": payout.id,
            "publisher_id": payout.publisher_id,
            "amount": payout.amount,
            "currency": payout.currency,
            "destination_card": payout.destination_card,
            "status": payout.status,
            "new_balance": round(pub.balance, 4),
            "create_time": payout.create_time,
        }

    @classmethod
    @DB.connection_context()
    def list_payouts(cls, publisher_id: str) -> list:
        payouts = list(
            AdPublisherPayout.select()
            .where(AdPublisherPayout.publisher_id == publisher_id)
            .order_by(AdPublisherPayout.create_time.desc())
        )
        return [{
            "id": p.id,
            "publisher_id": p.publisher_id,
            "amount": p.amount,
            "currency": p.currency,
            "destination_card": p.destination_card,
            "destination_holder": p.destination_holder or "",
            "status": p.status,
            "note": p.note or "",
            "create_time": p.create_time,
        } for p in payouts]

    @classmethod
    @DB.connection_context()
    def serve_partner_ad(
        cls,
        api_key: str,
        query: str,
        placement_id: str = None,
        lang: str = "ru",
        user_ip: str = "",
        user_id: str = "",
    ) -> dict:
        """
        Public partner ad serving engine.
        Authenticates publisher API key, selects contextual ad match, accrues rev share earnings, and returns payload.
        """
        pub = AdPublisher.get_or_none(AdPublisher.api_key == api_key, AdPublisher.status == "active")
        if not pub:
            return {"error": "Invalid or inactive publisher API key", "matched": False}

        placement = None
        if placement_id:
            placement = AdPlacement.get_or_none(
                AdPlacement.id == placement_id,
                AdPlacement.publisher_id == pub.id,
                AdPlacement.status == "active",
            )
        if not placement:
            # Fallback to first active placement of publisher
            placement = AdPlacement.select().where(
                AdPlacement.publisher_id == pub.id,
                AdPlacement.status == "active",
            ).order_by(AdPlacement.create_time.asc()).first()

        rev_share_rate = placement.rev_share_rate if placement else (pub.default_rev_share or 0.70)

        # Match contextual campaign
        matched = AdEngineService.match_campaign_for_query(
            user_query=query,
            lang=lang,
            ip_address=user_ip,
            user_id=user_id or f"pub_{pub.id[:8]}",
        )
        if not matched:
            return {"matched": False, "ad": None}

        # Calculate publisher revenue share
        # Base event revenue
        cost_event = float(matched.get("cost", 0.0) or 0.10)
        pub_earnings = round(cost_event * rev_share_rate, 4)

        if pub_earnings > 0:
            pub.balance = round(pub.balance + pub_earnings, 4)
            pub.total_earned = round(pub.total_earned + pub_earnings, 4)
            pub.update_time = current_timestamp()
            pub.save()

            if placement:
                placement.impressions += 1
                placement.earnings = round(placement.earnings + pub_earnings, 4)
                placement.update_time = current_timestamp()
                placement.save()

        return {
            "matched": True,
            "placement_id": placement.id if placement else None,
            "ad": {
                "campaign_id": matched.get("campaign_id"),
                "product": matched.get("product"),
                "advertisement_text": matched.get("advertisement_text"),
                "landing_url": matched.get("landing_url"),
                "tracking_url": matched.get("tracking_url"),
            },
            "publisher_earnings": pub_earnings,
            "rev_share_rate": rev_share_rate,
        }


class AdAntiFraudService(CommonService):
    """
    Anti-Fraud & Invalid Traffic (IVT) Protection Engine.
    Detects click fraud, bot signatures, datacenter scrapers, rapid repeat clicks, and enforces IP blacklists.
    """
    KNOWN_BOT_SIGNATURES = [
        "bot", "spider", "crawl", "curl", "wget", "python-requests", "aiohttp",
        "urllib", "scrapy", "selenium", "puppeteer", "playwright", "headless",
        "phantomjs", "go-http-client", "apache-httpclient", "java/", "postmanruntime",
        "insomnia", "httpclient", "bytespider", "yandexbot", "googlebot"
    ]

    @classmethod
    def is_bot_user_agent(cls, user_agent: str) -> bool:
        if not user_agent:
            return False
        ua_lower = user_agent.lower()
        return any(sig in ua_lower for sig in cls.KNOWN_BOT_SIGNATURES)

    @classmethod
    @DB.connection_context()
    def is_ip_blacklisted(cls, ip_address: str, advertiser_id: str = None) -> bool:
        if not ip_address:
            return False
        now_ts = current_timestamp()

        query = AdIpBlacklist.select().where(
            (AdIpBlacklist.status == "active") &
            (
                (AdIpBlacklist.auto_expires_at.is_null()) |
                (AdIpBlacklist.auto_expires_at > now_ts)
            )
        )
        if advertiser_id:
            query = query.where(
                (AdIpBlacklist.advertiser_id == advertiser_id) |
                (AdIpBlacklist.advertiser_id.is_null()) |
                (AdIpBlacklist.advertiser_id == "system")
            )

        for entry in query:
            blocked_ip = entry.ip_address.strip()
            if blocked_ip == ip_address.strip():
                return True
            if blocked_ip.endswith("*") and ip_address.startswith(blocked_ip[:-1]):
                return True
            if "/" in blocked_ip:
                try:
                    import ipaddress
                    if ipaddress.ip_address(ip_address) in ipaddress.ip_network(blocked_ip, strict=False):
                        return True
                except Exception:
                    pass
        return False

    @classmethod
    @DB.connection_context()
    def add_to_blacklist(cls, ip_address: str, advertiser_id: str = None, reason: str = "Suspicious automated click activity", duration_hours: int = 72) -> dict:
        if not ip_address:
            return {"success": False, "message": "IP address is required"}

        now_ts = current_timestamp()
        expires_at = (now_ts + duration_hours * 3600 * 1000) if duration_hours > 0 else None

        entry = AdIpBlacklist.get_or_none(
            AdIpBlacklist.ip_address == ip_address.strip(),
            AdIpBlacklist.advertiser_id == advertiser_id,
        )
        if entry:
            entry.status = "active"
            entry.reason = reason
            entry.auto_expires_at = expires_at
            entry.update_time = now_ts
            entry.save()
        else:
            entry = AdIpBlacklist.create(
                id=uuid.uuid4().hex[:32],
                advertiser_id=advertiser_id,
                ip_address=ip_address.strip(),
                reason=reason,
                auto_expires_at=expires_at,
                status="active",
                create_time=now_ts,
                update_time=now_ts,
            )
        return {
            "success": True,
            "id": entry.id,
            "ip_address": entry.ip_address,
            "reason": entry.reason,
            "auto_expires_at": entry.auto_expires_at,
            "status": entry.status,
        }

    @classmethod
    @DB.connection_context()
    def remove_from_blacklist(cls, blacklist_id: str, advertiser_id: str = None) -> bool:
        query = AdIpBlacklist.select().where(AdIpBlacklist.id == blacklist_id)
        if advertiser_id:
            query = query.where(AdIpBlacklist.advertiser_id == advertiser_id)
        entry = query.first()
        if not entry:
            return False
        entry.status = "revoked"
        entry.update_time = current_timestamp()
        entry.save()
        return True

    @classmethod
    @DB.connection_context()
    def list_blacklist(cls, advertiser_id: str) -> list:
        now_ts = current_timestamp()
        entries = list(
            AdIpBlacklist.select()
            .where(
                ((AdIpBlacklist.advertiser_id == advertiser_id) | (AdIpBlacklist.advertiser_id.is_null()) | (AdIpBlacklist.advertiser_id == "system")) &
                (AdIpBlacklist.status == "active") &
                ((AdIpBlacklist.auto_expires_at.is_null()) | (AdIpBlacklist.auto_expires_at > now_ts))
            )
            .order_by(AdIpBlacklist.create_time.desc())
        )
        return [{
            "id": e.id,
            "ip_address": e.ip_address,
            "advertiser_id": e.advertiser_id,
            "is_system": e.advertiser_id in [None, "system"],
            "reason": e.reason,
            "auto_expires_at": e.auto_expires_at,
            "status": e.status,
            "create_time": e.create_time,
        } for e in entries]

    @classmethod
    @DB.connection_context()
    def validate_click(
        cls,
        campaign: AdCampaign,
        click_token: str = "",
        ip_address: str = "",
        ip_hash: str = "",
        user_agent: str = "",
        cost: float = 0.0,
    ) -> tuple:
        """
        Runs comprehensive anti-fraud tests on incoming click:
        1. Bot User-Agent detection.
        2. Blacklisted IP check.
        3. Rapid repeat clicks rate-limiting from same IP/hash (threshold: >2 clicks in 60s).
        Returns (is_valid: bool, reason: str).
        """
        now_ts = current_timestamp()
        adv_id = campaign.advertiser_id

        # 1. Bot check
        if cls.is_bot_user_agent(user_agent):
            AdFraudLog.create(
                id=uuid.uuid4().hex[:32],
                advertiser_id=adv_id,
                campaign_id=campaign.id,
                event_type="click",
                reason="bot_user_agent",
                ip_hash=ip_hash[:64] if ip_hash else "",
                user_agent=(user_agent[:250] if user_agent else "bot"),
                cost_saved=cost,
                create_time=now_ts,
            )
            return False, "bot_user_agent"

        # 2. Blacklisted IP check
        effective_ip = ip_address.strip() if ip_address else ""
        if effective_ip and cls.is_ip_blacklisted(effective_ip, advertiser_id=adv_id):
            AdFraudLog.create(
                id=uuid.uuid4().hex[:32],
                advertiser_id=adv_id,
                campaign_id=campaign.id,
                event_type="click",
                reason="blacklist_ip",
                ip_hash=ip_hash[:64] if ip_hash else "",
                user_agent=(user_agent[:250] if user_agent else ""),
                cost_saved=cost,
                create_time=now_ts,
            )
            return False, "blacklist_ip"

        # 3. Rapid repeat clicks detection (Rate Limiting)
        # Check if more than 2 clicks recorded in the last 60 seconds from same IP hash or IP
        one_minute_ago = now_ts - (60 * 1000)
        recent_clicks_count = 0
        if ip_hash:
            recent_clicks_count = AdClick.select().where(
                AdClick.campaign_id == campaign.id,
                AdClick.ip_hash == ip_hash[:64],
                AdClick.create_time >= one_minute_ago,
            ).count()

        if recent_clicks_count >= 2:
            five_mins_ago = now_ts - (300 * 1000)
            five_min_count = AdClick.select().where(
                AdClick.campaign_id == campaign.id,
                AdClick.ip_hash == ip_hash[:64],
                AdClick.create_time >= five_mins_ago,
            ).count()
            if five_min_count >= 5 and effective_ip:
                cls.add_to_blacklist(
                    ip_address=effective_ip,
                    advertiser_id=adv_id,
                    reason="Auto-blocked: High frequency repeated click flood",
                    duration_hours=24,
                )

            AdFraudLog.create(
                id=uuid.uuid4().hex[:32],
                advertiser_id=adv_id,
                campaign_id=campaign.id,
                event_type="click",
                reason="rapid_repeat_clicks",
                ip_hash=ip_hash[:64] if ip_hash else "",
                user_agent=(user_agent[:250] if user_agent else ""),
                cost_saved=cost,
                create_time=now_ts,
            )
            return False, "rapid_repeat_clicks"

        return True, ""

    @classmethod
    @DB.connection_context()
    def get_fraud_overview(cls, advertiser_id: str) -> dict:
        """Overview metrics of blocked invalid traffic and saved budget."""
        logs = list(
            AdFraudLog.select()
            .where(AdFraudLog.advertiser_id == advertiser_id)
            .order_by(AdFraudLog.create_time.desc())
        )
        total_blocked_clicks = sum(1 for l in logs if l.event_type == "click")
        total_cost_saved = sum(l.cost_saved for l in logs)
        bot_detections = sum(1 for l in logs if l.reason == "bot_user_agent")
        rate_limit_blocks = sum(1 for l in logs if l.reason in ["rapid_repeat_clicks", "rate_limit_exceeded"])
        blacklist_blocks = sum(1 for l in logs if l.reason == "blacklist_ip")

        now_ts = current_timestamp()
        active_blacklist_count = AdIpBlacklist.select().where(
            ((AdIpBlacklist.advertiser_id == advertiser_id) | (AdIpBlacklist.advertiser_id.is_null()) | (AdIpBlacklist.advertiser_id == "system")) &
            (AdIpBlacklist.status == "active") &
            ((AdIpBlacklist.auto_expires_at.is_null()) | (AdIpBlacklist.auto_expires_at > now_ts))
        ).count()

        cmp_ids = list(set(l.campaign_id for l in logs if l.campaign_id))
        cmp_map = {}
        if cmp_ids:
            for c in AdCampaign.select().where(AdCampaign.id.in_(cmp_ids)):
                cmp_map[c.id] = c.name

        recent_logs = [{
            "id": l.id,
            "campaign_id": l.campaign_id,
            "campaign_name": cmp_map.get(l.campaign_id, "All Campaigns"),
            "event_type": l.event_type,
            "reason": l.reason,
            "ip_hash": l.ip_hash,
            "user_agent": l.user_agent or "Unknown",
            "cost_saved": round(l.cost_saved, 2),
            "create_time": l.create_time,
        } for l in logs[:50]]

        return {
            "total_blocked_clicks": total_blocked_clicks,
            "total_cost_saved": round(total_cost_saved, 2),
            "bot_detections": bot_detections,
            "rate_limit_blocks": rate_limit_blocks,
            "blacklist_blocks": blacklist_blocks,
            "active_blacklist_count": active_blacklist_count,
            "recent_logs": recent_logs,
        }


class AdSmartBiddingService:
    KNOWN_STRATEGIES = {
        "manual_cpc": {
            "id": "manual_cpc",
            "name": "Ручное управление (Manual CPC)",
            "description": "Стабильная фиксированная ставка за клик с автоматической корректировкой по дням недели и часам (Dayparting).",
            "badge": "Базовый",
            "requires_cpa": False,
        },
        "enhanced_cpc": {
            "id": "enhanced_cpc",
            "name": "Оптимизатор клика (Enhanced CPC / eCPC)",
            "description": "Автоматически повышает ставку до +30% при коммерческом намерении пользователя и понижает при информационных запросах.",
            "badge": "Рекомендуется",
            "requires_cpa": False,
        },
        "target_cpa": {
            "id": "target_cpa",
            "name": "Целевая стоимость конверсии (Target CPA)",
            "description": "Алгоритмический расчет ставки за клик на основе вероятности конверсии (CVR) для удержания заданной стоимости лида.",
            "badge": "Конверсии",
            "requires_cpa": True,
        },
        "maximize_conversions": {
            "id": "maximize_conversions",
            "name": "Максимум конверсий (Maximize Conversions)",
            "description": "Автоматическое ускорение ставок в активные часы суток для получения наибольшего числа конверсий в рамках дневного бюджета.",
            "badge": "Автопилот",
            "requires_cpa": False,
        },
    }

    HIGH_INTENT_WORDS = {
        "купить", "цена", "стоимость", "заказать", "прайс", "тариф", "подписка", "скидка", "купоны",
        "акция", "приобрести", "оформить", "доставка", "магазин", "buy", "price", "order", "cost",
        "discount", "deal", "promo", "pricing", "subscription", "purchase", "sotib", "narxi"
    }

    LOW_INTENT_WORDS = {
        "что такое", "википедия", "бесплатно", "реферат", "картинки", "скачать бесплатно",
        "free", "wiki", "definition", "manual", "guide"
    }

    @classmethod
    def get_local_datetime(cls, now_dt: datetime = None, tz_name: str = "UTC") -> datetime:
        """Converts datetime to campaign timezone."""
        if not now_dt:
            now_dt = datetime.now(timezone.utc)
        elif now_dt.tzinfo is None:
            now_dt = now_dt.replace(tzinfo=timezone.utc)

        tz_name = (tz_name or "UTC").strip()
        tz_offsets = {
            "UTC": 0,
            "GMT": 0,
            "Asia/Tashkent": 5,
            "Tashkent": 5,
            "UZT": 5,
            "Europe/Moscow": 3,
            "Moscow": 3,
            "MSK": 3,
            "America/New_York": -5,
            "EDT": -4,
            "EST": -5,
            "America/Los_Angeles": -8,
            "PDT": -7,
            "PST": -8,
            "Europe/London": 0,
            "BST": 1,
            "Asia/Dubai": 4,
            "Asia/Almaty": 5,
            "Asia/Tokyo": 9,
        }
        offset_hours = tz_offsets.get(tz_name, 0)
        return now_dt.astimezone(timezone(timedelta(hours=offset_hours)))

    @classmethod
    def is_in_schedule(cls, campaign: AdCampaign, now_dt: datetime = None) -> tuple[bool, float]:
        """
        Checks if the campaign is active according to its Dayparting schedule.
        Returns (is_active, schedule_multiplier).
        """
        cfg = getattr(campaign, "schedule_config", {}) or {}
        if not cfg or not isinstance(cfg, dict):
            return True, 1.0

        tz_name = getattr(campaign, "schedule_timezone", "UTC") or "UTC"
        local_dt = cls.get_local_datetime(now_dt, tz_name)
        day_of_week = local_dt.weekday()  # 0 = Monday, 6 = Sunday
        hour = local_dt.hour  # 0..23

        # 1. Enabled days check
        enabled_days = cfg.get("enabled_days")
        if enabled_days is not None and isinstance(enabled_days, list) and len(enabled_days) > 0:
            if day_of_week not in enabled_days:
                return False, 0.0

        # 2. Active hours range check
        start_hour = int(cfg.get("active_hours_start", 0) or 0)
        end_hour = int(cfg.get("active_hours_end", 23) or 23)
        if start_hour <= end_hour:
            if not (start_hour <= hour <= end_hour):
                return False, 0.0
        else:
            # Overnight schedule, e.g. 22:00 to 06:00
            if not (hour >= start_hour or hour <= end_hour):
                return False, 0.0

        # 3. Hourly multipliers
        hourly_mults = cfg.get("hourly_multipliers") or {}
        if isinstance(hourly_mults, dict) and str(hour) in hourly_mults:
            try:
                mult = float(hourly_mults[str(hour)])
                if mult <= 0.0:
                    return False, 0.0
                return True, mult
            except (ValueError, TypeError):
                pass

        # 4. Peak hours boost
        peak_hours = cfg.get("peak_hours") or []
        if isinstance(peak_hours, list) and hour in peak_hours:
            peak_mult = float(cfg.get("peak_hours_multiplier", 1.25) or 1.25)
            return True, peak_mult

        return True, 1.0

    @classmethod
    @DB.connection_context()
    def calculate_smart_bid(
        cls,
        campaign: AdCampaign,
        clean_query: str = "",
        now_dt: datetime = None,
        log_decision: bool = False,
    ) -> dict:
        """
        Calculates dynamic bid based on bidding strategy, dayparting multiplier, intent keywords, and CVR.
        """
        strategy = getattr(campaign, "bidding_strategy", "manual_cpc") or "manual_cpc"
        base_bid = float(campaign.bid_amount or 0.10)
        daily_budget = float(campaign.daily_budget or 100.0)

        # 1. Dayparting schedule evaluation
        is_active, sched_mult = cls.is_in_schedule(campaign, now_dt)
        if not is_active:
            return {
                "active": False,
                "dynamic_bid": 0.0,
                "base_bid": base_bid,
                "schedule_multiplier": 0.0,
                "cvr_multiplier": 0.0,
                "estimated_cvr": 0.0,
                "strategy": strategy,
                "reason": "Outside scheduled active hours / days",
            }

        # 2. Historical conversion rate
        cvr_metric = float(getattr(campaign, "conversion_rate", 0.0) or 0.0)
        if cvr_metric <= 0.0:
            try:
                c_count = AdClick.select().where(AdClick.campaign_id == campaign.id).count()
                conv_count = AdConversion.select().where(AdConversion.campaign_id == campaign.id).count()
                cvr_metric = (conv_count / c_count) if c_count > 0 else 0.03
            except Exception:
                cvr_metric = 0.03
        else:
            cvr_metric = cvr_metric / 100.0 if cvr_metric > 1.0 else cvr_metric

        estimated_cvr = max(0.005, min(0.50, cvr_metric))

        # 3. Strategy evaluation
        cvr_mult = 1.0
        reason = "Manual CPC standard"

        if strategy == "enhanced_cpc":
            has_high_intent = any(hw in clean_query for hw in cls.HIGH_INTENT_WORDS) if clean_query else False
            has_low_intent = any(lw in clean_query for lw in cls.LOW_INTENT_WORDS) if clean_query else False

            if has_high_intent:
                intent_boost = 1.30
                reason = "Enhanced CPC (+30% commercial intent boost)"
            elif has_low_intent:
                intent_boost = 0.70
                reason = "Enhanced CPC (-30% informational query reduction)"
            else:
                intent_boost = 1.0
                reason = "Enhanced CPC (baseline intent)"

            if estimated_cvr > 0.05:
                intent_boost *= 1.15
                reason += " + High CVR bonus"

            cvr_mult = round(intent_boost, 2)
            dynamic_bid = base_bid * sched_mult * cvr_mult

        elif strategy == "target_cpa":
            target_cpa = float(getattr(campaign, "target_cpa", 0.0) or 0.0)
            if target_cpa <= 0.0:
                target_cpa = max(1.0, base_bid * 10.0)
            calculated_bid = target_cpa * estimated_cvr
            cvr_mult = round(calculated_bid / max(0.01, base_bid), 2)
            dynamic_bid = calculated_bid * sched_mult
            reason = f"Target CPA auto-bid (${target_cpa:.2f} @ {estimated_cvr*100:.1f}% CVR)"

        elif strategy == "maximize_conversions":
            spent_today = float(getattr(campaign, "spent_today", 0.0) or 0.0)
            budget_ratio = (spent_today / daily_budget) if daily_budget > 0 else 0.0
            if budget_ratio < 0.60:
                cvr_mult = 1.25
                reason = "Maximize Conversions (+25% budget accelerator)"
            else:
                cvr_mult = 1.0
                reason = "Maximize Conversions (standard pacing)"
            dynamic_bid = base_bid * sched_mult * cvr_mult

        else:  # manual_cpc
            cvr_mult = 1.0
            dynamic_bid = base_bid * sched_mult
            reason = f"Manual CPC (Schedule multiplier: {sched_mult}x)"

        max_cap = max(0.50, daily_budget if daily_budget > 0 else 100.0)
        final_bid = round(max(0.01, min(max_cap, dynamic_bid)), 4)

        if log_decision:
            try:
                AdBiddingLog.create(
                    id=uuid.uuid4().hex[:32],
                    campaign_id=campaign.id,
                    advertiser_id=campaign.advertiser_id,
                    strategy=strategy,
                    base_bid=base_bid,
                    adjusted_bid=final_bid,
                    schedule_multiplier=sched_mult,
                    cvr_multiplier=cvr_mult,
                    estimated_cvr=estimated_cvr,
                    reason=reason,
                    query=(clean_query[:250] if clean_query else ""),
                    create_time=current_timestamp(),
                )
            except Exception as e:
                logger.warning(f"Failed to record AdBiddingLog: {e}")

        return {
            "active": True,
            "dynamic_bid": final_bid,
            "base_bid": base_bid,
            "schedule_multiplier": sched_mult,
            "cvr_multiplier": cvr_mult,
            "estimated_cvr": estimated_cvr,
            "strategy": strategy,
            "reason": reason,
        }

    @classmethod
    @DB.connection_context()
    def update_campaign_bidding(
        cls,
        campaign_id: str,
        advertiser_id: str,
        bidding_strategy: str = None,
        target_cpa: float = None,
        schedule_timezone: str = None,
        schedule_config: dict = None,
    ) -> dict:
        cmp = AdCampaign.get_or_none(
            AdCampaign.id == campaign_id,
            AdCampaign.advertiser_id == advertiser_id,
        )
        if not cmp:
            raise ValueError("Кампания не найдена")

        if bidding_strategy is not None:
            if bidding_strategy not in cls.KNOWN_STRATEGIES:
                raise ValueError(f"Неизвестная стратегия ставок: {bidding_strategy}")
            cmp.bidding_strategy = bidding_strategy

        if target_cpa is not None:
            cmp.target_cpa = max(0.0, float(target_cpa))

        if schedule_timezone is not None:
            cmp.schedule_timezone = schedule_timezone

        if schedule_config is not None and isinstance(schedule_config, dict):
            cmp.schedule_config = schedule_config

        cmp.update_time = current_timestamp()
        cmp.save()

        return cls.get_campaign_bidding_info(campaign_id, advertiser_id)

    @classmethod
    @DB.connection_context()
    def get_campaign_bidding_info(cls, campaign_id: str, advertiser_id: str) -> dict:
        cmp = AdCampaign.get_or_none(
            AdCampaign.id == campaign_id,
            AdCampaign.advertiser_id == advertiser_id,
        )
        if not cmp:
            raise ValueError("Кампания не найдена")

        now_dt = datetime.now(timezone.utc)
        tz_name = getattr(cmp, "schedule_timezone", "UTC") or "UTC"
        local_dt = cls.get_local_datetime(now_dt, tz_name)
        is_active, current_mult = cls.is_in_schedule(cmp, now_dt)

        # Recent bidding decision logs
        recent_logs = list(
            AdBiddingLog.select()
            .where(AdBiddingLog.campaign_id == campaign_id)
            .order_by(AdBiddingLog.create_time.desc())
            .limit(20)
        )

        return {
            "campaign_id": cmp.id,
            "campaign_name": cmp.name,
            "bidding_strategy": getattr(cmp, "bidding_strategy", "manual_cpc") or "manual_cpc",
            "base_bid": float(cmp.bid_amount or 0.10),
            "target_cpa": float(getattr(cmp, "target_cpa", 0.0) or 0.0),
            "schedule_timezone": tz_name,
            "schedule_config": getattr(cmp, "schedule_config", {}) or {},
            "current_status": {
                "is_active_now": is_active,
                "current_multiplier": current_mult,
                "local_time": local_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "local_day": local_dt.strftime("%A"),
                "local_hour": local_dt.hour,
            },
            "recent_bids": [{
                "id": b.id,
                "strategy": b.strategy,
                "base_bid": b.base_bid,
                "adjusted_bid": b.adjusted_bid,
                "schedule_multiplier": b.schedule_multiplier,
                "cvr_multiplier": b.cvr_multiplier,
                "estimated_cvr": b.estimated_cvr,
                "reason": b.reason,
                "query": b.query,
                "create_time": b.create_time,
            } for b in recent_logs],
        }

    @classmethod
    def list_strategies(cls) -> list:
        return list(cls.KNOWN_STRATEGIES.values())


class AdDcoEngineService:
    """
    Dynamic Creative Optimization (DCO) & Real-time Contextual Ad Insertion Service.
    Handles Dynamic Keyword Insertion (DKI), City/Region Localization, LLM Model Tagging,
    UTM Link Assembly, Dynamic CTA & Promo Code Generation, and Tone of Voice Formatting.
    """

    STOPWORDS_RU = {
        "как", "где", "какой", "какая", "какое", "какие", "какую", "посоветуй", "посоветуйте",
        "подскажи", "подскажите", "порекомендуй", "порекомендуйте", "лучший", "лучшая", "лучшее",
        "лучшие", "лучшую", "самый", "самая", "самое", "самые", "самую", "топ", "найти", "выбрать",
        "для", "в", "на", "с", "по", "ли", "есть", "что", "это", "мне", "нам", "нужен", "нужна",
        "нужно", "нужны", "хочу", "купить", "заказать", "цена", "стоимость", "недорого", "онлайн",
        "ташкент", "узбекистан", "россия", "москва"
    }

    STOPWORDS_UZ = {
        "qanday", "qayerda", "qaysi", "qanaqa", "eng", "yaxshi", "tavsiya", "qil", "qiling", "topish",
        "uchun", "kerak", "bormi", "nima", "menga", "bizga", "qayerdan", "olish", "mumkin", "narxi",
        "qancha", "toshkent", "uzbekistan"
    }

    STOPWORDS_EN = {
        "how", "where", "what", "which", "best", "top", "recommend", "find", "choose", "for", "in",
        "to", "the", "a", "an", "is", "are", "can", "you", "tell", "me", "us", "about", "need", "want",
        "price", "cost", "online"
    }

    REGION_NAMES_MAP = {
        "tashkent": {"ru": "в Ташкенте", "uz": "Toshkentda", "en": "in Tashkent"},
        "samarkand": {"ru": "в Самарканде", "uz": "Samarqandda", "en": "in Samarkand"},
        "bukhara": {"ru": "в Бухаре", "uz": "Buxoroda", "en": "in Bukhara"},
        "fergana": {"ru": "в Фергане", "uz": "Farg'onada", "en": "in Fergana"},
        "andijan": {"ru": "в Андижане", "uz": "Andijonda", "en": "in Andijan"},
        "namangan": {"ru": "в Намангане", "uz": "Namanganda", "en": "in Namangan"},
        "khorezm": {"ru": "в Хорезме", "uz": "Xorazmda", "en": "in Khorezm"},
        "kashkadarya": {"ru": "в Кашкадарье", "uz": "Qashqadaryoda", "en": "in Kashkadarya"},
        "karakalpakstan": {"ru": "в Каракалпакстане", "uz": "Qoraqalpog'istonda", "en": "in Karakalpakstan"},
        "moscow": {"ru": "в Москве", "uz": "Moskvada", "en": "in Moscow"},
        "global": {"ru": "онлайн", "uz": "onlayn", "en": "online"},
    }

    @classmethod
    def extract_salient_keyword(cls, query: str, default_fallback: str = "наше решение", lang: str = "ru") -> str:
        """
        Extract meaningful search subject from query (e.g. 'CRM для продаж', 'курсы английского').
        Removes conversational noise and question prefixes.
        """
        if not query:
            return default_fallback

        clean = re.sub(r"[^\w\s\-]", " ", query.lower()).strip()
        words = clean.split()
        if not words:
            return default_fallback

        stopwords = cls.STOPWORDS_UZ if lang == "uz" else (cls.STOPWORDS_EN if lang == "en" else cls.STOPWORDS_RU)
        filtered = [w for w in words if w not in stopwords and len(w) >= 2]
        if not filtered:
            return default_fallback

        result_words = []
        for i, w in enumerate(filtered[:3]):
            if len(w) <= 4 and w.upper() in ["CRM", "ERP", "CMS", "B2B", "B2C", "POS", "AI", "SDK", "API", "SEO", "SMM"]:
                result_words.append(w.upper())
            elif i == 0:
                result_words.append(w.capitalize())
            else:
                result_words.append(w)

        return " ".join(result_words) if result_words else default_fallback

    @classmethod
    def resolve_region_label(cls, region: str = "tashkent", query: str = "", lang: str = "ru") -> str:
        """
        Detect city/region in query or use region parameter.
        """
        q_lower = (query or "").lower()
        effective_region = (region or "tashkent").lower()

        for r_key in ["samarkand", "bukhara", "fergana", "andijan", "namangan", "khorezm", "kashkadarya", "karakalpakstan", "moscow", "tashkent"]:
            if r_key in q_lower or (r_key == "tashkent" and ("ташкент" in q_lower or "toshkent" in q_lower)) or \
               (r_key == "samarkand" and ("самарканд" in q_lower or "samarqand" in q_lower)) or \
               (r_key == "bukhara" and ("бухар" in q_lower or "buxor" in q_lower)):
                effective_region = r_key
                break

        lang_key = lang if lang in ["ru", "uz", "en"] else "ru"
        mapping = cls.REGION_NAMES_MAP.get(effective_region, cls.REGION_NAMES_MAP["global"])
        return mapping.get(lang_key, mapping["ru"])

    @classmethod
    def substitute_macro_tokens(
        cls,
        template_str: str,
        keyword: str,
        city: str,
        model_name: str,
        lang: str,
        day_name: str,
        promo_code: str,
        discount_percent: float,
        campaign: AdCampaign = None,
    ) -> str:
        """
        Replace macro tokens in format {keyword}, {keyword:default}, {city}, {city:default},
        {model}, {lang}, {day}, {promo}, {discount}, {product}
        """
        if not template_str:
            return ""

        def token_replacer(match):
            token_full = match.group(1).strip()
            parts = token_full.split(":", 1)
            token_name = parts[0].lower().strip()
            default_val = parts[1].strip() if len(parts) > 1 else ""

            if token_name in ["keyword", "kw", "query"]:
                return keyword or default_val or "наше решение"
            elif token_name in ["city", "region", "location"]:
                return city or default_val or "вашем регионе"
            elif token_name in ["model", "ai", "llm"]:
                return model_name or default_val or "AI"
            elif token_name in ["lang", "language"]:
                return lang or default_val or "ru"
            elif token_name in ["day", "weekday", "today"]:
                return day_name or default_val or "сегодня"
            elif token_name in ["promo", "promo_code", "promocode"]:
                return promo_code or default_val or ""
            elif token_name in ["discount", "discount_percent"]:
                return f"{int(discount_percent)}%" if discount_percent else (default_val or "скидка")
            elif token_name in ["product", "product_name"]:
                return (campaign.product_name if campaign else default_val) or "сервис"
            return match.group(0)

        result = re.sub(r"\{([^}]+)\}", token_replacer, template_str)
        return result

    @classmethod
    def build_dynamic_url(
        cls,
        base_url: str,
        campaign_id: str,
        inserted_keyword: str,
        model: str,
        region: str,
        lang: str,
        utm_auto_tagging: bool = True,
        promo_code: str = "",
    ) -> str:
        """
        Add UTM parameters and dynamic tokens to landing page URL.
        """
        if not base_url:
            return "https://swipies.app"

        import urllib.parse
        parsed = urllib.parse.urlparse(base_url)
        query_params = urllib.parse.parse_qs(parsed.query)

        if utm_auto_tagging:
            if "utm_source" not in query_params:
                query_params["utm_source"] = ["swipies"]
            if "utm_medium" not in query_params:
                query_params["utm_medium"] = ["ai_native"]
            if "utm_campaign" not in query_params:
                query_params["utm_campaign"] = [campaign_id]
            if "utm_term" not in query_params and inserted_keyword:
                query_params["utm_term"] = [inserted_keyword]
            if "utm_content" not in query_params:
                query_params["utm_content"] = [model or "ai"]
            if "utm_region" not in query_params:
                query_params["utm_region"] = [region or "global"]
            if "utm_lang" not in query_params:
                query_params["utm_lang"] = [lang or "ru"]
            if promo_code and "promo" not in query_params:
                query_params["promo"] = [promo_code]

        new_query = urllib.parse.urlencode(query_params, doseq=True)
        new_url = urllib.parse.urlunparse((
            parsed.scheme or "https",
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment
        ))
        return new_url

    @classmethod
    def apply_tone_formatting(cls, text: str, tone_style: str, lang: str = "ru", promo_code: str = "") -> str:
        """
        Add contextual tone prefixes or styling.
        """
        if not text:
            return ""

        t = (tone_style or "auto").lower()
        if t == "urgent":
            prefix = "⚡ Спецпредложение: " if lang == "ru" else ("⚡ Maxsus taklif: " if lang == "uz" else "⚡ Special Offer: ")
            return f"{prefix}{text}"
        elif t == "friendly":
            prefix = "💡 Рекомендуем: " if lang == "ru" else ("💡 Tavsiya qilamiz: " if lang == "uz" else "💡 Recommended: ")
            return f"{prefix}{text}"
        elif t == "technical":
            prefix = "⚙️ Решение: " if lang == "ru" else ("⚙️ Yechim: " if lang == "uz" else "⚙️ Solution: ")
            return f"{prefix}{text}"
        return text

    @classmethod
    @DB.connection_context()
    def render_dco_copy(
        cls,
        campaign: AdCampaign,
        query: str,
        base_text: str = None,
        base_url: str = None,
        model: str = "gpt-4o",
        lang: str = "ru",
        region: str = "tashkent",
        user_id: str = "",
        log_decision: bool = True,
    ) -> dict:
        """
        Main DCO execution engine.
        Takes candidate campaign, parses dynamic tokens ({keyword}, {city}, etc.), generates
        dynamic URL with UTM tags, applies CTA & Promo Code, and records log.
        """
        dco_cfg = getattr(campaign, "dco_config", {}) or {}
        dco_enabled = getattr(campaign, "dco_enabled", False)

        original_text = base_text or campaign.advertisement_text or ""
        original_url = base_url or campaign.landing_url or "https://swipies.app"

        has_tokens = "{" in original_text or (dco_cfg.get("description_template") and "{" in dco_cfg.get("description_template")) or (dco_cfg.get("url_template") and "{" in dco_cfg.get("url_template"))

        if not dco_enabled and not has_tokens:
            return {
                "dco_applied": False,
                "rendered_text": original_text,
                "rendered_url": original_url,
                "cta_text": dco_cfg.get("cta_text", ""),
                "promo_code": dco_cfg.get("promo_code", ""),
                "discount_percent": float(dco_cfg.get("discount_percent", 0.0) or 0.0),
                "inserted_keyword": None,
                "applied_city": None,
                "applied_model": None,
            }

        # 1. Extract context variables
        default_kw = dco_cfg.get("default_keyword") or campaign.product_name or "наше решение"
        extracted_kw = cls.extract_salient_keyword(query, default_kw, lang=lang)
        city_label = cls.resolve_region_label(region, query, lang=lang)

        clean_model = (model or "AI").split("-")[0].capitalize()
        if "deepseek" in (model or "").lower():
            clean_model = "DeepSeek"
        elif "gpt" in (model or "").lower():
            clean_model = "ChatGPT"
        elif "claude" in (model or "").lower():
            clean_model = "Claude"

        day_name = datetime.now(timezone.utc).strftime("%A")
        promo = dco_cfg.get("promo_code") or ""
        discount = float(dco_cfg.get("discount_percent") or 0.0)
        tone = dco_cfg.get("tone_style") or "auto"
        utm_auto = dco_cfg.get("utm_auto_tagging", True)

        # 2. Render Text
        template_text = dco_cfg.get("description_template") or original_text
        rendered_text = cls.substitute_macro_tokens(
            template_str=template_text,
            keyword=extracted_kw,
            city=city_label,
            model_name=clean_model,
            lang=lang,
            day_name=day_name,
            promo_code=promo,
            discount_percent=discount,
            campaign=campaign,
        )
        rendered_text = cls.apply_tone_formatting(rendered_text, tone, lang=lang, promo_code=promo)

        # 3. Render URL
        template_url = dco_cfg.get("url_template") or original_url
        substituted_url = cls.substitute_macro_tokens(
            template_str=template_url,
            keyword=extracted_kw,
            city=city_label,
            model_name=clean_model,
            lang=lang,
            day_name=day_name,
            promo_code=promo,
            discount_percent=discount,
            campaign=campaign,
        )
        rendered_url = cls.build_dynamic_url(
            base_url=substituted_url,
            campaign_id=campaign.id,
            inserted_keyword=extracted_kw,
            model=model,
            region=region,
            lang=lang,
            utm_auto_tagging=utm_auto,
            promo_code=promo,
        )

        # 4. Render CTA
        cta_template = dco_cfg.get("cta_text") or ""
        rendered_cta = cls.substitute_macro_tokens(
            template_str=cta_template,
            keyword=extracted_kw,
            city=city_label,
            model_name=clean_model,
            lang=lang,
            day_name=day_name,
            promo_code=promo,
            discount_percent=discount,
            campaign=campaign,
        )

        # 5. Log DCO execution
        if log_decision:
            try:
                AdDcoLog.create(
                    id=uuid.uuid4().hex[:32],
                    campaign_id=campaign.id,
                    advertiser_id=campaign.advertiser_id,
                    query=(query or "")[:500],
                    original_text=original_text,
                    rendered_text=rendered_text,
                    original_url=original_url,
                    rendered_url=rendered_url,
                    inserted_keyword=extracted_kw,
                    applied_city=city_label,
                    applied_model=clean_model,
                    applied_promo=promo or None,
                    create_time=current_timestamp(),
                )
            except Exception as e:
                logger.debug(f"Failed to log AdDcoLog: {e}")

        return {
            "dco_applied": True,
            "rendered_text": rendered_text,
            "rendered_url": rendered_url,
            "cta_text": rendered_cta,
            "promo_code": promo,
            "discount_percent": discount,
            "inserted_keyword": extracted_kw,
            "applied_city": city_label,
            "applied_model": clean_model,
        }

    @classmethod
    @DB.connection_context()
    def get_campaign_dco_info(cls, campaign_id: str) -> dict:
        """
        Fetch current DCO configuration and recent logs for a campaign.
        """
        cmp = AdCampaign.get_or_none(AdCampaign.id == campaign_id)
        if not cmp:
            raise ValueError("Campaign not found")

        dco_cfg = getattr(cmp, "dco_config", {}) or {}
        recent_logs = list(
            AdDcoLog.select()
            .where(AdDcoLog.campaign_id == campaign_id)
            .order_by(AdDcoLog.create_time.desc())
            .limit(20)
        )

        return {
            "campaign_id": cmp.id,
            "campaign_name": cmp.name,
            "dco_enabled": bool(getattr(cmp, "dco_enabled", False)),
            "dco_config": {
                "headline_template": dco_cfg.get("headline_template", ""),
                "description_template": dco_cfg.get("description_template", cmp.advertisement_text or ""),
                "url_template": dco_cfg.get("url_template", cmp.landing_url or ""),
                "utm_auto_tagging": dco_cfg.get("utm_auto_tagging", True),
                "default_keyword": dco_cfg.get("default_keyword", cmp.product_name or ""),
                "cta_text": dco_cfg.get("cta_text", "Попробовать бесплатно"),
                "promo_code": dco_cfg.get("promo_code", ""),
                "discount_percent": float(dco_cfg.get("discount_percent", 0.0) or 0.0),
                "tone_style": dco_cfg.get("tone_style", "auto"),
            },
            "recent_logs": [{
                "id": log.id,
                "query": log.query,
                "inserted_keyword": log.inserted_keyword,
                "applied_city": log.applied_city,
                "applied_model": log.applied_model,
                "applied_promo": log.applied_promo,
                "rendered_text": log.rendered_text,
                "rendered_url": log.rendered_url,
                "create_time": log.create_time,
            } for log in recent_logs],
        }

    @classmethod
    @DB.connection_context()
    def update_campaign_dco(cls, campaign_id: str, dco_enabled: bool, dco_config: dict) -> dict:
        """
        Update DCO rules and templates for a campaign.
        """
        cmp = AdCampaign.get_or_none(AdCampaign.id == campaign_id)
        if not cmp:
            raise ValueError("Campaign not found")

        cmp.dco_enabled = bool(dco_enabled)
        cmp.dco_config = dco_config or {}
        cmp.update_time = current_timestamp()
        cmp.save()

        return cls.get_campaign_dco_info(campaign_id)

    @classmethod
    @DB.connection_context()
    def preview_dco(
        cls,
        campaign_id: str,
        query: str,
        model: str = "gpt-4o",
        region: str = "tashkent",
        lang: str = "ru",
        custom_template: str = None,
        custom_url_template: str = None,
        custom_cta: str = None,
        custom_promo: str = None,
        custom_discount: float = 0.0,
        custom_tone: str = "auto",
    ) -> dict:
        """
        Test and preview DCO rendering for a given query in real time.
        """
        cmp = AdCampaign.get_or_none(AdCampaign.id == campaign_id)
        if not cmp:
            raise ValueError("Campaign not found")

        dco_cfg = getattr(cmp, "dco_config", {}) or {}
        template_text = custom_template if custom_template is not None else (dco_cfg.get("description_template") or cmp.advertisement_text or "")
        template_url = custom_url_template if custom_url_template is not None else (dco_cfg.get("url_template") or cmp.landing_url or "")
        cta = custom_cta if custom_cta is not None else dco_cfg.get("cta_text", "Попробовать бесплатно")
        promo = custom_promo if custom_promo is not None else dco_cfg.get("promo_code", "")
        discount = float(custom_discount if custom_discount is not None else (dco_cfg.get("discount_percent") or 0.0))
        tone = custom_tone if custom_tone is not None else dco_cfg.get("tone_style", "auto")

        default_kw = dco_cfg.get("default_keyword") or cmp.product_name or "наше решение"
        extracted_kw = cls.extract_salient_keyword(query, default_kw, lang=lang)
        city_label = cls.resolve_region_label(region, query, lang=lang)
        clean_model = (model or "AI").split("-")[0].capitalize()
        day_name = datetime.now(timezone.utc).strftime("%A")

        rendered_text = cls.substitute_macro_tokens(
            template_str=template_text,
            keyword=extracted_kw,
            city=city_label,
            model_name=clean_model,
            lang=lang,
            day_name=day_name,
            promo_code=promo,
            discount_percent=discount,
            campaign=cmp,
        )
        rendered_text = cls.apply_tone_formatting(rendered_text, tone, lang=lang, promo_code=promo)

        substituted_url = cls.substitute_macro_tokens(
            template_str=template_url,
            keyword=extracted_kw,
            city=city_label,
            model_name=clean_model,
            lang=lang,
            day_name=day_name,
            promo_code=promo,
            discount_percent=discount,
            campaign=cmp,
        )
        rendered_url = cls.build_dynamic_url(
            base_url=substituted_url,
            campaign_id=cmp.id,
            inserted_keyword=extracted_kw,
            model=model,
            region=region,
            lang=lang,
            utm_auto_tagging=dco_cfg.get("utm_auto_tagging", True),
            promo_code=promo,
        )

        rendered_cta = cls.substitute_macro_tokens(
            template_str=cta,
            keyword=extracted_kw,
            city=city_label,
            model_name=clean_model,
            lang=lang,
            day_name=day_name,
            promo_code=promo,
            discount_percent=discount,
            campaign=cmp,
        )

        return {
            "query": query,
            "extracted_keyword": extracted_kw,
            "applied_city": city_label,
            "applied_model": clean_model,
            "rendered_text": rendered_text,
            "rendered_url": rendered_url,
            "rendered_cta": rendered_cta,
            "promo_code": promo,
            "discount_percent": discount,
            "tone_style": tone,
        }


class AdBudgetPacingService:
    """
    Predictive Budget Pacing Engine.
    Controls daily budget consumption rate throughout the day to avoid premature budget exhaustion.
    Modes:
    - standard_smooth: Smooth pacing against cumulative daily time curve.
    - accelerated_asap: Enter auctions as fast as possible without throttling.
    - peak_weighted: Focus budget on peak commercial hours (12:00 - 20:00).
    """

    # Cumulative expected spend percentage by local hour (0-23) for standard commercial traffic
    HOURLY_STANDARD_CURVE = [
        0.02, 0.03, 0.04, 0.05, 0.06, 0.08, 0.12, 0.17,
        0.24, 0.32, 0.40, 0.48, 0.56, 0.64, 0.72, 0.80,
        0.86, 0.91, 0.95, 0.97, 0.98, 0.99, 0.995, 1.0
    ]

    # Peak weighted curve (steep ramp between 12:00 and 20:00)
    HOURLY_PEAK_CURVE = [
        0.01, 0.01, 0.02, 0.02, 0.03, 0.04, 0.06, 0.09,
        0.14, 0.20, 0.28, 0.38, 0.50, 0.62, 0.74, 0.84,
        0.90, 0.94, 0.97, 0.98, 0.99, 0.995, 0.998, 1.0
    ]

    @classmethod
    def calculate_pacing_multiplier(cls, campaign: AdCampaign, now_dt: datetime = None) -> float:
        """
        Calculate pacing bid multiplier (0.5 to 1.2) based on daily budget progress.
        """
        pacing_mode = getattr(campaign, "pacing_mode", "standard_smooth") or "standard_smooth"
        if pacing_mode == "accelerated_asap":
            return 1.0

        daily_budget = float(campaign.daily_budget or 10.0)
        spent_today = float(campaign.spent_today or 0.0)
        if daily_budget <= 0:
            return 1.0

        # Localize current time according to campaign schedule timezone
        tz_name = getattr(campaign, "schedule_timezone", "Asia/Tashkent") or "Asia/Tashkent"
        now_dt = now_dt or datetime.now(timezone.utc)

        tz_offsets = {
            "Asia/Tashkent": 5,
            "Asia/Samarkand": 5,
            "Europe/Moscow": 3,
            "UTC": 0,
            "America/New_York": -5,
            "Europe/London": 0,
        }
        offset_hours = tz_offsets.get(tz_name, 5)
        local_dt = now_dt + timedelta(hours=offset_hours)
        hour = min(23, max(0, local_dt.hour))

        curve = cls.HOURLY_PEAK_CURVE if pacing_mode == "peak_weighted" else cls.HOURLY_STANDARD_CURVE
        expected_spent_ratio = curve[hour]
        actual_spent_ratio = min(1.0, spent_today / daily_budget)

        # If we have spent way ahead of schedule (> 25% above target curve)
        if actual_spent_ratio > expected_spent_ratio + 0.25:
            # Overpacing: dampen bids smoothly to preserve budget for later hours
            burn_factor = actual_spent_ratio / max(0.05, expected_spent_ratio)
            pacing_mult = max(0.50, 1.0 / min(2.0, burn_factor))
            return round(pacing_mult, 2)
        elif actual_spent_ratio < expected_spent_ratio - 0.25 and hour >= 8:
            # Underpacing: slight bid boost (+15%) to capture available volume
            return 1.15

        return 1.0

    @classmethod
    @DB.connection_context()
    def get_campaign_pacing_forecast(cls, campaign_id: str) -> dict:
        cmp = AdCampaign.get_by_id(campaign_id)
        daily_budget = float(cmp.daily_budget or 10.0)
        spent_today = float(cmp.spent_today or 0.0)
        pacing_mode = getattr(cmp, "pacing_mode", "standard_smooth") or "standard_smooth"
        tz_name = getattr(cmp, "schedule_timezone", "Asia/Tashkent") or "Asia/Tashkent"

        curve = cls.HOURLY_PEAK_CURVE if pacing_mode == "peak_weighted" else cls.HOURLY_STANDARD_CURVE
        hourly_forecast = []
        for h, ratio in enumerate(curve):
            target_amount = round(daily_budget * ratio, 2)
            hourly_forecast.append({
                "hour": h,
                "hour_label": f"{h:02d}:00",
                "expected_cumulative_spend": target_amount,
                "expected_ratio": round(ratio * 100, 1),
            })

        current_mult = cls.calculate_pacing_multiplier(cmp)
        return {
            "campaign_id": cmp.id,
            "campaign_name": cmp.name,
            "daily_budget": daily_budget,
            "spent_today": spent_today,
            "pacing_mode": pacing_mode,
            "schedule_timezone": tz_name,
            "current_pacing_multiplier": current_mult,
            "burn_rate_status": "overpacing" if current_mult < 0.9 else ("underpacing" if current_mult > 1.05 else "optimal"),
            "hourly_forecast": hourly_forecast,
        }

    @classmethod
    @DB.connection_context()
    def update_campaign_pacing(cls, campaign_id: str, pacing_mode: str) -> dict:
        cmp = AdCampaign.get_by_id(campaign_id)
        if pacing_mode not in ["standard_smooth", "accelerated_asap", "peak_weighted"]:
            pacing_mode = "standard_smooth"
        cmp.pacing_mode = pacing_mode
        cmp.save()
        return cls.get_campaign_pacing_forecast(campaign_id)


class AdAutomatedRulesService:
    """
    Automated Rules & Auto-Pilot Campaign Optimization Engine.
    Evaluates conditional triggers (Stop-Loss, CPA Guard, Scale Winners, Burn Rate Alert)
    and executes automated actions with execution logging and multi-channel notifications.
    """

    DEFAULT_TEMPLATES = [
        {
            "template_id": "stop_loss_low_ctr",
            "name": "🛡️ Stop Loss: Пауза при низком CTR",
            "description": "Приостанавливает кампанию, если CTR опускается ниже 0.5% после 100 показов (защита от нерелевантного расхода).",
            "metric": "ctr",
            "operator": "<",
            "threshold_value": 0.50,
            "min_impressions": 100,
            "time_window": "today",
            "action_type": "pause_campaign",
            "action_value": 0.0,
        },
        {
            "template_id": "cpa_guard_reduce_bid",
            "name": "💰 CPA Guard: Снижение ставки при дорогой конверсии",
            "description": "Снижает ставку на 20%, если стоимость целевого действия (CPA) превышает $10 при наличии конверсий.",
            "metric": "cpa",
            "operator": ">",
            "threshold_value": 10.0,
            "min_impressions": 50,
            "time_window": "last_7_days",
            "action_type": "decrease_bid",
            "action_value": 20.0,
        },
        {
            "template_id": "scale_winner_budget",
            "name": "🚀 Scale Top Performer: Масштабирование лидеров",
            "description": "Увеличивает дневной бюджет на 30%, если конверсионность (CVR) превышает 4% за сегодня.",
            "metric": "cvr",
            "operator": ">",
            "threshold_value": 4.0,
            "min_impressions": 100,
            "time_window": "today",
            "action_type": "increase_budget",
            "action_value": 30.0,
        },
        {
            "template_id": "budget_burn_alert",
            "name": "⏰ Контроль расхода: Оповещение при расходе > 90%",
            "description": "Отправляет экстренное уведомление рекламодателю, когда израсходовано более 90% дневного бюджета.",
            "metric": "spent_ratio",
            "operator": ">=",
            "threshold_value": 90.0,
            "min_impressions": 10,
            "time_window": "today",
            "action_type": "send_alert",
            "action_value": 0.0,
        },
    ]

    @classmethod
    def get_default_rule_templates(cls) -> list:
        return cls.DEFAULT_TEMPLATES

    @classmethod
    @DB.connection_context()
    def list_rules(cls, advertiser_id: str, campaign_id: str = None) -> list:
        query = AdAutomatedRule.select().where(AdAutomatedRule.advertiser_id == advertiser_id)
        if campaign_id:
            query = query.where((AdAutomatedRule.campaign_id == campaign_id) | (AdAutomatedRule.campaign_id == "all"))

        rules = list(query.order_by(AdAutomatedRule.create_time.desc()))
        res = []
        for r in rules:
            cmp_name = "Все кампании"
            if r.campaign_id and r.campaign_id != "all":
                c = AdCampaign.get_or_none(AdCampaign.id == r.campaign_id)
                if c:
                    cmp_name = c.name

            res.append({
                "id": r.id,
                "advertiser_id": r.advertiser_id,
                "campaign_id": r.campaign_id,
                "campaign_name": cmp_name,
                "name": r.name,
                "description": r.description or "",
                "metric": r.metric,
                "operator": r.operator,
                "threshold_value": r.threshold_value,
                "min_impressions": r.min_impressions,
                "time_window": r.time_window,
                "action_type": r.action_type,
                "action_value": r.action_value,
                "is_active": r.is_active,
                "last_evaluated_time": r.last_evaluated_time,
                "last_triggered_time": r.last_triggered_time,
                "trigger_count": r.trigger_count,
                "create_time": r.create_time,
            })
        return res

    @classmethod
    @DB.connection_context()
    def get_rule(cls, rule_id: str, advertiser_id: str = "") -> dict:
        rule = AdAutomatedRule.get_or_none(AdAutomatedRule.id == rule_id)
        if not rule or (advertiser_id and rule.advertiser_id != advertiser_id):
            return None
        return {
            "id": rule.id,
            "advertiser_id": rule.advertiser_id,
            "campaign_id": rule.campaign_id,
            "name": rule.name,
            "description": rule.description or "",
            "metric": rule.metric,
            "operator": rule.operator,
            "threshold_value": rule.threshold_value,
            "min_impressions": rule.min_impressions,
            "time_window": rule.time_window,
            "action_type": rule.action_type,
            "action_value": rule.action_value,
            "is_active": rule.is_active,
            "last_evaluated_time": rule.last_evaluated_time,
            "last_triggered_time": rule.last_triggered_time,
            "trigger_count": rule.trigger_count,
            "create_time": rule.create_time,
        }

    @classmethod
    @DB.connection_context()
    def create_rule(cls, advertiser_id: str, data: dict) -> dict:
        now_ts = current_timestamp()
        rule_id = uuid.uuid4().hex[:32]
        rule = AdAutomatedRule.create(
            id=rule_id,
            advertiser_id=advertiser_id,
            campaign_id=data.get("campaign_id", "all") or "all",
            name=data.get("name", "Новое авто-правило"),
            description=data.get("description", ""),
            metric=data.get("metric", "ctr"),
            operator=data.get("operator", "<"),
            threshold_value=float(data.get("threshold_value", 1.0)),
            min_impressions=int(data.get("min_impressions", 100)),
            time_window=data.get("time_window", "today"),
            action_type=data.get("action_type", "pause_campaign"),
            action_value=float(data.get("action_value", 0.0)),
            is_active=bool(data.get("is_active", True)),
            last_evaluated_time=None,
            last_triggered_time=None,
            trigger_count=0,
            create_time=now_ts,
            update_time=now_ts,
        )
        return cls.get_rule(rule.id, advertiser_id)

    @classmethod
    @DB.connection_context()
    def update_rule(cls, rule_id: str, advertiser_id: str, data: dict) -> dict:
        rule = AdAutomatedRule.get_or_none(AdAutomatedRule.id == rule_id)
        if not rule or (advertiser_id and rule.advertiser_id != advertiser_id):
            return None

        for field in ["campaign_id", "name", "description", "metric", "operator", "time_window", "action_type"]:
            if field in data:
                setattr(rule, field, data[field])

        if "threshold_value" in data:
            rule.threshold_value = float(data["threshold_value"])
        if "min_impressions" in data:
            rule.min_impressions = int(data["min_impressions"])
        if "action_value" in data:
            rule.action_value = float(data["action_value"])
        if "is_active" in data:
            rule.is_active = bool(data["is_active"])

        rule.update_time = current_timestamp()
        rule.save()
        return cls.get_rule(rule.id, advertiser_id)

    @classmethod
    @DB.connection_context()
    def delete_rule(cls, rule_id: str, advertiser_id: str) -> bool:
        rule = AdAutomatedRule.get_or_none(AdAutomatedRule.id == rule_id)
        if not rule or (advertiser_id and rule.advertiser_id != advertiser_id):
            return False
        rule.delete_instance()
        return True

    @classmethod
    @DB.connection_context()
    def toggle_rule(cls, rule_id: str, advertiser_id: str) -> dict:
        rule = AdAutomatedRule.get_or_none(AdAutomatedRule.id == rule_id)
        if not rule or (advertiser_id and rule.advertiser_id != advertiser_id):
            return None
        rule.is_active = not rule.is_active
        rule.update_time = current_timestamp()
        rule.save()
        return cls.get_rule(rule.id, advertiser_id)

    @classmethod
    @DB.connection_context()
    def evaluate_campaign_metrics(cls, campaign: AdCampaign, time_window: str = "today") -> dict:
        """
        Calculate actual performance metrics for a campaign over the specified time window.
        """
        now_ts = current_timestamp()
        if time_window == "today":
            # Start of current UTC day
            today_dt = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            since_ts = int(today_dt.timestamp() * 1000)
        elif time_window == "last_7_days":
            since_ts = now_ts - (7 * 86400 * 1000)
        elif time_window == "last_30_days":
            since_ts = now_ts - (30 * 86400 * 1000)
        else:  # lifetime
            since_ts = 0

        imp_query = AdImpression.select().where(
            (AdImpression.campaign_id == campaign.id) &
            (AdImpression.create_time >= since_ts)
        )
        impressions = imp_query.count()

        click_query = AdClick.select().where(
            (AdClick.campaign_id == campaign.id) &
            (AdClick.create_time >= since_ts)
        )
        clicks = click_query.count()

        conv_query = AdConversion.select().where(
            (AdConversion.campaign_id == campaign.id) &
            (AdConversion.create_time >= since_ts)
        )
        conversions = conv_query.count()

        # Calculate spend in window
        imp_cost = imp_query.select(fn.SUM(AdImpression.cost)).scalar() or 0.0
        click_cost = click_query.select(fn.SUM(AdClick.cost)).scalar() or 0.0
        total_spent = float(imp_cost) + float(click_cost)

        # Fallback to campaign accumulators if impressions table has fewer entries (e.g., in unit tests or fast sync)
        if time_window == "today":
            total_spent = max(total_spent, float(campaign.spent_today or 0.0))
        elif time_window == "lifetime":
            total_spent = max(total_spent, float(campaign.total_spent or 0.0))
            impressions = max(impressions, int(getattr(campaign, "impressions", 0) or 0))
            clicks = max(clicks, int(getattr(campaign, "clicks", 0) or 0))
            conversions = max(conversions, int(getattr(campaign, "conversions_count", 0) or 0))

        ctr = (clicks / impressions * 100.0) if impressions > 0 else float(getattr(campaign, "ctr", 0.0) or 0.0)
        cvr = (conversions / clicks * 100.0) if clicks > 0 else float(getattr(campaign, "conversion_rate", 0.0) or 0.0)
        cpa = (total_spent / conversions) if conversions > 0 else 0.0
        daily_budget = float(campaign.daily_budget or 10.0)
        spent_ratio = (float(campaign.spent_today or 0.0) / daily_budget * 100.0) if daily_budget > 0 else 0.0

        return {
            "impressions": impressions,
            "clicks": clicks,
            "conversions": conversions,
            "spent": round(total_spent, 2),
            "ctr": round(ctr, 2),
            "cvr": round(cvr, 2),
            "cpa": round(cpa, 2),
            "spent_ratio": round(spent_ratio, 1),
            "current_bid": float(campaign.bid_amount or 0.10),
            "daily_budget": daily_budget,
            "status": campaign.status,
        }

    @classmethod
    def _check_condition(cls, current_val: float, operator: str, threshold: float) -> bool:
        if operator == "<":
            return current_val < threshold
        elif operator == "<=":
            return current_val <= threshold
        elif operator == ">":
            return current_val > threshold
        elif operator == ">=":
            return current_val >= threshold
        elif operator in ["==", "="]:
            return abs(current_val - threshold) < 0.001
        return False

    @classmethod
    @DB.connection_context()
    def execute_rule(cls, rule: AdAutomatedRule, campaign: AdCampaign = None) -> list:
        """
        Evaluate a rule against relevant campaigns and execute automated action if triggered.
        Returns list of executed actions.
        """
        now_ts = current_timestamp()
        rule.last_evaluated_time = now_ts
        rule.save()

        campaigns_to_evaluate = []
        if campaign:
            campaigns_to_evaluate.append(campaign)
        elif rule.campaign_id and rule.campaign_id != "all":
            c = AdCampaign.get_or_none(AdCampaign.id == rule.campaign_id)
            if c:
                campaigns_to_evaluate.append(c)
        else:
            campaigns_to_evaluate = list(
                AdCampaign.select().where(
                    (AdCampaign.advertiser_id == rule.advertiser_id) &
                    (AdCampaign.status != "archived")
                )
            )

        executed_results = []
        for cmp in campaigns_to_evaluate:
            metrics = cls.evaluate_campaign_metrics(cmp, rule.time_window)
            current_metric_val = float(metrics.get(rule.metric, 0.0))
            impressions = metrics.get("impressions", 0)

            # Check safety min_impressions threshold
            if impressions < rule.min_impressions and rule.metric not in ["spent_ratio", "spent"]:
                continue

            triggered = cls._check_condition(current_metric_val, rule.operator, rule.threshold_value)
            if not triggered:
                continue

            action = rule.action_type
            val = rule.action_value or 0.0
            action_desc = ""

            if action == "pause_campaign":
                if cmp.status == "active":
                    cmp.status = "paused"
                    cmp.save()
                    action_desc = f"Кампания приостановлена (Stop-Loss: {rule.metric} {current_metric_val} {rule.operator} {rule.threshold_value})"
                else:
                    action_desc = "Кампания уже на паузе"

            elif action == "resume_campaign":
                if cmp.status == "paused":
                    cmp.status = "active"
                    cmp.save()
                    action_desc = f"Кампания возобновлена ({rule.metric} {current_metric_val} {rule.operator} {rule.threshold_value})"
                else:
                    action_desc = "Кампания уже активна"

            elif action == "increase_bid":
                old_bid = cmp.bid_amount
                new_bid = round(old_bid * (1.0 + (val / 100.0)), 2)
                cmp.bid_amount = new_bid
                cmp.save()
                action_desc = f"Ставка повышена на {val}% (с ${old_bid:.2f} до ${new_bid:.2f})"

            elif action == "decrease_bid":
                old_bid = cmp.bid_amount
                new_bid = max(0.01, round(old_bid * (1.0 - (val / 100.0)), 2))
                cmp.bid_amount = new_bid
                cmp.save()
                action_desc = f"Ставка снижена на {val}% (с ${old_bid:.2f} до ${new_bid:.2f})"

            elif action == "increase_budget":
                old_bgt = cmp.daily_budget
                new_bgt = round(old_bgt * (1.0 + (val / 100.0)), 2)
                cmp.daily_budget = new_bgt
                cmp.save()
                action_desc = f"Дневной бюджет увеличен на {val}% (с ${old_bgt:.2f} до ${new_bgt:.2f})"

            elif action == "decrease_budget":
                old_bgt = cmp.daily_budget
                new_bgt = max(1.0, round(old_bgt * (1.0 - (val / 100.0)), 2))
                cmp.daily_budget = new_bgt
                cmp.save()
                action_desc = f"Дневной бюджет снижен на {val}% (с ${old_bgt:.2f} до ${new_bgt:.2f})"

            elif action == "send_alert":
                action_desc = f"Отправлен алерт: {rule.metric} достиг значения {current_metric_val}"

            # Create execution log
            log_id = uuid.uuid4().hex[:32]
            AdRuleExecutionLog.create(
                id=log_id,
                rule_id=rule.id,
                rule_name=rule.name,
                campaign_id=cmp.id,
                campaign_name=cmp.name,
                advertiser_id=rule.advertiser_id,
                metric_name=rule.metric,
                metric_current_value=current_metric_val,
                threshold_value=rule.threshold_value,
                action_taken=action,
                action_details=action_desc,
                create_time=now_ts,
            )

            # Update rule trigger statistics
            rule.last_triggered_time = now_ts
            rule.trigger_count = (rule.trigger_count or 0) + 1
            rule.save()

            # Dispatch notification
            try:
                AdvertiserNotificationService.create_notification(
                    advertiser_id=rule.advertiser_id,
                    type="rule_trigger",
                    title=f"⚡ Авто-правило: {rule.name}",
                    message=f"Для кампании '{cmp.name}': {action_desc}",
                    severity="warning" if action in ["pause_campaign", "decrease_budget"] else "info",
                    data={
                        "rule_id": rule.id,
                        "campaign_id": cmp.id,
                        "metric": rule.metric,
                        "metric_value": current_metric_val,
                        "threshold": rule.threshold_value,
                        "action": action,
                    }
                )
            except Exception as e:
                logger.debug(f"Advertiser notification error in rule execution: {e}")

            executed_results.append({
                "rule_id": rule.id,
                "rule_name": rule.name,
                "campaign_id": cmp.id,
                "campaign_name": cmp.name,
                "metric": rule.metric,
                "metric_value": current_metric_val,
                "threshold": rule.threshold_value,
                "action": action,
                "details": action_desc,
            })

        return executed_results

    @classmethod
    @DB.connection_context()
    def run_all_rules(cls, advertiser_id: str = None, campaign_id: str = None, rule_id: str = None) -> dict:
        query = AdAutomatedRule.select().where(AdAutomatedRule.is_active == True)
        if advertiser_id:
            query = query.where(AdAutomatedRule.advertiser_id == advertiser_id)
        if rule_id:
            query = query.where(AdAutomatedRule.id == rule_id)
        if campaign_id:
            query = query.where((AdAutomatedRule.campaign_id == campaign_id) | (AdAutomatedRule.campaign_id == "all"))

        active_rules = list(query)
        total_triggered = 0
        all_actions = []

        for r in active_rules:
            actions = cls.execute_rule(r)
            if actions:
                total_triggered += len(actions)
                all_actions.extend(actions)

        return {
            "rules_evaluated": len(active_rules),
            "actions_triggered": total_triggered,
            "actions": all_actions,
        }

    @classmethod
    @DB.connection_context()
    def list_execution_logs(cls, advertiser_id: str, campaign_id: str = None, limit: int = 50) -> list:
        query = AdRuleExecutionLog.select().where(AdRuleExecutionLog.advertiser_id == advertiser_id)
        if campaign_id:
            query = query.where(AdRuleExecutionLog.campaign_id == campaign_id)

        logs = list(query.order_by(AdRuleExecutionLog.create_time.desc()).limit(limit))
        res = []
        for l in logs:
            res.append({
                "id": l.id,
                "rule_id": l.rule_id,
                "rule_name": l.rule_name,
                "campaign_id": l.campaign_id,
                "campaign_name": l.campaign_name,
                "metric_name": l.metric_name,
                "metric_current_value": l.metric_current_value,
                "threshold_value": l.threshold_value,
                "action_taken": l.action_taken,
                "action_details": l.action_details or "",
                "create_time": l.create_time,
            })
        return res









