# External agent access — swipies_26

Implemented 2026-10-26. This feature executes commands from an external AI application; it does not run an autonomous LLM inside Swipies.

## User experience

Configure the stdio client once in the external MCP host. On its first request the client generates and stores a random identity locally, provisions an isolated Free account and then forwards MCP requests. Later sessions reuse that identity. No browser, email verification or copied API key is needed for this service-account flow. Existing customers can instead supply their existing API key via `SWIPIES_API_KEY`; this operates on their existing tenant and subscription.

The external AI discovers operations, reads the selected operation's API documentation and executes it. It can create/update/delete datasets, documents, agents and chat assistants; configure channels, providers and connectors; upload small documents; start parsing; inspect status; manage memory, searches, files, tenant membership and available intelligence features. This is a catalog of authenticated Python REST operations, not an independent reimplementation of platform business logic. Actual availability depends on the loaded routes, existing authorization and subscription.

## Server endpoints

| Endpoint | Purpose |
|---|---|
| `GET /api/v1/agent-access/manifest` | Public machine-readable discovery, no secrets |
| `POST /api/v1/agent-access/bootstrap` | Create/reconnect a Free service account |
| `GET /api/v1/agent-access/operations` | Authenticated operation catalog |
| `POST /api/v1/agent-access/mcp` | Stateless Streamable HTTP MCP, protocol 2025-03-26 |

MCP methods: initialize, ping, tools/list, tools/call, notifications. GET/DELETE at the MCP URL return 405; no server-initiated SSE session is offered. Tools: `swipies_list_operations`, `swipies_describe_operation`, `swipies_execute`.

Bootstrap accepts only `registration_secret` (at least 43 URL-safe characters, generated from 32 random bytes) and optional `name`. Persist the secret before sending it. The same secret identifies the same account. Provisioning writes the user, tenant, owner membership, root folder and API credential atomically. A disabled or deleted credential/account is not recreated by retrying. No requested email, plan, owner id or privilege fields are accepted. Human registration and 2FA remain unchanged.

## Configure Codex

Using Python 3.10+ on the MCP client's machine:

```powershell
codex mcp add swipies -- python D:\ragflow\swipies_25\ragflow\tools\swipies_agent_client.py
```

Alternatively, add to the client's MCP configuration:

```json
{
  "mcpServers": {
    "swipies": {
      "command": "python",
      "args": ["D:\\ragflow\\swipies_25\\ragflow\\tools\\swipies_agent_client.py"]
    }
  }
}
```

The local script uses only the Python standard library. For an existing tenant, set `SWIPIES_API_KEY` through the host's secret configuration, without putting it in source control. Optional `--url https://your-server.example` and `--state-file <private-path>` are supported. HTTPS is required and redirects are rejected. Default credential storage is under the platform's user data directory; Windows uses the current user's DPAPI, POSIX uses an owner-only file. A different external customer must have a different state file/user profile. Losing the service-account secret loses access; email recovery/account claiming is not implemented by this flow.

Remote MCP clients that support bearer API keys can connect directly to `https://api.swipies.app/api/v1/agent-access/mcp` after provisioning. Connecting an MCP integration still depends on the external host's configuration, authorizations and tool approval rules. A URL alone cannot install a connector in every AI product. Automatic bootstrap is provided by the included stdio client.

## Server configuration and release

Requires the Python API server and existing DB/Redis schema, not a new worker or Go build. Existing Docker compose already mounts `api`, `common` and `tools` and loads `docker/.env`.

| Environment variable | Default | Effect |
|---|---|---|
| `SWIPIES_AGENT_REGISTRATION_ENABLED` | `1` | Controls creation of new service accounts; existing accounts can reconnect |
| `REGISTER_ENABLED` | Existing setting | Existing platform registration setting also applies |
| `SWIPIES_AGENT_REGISTRATIONS_PER_IP_HOUR` | `3` | New service accounts per source IP/hour |
| `SWIPIES_AGENT_REGISTRATIONS_PER_HOUR` | `100` | Global new accounts/hour |
| `SWIPIES_AGENT_TRUSTED_PROXIES` | `127.0.0.1/32,::1/128` | Only these peers may supply `X-Real-IP` |
| `SWIPIES_AGENT_ALLOWED_ORIGINS` | `https://api.swipies.app` | Exact allowed browser Origins; native clients may omit Origin |

Keep the Python API port behind the trusted reverse proxy if forwarding client addresses. Nginx must overwrite `X-Real-IP`; never trust arbitrary client Forwarded headers. Redis failure blocks new registrations. Rate limits are atomic across workers and attempts expire. They are initial anti-abuse limits, not a comprehensive fraud prevention system.

After an authorized release, restart the Python API and verify the manifest through the public reverse proxy, then test a dedicated service account. Public availability and dedicated-account CRUD/MCP were verified on 2026-10-26 after the owner deployed. That live audit found a separate provider model-type defect blocking chatbot inference and document embeddings; its correction still requires a server update and live retest. See handoffs/2026-10-26-live-verification.md. Go-only deployments do not expose this feature; Python/hybrid deployments route `/api/v1/agent-access/*` to Python.

## Branding

Only persisted active `plus` or `pro` tenant plans omit attribution. Expired/malformed plans, unknown plans, Free, enterprise/custom/unlimited and missing tenant records require it. Advertising switches and superuser status do not bypass this rule. A complete existing attribution footer is retained without duplication; merely mentioning Swipies does not suppress branding. Agent Message-only canvases receive attribution before `message_end`, as do LLM-backed replies through the existing LLM policy. Channel policy errors append a fallback footer.

## Boundaries

- Operations reuse the caller's API key and existing tenant authorization. No system owner credential is used. Admin actions, payment execution, token management, OAuth callbacks and human authentication are not exposed as generic MCP operations.
- Third-party OAuth permissions/credentials must already be available or supplied through that service's supported authorization. No connector can invent access to a private database.
- MCP request limit is 24 MiB, upload total 16 MiB, result limit 8 MiB, execution timeout 90 seconds. Large downloads and long-lived streams should use the direct REST API. Parsing jobs run in existing workers and can be polled; no new background AI is created.
- A timed-out write may have completed; inspect resource state before repeating it. No generic write retry or payment retry is performed.
- Service accounts are real isolated Free tenants. They do not silently acquire another customer's data or paid plan. Existing customers should use their own API key to access their existing subscription. Account claiming, email recovery and OAuth-based seamless linking are separate features.
- The platform enforces branding on its own outputs; an external application receiving text can still edit it. Technical API access cannot prevent all downstream transformations.

## Validation

Run `python -m pytest test/test_agent_access.py test/test_agent_access_model_integration.py -q -p no:cacheprovider` for transport tests (including official MCP SDK), tenant isolation, invalid Origin rejection, path traversal, route-shadow prevention, repeated multipart file fields, headerless body bounds, response bounds, idempotent registration, revoked key handling, SQLite rollback, native Windows DPAPI, concurrent client storage and subscription/agent attribution. The model integration suite uses actual model/auth/registration definitions on SQLite and includes a real stdio subprocess over locally trusted HTTPS with non-ASCII data.

The pre-deployment audit fixed seven reproduced bugs. Tool responses now mask known credential fields; route parameters cannot select another endpoint; credential files are atomically published; request limits also apply to chunked bodies. The client uses native Windows DPAPI, UTF-8 stdio, and bounded retries only for idempotent bootstrap. Authenticated writes are never automatically retried. See handoffs/2026-10-26-predeploy-audit.md for validation results and remaining server-side release conditions.

The live audit also confirmed that the deployment's Cloudflare configuration blocks the default Python-urllib User-Agent with error 1010. The bridge now identifies itself as `SwipiesAgent/1.0` on bootstrap and MCP requests. The updated local bridge passed a real stdio session through the official MCP SDK against public HTTPS. Update client copies as well as server code when applying this correction.

Additional regression suites: `python -m unittest test.test_connector_security`, `python -m unittest test.test_swipies_ads_watermark_and_crawler_keywords`, and the channel/agent access tests in `test/unit_test/api/`.
