"""Provision isolated free service accounts, without altering human sign-in/2FA."""
import hashlib
import ipaddress
import os
import re
import secrets
import time
from datetime import datetime
from werkzeug.security import generate_password_hash


def origin_allowed(origin):
    if not origin:
        return True  # Native MCP clients do not send Origin.
    configured = os.getenv("SWIPIES_AGENT_ALLOWED_ORIGINS", "https://api.swipies.app")
    return origin in {item.strip().rstrip("/") for item in configured.split(",") if item.strip()}


def validate_registration(data):
    secret = data.get("registration_secret", "")
    if not isinstance(secret, str) or not re.fullmatch(r"[A-Za-z0-9_-]{43,128}", secret):
        raise ValueError("registration_secret must be a locally generated random URL-safe secret of at least 43 characters")
    name = data.get("name", "Agent workspace")
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 80:
        raise ValueError("name must contain 1 to 80 characters")
    # Do not accept caller-supplied email, owner id, plan or privileges.
    if set(data) - {"registration_secret", "name"}:
        raise ValueError("Only registration_secret and name are accepted")
    return secret, name.strip()


def client_address(remote_addr, real_ip):
    """Only an explicitly trusted proxy may set the rate-limit client address."""
    try:
        peer = ipaddress.ip_address(remote_addr)
        proxies = os.getenv("SWIPIES_AGENT_TRUSTED_PROXIES", "127.0.0.1/32,::1/128")
        if any(peer in ipaddress.ip_network(network.strip()) for network in proxies.split(",") if network.strip()):
            return str(ipaddress.ip_address(real_ip)) if real_ip else str(peer)
    except (ValueError, TypeError):
        pass
    return str(remote_addr)


def _limit_registration(remote_addr):
    from rag.utils.redis_conn import REDIS_CONN
    client = REDIS_CONN.REDIS
    if client is None:
        raise RuntimeError("Limiter unavailable")
    hour = int(time.time() // 3600)
    # Never trust caller-controlled Forwarded/X-Forwarded-For. Configure the
    # trusted reverse proxy to supply remote_addr; otherwise use global limit.
    address = hashlib.sha256(str(remote_addr).encode()).hexdigest()[:24]
    for suffix, limit in ((address, int(os.getenv("SWIPIES_AGENT_REGISTRATIONS_PER_IP_HOUR", "3"))), ("global", int(os.getenv("SWIPIES_AGENT_REGISTRATIONS_PER_HOUR", "100")))):
        pipe = client.pipeline(transaction=True)
        key = f"swipies:agent-registration:{hour}:{suffix}"
        count, _ = pipe.incr(key).expire(key, 7200).execute()
        if count > limit:
            raise RuntimeError("Registration limited")


def provision(data, remote_addr):
    from api.db.db_models import DB, APIToken, User, Tenant, UserTenant, File
    from api.apps.restful_apis.user_api import prepare_user_registration
    from common import settings
    from common.misc_utils import get_uuid

    secret, name = validate_registration(data)
    user_id = hashlib.sha256(("swipies-agent:" + secret).encode()).hexdigest()[:32]
    token = "ragflow-" + secret
    # Retries resolve the same account. Revoked keys/accounts are never restored.
    existing = APIToken.get_or_none(APIToken.token == token)
    if existing:
        user = User.get_or_none(User.id == existing.tenant_id)
        if existing.tenant_id != user_id or str(existing.status) != "1" or not user or str(user.status) != "1":
            raise PermissionError()
        return {"tenant_id": user_id, "api_key": token, "created": False, "mcp_path": "/api/v1/agent-access/mcp"}
    if User.get_or_none(User.id == user_id):
        raise PermissionError()
    if not settings.REGISTER_ENABLED or os.getenv("SWIPIES_AGENT_REGISTRATION_ENABLED", "1").lower() not in {"1", "true", "yes"}:
        raise PermissionError()
    _limit_registration(remote_addr)
    user = {"nickname": name, "email": f"{user_id}@agents.swipies.invalid", "password": secrets.token_urlsafe(48), "access_token": get_uuid(), "login_channel": "agent", "is_active": "1", "status": "1", "marketing_consent": False}
    tenant, membership, root_file = prepare_user_registration(user_id, user)
    tenant.update(name=name, plan_type="free")
    user["password"] = generate_password_hash(user["password"])
    now = datetime.now()
    timestamps = {"create_time": int(now.timestamp() * 1000), "update_time": int(now.timestamp() * 1000), "create_date": now, "update_date": now}
    # Use model writes here. CommonService methods have connection_context
    # decorators that close the connection and cannot nest inside DB.atomic().
    with DB.atomic():
        User.create(**user, **timestamps)
        Tenant.create(**tenant, **timestamps)
        membership.setdefault("id", get_uuid())
        UserTenant.create(**membership, **timestamps)
        File.create(**root_file, **timestamps)
        APIToken.create(tenant_id=user_id, token=token, beta=secrets.token_urlsafe(32), name="Agent access", status="1", **timestamps)
    return {"tenant_id": user_id, "api_key": token, "created": True, "mcp_path": "/api/v1/agent-access/mcp"}


async def bootstrap(data, remote_addr):
    from common.misc_utils import thread_pool_exec
    from api.db.db_models import DB
    from quart import request
    address = client_address(remote_addr, request.headers.get("X-Real-IP"))
    def work():
        try:
            return provision(data, address)
        finally:
            if not DB.is_closed():
                DB.close()
    return await thread_pool_exec(work)
