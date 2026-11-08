# ChatGPT OAuth access — swipies_26

Implemented locally on 2026-10-29. Not deployed or verified inside ChatGPT yet.
The live manifest's `mcp.oauth.enabled` is authoritative. The default is disabled.

## User flow

An owner adds the remote MCP URL to an OAuth-capable client:
`https://api.swipies.app/api/v1/agent-access/mcp`. The client discovers authorization
from the unauthenticated 401 challenge. Swipies shows a consent page with the
requested rights. The owner chooses a separate Free workspace or signs in and
connects their current owner account. Free provisioning uses the existing
registration service, limits, quotas and branding. No Swipies API key is copied
into ChatGPT. After consent the client exchanges the code using S256 PKCE and
calls the existing tenant MCP gateway.

This requires a one-time client connection and consent. Visiting a public page
cannot add tools to a chat. Client availability, administrative policy and
approval of later write actions remain controlled by the external host. No
OpenAI API key or internal OpenAI model is required by this server feature.

The authorization page supports current ChatGPT callbacks only:

- `https://chatgpt.com/connector_platform_oauth_redirect`
- `https://chatgpt.com/connector/oauth/<callback_id>`

Adding other OAuth clients requires an explicit reviewed callback allowlist
extension. Existing stdio clients and API-key HTTP clients continue to work.

## Protocol and implementation

- [OAuth adapter](../../api/agent_oauth.py): OAuthLib authorization code flow,
  mandatory S256, public clients (`token_endpoint_auth_method=none`), exact
  registered redirect matching, exact MCP resource binding and issuer response.
- [Production identity adapter](../../api/db/services/agent_oauth_service.py):
  owner-only login linking or isolated Free provisioning. Each connection gets
  its own private APIToken, never an administrator credential.
- [Consent page](../../api/apps/templates/agent_oauth_consent.html): server-rendered,
  one-use browser-bound state, Secure/HttpOnly/SameSite cookie, exact Origin,
  CSP and no-store responses. Authentication is resolved using the existing
  login/session policy; platform API keys cannot link an existing owner account.
- [Gateway](../../api/agent_access.py): opaque OAuth bearer resolution, no fallback
  for invalid OAuth tokens, dynamic discovery and write-scope enforcement before
  dispatch. The underlying REST views retain their tenant/plan checks.
- [Proxy](../../web/nginx.conf.template): routes standard discovery to Python.

| Public endpoint | Purpose |
|---|---|
| `GET /.well-known/oauth-authorization-server` | Authorization server metadata |
| `GET /.well-known/oauth-protected-resource` | MCP protected resource metadata |
| `GET /.well-known/oauth-protected-resource/api/v1/agent-access/mcp` | Resource-specific discovery |
| `GET /api/v1/agent-access/oauth/server-metadata` | Same server metadata, API path |
| `GET /api/v1/agent-access/oauth/resource-metadata` | Same resource metadata, used in 401 challenge |
| `POST /api/v1/agent-access/oauth/register` | Bounded dynamic client registration |
| `GET, POST /api/v1/agent-access/oauth/authorize` | Consent and authorization |
| `POST /api/v1/agent-access/oauth/token` | Code exchange and rotating refresh |
| `POST /api/v1/agent-access/oauth/revoke` | Revoke the connection and private delegate key |

Client ID metadata documents are fetched only from the pinned ChatGPT HTTPS URL
patterns, without redirects, with a 5-second timeout and 64 KiB bound. The
current [ChatGPT document](https://chatgpt.com/oauth/client.json) advertises both
`none` and `private_key_jwt`; this implementation advertises and uses `none` with
PKCE. Requests are bound to the canonical HTTPS resource and issuer rather than
the incoming Host header.

Blocking protocol/CIMD work and bearer resolution run outside Quart's event loop
with bounded concurrency. Thread-local database checks close their connections.
The concurrency test verifies a delayed metadata fetch does not block a normal
manifest request.

Scopes are `swipies:read`, `swipies:write` and `offline_access`. Read is mandatory;
non-GET operation execution requires write. This conservatively treats POST
search operations as write. Refresh can reduce scopes but cannot expand them.
Clients without the refresh grant cannot request offline access.

Access tokens last at most 15 minutes. The entire grant expires after 30 days,
including refreshed tokens. Codes last 5 minutes and consent state 10 minutes.
Refresh tokens rotate; replay of a consumed code/refresh revokes the entire
grant and its delegate key. Atomic Redis Lua consumption prevents issuing two
valid token chains from one code. Revocation/key/account status are checked
at each OAuth request.

All client records, pending states, grants and token mappings are encrypted
using the existing `enc:v2:` AES-256-GCM and master-secret policy. Redis keys hash
opaque values; counter records contain counts only. No new SQL schema or custom
JWT signing is introduced. State has TTLs and DCR has per-IP/global limits.
The encrypted envelope binds each record to its token/family and deadline, so
copying ciphertext to a chosen token or extending Redis TTL cannot forge access.
OAuthLib DEBUG logging is suppressed because it can include token bodies.

## Operational limits

Redis must be shared by API workers and configured for appropriate persistence
and capacity. Redis loss/eviction invalidates affected connections; it does not
delete tenant resources. A user must reconnect after expiry/state loss. A newly
chosen Free workspace is separate; automatic email recovery or claiming of an
anonymous Free workspace is not implemented. Do not promise permanent recovery
of an anonymous workspace after its private identity/grant is lost.

Delegate keys can be revoked through existing API-key management; doing so also
invalidates the OAuth connection. Disconnect/revoke invalidates the entire grant.
Browser logout does not revoke an already approved API-key-backed grant; linking
a new existing-account connection still requires a valid owner login. Disabling
the owner account or its delegate key invalidates access.
Expired or abandoned grants may leave an unused delegate key row in the owner's
key list. No automatic SQL deletion of tenant data/keys is performed. Deleting a
connector from a client may only delete that client's saved token unless it also
calls the revocation endpoint; server-side key revocation is the reliable fallback.

## Release procedure (owner authorization required)

1. Check out the reviewed `swipies_26` revision. Confirm `oauthlib>=3.3.1,<4` is
   available in the Python runtime. It was already a transitive locked dependency;
   it is now explicit. Test-only fakeredis/Lua packages do not belong in production.
2. In the backend environment set `SWIPIES_AGENT_OAUTH_ENABLED=1` and
   `SWIPIES_AGENT_PUBLIC_ORIGIN=https://api.swipies.app`. Keep the existing unique
   `RAGFLOW_SECRET_KEY` (or supported `SECRET_KEY`) configured. Do not rotate it
   merely to enable OAuth. Enabled OAuth fails startup with an insecure master
   secret. Keep normal registration enabled if the Free option is wanted.
3. Deploy/recreate only the Python API service with the new environment and code.
   An ordinary restart does not apply changed Docker environment variables.
   No schema migration, Go change, model worker or frontend JavaScript build is
   required. Do not run the memory-heavy frontend build on the production host.
4. Apply the narrow discovery locations from `web/nginx.conf.template` to the
   actual serving Nginx configuration, validate with `nginx -t`, then reload it.
   Updating the repository template alone does not change a running container.
   Preserve the existing frontend static files and all other proxy routes. If an
   outer Nginx handles the hostname, ensure it forwards these paths too.
5. Through Cloudflare, ensure `/api/v1/agent-access/*` and the discovery paths
   reach the origin without cache or interactive browser challenges. Preserve
   application authentication, rate limits and unrelated protection. Do not
   expose a tenant credential in a Worker or public file.
6. Verify public HTTPS: manifest has `mcp.oauth.enabled=true`; both metadata
   documents are JSON; issuer/resource/endpoint hosts are the exact canonical
   host. An unauthenticated POST to MCP returns **401** with `WWW-Authenticate:
   Bearer resource_metadata="..."`, not HTML, a challenge page or a redirect.
7. Add an OAuth MCP connection in an eligible ChatGPT account using the MCP URL.
   Verify consent, first Free creation, reconnect and a test dataset/chatbot.
   Separately verify existing-owner linking keeps the current tenant and plan,
   and revoking its named API key blocks the connection. Do not claim ChatGPT
   integration success from unit tests alone.
8. Publish updated static connection instructions together with enabled OAuth.
   Instructions condition OAuth availability on the runtime manifest.

Rollback: set `SWIPIES_AGENT_OAUTH_ENABLED=0`, recreate only the API service and
check API-key MCP still works. OAuth tokens fail closed while disabled. Existing
resources and the old API-key path are retained. Remove individual delegate keys
through normal owner management if required; do not flush shared Redis.

## Validation

`uv lock --check --offline --python <python3.13>` validates the locked dependency
graph. Install the normal test group (`uv sync --group test --locked` in a test
environment). Run:

```text
python -m pytest test/test_agent_oauth.py test/test_agent_access.py test/test_agent_access_model_integration.py test/test_connector_security.py -q -p no:cacheprovider
```

Local result on 2026-10-29: **144 passed** in the command above; the separate Ads/
branding/crawler keyword regression suite passed **15 tests**. Ruff checks,
rendered consent JavaScript syntax and `uv lock --check --offline` passed.
The lock has 700 resolved packages; all pre-existing package versions are retained.

Tests use OAuthLib, AES-GCM, fakeredis executing real Lua, the actual registration/
auth/model definitions on SQLite and the official MCP SDK for legacy transport.
They cover code/refresh replay, concurrent consumption, PKCE, redirects, issuer,
resource/scope restrictions, CSRF, encrypted persistence, revoke/outage behavior,
legacy compatibility and real owner/Free identity delegation. No production
credentials or production database are used. Actual deployment, Cloudflare,
Nginx runtime syntax and the ChatGPT client remain release verification steps.

References: [OpenAI MCP authentication](https://developers.openai.com/plugins/build/auth),
[MCP authorization](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization),
[OAuthLib server](https://oauthlib.readthedocs.io/en/latest/oauth2/server.html).
