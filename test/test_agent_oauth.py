"""OAuth protocol/security tests using OAuthLib, real AES-GCM and Redis Lua."""

import asyncio
import base64
import hashlib
import json
import re
import secrets
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit

import fakeredis
import pytest
from quart import Quart, jsonify, request

from api.agent_access import operations, register_agent_access
from api.agent_oauth import OAuthService, RedisStore, PREFIX, SCOPES
from api.utils.key_crypto import encrypt_api_key, decrypt_api_key

ORIGIN = "https://api.swipies.app"
RESOURCE = ORIGIN + "/api/v1/agent-access/mcp"
CALLBACK = "https://chatgpt.com/connector_platform_oauth_redirect"


def run(coro):
    return asyncio.run(coro)


@pytest.fixture
def fixture():
    redis = fakeredis.FakeRedis()
    secret = "oauth-test-master-" + "x" * 40
    store = RedisStore(redis, lambda data: encrypt_api_key(data, secret), lambda data: decrypt_api_key(data, secret))
    active, created = {"key-owner-a", "key-new-free"}, []
    metadata = {"redirect_uris": [CALLBACK], "client_name": "ChatGPT", "token_endpoint_auth_methods_supported": ["none", "private_key_jwt"]}
    fetched = []

    def fetch(url):
        fetched.append(url)
        return metadata

    service = OAuthService(store, ORIGIN, fetch, lambda p: p["api_key"] in active, lambda p: active.discard(p["api_key"]))
    app = Quart(__name__, template_folder=str(Path(__file__).parents[1] / "api/apps/templates"))
    app.testing = True

    async def delegate(choice, secret):
        if choice == "existing" and request.headers.get("Authorization") == "Bearer owner-a":
            return {"tenant_id": "owner-a", "api_key": "key-owner-a"}
        if choice == "free":
            created.append(secret)
            return {"tenant_id": "new-free", "api_key": "key-new-free"}
        return None

    from api.agent_oauth import register_agent_oauth

    register_agent_oauth(app, service, delegate, lambda: "test-address")

    @app.route("/api/v1/datasets", methods=["GET", "POST"])
    async def datasets():
        return jsonify(code=0, data={"identity": request.headers.get("Authorization")})

    datasets.swipies_auth_types = {"API"}

    async def bootstrap(data, address):
        return {"created": True}

    register_agent_access(app, lambda: request.headers.get("Authorization") == "Bearer legacy-key", bootstrap, lambda origin: origin in (None, ORIGIN), oauth=service)
    return app, service, active, created, redis, fetched


async def client_id(client, **metadata):
    response = await client.post(PREFIX + "/register", json={"redirect_uris": [CALLBACK], "client_name": "ChatGPT", **metadata}, scheme="https")
    assert response.status_code == 201
    return (await response.get_json())["client_id"]


def params(identifier, scope=" ".join(SCOPES), **extra):
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    return {
        "client_id": identifier,
        "redirect_uri": CALLBACK,
        "response_type": "code",
        "state": "opaque-state",
        "resource": RESOURCE,
        "scope": scope,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        **extra,
    }, verifier


async def approve(client, query, choice="free", authorization=None):
    response = await client.get(PREFIX + "/authorize", query_string=query, scheme="https")
    assert response.status_code == 200
    html = await response.get_data(as_text=True)
    pending = json.loads(re.search(r'const pending = ("[^"]+");', html)[1])
    headers = {"Origin": ORIGIN, **({"Authorization": authorization} if authorization else {})}
    response = await client.post(PREFIX + "/authorize", json={"pending": pending, "choice": choice}, headers=headers, scheme="https")
    return response


async def exchange(client, identifier, code, verifier, **extra):
    values = {"grant_type": "authorization_code", "client_id": identifier, "redirect_uri": CALLBACK, "code": code, "code_verifier": verifier, "resource": RESOURCE, **extra}
    return await client.post(PREFIX + "/token", data=urlencode(values), headers={"Content-Type": "application/x-www-form-urlencoded"}, scheme="https")


async def grant(client, choice="free", authorization=None, scope=" ".join(SCOPES)):
    identifier = await client_id(client)
    query, verifier = params(identifier, scope)
    approved = await approve(client, query, choice, authorization)
    assert approved.status_code == 200
    callback = (await approved.get_json())["redirect"]
    callback_params = parse_qs(urlsplit(callback).query)
    assert callback_params["state"] == ["opaque-state"] and callback_params["iss"] == [ORIGIN]
    code = callback_params["code"][0]
    response = await exchange(client, identifier, code, verifier)
    assert response.status_code == 200, await response.get_json()
    return identifier, await response.get_json(), code, verifier


async def mcp(client, token, method="initialize", arguments=None):
    message = {"jsonrpc": "2.0", "id": 1, "method": method, "params": arguments or {}}
    return await client.post("/api/v1/agent-access/mcp", headers={"Authorization": "Bearer " + token}, json=message)


def test_full_free_registration_pkce_mcp_refresh_and_revoke(fixture):
    app, service, active, created, redis, fetched = fixture

    async def scenario():
        client = app.test_client()
        response = await client.get("/.well-known/oauth-authorization-server")
        metadata = await response.get_json()
        assert metadata["code_challenge_methods_supported"] == ["S256"]
        assert metadata["authorization_response_iss_parameter_supported"]
        assert (await client.get("/.well-known/oauth-protected-resource/api/v1/agent-access/mcp")).status_code == 200
        unauth = await client.post("/api/v1/agent-access/mcp", json={})
        assert unauth.status_code == 401 and "resource_metadata=" in unauth.headers["WWW-Authenticate"]
        identifier, token, _, _ = await grant(client)
        assert len(created) == 1 and token["expires_in"] <= 900 and token["token_type"] == "Bearer"
        initialized = await mcp(client, token["access_token"])
        assert initialized.status_code == 200
        op = next(x for x in operations(app).values() if x["method"] == "POST")
        executed = await mcp(client, token["access_token"], "tools/call", {"name": "swipies_execute", "arguments": {"operation_id": op["operation_id"], "body": {"name": "customer-docs"}}})
        result = await executed.get_json()
        assert not result["result"].get("isError")
        refresh = await client.post(
            PREFIX + "/token",
            data=urlencode({"grant_type": "refresh_token", "client_id": identifier, "refresh_token": token["refresh_token"], "resource": RESOURCE}),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert refresh.status_code == 200
        rotated = await refresh.get_json()
        assert rotated["refresh_token"] != token["refresh_token"]
        response = await client.post(PREFIX + "/revoke", data=urlencode({"client_id": identifier, "token": rotated["access_token"]}), headers={"Content-Type": "application/x-www-form-urlencoded"})
        assert response.status_code == 200
        assert (await mcp(client, rotated["access_token"])).status_code == 401
        assert "key-new-free" not in active
        for key in redis.scan_iter():
            value = redis.get(key)
            if b":rate-" not in key:
                assert value.startswith(b"enc:v2:") and b"key-new-free" not in value

    run(scenario())


def test_existing_owner_and_cimd(fixture):
    app, service, active, created, redis, fetched = fixture

    async def scenario():
        client = app.test_client()
        query, verifier = params("https://chatgpt.com/oauth/client.json")
        approved = await approve(client, query, "existing", "Bearer owner-a")
        assert approved.status_code == 200 and not created
        code = parse_qs(urlsplit((await approved.get_json())["redirect"]).query)["code"][0]
        response = await exchange(client, query["client_id"], code, verifier)
        token = await response.get_json()
        assert response.status_code == 200 and (await mcp(client, token["access_token"])).status_code == 200
        assert fetched == ["https://chatgpt.com/oauth/client.json"]

    run(scenario())


@pytest.mark.parametrize("choice,authorization", [("existing", None), ("existing", "Bearer someone-else"), ("admin", "Bearer owner-a")])
def test_existing_account_requires_own_login(fixture, choice, authorization):
    async def scenario():
        client = fixture[0].test_client()
        query, _ = params(await client_id(client))
        approved = await approve(client, query, choice, authorization)
        assert approved.status_code == 401 and not fixture[3]

    run(scenario())


@pytest.mark.parametrize(
    "overrides",
    [
        {"redirect_uri": "https://evil.example/callback"},
        {"resource": "https://evil.example/mcp"},
        {"code_challenge_method": "plain"},
        {"code_challenge": "short"},
        {"response_type": "token"},
        {"scope": "admin"},
        {"scope": "swipies:write"},
    ],
)
def test_invalid_authorization_is_never_redirected(fixture, overrides):
    async def scenario():
        client = fixture[0].test_client()
        query, _ = params(await client_id(client), **overrides)
        response = await client.get(PREFIX + "/authorize", query_string=query, scheme="https")
        assert response.status_code == 400 and "Location" not in response.headers

    run(scenario())


@pytest.mark.parametrize(
    "uri",
    [
        "http://chatgpt.com/callback",
        "https://chatgpt.com.evil.example/callback",
        "https://chatgpt.com:443/callback",
        "https://user@chatgpt.com/callback",
        "https://chatgpt.com/callback#fragment",
        "https://127.0.0.1/callback",
        "https://chatgpt.com/auth/logout?redirect=https://evil.example",
        "https://chatgpt.com/connector/oauth/../logout",
        CALLBACK + "?redirect=https://evil.example",
    ],
)
def test_dcr_redirect_allowlist(fixture, uri):
    async def scenario():
        response = await fixture[0].test_client().post(PREFIX + "/register", json={"redirect_uris": [uri]})
        assert response.status_code == 400

    run(scenario())


@pytest.mark.parametrize(
    "identifier", ["https://127.0.0.1/client.json", "https://chatgpt.com.evil.example/oauth/client.json", "https://chatgpt.com/oauth/client.json?x=1", "https://chatgpt.com/oauth/../../client.json"]
)
def test_cimd_ssrf_is_not_fetched(fixture, identifier):
    assert fixture[1].client(identifier) is None and not fixture[5]


def test_csrf_consent_deny_and_cookie_bound_browser(fixture):
    async def scenario():
        client = fixture[0].test_client()
        query, _ = params(await client_id(client))
        response = await client.get(PREFIX + "/authorize", query_string=query, scheme="https")
        pending = json.loads(re.search(r'const pending = ("[^"]+");', await response.get_data(as_text=True))[1])
        assert "frame-ancestors" in response.headers["Content-Security-Policy"]
        for other, origin in [(client, "https://evil.example"), (fixture[0].test_client(), ORIGIN)]:
            response = await other.post(PREFIX + "/authorize", json={"pending": pending, "choice": "free"}, headers={"Origin": origin}, scheme="https")
            assert response.status_code == 403
        response = await client.post(PREFIX + "/authorize", json={"pending": pending, "choice": "deny"}, headers={"Origin": ORIGIN}, scheme="https")
        assert response.status_code == 200
        callback = parse_qs(urlsplit((await response.get_json())["redirect"]).query)
        assert callback["error"] == ["access_denied"] and callback["iss"] == [ORIGIN] and not fixture[3]
        response = await client.post(PREFIX + "/authorize", json={"pending": pending, "choice": "free"}, headers={"Origin": ORIGIN}, scheme="https")
        assert response.status_code == 403

    run(scenario())


def test_wrong_pkce_resource_client_and_redirect(fixture):
    async def scenario():
        client = fixture[0].test_client()
        identifier = await client_id(client)
        query, verifier = params(identifier)
        approved = await approve(client, query)
        code = parse_qs(urlsplit((await approved.get_json())["redirect"]).query)["code"][0]
        for changes in [{"code_verifier": "b" * 48}, {"resource": "https://other.example/mcp"}, {"client_id": await client_id(client)}, {"redirect_uri": CALLBACK + "?other=1"}]:
            assert (await exchange(client, identifier, code, verifier, **changes)).status_code >= 400
        assert (await exchange(client, identifier, code, verifier)).status_code == 200

    run(scenario())


def test_code_and_refresh_replay_revoke_grant(fixture):
    async def scenario():
        client = fixture[0].test_client()
        identifier, token, code, verifier = await grant(client)
        assert (await exchange(client, identifier, code, verifier)).status_code >= 400
        assert (await mcp(client, token["access_token"])).status_code == 401

    run(scenario())


def test_rotating_refresh_replay_revokes_new_tokens(fixture):
    async def scenario():
        client = fixture[0].test_client()
        identifier, token, _, _ = await grant(client)
        body = urlencode({"grant_type": "refresh_token", "client_id": identifier, "refresh_token": token["refresh_token"], "resource": RESOURCE})
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        first = await client.post(PREFIX + "/token", data=body, headers=headers)
        assert first.status_code == 200
        second = await client.post(PREFIX + "/token", data=body, headers=headers)
        assert second.status_code >= 400
        assert (await mcp(client, (await first.get_json())["access_token"])).status_code == 401

    run(scenario())


def test_read_only_scope_cannot_write_and_no_refresh_without_offline(fixture):
    async def scenario():
        client = fixture[0].test_client()
        _, token, _, _ = await grant(client, scope="swipies:read")
        assert "refresh_token" not in token
        assert (await mcp(client, token["access_token"], "tools/list")).status_code == 200
        op = next(x for x in operations(fixture[0]).values() if x["method"] == "POST")
        denied = await mcp(client, token["access_token"], "tools/call", {"name": "swipies_execute", "arguments": {"operation_id": op["operation_id"]}})
        assert denied.status_code == 403 and "insufficient_scope" in denied.headers["WWW-Authenticate"]
        assert (await mcp(client, "legacy-key", "tools/list")).status_code == 200

    run(scenario())


def test_real_redis_lua_consumes_once_across_threads(fixture):
    store = fixture[1].store
    store.put("code", "synthetic-code", {"grant_id": "one"}, 300)
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: store.consume("code", "synthetic-code"), range(16)))
    assert sum(value is not None for value in results) == 1
    assert store.get("code-used", "synthetic-code") == {"grant_id": "one"}


def test_disabled_oauth_does_not_break_existing_api_keys(fixture):
    fixture[1].enabled = lambda: False

    async def scenario():
        client = fixture[0].test_client()
        assert (await client.get(PREFIX + "/server-metadata")).status_code == 503
        manifest = await (await client.get("/api/v1/agent-access/manifest")).get_json()
        assert manifest["mcp"]["oauth"] == {"enabled": False}
        assert manifest["mcp"]["authentication_methods"] == ["bearer-api-key"]
        assert (await mcp(client, "legacy-key", "tools/list")).status_code == 200

    run(scenario())


@pytest.mark.parametrize("grants", [["refresh_token", "authorization_code"], ["authorization_code"]])
def test_dcr_accepts_grant_order_and_code_only_clients(fixture, grants):
    async def scenario():
        client = fixture[0].test_client()
        identifier = await client_id(client, grant_types=grants)
        query, verifier = params(identifier, scope="swipies:read")
        approved = await approve(client, query)
        code = parse_qs(urlsplit((await approved.get_json())["redirect"]).query)["code"][0]
        response = await exchange(client, identifier, code, verifier)
        assert response.status_code == 200 and "refresh_token" not in await response.get_json()
        if "refresh_token" not in grants:
            query, _ = params(identifier)
            assert (await client.get(PREFIX + "/authorize", query_string=query, scheme="https")).status_code == 400

    run(scenario())


@pytest.mark.parametrize("scope", ["offline_access", "swipies:write", "swipies:read admin", ""])
def test_refresh_requires_read_and_no_unknown_scopes(fixture, scope):
    async def scenario():
        client = fixture[0].test_client()
        identifier, token, _, _ = await grant(client)
        response = await client.post(
            PREFIX + "/token",
            data=urlencode({"grant_type": "refresh_token", "client_id": identifier, "refresh_token": token["refresh_token"], "resource": RESOURCE, "scope": scope}),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert response.status_code == 400 and (await response.get_json())["error"] == "invalid_scope"
        assert (await mcp(client, token["access_token"])).status_code == 200

    run(scenario())


def test_refresh_can_only_narrow_granted_scopes(fixture):
    async def scenario():
        client = fixture[0].test_client()
        identifier, token, _, _ = await grant(client, scope="swipies:read offline_access")
        values = {"grant_type": "refresh_token", "client_id": identifier, "refresh_token": token["refresh_token"], "resource": RESOURCE, "scope": "swipies:read swipies:write offline_access"}
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        response = await client.post(PREFIX + "/token", data=urlencode(values), headers=headers)
        assert response.status_code == 400
        values["scope"] = "swipies:read"
        response = await client.post(PREFIX + "/token", data=urlencode(values), headers=headers)
        assert response.status_code == 200
        narrowed = await response.get_json()
        assert narrowed["scope"] == "swipies:read" and "refresh_token" not in narrowed

    run(scenario())


@pytest.mark.parametrize("change", ["key-revoked", "expired", "resource", "read-scope"])
def test_inactive_or_wrong_audience_token_fails_closed(fixture, change):
    async def scenario():
        client = fixture[0].test_client()
        _, token, _, _ = await grant(client)
        service = fixture[1]
        record = service.store.get("access", token["access_token"])
        if change == "key-revoked":
            fixture[2].clear()
        elif change == "expired":
            record["expires"] = 0
        elif change == "resource":
            record["resource"] = "https://other.example/mcp"
        else:
            record["scopes"] = ["swipies:write"]
        service.store.put("access", token["access_token"], record, 60)
        assert (await mcp(client, token["access_token"])).status_code == 401

    run(scenario())


def test_redis_loss_never_falls_back_to_api_authentication(fixture, monkeypatch):
    async def scenario():
        client = fixture[0].test_client()
        _, token, _, _ = await grant(client)

        def unavailable(*args, **kwargs):
            raise ConnectionError("synthetic outage")

        monkeypatch.setattr(fixture[4], "get", unavailable)
        assert (await mcp(client, token["access_token"])).status_code == 503

    run(scenario())


def test_chunked_and_duplicate_token_parameters_rejected(fixture):
    async def scenario():
        client = fixture[0].test_client()
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        for body in ["resource=" + RESOURCE + "&resource=" + RESOURCE, "x=" + "a" * 17000]:
            async with client.request(PREFIX + "/token", method="POST", headers=headers) as connection:
                await connection.send(body.encode())
                await connection.send_complete()
            response = await connection.as_response()
            assert response.status_code == 400
        assert (await client.post(PREFIX + "/register", json=[])).status_code == 400

    run(scenario())


def test_current_chatgpt_callback_paths_and_cimd_cache(fixture):
    assert fixture[1].safe_redirect("https://chatgpt.com/connector/oauth/abc_123-xyz")
    identifier = "https://chatgpt.com/oauth/abc_123-xyz/client.json"
    assert fixture[1].client(identifier)["grant_types"] == ["authorization_code", "refresh_token"]
    assert fixture[1].client(identifier) and fixture[5] == [identifier]


def test_rate_limit_blocks_registration_before_provisioning(fixture):
    async def scenario():
        client = fixture[0].test_client()
        for _ in range(30):
            await client_id(client)
        response = await client.post(PREFIX + "/register", json={"redirect_uris": [CALLBACK]})
        assert response.status_code == 400 and not fixture[3]

    run(scenario())


def test_enabled_manifest_discovery_and_missing_master_secret_fail_closed(fixture, monkeypatch):
    import sys
    import importlib.util
    from types import ModuleType, SimpleNamespace
    from api.utils.key_crypto import InsecureSecretKeyError

    spec = importlib.util.spec_from_file_location("oauth_factory_test", Path(__file__).parents[1] / "api/db/services/agent_oauth_service.py")
    adapter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adapter)
    make_service = adapter.make_service

    module = ModuleType("rag.utils.redis_conn")
    module.REDIS_CONN = SimpleNamespace(REDIS=fixture[4])
    monkeypatch.setitem(sys.modules, "rag.utils.redis_conn", module)
    monkeypatch.setenv("SWIPIES_AGENT_OAUTH_ENABLED", "1")
    monkeypatch.delenv("RAGFLOW_SECRET_KEY", raising=False)
    monkeypatch.delenv("SECRET_KEY", raising=False)
    with pytest.raises(InsecureSecretKeyError):
        make_service()
    monkeypatch.setenv("RAGFLOW_SECRET_KEY", "synthetic-oauth-master-" + "z" * 40)
    assert make_service().enabled()

    async def scenario():
        response = await fixture[0].test_client().get("/api/v1/agent-access/manifest")
        data = await response.get_json()
        assert data["mcp"]["oauth"]["enabled"] and data["mcp"]["oauth"]["resource"] == RESOURCE
        assert data["mcp"]["authentication_methods"] == ["bearer-api-key", "oauth2-pkce"]
        assert response.headers["Cache-Control"] == "no-store"

    run(scenario())


def test_cimd_fetch_does_not_block_other_api_requests(fixture):
    import time
    import threading

    original = fixture[1].fetch_metadata
    started = threading.Event()
    release = threading.Event()

    def slow_fetch(url):
        started.set()
        release.wait(2)
        return original(url)

    fixture[1].fetch_metadata = slow_fetch

    async def scenario():
        client = fixture[0].test_client()
        query, _ = params("https://chatgpt.com/oauth/client.json")
        task = asyncio.create_task(client.get(PREFIX + "/authorize", query_string=query, scheme="https"))
        try:
            deadline = time.monotonic() + 1
            while not started.is_set() and time.monotonic() < deadline:
                await asyncio.sleep(0.005)
            assert started.is_set() and not release.is_set()
            assert not task.done(), "CIMD fetched synchronously in the event loop"
            response = await asyncio.wait_for(client.get("/api/v1/agent-access/manifest"), timeout=0.5)
            assert response.status_code == 200 and not task.done()
        finally:
            release.set()
            response = await task
        assert response.status_code == 200

    run(scenario())


def test_encrypted_state_cannot_be_moved_to_a_chosen_token_or_family(fixture):
    store = fixture[1].store
    store.put("access", "original-opaque-token", {"principal": "synthetic-owner"}, 60)
    ciphertext = fixture[4].get(store.key("access", "original-opaque-token"))
    for family, key in [("access", "attacker-chosen-token"), ("refresh", "original-opaque-token")]:
        fixture[4].set(store.key(family, key), ciphertext, ex=60)
        with pytest.raises(ValueError, match="context mismatch"):
            store.get(family, key)


def test_encrypted_deadline_survives_redis_ttl_extension(fixture, monkeypatch):
    import time

    store = fixture[1].store
    store.put("access", "expired-synthetic-token", {"principal": "synthetic-owner"}, 1)
    ciphertext = fixture[4].get(store.key("access", "expired-synthetic-token"))
    fixture[4].set(store.key("access", "expired-synthetic-token"), ciphertext, ex=300)
    original = time.time
    monkeypatch.setattr("api.agent_oauth.time.time", lambda: original() + 2)
    assert store.get("access", "expired-synthetic-token") is None
