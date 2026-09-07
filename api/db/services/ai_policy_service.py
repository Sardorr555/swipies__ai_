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
import uuid
from datetime import datetime, timezone
from peewee import fn

from common.time_utils import current_timestamp
from api.db.db_models import (
    DB,
    AIModel,
    AIProvider,
    SubscriptionAIPolicy,
    SubscriptionPlan,
    Tenant,
    TokenUsageLog,
    User,
    UserTokenLimit,
)
from api.db.services.common_service import CommonService
from api.db.services.global_instance_service import GlobalInstanceService, GLOBAL_INSTANCE_ID
from api.db.services.ai_audit_log_service import AIAuditLogService
from api.utils.key_crypto import encrypt_api_key, decrypt_api_key, mask_api_key

logger = logging.getLogger(__name__)


class SubscriptionPlanService(CommonService):
    model = SubscriptionPlan


class AIModelService(CommonService):
    model = AIModel

    @classmethod
    @DB.connection_context()
    def get_platform_models(cls) -> list[dict]:
        from common.settings import FACTORY_LLM_INFOS
        from common.time_utils import current_timestamp

        # Fetch active providers with valid configured API keys
        active_providers = {
            p.provider_name.lower(): p
            for p in AIProvider.select().where(
                AIProvider.is_global == True,
                AIProvider.status == "active",
                AIProvider.api_key.is_null(False),
                AIProvider.api_key != "",
            )
        }

        # Purge placeholder/garbage models like "open ai models" or "openai models"
        placeholder_models = cls.model.select().where(
            cls.model.is_global == True,
            (cls.model.model_name.contains("open ai models") | 
             cls.model.model_name.contains("openai models") |
             cls.model.model_name.contains("placeholder"))
        )
        for pm in placeholder_models:
            pm.delete_instance()

        now = current_timestamp()

        # For every active provider with an API key, ensure all capabilities are present in AIModel
        for prov_lower, p_obj in active_providers.items():
            prov_name = p_obj.provider_name
            count = cls.model.select().where(
                cls.model.is_global == True,
                cls.model.provider == prov_name,
                cls.model.enabled == True,
            ).count()

            if count == 0:
                fac_entry = next(
                    (f for f in (FACTORY_LLM_INFOS or []) if f.get("name", "").lower() == prov_lower),
                    None,
                )
                if fac_entry and fac_entry.get("llm"):
                    for llm in fac_entry["llm"]:
                        m_name = llm.get("llm_name") or llm.get("name", "")
                        if not m_name:
                            continue
                        raw_types = llm.get("model_type", ["chat"])
                        m_types = raw_types if isinstance(raw_types, list) else [raw_types]
                        max_tok = llm.get("max_tokens", 8192) or 8192

                        for mt in m_types:
                            norm_type = str(mt).upper()
                            if "EMBED" in norm_type:
                                norm_type = "EMBEDDING"
                            elif "RERANK" in norm_type or "RE-RANK" in norm_type:
                                norm_type = "RERANK"
                            elif "IMAGE2TEXT" in norm_type or "VISION" in norm_type:
                                norm_type = "IMAGE2TEXT"
                            elif "SPEECH2TEXT" in norm_type or "ASR" in norm_type or "AUDIO" in norm_type:
                                norm_type = "SPEECH2TEXT"
                            elif "TTS" in norm_type or "TEXT2SPEECH" in norm_type:
                                norm_type = "TTS"
                            else:
                                norm_type = "CHAT"

                            m_id = f"{prov_lower}/{m_name}" if norm_type == "CHAT" else f"{prov_lower}/{m_name}_{norm_type.lower()}"

                            if not cls.model.select().where(cls.model.id == m_id).count():
                                cls.model.create(
                                    id=m_id,
                                    provider=prov_name,
                                    model_name=m_name,
                                    model_type=norm_type,
                                    base_url=p_obj.base_url or "",
                                    api_key=p_obj.api_key or "",
                                    max_tokens=max_tok,
                                    input_token_price=0.0,
                                    output_token_price=0.0,
                                    enabled=True,
                                    is_global=True,
                                    is_custom=False,
                                    global_instance_id=GLOBAL_INSTANCE_ID,
                                    status="active",
                                    create_time=now,
                                    update_time=now,
                                )

        models = list(cls.model.select().where(cls.model.is_global == True, cls.model.enabled == True))
        res = []
        for m in models:
            prov_key = (m.provider or "").lower()
            # Only include models that have a direct key or whose provider is authenticated
            if prov_key in active_providers or (m.api_key and len(m.api_key.strip()) > 0):
                md = m.to_dict()
                prov_obj = active_providers.get(prov_key)
                effective_key = m.api_key or (prov_obj.api_key if prov_obj else "")
                md["api_key_masked"] = mask_api_key(effective_key)
                del md["api_key"]
                res.append(md)
        return res

    @classmethod
    @DB.connection_context()
    def get_user_byok_models(cls, user_id: str) -> list[dict]:
        models = list(cls.model.select().where(cls.model.owner_user_id == user_id, cls.model.is_custom == True))
        res = []
        for m in models:
            md = m.to_dict()
            md["api_key_masked"] = mask_api_key(m.api_key)
            del md["api_key"]
            res.append(md)
        return res


class SubscriptionAIPolicyService(CommonService):
    model = SubscriptionAIPolicy


class UserTokenLimitService(CommonService):
    model = UserTokenLimit


class TokenUsageLogService(CommonService):
    model = TokenUsageLog


class AIPolicyManager:
    """
    Central Manager for the RAGFlow Single Global Instance:
    - Global subscription policy resolution
    - Central rate limiting and token accounting
    - PRO BYOK model authorization and lifecycle
    - Global model resolution and provider fallback
    - Cost analytics
    """

    @classmethod
    def get_current_period(cls) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m")

    @classmethod
    def get_current_date_str(cls) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    @classmethod
    @DB.connection_context()
    def init_default_data(cls):
        """Seed Global Instance, default plans, platform models, and policies."""
        try:
            # 1. Initialize Single Global Instance
            GlobalInstanceService.get_global_instance()

            # 2. Default Plans (FREE / PLUS / PRO)
            default_plans = [
                {
                    "id": "free",
                    "name": "FREE",
                    "daily_token_limit": 50000,
                    "monthly_token_limit": 1000000,
                    "daily_request_limit": 500,
                    "monthly_request_limit": 10000,
                    "requests_per_minute": 60,
                    "max_tokens_per_request": 4096,
                    "limit_mode": "shared",
                    "max_storage_gb": 1.0,
                    "max_datasets": 2,
                    "max_agents": 2,
                    "allow_custom_providers": False,
                    "allow_custom_models": False,
                    "allow_custom_endpoints": False,
                    "allow_private_servers": False,
                    "allow_byok": False,
                    "max_byok_models": 0,
                    "default_llm_id": "openai/gpt-4o-mini",
                    "default_embd_id": "openai/text-embedding-3-small",
                    "default_rerank_id": "BAAI/bge-reranker-v2-m3",
                    "status": "1",
                },
                {
                    "id": "plus",
                    "name": "PLUS",
                    "daily_token_limit": 500000,
                    "monthly_token_limit": 10000000,
                    "daily_request_limit": 5000,
                    "monthly_request_limit": 100000,
                    "requests_per_minute": 120,
                    "max_tokens_per_request": 8192,
                    "limit_mode": "shared",
                    "max_storage_gb": 10.0,
                    "max_datasets": 10,
                    "max_agents": 10,
                    "allow_custom_providers": False,
                    "allow_custom_models": False,
                    "allow_custom_endpoints": False,
                    "allow_private_servers": False,
                    "allow_byok": False,
                    "max_byok_models": 0,
                    "default_llm_id": "openai/gpt-4o",
                    "default_embd_id": "openai/text-embedding-3-small",
                    "default_rerank_id": "BAAI/bge-reranker-v2-m3",
                    "status": "1",
                },
                {
                    "id": "pro",
                    "name": "PRO",
                    "daily_token_limit": 2000000,
                    "monthly_token_limit": 50000000,
                    "daily_request_limit": 20000,
                    "monthly_request_limit": 500000,
                    "requests_per_minute": 300,
                    "max_tokens_per_request": 16384,
                    "limit_mode": "per_model",
                    "max_storage_gb": 50.0,
                    "max_datasets": 50,
                    "max_agents": 50,
                    "allow_custom_providers": True,
                    "allow_custom_models": True,
                    "allow_custom_endpoints": True,
                    "allow_private_servers": True,
                    "allow_byok": True,
                    "max_byok_models": 10,
                    "default_llm_id": None,
                    "default_embd_id": None,
                    "default_rerank_id": None,
                    "status": "1",
                },
            ]

            for plan in default_plans:
                if not SubscriptionPlanService.query(id=plan["id"]):
                    SubscriptionPlanService.save(**plan)

            # 3. Default Global Providers
            default_providers = [
                {"id": "global_openai", "provider_name": "OpenAI", "base_url": "https://api.openai.com/v1", "status": "active"},
                {"id": "global_anthropic", "provider_name": "Anthropic", "base_url": "https://api.anthropic.com/v1", "status": "active"},
                {"id": "global_deepseek", "provider_name": "DeepSeek", "base_url": "https://api.deepseek.com/v1", "status": "active"},
                {"id": "global_gemini", "provider_name": "Gemini", "base_url": "https://generativelanguage.googleapis.com", "status": "active"},
            ]
            for p in default_providers:
                if not AIProvider.select().where(AIProvider.id == p["id"]).count():
                    AIProvider.create(
                        id=p["id"],
                        provider_name=p["provider_name"],
                        base_url=p["base_url"],
                        status=p["status"],
                        is_global=True,
                        global_instance_id=GLOBAL_INSTANCE_ID,
                        create_time=current_timestamp(),
                    )

            # Clean up dummy models that have no API key and no provider key
            active_provider_names = {
                p.provider_name.lower()
                for p in AIProvider.select().where(
                    AIProvider.is_global == True,
                    AIProvider.api_key.is_null(False),
                    AIProvider.api_key != ""
                )
            }
            dummy_models = AIModel.select().where(
                AIModel.is_global == True,
                (AIModel.api_key.is_null(True) | (AIModel.api_key == "")),
            )
            for dm in dummy_models:
                if (dm.provider or "").lower() not in active_provider_names:
                    dm.delete_instance()

            logger.info("Successfully initialized Global Instance AI infrastructure.")
        except Exception as e:
            logger.exception("AIPolicyManager.init_default_data failed: %s", e)

    @classmethod
    @DB.connection_context()
    def get_user_plan(cls, tenant_id: str, user_id: str = None) -> dict:
        """Resolve subscription plan for tenant or user (fallback to FREE)."""
        plan_type = "free"
        try:
            target_id = user_id or tenant_id
            if target_id:
                user = User.get_or_none(User.id == target_id)
                if user and getattr(user, "is_superuser", False):
                    # Superuser enjoys unrestricted Pro capabilities
                    pro_plan = SubscriptionPlanService.query(id="pro")
                    if pro_plan:
                        return pro_plan[0].to_dict()

            if tenant_id:
                tenant = Tenant.get_or_none(Tenant.id == tenant_id)
                if tenant and getattr(tenant, "plan_type", None):
                    plan_type = tenant.plan_type.lower()
        except Exception as e:
            logger.warning("Error fetching tenant plan: %s", e)

        plans = SubscriptionPlanService.query(id=plan_type)
        if plans:
            return plans[0].to_dict()

        # Fallback to default free plan
        return {
            "id": "free",
            "name": "FREE",
            "daily_token_limit": 50000,
            "monthly_token_limit": 1000000,
            "daily_request_limit": 500,
            "monthly_request_limit": 10000,
            "requests_per_minute": 60,
            "max_tokens_per_request": 4096,
            "allow_byok": False,
            "max_byok_models": 0,
            "default_llm_id": "openai/gpt-4o-mini",
            "default_embd_id": "openai/text-embedding-3-small",
            "default_rerank_id": "BAAI/bge-reranker-v2-m3",
        }

    @classmethod
    @DB.connection_context()
    def get_tenant_total_tokens_used(cls, tenant_id: str, period: str = None) -> int:
        if not period:
            period = cls.get_current_period()
        res = (
            TokenUsageLog.select(fn.SUM(TokenUsageLog.total_tokens))
            .where(TokenUsageLog.tenant_id == tenant_id, TokenUsageLog.billing_period == period)
            .scalar()
        )
        return int(res or 0)

    @classmethod
    @DB.connection_context()
    def get_tenant_daily_tokens_used(cls, tenant_id: str, date_str: str = None) -> int:
        if not date_str:
            date_str = cls.get_current_date_str()
        res = (
            TokenUsageLog.select(fn.SUM(TokenUsageLog.total_tokens))
            .where(TokenUsageLog.tenant_id == tenant_id, TokenUsageLog.date_str == date_str)
            .scalar()
        )
        return int(res or 0)

    @classmethod
    @DB.connection_context()
    def get_tenant_daily_requests_used(cls, tenant_id: str, date_str: str = None) -> int:
        if not date_str:
            date_str = cls.get_current_date_str()
        return TokenUsageLog.select().where(TokenUsageLog.tenant_id == tenant_id, TokenUsageLog.date_str == date_str).count()

    @classmethod
    @DB.connection_context()
    def get_tenant_monthly_requests_used(cls, tenant_id: str, period: str = None) -> int:
        if not period:
            period = cls.get_current_period()
        return TokenUsageLog.select().where(TokenUsageLog.tenant_id == tenant_id, TokenUsageLog.billing_period == period).count()

    @classmethod
    @DB.connection_context()
    def get_tenant_model_tokens_used(cls, tenant_id: str, model_id: str, period: str = None) -> int:
        if not period:
            period = cls.get_current_period()

        from api.db.services.tenant_llm_service import TenantLLMService
        mdl_name, fid = TenantLLMService.split_model_name_and_factory(model_id)
        res = (
            TokenUsageLog.select(fn.SUM(TokenUsageLog.total_tokens))
            .where(
                TokenUsageLog.tenant_id == tenant_id,
                TokenUsageLog.billing_period == period,
                (TokenUsageLog.model_id == model_id) | (TokenUsageLog.model_id == mdl_name),
            )
            .scalar()
        )
        return int(res or 0)

    @classmethod
    @DB.connection_context()
    def check_model_access(
        cls,
        tenant_id: str,
        model_name: str,
        model_type: str = None,
        user_id: str = None,
    ) -> tuple[bool, str, int]:
        """
        Validate model access based on single Global Instance subscription policy and token quotas.
        Returns: (allowed: bool, message: str, status_code: int)
        """
        if not tenant_id:
            return True, "OK", 200

        target_user_id = user_id or tenant_id
        is_super = False
        if target_user_id:
            u = User.get_or_none(User.id == target_user_id)
            is_super = bool(u and getattr(u, "is_superuser", False))

        plan = cls.get_user_plan(tenant_id, target_user_id)
        plan_id = plan["id"].lower()
        monthly_token_limit = plan.get("monthly_token_limit", 1000000)
        daily_token_limit = plan.get("daily_token_limit", 50000)
        daily_request_limit = plan.get("daily_request_limit", 500)
        monthly_request_limit = plan.get("monthly_request_limit", 10000)

        # Check user-specific limit override if configured
        if target_user_id:
            user_limits = UserTokenLimitService.query(user_id=target_user_id, enabled=True)
            if user_limits and user_limits[0].monthly_token_limit > 0:
                monthly_token_limit = user_limits[0].monthly_token_limit

        if not is_super:
            # 1. Total monthly token quota check
            monthly_used = cls.get_tenant_total_tokens_used(tenant_id)
            if monthly_token_limit > 0 and monthly_used >= monthly_token_limit:
                msg = f"Monthly AI token limit reached ({monthly_used:,} / {monthly_token_limit:,}). Upgrade to PLUS or PRO to continue using AI."
                return False, msg, 429

            # 2. Daily token quota check
            daily_used = cls.get_tenant_daily_tokens_used(tenant_id)
            if daily_token_limit > 0 and daily_used >= daily_token_limit:
                msg = f"Daily AI token limit reached ({daily_used:,} / {daily_token_limit:,}). Upgrade your plan to increase limits."
                return False, msg, 429

            # 3. Daily request quota check
            daily_req_count = cls.get_tenant_daily_requests_used(tenant_id)
            if daily_request_limit > 0 and daily_req_count >= daily_request_limit:
                msg = f"Daily AI request limit reached ({daily_req_count:,} / {daily_request_limit:,})."
                return False, msg, 429

        # Normalize model identifiers
        from api.db.services.tenant_llm_service import TenantLLMService
        pure_name, fid = TenantLLMService.split_model_name_and_factory(model_name)
        candidate_ids = [model_name, pure_name]
        if fid:
            candidate_ids.extend([f"{fid}/{pure_name}", f"{pure_name}@{fid}", f"{fid}/{model_name}"])

        # Check if requested model is a user-owned BYOK model
        byok_model = None
        for cid in candidate_ids:
            found_byok = AIModel.get_or_none(AIModel.id == cid, AIModel.is_custom == True)
            if found_byok:
                byok_model = found_byok
                break
        if not byok_model:
            byok_model = AIModel.get_or_none(AIModel.model_name == pure_name, AIModel.is_custom == True)

        if byok_model:
            # Enforce BYOK access rules
            if not is_super:
                if not plan.get("allow_byok", False) and plan_id not in ["pro", "enterprise"]:
                    return False, "BYOK_NOT_AVAILABLE: Connect Your Own AI is available only with the PRO subscription.", 403

                # Ownership check
                if byok_model.owner_user_id and byok_model.owner_user_id != target_user_id and byok_model.owner_tenant_id != tenant_id:
                    return False, "Access denied: This custom AI model belongs to another account.", 403

                # Status check (e.g. locked after downgrade)
                if byok_model.status == "locked_pro_required":
                    return False, "LOCKED_PRO_REQUIRED: This custom AI model is locked because your PRO subscription expired. Upgrade to PRO to reactivate.", 403
                if not byok_model.enabled or byok_model.status != "active":
                    return False, f"Custom AI Model '{byok_model.model_name}' is currently disabled.", 403

            return True, "OK", 200

        # Platform Model Check
        ai_model = None
        for cid in candidate_ids:
            models = AIModelService.query(id=cid, is_global=True)
            if models:
                ai_model = models[0]
                break

        if not ai_model:
            models = AIModelService.query(model_name=pure_name, is_global=True)
            if models:
                ai_model = models[0]

        if ai_model and not ai_model.enabled:
            return False, f"Model '{model_name}' is currently disabled by administrator.", 403

        # Always allow system default models configured by admin
        try:
            from api.db.services.global_instance_service import GlobalInstanceService
            g_inst = GlobalInstanceService.get_instance_stats()
            system_default_models = {
                g_inst.get("default_chat_model"),
                g_inst.get("default_free_model_id"),
                g_inst.get("default_plus_model_id"),
                g_inst.get("default_pro_model_id"),
                g_inst.get("default_embd_id"),
                g_inst.get("default_rerank_id"),
                g_inst.get("default_image2text_model"),
                g_inst.get("default_asr_model"),
                g_inst.get("default_tts_model"),
            }
            system_default_models.discard(None)
            system_default_models.discard("")
            if any(cid in system_default_models for cid in candidate_ids) or pure_name in system_default_models:
                return True, "OK", 200
        except Exception:
            pass

        # Subscription policy check for platform model
        policy = None
        if ai_model:
            policies = SubscriptionAIPolicyService.query(plan_id=plan_id, model_id=ai_model.id)
            if policies:
                policy = policies[0]

        if not policy:
            for cid in candidate_ids:
                policies = SubscriptionAIPolicyService.query(plan_id=plan_id, model_id=cid)
                if policies:
                    policy = policies[0]
                    break

        if policy is not None:
            if not policy.enabled and not is_super:
                return False, f"Model '{model_name}' is not authorized for your {plan['name']} subscription plan.", 403
        else:
            if ai_model and ai_model.allowed_plans:
                try:
                    allowed_plans = ai_model.allowed_plans if isinstance(ai_model.allowed_plans, list) else json.loads(ai_model.allowed_plans)
                    if plan_id not in [p.lower() for p in allowed_plans] and not is_super:
                        return False, f"Model '{model_name}' is not included in your {plan['name']} subscription plan.", 403
                except Exception:
                    pass

        # Per-model token cap check
        if policy and policy.model_token_limit > 0 and not is_super:
            used_for_model = cls.get_tenant_model_tokens_used(tenant_id, policy.model_id)
            if used_for_model >= policy.model_token_limit:
                msg = f"Monthly token limit reached for model '{pure_name}' ({used_for_model:,} / {policy.model_token_limit:,})."
                return False, msg, 429

        return True, "OK", 200

    @classmethod
    @DB.connection_context()
    def can_add_custom_model(cls, tenant_id_or_user_id: str) -> tuple[bool, str]:
        """Server-side check: only PRO users (or superuser) can configure custom BYOK models."""
        if not tenant_id_or_user_id:
            return False, "Authentication required."
        user = User.get_or_none(User.id == tenant_id_or_user_id)
        if user and getattr(user, "is_superuser", False):
            return True, "OK"

        plan = cls.get_user_plan(tenant_id_or_user_id)
        plan_id = (plan.get("id") or "").lower()
        if plan_id not in ["pro", "enterprise"] and not plan.get("allow_byok", False):
            return False, "Connect Your Own AI is available only with the PRO subscription."

        # Check max custom models limit
        max_models = plan.get("max_byok_models", 10)
        current_count = AIModel.select().where(AIModel.owner_user_id == tenant_id_or_user_id, AIModel.is_custom == True).count()
        if current_count >= max_models:
            return False, f"Maximum custom AI models reached ({current_count}/{max_models})."

        return True, "OK"

    @classmethod
    @DB.connection_context()
    def handle_subscription_downgrade(cls, user_id: str, new_plan_id: str):
        """
        When a user downgrades from PRO -> PLUS or FREE:
        BYOK models are NOT deleted, but locked to status 'locked_pro_required'.
        """
        if new_plan_id.lower() in ["pro", "enterprise"]:
            return
        updated = (
            AIModel.update(status="locked_pro_required")
            .where(AIModel.owner_user_id == user_id, AIModel.is_custom == True)
            .execute()
        )
        logger.info("Locked %d BYOK models for downgraded user %s", updated, user_id)

    @classmethod
    @DB.connection_context()
    def handle_subscription_upgrade(cls, user_id: str, new_plan_id: str):
        """When a user upgrades back to PRO: reactivates locked BYOK models."""
        if new_plan_id.lower() in ["pro", "enterprise"]:
            updated = (
                AIModel.update(status="active")
                .where(AIModel.owner_user_id == user_id, AIModel.is_custom == True, AIModel.status == "locked_pro_required")
                .execute()
            )
            logger.info("Reactivated %d BYOK models for upgraded PRO user %s", updated, user_id)

    @classmethod
    @DB.connection_context()
    def record_token_usage(
        cls,
        tenant_id: str,
        user_id: str,
        model_id: str,
        model_type: str,
        input_tokens: int,
        output_tokens: int,
        total_tokens: int,
        status: str = "SUCCESS",
        provider_id: str = None,
    ):
        """
        Central token accounting:
        - Calculates estimated dollar cost from model pricing
        - Stores usage log tied to GLOBAL_INSTANCE_ID
        """
        if not total_tokens and not input_tokens and not output_tokens:
            return

        total_tokens = total_tokens or ((input_tokens or 0) + (output_tokens or 0))
        period = cls.get_current_period()
        date_str = cls.get_current_date_str()
        plan = cls.get_user_plan(tenant_id, user_id)

        # Lookup pricing
        input_price = 0.0
        output_price = 0.0
        resolved_provider = provider_id
        try:
            m = AIModel.get_or_none((AIModel.id == model_id) | (AIModel.model_name == model_id))
            if m:
                input_price = m.input_token_price or 0.0
                output_price = m.output_token_price or 0.0
                if not resolved_provider:
                    resolved_provider = m.provider
        except Exception:
            pass

        estimated_cost = round(
            ((input_tokens or 0) * input_price + (output_tokens or 0) * output_price) / 1000000.0,
            6,
        )

        try:
            record_id = uuid.uuid4().hex
            TokenUsageLogService.save(
                id=record_id,
                user_id=user_id or tenant_id,
                tenant_id=tenant_id,
                subscription_id=plan["id"],
                global_instance_id=GLOBAL_INSTANCE_ID,
                model_id=model_id or "unknown",
                provider_id=resolved_provider or "unknown",
                model_type=model_type or "CHAT",
                input_tokens=input_tokens or 0,
                output_tokens=output_tokens or 0,
                total_tokens=total_tokens,
                estimated_cost=estimated_cost,
                status=status,
                billing_period=period,
                date_str=date_str,
                create_time=current_timestamp(),
            )
        except Exception as e:
            logger.exception("AIPolicyManager.record_token_usage error: %s", e)

    @classmethod
    @DB.connection_context()
    def get_user_usage_summary(cls, tenant_id: str, user_id: str = None) -> dict:
        """Returns the user's personal usage statistics and quota progress."""
        period = cls.get_current_period()
        date_str = cls.get_current_date_str()
        plan = cls.get_user_plan(tenant_id, user_id)
        if not isinstance(plan, dict):
            plan = {"id": "free", "name": "FREE"}
        if not plan.get("name"):
            plan["name"] = str(plan.get("id", "free")).upper()

        monthly_limit = plan.get("monthly_token_limit", 1000000)
        daily_limit = plan.get("daily_token_limit", 50000)

        if user_id:
            user_limits = UserTokenLimitService.query(user_id=user_id, enabled=True)
            if user_limits and user_limits[0].monthly_token_limit > 0:
                monthly_limit = user_limits[0].monthly_token_limit

        monthly_used = cls.get_tenant_total_tokens_used(tenant_id, period)
        daily_used = cls.get_tenant_daily_tokens_used(tenant_id, date_str)
        percentage = round((monthly_used / monthly_limit) * 100, 1) if monthly_limit > 0 else 0

        # Model breakdown for current billing period
        breakdown_query = (
            TokenUsageLog.select(
                TokenUsageLog.model_id,
                TokenUsageLog.model_type,
                fn.SUM(TokenUsageLog.total_tokens).alias("tokens_used"),
                fn.SUM(TokenUsageLog.estimated_cost).alias("cost"),
            )
            .where(TokenUsageLog.tenant_id == tenant_id, TokenUsageLog.billing_period == period)
            .group_by(TokenUsageLog.model_id, TokenUsageLog.model_type)
            .dicts()
        )
        breakdown = list(breakdown_query)

        # Allowed models list
        plan_id = plan.get("id", "free")
        policies = (
            SubscriptionAIPolicy.select(
                SubscriptionAIPolicy.model_id,
                SubscriptionAIPolicy.model_token_limit,
                SubscriptionAIPolicy.is_default_llm,
                SubscriptionAIPolicy.enabled,
            )
            .where(SubscriptionAIPolicy.plan_id == plan_id, SubscriptionAIPolicy.enabled == True)
            .dicts()
        )

        return {
            "plan": plan,
            "period": period,
            "date": date_str,
            "monthly_used": monthly_used,
            "total_used": monthly_used,
            "monthly_limit": monthly_limit,
            "daily_used": daily_used,
            "daily_limit": daily_limit,
            "percentage": percentage,
            "breakdown": breakdown,
            "allowed_models": list(policies),
            "global_instance_id": GLOBAL_INSTANCE_ID,
        }

    @classmethod
    @DB.connection_context()
    def get_admin_analytics(cls, period: str = None) -> dict:
        """
        Calculates platform-wide AI usage, cost, and breakdown across subscriptions,
        models, providers, and users for the single Global Instance.
        """
        if not period:
            period = cls.get_current_period()

        # Overall summary
        summary_query = (
            TokenUsageLog.select(
                fn.COUNT(TokenUsageLog.id).alias("total_requests"),
                fn.SUM(TokenUsageLog.input_tokens).alias("total_input_tokens"),
                fn.SUM(TokenUsageLog.output_tokens).alias("total_output_tokens"),
                fn.SUM(TokenUsageLog.total_tokens).alias("total_tokens"),
                fn.SUM(TokenUsageLog.estimated_cost).alias("total_cost"),
                fn.COUNT(fn.DISTINCT(TokenUsageLog.user_id)).alias("active_users"),
            )
            .where(TokenUsageLog.billing_period == period)
            .dicts()
        )
        summary = summary_query[0] if summary_query else {}

        # Breakdown by Subscription (FREE, PLUS, PRO)
        by_plan = list(
            TokenUsageLog.select(
                TokenUsageLog.subscription_id,
                fn.COUNT(TokenUsageLog.id).alias("requests"),
                fn.SUM(TokenUsageLog.total_tokens).alias("tokens"),
                fn.SUM(TokenUsageLog.estimated_cost).alias("cost"),
            )
            .where(TokenUsageLog.billing_period == period)
            .group_by(TokenUsageLog.subscription_id)
            .dicts()
        )

        # Breakdown by Model
        by_model = list(
            TokenUsageLog.select(
                TokenUsageLog.model_id,
                TokenUsageLog.model_type,
                fn.COUNT(TokenUsageLog.id).alias("requests"),
                fn.SUM(TokenUsageLog.input_tokens).alias("input_tokens"),
                fn.SUM(TokenUsageLog.output_tokens).alias("output_tokens"),
                fn.SUM(TokenUsageLog.total_tokens).alias("total_tokens"),
                fn.SUM(TokenUsageLog.estimated_cost).alias("cost"),
            )
            .where(TokenUsageLog.billing_period == period)
            .group_by(TokenUsageLog.model_id, TokenUsageLog.model_type)
            .order_by(fn.SUM(TokenUsageLog.total_tokens).desc())
            .limit(20)
            .dicts()
        )

        # Breakdown by Provider
        by_provider = list(
            TokenUsageLog.select(
                TokenUsageLog.provider_id,
                fn.COUNT(TokenUsageLog.id).alias("requests"),
                fn.SUM(TokenUsageLog.total_tokens).alias("tokens"),
                fn.SUM(TokenUsageLog.estimated_cost).alias("cost"),
            )
            .where(TokenUsageLog.billing_period == period)
            .group_by(TokenUsageLog.provider_id)
            .dicts()
        )

        # Top Users by Consumption
        top_users_query = list(
            TokenUsageLog.select(
                TokenUsageLog.user_id,
                TokenUsageLog.subscription_id,
                fn.COUNT(TokenUsageLog.id).alias("requests"),
                fn.SUM(TokenUsageLog.total_tokens).alias("tokens"),
                fn.SUM(TokenUsageLog.estimated_cost).alias("cost"),
            )
            .where(TokenUsageLog.billing_period == period)
            .group_by(TokenUsageLog.user_id, TokenUsageLog.subscription_id)
            .order_by(fn.SUM(TokenUsageLog.total_tokens).desc())
            .limit(20)
            .dicts()
        )

        # Join user details for top users
        uids = [u["user_id"] for u in top_users_query if u.get("user_id")]
        user_info_map = {}
        if uids:
            for usr in User.select(User.id, User.email, User.nickname).where(User.id.in_(uids)):
                user_info_map[usr.id] = {"email": usr.email, "nickname": usr.nickname}

        for u in top_users_query:
            info = user_info_map.get(u["user_id"], {"email": u["user_id"], "nickname": u["user_id"]})
            u["email"] = info["email"]
            u["nickname"] = info["nickname"]

        # BYOK Stats
        byok_count = AIModel.select().where(AIModel.is_custom == True).count()
        byok_active = AIModel.select().where(AIModel.is_custom == True, AIModel.status == "active").count()

        return {
            "period": period,
            "global_instance_id": GLOBAL_INSTANCE_ID,
            "summary": {
                "total_requests": int(summary.get("total_requests") or 0),
                "total_input_tokens": int(summary.get("total_input_tokens") or 0),
                "total_output_tokens": int(summary.get("total_output_tokens") or 0),
                "total_tokens": int(summary.get("total_tokens") or 0),
                "total_cost": round(float(summary.get("total_cost") or 0.0), 4),
                "active_users": int(summary.get("active_users") or 0),
            },
            "by_subscription": by_plan,
            "by_model": by_model,
            "by_provider": by_provider,
            "top_users": top_users_query,
            "byok_stats": {
                "total_byok_models": byok_count,
                "active_byok_models": byok_active,
            },
        }
