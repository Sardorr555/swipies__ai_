"""OAuthLib authorization-code/PKCE adapter for the tenant MCP gateway.

All persistence, encryption and account resolution are injected. No platform
management credential is ever returned to an OAuth client.
"""

import asyncio
import hashlib
import hmac
import json
import re
import secrets
import time
from types import SimpleNamespace
from urllib.parse import urlencode, urlsplit

from oauthlib.oauth2 import RequestValidator, Server, OAuth2Error, InvalidGrantError
from quart import Response, jsonify, render_template, request

PREFIX = "/api/v1/agent-access/oauth"
SCOPES = ("swipies:read", "swipies:write", "offline_access")
ACCESS_SECONDS = 900
GRANT_SECONDS = 30 * 86400


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


class RedisStore:
    """Encrypted, bounded, expiring state shared by all API workers."""

    CONSUME = """
local value = redis.call('GET', KEYS[1])
if not value then return nil end
redis.call('SET', KEYS[2], value, 'EX', ARGV[1])
redis.call('DEL', KEYS[1])
return value
"""

    def __init__(self, redis, encrypt, decrypt):
        self._redis, self.encrypt, self.decrypt = redis, encrypt, decrypt

    @property
    def redis(self):
        client = self._redis() if callable(self._redis) else self._redis
        if client is None:
            raise RuntimeError("OAuth store unavailable")
        return client

    def key(self, family, value):
        return "swipies:mcp-oauth:" + family + ":" + digest(value)

    def put(self, family, key, value, ttl):
        ttl = max(1, int(ttl))
        envelope = {"context": self.key(family, key), "expires": time.time() + ttl, "value": value}
        self.redis.set(self.key(family, key), self.encrypt(json.dumps(envelope)), ex=ttl)

    def decode(self, value, family, key):
        if isinstance(value, bytes):
            value = value.decode()
        envelope = json.loads(self.decrypt(value))
        # Bind encrypted state to its token/family as well as its deadline.
        # Lua intentionally copies one-use records into their replay tombstone.
        source_family = family.removesuffix("-used")
        if not isinstance(envelope.get("context"), str) or not hmac.compare_digest(envelope["context"], self.key(source_family, key)):
            raise ValueError("OAuth state context mismatch")
        if not family.endswith("-used") and envelope["expires"] <= time.time():
            return None
        return envelope["value"]

    def get(self, family, key):
        value = self.redis.get(self.key(family, key))
        if value is None:
            return None
        return self.decode(value, family, key)

    def consume(self, family, key):
        retention = 600 if family == "pending" else GRANT_SECONDS
        value = self.redis.eval(self.CONSUME, 2, self.key(family, key), self.key(family + "-used", key), retention)
        if value is None:
            return None
        return self.decode(value, family, key)

    def limit(self, address, family, maximum):
        key = self.key("rate-" + family, str(int(time.time() // 3600)) + ":" + address)
        pipe = self.redis.pipeline(transaction=True)
        count, _ = pipe.incr(key).expire(key, 7200).execute()
        if count > maximum:
            raise ValueError("Rate limit reached")


class Validator(RequestValidator):
    def __init__(self, service):
        self.service = service

    def validate_client_id(self, client_id, request, *args, **kwargs):
        client = self.service.client(client_id)
        if not client:
            return False
        request.client = SimpleNamespace(client_id=client_id, **client)
        return True

    def authenticate_client_id(self, client_id, request, *args, **kwargs):
        return self.validate_client_id(client_id, request)

    def client_authentication_required(self, request, *args, **kwargs):
        return False  # Public clients authenticate code possession through S256 PKCE.

    def validate_redirect_uri(self, client_id, redirect_uri, request, *args, **kwargs):
        return redirect_uri in request.client.redirect_uris

    def get_default_redirect_uri(self, client_id, request, *args, **kwargs):
        return request.client.redirect_uris[0]

    def validate_response_type(self, client_id, response_type, client, request, *args, **kwargs):
        return response_type == "code"

    def validate_grant_type(self, client_id, grant_type, client, request, *args, **kwargs):
        return grant_type in client.grant_types

    def get_default_scopes(self, client_id, request, *args, **kwargs):
        return list(SCOPES if "refresh_token" in request.client.grant_types else SCOPES[:2])

    def validate_scopes(self, client_id, scopes, client, request, *args, **kwargs):
        return "swipies:read" in scopes and set(scopes) <= set(SCOPES) and ("offline_access" not in scopes or "refresh_token" in client.grant_types)

    def is_pkce_required(self, client_id, request):
        return True

    def save_authorization_code(self, client_id, code, request, *args, **kwargs):
        grant_id = secrets.token_urlsafe(24)
        value = {
            "client_id": client_id,
            "redirect_uri": request.redirect_uri,
            "scopes": list(request.scopes),
            "resource": self.service.resource,
            "code_challenge": request.code_challenge,
            "code_challenge_method": "S256",
            "grant_id": grant_id,
            "expires": time.time() + GRANT_SECONDS,
            "principal": request.user,
        }
        self.service.store.put("grant", grant_id, value, GRANT_SECONDS)
        self.service.store.put("code", code["code"], value, 300)

    def _load(self, family, token, client_id):
        value = self.service.store.get(family, token)
        if value is None:
            used = self.service.store.get(family + "-used", token)
            if used and used["client_id"] == client_id:
                self.service.revoke(used)
            return None
        if value["client_id"] != client_id or not self.service.active(value):
            return None
        return value

    def validate_code(self, client_id, code, client, request, *args, **kwargs):
        value = self._load("code", code, client_id)
        if value is None:
            return False
        request.user, request.scopes, request.oauth_record = value["principal"], value["scopes"], value
        return True

    def get_code_challenge(self, code, request):
        return request.oauth_record["code_challenge"]

    def get_code_challenge_method(self, code, request):
        return request.oauth_record["code_challenge_method"]

    def confirm_redirect_uri(self, client_id, code, redirect_uri, client, request, *args, **kwargs):
        return request.oauth_record["redirect_uri"] == redirect_uri

    def invalidate_authorization_code(self, client_id, code, request, *args, **kwargs):
        pass  # Consumed atomically by save_bearer_token, before any token is issued.

    def validate_refresh_token(self, refresh_token, client, request, *args, **kwargs):
        value = self._load("refresh", refresh_token, request.client_id)
        if value is None:
            return False
        request.user, request.oauth_record = value["principal"], value
        return True

    def get_original_scopes(self, refresh_token, request, *args, **kwargs):
        return request.oauth_record["scopes"]

    def rotate_refresh_token(self, request):
        return True

    def save_bearer_token(self, token, request, *args, **kwargs):
        family, previous = ("code", request.code) if request.grant_type == "authorization_code" else ("refresh", request.refresh_token)
        value = self.service.store.consume(family, previous)
        if value is None:
            self.service.revoke(request.oauth_record)
            raise InvalidGrantError()
        if not self.service.active(value):
            raise InvalidGrantError()
        remaining = int(value["expires"] - time.time())
        value = {**value, "scopes": list(request.scopes)}
        token["expires_in"] = min(ACCESS_SECONDS, remaining)
        self.service.store.put("access", token["access_token"], value, token["expires_in"])
        if "offline_access" in request.scopes:
            self.service.store.put("refresh", token["refresh_token"], value, remaining)
        else:
            token.pop("refresh_token", None)


class OAuthService:
    def __init__(self, store, origin, fetch_metadata, key_active, revoke_key, enabled=lambda: True):
        parsed = urlsplit(origin)
        if parsed.scheme != "https" or not parsed.hostname or parsed.path not in ("", "/") or parsed.query or parsed.fragment or parsed.username or "\\" in origin or any(ord(c) < 33 for c in origin):
            raise ValueError("OAuth public origin must be a canonical HTTPS origin")
        self.origin = origin.rstrip("/")
        self.resource = self.origin + "/api/v1/agent-access/mcp"
        self.store, self.fetch_metadata, self.key_active, self.revoke_key, self.enabled = store, fetch_metadata, key_active, revoke_key, enabled
        self.server = Server(Validator(self), token_expires_in=ACCESS_SECONDS, token_generator=lambda request: "swipies_oauth_" + secrets.token_urlsafe(32))

    def safe_redirect(self, uri):
        parsed = urlsplit(uri)
        # Pin provider-owned callback paths as well as the host; never accept an
        # arbitrary URL on the provider (it could be an open redirect endpoint).
        return (
            parsed.scheme == "https"
            and parsed.netloc == "chatgpt.com"
            and re.fullmatch(r"/(?:connector_platform_oauth_redirect|connector/oauth/[A-Za-z0-9_-]+)", parsed.path)
            and not parsed.query
            and not parsed.username
            and not parsed.fragment
            and "\\" not in uri
            and not any(ord(c) < 33 for c in uri)
        )

    def metadata_client(self, value):
        if not isinstance(value, dict):
            raise ValueError("Invalid client metadata")
        redirects = value.get("redirect_uris")
        grants = value.get("grant_types", ["authorization_code", "refresh_token"])
        methods = value.get("token_endpoint_auth_methods_supported", [value.get("token_endpoint_auth_method", "none")])
        if (
            not isinstance(redirects, list)
            or not 1 <= len(redirects) <= 20
            or any(not isinstance(uri, str) or len(uri) > 2048 or not self.safe_redirect(uri) for uri in redirects)
            or not isinstance(methods, list)
            or "none" not in methods
            or not isinstance(grants, list)
            or not all(isinstance(item, str) for item in grants)
            or "authorization_code" not in grants
            or not set(grants) <= {"authorization_code", "refresh_token"}
            or value.get("response_types", ["code"]) != ["code"]
        ):
            raise ValueError("Unsupported redirect URI or client authentication")
        return {"redirect_uris": redirects, "grant_types": list(dict.fromkeys(grants)), "client_name": str(value.get("client_name", "AI client"))[:80]}

    def client(self, client_id):
        if not isinstance(client_id, str) or len(client_id) > 512:
            return None
        found = self.store.get("client", client_id)
        if found:
            return found
        if not re.fullmatch(r"https://chatgpt\.com/oauth/(?:[A-Za-z0-9_-]+/)?client\.json", client_id):
            return None
        document = self.fetch_metadata(client_id)
        if not isinstance(document, dict) or document.get("client_id") not in (None, client_id):
            return None
        found = self.metadata_client(document)
        self.store.put("client", client_id, found, 300)
        return found

    def active(self, record):
        return (
            record["expires"] > time.time()
            and record["resource"] == self.resource
            and "swipies:read" in record["scopes"]
            and not self.store.get("revoked", record["grant_id"])
            and self.key_active(record["principal"])
        )

    def revoke(self, record):
        self.store.put("revoked", record["grant_id"], True, GRANT_SECONDS)
        self.revoke_key(record["principal"])

    def resolve(self, authorization):
        if not self.enabled() or not authorization.startswith("Bearer swipies_oauth_"):
            return None
        record = self.store.get("access", authorization[7:])
        if record and self.active(record):
            return {"authorization": "Bearer " + record["principal"]["api_key"], "scopes": record["scopes"]}
        return None

    def challenge(self, error=None, scope=None):
        value = 'Bearer resource_metadata="' + self.origin + PREFIX + '/resource-metadata"'
        if error:
            value += ', error="' + error + '"'
        if scope:
            value += ', scope="' + scope + '"'
        return value

    def validate_authorize(self, uri):
        from urllib.parse import parse_qs

        args = parse_qs(urlsplit(uri).query, keep_blank_values=True)
        if (
            any(len(values) != 1 for values in args.values())
            or len(uri) > 12000
            or args.get("resource") != [self.resource]
            or args.get("response_type") != ["code"]
            or args.get("code_challenge_method") != ["S256"]
            or not re.fullmatch(r"[A-Za-z0-9_-]{43}", args.get("code_challenge", [""])[0])
            or not args.get("redirect_uri", [""])[0]
        ):
            raise ValueError("A unique resource, redirect URI and S256 PKCE challenge are required")
        return self.server.validate_authorization_request(uri)


def register_agent_oauth(app, service, delegate, address):
    """delegate(choice, name) resolves only a logged-in owner or a new Free tenant."""
    protocol_slots = asyncio.Semaphore(8)

    async def protocol(function, *args, **kwargs):
        # CIMD HTTPS and synchronous DB/Redis adapters must not stall Quart's
        # event loop. Bound this work separately from normal tenant requests.
        async with protocol_slots:
            return await asyncio.to_thread(function, *args, **kwargs)

    def secure(response):
        response.headers.update({"Cache-Control": "no-store", "Pragma": "no-cache", "Referrer-Policy": "no-referrer", "X-Content-Type-Options": "nosniff"})
        return response

    def error(name, status=400):
        return secure(jsonify(error=name)), status

    @app.before_request
    async def oauth_availability():
        if request.path.startswith(PREFIX) or request.path.startswith("/.well-known/oauth-"):
            if not service.enabled():
                return error("temporarily_unavailable", 503)

    @app.get("/.well-known/oauth-protected-resource")
    @app.get("/.well-known/oauth-protected-resource/api/v1/agent-access/mcp")
    @app.get(PREFIX + "/resource-metadata")
    async def oauth_resource_metadata():
        return secure(jsonify(resource=service.resource, authorization_servers=[service.origin], scopes_supported=list(SCOPES), bearer_methods_supported=["header"]))

    @app.get("/.well-known/oauth-authorization-server")
    @app.get(PREFIX + "/server-metadata")
    async def oauth_server_metadata():
        return secure(
            jsonify(
                issuer=service.origin,
                authorization_endpoint=service.origin + PREFIX + "/authorize",
                token_endpoint=service.origin + PREFIX + "/token",
                registration_endpoint=service.origin + PREFIX + "/register",
                revocation_endpoint=service.origin + PREFIX + "/revoke",
                response_types_supported=["code"],
                grant_types_supported=["authorization_code", "refresh_token"],
                token_endpoint_auth_methods_supported=["none"],
                code_challenge_methods_supported=["S256"],
                scopes_supported=list(SCOPES),
                client_id_metadata_document_supported=True,
                authorization_response_iss_parameter_supported=True,
            )
        )

    @app.post(PREFIX + "/register")
    async def oauth_register():
        from api.agent_access import read_json

        try:
            service.store.limit(address(), "registration", 30)
            service.store.limit("global", "registration-global", 1000)
            data = await read_json(8192)
            if not isinstance(data, dict):
                return error("invalid_client_metadata")
            client = service.metadata_client(data)
            client_id = "swipies-client-" + secrets.token_urlsafe(24)
            service.store.put("client", client_id, client, 90 * 86400)
            return secure(
                jsonify(
                    client_id=client_id,
                    client_name=client["client_name"],
                    redirect_uris=client["redirect_uris"],
                    token_endpoint_auth_method="none",
                    grant_types=client["grant_types"],
                    response_types=["code"],
                )
            ), 201
        except Exception:
            return error("invalid_client_metadata")

    @app.get(PREFIX + "/authorize")
    async def oauth_authorize_page():
        try:
            service.store.limit(address(), "authorize", 90)
            uri = service.origin + request.full_path.rstrip("?")
            scopes, credentials = await protocol(service.validate_authorize, uri)
            client = await protocol(service.client, credentials["client_id"])
            csrf, pending = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
            service.store.put("pending", pending, {"uri": uri, "csrf": digest(csrf), "registration_secret": secrets.token_urlsafe(48)}, 600)
            nonce = secrets.token_urlsafe(24)
            response = secure(
                Response(
                    await render_template(
                        "agent_oauth_consent.html", pending=pending, nonce=nonce, client_name=client["client_name"], scopes=scopes, login_url=service.origin + "/login?" + urlencode({"redirect": uri})
                    ),
                    mimetype="text/html",
                )
            )
            response.headers["Content-Security-Policy"] = (
                "default-src 'none'; script-src 'nonce-" + nonce + "'; style-src 'unsafe-inline'; connect-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'"
            )
            response.set_cookie("swipies_oauth_csrf", csrf, max_age=600, secure=True, httponly=True, samesite="Lax", path=PREFIX)
            return response
        except Exception:
            return error("invalid_request")

    @app.post(PREFIX + "/authorize")
    async def oauth_authorize_decision():
        from api.agent_access import read_json

        if request.headers.get("Origin") != service.origin:
            return error("access_denied", 403)
        try:
            data = await read_json(4096)
            pending_id = data.get("pending", "")
            saved = service.store.get("pending", pending_id)
            csrf = request.cookies.get("swipies_oauth_csrf", "")
            if not saved or not csrf or not hmac.compare_digest(saved["csrf"], digest(csrf)):
                return error("access_denied", 403)
            scopes, _ = await protocol(service.validate_authorize, saved["uri"])
            # Consume before creating a credential or granting access; concurrent submissions fail closed.
            if service.store.consume("pending", pending_id) is None:
                return error("access_denied", 403)
            if data.get("choice") == "deny":
                from urllib.parse import parse_qs

                args = parse_qs(urlsplit(saved["uri"]).query)
                location = (
                    args["redirect_uri"][0] + ("&" if "?" in args["redirect_uri"][0] else "?") + urlencode({"error": "access_denied", "state": args.get("state", [""])[0], "iss": service.origin})
                )
            else:
                principal = await delegate(data.get("choice"), saved["registration_secret"])
                if not principal:
                    return error("login_required", 401)
                headers, _, status = await protocol(service.server.create_authorization_response, saved["uri"], scopes=scopes, credentials={"user": principal})
                if status != 302:
                    return error("access_denied", 403)
                location = headers["Location"]
                location += ("&" if "?" in location else "?") + urlencode({"iss": service.origin})
            return secure(jsonify(redirect=location))
        except Exception:
            return error("access_denied", 403)

    async def form():
        if request.mimetype != "application/x-www-form-urlencoded" or (request.content_length and request.content_length > 16384):
            raise ValueError("Invalid token request")
        raw = bytearray()
        async with asyncio.timeout(30):
            async for chunk in request.body:
                if len(raw) + len(chunk) > 16384:
                    raise ValueError("Invalid token request")
                raw.extend(chunk)
        from urllib.parse import parse_qs

        values = parse_qs(raw.decode(), keep_blank_values=True)
        if any(len(items) != 1 for items in values.values()):
            raise ValueError("Duplicate parameter")
        return raw.decode(), {key: value[0] for key, value in values.items()}

    @app.post(PREFIX + "/token")
    async def oauth_token():
        try:
            service.store.limit(address(), "token", 300)
            body, values = await form()
            if values.get("resource") != service.resource:
                return error("invalid_target")
            if "scope" in values and ("swipies:read" not in values["scope"].split() or not set(values["scope"].split()) <= set(SCOPES)):
                return error("invalid_scope")
            if values.get("grant_type") == "authorization_code" and not re.fullmatch(r"[A-Za-z0-9._~-]{43,128}", values.get("code_verifier", "")):
                return error("invalid_grant")
            headers, body, status = await protocol(service.server.create_token_response, service.origin + PREFIX + "/token", http_method="POST", body=body)
            return secure(Response(body, status=status, headers=headers, mimetype="application/json"))
        except OAuth2Error:
            return error("invalid_grant")
        except ValueError:
            return error("invalid_request")
        except Exception:
            return error("temporarily_unavailable", 503)

    @app.post(PREFIX + "/revoke")
    async def oauth_revoke():
        try:
            service.store.limit(address(), "revoke", 300)
            _, values = await form()
            client_id, token = values.get("client_id"), values.get("token", "")
            if not await protocol(service.client, client_id):
                return error("invalid_client")
            record = service.store.get("access", token) or service.store.get("refresh", token) or service.store.get("refresh-used", token)
            if record and record["client_id"] == client_id:
                await protocol(service.revoke, record)
            return secure(Response(status=200))
        except Exception:
            return error("invalid_request")
