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
    AdCampaign,
    AdVariant,
    AdImpression,
    AdClick,
    AdConversion,
    AdTransaction,
    AdSettings,
    AdAttributionVisit,
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
    ) -> dict | None:
        """
        Evaluate candidate ad campaigns for an incoming user prompt.
        Applies intent analysis, regional, language & model targeting, status/moderation checks,
        budget & balance verification, and frequency capping before ranking candidates.
        """
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

            # 1. Budget and Balance Gate & Smart Auto-Bidding Calculation
            is_cpa = getattr(cmp, "pricing_model", "cpc") == "cpa"
            target_cpa = float(getattr(cmp, "target_cpa", 0.0) or 0.0)

            if is_cpa or target_cpa > 0:
                # Smart CPA Auto-Bidding Formula: eCPC = Target CPA * max(0.01, Campaign CVR / 100.0)
                raw_cvr = float(getattr(cmp, "conversion_rate", 0.0) or 2.5) / 100.0
                calc_cpa = target_cpa if target_cpa > 0 else float(cmp.bid_amount or 5.0)
                cost_per_event = round(max(0.05, min(calc_cpa * raw_cvr, 5.0)), 2)
            else:
                cost_per_event = float(cmp.bid_amount or 0.10)

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

            # Compute normalized score with language & model bonuses
            lang_bonus = 0.2 if (cmp_langs and effective_lang in cmp_langs) else 0.0
            model_bonus = 0.1 if (cmp_models and any(cm in clean_model for cm in cmp_models)) else 0.0
            relevance_score = min(1.0, (overlap_count / 3.0) + lang_bonus + model_bonus)
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

        # Select active variant (A/B testing with Bandit strategy) or fallback to campaign defaults
        selected_variant, ad_text, landing_url = AdVariantService.select_variant_for_impression(winner_campaign)

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

        now_ts = current_timestamp()
        cost = float(campaign.bid_amount or 0.10) if campaign.pricing_model == "cpc" else 0.0

        # Check deduplication within 1 hour
        one_hour_ago = now_ts - (3600 * 1000)
        recent_click = AdClick.select().where(
            AdClick.campaign_id == campaign.id,
            AdClick.impression_id == impression_id,
            AdClick.create_time >= one_hour_ago,
        ).first()

        variant_obj = None
        if target_variant_id and target_variant_id != "main":
            variant_obj = AdVariant.get_or_none(AdVariant.id == target_variant_id)

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




