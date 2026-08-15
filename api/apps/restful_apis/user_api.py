#
#  Copyright 2024 The InfiniFlow Authors. All Rights Reserved.
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
import asyncio
import logging
import string
import os
import re
import secrets
import time
from datetime import datetime
import base64

from quart import make_response, redirect, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from api.apps.auth import get_auth_client
from api.db import FileType, UserTenantRole
from api.db.db_models import Lead
from api.db.services.file_service import FileService
from api.db.services.user_service import TenantService, UserService, UserTenantService
from api.db.services.lead_service import LeadService
from common.time_utils import current_timestamp, datetime_format, get_format_time
from common.misc_utils import download_img, get_uuid
from common.constants import RetCode
from common.connection_utils import construct_response
from api.utils.api_utils import (
    get_data_error_result,
    get_json_result,
    get_request_json,
    server_error_response,
    validate_request,
)
from api.utils.nickname_validation import validate_nickname
from api.utils.crypt import decrypt
from rag.utils.redis_conn import REDIS_CONN
from api.apps import login_required, current_user, login_user, logout_user
from api.utils.web_utils import (
    send_email_html,
    dispatch_email_bg,
    OTP_LENGTH,
    OTP_TTL_SECONDS,
    ATTEMPT_LIMIT,
    ATTEMPT_LOCK_SECONDS,
    RESEND_COOLDOWN_SECONDS,
    otp_keys,
    activation_keys,
    hash_code,
    captcha_key,
)
from common import settings


@manager.route("/auth/login", methods=["POST"])  # noqa: F821
async def login():
    """
    User login endpoint.
    ---
    tags:
      - User
    parameters:
      - in: body
        name: body
        description: Login credentials.
        required: true
        schema:
          type: object
          properties:
            email:
              type: string
              description: User email.
            password:
              type: string
              description: User password.
    responses:
      200:
        description: Login successful.
        schema:
          type: object
      401:
        description: Authentication failed.
        schema:
          type: object
    """
    json_body = await get_request_json()
    if not json_body:
        logging.warning("Login failed: invalid or empty JSON body")
        return get_json_result(data=False, code=RetCode.AUTHENTICATION_ERROR, message="Unauthorized!")

    email = json_body.get("email", "")

    users = UserService.query(email=email)
    if not users:
        logging.warning("Login failed: email not registered")
        return get_json_result(
            data=False,
            code=RetCode.AUTHENTICATION_ERROR,
            message=f"Email: {email} is not registered!",
        )

    password = json_body.get("password")
    try:
        password = decrypt(password)
    except BaseException:
        logging.warning("Login failed: password decryption error")
        return get_json_result(data=False, code=RetCode.SERVER_ERROR, message="Fail to crypt password")

    user = UserService.query_user(email, password)

    if user and hasattr(user, "is_active") and user.is_active == "0":
        logging.warning("Login failed: unactivated or disabled account for user_id=%s", user.id)
        return get_json_result(
            data={"email": email, "requires_activation": True},
            code=RetCode.FORBIDDEN,
            message="Your account is not activated yet. Please enter the 6-digit code sent to your email.",
        )
    elif user:
        user.access_token = get_uuid()
        login_user(user)
        user.last_login_time = get_format_time()
        user.update_time = current_timestamp()
        user.update_date = datetime_format(datetime.now())
        user.save()
        logging.info("Login successful: user_id=%s", user.id)
        msg = "Welcome back!"

        return await construct_response(data=user.to_safe_dict(for_self=True), auth=user.get_id(), message=msg)
    else:
        logging.warning("Login failed: wrong credentials")
        return get_json_result(
            data=False,
            code=RetCode.AUTHENTICATION_ERROR,
            message="Email and password do not match!",
        )


def get_oauth_config(channel: str, host_url: str = ""):
    channel = channel.lower()
    oauth_conf = getattr(settings, "OAUTH_CONFIG", {}) or {}
    config = oauth_conf.get(channel)
    if not config:
        from api.db.services.system_settings_service import SystemSettingsService
        def get_sys_val(key, env_key=""):
            try:
                objs = SystemSettingsService.get_by_name(key)
                if objs and objs[0].value:
                    return objs[0].value
            except Exception:
                pass
            return os.environ.get(env_key or key.upper().replace(".", "_"), "")

        client_id = get_sys_val(f"oauth.{channel}.client_id", f"{channel.upper()}_CLIENT_ID")
        client_secret = get_sys_val(f"oauth.{channel}.client_secret", f"{channel.upper()}_CLIENT_SECRET")
        if client_id and client_secret:
            config = {
                "channel": channel,
                "client_id": client_id,
                "client_secret": client_secret,
                "display_name": channel.capitalize(),
                "icon": channel,
            }
            if channel == "google":
                config.update({
                    "type": "google",
                    "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth",
                    "token_url": "https://oauth2.googleapis.com/token",
                    "userinfo_url": "https://www.googleapis.com/oauth2/v3/userinfo",
                    "scope": "openid email profile"
                })
            elif channel == "github":
                config.update({
                    "type": "github",
                    "authorization_url": "https://github.com/login/oauth/authorize",
                    "token_url": "https://github.com/login/oauth/access_token",
                    "userinfo_url": "https://api.github.com/user",
                    "scope": "user:email"
                })

    if config:
        config = dict(config)
        config["channel"] = channel
        if not config.get("redirect_uri") and host_url:
            config["redirect_uri"] = f"{host_url.rstrip('/')}/v1/user/oauth/callback/{channel}"
    return config


@manager.route("/auth/login/channels", methods=["GET"])  # noqa: F821
@manager.route("/oauth/channels", methods=["GET"])  # noqa: F821
async def get_login_channels():
    try:
        channels = []
        oauth_conf = getattr(settings, "OAUTH_CONFIG", {}) or {}
        configured_channels = dict(oauth_conf)

        for ch in ["google", "github"]:
            if ch not in configured_channels:
                cfg = get_oauth_config(ch)
                if cfg and cfg.get("client_id"):
                    configured_channels[ch] = cfg

        for channel, config in configured_channels.items():
            channels.append(
                {
                    "channel": channel,
                    "display_name": config.get("display_name", channel.title()),
                    "icon": config.get("icon", channel),
                }
            )
        return get_json_result(data=channels)
    except Exception as e:
        logging.exception(e)
        return get_json_result(data=[], message=f"Load channels failure, error: {str(e)}", code=RetCode.EXCEPTION_ERROR)


@manager.route("/auth/login/<channel>", methods=["GET"])  # noqa: F821
@manager.route("/oauth/<channel>", methods=["GET"])  # noqa: F821
@manager.route("/oauth/login/<channel>", methods=["GET"])  # noqa: F821
@manager.route("/oauth/<channel>/start", methods=["GET"])  # noqa: F821
async def oauth_login(channel):
    host_url = request.host_url
    channel_config = get_oauth_config(channel, host_url)
    if not channel_config or not channel_config.get("client_id"):
        return get_json_result(
            data=False,
            message=f"OAuth channel '{channel}' is not configured on this server.",
            code=RetCode.ARGUMENT_ERROR,
        )
    auth_cli = get_auth_client(channel_config)

    state = get_uuid()
    session["oauth_state"] = state
    auth_url = auth_cli.get_authorization_url(state)
    logging.info("OAuth login initiated: channel='%s', state='%s', url='%s'", channel, state, auth_url)
    return redirect(auth_url)


@manager.route("/auth/oauth/<channel>/callback", methods=["GET"])  # noqa: F821
@manager.route("/oauth/callback/<channel>", methods=["GET"])  # noqa: F821
@manager.route("/oauth/<channel>/callback", methods=["GET"])  # noqa: F821
@manager.route("/oauth/<channel>/auth/callback", methods=["GET"])  # noqa: F821
async def oauth_callback(channel):
    """
    Handle the OAuth/OIDC callback for Google, GitHub, and other channels dynamically.
    """
    try:
        host_url = request.host_url
        channel_config = get_oauth_config(channel, host_url)
        if not channel_config or not channel_config.get("client_id"):
            return redirect(f"/?error=oauth_not_configured_{channel}")
        auth_cli = get_auth_client(channel_config)

        state = request.args.get("state")
        session.pop("oauth_state", None)

        code = request.args.get("code")
        if not code:
            return redirect("/?error=missing_code")

        if hasattr(auth_cli, "async_exchange_code_for_token"):
            token_info = await auth_cli.async_exchange_code_for_token(code)
        else:
            token_info = auth_cli.exchange_code_for_token(code)
        access_token = token_info.get("access_token")
        if not access_token:
            return redirect("/?error=token_failed")

        id_token = token_info.get("id_token")

        if hasattr(auth_cli, "async_fetch_user_info"):
            user_info = await auth_cli.async_fetch_user_info(access_token, id_token=id_token)
        else:
            user_info = auth_cli.fetch_user_info(access_token, id_token=id_token)

        if not user_info or not user_info.email:
            return redirect("/?error=email_missing")

        users = UserService.query(email=user_info.email)
        user_id = get_uuid()

        if not users:
            try:
                try:
                    avatar = await download_img(user_info.avatar_url) if user_info.avatar_url else ""
                except Exception as e:
                    logging.exception(e)
                    avatar = ""

                users = user_register(
                    user_id,
                    {
                        "access_token": get_uuid(),
                        "email": user_info.email,
                        "avatar": avatar,
                        "nickname": user_info.nickname or user_info.email.split("@")[0],
                        "login_channel": channel,
                        "last_login_time": get_format_time(),
                        "is_superuser": False,
                    },
                )

                if not users:
                    raise Exception(f"Failed to register {user_info.email}")
                if len(users) > 1:
                    raise Exception(f"Same email: {user_info.email} exists!")

                user = users[0]
                login_user(user)
                return redirect(f"/?auth={user.get_id()}")

            except Exception as e:
                rollback_user_registration(user_id)
                logging.exception(e)
                return redirect(f"/?error={str(e)}")

        user = users[0]
        user.access_token = get_uuid()
        if user and hasattr(user, "is_active") and user.is_active == "0":
            return redirect("/?error=user_inactive")

        login_user(user)
        user.save()
        return redirect(f"/?auth={user.get_id()}")
    except Exception as e:
        logging.exception(e)
        return redirect(f"/?error={str(e)}")


@manager.route("/auth/logout", methods=["POST"])  # noqa: F821
@login_required
async def log_out():
    """
    User logout endpoint.
    ---
    tags:
      - User
    security:
      - ApiKeyAuth: []
    responses:
      200:
        description: Logout successful.
        schema:
          type: object
    """
    user = current_user._get_current_object() if hasattr(current_user, "_get_current_object") else current_user
    user_id = user.id
    user.access_token = f"INVALID_{secrets.token_hex(16)}"
    saved = user.save()
    if saved == 0:
        logging.error("Logout failed to persist access token update: user_id=%s", user_id)
        return get_json_result(code=RetCode.SERVER_ERROR, data=False, message="Failed to update access token")
    logout_user()
    logging.info("Logout: user_id=%s, access_token invalidated", user_id)
    return get_json_result(data=True)


@manager.route("/users/me", methods=["PATCH"])  # noqa: F821
@login_required
async def setting_user():
    """
    Update user settings.
    ---
    tags:
      - User
    security:
      - ApiKeyAuth: []
    parameters:
      - in: body
        name: body
        description: User settings to update.
        required: true
        schema:
          type: object
          properties:
            nickname:
              type: string
              description: New nickname.
            email:
              type: string
              description: New email.
    responses:
      200:
        description: Settings updated successfully.
        schema:
          type: object
    """
    update_dict = {}
    request_data = await get_request_json()
    password_changed = False
    if request_data.get("password"):
        new_password = request_data.get("new_password")
        if not check_password_hash(current_user.password, decrypt(request_data["password"])):
            return get_json_result(
                data=False,
                code=RetCode.AUTHENTICATION_ERROR,
                message="Password error!",
            )

        if new_password:
            update_dict["password"] = generate_password_hash(decrypt(new_password))
            update_dict["access_token"] = f"INVALID_{secrets.token_hex(16)}"
            password_changed = True

    for k in request_data.keys():
        if k in [
            "password",
            "new_password",
            "email",
            "status",
            "is_superuser",
            "login_channel",
            "is_anonymous",
            "is_active",
            "is_authenticated",
            "last_login_time",
        ]:
            continue
        update_dict[k] = request_data[k]

    if "nickname" in update_dict:
        error_message, error_code = validate_nickname(update_dict["nickname"])
        if error_message:
            return get_json_result(data=False, message=error_message, code=error_code)
        update_dict["nickname"] = update_dict["nickname"].strip()

    try:
        UserService.update_by_id(current_user.id, update_dict)
        if password_changed:
            logout_user()
        return get_json_result(data=True)
    except Exception as e:
        logging.exception(e)
        return get_json_result(data=False, message="Update failure!", code=RetCode.EXCEPTION_ERROR)


@manager.route("/users/me", methods=["DELETE"])  # noqa: F821
@login_required
async def delete_user():
    """
    Deactivate user account (soft delete).
    ---
    tags:
      - User
    security:
      - ApiKeyAuth: []
    responses:
      200:
        description: Account deactivated successfully.
        schema:
          type: object
    """
    try:
        # Set is_active to "0" and status to "0" to deactivate the account while keeping data
        update_dict = {
            "is_active": "0",
            "status": "0",
            "access_token": f"DEACTIVATED_{secrets.token_hex(16)}"
        }
        UserService.update_by_id(current_user.id, update_dict)
        logout_user()
        return get_json_result(data=True)
    except Exception as e:
        logging.exception(e)
        return get_json_result(data=False, message="Deactivation failure!", code=RetCode.EXCEPTION_ERROR)


@manager.route("/users/me", methods=["GET"])  # noqa: F821
@login_required
async def user_profile():
    """
    Get user profile information.
    ---
    tags:
      - User
    security:
      - ApiKeyAuth: []
    responses:
      200:
        description: User profile retrieved successfully.
        schema:
          type: object
          properties:
            id:
              type: string
              description: User ID.
            nickname:
              type: string
              description: User nickname.
            email:
              type: string
              description: User email.
    """
    return get_json_result(data=current_user.to_safe_dict(for_self=True))


@manager.route("/users/me/onboarding", methods=["POST"])  # noqa: F821
@login_required
async def save_onboarding_responses():
    """
    Save user onboarding survey choices.
    """
    req = await get_request_json()
    try:
        update_dict = {
            "is_onboarded": True,
            "onboarding_info": json.dumps(req) if isinstance(req, dict) else str(req),
        }
        UserService.update_by_id(current_user.id, update_dict)
        return get_json_result(data=True, message="Onboarding responses saved successfully.")
    except Exception as e:
        logging.exception(e)
        return get_json_result(
            data=False,
            message=f"Failed to save onboarding survey: {str(e)}",
            code=RetCode.EXCEPTION_ERROR,
        )


@manager.route("/users/me/referrals", methods=["GET"])  # noqa: F821
@login_required
async def get_my_referrals():
    try:
        from api.db.services.user_service import UserService
        referrals = UserService.query(referred_by_id=current_user.id)
        data = []
        for u in referrals:
            email = u.email
            if email and "@" in email:
                name_part, domain_part = email.split("@", 1)
                if len(name_part) > 2:
                    masked_name = name_part[:2] + "***"
                else:
                    masked_name = name_part + "***"
                email = f"{masked_name}@{domain_part}"

            data.append({
                "email": email,
                "nickname": u.nickname,
                "created_at": datetime_format(u.create_date) if u.create_date else None,
            })
        return get_json_result(data=data)
    except Exception as e:
        logging.exception(e)
        return get_json_result(data=[], message="Failed to fetch referrals", code=RetCode.EXCEPTION_ERROR)


def rollback_user_registration(user_id):
    try:
        UserService.delete_by_id(user_id)
    except Exception:
        pass
    try:
        TenantService.delete_by_id(user_id)
    except Exception:
        pass
    try:
        u = UserTenantService.query(tenant_id=user_id)
        if u:
            UserTenantService.delete_by_id(u[0].id)
    except Exception:
        pass


def user_register(user_id, user):
    user["id"] = user_id
    user["is_superuser"] = False
    tenant = {
        "id": user_id,
        "name": user["nickname"] + "‘s Kingdom",
        "llm_id": settings.CHAT_MDL,
        "embd_id": settings.EMBEDDING_MDL,
        "asr_id": settings.ASR_MDL,
        "parser_ids": settings.PARSERS,
        "img2txt_id": settings.IMAGE2TEXT_MDL,
        "rerank_id": settings.RERANK_MDL,
        "plan_type": "free",
    }
    usr_tenant = {
        "tenant_id": user_id,
        "user_id": user_id,
        "invited_by": user_id,
        "role": UserTenantRole.NORMAL,
    }
    file_id = get_uuid()
    file = {
        "id": file_id,
        "parent_id": file_id,
        "tenant_id": user_id,
        "created_by": user_id,
        "name": "/",
        "type": FileType.FOLDER.value,
        "size": 0,
        "location": "",
    }

    # tenant_llm = get_init_tenant_llm(user_id)

    if not UserService.save(**user):
        return None
    TenantService.insert(**tenant)
    UserTenantService.insert(**usr_tenant)
    # TenantLLMService.insert_many(tenant_llm)
    FileService.insert(file)
    return UserService.query(email=user["email"])


@manager.route("/users", methods=["POST"])  # noqa: F821
@validate_request("nickname", "email", "password")
async def user_add():
    """
    Register a new user.
    ---
    tags:
      - User
    parameters:
      - in: body
        name: body
        description: Registration details.
        required: true
        schema:
          type: object
          properties:
            nickname:
              type: string
              description: User nickname.
            email:
              type: string
              description: User email.
            password:
              type: string
              description: User password.
    responses:
      200:
        description: Registration successful.
        schema:
          type: object
    """

    if not settings.REGISTER_ENABLED:
        return get_json_result(
            data=False,
            message="User registration is disabled!",
            code=RetCode.OPERATING_ERROR,
        )

    req = await get_request_json()
    email_address = req["email"]

    # Validate the email address
    if not re.match(r"^[\w\._-]+@([\w_-]+\.)+[\w-]{2,}$", email_address):
        return get_json_result(
            data=False,
            message=f"Invalid email address: {email_address}!",
            code=RetCode.OPERATING_ERROR,
        )

    # Check if the email address is already used
    if UserService.query(email=email_address):
        return get_json_result(
            data=False,
            message=f"Email: {email_address} has already registered!",
            code=RetCode.OPERATING_ERROR,
        )

    # Construct user info data
    nickname = req["nickname"]
    error_message, error_code = validate_nickname(nickname)
    if error_message:
        return get_json_result(data=False, message=error_message, code=error_code)
    nickname = nickname.strip()
    
    referred_by = req.get("referred_by_id")
    resolved_referrer_id = None
    if referred_by:
        # Check if nickname matches (e.g. SARDOR)
        referrers = UserService.query(nickname=referred_by)
        if not referrers:
            # Check if email matches
            referrers = UserService.query(email=referred_by)
        if not referrers:
            # Check if direct ID matches
            referrers = UserService.query(id=referred_by)
        if referrers:
            resolved_referrer_id = referrers[0].id


    raw_password = decrypt(req["password"])
    if not raw_password or len(raw_password) < 8:
        return get_json_result(
            data=False,
            message="Password must be at least 8 characters long!",
            code=RetCode.OPERATING_ERROR,
        )
    if not re.search(r"[A-Za-z]", raw_password) or not re.search(r"[0-9]", raw_password):
        return get_json_result(
            data=False,
            message="Password must contain at least one letter and one number!",
            code=RetCode.OPERATING_ERROR,
        )
    if raw_password.lower() in {"123456", "12345678", "123456789", "password", "qwerty", "12345", "1234567"}:
        return get_json_result(
            data=False,
            message="Password is too common and weak. Please choose a stronger password!",
            code=RetCode.OPERATING_ERROR,
        )

    user_dict = {
        "access_token": get_uuid(),
        "email": email_address,
        "nickname": nickname,
        "phone": req.get("phone"),
        "password": raw_password,
        "login_channel": "password",
        "last_login_time": get_format_time(),
        "is_superuser": False,
        "is_active": "0",
        "status": "0",
        "referred_by_id": resolved_referrer_id
    }

    user_id = get_uuid()
    try:
        users = user_register(user_id, user_dict)
        if not users:
            raise Exception(f"Fail to register {email_address}.")
        if len(users) > 1:
            raise Exception(f"Same email: {email_address} exists!")
        user = users[0]

        # Generate 6-digit numeric activation code
        code = "".join(secrets.choice(string.digits) for _ in range(6))
        salt = os.urandom(16)
        code_hash = hash_code(code, salt)

        k_code, k_attempts, k_last, k_lock = activation_keys(email_address)
        now = int(time.time())
        REDIS_CONN.set(k_code, f"{code_hash}:{salt.hex()}", OTP_TTL_SECONDS)
        REDIS_CONN.set(k_attempts, 0, OTP_TTL_SECONDS)
        REDIS_CONN.set(k_last, now, OTP_TTL_SECONDS)
        REDIS_CONN.delete(k_lock)

        # Dispatch activation email in non-blocking background thread
        dispatch_email_bg(
            to_email=email_address,
            subject="Activate Your Swipies AI Account",
            template_key="activation_code",
            code=code,
            nickname=nickname,
            ttl_min=OTP_TTL_SECONDS // 60,
        )

        return get_json_result(
            data={"email": email_address, "requires_activation": True},
            code=RetCode.SUCCESS,
            message="Registration successful! An activation code has been sent to your email address.",
        )
    except Exception as e:
        rollback_user_registration(user_id)
        logging.exception(e)
        return get_json_result(
            data=False,
            message=f"User registration failure, error: {str(e)}",
            code=RetCode.EXCEPTION_ERROR,
        )


@manager.route("/auth/activate", methods=["POST"])  # noqa: F821
async def activate_account():
    """
    POST /auth/activate
    Activate account using email and 6-digit activation code sent via email.
    """
    req = await get_request_json()
    email = (req.get("email") or "").strip().lower()
    code = (req.get("code") or "").strip()

    if not email or not code:
        return get_json_result(data=False, code=RetCode.ARGUMENT_ERROR, message="Email and activation code are required")

    users = UserService.query(email=email)
    if not users:
        return get_json_result(data=False, code=RetCode.DATA_ERROR, message="Account with this email does not exist")

    user = users[0]
    if hasattr(user, "is_active") and user.is_active == "1" and getattr(user, "status", "1") == "1":
        return get_json_result(data=True, code=RetCode.SUCCESS, message="Account is already activated! Please log in.")

    k_code, k_attempts, k_last, k_lock = activation_keys(email)
    if REDIS_CONN.get(k_lock):
        return get_json_result(data=False, code=RetCode.NOT_EFFECTIVE, message="Too many failed attempts. Please wait 30 minutes before trying again.")

    stored = REDIS_CONN.get(k_code)
    if not stored:
        return get_json_result(data=False, code=RetCode.NOT_EFFECTIVE, message="Activation code has expired or is invalid. Please request a new code.")

    try:
        stored_hash, salt_hex = str(stored).split(":", 1)
        salt = bytes.fromhex(salt_hex)
    except Exception:
        return get_json_result(data=False, code=RetCode.EXCEPTION_ERROR, message="Activation code verification failed")

    calc = hash_code(code, salt)
    if calc != stored_hash:
        try:
            attempts = int(REDIS_CONN.get(k_attempts) or 0) + 1
        except Exception:
            attempts = 1
        REDIS_CONN.set(k_attempts, attempts, OTP_TTL_SECONDS)
        if attempts >= ATTEMPT_LIMIT:
            REDIS_CONN.set(k_lock, int(time.time()), ATTEMPT_LOCK_SECONDS)
        return get_json_result(data=False, code=RetCode.AUTHENTICATION_ERROR, message="Invalid activation code.")

    # Success: consume activation keys & activate user
    REDIS_CONN.delete(k_code)
    REDIS_CONN.delete(k_attempts)
    REDIS_CONN.delete(k_last)
    REDIS_CONN.delete(k_lock)

    UserService.update_by_id(user.id, {"is_active": "1", "status": "1"})

    updated_users = UserService.query(email=email)
    if updated_users:
        user = updated_users[0]

    user.access_token = get_uuid()
    login_user(user)
    user.last_login_time = get_format_time()
    user.update_time = current_timestamp()
    user.update_date = datetime_format(datetime.now())
    user.save()

    logging.info("Account activated successfully for user_id=%s, email=%s", user.id, email)
    return await construct_response(
        data=user.to_safe_dict(for_self=True),
        auth=user.get_id(),
        message="Account activated successfully! Welcome to Swipies AI.",
    )


@manager.route("/auth/activate/resend", methods=["POST"])  # noqa: F821
async def resend_activation_code():
    """
    POST /auth/activate/resend
    Resend 6-digit activation code to user's email.
    """
    req = await get_request_json()
    email = (req.get("email") or "").strip().lower()

    if not email:
        return get_json_result(data=False, code=RetCode.ARGUMENT_ERROR, message="Email is required")

    users = UserService.query(email=email)
    if not users:
        return get_json_result(data=False, code=RetCode.DATA_ERROR, message="Account with this email does not exist")

    user = users[0]
    if hasattr(user, "is_active") and user.is_active == "1" and getattr(user, "status", "1") == "1":
        return get_json_result(data=True, code=RetCode.SUCCESS, message="Account is already activated!")

    k_code, k_attempts, k_last, k_lock = activation_keys(email)
    now = int(time.time())
    last_ts = REDIS_CONN.get(k_last)
    if last_ts:
        try:
            elapsed = now - int(last_ts)
        except Exception:
            elapsed = RESEND_COOLDOWN_SECONDS
        remaining = RESEND_COOLDOWN_SECONDS - elapsed
        if remaining > 0:
            return get_json_result(data=False, code=RetCode.NOT_EFFECTIVE, message=f"Please wait {remaining} seconds before resending code.")

    code = "".join(secrets.choice(string.digits) for _ in range(6))
    salt = os.urandom(16)
    code_hash = hash_code(code, salt)

    REDIS_CONN.set(k_code, f"{code_hash}:{salt.hex()}", OTP_TTL_SECONDS)
    REDIS_CONN.set(k_attempts, 0, OTP_TTL_SECONDS)
    REDIS_CONN.set(k_last, now, OTP_TTL_SECONDS)
    REDIS_CONN.delete(k_lock)

    # Dispatch activation email in non-blocking background thread
    dispatch_email_bg(
        to_email=email,
        subject="Activate Your Swipies AI Account",
        template_key="activation_code",
        code=code,
        nickname=user.nickname,
        ttl_min=OTP_TTL_SECONDS // 60,
    )

    return get_json_result(data=True, code=RetCode.SUCCESS, message="New activation code sent to your email.")


@manager.route("/users/me/models", methods=["GET"])  # noqa: F821
@login_required
async def tenant_info():
    """
    Get tenant information.
    ---
    tags:
      - Tenant
    security:
      - ApiKeyAuth: []
    responses:
      200:
        description: Tenant information retrieved successfully.
        schema:
          type: object
          properties:
            tenant_id:
              type: string
              description: Tenant ID.
            name:
              type: string
              description: Tenant name.
            llm_id:
              type: string
              description: LLM ID.
            embd_id:
              type: string
              description: Embedding model ID.
    """
    try:
        tenants = TenantService.get_info_by(current_user.id)
        if not tenants:
            return get_data_error_result(message="Tenant not found!")
        return get_json_result(data=tenants[0])
    except Exception as e:
        return server_error_response(e)


@manager.route("/users/me/models", methods=["PATCH"])  # noqa: F821
@login_required
@validate_request("tenant_id", "asr_id", "embd_id", "img2txt_id", "llm_id")
async def set_tenant_info():
    """
    Update tenant information.
    ---
    tags:
      - Tenant
    security:
      - ApiKeyAuth: []
    parameters:
      - in: body
        name: body
        description: Tenant information to update.
        required: true
        schema:
          type: object
          properties:
            tenant_id:
              type: string
              description: Tenant ID.
            llm_id:
              type: string
              description: LLM ID.
            embd_id:
              type: string
              description: Embedding model ID.
            asr_id:
              type: string
              description: ASR model ID.
            img2txt_id:
              type: string
              description: Image to Text model ID.
    responses:
      200:
        description: Tenant information updated successfully.
        schema:
          type: object
    """
    req = await get_request_json()
    try:
        tid = req.pop("tenant_id")

        TenantService.update_by_id(tid, req)
        return get_json_result(data=True)
    except Exception as e:
        return server_error_response(e)


@manager.route("/auth/password/forgot/captcha", methods=["POST"])  # noqa: F821
async def forget_get_captcha():
    """
    GET /forget/captcha?email=<email>
    - Generate an image captcha and cache it in Redis under key captcha:{email} with TTL = OTP_TTL_SECONDS.
    - Returns the captcha as a PNG image.
    """
    email = request.args.get("email") or ""
    if not email:
        return get_json_result(data=False, code=RetCode.ARGUMENT_ERROR, message="email is required")

    users = UserService.query(email=email)
    if not users:
        return get_json_result(data=False, code=RetCode.DATA_ERROR, message="invalid email")

    # Generate captcha text
    allowed = string.ascii_uppercase + string.digits
    captcha_text = "".join(secrets.choice(allowed) for _ in range(OTP_LENGTH))
    REDIS_CONN.set(captcha_key(email), captcha_text, 60)  # Valid for 60 seconds

    from captcha.image import ImageCaptcha

    image = ImageCaptcha(width=300, height=120, font_sizes=[50, 60, 70])
    img_bytes = image.generate(captcha_text).read()
    response = await make_response(img_bytes)
    response.headers.set("Content-Type", "image/JPEG")
    return response


@manager.route("/auth/password/forgot/otp", methods=["POST"])  # noqa: F821
async def forget_send_otp():
    """
    POST /forget/otp
    - Verify the image captcha stored at captcha:{email} (case-insensitive).
    - On success, generate an email OTP (A–Z with length = OTP_LENGTH), store hash + salt (and timestamp) in Redis with TTL, reset attempts and cooldown, and send the OTP via email.
    """
    req = await get_request_json()
    email = req.get("email") or ""
    captcha = (req.get("captcha") or "").strip()

    if not email or not captcha:
        return get_json_result(data=False, code=RetCode.ARGUMENT_ERROR, message="email and captcha required")

    users = UserService.query(email=email)
    if not users:
        return get_json_result(data=False, code=RetCode.DATA_ERROR, message="invalid email")

    stored_captcha = REDIS_CONN.get(captcha_key(email))
    if not stored_captcha:
        return get_json_result(data=False, code=RetCode.NOT_EFFECTIVE, message="invalid or expired captcha")
    if (stored_captcha or "").strip().lower() != captcha.lower():
        return get_json_result(data=False, code=RetCode.AUTHENTICATION_ERROR, message="invalid or expired captcha")

    # Delete captcha to prevent reuse
    REDIS_CONN.delete(captcha_key(email))

    k_code, k_attempts, k_last, k_lock = otp_keys(email)
    now = int(time.time())
    last_ts = REDIS_CONN.get(k_last)
    if last_ts:
        try:
            elapsed = now - int(last_ts)
        except Exception:
            elapsed = RESEND_COOLDOWN_SECONDS
        remaining = RESEND_COOLDOWN_SECONDS - elapsed
        if remaining > 0:
            return get_json_result(data=False, code=RetCode.NOT_EFFECTIVE, message=f"you still have to wait {remaining} seconds")

    # Generate OTP (uppercase letters only) and store hashed
    otp = "".join(secrets.choice(string.ascii_uppercase) for _ in range(OTP_LENGTH))
    salt = os.urandom(16)
    code_hash = hash_code(otp, salt)
    REDIS_CONN.set(k_code, f"{code_hash}:{salt.hex()}", OTP_TTL_SECONDS)
    REDIS_CONN.set(k_attempts, 0, OTP_TTL_SECONDS)
    REDIS_CONN.set(k_last, now, OTP_TTL_SECONDS)
    REDIS_CONN.delete(k_lock)

    ttl_min = OTP_TTL_SECONDS // 60

    try:
        await send_email_html(
            subject="Your Password Reset Code",
            to_email=email,
            template_key="reset_code",
            code=otp,
            ttl_min=ttl_min,
        )

    except Exception as e:
        logging.exception(e)
        return get_json_result(data=False, code=RetCode.SERVER_ERROR, message="failed to send email")

    return get_json_result(data=True, code=RetCode.SUCCESS, message="verification passed, email sent")


def _verified_key(email: str) -> str:
    return f"otp:verified:{email}"


@manager.route("/auth/password/forgot/otp/verify", methods=["POST"])  # noqa: F821
async def forget_verify_otp():
    """
    Verify email + OTP only. On success:
    - consume the OTP and attempt counters
    - set a short-lived verified flag in Redis for the email
    Request JSON: { email, otp }
    """
    req = await get_request_json()
    email = req.get("email") or ""
    otp = (req.get("otp") or "").strip()

    if not all([email, otp]):
        return get_json_result(data=False, code=RetCode.ARGUMENT_ERROR, message="email and otp are required")

    users = UserService.query(email=email)
    if not users:
        return get_json_result(data=False, code=RetCode.DATA_ERROR, message="invalid email")

    # Verify OTP from Redis
    k_code, k_attempts, k_last, k_lock = otp_keys(email)
    if REDIS_CONN.get(k_lock):
        return get_json_result(data=False, code=RetCode.NOT_EFFECTIVE, message="too many attempts, try later")

    stored = REDIS_CONN.get(k_code)
    if not stored:
        return get_json_result(data=False, code=RetCode.NOT_EFFECTIVE, message="expired otp")

    try:
        stored_hash, salt_hex = str(stored).split(":", 1)
        salt = bytes.fromhex(salt_hex)
    except Exception:
        return get_json_result(data=False, code=RetCode.EXCEPTION_ERROR, message="otp storage corrupted")

    calc = hash_code(otp.upper(), salt)
    if calc != stored_hash:
        # bump attempts
        try:
            attempts = int(REDIS_CONN.get(k_attempts) or 0) + 1
        except Exception:
            attempts = 1
        REDIS_CONN.set(k_attempts, attempts, OTP_TTL_SECONDS)
        if attempts >= ATTEMPT_LIMIT:
            REDIS_CONN.set(k_lock, int(time.time()), ATTEMPT_LOCK_SECONDS)
        return get_json_result(data=False, code=RetCode.AUTHENTICATION_ERROR, message="expired otp")

    # Success: consume OTP and attempts; mark verified
    REDIS_CONN.delete(k_code)
    REDIS_CONN.delete(k_attempts)
    REDIS_CONN.delete(k_last)
    REDIS_CONN.delete(k_lock)

    # set verified flag with limited TTL, reuse OTP_TTL_SECONDS or smaller window
    try:
        REDIS_CONN.set(_verified_key(email), "1", OTP_TTL_SECONDS)
    except Exception:
        return get_json_result(data=False, code=RetCode.SERVER_ERROR, message="failed to set verification state")

    return get_json_result(data=True, code=RetCode.SUCCESS, message="otp verified")


@manager.route("/auth/password/reset", methods=["POST"])  # noqa: F821
async def forget_reset_password():
    """
    Reset password after successful OTP verification.
    Requires: { email, new_password, confirm_new_password }
    Steps:
    - check verified flag in Redis
    - update user password
    - auto login
    - clear verified flag
    """

    req = await get_request_json()
    email = req.get("email") or ""
    new_pwd = req.get("new_password")
    new_pwd2 = req.get("confirm_new_password")

    if not all([email, new_pwd, new_pwd2]):
        return get_json_result(data=False, code=RetCode.ARGUMENT_ERROR, message="email and passwords are required")

    if not REDIS_CONN.get(_verified_key(email)):
        return get_json_result(data=False, code=RetCode.AUTHENTICATION_ERROR, message="email not verified")

    new_pwd_base64 = decrypt(new_pwd)
    new_pwd_string = base64.b64decode(new_pwd_base64).decode("utf-8")
    new_pwd2_string = base64.b64decode(decrypt(new_pwd2)).decode("utf-8")

    if new_pwd_string != new_pwd2_string:
        return get_json_result(data=False, code=RetCode.ARGUMENT_ERROR, message="passwords do not match")

    users = UserService.query_user_by_email(email=email)
    if not users:
        return get_json_result(data=False, code=RetCode.DATA_ERROR, message="invalid email")

    user = users[0]
    try:
        UserService.update_user_password(user.id, new_pwd_base64)
    except Exception as e:
        logging.exception(e)
        return get_json_result(data=False, code=RetCode.EXCEPTION_ERROR, message="failed to reset password")

    # clear verified flag
    try:
        REDIS_CONN.delete(_verified_key(email))
    except Exception:
        pass

    msg = "Password reset successful. Logged in."
    return await construct_response(data=user.to_safe_dict(for_self=True), auth=user.get_id(), message=msg)

@manager.route("/leads", methods=["POST"])
async def create_lead():
    req = await get_request_json()
    company = req.get("company", "")
    name = req.get("name", "")
    email = req.get("email", "")
    phone = req.get("phone", "")
    message = req.get("message", "")
    referral_code = req.get("referral_code", "")

    if not name or not email:
        return get_json_result(
            data=False,
            message="Name and email are required fields.",
            code=RetCode.OPERATING_ERROR,
        )

    # Save lead using insert to automatically generate ID and timestamps
    LeadService.insert(
        company=company,
        name=name,
        email=email,
        phone=phone,
        message=message,
        referral_code=referral_code,
        status="1"  # '1' represents unread
    )
    return get_json_result(data=True, message="Lead saved successfully")


@manager.route("/leads", methods=["GET"])
@login_required
def get_leads():
    if not current_user.is_superuser:
        return get_json_result(
            data=False,
            message="Unauthorized access",
            code=RetCode.AUTHENTICATION_ERROR,
        )
    # Get all leads, reverse-sorted by creation date
    leads = LeadService.query(order_by="create_time", reverse=True)
    return get_json_result(
        data=[lead.to_dict() for lead in leads]
    )


@manager.route("/leads/<lead_id>", methods=["PUT"])
@login_required
async def update_lead(lead_id):
    if not current_user.is_superuser:
        return get_json_result(
            data=False,
            message="Unauthorized access",
            code=RetCode.AUTHENTICATION_ERROR,
        )
    req = await get_request_json()
    status = req.get("status")

    lead = LeadService.query(id=lead_id)
    if not lead:
        return get_json_result(
            data=False,
            message="Lead not found.",
            code=RetCode.OPERATING_ERROR,
        )

    update_dict = {}
    if status is not None:
        update_dict["status"] = str(status)

    if update_dict:
        LeadService.update_by_id(lead_id, update_dict)

    return get_json_result(data=True, message="Lead updated successfully")


@manager.route("/leads/<lead_id>", methods=["DELETE"])
@login_required
def delete_lead(lead_id):
    if not current_user.is_superuser:
        return get_json_result(
            data=False,
            message="Unauthorized access",
            code=RetCode.AUTHENTICATION_ERROR,
        )
    lead = LeadService.query(id=lead_id)
    if not lead:
        return get_json_result(
            data=False,
            message="Lead not found.",
            code=RetCode.OPERATING_ERROR,
        )
    
    LeadService.filter_delete([Lead.id == lead_id])
    return get_json_result(data=True, message="Lead deleted successfully")


@manager.route("/admin/analytics/query", methods=["POST"])
@login_required
async def admin_analytics_query():
    if not current_user.is_superuser:
        return get_json_result(
            data=False,
            message="Unauthorized access",
            code=RetCode.AUTHENTICATION_ERROR,
        )
    
    req = await get_request_json()
    property_id = req.get("property_id")
    service_key_str = req.get("service_account_key")
    endpoint = req.get("endpoint", "runReport")
    payload = req.get("payload")
    
    if not property_id or not service_key_str or not payload:
        return get_json_result(
            data=False,
            message="Missing required parameters: property_id, service_account_key, and payload are required.",
            code=RetCode.ARGUMENT_ERROR
        )
        
    try:
        import json
        service_account_info = json.loads(service_key_str)
    except Exception:
        return get_json_result(
            data=False,
            message="Invalid Service Account JSON key format.",
            code=RetCode.ARGUMENT_ERROR
        )
        
    try:
        from google.oauth2 import service_account
        from google.auth.transport.requests import Request
        import requests
        
        credentials = service_account.Credentials.from_service_account_info(
            service_account_info,
            scopes=['https://www.googleapis.com/auth/analytics.readonly']
        )
        credentials.refresh(Request())
        access_token = credentials.token
        
        url = f"https://analyticsdata.googleapis.com/v1beta/properties/{property_id}:{endpoint}"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        
        if not response.ok:
            try:
                err_msg = response.json().get("error", {}).get("message", "Google Analytics API query failed.")
            except Exception:
                err_msg = response.text or "Google Analytics API query failed."
            return get_json_result(
                data=False,
                message=err_msg,
                code=RetCode.OPERATING_ERROR
            )
            
        return get_json_result(data=response.json())
        
    except Exception as e:
        logging.exception(e)
        return get_json_result(
            data=False,
            message=str(e),
            code=RetCode.EXCEPTION_ERROR
        )


@manager.route("/admin/yandex_analytics/query", methods=["POST"])
@login_required
async def admin_yandex_analytics_query():
    if not current_user.is_superuser:
        return get_json_result(
            data=False,
            message="Unauthorized access",
            code=RetCode.AUTHENTICATION_ERROR,
        )
    
    req = await get_request_json()
    counter_id = req.get("counter_id")
    oauth_token = req.get("oauth_token")
    params = req.get("params", {})
    
    if not counter_id or not oauth_token:
        return get_json_result(
            data=False,
            message="Missing required parameters: counter_id and oauth_token are required.",
            code=RetCode.ARGUMENT_ERROR
        )
        
    try:
        import requests
        
        url = "https://api-metrika.yandex.net/stat/v1/data"
        
        headers = {
            "Authorization": f"OAuth {oauth_token}",
            "Accept": "application/json"
        }
        
        query_params = dict(params)
        query_params["ids"] = counter_id
        
        response = requests.get(url, params=query_params, headers=headers, timeout=15)
        
        if not response.ok:
            try:
                err_msg = response.json().get("message", "Yandex Metrika API query failed.")
            except Exception:
                err_msg = response.text or "Yandex Metrika API query failed."
            return get_json_result(
                data=False,
                message=err_msg,
                code=RetCode.OPERATING_ERROR
            )
            
        return get_json_result(data=response.json())
        
    except Exception as e:
        logging.exception(e)
        return get_json_result(
            data=False,
            message=str(e),
            code=RetCode.EXCEPTION_ERROR
        )




