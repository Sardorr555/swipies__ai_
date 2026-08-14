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
from quart import request

from api.apps import current_user, login_required
from api.db.services.ai_policy_service import (
    AIModelService,
    AIPolicyManager,
    SubscriptionAIPolicyService,
    SubscriptionPlanService,
    UserTokenLimitService,
)
from api.utils.api_utils import (
    get_data_error_result,
    get_json_result,
    get_request_json,
)
from common.constants import RetCode


def require_superuser():
    if not getattr(current_user, "is_superuser", False):
        return get_json_result(
            data=False,
            message="Superuser authorization required.",
            code=RetCode.AUTHENTICATION_ERROR,
        )
    return None


# ==========================================
# Admin APIs: Subscription Plans & Policies
# ==========================================


@manager.route("/admin/ai/plans", methods=["GET"])  # noqa: F821
@login_required
async def admin_get_plans():
    auth_err = require_superuser()
    if auth_err:
        return auth_err

    plans = SubscriptionPlanService.get_all()
    res = [p.to_dict() for p in plans]
    return get_json_result(data=res)


@manager.route("/admin/ai/plans/<plan_id>", methods=["PUT"])  # noqa: F821
@login_required
async def admin_update_plan(plan_id):
    auth_err = require_superuser()
    if auth_err:
        return auth_err

    req = await get_request_json()
    if not req:
        return get_data_error_result(message="Request payload is empty.")

    plans = SubscriptionPlanService.query(id=plan_id)
    if not plans:
        return get_data_error_result(message=f"Plan '{plan_id}' not found.")

    update_fields = {}
    allowed_keys = [
        "name",
        "monthly_token_limit",
        "limit_mode",
        "max_storage_gb",
        "max_datasets",
        "max_agents",
        "allow_custom_providers",
        "allow_custom_models",
        "allow_custom_endpoints",
        "allow_private_servers",
        "default_llm_id",
        "default_embd_id",
        "status",
    ]
    for k in allowed_keys:
        if k in req:
            update_fields[k] = req[k]

    if update_fields:
        SubscriptionPlanService.filter_update([SubscriptionPlanService.model.id == plan_id], update_fields)

    return get_json_result(data=True)


# ==========================================
# Admin APIs: Global AI Models
# ==========================================


@manager.route("/admin/ai/models", methods=["GET"])  # noqa: F821
@login_required
async def admin_get_models():
    auth_err = require_superuser()
    if auth_err:
        return auth_err

    models = AIModelService.get_all()
    res = [m.to_dict() for m in models]
    return get_json_result(data=res)


@manager.route("/admin/ai/models", methods=["POST"])  # noqa: F821
@login_required
async def admin_save_model():
    auth_err = require_superuser()
    if auth_err:
        return auth_err

    req = await get_request_json()
    model_id = req.get("id")
    provider = req.get("provider")
    model_name = req.get("model_name")
    model_type = req.get("model_type", "CHAT")

    if not provider or not model_name:
        return get_data_error_result(message="provider and model_name are required.")

    if not model_id:
        model_id = f"{provider}/{model_name}".lower()

    model_data = {
        "id": model_id,
        "provider": provider,
        "model_name": model_name,
        "model_type": model_type.upper(),
        "base_url": req.get("base_url", ""),
        "api_key": req.get("api_key", ""),
        "enabled": req.get("enabled", True),
        "is_global": req.get("is_global", True),
        "is_custom": req.get("is_custom", False),
    }

    if AIModelService.query(id=model_id):
        AIModelService.filter_update([AIModelService.model.id == model_id], model_data)
    else:
        AIModelService.save(**model_data)

    return get_json_result(data=model_data)


@manager.route("/admin/ai/models/<path:model_id>", methods=["DELETE"])  # noqa: F821
@login_required
async def admin_delete_model(model_id):
    auth_err = require_superuser()
    if auth_err:
        return auth_err

    AIModelService.filter_delete([AIModelService.model.id == model_id])
    return get_json_result(data=True)


# ==========================================
# Admin APIs: Subscription AI Policies
# ==========================================


@manager.route("/admin/ai/policies", methods=["GET"])  # noqa: F821
@login_required
async def admin_get_policies():
    auth_err = require_superuser()
    if auth_err:
        return auth_err

    plan_id = request.args.get("plan_id")
    if plan_id:
        policies = SubscriptionAIPolicyService.query(plan_id=plan_id)
    else:
        policies = SubscriptionAIPolicyService.get_all()

    res = [p.to_dict() for p in policies]
    return get_json_result(data=res)


@manager.route("/admin/ai/policies", methods=["PUT"])  # noqa: F821
@login_required
async def admin_update_policies():
    auth_err = require_superuser()
    if auth_err:
        return auth_err

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
            "model_token_limit": item.get("model_token_limit", 0),
            "is_default_llm": item.get("is_default_llm", False),
            "is_default_embd": item.get("is_default_embd", False),
            "enabled": item.get("enabled", True),
        }

        if SubscriptionAIPolicyService.query(id=pol_id):
            SubscriptionAIPolicyService.filter_update([SubscriptionAIPolicyService.model.id == pol_id], pol_data)
        else:
            SubscriptionAIPolicyService.save(**pol_data)

    return get_json_result(data=True)


# ==========================================
# Admin APIs: User Token Overrides
# ==========================================


@manager.route("/admin/ai/user-limits/<user_id>", methods=["GET"])  # noqa: F821
@login_required
async def admin_get_user_limit(user_id):
    auth_err = require_superuser()
    if auth_err:
        return auth_err

    limits = UserTokenLimitService.query(user_id=user_id)
    data = limits[0].to_dict() if limits else {"user_id": user_id, "monthly_token_limit": 0, "enabled": True}
    return get_json_result(data=data)


@manager.route("/admin/ai/user-limits", methods=["PUT"])  # noqa: F821
@login_required
async def admin_set_user_limit():
    auth_err = require_superuser()
    if auth_err:
        return auth_err

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

    return get_json_result(data=True)


# ==========================================
# User APIs: AI Usage & Allowed Models
# ==========================================


@manager.route("/user/ai/usage", methods=["GET"])  # noqa: F821
@login_required
async def user_get_ai_usage():
    try:
        tenant_id = current_user.id
        summary = AIPolicyManager.get_user_usage_summary(tenant_id, current_user.id)
        return get_json_result(data=summary)
    except Exception as e:
        logging.exception(f"user_get_ai_usage error: {e}")
        return get_data_error_result(message=str(e))


@manager.route("/user/ai/allowed-models", methods=["GET"])  # noqa: F821
@login_required
async def user_get_allowed_models():
    try:
        tenant_id = current_user.id
        plan = AIPolicyManager.get_user_plan(tenant_id)
        policies = SubscriptionAIPolicyService.query(plan_id=plan["id"], enabled=True)
        res = [p.to_dict() for p in policies]
        return get_json_result(data={"plan": plan, "models": res})
    except Exception as e:
        logging.exception(f"user_get_allowed_models error: {e}")
        return get_data_error_result(message=str(e))
