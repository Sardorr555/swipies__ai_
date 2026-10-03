# Implementation Plan: CRM Integration v1 (Risk-First Phasing)

**Specification**: `specs/003-crm-v1-integration/spec.md`  
**Целевая ветка**: `feat/crm-v1` (Base: `3bb88c257`, целевой merge в ветку `test`)  
**Author**: `Sardor <albakiev.sardorbek@gmail.com>`  
**Status**: Completed (T0–T6 and T8 fully implemented and verified; T7 excluded from v1)

---

## 1. Risk Analysis & Phased Sequence

The architecture follows a strict **Risk-First** progression. Lower layers with critical vulnerabilities or security prerequisites are resolved and validated before higher-level features are built upon them (T0–T6, T8; T7 исключён из v1).

```
┌─────────────────────────────────────────────────────────────┐
│ C0: Upstream Go Compiler Error Resolution                   │
│     - tenant_model_provider.go, handler/user.go, service/user│
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ T0: Hygiene & Test Debt Baselines                           │
│     - test DB isolation (:memory:), .gitignore defense     │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ T1: MCP Cross-Tenant Isolation Fix                          │
│     - get_by_id_and_tenant, agent_api.py, canvas_owner_tenant│
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ T2: Core CRM Models, Crypto, License Gate & Fencing Engine  │
│     - crm_models.py (token_version), transport.py, base.py  │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ T3: amoCRM Client & Fenced Distributed Token Refresh        │
│     - Redis lock + Lua ownership release + recovery read    │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ T4: Bitrix24 Provider 2 Inbound Webhook Adapter             │
│     - Cloud zone allowlist, on-prem SSRF guard, redaction   │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ T5: Canvas Lead Tool & Leased Outbox Worker                 │
│     - create_incoming_lead (1/turn, 100/hr), lease worker   │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ T6: Phase 2 - 1C:Enterprise Stock Checker Tool              │
│     - check_stock tool, read-only OData, admin IP allowlist │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ T8: Docker Packaging, Migration & Rollout Verification      │
│     - init_database_tables, worker supervisor, phonenumbers │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Phase Breakdown & Gated Criteria

### Phase C0: Upstream Go Compiler Error Resolution (Prerequisite)
- **Goal**: Fix compilation errors in user registration, referrals, and model provider check so `go build/test` passes cleanly on all packages.
- **Components**:
  1. `internal/dao/tenant_model_provider.go`: Safe pointer check `if user.IsSuperuser != nil && *user.IsSuperuser`.
  2. `internal/handler/user.go`: Replace undefined `jsonError` with standard helper `common.ErrorWithCode`.
  3. `internal/service/user.go`: Pass `ctx, dao.DB` to `s.userDAO.GetByTenantID` and `GetByEmail`.
- **Quality Gate**:
  - `go test ./internal/dao/...`, `./internal/service/...`, `./internal/handler/...` build and pass with 0 errors.

---

### Phase T0: Hygiene, Test Debts & Environment Baselines (Risk: Low / Baseline)
- **Goal**: Clean git working tree, lock down test debt solutions, and eliminate temporary database files on disk.
- **Components**:
  1. Isolate connector and MCP security tests from real DB in `test/test_connector_security.py` and `test/test_mcp_security.py` using strictly in-memory SQLite (`:memory:`) and `DB.connect` interceptor, completely eliminating creation of temporary database files on disk (`temp.db`).
  2. Maintain `test/*_temp.db` and `test/*.db` in `.gitignore` as defense-in-depth against accidental disk file creation.
  3. Verify clean git working tree baseline without uncommitted scratch scripts.
- **Quality Gate**:
  - `python -m unittest test.test_connector_security -v` passes with 21/21 green tests with DB interceptor active.
  - `python -m pytest test/test_mcp_security.py` passes with 29/29 green tests.

---

### Phase T1: MCP Cross-Tenant Vulnerability Fix (Risk: High / Security)
- **Goal**: Eliminate cross-tenant resource injection via Canvas DSL while preserving team canvas sharing.
- **Components**:
  1. Add `MCPServerService.get_by_id_and_tenant(mcp_id, tenant_id)` to `api/db/services/mcp_server_service.py`.
  2. In `api/apps/restful_apis/agent_api.py` (`create_agent`, `update_agent`, `rerun_agent`), validate that any `mcp_id` in the submitted DSL belongs to `canvas_owner_tenant`.
  3. In `agent/component/agent_with_tools.py`, resolve MCP server using canvas owner tenant (`self._canvas.get_canvas_owner_tenant()`) with fallback to `self._canvas.get_tenant_id()`, keeping canvas tenant isolated.
  4. Write regression tests demonstrating cross-tenant MCP rejection during both save and execution, with mutation tests.
- **Quality Gate**:
  - Tenant A cannot save or execute Tenant B's MCP servers under any Canvas DSL configuration.
  - Team member (Tenant B) can execute shared Canvas owned by Tenant A with Tenant A's MCP servers.

---

### Phase T2: Core CRM Models, Storage, License Infrastructure & Provider Contract (Risk: Medium / Foundation)
- **Goal**: Implement tenant-scoped database models without circular imports, establish AES-256-GCM field encryption, include fencing token `token_version`, define provider-agnostic interface (`CRMProviderBase`), build SSRF/DNS-pinned `transport.py`, and enforce explicit fail-closed licensing (`features: ["crm"]`).
- **Components**:
  1. Create `api/db/crm_models.py` defining `CRMConnection` (with `token_version = IntegerField(default=1)`, `crm_type = CharField(default="amocrm")` for `amocrm`, `bitrix24`, `bitrix24_onprem`, `1c_odata`) and `CRMOutbox`.
  2. Register models inside `init_database_tables()` in `api/db/db_models.py` via lazy import.
  3. Add bidirectional import order test: `import crm_models; import db_models` and `import db_models; import crm_models`.
  4. Define abstract contract `CRMProviderBase` (`api/crm/base.py`) with `create_lead`, `find_contact`, `refresh_auth`, `check_stock`.
  5. Implement `transport.py` wrapping `common/ssrf_guard.py` with DNS pinning, blocking private IPs and strictly disabling redirects (`allow_redirects=False`). External libs allowed only if routed through this transport; otherwise thin clients mandatory.
  6. Implement `CRMService` with tenant-scoped CRUD methods.
  7. Implement `license_verifier.py` integration: fail-closed checks returning `PERMISSION_ERROR` unless `"crm"` is explicitly present in license payload's `features` (commercial type alone does not enable CRM).
- **Quality Gate**:
  - Database tables auto-migrate safely with `token_version` and provider-agnostic `crm_type`.
  - All credentials stored in `CRMConnection.config` are encrypted with `enc:v2:`.
  - License validation unit tests verify complete fail-closed behavior: valid license without `"crm"` in `features` fails closed.
  - MCP is strictly excluded from v1.

---

### Phase T3: amoCRM Provider 1 Adapter & Fenced Distributed Token Refresh Engine (Risk: High / Concurrency)
- **Goal**: Build a resilient amoCRM REST client that survives parallel worker token rotation, worker pauses, and network hiccups via fenced locking over `transport.py`.
- **Components**:
  1. amoCRM thin client (`api/crm/clients/amocrm.py`) implementing `CRMProviderBase` over `transport.py`.
  2. Redis distributed lock (`crm:lock:refresh:{conn_id}`, TTL: 30s) with Lua-based ownership release.
  3. Double-checked DB read upon lock acquisition: if already refreshed by another worker, skip remote call.
  4. **Fencing token check**: on successful refresh, update DB using conditional compare-and-swap on `token_version`. Every update to `config` increments `token_version`.
  5. **Invalid grant recovery**: if refresh returns `invalid_grant`, re-read MySQL; if `token_version` increased, use new token; if unchanged, transition status to `reauth_required`.
  6. Domain allowlisting: enforce outgoing host matches exact boundary: `*.amocrm.ru`, `*.amocrm.com`, or `*.kommo.com` `[VERIFY по документации Kommo и по реальному URL аккаунта заказчика]`; strictly disable HTTP redirects (`allow_redirects=False`).
- **Quality Gate**:
  - Concurrent simulation test: 5 simultaneous workers needing refresh execute exactly 1 OAuth request; all 5 acquire valid tokens.
  - Stale worker with outdated fencing token is rejected on commit.
  - Revocation test: invalid token transitions status to `reauth_required` without infinite retry.

---

### Phase T4: Bitrix24 Provider 2 Inbound Webhook Adapter (Risk: Medium / Webhook Security)
- **Goal**: Implement Bitrix24 inbound webhook adapter over `transport.py` with URL/token encryption at rest, cloud zone allowlisting, on-premise SSRF/DNS-pinning isolation, and webhook path secret redaction.
- **Components**:
  1. Bitrix24 thin client (`api/crm/clients/bitrix24.py`) implementing `CRMProviderBase` over `transport.py`.
  2. Cloud domain boundary validation:
     - URL parsing via `urllib.parse.urlsplit(url)`:
       - Scheme must be strictly `https`.
       - Userinfo (`username` / `password`) must be `None` (rejects `https://user:pass@portal.bitrix24.com/`).
       - Custom port must be `None` or `443` (rejects `:8080`).
       - Hostname normalized to lowercase.
       - Reject leading/trailing dots (`.portal.bitrix24.com`, `portal.bitrix24.com.`).
       - Reject punycode / IDN (`xn--...`).
     - Match hostname using `re.escape` with `re.fullmatch`:
       - Allowed zones dynamically loaded from `RAGFLOW_CRM_B24_ZONES`. Confirmed per official Bitrix24 docs: `ru,kz,by,uz,com,eu,de,es,fr,it,pl,in,cn,jp,id,vn,ae,mx,uk,com.tr`. Unverified defaults [VERIFY]: `com.br,ua,co,cl`. Reject lookalikes (`x.bitrix24.evil.com`, `bitrix24.com.evil.net`) and raise explicit error on unknown zones: `"Unsupported Bitrix24 cloud zone '<zone>'. Allowed zones: ..."`
  3. On-premise validation (`crm_type: bitrix24_onprem`): strictly HTTPS, public IPs via `ssrf_guard` + DNS-pinning, no redirects (`allow_redirects=False`); private IPs (`127.0.0.1`, `169.254.169.254`, `10.0.0.1`, `192.168.x`, `172.16.x`, `0.0.0.0`, DNS-rebinding, redirect to private) all rejected fail-closed unless included in platform allowlist `RAGFLOW_CRM_PRIVATE_ALLOWLIST_CIDR`.
  4. Webhook URL with secret key stored encrypted at rest with `enc:v2:`, and redacted in logs/traces (`/rest/<id>/<key>/` -> `/rest/<id>/********/`).
  5. Inbound webhook methods: `crm.lead.add`, `crm.contact.list`.
  6. Rate limiting: centralized ~2 req/s per portal via Redis (`crm:ratelimit:b24:{portal_host}`) and transient error handling (`QUERY_LIMIT_EXCEEDED` / 5xx) with jittered backoff.
  7. `refresh_auth`: Ping endpoint (`crm.lead.fields`) to verify validity without mutating token.
- **Quality Gate**:
  - Inbound webhook URL stored encrypted as `enc:v2:` and masked in all logs, exceptions, and API responses.
  - Outbound requests to non-bitrix24 domains fail closed with `SecurityError`.
  - On-premise SSRF test matrix confirms rejection of `127.0.0.1`, `169.254.169.254`, `10.0.0.1`, `192.168.1.1`, DNS-rebinding, and redirects to private IPs.

---

### Phase T5: Canvas Lead Tool & Leased Outbox Worker (Risk: High / Agent Runtime)
- **Goal**: Implement agent Canvas tool `create_incoming_lead` and leased Outbox background worker dispatching to configured provider.
- **Components**:
  1. Canvas tool `agent/tools/create_incoming_lead.py` inheriting from `ToolBase` (native implementation).
  2. Rate limit enforcement: strictly **1 lead write per turn** and **100 leads/hour per tenant**.
  3. Channel check: for public channels (Webhook or Embed), allow execution ONLY if `security.allow_anonymous = True`.
  4. Input validation: E.164 phone normalization, max 128 chars for name, 2000 chars for text, control char stripping.
  5. Deduplication: compute `business_key = HMAC_SHA256(server_secret_key, f"{tenant_id}:{connection_id}:{e164_phone}")`, acquire short dedup lock, check 24h sliding window in MySQL.
  6. Outbox background worker in `rag/svr/crm_outbox_worker.py`: 5-minute atomic lease, search-before-create contact, open deal lookup, lead creation, dispatching via `CRMProviderRegistry`, exponential backoff, dead-letter after 5 tries.
  7. Worker supervision in `docker/entrypoint.sh` and `launch_backend_service.sh` with health status checks and structured logging alert on lag $>15\text{m}$.
  8. Scheduled PII retention task: scrub customer data AND set `business_key = NULL` on records older than 30 days.
- **Quality Gate**:
  - Repeated agent tool calls in one turn are rejected after the first.
  - Deduplication prevents duplicate outbox entries within 24 hours.
  - Outbox worker reliably transitions records through `PENDING` -> `PROCESSING` -> `SENT`.

---

### Phase T6: Phase 2 / Provider 3: 1C:Enterprise Stock Checker Tool (Risk: Low / Extension)
- **Goal**: Provide read-only stock inquiry tool without order creation over standard 1C OData.
- **Components**:
  1. Tool `agent/tools/check_stock.py` querying 1C OData REST endpoints via thin client on `transport.py`.
  2. Read-only enforcement: only HTTP `GET` requests permitted.
  3. SSRF guard with platform admin private IP allowlist (`RAGFLOW_CRM_1C_ALLOWLIST_CIDR`) + 5-second strict timeout.
  4. Permitted for anonymous channels if `security.allow_anonymous = True`.
- **Quality Gate**:
  - Unit tests verify inventory queries return stock counts and mutation attempts are blocked.

---

### Phase T7: MCP CRM Integration (Excluded from v1)
> [!NOTE]
> **T7 removed**: MCP CRM integration deferred to post-v1. Agent tool integration in v1 is implemented natively via native Canvas tools (`CreateIncomingLead` in T5 and `CheckStock` in T6) inheriting directly from `agent.tools.base.ToolBase`. MCP wrapper for CRM providers is deferred to post-v1.

---

### Phase T8: Docker Packaging, Migration & Rollout Verification (Risk: Medium / Operations)
- **Goal**: Package worker, implement safe automated schema creation, and verify dependencies and Docker deployment assets.
- **Components**:
  1. Automated table creation via Peewee `create_tables([CRMConnection, CRMOutbox], safe=True)` in `init_database_tables()`.
  2. Integration of `crm_outbox` into `docker/launch_backend_service.sh` and `docker/entrypoint*.sh`.
  3. Environment variable declarations in `docker/.env` and `docker/.env-go` (`RAGFLOW_SECRET_KEY=${RAGFLOW_SECRET_KEY}`, `RAGFLOW_CRM_HOURLY_LIMIT=100`, `RAGFLOW_CRM_B24_ZONES=`, `RAGFLOW_CRM_PRIVATE_ALLOWLIST_CIDR=`).
  4. Dependency verification: ensure `phonenumbers>=9.0.24` is verified via `uv lock --check` and validated in container image via `docker run <image> python -c "import phonenumbers"`.
  5. Rollback and Backup Policy: Бэкап только вручную перед деплоем; automated startup backup and reverse migrations are strictly excluded.
- **Quality Gate**:
  - Clean startup without orphan locks or schema drift.
  - No secrets stored in git-tracked configuration files.
  - `phonenumbers` cleanly imports and validates international numbers across target environments.
