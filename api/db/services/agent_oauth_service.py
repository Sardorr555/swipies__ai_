"""Production adapters for MCP OAuth; existing tenant/key policy stays authoritative."""

import json
import logging
import os
import secrets
import urllib.request

from api.agent_oauth import OAuthService, RedisStore


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch_chatgpt_metadata(url):
    # The caller accepts only the exact ChatGPT CIMD URL patterns; redirects are never followed.
    opener = urllib.request.build_opener(NoRedirect())
    with opener.open(urllib.request.Request(url, headers={"User-Agent": "SwipiesAgent/1.0", "Accept": "application/json"}), timeout=5) as response:
        data = response.read(65537)
        if len(data) > 65536 or response.status != 200:
            raise ValueError("Invalid client document")
        return json.loads(data)


def make_service():
    from rag.utils.redis_conn import REDIS_CONN
    from api.utils.key_crypto import encrypt_api_key, decrypt_api_key

    # OAuthLib's DEBUG messages can include authorization codes/token bodies.
    logging.getLogger("oauthlib").setLevel(logging.WARNING)
    if os.getenv("SWIPIES_AGENT_OAUTH_ENABLED", "0") == "1":
        # Fail startup rather than advertise a flow that cannot protect grants.
        # This uses the existing connector encryption/master-secret policy.
        encrypt_api_key("OAuth startup validation")
    store = RedisStore(lambda: REDIS_CONN.REDIS, encrypt_api_key, decrypt_api_key)
    return OAuthService(
        store, os.getenv("SWIPIES_AGENT_PUBLIC_ORIGIN", "https://api.swipies.app"), fetch_chatgpt_metadata, key_active, revoke_key, enabled=lambda: os.getenv("SWIPIES_AGENT_OAUTH_ENABLED", "0") == "1"
    )


def key_active(principal):
    from api.db.db_models import APIToken, User, DB

    with DB.connection_context():
        token = APIToken.get_or_none(APIToken.token == principal["api_key"], APIToken.tenant_id == principal["tenant_id"], APIToken.status == "1")
        user = User.get_or_none(User.id == principal["tenant_id"], User.status == "1")
        # An approved OAuth grant survives browser logout just like its private
        # API key. Account disable/delete or explicit key/grant revocation stops
        # it; the browser's login token is only required at initial owner consent.
        return bool(token and user and str(user.access_token or "").strip())


def revoke_key(principal):
    from api.db.db_models import APIToken, DB

    with DB.connection_context():
        APIToken.update(status="0").where(APIToken.token == principal["api_key"], APIToken.tenant_id == principal["tenant_id"]).execute()


async def delegate(choice, registration_secret):
    from api.apps import AUTH_JWT, _load_user
    from api.db.services.agent_access_service import bootstrap
    from common.misc_utils import thread_pool_exec
    from quart import request

    if choice == "free":
        # bootstrap resolves X-Real-IP against the configured trusted proxies.
        result = await bootstrap({"registration_secret": registration_secret, "name": "ChatGPT workspace"}, request.remote_addr)
        return {"tenant_id": result["tenant_id"], "api_key": result["api_key"]}
    if choice != "existing":
        return None
    user = _load_user((AUTH_JWT,))
    if not user:
        return None
    owner_id = user.id

    def create_key():
        from api.db.db_models import APIToken, DB, UserTenant

        try:
            if not UserTenant.get_or_none(UserTenant.user_id == owner_id, UserTenant.tenant_id == owner_id, UserTenant.role == "owner"):
                return None
            value = "ragflow-" + secrets.token_urlsafe(48)
            APIToken.create(tenant_id=owner_id, token=value, beta=secrets.token_urlsafe(32), name="ChatGPT OAuth connection", status="1")
            return {"tenant_id": owner_id, "api_key": value}
        finally:
            if not DB.is_closed():
                DB.close()

    return await thread_pool_exec(create_key)


def address():
    from api.db.services.agent_access_service import client_address
    from quart import request

    return client_address(request.remote_addr, request.headers.get("X-Real-IP"))
