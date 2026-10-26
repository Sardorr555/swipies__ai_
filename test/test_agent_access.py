"""Transport/tenant boundary tests without production services or credentials."""
import asyncio
import importlib.util
import io
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import sys
import types
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from quart import Quart, jsonify, request

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gateway = load("gateway_under_test", "api/agent_access.py")
policy = load("branding_under_test", "api/branding_policy.py")
registration = load("registration_under_test", "api/db/services/agent_access_service.py")
client_module = load("client_under_test", "tools/swipies_agent_client.py")


def run(coro):
    return asyncio.run(coro)


@pytest.fixture
def app():
    app = Quart(__name__)
    app.testing = True
    @app.route("/api/v1/datasets", methods=["GET", "POST"])
    async def datasets():
        """List or create a dataset. JSON body: {name: string}."""
        return jsonify(code=0, data={"identity": request.headers.get("Authorization"), "body": await request.get_json(silent=True), "query": request.args.to_dict()})
    datasets.swipies_auth_types = {"API"}
    @app.route("/api/v1/datasets/<dataset_id>", methods=["GET"])
    async def dataset(dataset_id):
        if dataset_id != request.headers.get("Authorization", "").removeprefix("Bearer "):
            return jsonify(code=109, data=False), 403
        return jsonify(code=0, data={"id": dataset_id})
    dataset.swipies_auth_types = {"API"}
    @app.route("/api/v1/documents/upload", methods=["POST"])
    async def upload():
        files = await request.files
        return jsonify(code=0, data={"filename": files["file"].filename, "content": files["file"].read().decode()})
    upload.swipies_auth_types = {"API"}
    @app.get("/api/v1/models/public")
    async def unprotected():
        return jsonify(secret="must not appear")
    @app.get("/api/v1/admin/users")
    async def admin():
        return jsonify(secret="must not appear")
    admin.swipies_auth_types = {"API"}
    async def bootstrap(data, address):
        registration.validate_registration(data)
        return {"tenant_id": "new-tenant", "created": True}
    gateway.register_agent_access(app, lambda: request.headers.get("Authorization", "").startswith("Bearer "), bootstrap, registration.origin_allowed)
    return app


def rpc(app, method, params=None, token="tenant-a", ident=1, headers=None):
    async def invoke():
        message = {"jsonrpc": "2.0", "id": ident, "method": method}
        if params is not None:
            message["params"] = params
        hdr = {"Authorization": "Bearer " + token} if token else {}
        hdr.update(headers or {})
        response = await app.test_client().post("/api/v1/agent-access/mcp", headers=hdr, json=message)
        return response.status_code, await response.get_json(), response.headers
    return run(invoke())


def test_initialize_and_tools(app):
    status, response, headers = rpc(app, "initialize", {"protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "test", "version": "1"}})
    assert status == 200 and response["result"]["protocolVersion"] == "2025-03-26"
    assert headers["Cache-Control"] == "no-store"
    _, response, _ = rpc(app, "tools/list")
    assert {tool["name"] for tool in response["result"]["tools"]} == {"swipies_list_operations", "swipies_describe_operation", "swipies_execute"}


def test_only_authenticated_user_routes_in_catalog(app):
    catalog = gateway.operations(app)
    assert len(catalog) == 4
    assert all("admin" not in op["path"] and "public" not in op["path"] for op in catalog.values())


@pytest.mark.parametrize("origin", ["https://evil.invalid", "null", "https://api.swipies.app.evil.invalid"])
def test_untrusted_origins_rejected(app, origin):
    assert rpc(app, "initialize", headers={"Origin": origin})[0] == 403


def test_api_key_required(app):
    assert rpc(app, "tools/list", token=None)[0] == 401


def test_notifications_have_empty_202_and_no_side_effect(app):
    async def invoke():
        response = await app.test_client().post("/api/v1/agent-access/mcp", headers={"Authorization": "Bearer a"}, json={"jsonrpc": "2.0", "method": "notifications/initialized"})
        assert response.status_code == 202 and await response.get_data() == b""
    run(invoke())


@pytest.mark.parametrize("value", [[], None, {"jsonrpc": "2.0", "method": "ping", "id": True}, {"jsonrpc": "2.0", "method": "ping", "id": 1, "params": []}])
def test_invalid_rpc_is_safe(app, value):
    async def invoke():
        response = await app.test_client().post("/api/v1/agent-access/mcp", headers={"Authorization": "Bearer a"}, json=value)
        assert (await response.get_json())["error"]["code"] in {-32600, -32602}
    run(invoke())


def operation(app, path, method="GET"):
    return next(op["operation_id"] for op in gateway.operations(app).values() if op["path"] == path and op["method"] == method)


def call(app, args, token="tenant-a"):
    return rpc(app, "tools/call", {"name": "swipies_execute", "arguments": args}, token=token)[1]["result"]


def test_execute_forwards_caller_body_and_query(app):
    result = call(app, {"operation_id": operation(app, "/api/v1/datasets", "POST"), "body": {"name": "catalog"}, "query": {"page": "2"}})
    assert not result["isError"]
    data = json.loads(result["content"][0]["text"])["data"]["data"]
    assert data == {"identity": "Bearer tenant-a", "body": {"name": "catalog"}, "query": {"page": "2"}}


def test_tenant_context_does_not_leak_between_calls(app):
    args = {"operation_id": operation(app, "/api/v1/datasets/<dataset_id>"), "path_parameters": {"dataset_id": "tenant-a"}}
    assert not call(app, args, "tenant-a")["isError"]
    assert call(app, args, "tenant-b")["isError"]
    assert not call(app, args, "tenant-a")["isError"]


@pytest.mark.parametrize("value", ["../admin", "%2fadmin", "a?x=1", "a\\b", "..", "a\nheader"])
def test_path_escape_rejected(app, value):
    result = call(app, {"operation_id": operation(app, "/api/v1/datasets/<dataset_id>"), "path_parameters": {"dataset_id": value}})
    assert result["isError"]


def test_path_converter_supports_provider_model_names_without_traversal():
    op = {"path": "/api/v1/providers/vendor/models/<path:model_name>", "path_parameters": ["model_name"]}
    assert gateway.render_path(op, {"model_name": "vendor/model"}).endswith("/vendor/model")
    with pytest.raises(ValueError):
        gateway.render_path(op, {"model_name": "vendor/../admin"})


def test_multipart_upload(app):
    result = call(app, {"operation_id": operation(app, "/api/v1/documents/upload", "POST"), "files": [{"field": "file", "filename": "catalog.txt", "base64": "aGVsbG8="}]})
    assert not result["isError"]
    assert json.loads(result["content"][0]["text"])["data"]["data"] == {"filename": "catalog.txt", "content": "hello"}


def test_unknown_operation_cannot_dispatch_arbitrary_url(app):
    assert call(app, {"operation_id": "http://localhost/admin"})["isError"]


def test_large_results_are_bounded(app, monkeypatch):
    @app.get("/api/v1/files/large")
    async def large():
        return "x" * 2048
    large.swipies_auth_types = {"API"}
    monkeypatch.setattr(gateway, "MAX_RESULT", 128)
    result = call(app, {"operation_id": operation(app, "/api/v1/files/large")})
    assert result["isError"] and "8 MiB" in result["content"][0]["text"]


def test_public_manifest_does_not_need_account(app):
    async def invoke():
        response = await app.test_client().get("/api/v1/agent-access/manifest")
        data = await response.get_json()
        assert response.status_code == 200
        assert data["branding"]["removal_plans"] == ["plus", "pro"]
        assert data["bootstrap"]["required"] == ["registration_secret"]
    run(invoke())


def test_binary_download_preserves_bytes(app):
    from quart import Response
    @app.get("/api/v1/files/binary")
    async def binary():
        return Response(b"\x00\xff\x01", content_type="application/octet-stream")
    binary.swipies_auth_types = {"API"}
    result = call(app, {"operation_id": operation(app, "/api/v1/files/binary")})
    assert not result["isError"]
    assert json.loads(result["content"][0]["text"])["data"]["base64"] == "AP8B"


def test_bulk_upload_supports_repeated_file_fields(app):
    @app.post("/api/v1/documents/bulk")
    async def bulk():
        files = await request.files
        return jsonify(code=0, data=[file.filename for file in files.getlist("file")])
    bulk.swipies_auth_types = {"API"}
    result = call(app, {"operation_id": operation(app, "/api/v1/documents/bulk", "POST"), "files": [{"filename": "one.txt", "base64": "aGk="}, {"filename": "two.txt", "base64": "aGk="}]})
    assert not result["isError"]
    assert json.loads(result["content"][0]["text"])["data"]["data"] == ["one.txt", "two.txt"]


def test_path_converter_cannot_select_an_uncatalogued_endpoint(app):
    @app.get("/api/v1/providers/<path:model_name>")
    async def model(model_name):
        return jsonify(code=0, data=model_name)
    model.swipies_auth_types = {"API"}
    @app.get("/api/v1/providers/private")
    async def private():
        return jsonify(code=0, data="not a tenant operation")
    result = call(app, {"operation_id": operation(app, "/api/v1/providers/<path:model_name>"), "path_parameters": {"model_name": "private"}})
    assert result["isError"]


def test_mcp_limits_chunked_body_without_content_length(app, monkeypatch):
    import httpx
    monkeypatch.setattr(gateway, "MAX_BODY", 256)
    async def body():
        yield json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"padding": "x" * 1000}}).encode()
    async def invoke():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://api.swipies.app") as client:
            response = await client.post("/api/v1/agent-access/mcp", headers={"Authorization": "Bearer a", "Content-Type": "application/json"}, content=body())
            assert response.status_code == 413
    run(invoke())


@pytest.mark.parametrize("scheme", ["Bearer", "BEARER", "bEaReR"])
def test_mcp_redacts_nested_credentials_and_credential_echo(scheme):
    key = "synthetic-test-only-credential-" + "x" * 20
    value = {"data": [{"access_token": "synthetic-login", "config": {"client_secret": "synthetic-provider"}, "message": "echo " + key}]}
    cleaned = gateway.redact_response(value, scheme + " " + key)
    assert cleaned["data"][0]["access_token"] == "[REDACTED]"
    assert cleaned["data"][0]["config"]["client_secret"] == "[REDACTED]"
    leaked = any(secret in json.dumps(cleaned) for secret in (key, "synthetic-login", "synthetic-provider"))
    assert not leaked, "Sensitive tool response field was not redacted"


def test_concurrent_clients_never_read_partial_credential(tmp_path, monkeypatch):
    original = client_module.os.fdopen
    def delayed(*args, **kwargs):
        time.sleep(0.05)
        return original(*args, **kwargs)
    monkeypatch.setattr(client_module.os, "fdopen", delayed)
    monkeypatch.setattr(client_module, "_windows_protect", lambda value, decrypt=False: value)
    path = tmp_path / "shared-identity"
    with ThreadPoolExecutor(max_workers=8) as pool:
        values = list(pool.map(lambda _: client_module.registration_secret(path), range(16)))
    assert all(len(value) >= 43 for value in values)
    assert len(set(values)) == 1


def test_timeout_cancels_the_internal_request_without_retry(app, monkeypatch):
    state = {"started": 0, "cleaned": False}
    @app.post("/api/v1/tasks/slow")
    async def slow():
        state["started"] += 1
        try:
            await asyncio.sleep(1)
        finally:
            state["cleaned"] = True
        return jsonify(code=0)
    slow.swipies_auth_types = {"API"}
    monkeypatch.setattr(gateway, "OPERATION_TIMEOUT", 0.02)
    result = call(app, {"operation_id": operation(app, "/api/v1/tasks/slow", "POST")})
    assert result["isError"]
    assert state == {"started": 1, "cleaned": True}


def test_bootstrap_retries_a_transient_error_with_same_identity(tmp_path, monkeypatch):
    monkeypatch.delenv("SWIPIES_API_KEY", raising=False)
    monkeypatch.setattr(client_module, "_windows_protect", lambda value, decrypt=False: value)
    monkeypatch.setattr(client_module.time, "sleep", lambda _: None)
    bridge = client_module.Bridge("https://example.com", tmp_path / "identity")
    attempts = []
    def post(path, data, authenticated=True):
        if authenticated:
            return {"jsonrpc": "2.0", "id": data["id"], "result": {}}
        attempts.append(data["registration_secret"])
        if len(attempts) == 1:
            raise client_module.HTTPFailure(503)
        return {"api_key": "ragflow-" + data["registration_secret"]}
    monkeypatch.setattr(bridge, "post", post)
    bridge.send({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
    assert len(attempts) == 2 and attempts[0] == attempts[1]


@pytest.mark.skipif(client_module.os.name != "nt", reason="Windows DPAPI integration")
def test_windows_dpapi_credential_roundtrip(tmp_path):
    path = tmp_path / "protected-identity"
    first = client_module.registration_secret(path)
    second = client_module.registration_secret(path)
    assert first == second and len(first) >= 43
    leaked = first in path.read_text(encoding="utf-8")
    assert not leaked, "Credential persisted without DPAPI encryption"


def test_client_does_not_retry_an_authenticated_write(tmp_path, monkeypatch):
    bridge = client_module.Bridge("https://example.com", tmp_path / "identity")
    bridge.api_key = "synthetic-test-key"
    attempts = []
    def post(*args, **kwargs):
        attempts.append(1)
        raise client_module.HTTPFailure(503)
    monkeypatch.setattr(bridge, "post", post)
    with pytest.raises(client_module.HTTPFailure):
        bridge.send({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "swipies_execute"}})
    assert len(attempts) == 1


@pytest.mark.parametrize("plan,required", [(None, True), ("free", True), ("enterprise", True), ("custom", True), ("premium", True), ("plus", False), ("pro", False), (" PRO ", False)])
def test_only_plus_pro_remove_branding(plan, required):
    assert policy.branding_required(plan) is required


def test_expired_or_invalid_subscription_keeps_branding():
    now = datetime.now(timezone.utc)
    for plan in ("plus", "pro"):
        assert policy.branding_required(plan, now - timedelta(seconds=1), now)
        assert policy.branding_required(plan, "invalid", now)
        assert policy.branding_required(plan, 12345, now)
        assert not policy.branding_required(plan, now + timedelta(days=1), now)


def test_only_complete_footer_prevents_duplicate_branding():
    line = "Generated by [Swipies AI](https://swipies.app?ref=tenant) — Sent via Swipies AI Platform"
    assert not policy.attribution_present("Visit swipies.app", line)
    assert not policy.attribution_present("Swipies AI", line)
    assert policy.attribution_present("answer\n" + line, line)
    assert policy.attribution_present("answer\n" + line.replace("?ref=tenant", ""), line)


@pytest.mark.parametrize("ending", ["message_end", "workflow_finished", "user_inputs", None])
def test_message_only_canvas_attribution_precedes_terminal_event(ending):
    async def events():
        yield {"event": "message", "data": {"content": "Static answer"}}
        if ending:
            yield {"event": ending, "data": {}}
    async def invoke():
        return [event async for event in policy.brand_agent_events(events(), lambda _: " [Swipies]")]
    result = run(invoke())
    assert result[1]["data"]["content"] == " [Swipies]"
    if ending:
        assert result[2]["event"] == ending


def test_paid_canvas_preserves_events():
    async def events():
        yield {"event": "message", "data": {"content": "Paid answer"}}
        yield {"event": "message_end", "data": {}}
    async def invoke():
        return [event async for event in policy.brand_agent_events(events(), lambda _: "")]
    assert len(run(invoke())) == 2


def test_registration_rejects_privilege_injection():
    with pytest.raises(ValueError):
        registration.validate_registration({"registration_secret": "x" * 43, "plan_type": "pro"})
    with pytest.raises(ValueError):
        registration.validate_registration({"registration_secret": "short"})


def test_forwarded_ip_is_only_accepted_from_trusted_proxy(monkeypatch):
    monkeypatch.setenv("SWIPIES_AGENT_TRUSTED_PROXIES", "127.0.0.1/32")
    assert registration.client_address("127.0.0.1", "203.0.113.4") == "203.0.113.4"
    assert registration.client_address("203.0.113.1", "203.0.113.4") == "203.0.113.1"
    assert registration.client_address("127.0.0.1", "forged,header") == "127.0.0.1"


def test_bootstrap_cache_and_no_email_requirement(app):
    async def invoke():
        response = await app.test_client().post("/api/v1/agent-access/bootstrap", json={"registration_secret": "x" * 43})
        assert response.status_code == 200 and response.headers["Cache-Control"] == "no-store"
        assert (await response.get_json())["created"]
    run(invoke())


def test_registration_failure_never_leaks_secret():
    app = Quart(__name__)
    async def bootstrap(data, _):
        raise RuntimeError(data["registration_secret"])
    gateway.register_agent_access(app, lambda: False, bootstrap, lambda _: True)
    async def invoke():
        response = await app.test_client().post("/api/v1/agent-access/bootstrap", json={"registration_secret": "x" * 43})
        assert response.status_code == 503
        assert "x" * 43 not in (await response.get_data()).decode()
    run(invoke())


def test_stdio_bridge_persists_identity_before_registering(tmp_path):
    with patch.object(client_module, "_windows_protect", side_effect=lambda v, decrypt=False: v):
        path = tmp_path / "identity"
        first = client_module.registration_secret(path)
        assert len(first) >= 43
        assert client_module.registration_secret(path) == first


@pytest.mark.parametrize("url", ["http://example.com", "https://user:password@example.com", "https://example.com/path", "https://example.com/?key=secret"])
def test_stdio_bridge_only_accepts_https_origins(url):
    with pytest.raises(ValueError):
        client_module.validate_url(url)


def test_stdio_bridge_registers_once_and_keeps_bearer_out_of_json(tmp_path):
    bridge = client_module.Bridge("https://example.com", tmp_path / "credential")
    bridge.api_key = None
    requests = []
    def post(path, data, authenticated=True):
        requests.append((path, data, authenticated))
        if not authenticated:
            assert bridge.state_file.exists()
            return {"api_key": "test-key"}
        return {"jsonrpc": "2.0", "id": data["id"], "result": {}}
    with patch.object(client_module, "_windows_protect", side_effect=lambda v, decrypt=False: v), patch.object(bridge, "post", side_effect=post):
        bridge.send({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
        bridge.send({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    assert len(requests) == 3
    assert requests[0][2] is False
    assert all("test-key" not in json.dumps(req[1]) for req in requests[1:])


def test_official_mcp_sdk_can_initialize_discover_and_execute(app):
    import httpx
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client
    def factory(headers=None, timeout=None, auth=None):
        return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), headers=headers, timeout=timeout, auth=auth)
    async def invoke():
        async with streamablehttp_client("https://api.swipies.app/api/v1/agent-access/mcp", headers={"Authorization": "Bearer tenant-a"}, httpx_client_factory=factory) as (read, write, _):
            async with ClientSession(read, write) as session:
                initialized = await session.initialize()
                assert initialized.serverInfo.name == "swipies-agent-access"
                assert len((await session.list_tools()).tools) == 3
                listing = await session.call_tool("swipies_list_operations", {"keyword": "datasets"})
                assert not listing.isError
                response = await session.call_tool("swipies_execute", {"operation_id": operation(app, "/api/v1/datasets")})
                assert not response.isError
    run(invoke())


@pytest.fixture
def provisioning_db(monkeypatch):
    import peewee as pw
    db = pw.SqliteDatabase(":memory:")
    class User(pw.Model):
        id = pw.CharField(primary_key=True)
        status = pw.CharField(default="1")
        class Meta:
            database = db
    class Tenant(pw.Model):
        id = pw.CharField(primary_key=True)
        name = pw.CharField()
        plan_type = pw.CharField(default="free")
        class Meta:
            database = db
    class APIToken(pw.Model):
        tenant_id = pw.CharField()
        token = pw.CharField(unique=True)
        status = pw.CharField(default="1")
        class Meta:
            database = db
    class Membership(pw.Model):
        id = pw.CharField(primary_key=True)
        tenant_id = pw.CharField()
        class Meta:
            database = db
    class File(pw.Model):
        id = pw.CharField(primary_key=True)
        class Meta:
            database = db
    db.create_tables([User, Tenant, APIToken, Membership, File])
    def prepare_user_registration(ident, values):
        assert values["marketing_consent"] is False and values["login_channel"] == "agent"
        values["id"] = ident
        values["is_superuser"] = False
        return {"id": ident, "name": values["nickname"]}, {"tenant_id": ident}, {"id": "root"}
    def module(name, **attrs):
        mod = types.ModuleType(name)
        mod.__dict__.update(attrs)
        monkeypatch.setitem(sys.modules, name, mod)
    module("api.db.db_models", DB=db, User=User, APIToken=APIToken, Tenant=Tenant, UserTenant=Membership, File=File)
    module("api.apps.restful_apis.user_api", prepare_user_registration=prepare_user_registration)
    module("common", settings=SimpleNamespace(REGISTER_ENABLED=True))
    module("common.misc_utils", get_uuid=lambda: "random-login-identifier")
    monkeypatch.setattr(registration, "_limit_registration", lambda _: None)
    monkeypatch.setenv("SWIPIES_AGENT_REGISTRATION_ENABLED", "1")
    yield SimpleNamespace(User=User, Tenant=Tenant, APIToken=APIToken, Membership=Membership, File=File)
    db.close()


def test_bootstrap_is_idempotent_and_assigns_free_plan(provisioning_db):
    data = {"registration_secret": "x" * 43, "name": "Store"}
    first = registration.provision(data, "127.0.0.1")
    second = registration.provision(data, "127.0.0.1")
    assert first["created"] and not second["created"]
    assert first["tenant_id"] == second["tenant_id"]
    assert provisioning_db.User.select().count() == 1
    assert provisioning_db.APIToken.select().count() == 1
    assert provisioning_db.Tenant.get_by_id(first["tenant_id"]).plan_type == "free"


def test_revoked_bootstrap_key_is_not_recreated(provisioning_db):
    data = {"registration_secret": "x" * 43}
    registration.provision(data, "127.0.0.1")
    provisioning_db.APIToken.update(status="0").execute()
    with pytest.raises(PermissionError):
        registration.provision(data, "127.0.0.1")
    assert provisioning_db.APIToken.select().count() == 1


def test_failed_key_creation_rolls_back_user_and_tenant(provisioning_db):
    with patch.object(provisioning_db.APIToken, "create", side_effect=RuntimeError("database unavailable")):
        with pytest.raises(RuntimeError):
            registration.provision({"registration_secret": "x" * 43}, "127.0.0.1")
    assert provisioning_db.User.select().count() == 0
    assert provisioning_db.Tenant.select().count() == 0
    assert provisioning_db.Membership.select().count() == 0
    assert provisioning_db.File.select().count() == 0


def test_registration_setting_blocks_new_accounts(provisioning_db, monkeypatch):
    monkeypatch.setenv("SWIPIES_AGENT_REGISTRATION_ENABLED", "0")
    with pytest.raises(PermissionError):
        registration.provision({"registration_secret": "x" * 43}, "127.0.0.1")
    assert provisioning_db.User.select().count() == 0


def test_existing_account_reconnects_when_registration_disabled(provisioning_db, monkeypatch):
    data = {"registration_secret": "x" * 43}
    registration.provision(data, "127.0.0.1")
    monkeypatch.setenv("SWIPIES_AGENT_REGISTRATION_ENABLED", "0")
    assert not registration.provision(data, "127.0.0.1")["created"]
