"""Exercise production model definitions/auth/registration on isolated SQLite.

Compile only the relevant definitions from their real sources to avoid importing
the server's deployment config, optional parsers or production DB connection.
No model fields, auth functions or registration-record builders are re-created.
"""
import ast
import asyncio
from collections.abc import Iterable
from datetime import datetime
from functools import wraps
import importlib.util
import logging
import os
import operator
from pathlib import Path
import sys
import time
from types import ModuleType, SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import peewee as pw
import pytest
from quart import Quart, Blueprint, current_app, g, jsonify, request, session
from quart_auth import AuthUser, Unauthorized
from werkzeug.local import LocalProxy

ROOT = Path(__file__).resolve().parents[1]


def definitions(path, names, namespace, strip_decorators=False):
    tree = ast.parse((ROOT / path).read_text(encoding="utf-8"))
    nodes = [node for node in tree.body if getattr(node, "name", None) in names]
    assert {node.name for node in nodes} == set(names)
    if strip_decorators:
        for node in nodes:
            node.decorator_list = []
    future = ast.parse("from __future__ import annotations").body
    exec(compile(ast.fix_missing_locations(ast.Module(body=future + nodes, type_ignores=[])), str(ROOT / path), "exec"), namespace)


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def server(monkeypatch):
    db = pw.SqliteDatabase(":memory:")
    settings = SimpleNamespace(REGISTER_ENABLED=True, DATABASE_TYPE="mysql", PARSERS="naive", CHAT_MDL="chat-model", EMBEDDING_MDL="embedding-model")
    namespace = {**vars(pw), "os": os, "operator": operator, "DB": db, "AuthUser": AuthUser, "EmptyStringCharField": pw.CharField, "get_uuid": lambda: uuid4().hex, "settings": settings, "current_timestamp": lambda: int(time.time() * 1000), "timestamp_to_date": lambda ts: datetime.fromtimestamp(ts / 1000), "AUTO_DATE_TIMESTAMP_FIELD_PREFIX": {"create", "update"}}
    # Real BaseModel date normalization and real persistent table definitions.
    definitions("api/db/db_models.py", {"BaseModel", "DataBaseModel", "User", "Tenant", "UserTenant", "File", "APIToken"}, namespace)
    models = [namespace[name] for name in ("User", "Tenant", "UserTenant", "File", "APIToken")]
    db.create_tables(models)
    User, Tenant, Membership, File, APIToken = models
    def stub(name, **values):
        mod = ModuleType(name)
        mod.__dict__.update(values)
        monkeypatch.setitem(sys.modules, name, mod)
        return mod
    stub("api.db.db_models", DB=db, **{model.__name__: model for model in models})
    stub("common", settings=settings)
    stub("common.misc_utils", get_uuid=lambda: uuid4().hex)
    stub("api.db.services.global_instance_service", GlobalInstanceService=SimpleNamespace(get_instance_stats=lambda: {}))
    stub("api.apps.services.models_api_service", parse_and_resolve_model_components=lambda value, _: (value, "default", "OpenAI"))
    record_namespace = {"settings": settings, "logging": logging, "get_uuid": lambda: uuid4().hex, "FileType": SimpleNamespace(FOLDER=SimpleNamespace(value="folder")), "UserTenantRole": SimpleNamespace(OWNER="owner")}
    definitions("api/apps/restful_apis/user_api.py", {"prepare_user_registration"}, record_namespace)
    stub("api.apps.restful_apis.user_api", prepare_user_registration=record_namespace["prepare_user_registration"])
    def query_users(**values):
        return list(User.select().where(*[getattr(User, name) == value for name, value in values.items()]))
    auth = {"wraps": wraps, "Iterable": Iterable, "os": os, "time": time, "logging": logging, "request": request, "session": session, "g": g, "current_app": current_app, "UserService": SimpleNamespace(query=query_users), "APIToken": APIToken, "StatusEnum": SimpleNamespace(VALID=SimpleNamespace(value="1")), "AUTH_JWT": "JWT", "AUTH_API": "API", "AUTH_BETA": "BETA", "DEFAULT_AUTH_TYPES": ("JWT", "API"), "QuartAuthUnauthorized": Unauthorized}
    definitions("api/apps/__init__.py", {"_normalize_auth_types", "_load_user_from_session", "_load_user", "login_required"}, auth)
    app = Quart(__name__)
    app.testing = True
    profile_namespace = {"current_user": LocalProxy(auth["_load_user"]), "UserOnboardingService": SimpleNamespace(is_user_onboarded=lambda _: True), "get_json_result": lambda data: jsonify(code=0, data=data)}
    definitions("api/apps/restful_apis/user_api.py", {"user_profile"}, profile_namespace, strip_decorators=True)
    profile = auth["login_required"](profile_namespace["user_profile"])
    app.add_url_rule("/api/v1/users/me", view_func=profile)
    @app.errorhandler(Unauthorized)
    async def unauthorized(_):
        return jsonify(code=109), 401
    gateway = load("api/agent_access.py", "real_model_gateway")
    service = load("api/db/services/agent_access_service.py", "real_model_registration")
    monkeypatch.setattr(service, "_limit_registration", lambda _: None)
    monkeypatch.setenv("SWIPIES_AGENT_REGISTRATION_ENABLED", "1")
    async def bootstrap(data, address):
        return service.provision(data, address)
    gateway.register_agent_access(app, lambda: auth["_load_user"](("API",)), bootstrap, lambda _: True)
    yield SimpleNamespace(app=app, db=db, User=User, Tenant=Tenant, Membership=Membership, File=File, APIToken=APIToken, service=service, gateway=gateway)
    db.close()


def test_real_models_bootstrap_auth_and_mcp_profile(server):
    async def scenario():
        client = server.app.test_client()
        response = await client.post("/api/v1/agent-access/bootstrap", json={"registration_secret": "a" * 43, "name": "Shop"})
        assert response.status_code == 200
        identity = await response.get_json()
        ident = identity["tenant_id"]
        user = server.User.get_by_id(ident)
        assert not user.is_superuser and user.marketing_consent is False
        assert len(user.access_token) == 32 and user.password.startswith("scrypt:")
        tenant = server.Tenant.get_by_id(ident)
        assert tenant.plan_type == "free" and tenant.llm_id == "chat-model@default@OpenAI"
        member = server.Membership.get(server.Membership.user_id == ident)
        assert member.role == "owner" and member.tenant_id == ident
        root = server.File.get(server.File.tenant_id == ident)
        assert root.parent_id == root.id and root.type == "folder"
        operations = server.gateway.operations(server.app)
        op_id = next(op["operation_id"] for op in operations.values() if op["path"] == "/api/v1/users/me")
        headers = {"Authorization": "Bearer " + identity["api_key"]}
        result = await client.post("/api/v1/agent-access/mcp", headers=headers, json={"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "swipies_execute", "arguments": {"operation_id": op_id}}})
        payload = await result.get_json()
        assert result.status_code == 200 and not payload["result"]["isError"]
        text = payload["result"]["content"][0]["text"]
        import json
        assert json.loads(text)["data"]["data"]["id"] == ident
        leaked = any(value in text for value in (identity["api_key"], user.password, user.access_token))
        assert not leaked, "Credential found in MCP profile response"
    asyncio.run(scenario())


def test_real_api_token_revocation_rejects_mcp(server):
    identity = server.service.provision({"registration_secret": "b" * 43}, "127.0.0.1")
    server.APIToken.update(status="0").execute()
    async def scenario():
        response = await server.app.test_client().post("/api/v1/agent-access/mcp", headers={"Authorization": "Bearer " + identity["api_key"]}, json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        assert response.status_code == 401
    asyncio.run(scenario())


def test_real_model_transaction_rolls_back_all_records(server):
    with patch.object(server.APIToken, "create", side_effect=RuntimeError("simulated write failure")):
        with pytest.raises(RuntimeError):
            server.service.provision({"registration_secret": "c" * 43}, "127.0.0.1")
    assert all(model.select().count() == 0 for model in (server.User, server.Tenant, server.Membership, server.File, server.APIToken))


def test_stdio_client_bootstraps_over_verified_https(server, tmp_path, monkeypatch):
    """Real subprocess + TLS + registration + MCP, including non-ASCII output."""
    import ipaddress
    import socket
    import ssl
    from datetime import timedelta, timezone
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID
    from hypercorn.asyncio import serve
    from hypercorn.config import Config
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
    now = datetime.now(timezone.utc)
    cert = x509.CertificateBuilder().subject_name(subject).issuer_name(subject).public_key(key.public_key()).serial_number(x509.random_serial_number()).not_valid_before(now - timedelta(minutes=1)).not_valid_after(now + timedelta(days=1)).add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True).add_extension(x509.SubjectAlternativeName([x509.DNSName("localhost"), x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]), critical=False).sign(key, hashes.SHA256())
    cert_path = tmp_path / "local-ca.pem"
    key_path = tmp_path / "local-server.pem"
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    config = Config()
    config.bind = [f"127.0.0.1:{port}"]
    config.certfile, config.keyfile = str(cert_path), str(key_path)
    config.accesslog, config.errorlog = None, None
    monkeypatch.delenv("SWIPIES_API_KEY", raising=False)
    async def scenario():
        stop = asyncio.Event()
        task = asyncio.create_task(serve(server.app, config, shutdown_trigger=stop.wait))
        try:
            context = ssl.create_default_context(cafile=str(cert_path))
            for _ in range(100):
                if task.done():
                    await task
                try:
                    _, writer = await asyncio.open_connection("127.0.0.1", port, ssl=context, server_hostname="localhost")
                    writer.close()
                    await writer.wait_closed()
                    break
                except OSError:
                    await asyncio.sleep(0.02)
            else:
                raise RuntimeError("Local HTTPS test server did not start")
            parameters = StdioServerParameters(command=sys.executable, args=[str(ROOT / "tools/swipies_agent_client.py"), "--url", f"https://127.0.0.1:{port}", "--state-file", str(tmp_path / "identity"), "--name", "Магазин"], env={**os.environ, "SSL_CERT_FILE": str(cert_path), "PYTHONIOENCODING": "cp1252"})
            async with stdio_client(parameters) as (read, write):
                async with ClientSession(read, write) as client:
                    assert (await client.initialize()).serverInfo.name == "swipies-agent-access"
                    assert len((await client.list_tools()).tools) == 3
                    op_id = next(op["operation_id"] for op in server.gateway.operations(server.app).values() if op["path"] == "/api/v1/users/me")
                    result = await client.call_tool("swipies_execute", {"operation_id": op_id})
                    assert not result.isError
                    import json
                    assert json.loads(result.content[0].text)["data"]["data"]["nickname"] == "Магазин"
            assert server.User.select().count() == 1
        finally:
            stop.set()
            await task
    asyncio.run(scenario())
