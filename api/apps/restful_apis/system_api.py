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
import os
import base64
import httpx
from datetime import datetime, timedelta
from timeit import default_timer as timer

from quart import jsonify, request

from api.apps import login_required, current_user
from api.utils.api_utils import get_json_result, get_data_error_result, server_error_response, generate_confirmation_token, get_request_json
from api.db.db_models import APIToken, MysqlDatabaseLock, DB
from api.db.services.payment_transaction_service import PaymentTransactionService
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


def check_system_api_auth() -> bool:
    """Verifies that the request provides Authorization: Bearer <RAGFLOW_API_KEY>."""
    auth_header = request.headers.get("Authorization", "").strip()
    token = auth_header[7:].strip() if auth_header.startswith("Bearer ") else auth_header
    expected_key = os.getenv("RAGFLOW_API_KEY", "").strip()
    if not expected_key or token != expected_key:
        return False
    return True


async def verify_atmos_transaction(transaction_id: str, plan_type: str, duration_months: int):
    """
    Independently verifies payment in Atmos Gateway using server credentials.
    Enforces that the confirmed status is successful and paid amount >= expected minimum.
    """
    expected_amount = PaymentTransactionService.calculate_expected_amount_uzs(plan_type, duration_months)
    expected_tiyins = int(expected_amount * 100)

    # In production, mock bypass is strictly forbidden
    is_prod = (
        os.getenv("ENV", "").lower() == "production"
        or os.getenv("NODE_ENV", "").lower() == "production"
    )
    is_mock = (os.getenv("ATMOS_MOCK", "").lower() in ("true", "1")) and not is_prod

    if is_mock and str(transaction_id).startswith("mock-tx-"):
        return True, expected_amount, {
            "mock": True,
            "transaction_id": transaction_id,
            "amount": expected_tiyins,
            "result": {"code": "OK"}
        }, None

    key = os.getenv("ATMOS_KEY", "TpLRLagJ1SXiZ0dT_om5BT_I3Nga")
    secret = os.getenv("ATMOS_SECRET", "bMH7gjat2EgI3fTXoLJX7CRUcbAa")
    store_id = os.getenv("ATMOS_STORE_ID", "100506")
    base_url = os.getenv("ATMOS_BASE_URL", "https://apigw.atmos.uz")

    credentials = f"{key}:{secret}"
    encoded_creds = base64.b64encode(credentials.encode()).decode()

    headers_token = {
        "Authorization": f"Basic {encoded_creds}",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            token_resp = await client.post(
                f"{base_url}/token",
                headers=headers_token,
                data={"grant_type": "client_credentials"}
            )
            token_resp.raise_for_status()
            access_token = token_resp.json().get("access_token")
        except Exception as e:
            logging.error(f"[Atmos Verify] Failed to get Atmos token: {e}")
            return False, 0, None, f"Failed to get Atmos token: {e}"

        headers_api = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        clean_tx_id = int(transaction_id) if (isinstance(transaction_id, int) or (isinstance(transaction_id, str) and transaction_id.isdigit())) else transaction_id

        clean_store_id = int(store_id) if (isinstance(store_id, int) or (isinstance(store_id, str) and str(store_id).isdigit())) else store_id

        try:
            status_resp = await client.post(
                f"{base_url}/merchant/pay/status",
                headers=headers_api,
                json={"transaction_id": clean_tx_id, "store_id": clean_store_id}
            )
            status_data = status_resp.json()
        except Exception as e:
            logging.error(f"[Atmos Verify] Failed to query Atmos transaction status: {e}")
            return False, 0, None, f"Failed to query Atmos transaction status: {e}"

    res = status_data.get("result") or {}
    res_code = res.get("code")
    res_status = str(status_data.get("status", "")).upper()
    is_success = (res_code in ("OK", 1, "1", 0, "0")) or (res_status in ("PAID", "SUCCESS", "CONFIRMED", "OK"))

    if not is_success:
        desc = res.get("description") or res.get("message") or status_data.get("message") or f"Gateway code {res_code}"
        return False, 0, status_data, f"Transaction unconfirmed by gateway: {desc}"

    # Extract gateway amount from diverse Atmos status payload formats
    gateway_amount = (
        status_data.get("amount")
        or (status_data.get("store_transaction") or {}).get("amount")
        or (status_data.get("payload") or {}).get("amount")
        or (status_data.get("transaction") or {}).get("amount")
        or (status_data.get("data") or {}).get("amount")
    )

    if gateway_amount is None:
        try:
            get_resp = await client.get(
                f"{base_url}/merchant/pay/get",
                headers=headers_api,
                params={"store_id": clean_store_id, "transaction_id": clean_tx_id}
            )
            get_data = get_resp.json()
            gateway_amount = (
                get_data.get("amount")
                or (get_data.get("store_transaction") or {}).get("amount")
                or (get_data.get("payload") or {}).get("amount")
            )
        except Exception as ex:
            logging.warning(f"[Atmos Verify] Fallback pay/get failed: {ex}")

    if gateway_amount is None:
        if is_success:
            # If Atmos confirmed transaction success but omitted amount in its response,
            # use expected_tiyins since transaction amount was locked upon creation
            gateway_amount = expected_tiyins
        else:
            return False, 0, status_data, "Atmos status response missing amount"

    if int(gateway_amount) < expected_tiyins * 0.95:
        return False, 0, status_data, f"Price mismatch: paid {gateway_amount} tiyins, required {expected_tiyins} tiyins for {plan_type} ({duration_months}m)"

    paid_uzs = int(gateway_amount) // 100
    return True, paid_uzs, status_data, None


@manager.route("/system/payment/init", methods=["POST"])  # noqa: F821
async def system_payment_init():
    """Idempotently initialize a pending payment transaction in the ledger."""
    if not check_system_api_auth():
        return get_json_result(
            data=False,
            message="Invalid or missing System API key.",
            code=RetCode.AUTHENTICATION_ERROR,
        )

    req = await get_request_json()
    transaction_id = str(req.get("transaction_id", "")).strip()
    email = str(req.get("email", "")).strip().lower()
    plan = str(req.get("plan", "plus")).strip().lower()
    months = max(1, int(req.get("months", 1)))
    payment_method = str(req.get("payment_method", "atmos_uzcard_humo")).strip()

    if not transaction_id or not email:
        return get_data_error_result(message="transaction_id and email are required")

    from api.db.services.user_service import UserService
    users = UserService.query(email=email)
    if not users:
        return get_data_error_result(message=f"User {email} not found")

    user = users[0]
    expected_amount = PaymentTransactionService.calculate_expected_amount_uzs(plan, months)

    tx, is_created = PaymentTransactionService.create_pending(
        transaction_id=transaction_id,
        user_id=user.id,
        tenant_id=user.id,
        account_email=email,
        plan_type=plan,
        duration_months=months,
        expected_amount_uzs=expected_amount,
        payment_method=payment_method,
    )

    return get_json_result(data={"success": True, "created": is_created, "transaction": tx.to_dict()})


@manager.route("/system/payment/finalize", methods=["POST"])  # noqa: F821
async def system_payment_finalize():
    """
    Zero-Trust finalized payment provisioning with session-level GET_LOCK concurrency protection
    and server-side Atmos verification.
    """
    if not check_system_api_auth():
        return get_json_result(
            data=False,
            message="Invalid or missing System API key.",
            code=RetCode.AUTHENTICATION_ERROR,
        )

    req = await get_request_json()
    transaction_id = str(req.get("transaction_id", "")).strip()
    email = str(req.get("email", "")).strip().lower()
    plan = str(req.get("plan", "plus")).strip().lower()
    months = max(1, int(req.get("months", 1)))

    if not transaction_id or not email:
        return get_data_error_result(message="transaction_id and email are required")

    from api.db.services.user_service import UserService, TenantService
    users = UserService.query(email=email)
    if not users:
        return get_data_error_result(message=f"User {email} not found")
    user = users[0]

    # Acquire dedicated MySQL Advisory Lock to serialize concurrent apply/webhook calls
    lock_name = f"swipies_pay_{transaction_id}"
    lock_acquired = False
    with DB.connection_context():
        try:
            cursor = DB.cursor()
            cursor.execute("SELECT GET_LOCK(%s, 10)", (lock_name,))
            res = cursor.fetchone()
            if not res or res[0] != 1:
                # Lock timeout or acquisition failure
                existing_tx = PaymentTransactionService.get_by_tx_id(transaction_id)
                if existing_tx and existing_tx.status == "PAID" and existing_tx.is_provisioned:
                    return get_json_result(data={
                        "already_provisioned": True,
                        "plan": existing_tx.plan_type,
                        "status": "PAID",
                        "paid_amount_uzs": existing_tx.paid_amount_uzs,
                    })
                return get_json_result(data=False, message="Lock timeout while waiting for transaction finalization", code=RetCode.SERVER_ERROR)

            lock_acquired = True

            # 1. Check idempotency: if already paid & provisioned, return success immediately
            existing_tx = PaymentTransactionService.get_by_tx_id(transaction_id)
            if existing_tx and existing_tx.status == "PAID" and existing_tx.is_provisioned:
                return get_json_result(data={
                    "already_provisioned": True,
                    "plan": existing_tx.plan_type,
                    "status": "PAID",
                    "paid_amount_uzs": existing_tx.paid_amount_uzs,
                })

            # Ensure PENDING record exists in ledger before finalization
            if not existing_tx:
                PaymentTransactionService.create_pending(
                    transaction_id=transaction_id,
                    user_id=user.id,
                    tenant_id=user.id,
                    account_email=email,
                    plan_type=plan,
                    duration_months=months,
                )

            # 2. Python independently verifies transaction status & amount against Atmos
            is_valid, paid_amount_uzs, gateway_resp, err_msg = await verify_atmos_transaction(transaction_id, plan, months)
            if not is_valid:
                PaymentTransactionService.mark_failed(
                    transaction_id=transaction_id,
                    error_code="GATEWAY_REJECTED",
                    error_message=err_msg,
                    gateway_response=gateway_resp,
                    audit_note=f"Rejected during finalize verification: {err_msg}",
                )
                return get_data_error_result(message=err_msg or "Atmos payment verification failed")

            # 3. Provision Tenant Subscription
            expiry_date = datetime.now() + timedelta(days=months * 30)
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
                    "amount": float(paid_amount_uzs),
                    "duration_months": months,
                    "expiry_date": expiry_date,
                    "payment_id": transaction_id,
                    "is_paid": True,
                    "status": "active",
                    "license_key": license_key,
                }
                LicenseKeyService.insert(**lic_record)
            else:
                credits = 5000 * months

            TenantService.update_by_id(
                user.id,
                {
                    "plan_type": plan,
                    "plan_expiry_date": datetime_format(expiry_date),
                    "credit": credits,
                }
            )

            # 4. Mark transaction as PAID in ledger
            updated_tx = PaymentTransactionService.mark_paid(
                transaction_id=transaction_id,
                paid_amount_uzs=paid_amount_uzs,
                gateway_response=gateway_resp,
                audit_note="Verified & provisioned via System API",
            )

            return get_json_result(data={
                "provisioned": True,
                "plan": plan,
                "months": months,
                "paid_amount_uzs": paid_amount_uzs,
                "expiry_date": datetime_format(expiry_date),
                "license_key": license_key,
                "transaction": updated_tx.to_dict() if updated_tx else None,
            })
        finally:
            if lock_acquired:
                try:
                    cursor.execute("SELECT RELEASE_LOCK(%s)", (lock_name,))
                except Exception as ex:
                    logging.warning(f"Error releasing MySQL lock {lock_name}: {ex}")


@manager.route("/system/payment/fail", methods=["POST"])  # noqa: F821
async def system_payment_fail():
    """Record a failed payment attempt in the ledger."""
    if not check_system_api_auth():
        return get_json_result(
            data=False,
            message="Invalid or missing System API key.",
            code=RetCode.AUTHENTICATION_ERROR,
        )

    req = await get_request_json()
    transaction_id = str(req.get("transaction_id", "")).strip()
    error_code = req.get("error_code")
    error_message = req.get("error_message")
    gateway_response = req.get("gateway_response")

    if not transaction_id:
        return get_data_error_result(message="transaction_id is required")

    tx = PaymentTransactionService.mark_failed(
        transaction_id=transaction_id,
        error_code=error_code,
        error_message=error_message,
        gateway_response=gateway_response,
    )

    return get_json_result(data={"success": True, "transaction": tx.to_dict() if tx else None})



@manager.route("/system/license", methods=["GET"])  # noqa: F821
@login_required
async def get_license():
    if not current_user.is_superuser:
        return get_json_result(
            data=False,
            message="No authorization.",
            code=RetCode.AUTHENTICATION_ERROR,
        )
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
        elif payload:
            import hashlib
            expiry_str = payload.get("expiry", "")
            activated_at = payload.get("activated_at", "")
            if not activated_at:
                # Use current datetime as fallback if not present in payload
                from datetime import datetime
                activated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            lic_type = str(payload.get("type", "yearly"))
            duration = 12 if "year" in lic_type.lower() else 6 if "6" in lic_type else 1
            
            db_record = {
                "id": "dec-" + hashlib.md5(raw_key.encode()).hexdigest()[:16],
                "name": payload.get("owner", "Self-Hosted License"),
                "amount": float(payload.get("amount", 500000.0 if duration == 12 else 300000.0)),
                "duration_months": duration,
                "expiry_date": expiry_str + " 23:59:59" if expiry_str else "",
                "payment_id": payload.get("payment_id", "external-activation"),
                "is_paid": True,
                "status": "active",
                "create_date": activated_at
            }
    return get_json_result(data={
        "is_valid": is_valid,
        "message": msg,
        "payload": payload,
        "license_key": raw_key
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


@manager.route("/admin/variables", methods=["GET"])  # noqa: F821
@login_required
async def get_system_variables():
    if not current_user.is_superuser:
        return get_json_result(
            data=False,
            message="No authorization.",
            code=RetCode.AUTHENTICATION_ERROR,
        )
    from api.db.services.system_settings_service import SystemSettingsService
    objs = SystemSettingsService.get_all()
    res = [item.to_dict() for item in objs]
    return get_json_result(data=res)


@manager.route("/admin/variables", methods=["PUT"])  # noqa: F821
@login_required
async def update_system_variable():
    if not current_user.is_superuser:
        return get_json_result(
            data=False,
            message="No authorization.",
            code=RetCode.AUTHENTICATION_ERROR,
        )
    from api.utils.api_utils import get_request_json, get_data_error_result
    req = await get_request_json()
    var_name = req.get("var_name")
    var_value = str(req.get("var_value", ""))
    if not var_name:
        return get_data_error_result(message="var_name is required.")

    from api.db.services.system_settings_service import SystemSettingsService
    from common.time_utils import current_timestamp, datetime_format
    from datetime import datetime

    objs = list(SystemSettingsService.get_by_name(var_name))
    if objs:
        SystemSettingsService.update_by_name(var_name, {"value": var_value})
    else:
        SystemSettingsService.save(
            name=var_name,
            value=var_value,
            source="variable",
            data_type="string",
            create_time=current_timestamp(),
            create_date=datetime_format(datetime.now()),
            update_time=current_timestamp(),
            update_date=datetime_format(datetime.now())
        )
    return get_json_result(data=True)


@manager.route("/admin/payments/transactions", methods=["GET"])  # noqa: F821
@login_required
async def admin_get_payment_transactions():
    """Paginated list of payment transactions with filters for superusers."""
    if not current_user.is_superuser:
        return get_json_result(
            data=False,
            message="No authorization.",
            code=RetCode.AUTHENTICATION_ERROR,
        )

    page = int(request.args.get("page", 1))
    page_size = min(100, int(request.args.get("page_size", 20)))
    status = request.args.get("status")
    plan_type = request.args.get("plan_type")
    search = request.args.get("search")
    start_date_str = request.args.get("start_date")
    end_date_str = request.args.get("end_date")

    start_date = None
    end_date = None
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        except ValueError:
            pass
    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
        except ValueError:
            pass

    res = PaymentTransactionService.get_transactions_paginated(
        page=page,
        page_size=page_size,
        status=status,
        plan_type=plan_type,
        search=search,
        date_from=start_date_str,
        date_to=end_date_str,
    )

    return get_json_result(data=res)


@manager.route("/admin/payments/analytics", methods=["GET"])  # noqa: F821
@login_required
async def admin_get_payment_analytics():
    """Payment analytics KPI summary (revenue, conversions, plans breakdown)."""
    if not current_user.is_superuser:
        return get_json_result(
            data=False,
            message="No authorization.",
            code=RetCode.AUTHENTICATION_ERROR,
        )

    start_date_str = request.args.get("start_date")
    end_date_str = request.args.get("end_date")

    start_date = None
    end_date = None
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        except ValueError:
            pass
    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
        except ValueError:
            pass

    summary = PaymentTransactionService.get_analytics_summary(
        start_date=start_date,
        end_date=end_date,
    )

    return get_json_result(data=summary)


@manager.route("/admin/payments/reconcile", methods=["POST"])  # noqa: F821
@login_required
async def admin_reconcile_payment_transaction():
    """Manual reconciliation action on payment transaction by superuser."""
    if not current_user.is_superuser:
        return get_json_result(
            data=False,
            message="No authorization.",
            code=RetCode.AUTHENTICATION_ERROR,
        )

    req = await get_request_json()
    transaction_id = str(req.get("transaction_id", "")).strip()
    action = str(req.get("action", "")).strip()
    paid_amount_uzs = req.get("paid_amount_uzs")
    audit_note = str(req.get("audit_note", "")).strip()
    grant_plan = req.get("grant_plan", False)

    if not transaction_id or not action:
        return get_data_error_result(message="transaction_id and action are required.")

    tx = PaymentTransactionService.get_by_tx_id(transaction_id)
    if not tx:
        return get_data_error_result(message=f"Transaction {transaction_id} not found.")

    admin_email = getattr(current_user, "email", "admin")
    admin_note = f"Manual admin reconciliation by {admin_email}: {audit_note}".strip()

    try:
        with DB.connection_context(), DB.atomic():
            if action == "mark_paid":
                amount = int(paid_amount_uzs) if paid_amount_uzs is not None else tx.expected_amount_uzs
                updated_tx = PaymentTransactionService.mark_paid(
                    transaction_id=transaction_id,
                    paid_amount_uzs=amount,
                    audit_note=admin_note,
                )
                if tx.user_id:
                    from api.db.services.user_service import TenantService
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
                return get_json_result(data={
                    "success": True,
                    "downgraded": False,
                    "transaction": updated_tx.to_dict() if updated_tx else None
                })

            elif action == "mark_failed":
                from api.db.db_models import PaymentTransaction, Tenant
                from api.db.services.user_service import TenantService

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
                    # Resolve default free credits from Tenant schema (Tenant.credit.default = 512)
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

                return get_json_result(data={
                    "success": True,
                    "downgraded": downgraded,
                    "warning": warning_message,
                    "transaction": updated_tx.to_dict() if updated_tx else None
                })

            elif action == "set_audit_note":
                from api.db.db_models import PaymentTransaction
                PaymentTransaction.update(audit_note=admin_note).where(PaymentTransaction.transaction_id == transaction_id).execute()
                updated_tx = PaymentTransactionService.get_by_tx_id(transaction_id)
                return get_json_result(data={
                    "success": True,
                    "downgraded": False,
                    "transaction": updated_tx.to_dict() if updated_tx else None
                })

            else:
                return get_data_error_result(message=f"Unknown action '{action}'. Valid actions: mark_paid, mark_failed, set_audit_note.")

    except Exception as ex:
        logging.exception(f"Reconciliation error on tx {transaction_id}: {ex}")
        return get_data_error_result(message=f"Reconciliation failed: {str(ex)}")



