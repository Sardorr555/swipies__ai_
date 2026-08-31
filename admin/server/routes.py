#
#  Copyright 2025 The InfiniFlow Authors. All Rights Reserved.
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

import secrets
import logging
from typing import Any

from common.time_utils import current_timestamp, datetime_format
from datetime import datetime
from flask import Blueprint, Response, request
from flask_login import current_user, login_required, logout_user

from auth import login_verify, login_admin, check_admin_auth
from responses import success_response, error_response
from services import UserMgr, ServiceMgr, UserServiceMgr, SettingsMgr, ConfigMgr, EnvironmentsMgr, SandboxMgr, ReferralMgr, LicenseMgr
from roles import RoleMgr
from api.common.exceptions import AdminException
from common.versions import get_ragflow_version
from api.utils.api_utils import generate_confirmation_token
from common.log_utils import get_log_levels, set_log_level

admin_bp = Blueprint("admin", __name__, url_prefix="/api/v1/admin")


@admin_bp.errorhandler(AdminException)
def handle_admin_exception(e):
    code = e.code if isinstance(e.code, int) and 100 <= e.code < 600 else 400
    return error_response(e.message, code)


@admin_bp.errorhandler(Exception)
def handle_general_exception(e):
    logging.exception("Admin API exception: %s", e)
    return error_response(str(e), 500)


@admin_bp.route("/ping", methods=["GET"])
def ping():
    return success_response(message="pong")


@admin_bp.route("/login", methods=["POST"])
def login():
    if not request.json:
        return error_response("Authorize admin failed.", 400)
    try:
        email = request.json.get("email", "")
        password = request.json.get("password", "")
        return login_admin(email, password)
    except Exception as e:
        return error_response(str(e), 500)


@admin_bp.route("/logout", methods=["GET"])
@login_required
def logout():
    try:
        current_user.access_token = f"INVALID_{secrets.token_hex(16)}"
        current_user.save()
        logout_user()
        return success_response(True)
    except Exception as e:
        return error_response(str(e), 500)


@admin_bp.route("/auth", methods=["GET"])
@login_verify
def auth_admin():
    try:
        return success_response(None, "Admin is authorized", 0)
    except Exception as e:
        return error_response(str(e), 500)


@admin_bp.route("/users", methods=["GET"])
@login_required
@check_admin_auth
def list_users():
    try:
        users = UserMgr.get_all_users()
        return success_response(users, "Get all users", 0)
    except Exception as e:
        return error_response(str(e), 500)


@admin_bp.route("/users", methods=["POST"])
@login_required
@check_admin_auth
def create_user():
    try:
        data = request.get_json()
        if not data or "username" not in data or "password" not in data:
            return error_response("Username and password are required", 400)

        username = data["username"]
        password = data["password"]
        role = data.get("role", "user")

        res = UserMgr.create_user(username, password, role)
        if res["success"]:
            user_info = res["user_info"]
            user_info.pop("password")  # do not return password
            return success_response(user_info, "User created successfully")
        else:
            return error_response("create user failed")

    except AdminException as e:
        return error_response(e.message, e.code)
    except Exception as e:
        return error_response(str(e))


@admin_bp.route("/users/<username>", methods=["DELETE"])
@login_required
@check_admin_auth
def delete_user(username):
    try:
        res = UserMgr.delete_user(username)
        if res["success"]:
            return success_response(None, res["message"])
        else:
            return error_response(res["message"])

    except AdminException as e:
        return error_response(e.message, e.code)
    except Exception as e:
        return error_response(str(e), 500)


@admin_bp.route("/users/<username>/password", methods=["PUT"])
@login_required
@check_admin_auth
def change_password(username):
    try:
        data = request.get_json()
        if not data or "new_password" not in data:
            return error_response("New password is required", 400)

        new_password = data["new_password"]
        msg = UserMgr.update_user_password(username, new_password)
        return success_response(None, msg)

    except AdminException as e:
        return error_response(e.message, e.code)
    except Exception as e:
        return error_response(str(e), 500)


@admin_bp.route("/users/<username>/activate", methods=["PUT"])
@login_required
@check_admin_auth
def alter_user_activate_status(username):
    try:
        data = request.get_json()
        if not data or "activate_status" not in data:
            return error_response("Activation status is required", 400)
        activate_status = data["activate_status"]
        msg = UserMgr.update_user_activate_status(username, activate_status)
        return success_response(None, msg)
    except AdminException as e:
        return error_response(e.message, e.code)
    except Exception as e:
        return error_response(str(e), 500)


@admin_bp.route("/users/<username>/admin", methods=["PUT"])
@login_required
@check_admin_auth
def grant_admin(username):
    try:
        if current_user.email == username:
            return error_response(f"can't grant current user: {username}", 409)
        msg = UserMgr.grant_admin(username)
        return success_response(None, msg)

    except AdminException as e:
        return error_response(e.message, e.code)
    except Exception as e:
        return error_response(str(e), 500)


@admin_bp.route("/users/<username>/admin", methods=["DELETE"])
@login_required
@check_admin_auth
def revoke_admin(username):
    try:
        if current_user.email == username:
            return error_response(f"can't grant current user: {username}", 409)
        msg = UserMgr.revoke_admin(username)
        return success_response(None, msg)

    except AdminException as e:
        return error_response(e.message, e.code)
    except Exception as e:
        return error_response(str(e), 500)


@admin_bp.route("/users/<username>", methods=["GET"])
@login_required
@check_admin_auth
def get_user_details(username):
    try:
        user_details = UserMgr.get_user_details(username)
        return success_response(user_details)

    except AdminException as e:
        return error_response(e.message, e.code)
    except Exception as e:
        return error_response(str(e), 500)


@admin_bp.route("/users/<username>/subscription", methods=["PUT"])
@login_required
@check_admin_auth
def update_user_subscription(username):
    try:
        data = request.get_json()
        if not data:
            return error_response("Request body is required", 400)

        plan_type = data.get("plan_type")
        plan_expiry_date = data.get("plan_expiry_date")
        credit = data.get("credit")

        msg = UserMgr.update_user_subscription(username, plan_type, plan_expiry_date, credit)
        return success_response(None, msg)
    except AdminException as e:
        return error_response(e.message, e.code)
    except Exception as e:
        return error_response(str(e), 500)


@admin_bp.route("/users/<username>/details", methods=["PUT"])
@login_required
@check_admin_auth
def update_user_details_route(username):
    try:
        data = request.get_json()
        if not data:
            return error_response("Request body is required", 400)

        nickname = data.get("nickname")
        phone = data.get("phone")
        referred_by_id = data.get("referred_by_id")

        msg = UserMgr.update_user_details(username, nickname, phone, referred_by_id)
        return success_response(None, msg)
    except AdminException as e:
        return error_response(e.message, e.code)
    except Exception as e:
        return error_response(str(e), 500)


@admin_bp.route("/users/<username>/datasets", methods=["GET"])
@login_required
@check_admin_auth
def get_user_datasets(username):
    try:
        datasets_list = UserServiceMgr.get_user_datasets(username)
        return success_response(datasets_list)

    except AdminException as e:
        return error_response(e.message, e.code)
    except Exception as e:
        return error_response(str(e), 500)


@admin_bp.route("/users/<username>/agents", methods=["GET"])
@login_required
@check_admin_auth
def get_user_agents(username):
    try:
        agents_list = UserServiceMgr.get_user_agents(username)
        return success_response(agents_list)

    except AdminException as e:
        return error_response(e.message, e.code)
    except Exception as e:
        return error_response(str(e), 500)


@admin_bp.route("/services", methods=["GET"])
@login_required
@check_admin_auth
def get_services():
    try:
        services = ServiceMgr.get_all_services()
        return success_response(services, "Get all services", 0)
    except Exception as e:
        return error_response(str(e), 500)


@admin_bp.route("/service_types/<service_type>", methods=["GET"])
@login_required
@check_admin_auth
def get_services_by_type(service_type_str):
    try:
        services = ServiceMgr.get_services_by_type(service_type_str)
        return success_response(services)
    except Exception as e:
        return error_response(str(e), 500)


@admin_bp.route("/services/<service_id>", methods=["GET"])
@login_required
@check_admin_auth
def get_service(service_id):
    try:
        services = ServiceMgr.get_service_details(service_id)
        return success_response(services)
    except Exception as e:
        return error_response(str(e), 500)


@admin_bp.route("/services/<service_id>", methods=["DELETE"])
@login_required
@check_admin_auth
def shutdown_service(service_id):
    try:
        services = ServiceMgr.shutdown_service(service_id)
        return success_response(services)
    except Exception as e:
        return error_response(str(e), 500)


@admin_bp.route("/services/<service_id>", methods=["PUT"])
@login_required
@check_admin_auth
def restart_service(service_id):
    try:
        services = ServiceMgr.restart_service(service_id)
        return success_response(services)
    except Exception as e:
        return error_response(str(e), 500)


@admin_bp.route("/roles", methods=["POST"])
@login_required
@check_admin_auth
def create_role():
    try:
        data = request.get_json()
        if not data or "role_name" not in data:
            return error_response("Role name is required", 400)
        role_name: str = data["role_name"]
        description: str = data["description"]
        res = RoleMgr.create_role(role_name, description)
        return success_response(res)
    except Exception as e:
        return error_response(str(e), 500)


@admin_bp.route("/roles/<role_name>", methods=["PUT"])
@login_required
@check_admin_auth
def update_role(role_name: str):
    try:
        data = request.get_json()
        if not data or "description" not in data:
            return error_response("Role description is required", 400)
        description: str = data["description"]
        res = RoleMgr.update_role_description(role_name, description)
        return success_response(res)
    except Exception as e:
        return error_response(str(e), 500)


@admin_bp.route("/roles/<role_name>", methods=["DELETE"])
@login_required
@check_admin_auth
def delete_role(role_name: str):
    try:
        res = RoleMgr.delete_role(role_name)
        return success_response(res)
    except Exception as e:
        return error_response(str(e), 500)


@admin_bp.route("/roles", methods=["GET"])
@login_required
@check_admin_auth
def list_roles():
    try:
        res = RoleMgr.list_roles()
        return success_response(res)
    except Exception as e:
        return error_response(str(e), 500)


@admin_bp.route("/roles/<role_name>/permission", methods=["GET"])
@login_required
@check_admin_auth
def get_role_permission(role_name: str):
    try:
        res = RoleMgr.get_role_permission(role_name)
        return success_response(res)
    except Exception as e:
        return error_response(str(e), 500)


@admin_bp.route("/roles/<role_name>/permission", methods=["POST"])
@login_required
@check_admin_auth
def grant_role_permission(role_name: str):
    try:
        data = request.get_json()
        if not data or "actions" not in data or "resource" not in data:
            return error_response("Permission is required", 400)
        actions: list = data["actions"]
        resource: str = data["resource"]
        res = RoleMgr.grant_role_permission(role_name, actions, resource)
        return success_response(res)
    except Exception as e:
        return error_response(str(e), 500)


@admin_bp.route("/roles/<role_name>/permission", methods=["DELETE"])
@login_required
@check_admin_auth
def revoke_role_permission(role_name: str):
    try:
        data = request.get_json()
        if not data or "actions" not in data or "resource" not in data:
            return error_response("Permission is required", 400)
        actions: list = data["actions"]
        resource: str = data["resource"]
        res = RoleMgr.revoke_role_permission(role_name, actions, resource)
        return success_response(res)
    except Exception as e:
        return error_response(str(e), 500)


@admin_bp.route("/users/<user_name>/role", methods=["PUT"])
@login_required
@check_admin_auth
def update_user_role(user_name: str):
    try:
        data = request.get_json()
        if not data or "role_name" not in data:
            return error_response("Role name is required", 400)
        role_name: str = data["role_name"]
        res = RoleMgr.update_user_role(user_name, role_name)
        return success_response(res)
    except Exception as e:
        return error_response(str(e), 500)


@admin_bp.route("/users/<user_name>/permission", methods=["GET"])
@login_required
@check_admin_auth
def get_user_permission(user_name: str):
    try:
        res = RoleMgr.get_user_permission(user_name)
        return success_response(res)
    except Exception as e:
        return error_response(str(e), 500)


@admin_bp.route("/variables", methods=["PUT"])
@login_required
@check_admin_auth
def set_variable():
    try:
        data = request.get_json()
        if not data or "var_name" not in data:
            return error_response("Var name is required", 400)

        if "var_value" not in data:
            return error_response("Var value is required", 400)
        var_name: str = data["var_name"]
        var_value: str = data["var_value"]

        SettingsMgr.update_by_name(var_name, var_value)
        return success_response(None, "Set variable successfully")
    except AdminException as e:
        return error_response(str(e), 400)
    except Exception as e:
        return error_response(str(e), 500)


@admin_bp.route("/variables", methods=["GET"])
@login_required
@check_admin_auth
def get_variable():
    try:
        if request.content_length is None or request.content_length == 0:
            # list variables
            res = list(SettingsMgr.get_all())
            return success_response(res)

        # get var
        data = request.get_json()
        if not data or "var_name" not in data:
            return error_response("Var name is required", 400)
        var_name: str = data["var_name"]
        res = SettingsMgr.get_by_name(var_name)
        return success_response(res)
    except AdminException as e:
        return error_response(str(e), 400)
    except Exception as e:
        return error_response(str(e), 500)


@admin_bp.route("/configs", methods=["GET"])
@login_required
@check_admin_auth
def get_config():
    try:
        res = list(ConfigMgr.get_all())
        return success_response(res)
    except AdminException as e:
        return error_response(str(e), 400)
    except Exception as e:
        return error_response(str(e), 500)


@admin_bp.route("/environments", methods=["GET"])
@login_required
@check_admin_auth
def get_environments():
    try:
        res = list(EnvironmentsMgr.get_all())
        return success_response(res)
    except AdminException as e:
        return error_response(str(e), 400)
    except Exception as e:
        return error_response(str(e), 500)


@admin_bp.route("/users/<username>/keys", methods=["POST"])
@login_required
@check_admin_auth
def generate_user_api_key(username: str) -> tuple[Response, int]:
    try:
        user_details: list[dict[str, Any]] = UserMgr.get_user_details(username)
        if not user_details:
            return error_response("User not found!", 404)
        tenants: list[dict[str, Any]] = UserServiceMgr.get_user_tenants(username)
        if not tenants:
            return error_response("Tenant not found!", 404)
        tenant_id: str = tenants[0]["tenant_id"]
        key: str = generate_confirmation_token()
        obj: dict[str, Any] = {
            "tenant_id": tenant_id,
            "token": key,
            "beta": generate_confirmation_token().replace("ragflow-", "")[:32],
            "create_time": current_timestamp(),
            "create_date": datetime_format(datetime.now()),
            "update_time": None,
            "update_date": None,
        }

        if not UserMgr.save_api_key(obj):
            return error_response("Failed to generate API key!", 500)
        return success_response(obj, "API key generated successfully")
    except AdminException as e:
        return error_response(e.message, e.code)
    except Exception as e:
        return error_response(str(e), 500)


@admin_bp.route("/users/<username>/keys", methods=["GET"])
@login_required
@check_admin_auth
def get_user_api_keys(username: str) -> tuple[Response, int]:
    try:
        api_keys: list[dict[str, Any]] = UserMgr.get_user_api_key(username)
        return success_response(api_keys, "Get user API keys")
    except AdminException as e:
        return error_response(e.message, e.code)
    except Exception as e:
        return error_response(str(e), 500)


@admin_bp.route("/users/<username>/keys/<key>", methods=["DELETE"])
@login_required
@check_admin_auth
def delete_user_api_key(username: str, key: str) -> tuple[Response, int]:
    try:
        deleted = UserMgr.delete_api_key(username, key)
        if deleted:
            return success_response(None, "API key deleted successfully")
        else:
            return error_response("API key not found or could not be deleted", 404)
    except AdminException as e:
        return error_response(e.message, e.code)
    except Exception as e:
        return error_response(str(e), 500)


@admin_bp.route("/version", methods=["GET"])
@login_required
@check_admin_auth
def show_version():
    try:
        res = {"version": get_ragflow_version()}
        return success_response(res)
    except Exception as e:
        return error_response(str(e), 500)


@admin_bp.route("/sandbox/providers", methods=["GET"])
@login_required
@check_admin_auth
def list_sandbox_providers():
    """List all available sandbox providers."""
    try:
        res = SandboxMgr.list_providers()
        return success_response(res)
    except AdminException as e:
        return error_response(str(e), 400)
    except Exception as e:
        return error_response(str(e), 500)


@admin_bp.route("/sandbox/providers/<provider_id>/schema", methods=["GET"])
@login_required
@check_admin_auth
def get_sandbox_provider_schema(provider_id: str):
    """Get configuration schema for a specific provider."""
    try:
        res = SandboxMgr.get_provider_config_schema(provider_id)
        return success_response(res)
    except AdminException as e:
        return error_response(str(e), 400)
    except Exception as e:
        return error_response(str(e), 500)


@admin_bp.route("/sandbox/config", methods=["GET"])
@login_required
@check_admin_auth
def get_sandbox_config():
    """Get current sandbox configuration."""
    try:
        res = SandboxMgr.get_config()
        return success_response(res)
    except AdminException as e:
        return error_response(str(e), 400)
    except Exception as e:
        return error_response(str(e), 500)


@admin_bp.route("/sandbox/config", methods=["POST"])
@login_required
@check_admin_auth
def set_sandbox_config():
    """Set sandbox provider configuration."""
    try:
        data = request.get_json()
        if not data:
            logging.error("set_sandbox_config: Request body is required")
            return error_response("Request body is required", 400)

        provider_type = data.get("provider_type")
        if not provider_type:
            logging.error("set_sandbox_config: provider_type is required")
            return error_response("provider_type is required", 400)

        config = data.get("config", {})
        set_active = data.get("set_active", True)  # Default to True for backward compatibility

        logging.info(f"set_sandbox_config: provider_type={provider_type}, set_active={set_active}")
        logging.info(f"set_sandbox_config: config keys={list(config.keys())}")

        res = SandboxMgr.set_config(provider_type, config, set_active)
        return success_response(res, "Sandbox configuration updated successfully")
    except AdminException as e:
        logging.exception("set_sandbox_config AdminException")
        return error_response(str(e), 400)
    except Exception as e:
        logging.exception("set_sandbox_config unexpected error")
        return error_response(str(e), 500)


@admin_bp.route("/sandbox/test", methods=["POST"])
@login_required
@check_admin_auth
def test_sandbox_connection():
    """Test connection to sandbox provider."""
    try:
        data = request.get_json()
        if not data:
            return error_response("Request body is required", 400)

        provider_type = data.get("provider_type")
        if not provider_type:
            return error_response("provider_type is required", 400)

        config = data.get("config", {})
        res = SandboxMgr.test_connection(provider_type, config)
        return success_response(res)
    except AdminException as e:
        return error_response(str(e), 400)
    except Exception as e:
        return error_response(str(e), 500)


@admin_bp.route("/log_levels", methods=["GET"])
@login_required
@check_admin_auth
def get_logger_levels():
    """Get current log levels for all packages."""
    try:
        res = get_log_levels()
        return success_response(res, "Get log levels", 0)
    except Exception as e:
        return error_response(str(e), 500)


@admin_bp.route("/log_levels", methods=["PUT"])
@login_required
@check_admin_auth
def set_logger_level():
    """Set log level for a package."""
    try:
        data = request.get_json()
        if not data or "pkg_name" not in data or "level" not in data:
            return error_response("pkg_name and level are required", 400)

        pkg_name = data["pkg_name"]
        level = data["level"]
        if not isinstance(pkg_name, str) or not isinstance(level, str):
            return error_response("pkg_name and level must be strings", 400)

        success = set_log_level(pkg_name, level)
        if success:
            return success_response({"pkg_name": pkg_name, "level": level}, "Log level updated successfully")
        else:
            return error_response(f"Invalid log level: {level}", 400)
    except Exception as e:
        return error_response(str(e), 500)


@admin_bp.route("/referrals", methods=["GET"])
@login_required
@check_admin_auth
def get_referral_activity():
    try:
        page = int(request.args.get("page", 1))
        size = int(request.args.get("size", 30))
        search = request.args.get("search", "")

        res = ReferralMgr.get_referral_activity(page=page, size=size, search_query=search)
        return success_response(res)
    except Exception as e:
        return error_response(str(e), 500)


@admin_bp.route("/licenses", methods=["GET"])
@login_required
@check_admin_auth
def get_licenses():
    try:
        page = int(request.args.get("page", 1))
        size = int(request.args.get("size", 10))
        search = request.args.get("search", "")

        res = LicenseMgr.get_all_licenses(page=page, size=size, search=search)
        return success_response(res)
    except Exception as e:
        return error_response(str(e), 500)


@admin_bp.route("/licenses", methods=["POST"])
@login_required
@check_admin_auth
def issue_license():
    try:
        data = request.get_json()
        if not data or "user_email" not in data or "name" not in data or "duration_months" not in data:
            return error_response("user_email, name, and duration_months are required", 400)

        user_email = data["user_email"]
        name = data["name"]
        duration_months = int(data["duration_months"])

        res = LicenseMgr.issue_license(user_email, name, duration_months)
        return success_response(res)
    except AdminException as e:
        return error_response(e.message, e.code)
    except Exception as e:
        return error_response(str(e), 500)


@admin_bp.route("/licenses/<license_id>", methods=["DELETE"])
@login_required
@check_admin_auth
def revoke_license(license_id):
    try:
        res = LicenseMgr.revoke_license(license_id)
        return success_response(res)
    except AdminException as e:
        return error_response(e.message, e.code)
    except Exception as e:
        return error_response(str(e), 500)


@admin_bp.route("/licenses/pricing", methods=["GET"])
@login_required
@check_admin_auth
def get_license_pricing():
    try:
        res = LicenseMgr.get_pricing()
        return success_response(res)
    except Exception as e:
        return error_response(str(e), 500)


@admin_bp.route("/licenses/pricing", methods=["POST"])
@login_required
@check_admin_auth
def update_license_pricing():
    try:
        data = request.get_json()
        if not data:
            return error_response("Pricing configuration data is required", 400)
        res = LicenseMgr.update_pricing(data)
        return success_response(res)
    except AdminException as e:
        return error_response(e.message, e.code)
    except Exception as e:
        return error_response(str(e), 500)


@admin_bp.route("/onboarding/stats", methods=["GET"])
@login_required
@check_admin_auth
def get_onboarding_stats():
    try:
        from api.db.db_models import User
        import json

        total_users = User.select().count()
        completed_count = 0
        skipped_count = 0

        goal_counts = {}
        role_counts = {}
        team_size_counts = {}
        industry_counts = {}

        users_with_info = User.select().where(User.onboarding_info.is_null(False))
        for u in users_with_info:
            if not u.onboarding_info:
                continue
            try:
                raw_info = json.loads(u.onboarding_info) if isinstance(u.onboarding_info, str) else u.onboarding_info
                info = raw_info.get("data", raw_info) if isinstance(raw_info, dict) else {}
                if isinstance(info, dict):
                    if info.get("skipped"):
                        skipped_count += 1
                    else:
                        completed_count += 1
                        goal = info.get("purpose") or info.get("reason") or info.get("goal")
                        if goal:
                            goal_counts[goal] = goal_counts.get(goal, 0) + 1
                        if info.get("role"):
                            role_counts[info["role"]] = role_counts.get(info["role"], 0) + 1
                        if info.get("team_size"):
                            team_size_counts[info["team_size"]] = team_size_counts.get(info["team_size"], 0) + 1
                        industry = info.get("industry") or info.get("company_type")
                        if industry:
                            industry_counts[industry] = industry_counts.get(industry, 0) + 1
            except Exception:
                pass

        completion_rate = round((completed_count / total_users * 100)) if total_users > 0 else 0

        res = {
            "total_users": total_users,
            "completed_count": completed_count,
            "skipped_count": skipped_count,
            "completion_rate": completion_rate,
            "goals": goal_counts,
            "reasons": goal_counts,
            "roles": role_counts,
            "team_sizes": team_size_counts,
            "company_types": industry_counts,
            "industries": industry_counts,
        }
        return success_response(res)
    except Exception as e:
        return error_response(str(e), 500)


# =============================================================================
# Payment Ledger, Analytics & Reconciliation Endpoints (Admin Service)
# =============================================================================

@admin_bp.route("/payments/transactions", methods=["GET"])
@login_required
@check_admin_auth
def get_payment_transactions():
    """Query paginated payment transactions with multi-field filters."""
    try:
        from api.db.services.payment_transaction_service import PaymentTransactionService
        page = int(request.args.get("page", 1))
        size = int(request.args.get("size", 20))
        status = request.args.get("status")
        plan_type = request.args.get("plan_type")
        email = request.args.get("email")
        search = request.args.get("search")
        date_from = request.args.get("date_from")
        date_to = request.args.get("date_to")

        res = PaymentTransactionService.get_transactions_paginated(
            page=page,
            page_size=size,
            status=status if status and status != "ALL" else None,
            plan_type=plan_type if plan_type and plan_type != "ALL" else None,
            email=email,
            search=search,
            date_from=date_from,
            date_to=date_to,
        )
        return success_response(res)
    except Exception as e:
        logging.exception(f"Error fetching payment transactions: {e}")
        return error_response(str(e), 500)


@admin_bp.route("/payments/summary", methods=["GET"])
@admin_bp.route("/payments/analytics", methods=["GET"])
@login_required
@check_admin_auth
def get_payment_summary():
    """Calculate financial KPIs and checkout conversion summary."""
    try:
        from api.db.services.payment_transaction_service import PaymentTransactionService
        summary = PaymentTransactionService.get_analytics_summary()
        return success_response(summary)
    except Exception as e:
        logging.exception(f"Error fetching payment summary: {e}")
        return error_response(str(e), 500)


@admin_bp.route("/payments/reconcile", methods=["POST"])
@login_required
@check_admin_auth
def admin_reconcile_payment():
    """Manual reconciliation action on payment transaction by superuser."""
    try:
        from api.db.db_models import DB, PaymentTransaction, Tenant
        from api.db.services.payment_transaction_service import PaymentTransactionService
        from api.db.services.user_service import TenantService
        from common.time_utils import datetime_format

        req = request.get_json() or {}
        transaction_id = str(req.get("transaction_id", "")).strip()
        action = str(req.get("action", "")).strip()
        paid_amount_uzs = req.get("paid_amount_uzs")
        audit_note = str(req.get("audit_note", "")).strip()

        if not transaction_id or not action:
            return error_response("transaction_id and action are required", 400)

        tx = PaymentTransactionService.get_by_tx_id(transaction_id)
        if not tx:
            return error_response(f"Transaction {transaction_id} not found", 404)

        admin_email = getattr(current_user, "email", "admin")
        admin_note = f"Manual admin reconciliation by {admin_email}: {audit_note}".strip()

        with DB.connection_context(), DB.atomic():
            if action == "mark_paid":
                amount = int(paid_amount_uzs) if paid_amount_uzs is not None else tx.expected_amount_uzs
                updated_tx = PaymentTransactionService.mark_paid(
                    transaction_id=transaction_id,
                    paid_amount_uzs=amount,
                    audit_note=admin_note,
                )
                if tx.user_id:
                    from datetime import timedelta
                    months = max(1, int(tx.duration_months or 1))
                    expiry_date = datetime.now() + timedelta(days=months * 30)
                    credits = 5000 * months if tx.plan_type == "plus" else (10000 * months if tx.plan_type == "pro" else 999999 * months)
                    TenantService.update_by_id(
                        tx.user_id,
                        {
                            "plan_type": tx.plan_type,
                            "plan_expiry_date": datetime_format(expiry_date),
                            "credit": credits,
                        }
                    )
                return success_response({
                    "success": True,
                    "downgraded": False,
                    "transaction": updated_tx.to_dict() if updated_tx else None
                })

            elif action == "mark_failed":
                updated_tx = PaymentTransactionService.mark_failed(
                    transaction_id=transaction_id,
                    error_code=req.get("error_code") or "MANUAL_REVOKED",
                    error_message=audit_note or "Revoked by admin during reconciliation",
                    audit_note=admin_note,
                )

                # Check if tenant has any OTHER active confirmed PAID transaction
                other_active_paid = PaymentTransaction.select().where(
                    (PaymentTransaction.user_id == tx.user_id) &
                    (PaymentTransaction.id != tx.id) &
                    (PaymentTransaction.status == "PAID")
                ).order_by(PaymentTransaction.create_date.desc()).first()

                downgraded = False
                warning_message = None

                if other_active_paid and not req.get("force_downgrade", False):
                    warning_message = (
                        f"Transaction #{transaction_id} marked as FAILED in ledger. Tenant '{tx.account_email}' was NOT "
                        f"downgraded because account has another confirmed PAID transaction (#{other_active_paid.transaction_id}, plan: {other_active_paid.plan_type})."
                    )
                elif tx.user_id:
                    default_credit = Tenant.credit.default if hasattr(Tenant.credit, 'default') and Tenant.credit.default is not None else 512
                    TenantService.update_by_id(
                        tx.user_id,
                        {
                            "plan_type": "free",
                            "plan_expiry_date": None,
                            "credit": default_credit,
                        }
                    )
                    downgraded = True

                # Revoke self-hosted license key if applicable (raises on DB failure inside atomic block)
                if tx.plan_type == "license":
                    from api.db.db_models import LicenseKey
                    LicenseKey.update(status="revoked").where(
                        (LicenseKey.payment_id == transaction_id) | (LicenseKey.user_id == tx.user_id)
                    ).execute()

                return success_response({
                    "success": True,
                    "downgraded": downgraded,
                    "warning": warning_message,
                    "transaction": updated_tx.to_dict() if updated_tx else None
                })

            elif action == "set_audit_note":
                PaymentTransaction.update(audit_note=admin_note).where(PaymentTransaction.transaction_id == transaction_id).execute()
                updated_tx = PaymentTransactionService.get_by_tx_id(transaction_id)
                return success_response({
                    "success": True,
                    "downgraded": False,
                    "transaction": updated_tx.to_dict() if updated_tx else None
                })

            else:
                return error_response(f"Unknown action '{action}'. Valid actions: mark_paid, mark_failed, set_audit_note.", 400)

    except Exception as e:
        logging.exception(f"Error in admin_reconcile_payment: {e}")
        return error_response(str(e), 500)


