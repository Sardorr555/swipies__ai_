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
from datetime import datetime
from timeit import default_timer as timer

from quart import jsonify

from api.apps import login_required, current_user
from api.utils.api_utils import get_json_result, get_data_error_result, server_error_response, generate_confirmation_token
from api.utils.health_utils import run_health_checks, get_oceanbase_status
from common.versions import get_ragflow_version
from common.constants import RetCode
from common.time_utils import current_timestamp, datetime_format
from api.db.db_models import APIToken
from api.db.services.api_service import APITokenService
from api.db.services.knowledgebase_service import KnowledgebaseService
from api.db.services.user_service import UserTenantService
from common.log_utils import get_log_levels, set_log_level
from common import settings
from rag.utils.redis_conn import REDIS_CONN

@manager.route("/system/ping", methods=["GET"])  # noqa: F821
async def ping():
    return "pong", 200

@manager.route("/system/version", methods=["GET"])  # noqa: F821
def version():
    """
    Get the current version of the application.
    ---
    tags:
      - System
    security:
      - ApiKeyAuth: []
    responses:
      200:
        description: Version retrieved successfully.
        schema:
          type: object
          properties:
            version:
              type: string
              description: Version number.
    """
    return get_json_result(data=get_ragflow_version())


@manager.route("/system/status", methods=["GET"])  # noqa: F821
@login_required
def status():
    """
    Get the system status.
    ---
    tags:
      - System
    security:
      - ApiKeyAuth: []
    responses:
      200:
        description: System is operational.
        schema:
          type: object
          properties:
            es:
              type: object
              description: Elasticsearch status.
            storage:
              type: object
              description: Storage status.
            database:
              type: object
              description: Database status.
      503:
        description: Service unavailable.
        schema:
          type: object
          properties:
            error:
              type: string
              description: Error message.
    """
    res = {}
    st = timer()
    try:
        res["doc_engine"] = settings.docStoreConn.health()
        res["doc_engine"]["elapsed"] = "{:.1f}".format((timer() - st) * 1000.0)
    except Exception as e:
        res["doc_engine"] = {
            "type": "unknown",
            "status": "red",
            "elapsed": "{:.1f}".format((timer() - st) * 1000.0),
            "error": str(e),
        }

    st = timer()
    try:
        settings.STORAGE_IMPL.health()
        res["storage"] = {
            "storage": settings.STORAGE_IMPL_TYPE.lower(),
            "status": "green",
            "elapsed": "{:.1f}".format((timer() - st) * 1000.0),
        }
    except Exception as e:
        res["storage"] = {
            "storage": settings.STORAGE_IMPL_TYPE.lower(),
            "status": "red",
            "elapsed": "{:.1f}".format((timer() - st) * 1000.0),
            "error": str(e),
        }

    st = timer()
    try:
        KnowledgebaseService.get_by_id("x")
        res["database"] = {
            "database": settings.DATABASE_TYPE.lower(),
            "status": "green",
            "elapsed": "{:.1f}".format((timer() - st) * 1000.0),
        }
    except Exception as e:
        res["database"] = {
            "database": settings.DATABASE_TYPE.lower(),
            "status": "red",
            "elapsed": "{:.1f}".format((timer() - st) * 1000.0),
            "error": str(e),
        }

    st = timer()
    try:
        if not REDIS_CONN.health():
            raise Exception("Lost connection!")
        res["redis"] = {
            "status": "green",
            "elapsed": "{:.1f}".format((timer() - st) * 1000.0),
        }
    except Exception as e:
        res["redis"] = {
            "status": "red",
            "elapsed": "{:.1f}".format((timer() - st) * 1000.0),
            "error": str(e),
        }

    task_executor_heartbeats = {}
    try:
        task_executors = REDIS_CONN.smembers("TASKEXE")
        now = datetime.now().timestamp()
        for task_executor_id in task_executors:
            heartbeats = REDIS_CONN.zrangebyscore(task_executor_id, now - 60 * 30, now)
            heartbeats = [json.loads(heartbeat) for heartbeat in heartbeats]
            task_executor_heartbeats[task_executor_id] = heartbeats
    except Exception:
        logging.exception("get task executor heartbeats failed!")
    res["task_executor_heartbeats"] = task_executor_heartbeats

    return get_json_result(data=res)


@manager.route("/system/oceanbase/status", methods=["GET"])  # noqa: F821
@login_required
def oceanbase_status():
    """
    Get OceanBase health status and performance metrics.
    ---
    tags:
      - System
    security:
      - ApiKeyAuth: []
    responses:
      200:
        description: OceanBase status retrieved successfully.
        schema:
          type: object
          properties:
            status:
              type: string
              description: Status (alive/timeout).
            message:
              type: object
              description: Detailed status information including health and performance metrics.
    """
    try:
        status_info = get_oceanbase_status()
        return get_json_result(data=status_info)
    except Exception as e:
        return get_json_result(
            data={
                "status": "error",
                "message": f"Failed to get OceanBase status: {str(e)}"
            },
            code=500
        )


@manager.route("/system/config", methods=["GET"])  # noqa: F821
def get_config():
    """
    Get system configuration.
    ---
    tags:
        - System
    responses:
        200:
            description: Return system configuration
            schema:
                type: object
                properties:
                    registerEnable:
                        type: integer 0 means disabled, 1 means enabled
                        description: Whether user registration is enabled
    """
    from api.db.services.system_settings_service import SystemSettingsService

    def get_setting_val(name, default):
        try:
            objs = SystemSettingsService.get_by_name(name)
            if objs:
                return objs[0].value
        except Exception:
            pass
        return default

    plus_usd = float(get_setting_val("pricing.plus.usd", 20))
    plus_uzs = float(get_setting_val("pricing.plus.uzs", 199000))
    pro_usd = float(get_setting_val("pricing.pro.usd", 40))
    pro_uzs = float(get_setting_val("pricing.pro.uzs", 400000))

    return get_json_result(data={
        "registerEnabled": settings.REGISTER_ENABLED,
        "disablePasswordLogin": settings.DISABLE_PASSWORD_LOGIN,
        "pricing": {
            "plus_usd": plus_usd,
            "plus_uzs": plus_uzs,
            "pro_usd": pro_usd,
            "pro_uzs": pro_uzs,
        }
    })

@manager.route("/system/healthz", methods=["GET"])  # noqa: F821
def healthz():
    result, all_ok = run_health_checks()
    return jsonify(result), (200 if all_ok else 500)

@manager.route("/system/tokens", methods=["GET"])  # noqa: F821
@login_required
def token_list():
    """
    List all API tokens for the current user.
    ---
    tags:
      - API Tokens
    security:
      - ApiKeyAuth: []
    responses:
      200:
        description: List of API tokens.
        schema:
          type: object
          properties:
            tokens:
              type: array
              items:
                type: object
                properties:
                  token:
                    type: string
                    description: The API token.
                  name:
                    type: string
                    description: Name of the token.
                  create_time:
                    type: string
                    description: Token creation time.
    """
    try:
        tenants = UserTenantService.query(user_id=current_user.id)
        if not tenants:
            return get_data_error_result(message="Tenant not found!")

        tenant_id = [tenant for tenant in tenants if tenant.role == "owner"][0].tenant_id
        objs = APITokenService.query(tenant_id=tenant_id)
        objs = [o.to_dict() for o in objs]
        for o in objs:
            if not o["beta"]:
                o["beta"] = generate_confirmation_token().replace("ragflow-", "")[:32]
                APITokenService.filter_update([APIToken.tenant_id == tenant_id, APIToken.token == o["token"]], o)
        return get_json_result(data=objs)
    except Exception as e:
        return server_error_response(e)


@manager.route("/system/tokens", methods=["POST"])  # noqa: F821
@login_required
async def new_token():
    """
    Generate a new API token.
    ---
    tags:
      - API Tokens
    security:
      - ApiKeyAuth: []
    parameters:
      - in: query
        name: name
        type: string
        required: false
        description: Name of the token.
    responses:
      200:
        description: Token generated successfully.
        schema:
          type: object
          properties:
            token:
              type: string
              description: The generated API token.
    """
    try:
        tenants = UserTenantService.query(user_id=current_user.id)
        if not tenants:
            return get_data_error_result(message="Tenant not found!")

        tenant_id = [tenant for tenant in tenants if tenant.role == "owner"][0].tenant_id
        
        from quart import request
        req = await request.json or {}
        name = req.get("name") or request.args.get("name") or "API Key"
        
        obj = {
            "tenant_id": tenant_id,
            "token": generate_confirmation_token(),
            "beta": generate_confirmation_token().replace("ragflow-", "")[:32],
            "name": name,
            "status": "1",
            "create_time": current_timestamp(),
            "create_date": datetime_format(datetime.now()),
            "update_time": None,
            "update_date": None,
        }

        if not APITokenService.save(**obj):
            return get_data_error_result(message="Fail to new a dialog!")

        return get_json_result(data=obj)
    except Exception as e:
        return server_error_response(e)


@manager.route("/system/tokens/<token>", methods=["PUT"])  # noqa: F821
@login_required
async def update_token(token):
    """
    Update an API token.
    """
    try:
        tenants = UserTenantService.query(user_id=current_user.id)
        if not tenants:
            return get_data_error_result(message="Tenant not found!")

        tenant_id = tenants[0].tenant_id
        
        from quart import request
        req = await request.json or {}
        update_data = {}
        if "name" in req:
            update_data["name"] = req["name"]
        if "status" in req:
            update_data["status"] = req["status"]
            
        if not update_data:
            return get_json_result(data=True)
            
        update_data["update_time"] = current_timestamp()
        update_data["update_date"] = datetime_format(datetime.now())
        
        APITokenService.filter_update([APIToken.tenant_id == tenant_id, APIToken.token == token], update_data)
        return get_json_result(data=True)
    except Exception as e:
        return server_error_response(e)


@manager.route("/system/tokens/<token>", methods=["DELETE"])  # noqa: F821
@login_required
def rm(token):
    """
    Remove an API token.
    ---
    tags:
      - API Tokens
    security:
      - ApiKeyAuth: []
    parameters:
      - in: path
        name: token
        type: string
        required: true
        description: The API token to remove.
    responses:
      200:
        description: Token removed successfully.
        schema:
          type: object
          properties:
            success:
              type: boolean
              description: Deletion status.
    """
    try:
        tenants = UserTenantService.query(user_id=current_user.id)
        if not tenants:
            return get_data_error_result(message="Tenant not found!")

        tenant_id = tenants[0].tenant_id
        APITokenService.filter_delete([APIToken.tenant_id == tenant_id, APIToken.token == token])
        return get_json_result(data=True)
    except Exception as e:
        return server_error_response(e)


@manager.route("/system/config/log", methods=["GET"])  # noqa: F821
@login_required
async def get_logger_levels():
    """
    Get current log levels for all packages.
    ---
    tags:
        - System
    responses:
        200:
            description: Return current log levels
    """
    return get_json_result(data=get_log_levels())


@manager.route("/system/config/log", methods=["PUT"])  # noqa: F821
@login_required
async def set_logger_level():
    """
    Set log level for a package.
    ---
    tags:
        - System
    parameters:
        - in: body
          name: body
          required: true
          schema:
            type: object
            properties:
                pkg_name:
                    type: string
                    description: Package name (e.g., "rag.utils.es_conn")
                level:
                    type: string
                    description: Log level (DEBUG, INFO, WARNING, ERROR)
    responses:
        200:
            description: Log level updated successfully
    """
    from quart import request
    data = await request.get_json()
    if not data or "pkg_name" not in data or "level" not in data:
        return get_data_error_result(message="pkg_name and level are required")
    pkg_name = data["pkg_name"]
    level = data["level"]
    success = set_log_level(pkg_name, level)
    if success:
        return get_json_result(data={"pkg_name": pkg_name, "level": level})
    else:
        return get_data_error_result(message=f"Invalid log level: {level}")


@manager.route("/system/provision", methods=["POST"])  # noqa: F821
@login_required
async def system_provision():
    if not current_user.is_superuser:
        return get_json_result(
            data=False,
            message="No authorization.",
            code=RetCode.AUTHENTICATION_ERROR,
        )

    req = await get_request_json()
    email = req.get("email")
    plan = str(req.get("plan", "free")).lower()  # plus, pro, enterprise
    months = int(req.get("months", 1))

    if not email:
        return get_data_error_result(message="email is required")

    from api.db.services.user_service import UserService, TenantService
    users = UserService.query(email=email)
    if not users:
        return get_data_error_result(message=f"User {email} not found")

    user = users[0]

    from datetime import datetime, timedelta
    from common.time_utils import datetime_format

    expiry_date = datetime.now() + timedelta(days=months * 30)

    # Plus: 5000 credits/mo, Pro: 10000 credits/mo
    license_key = None
    if plan == "plus":
        credits = 5000 * months
    elif plan == "pro":
        credits = 10000 * months
    elif plan == "license":
        credits = 999999 * months
        try:
            from generate_license import generate_license
        except ImportError:
            try:
                from api.utils.license_generator import generate_license
            except ImportError:
                import sys
                from pathlib import Path
                sys.path.append(str(Path(__file__).resolve().parents[3]))
                from generate_license import generate_license
        from api.db.services.license_key_service import LicenseKeyService
        import uuid

        license_name = req.get("license_name") or "Self-Hosted License"
        expiry_str = expiry_date.strftime("%Y-%m-%d")
        lic_type = "yearly" if months >= 12 else "6_months"
        license_key = generate_license(owner=email, expiry=expiry_str, lic_type=lic_type)

        lic_record = {
            "id": uuid.uuid4().hex,
            "user_id": user.id,
            "name": license_name,
            "amount": 0.0,
            "duration_months": months,
            "expiry_date": expiry_date,
            "payment_id": f"system-prov-{uuid.uuid4().hex}",
            "is_paid": True,
            "status": "active",
            "license_key": license_key
        }
        LicenseKeyService.insert(**lic_record)

    TenantService.update_by_id(
        user.id,
        {
            "plan_type": plan,
            "plan_expiry_date": datetime_format(expiry_date),
            "credit": credits
        }
    )

    return get_json_result(data={"license_key": license_key} if license_key else True)



@manager.route("/system/license", methods=["GET"])  # noqa: F821
@login_required
async def get_license():
    from api.utils.license_verifier import check_license
    is_valid, msg, payload = check_license()
    
    # Read the raw key too
    from api.db.services.system_settings_service import SystemSettingsService
    objs = list(SystemSettingsService.get_by_name("license.key"))
    raw_key = objs[0].value if objs and objs[0].value else ""

    db_record = None
    if raw_key:
        from api.db.services.license_key_service import LicenseKeyService
        lic_records = LicenseKeyService.query(license_key=raw_key)
        if lic_records:
            db_record = lic_records[0].to_dict()
            from datetime import datetime
            for key_field in ["expiry_date", "create_date", "update_date"]:
                if db_record.get(key_field):
                    val = db_record[key_field]
                    if isinstance(val, datetime):
                        db_record[key_field] = val.strftime("%Y-%m-%d %H:%M:%S")
                    else:
                        db_record[key_field] = str(val)

    return get_json_result(data={
        "is_valid": is_valid,
        "message": msg,
        "payload": payload,
        "license_key": raw_key,
        "db_record": db_record
    })


@manager.route("/system/license", methods=["POST"])  # noqa: F821
@login_required
async def activate_license():
    from api.utils.api_utils import get_request_json
    req = await get_request_json()
    license_key = req.get("license_key", "").strip()
    if not license_key:
        return get_data_error_result(message="License key is required.")

    from api.utils.license_verifier import decode_license, verify_license_online
    payload = decode_license(license_key)
    if not payload:
        return get_data_error_result(message="Invalid license signature or structure.")

    expiry_str = payload.get("expiry")
    if not expiry_str:
        return get_data_error_result(message="License is missing expiry date.")

    try:
        expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d")
    except ValueError:
        return get_data_error_result(message="Invalid expiry date format in license.")

    if datetime.now() > expiry_date:
        return get_data_error_result(message=f"License key has expired on {expiry_str}.")

    # Verify online
    online_ok = verify_license_online(license_key)
    if not online_ok:
        return get_data_error_result(message="License verification failed with the central server.")

    # Save to system settings
    from api.db.services.system_settings_service import SystemSettingsService
    objs = list(SystemSettingsService.get_by_name("license.key"))
    if objs:
        SystemSettingsService.update_by_name("license.key", {"value": license_key})
    else:
        SystemSettingsService.save(
            name="license.key",
            value=license_key,
            source="variable",
            data_type="string"
        )

    days_left = (expiry_date - datetime.now()).days
    return get_json_result(data={
        "is_valid": True,
        "message": f"License activated successfully. {days_left} days remaining until {expiry_str}.",
        "payload": payload
    })


_IN_MEMORY_RATE_LIMITS = {}
_LAST_CLEANUP_TS = 0

def _check_in_memory_ratelimit(key: str, limit: int, window_sec: int) -> bool:
    global _LAST_CLEANUP_TS
    import time
    now = time.time()
    if now - _LAST_CLEANUP_TS > 60:
        _LAST_CLEANUP_TS = now
        expired_keys = [k for k, (ts, _) in _IN_MEMORY_RATE_LIMITS.items() if now - ts > 300]
        for k in expired_keys:
            _IN_MEMORY_RATE_LIMITS.pop(k, None)

    record = _IN_MEMORY_RATE_LIMITS.get(key)
    if not record or (now - record[0] > window_sec):
        _IN_MEMORY_RATE_LIMITS[key] = (now, 1)
        return True
    ts, count = record
    if count >= limit:
        return False
    _IN_MEMORY_RATE_LIMITS[key] = (ts, count + 1)
    return True


@manager.route("/licenses/verify", methods=["POST"])  # noqa: F821
async def verify_license_status():
    import hashlib
    from quart import request
    from api.utils.api_utils import get_request_json
    from api.utils.license_verifier import decode_license
    from api.db.services.license_key_service import LicenseKeyService
    from rag.utils.redis_conn import REDIS_CONN

    # Extract client IP: prefer X-Real-IP from trusted reverse proxy, or rightmost element of X-Forwarded-For
    client_ip = request.headers.get("X-Real-IP")
    if not client_ip and request.headers.get("X-Forwarded-For"):
        client_ip = request.headers.get("X-Forwarded-For").split(",")[-1].strip()
    if not client_ip:
        client_ip = request.remote_addr or "127.0.0.1"

    req = await get_request_json() or {}
    license_key = req.get("license_key", "").strip()

    # 1. Multi-dimensional Rate Limiting (by IP and by Key Hash)
    key_hash = hashlib.sha256(license_key.encode("utf-8", errors="ignore")).hexdigest()[:16] if license_key else "empty"
    rate_limited = False
    try:
        # IP Rate Limit: 60 requests/minute
        ip_count = REDIS_CONN.generate_auto_increment_id(
            key_prefix="ratelimit",
            namespace=f"lic_verify_ip:{client_ip}",
            increment=1
        )
        if ip_count == 1 and REDIS_CONN.REDIS:
            REDIS_CONN.REDIS.expire(f"ratelimit:lic_verify_ip:{client_ip}", 60)
        
        # Key Rate Limit: 10 requests / 5 minutes per key across all IPs (botnet protection)
        key_count = REDIS_CONN.generate_auto_increment_id(
            key_prefix="ratelimit",
            namespace=f"lic_verify_key:{key_hash}",
            increment=1
        )
        if key_count == 1 and REDIS_CONN.REDIS:
            REDIS_CONN.REDIS.expire(f"ratelimit:lic_verify_key:{key_hash}", 300)

        if ip_count > 60 or key_count > 10:
            rate_limited = True
    except Exception as e:
        logging.critical("CRITICAL: Redis unavailable in license verification rate limiter. Falling back to local in-memory rate limiting: %s", e)
        ip_ok = _check_in_memory_ratelimit(f"ip:{client_ip}", 60, 60)
        key_ok = _check_in_memory_ratelimit(f"key:{key_hash}", 10, 300)
        if not ip_ok or not key_ok:
            rate_limited = True

    if rate_limited:
        logging.warning("Rate limit triggered on verify [IP=%s, key_hash=%s]", client_ip, key_hash)
        return jsonify({
            "valid": False,
            "reason": "rate_limit_exceeded",
            "message": "Too many requests. Please try again later.",
            "code": 429
        }), 429

    if not license_key:
        return jsonify({"valid": False, "reason": "license_invalid", "code": 102}), 200

    # 2. Cryptographic signature check
    payload = decode_license(license_key)
    crypto_valid = payload is not None

    # 3. Always execute DB query regardless of crypto_valid to equalize response timing (Anti-Timing Attack)
    lic_records = LicenseKeyService.query(license_key=license_key) if license_key else []

    if not crypto_valid:
        logging.info("License verify failed [IP=%s, key_hash=%s]: invalid cryptographic signature", client_ip, key_hash)
        return jsonify({"valid": False, "reason": "license_invalid", "code": 102}), 200

    expiry_str = payload.get("expiry")
    if not expiry_str:
        logging.info("License verify failed [IP=%s, key_hash=%s]: missing expiry", client_ip, key_hash)
        return jsonify({"valid": False, "reason": "license_invalid", "code": 102}), 200

    try:
        expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d")
        if datetime.now() > expiry_date:
            logging.info("License verify failed [IP=%s, key_hash=%s]: expired on %s", client_ip, key_hash, expiry_str)
            return jsonify({"valid": False, "reason": "license_invalid", "code": 102}), 200
    except ValueError:
        logging.info("License verify failed [IP=%s, key_hash=%s]: invalid expiry date %s", client_ip, key_hash, expiry_str)
        return jsonify({"valid": False, "reason": "license_invalid", "code": 102}), 200

    # 4. Check DB status if record exists
    if lic_records:
        lic = lic_records[0]
        if not lic.is_paid or lic.status != "active":
            logging.info("License verify failed [IP=%s, key_hash=%s]: db record inactive/unpaid (status=%s, is_paid=%s)", client_ip, key_hash, lic.status, lic.is_paid)
            return jsonify({"valid": False, "reason": "license_invalid", "code": 102}), 200
        if lic.expiry_date and datetime.now() > lic.expiry_date:
            logging.info("License verify failed [IP=%s, key_hash=%s]: db record expired on %s", client_ip, key_hash, lic.expiry_date)
            return jsonify({"valid": False, "reason": "license_invalid", "code": 102}), 200

    return jsonify({
        "valid": True,
        "expiry": expiry_str,
        "type": payload.get("type", "yearly"),
        "code": 0
    }), 200




