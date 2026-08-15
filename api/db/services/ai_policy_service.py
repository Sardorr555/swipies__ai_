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
from datetime import datetime

from peewee import fn

from api.db.db_models import (
    DB,
    AIModel,
    SubscriptionAIPolicy,
    SubscriptionPlan,
    Tenant,
    TokenUsageLog,
    UserTokenLimit,
)
from api.db.services.common_service import CommonService
from api.db.services.tenant_llm_service import TenantLLMService
from api.db.services.user_service import TenantService, UserService
from common.time_utils import current_timestamp


class SubscriptionPlanService(CommonService):
    model = SubscriptionPlan


class AIModelService(CommonService):
    model = AIModel


class SubscriptionAIPolicyService(CommonService):
    model = SubscriptionAIPolicy


class UserTokenLimitService(CommonService):
    model = UserTokenLimit


class TokenUsageLogService(CommonService):
    model = TokenUsageLog


class AIPolicyManager:
    @staticmethod
    def get_current_period() -> str:
        return datetime.now().strftime("%Y-%m")

    @classmethod
    @DB.connection_context()
    def init_default_data(cls):
        """Seed default plans, global models, and policies if they do not exist."""
        try:
            # 1. Default Plans
            default_plans = [
                {
                    "id": "free",
                    "name": "FREE",
                    "monthly_token_limit": 100000,
                    "limit_mode": "shared",
                    "max_storage_gb": 1.0,
                    "max_datasets": 2,
                    "max_agents": 2,
                    "allow_custom_providers": False,
                    "allow_custom_models": False,
                    "allow_custom_endpoints": False,
                    "allow_private_servers": False,
                    "default_llm_id": "openai/gpt-4o-mini",
                    "default_embd_id": "openai/text-embedding-3-small",
                    "status": "1",
                },
                {
                    "id": "plus",
                    "name": "PLUS",
                    "monthly_token_limit": 1000000,
                    "limit_mode": "shared",
                    "max_storage_gb": 10.0,
                    "max_datasets": 10,
                    "max_agents": 10,
                    "allow_custom_providers": False,
                    "allow_custom_models": False,
                    "allow_custom_endpoints": False,
                    "allow_private_servers": False,
                    "default_llm_id": "deepseek/deepseek-chat",
                    "default_embd_id": "openai/text-embedding-3-small",
                    "status": "1",
                },
                {
                    "id": "pro",
                    "name": "PRO",
                    "monthly_token_limit": 5000000,
                    "limit_mode": "per_model",
                    "max_storage_gb": 50.0,
                    "max_datasets": 50,
                    "max_agents": 50,
                    "allow_custom_providers": True,
                    "allow_custom_models": True,
                    "allow_custom_endpoints": True,
                    "allow_private_servers": True,
                    "default_llm_id": "deepseek/deepseek-chat",
                    "default_embd_id": "openai/text-embedding-3-large",
                    "status": "1",
                },
            ]

            for plan in default_plans:
                if not SubscriptionPlanService.query(id=plan["id"]):
                    SubscriptionPlanService.save(**plan)

            # 2. Default Global Models
            default_models = [
                {
                    "id": "openai/gpt-4o",
                    "provider": "OpenAI",
                    "model_name": "gpt-4o",
                    "model_type": "CHAT",
                    "base_url": "https://api.openai.com/v1",
                    "enabled": True,
                    "is_global": True,
                    "is_custom": False,
                },
                {
                    "id": "openai/gpt-4o-mini",
                    "provider": "OpenAI",
                    "model_name": "gpt-4o-mini",
                    "model_type": "CHAT",
                    "base_url": "https://api.openai.com/v1",
                    "enabled": True,
                    "is_global": True,
                    "is_custom": False,
                },
                {
                    "id": "deepseek/deepseek-chat",
                    "provider": "DeepSeek",
                    "model_name": "deepseek-chat",
                    "model_type": "CHAT",
                    "base_url": "https://api.deepseek.com/v1",
                    "enabled": True,
                    "is_global": True,
                    "is_custom": False,
                },
                {
                    "id": "deepseek/deepseek-reasoner",
                    "provider": "DeepSeek",
                    "model_name": "deepseek-reasoner",
                    "model_type": "CHAT",
                    "base_url": "https://api.deepseek.com/v1",
                    "enabled": True,
                    "is_global": True,
                    "is_custom": False,
                },
                {
                    "id": "anthropic/claude-3-5-sonnet",
                    "provider": "Anthropic",
                    "model_name": "claude-3-5-sonnet-20241022",
                    "model_type": "CHAT",
                    "base_url": "https://api.anthropic.com/v1",
                    "enabled": True,
                    "is_global": True,
                    "is_custom": False,
                },
                {
                    "id": "anthropic/claude-3-5-haiku",
                    "provider": "Anthropic",
                    "model_name": "claude-3-5-haiku-20241022",
                    "model_type": "CHAT",
                    "base_url": "https://api.anthropic.com/v1",
                    "enabled": True,
                    "is_global": True,
                    "is_custom": False,
                },
                {
                    "id": "openai/text-embedding-3-small",
                    "provider": "OpenAI",
                    "model_name": "text-embedding-3-small",
                    "model_type": "EMBEDDING",
                    "base_url": "https://api.openai.com/v1",
                    "enabled": True,
                    "is_global": True,
                    "is_custom": False,
                },
                {
                    "id": "openai/text-embedding-3-large",
                    "provider": "OpenAI",
                    "model_name": "text-embedding-3-large",
                    "model_type": "EMBEDDING",
                    "base_url": "https://api.openai.com/v1",
                    "enabled": True,
                    "is_global": True,
                    "is_custom": False,
                },
                {
                    "id": "BAAI/bge-large-en-v1.5",
                    "provider": "BAAI",
                    "model_name": "bge-large-en-v1.5",
                    "model_type": "EMBEDDING",
                    "base_url": "",
                    "enabled": True,
                    "is_global": True,
                    "is_custom": False,
                },
                {
                    "id": "BAAI/bge-reranker-v2-m3",
                    "provider": "BAAI",
                    "model_name": "bge-reranker-v2-m3",
                    "model_type": "RERANK",
                    "base_url": "",
                    "enabled": True,
                    "is_global": True,
                    "is_custom": False,
                },
            ]

            for m in default_models:
                if not AIModelService.query(id=m["id"]):
                    AIModelService.save(**m)

            # 3. Default Plan Policies (Model availability & caps)
            default_policies = [
                # FREE
                {"plan_id": "free", "model_id": "openai/gpt-4o-mini", "model_token_limit": 50000, "enabled": True},
                {"plan_id": "free", "model_id": "openai/text-embedding-3-small", "model_token_limit": 50000, "enabled": True},
                {"plan_id": "free", "model_id": "BAAI/bge-large-en-v1.5", "model_token_limit": 0, "enabled": True},
                {"plan_id": "free", "model_id": "BAAI/bge-reranker-v2-m3", "model_token_limit": 0, "enabled": True},
                # PLUS
                {"plan_id": "plus", "model_id": "openai/gpt-4o-mini", "model_token_limit": 300000, "enabled": True},
                {"plan_id": "plus", "model_id": "deepseek/deepseek-chat", "model_token_limit": 700000, "enabled": True},
                {"plan_id": "plus", "model_id": "openai/text-embedding-3-small", "model_token_limit": 0, "enabled": True},
                {"plan_id": "plus", "model_id": "BAAI/bge-large-en-v1.5", "model_token_limit": 0, "enabled": True},
                {"plan_id": "plus", "model_id": "BAAI/bge-reranker-v2-m3", "model_token_limit": 0, "enabled": True},
                # PRO
                {"plan_id": "pro", "model_id": "openai/gpt-4o", "model_token_limit": 1000000, "enabled": True},
                {"plan_id": "pro", "model_id": "openai/gpt-4o-mini", "model_token_limit": 1000000, "enabled": True},
                {"plan_id": "pro", "model_id": "deepseek/deepseek-chat", "model_token_limit": 2000000, "enabled": True},
                {"plan_id": "pro", "model_id": "deepseek/deepseek-reasoner", "model_token_limit": 1000000, "enabled": True},
                {"plan_id": "pro", "model_id": "openai/text-embedding-3-small", "model_token_limit": 0, "enabled": True},
                {"plan_id": "pro", "model_id": "openai/text-embedding-3-large", "model_token_limit": 0, "enabled": True},
                {"plan_id": "pro", "model_id": "BAAI/bge-large-en-v1.5", "model_token_limit": 0, "enabled": True},
                {"plan_id": "pro", "model_id": "BAAI/bge-reranker-v2-m3", "model_token_limit": 0, "enabled": True},
            ]

            for pol in default_policies:
                pol_id = f"{pol['plan_id']}_{pol['model_id']}"
                if not SubscriptionAIPolicyService.query(id=pol_id):
                    SubscriptionAIPolicyService.save(id=pol_id, **pol)

        except Exception as e:
            logging.exception(f"AIPolicyManager.init_default_data failed: {e}")

    @classmethod
    @DB.connection_context()
    def get_user_plan(cls, tenant_id: str) -> dict:
        e, tenant = TenantService.get_by_id(tenant_id)
        if not e or not tenant:
            plan_type = "free"
        else:
            plan_type = (tenant.plan_type or "free").lower()

        plans = SubscriptionPlanService.query(id=plan_type)
        if not plans:
            # Fallback to free plan
            plans = SubscriptionPlanService.query(id="free")
            if not plans:
                cls.init_default_data()
                plans = SubscriptionPlanService.query(id="free")

        if plans:
            return plans[0].to_dict()
        return {
            "id": plan_type,
            "name": plan_type.upper(),
            "monthly_token_limit": 1000000,
            "limit_mode": "shared",
            "max_storage_gb": 10.0,
            "max_datasets": 10,
            "max_agents": 10,
            "allow_custom_providers": False,
            "allow_custom_models": False,
            "allow_custom_endpoints": False,
            "allow_private_servers": False,
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
    def get_tenant_model_tokens_used(cls, tenant_id: str, model_id: str, period: str = None) -> int:
        if not period:
            period = cls.get_current_period()

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
    def check_model_access(cls, tenant_id: str, model_name: str, model_type: str = None, user_id: str = None) -> tuple[bool, str, int]:
        """
        Validate model access based on subscription policy and token quotas.
        Returns: (allowed: bool, message: str, status_code: int)
        """
        if not tenant_id:
            return True, "OK", 200

        plan = cls.get_user_plan(tenant_id)
        plan_id = plan["id"]
        monthly_token_limit = plan["monthly_token_limit"]

        # Check user-specific limit override if available
        if user_id:
            user_limits = UserTokenLimitService.query(user_id=user_id, enabled=True)
            if user_limits and user_limits[0].monthly_token_limit > 0:
                monthly_token_limit = user_limits[0].monthly_token_limit

        # 1. Total monthly token limit check
        used_tokens = cls.get_tenant_total_tokens_used(tenant_id)
        if used_tokens >= monthly_token_limit:
            msg = f"Monthly AI token limit reached. You have used: {used_tokens:,} / {monthly_token_limit:,} tokens. Upgrade your plan to continue using AI."
            return False, msg, 429

        # Normalize model_id
        mdl_name, fid = TenantLLMService.split_model_name_and_factory(model_name)
        candidate_ids = [model_name, mdl_name]
        if fid:
            candidate_ids.append(f"{fid}/{mdl_name}")
            candidate_ids.append(f"{mdl_name}@{fid}")

        # Find global model definition if exists
        ai_model = None
        for cid in candidate_ids:
            models = AIModelService.query(id=cid)
            if models:
                ai_model = models[0]
                break

        if not ai_model:
            # Check by model_name
            models = AIModelService.query(model_name=mdl_name)
            if models:
                ai_model = models[0]

        # 2. Global model enabled check
        if ai_model and not ai_model.enabled:
            return False, f"Model '{model_name}' is currently disabled by system administrator.", 403

        # 3. Check Subscription AI Policy for this plan and model
        policy = None
        if ai_model:
            policies = SubscriptionAIPolicyService.query(plan_id=plan_id, model_id=ai_model.id, enabled=True)
            if policies:
                policy = policies[0]

        if not policy:
            for cid in candidate_ids:
                policies = SubscriptionAIPolicyService.query(plan_id=plan_id, model_id=cid, enabled=True)
                if policies:
                    policy = policies[0]
                    break

        # If model is not explicitly listed in policy:
        if not policy:
            # Check if it's a tenant custom model and if plan allows custom models
            if not plan.get("allow_custom_models", False):
                # If plan does not allow custom models and model is not in policy, reject
                return False, f"Model '{model_name}' is not available on your {plan['name']} subscription plan.", 403

        # 4. Check per-model token limit if applicable
        if policy and policy.model_token_limit > 0:
            target_model_id = policy.model_id
            model_used = cls.get_tenant_model_tokens_used(tenant_id, target_model_id)
            if model_used >= policy.model_token_limit:
                msg = f"Monthly token limit reached for model '{mdl_name}'. You have used: {model_used:,} / {policy.model_token_limit:,} tokens for this model. Upgrade your plan or switch models."
                return False, msg, 429

        return True, "OK", 200

    @classmethod
    @DB.connection_context()
    def can_add_custom_model(cls, tenant_id: str) -> tuple[bool, str]:
        from api.db.services.user_service import UserService
        user = UserService.query(id=tenant_id)
        if user and getattr(user[0], "is_superuser", False):
            return True, "OK"
        plan = cls.get_user_plan(tenant_id)
        plan_id = (plan.get("id") or "").lower()
        if plan_id not in ["pro", "enterprise"]:
            return False, "Добавление собственных AI-моделей доступно только для подписки PRO. Пожалуйста, обновите тарифный план до Pro."
        return True, "OK"

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
    ):
        if not total_tokens or total_tokens <= 0:
            return

        period = cls.get_current_period()
        plan = cls.get_user_plan(tenant_id)

        try:
            record_id = uuid.uuid4().hex
            TokenUsageLogService.save(
                id=record_id,
                user_id=user_id or tenant_id,
                tenant_id=tenant_id,
                subscription_id=plan["id"],
                model_id=model_id or "unknown",
                model_type=model_type or "CHAT",
                input_tokens=input_tokens or 0,
                output_tokens=output_tokens or 0,
                total_tokens=total_tokens,
                billing_period=period,
                create_time=current_timestamp(),
            )
        except Exception as e:
            logging.exception(f"AIPolicyManager.record_token_usage error: {e}")

    @classmethod
    @DB.connection_context()
    def get_user_usage_summary(cls, tenant_id: str, user_id: str = None) -> dict:
        period = cls.get_current_period()
        plan = cls.get_user_plan(tenant_id)

        monthly_limit = plan["monthly_token_limit"]
        if user_id:
            user_limits = UserTokenLimitService.query(user_id=user_id, enabled=True)
            if user_limits and user_limits[0].monthly_token_limit > 0:
                monthly_limit = user_limits[0].monthly_token_limit

        total_used = cls.get_tenant_total_tokens_used(tenant_id, period)
        percentage = round((total_used / monthly_limit) * 100, 1) if monthly_limit > 0 else 0

        # Query breakdown by model
        breakdown_query = (
            TokenUsageLog.select(
                TokenUsageLog.model_id,
                TokenUsageLog.model_type,
                fn.SUM(TokenUsageLog.total_tokens).alias("tokens_used"),
            )
            .where(TokenUsageLog.tenant_id == tenant_id, TokenUsageLog.billing_period == period)
            .group_by(TokenUsageLog.model_id, TokenUsageLog.model_type)
            .dicts()
        )
        breakdown = list(breakdown_query)

        # Get allowed models list for plan
        policies = (
            SubscriptionAIPolicy.select(
                SubscriptionAIPolicy.model_id, SubscriptionAIPolicy.model_token_limit, SubscriptionAIPolicy.enabled
            )
            .where(SubscriptionAIPolicy.plan_id == plan["id"], SubscriptionAIPolicy.enabled == True)
            .dicts()
        )

        return {
            "plan": plan,
            "period": period,
            "total_used": total_used,
            "monthly_limit": monthly_limit,
            "percentage": percentage,
            "breakdown": breakdown,
            "allowed_models": list(policies),
        }
