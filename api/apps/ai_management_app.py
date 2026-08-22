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
from peewee import fn
from quart import Blueprint, request

from api.apps import current_user, login_required
from api.db.db_models import AIModel, AIProvider, SubscriptionAIPolicy, User
from api.db.services.ai_audit_log_service import AIAuditLogService
from api.db.services.ai_policy_service import (
    AIModelService,
    AIPolicyManager,
    SubscriptionAIPolicyService,
    SubscriptionPlanService,
    UserTokenLimitService,
)
from api.db.services.ai_provider_service import AIProviderService
from api.db.services.global_instance_service import GlobalInstanceService, GLOBAL_INSTANCE_ID
from api.db.services.llm_service import LLMService
from api.db.services.tenant_llm_service import TenantLLMService, LLMFactoriesService
from api.utils.api_utils import (
    get_data_error_result,
    get_json_result,
    get_request_json,
)
from api.utils.key_crypto import encrypt_api_key, decrypt_api_key, mask_api_key
from common.constants import ActiveStatusEnum, RetCode, StatusEnum
from common.misc_utils import get_uuid
from common.time_utils import current_timestamp

# Define page_name so __init__.py mounts this blueprint at /v1/admin/ai
page_name = "admin/ai"


def require_superuser():
    if not getattr(current_user, "is_superuser", False):
        return get_json_result(
            data=False,
            message="Superuser authorization required.",
            code=RetCode.AUTHENTICATION_ERROR,
        )
    return None


# ==========================================
# Admin APIs: Global RAGFlow Instance
# ==========================================


@manager.route("/instance", methods=["GET"])  # noqa: F821
@login_required
async def admin_get_global_instance():
    auth_err = require_superuser()
    if auth_err:
        return auth_err

    try:
        stats = GlobalInstanceService.get_instance_stats()
        return get_json_result(data=stats)
    except Exception as e:
        logging.exception("admin_get_global_instance error: %s", e)
        return get_data_error_result(message=str(e))


@manager.route("/instance", methods=["PUT"])  # noqa: F821
@login_required
async def admin_update_global_instance():
    auth_err = require_superuser()
    if auth_err:
        return auth_err

    try:
        req = await get_request_json()
        if not req:
            return get_data_error_result(message="Request payload is empty.")

        GlobalInstanceService.update_global_instance(req, admin_user_id=current_user.id)
        return get_json_result(data=GlobalInstanceService.get_instance_stats())
    except Exception as e:
        logging.exception("admin_update_global_instance error: %s", e)
        return get_data_error_result(message=str(e))


@manager.route("/defaults", methods=["GET"])  # noqa: F821
@login_required
async def admin_get_default_models():
    auth_err = require_superuser()
    if auth_err:
        return auth_err

    try:
        stats = GlobalInstanceService.get_instance_stats()
        return get_json_result(data=stats)
    except Exception as e:
        logging.exception("admin_get_default_models error: %s", e)
        return get_data_error_result(message=str(e))


@manager.route("/defaults", methods=["PUT"])  # noqa: F821
@login_required
async def admin_update_default_models():
    auth_err = require_superuser()
    if auth_err:
        return auth_err

    try:
        req = await get_request_json()
        if not req:
            return get_data_error_result(message="Request payload is empty.")

        GlobalInstanceService.update_global_instance(req, admin_user_id=current_user.id)
        return get_json_result(data=GlobalInstanceService.get_instance_stats())
    except Exception as e:
        logging.exception("admin_update_default_models error: %s", e)
        return get_data_error_result(message=str(e))


# ==========================================
# Admin APIs: Global AI Providers
# ==========================================


@manager.route("/providers", methods=["GET"])  # noqa: F821
@login_required
async def admin_get_providers():
    auth_err = require_superuser()
    if auth_err:
        return auth_err

    try:
        providers = AIProviderService.get_global_providers()
        return get_json_result(data=providers)
    except Exception as e:
        logging.exception("admin_get_providers error: %s", e)
        return get_data_error_result(message=str(e))


@manager.route("/providers/available", methods=["GET"])  # noqa: F821
@login_required
async def admin_get_available_providers():
    auth_err = require_superuser()
    if auth_err:
        return auth_err

    try:
        from api.apps.services.provider_api_service import list_providers
        from api.db.services.tenant_model_provider_service import TenantModelProviderService
        admin_tenant_id = TenantModelProviderService._get_admin_tenant_id() or current_user.id
        success, providers = list_providers(admin_tenant_id, all_available=True)
        if success:
            return get_json_result(data=providers)
        return get_data_error_result(message="Failed to list system providers")
    except Exception as e:
        logging.exception("admin_get_available_providers error: %s", e)
        return get_data_error_result(message=str(e))


@manager.route("/providers/verify", methods=["POST"])  # noqa: F821
@login_required
async def admin_verify_provider():
    auth_err = require_superuser()
    if auth_err:
        return auth_err

    try:
        req = await get_request_json()
        provider_name = req.get("provider_name")
        raw_key = req.get("api_key", "")
        base_url = req.get("base_url", "")
        extra_params = req.get("extra", {})

        if not raw_key:
            existing = AIProviderService.model.get_or_none(AIProviderService.model.provider_name == provider_name, AIProviderService.model.is_global == True)
            if existing and existing.api_key:
                raw_key = existing.api_key

        if not raw_key:
            return get_data_error_result(message="API key is required for verification.")

        success, message, models = await AIProviderService.async_verify_provider_connection(
            provider_name=provider_name,
            raw_api_key=raw_key,
            base_url=base_url,
            extra_params=extra_params,
        )

        return get_json_result(data={
            "success": success,
            "message": message,
            "available_models": models,
            "count": len(models),
        })
    except Exception as e:
        logging.exception("admin_verify_provider error: %s", e)
        return get_data_error_result(message=str(e))


@manager.route("/providers", methods=["POST"])  # noqa: F821
@login_required
async def admin_save_provider():
    auth_err = require_superuser()
    if auth_err:
        return auth_err

    try:
        req = await get_request_json()
        if not req or not req.get("provider_name"):
            return get_data_error_result(message="provider_name is required.")

        res = AIProviderService.save_global_provider(req, admin_user_id=current_user.id)
        return get_json_result(data=res)
    except Exception as e:
        logging.exception("admin_save_provider error: %s", e)
        return get_data_error_result(message=str(e))


@manager.route("/providers/<provider_id>", methods=["DELETE"])  # noqa: F821
@login_required
async def admin_delete_provider(provider_id):
    auth_err = require_superuser()
    if auth_err:
        return auth_err

    try:
        success = AIProviderService.delete_global_provider(provider_id, admin_user_id=current_user.id)
        return get_json_result(data=success)
    except Exception as e:
        logging.exception("admin_delete_provider error: %s", e)
        return get_data_error_result(message=str(e))


# ==========================================
# Admin APIs: Platform Models & Pricing
# ==========================================


@manager.route("/models", methods=["GET"])  # noqa: F821
@login_required
async def admin_get_models():
    auth_err = require_superuser()
    if auth_err:
        return auth_err

    try:
        # Query all global platform models
        models = AIModelService.get_platform_models()

        # Attach subscription plan access for each model
        policies = SubscriptionAIPolicyService.get_all()
        plan_access_map = {}
        for p in policies:
            if p.model_id not in plan_access_map:
                plan_access_map[p.model_id] = []
            if p.enabled:
                plan_access_map[p.model_id].append(p.plan_id.lower())

        for m in models:
            m["allowed_plans"] = plan_access_map.get(m["id"], [])

        return get_json_result(data=models)
    except Exception as e:
        logging.exception("admin_get_models error: %s", e)
        return get_data_error_result(message=str(e))


@manager.route("/models", methods=["POST"])  # noqa: F821
@login_required
async def admin_save_model():
    auth_err = require_superuser()
    if auth_err:
        return auth_err

    try:
        req = await get_request_json()
        if not req:
            return get_data_error_result(message="Payload is required.")

        model_name = req.get("model_name")
        provider = req.get("provider")
        model_type = req.get("model_type", "CHAT")
        if not model_name or not provider:
            return get_data_error_result(message="model_name and provider are required.")

        model_id = req.get("id") or f"{provider.lower()}/{model_name}"
        raw_key = req.get("api_key", "")
        existing = AIModel.get_or_none(AIModel.id == model_id)

        if raw_key and not raw_key.startswith("enc:v1:"):
            enc_key = encrypt_api_key(raw_key)
        elif raw_key:
            enc_key = raw_key
        elif existing:
            enc_key = existing.api_key
        else:
            # Fallback to provider key if model key not explicitly given
            prov = AIProviderService.get_raw_by_provider_name(provider)
            enc_key = prov.api_key if prov else ""

        now = current_timestamp()
        model_data = {
            "id": model_id,
            "provider": provider,
            "model_name": model_name,
            "model_type": model_type.upper(),
            "base_url": req.get("base_url", ""),
            "api_key": enc_key,
            "input_token_price": float(req.get("input_token_price", 0.0) or 0.0),
            "output_token_price": float(req.get("output_token_price", 0.0) or 0.0),
            "max_tokens": int(req.get("max_tokens", 8192) or 8192),
            "enabled": bool(req.get("enabled", True)),
            "is_global": True,
            "is_custom": False,
            "global_instance_id": GLOBAL_INSTANCE_ID,
            "status": "active" if req.get("enabled", True) else "disabled",
            "update_time": now,
        }

        old_val = existing.to_dict() if existing else None
        if existing:
            AIModelService.filter_update([AIModelService.model.id == model_id], model_data)
        else:
            model_data["create_time"] = now
            AIModelService.save(**model_data)

        # Update subscription plan mappings if provided
        allowed_plans = req.get("allowed_plans", [])
        if isinstance(allowed_plans, list):
            for plan_id in ["free", "plus", "pro"]:
                pol_id = f"{plan_id}_{model_id}"
                is_enabled = plan_id in [p.lower() for p in allowed_plans]
                if SubscriptionAIPolicyService.query(id=pol_id):
                    SubscriptionAIPolicyService.filter_update(
                        [SubscriptionAIPolicyService.model.id == pol_id],
                        {"enabled": is_enabled},
                    )
                elif is_enabled:
                    SubscriptionAIPolicyService.save(
                        id=pol_id,
                        plan_id=plan_id,
                        model_id=model_id,
                        model_token_limit=0,
                        enabled=True,
                    )

        # Audit log
        AIAuditLogService.log_action(
            user_id=current_user.id,
            action="MODEL_UPDATE" if existing else "MODEL_CREATE",
            target_type="ai_model",
            target_id=model_id,
            old_val=old_val,
            new_val=model_data,
        )

        # Sync to RAGFlow core TenantLLM and TenantModel
        try:
            from api.db.services.tenant_model_provider_service import TenantModelProviderService
            from api.db.services.tenant_model_instance_service import TenantModelInstanceService
            from api.db.services.tenant_model_service import TenantModelService

            admin_tenant_id = TenantModelProviderService._get_admin_tenant_id()
            if admin_tenant_id:
                decrypted_key = decrypt_api_key(enc_key) if enc_key else ""
                p_obj = TenantModelProviderService.get_by_tenant_id_and_provider_name(admin_tenant_id, provider, fallback_admin=False)
                if not p_obj:
                    TenantModelProviderService.insert(id=get_uuid(), tenant_id=admin_tenant_id, provider_name=provider)
                    p_obj = TenantModelProviderService.get_by_tenant_id_and_provider_name(admin_tenant_id, provider, fallback_admin=False)
                if p_obj:
                    inst_obj = TenantModelInstanceService.get_by_provider_id_and_instance_name(p_obj.id, "default")
                    if not inst_obj:
                        inst_obj = TenantModelInstanceService.create_instance(
                            provider_id=p_obj.id,
                            instance_name="default",
                            api_key=decrypted_key,
                            extra=json.dumps({"base_url": model_data["base_url"]}),
                        )
                    else:
                        TenantModelInstanceService.filter_update(
                            [TenantModelInstanceService.model.id == inst_obj.id],
                            {"api_key": decrypted_key, "extra": json.dumps({"base_url": model_data["base_url"]})},
                        )

                    m_obj = TenantModelService.get_by_provider_id_and_instance_id_and_model_type_and_model_name(
                        p_obj.id, inst_obj.id, model_type.upper(), model_name
                    )
                    status_act = ActiveStatusEnum.ACTIVE.value if model_data["enabled"] else ActiveStatusEnum.INACTIVE.value
                    if not m_obj:
                        TenantModelService.insert(
                            id=get_uuid(),
                            model_name=model_name,
                            provider_id=p_obj.id,
                            instance_id=inst_obj.id,
                            model_type=model_type.upper(),
                            extra=json.dumps({"max_tokens": model_data["max_tokens"]}),
                            status=status_act,
                        )
                    else:
                        TenantModelService.filter_update(
                            [TenantModelService.model.id == m_obj.id],
                            {"status": status_act},
                        )
        except Exception as sync_e:
            logging.warning("Sync AIModel to RAGFlow LLM core warning: %s", sync_e)

        model_data["api_key_masked"] = mask_api_key(enc_key)
        del model_data["api_key"]
        return get_json_result(data=model_data)
    except Exception as e:
        logging.exception("admin_save_model error: %s", e)
        return get_data_error_result(message=str(e))


@manager.route("/models/<path:model_id>", methods=["DELETE"])  # noqa: F821
@login_required
async def admin_delete_model(model_id):
    auth_err = require_superuser()
    if auth_err:
        return auth_err

    try:
        m = AIModel.get_or_none(AIModel.id == model_id)
        if m:
            old_val = m.to_dict()
            AIModelService.filter_delete([AIModelService.model.id == model_id])
            SubscriptionAIPolicyService.filter_delete([SubscriptionAIPolicyService.model.model_id == model_id])
            AIAuditLogService.log_action(
                user_id=current_user.id,
                action="MODEL_DELETE",
                target_type="ai_model",
                target_id=model_id,
                old_val=old_val,
            )
        return get_json_result(data=True)
    except Exception as e:
        logging.exception("admin_delete_model error: %s", e)
        return get_data_error_result(message=str(e))


# ==========================================
# Admin APIs: Subscription Plans & Policies
# ==========================================


@manager.route("/plans", methods=["GET"])  # noqa: F821
@login_required
async def admin_get_plans():
    auth_err = require_superuser()
    if auth_err:
        return auth_err

    try:
        plans = SubscriptionPlanService.get_all()
        res = [p.to_dict() for p in plans]
        return get_json_result(data=res)
    except Exception as e:
        logging.exception("admin_get_plans error: %s", e)
        return get_data_error_result(message=str(e))


@manager.route("/plans/<plan_id>", methods=["PUT"])  # noqa: F821
@login_required
async def admin_update_plan(plan_id):
    auth_err = require_superuser()
    if auth_err:
        return auth_err

    try:
        req = await get_request_json()
        if not req:
            return get_data_error_result(message="Request payload is empty.")

        plans = SubscriptionPlanService.query(id=plan_id)
        if not plans:
            return get_data_error_result(message=f"Plan '{plan_id}' not found.")

        allowed_keys = [
            "name",
            "daily_token_limit",
            "monthly_token_limit",
            "daily_request_limit",
            "monthly_request_limit",
            "requests_per_minute",
            "max_tokens_per_request",
            "limit_mode",
            "max_storage_gb",
            "max_datasets",
            "max_agents",
            "allow_custom_providers",
            "allow_custom_models",
            "allow_custom_endpoints",
            "allow_private_servers",
            "allow_byok",
            "max_byok_models",
            "default_llm_id",
            "default_embd_id",
            "default_rerank_id",
            "status",
        ]
        update_fields = {k: req[k] for k in allowed_keys if k in req}

        old_val = plans[0].to_dict()
        SubscriptionPlanService.filter_update([SubscriptionPlanService.model.id == plan_id], update_fields)

        AIAuditLogService.log_action(
            user_id=current_user.id,
            action="PLAN_UPDATE",
            target_type="subscription_plan",
            target_id=plan_id,
            old_val=old_val,
            new_val=update_fields,
        )

        return get_json_result(data=True)
    except Exception as e:
        logging.exception("admin_update_plan error: %s", e)
        return get_data_error_result(message=str(e))


@manager.route("/policies", methods=["GET"])  # noqa: F821
@login_required
async def admin_get_policies():
    auth_err = require_superuser()
    if auth_err:
        return auth_err

    try:
        plan_id = request.args.get("plan_id")
        if plan_id:
            policies = SubscriptionAIPolicyService.query(plan_id=plan_id)
        else:
            policies = SubscriptionAIPolicyService.get_all()

        res = [p.to_dict() for p in policies]
        return get_json_result(data=res)
    except Exception as e:
        logging.exception("admin_get_policies error: %s", e)
        return get_data_error_result(message=str(e))


@manager.route("/policies", methods=["PUT"])  # noqa: F821
@login_required
async def admin_update_policies():
    auth_err = require_superuser()
    if auth_err:
        return auth_err

    try:
        req = await get_request_json()
        plan_id = req.get("plan_id")
        policies_list = req.get("policies", [])

        if not plan_id:
            return get_data_error_result(message="plan_id is required.")

        for item in policies_list:
            model_id = item.get("model_id")
            if not model_id:
                continue
            pol_id = f"{plan_id}_{model_id}"
            pol_data = {
                "id": pol_id,
                "plan_id": plan_id,
                "model_id": model_id,
                "model_token_limit": int(item.get("model_token_limit", 0) or 0),
                "is_default_llm": bool(item.get("is_default_llm", False)),
                "is_default_embd": bool(item.get("is_default_embd", False)),
                "is_default_rerank": bool(item.get("is_default_rerank", False)),
                "enabled": bool(item.get("enabled", True)),
            }

            if SubscriptionAIPolicyService.query(id=pol_id):
                SubscriptionAIPolicyService.filter_update([SubscriptionAIPolicyService.model.id == pol_id], pol_data)
            else:
                SubscriptionAIPolicyService.save(**pol_data)

        AIAuditLogService.log_action(
            user_id=current_user.id,
            action="POLICIES_UPDATE",
            target_type="subscription_ai_policy",
            target_id=plan_id,
            new_val={"count": len(policies_list)},
        )

        return get_json_result(data=True)
    except Exception as e:
        logging.exception("admin_update_policies error: %s", e)
        return get_data_error_result(message=str(e))


# ==========================================
# Admin APIs: Central Analytics & Audit Logs
# ==========================================


@manager.route("/analytics", methods=["GET"])  # noqa: F821
@manager.route("/metrics", methods=["GET"])  # noqa: F821
@manager.route("/usage-stats", methods=["GET"])  # noqa: F821
@login_required
async def admin_get_analytics():
    auth_err = require_superuser()
    if auth_err:
        return auth_err

    try:
        period = request.args.get("period")
        data = AIPolicyManager.get_admin_analytics(period)
        return get_json_result(data=data)
    except Exception as e:
        logging.exception("admin_get_analytics error: %s", e)
        return get_data_error_result(message=str(e))


@manager.route("/audit-logs", methods=["GET"])  # noqa: F821
@login_required
async def admin_get_audit_logs():
    auth_err = require_superuser()
    if auth_err:
        return auth_err

    try:
        limit = int(request.args.get("limit", 50))
        offset = int(request.args.get("offset", 0))
        action = request.args.get("action")
        target_type = request.args.get("target_type")

        logs, total = AIAuditLogService.get_logs(limit=limit, offset=offset, action=action, target_type=target_type)
        return get_json_result(data={"items": logs, "total": total})
    except Exception as e:
        logging.exception("admin_get_audit_logs error: %s", e)
        return get_data_error_result(message=str(e))


@manager.route("/byok-stats", methods=["GET"])  # noqa: F821
@login_required
async def admin_get_byok_stats():
    auth_err = require_superuser()
    if auth_err:
        return auth_err

    try:
        total_byok = AIModel.select().where(AIModel.is_custom == True).count()
        active_byok = AIModel.select().where(AIModel.is_custom == True, AIModel.status == "active").count()
        locked_byok = AIModel.select().where(AIModel.is_custom == True, AIModel.status == "locked_pro_required").count()
        unique_users = AIModel.select(fn.COUNT(fn.DISTINCT(AIModel.owner_user_id))).where(AIModel.is_custom == True).scalar() or 0

        return get_json_result(data={
            "total_byok_models": total_byok,
            "active_byok_models": active_byok,
            "locked_byok_models": locked_byok,
            "byok_users_count": unique_users,
        })
    except Exception as e:
        logging.exception("admin_get_byok_stats error: %s", e)
        return get_data_error_result(message=str(e))


# ==========================================
# Admin APIs: User Token Overrides
# ==========================================


@manager.route("/user-limits/<user_id>", methods=["GET"])  # noqa: F821
@login_required
async def admin_get_user_limit(user_id):
    auth_err = require_superuser()
    if auth_err:
        return auth_err

    try:
        limits = UserTokenLimitService.query(user_id=user_id)
        data = limits[0].to_dict() if limits else {"user_id": user_id, "monthly_token_limit": 0, "enabled": True}
        return get_json_result(data=data)
    except Exception as e:
        logging.exception("admin_get_user_limit error: %s", e)
        return get_data_error_result(message=str(e))


@manager.route("/user-limits", methods=["PUT"])  # noqa: F821
@login_required
async def admin_set_user_limit():
    auth_err = require_superuser()
    if auth_err:
        return auth_err

    try:
        req = await get_request_json()
        user_id = req.get("user_id")
        limit = req.get("monthly_token_limit", 0)
        enabled = req.get("enabled", True)

        if not user_id:
            return get_data_error_result(message="user_id is required.")

        if UserTokenLimitService.query(user_id=user_id):
            UserTokenLimitService.filter_update(
                [UserTokenLimitService.model.user_id == user_id],
                {"monthly_token_limit": limit, "enabled": enabled},
            )
        else:
            UserTokenLimitService.save(user_id=user_id, monthly_token_limit=limit, enabled=enabled)

        AIAuditLogService.log_action(
            user_id=current_user.id,
            action="USER_LIMIT_UPDATE",
            target_type="user",
            target_id=user_id,
            new_val={"monthly_token_limit": limit, "enabled": enabled},
        )

        return get_json_result(data=True)
    except Exception as e:
        logging.exception("admin_set_user_limit error: %s", e)
        return get_data_error_result(message=str(e))


# ==========================================
# User APIs: /v1/user/ai/...
# ==========================================

user_ai_manager = Blueprint("user_ai_manager", __name__)


@user_ai_manager.route("/usage", methods=["GET"])
@login_required
async def user_get_ai_usage():
    try:
        tenant_id = current_user.id
        summary = AIPolicyManager.get_user_usage_summary(tenant_id, current_user.id)
        return get_json_result(data=summary)
    except Exception as e:
        logging.exception("user_get_ai_usage error: %s", e)
        return get_data_error_result(message=str(e))


@user_ai_manager.route("/allowed-models", methods=["GET"])
@login_required
async def user_get_allowed_models():
    try:
        tenant_id = current_user.id
        plan = AIPolicyManager.get_user_plan(tenant_id, current_user.id)
        policies = SubscriptionAIPolicyService.query(plan_id=plan["id"], enabled=True)
        policies_list = [p.to_dict() for p in policies]

        is_super = getattr(current_user, "is_superuser", False)
        plan_id = (plan.get("id") or "").lower()
        can_add = is_super or (plan_id in ["pro", "enterprise"]) or plan.get("allow_byok", False)

        # Include user's own BYOK models
        byok_models = AIModelService.get_user_byok_models(current_user.id)

        return get_json_result(data={
            "plan": plan,
            "models": policies_list,
            "byok_models": byok_models,
            "is_superuser": is_super,
            "can_add_custom": can_add,
            "global_instance_id": GLOBAL_INSTANCE_ID,
        })
    except Exception as e:
        logging.exception("user_get_allowed_models error: %s", e)
        return get_data_error_result(message=str(e))


@user_ai_manager.route("/byok", methods=["GET"])
@login_required
async def user_get_byok():
    try:
        models = AIModelService.get_user_byok_models(current_user.id)
        return get_json_result(data=models)
    except Exception as e:
        logging.exception("user_get_byok error: %s", e)
        return get_data_error_result(message=str(e))


@user_ai_manager.route("/byok", methods=["POST"])
@login_required
async def user_save_byok():
    try:
        # Backend authorization: Enforce PRO subscription requirement
        can_add, reason = AIPolicyManager.can_add_custom_model(current_user.id)
        if not can_add:
            return get_json_result(
                data=False,
                message=reason,
                code=403,
            )

        req = await get_request_json()
        if not req or not req.get("model_name") or not req.get("provider"):
            return get_data_error_result(message="provider and model_name are required.")

        provider = req.get("provider")
        model_name = req.get("model_name")
        model_type = req.get("model_type", "CHAT").upper()
        base_url = req.get("base_url", "")
        raw_key = req.get("api_key", "")
        max_tokens = int(req.get("max_tokens", 8192) or 8192)

        model_id = req.get("id") or f"byok_{current_user.id}_{provider.lower()}_{model_name.lower().replace('/', '_')}"
        existing = AIModel.get_or_none(AIModel.id == model_id)

        if raw_key and not raw_key.startswith("enc:v1:"):
            enc_key = encrypt_api_key(raw_key)
        elif raw_key:
            enc_key = raw_key
        elif existing:
            enc_key = existing.api_key
        else:
            enc_key = ""

        now = current_timestamp()
        byok_record = {
            "id": model_id,
            "provider": provider,
            "model_name": model_name,
            "model_type": model_type,
            "base_url": base_url,
            "api_key": enc_key,
            "input_token_price": 0.0,
            "output_token_price": 0.0,
            "max_tokens": max_tokens,
            "enabled": True,
            "is_global": False,
            "is_custom": True,
            "owner_user_id": current_user.id,
            "owner_tenant_id": current_user.id,
            "status": "active",
            "global_instance_id": GLOBAL_INSTANCE_ID,
            "extra": req.get("extra", {}),
            "update_time": now,
        }

        if existing:
            AIModelService.filter_update([AIModelService.model.id == model_id], byok_record)
        else:
            byok_record["create_time"] = now
            AIModelService.save(**byok_record)

        byok_record["api_key_masked"] = mask_api_key(enc_key)
        del byok_record["api_key"]
        return get_json_result(data=byok_record)
    except Exception as e:
        logging.exception("user_save_byok error: %s", e)
        return get_data_error_result(message=str(e))


@user_ai_manager.route("/byok/<path:model_id>", methods=["DELETE"])
@login_required
async def user_delete_byok(model_id):
    try:
        m = AIModel.get_or_none(AIModel.id == model_id, AIModel.owner_user_id == current_user.id)
        if not m and not getattr(current_user, "is_superuser", False):
            return get_data_error_result(message="Model not found or permission denied.")
        AIModelService.filter_delete([AIModelService.model.id == model_id])
        return get_json_result(data=True)
    except Exception as e:
        logging.exception("user_delete_byok error: %s", e)
        return get_data_error_result(message=str(e))


def __init_app__(app_instance):
    app_instance.register_blueprint(user_ai_manager, url_prefix="/v1/user/ai")
