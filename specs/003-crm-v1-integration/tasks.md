# Tasks: CRM Integration v1 (Risk-First Implementation Checklist)

**Specification**: `specs/003-crm-v1-integration/spec.md`  
**Plan**: `specs/003-crm-v1-integration/plan.md`  
**Status**: Pending Review & User Approval (STOP gate: No implementation code before user approval)

---

## Task Matrix (Risk-First Order C0, T0–T6)

### [ ] Phase C0: Upstream Go Compiler Error Resolution
- [ ] **C0.1**: In `internal/dao/tenant_model_provider.go:62`, fix pointer condition to `if user.IsSuperuser != nil && *user.IsSuperuser`.
- [ ] **C0.2**: In `internal/handler/user.go:419`, replace undefined `jsonError` with standard helper `common.ErrorWithCode(c, errorCode, errorMessage)`.
- [ ] **C0.3**: In `internal/service/user.go:150,156`, pass `ctx, dao.DB` to `s.userDAO.GetByTenantID` and `GetByEmail`.
- [ ] **C0.4**: Run `go test` on packages `dao`, `service`, `handler` to verify clean compilation.
- [ ] **C0.5**: Stage C0 changes, show `git diff --cached --stat` to user, and await explicit OK before committing.

---

### [ ] Phase T0: Hygiene, Test Debts & Environment Baselines
- [ ] **T0.1**: Maintain `test/*_temp.db` and `test/*.db` in `.gitignore` as defense-in-depth.
- [ ] **T0.2**: Verify clean git working tree baseline without uncommitted scratch scripts.
- [ ] **T0.3**: Isolate connector and security tests from real DB in `test/test_connector_security.py` and `test/test_mcp_security.py` using strictly in-memory SQLite (`:memory:`) and `DB.connect` interceptor, completely eliminating on-disk temporary database files (`temp.db`).
- [ ] **T0.4**: Verify all 21 tests in `test/test_connector_security.py` pass with DB interceptor active.
- [ ] **T0.5**: Stage isolated connector security test isolation and `.gitignore`.
- [ ] **T0.6**: Run `git diff --cached --stat` and display raw output to user, awaiting explicit OK before committing.

---

### [ ] Phase T1: MCP Cross-Tenant Vulnerability Remediation
- [ ] **T1.1**: In `api/db/services/mcp_server_service.py`, implement `MCPServerService.get_by_id_and_tenant(mcp_id: str, tenant_id: str)`.
- [ ] **T1.2**: In `api/apps/restful_apis/agent_api.py` (`create_agent`, `update_agent`, `rerun_agent`), validate that all `mcp_id`s referenced in submitted DSL belong to `canvas_owner_tenant`.
- [ ] **T1.3**: In `agent/component/agent_with_tools.py`, resolve MCP server using canvas owner tenant (`self._canvas.get_canvas_owner_tenant()`) with fallback to `self._canvas.get_tenant_id()`.
- [ ] **T1.4**: Add unit tests verifying cross-tenant MCP rejection at both save time and execution time, and team member execution of shared canvas.
- [ ] **T1.5**: Execute mutation verification: (a) remove runtime check; (b) remove save-time check; (c) use caller tenant for team member; verify test failure on all.
- [ ] **T1.6**: Show `git diff --cached --stat` and STOP.

---

### [ ] Phase T2: Core CRM Models, Storage, License Infrastructure & Provider Contract
- [ ] **T2.1**: Create `api/db/crm_models.py` with `CRMConnection` (with `token_version = IntegerField(default=1)`, `crm_type = CharField(default="amocrm")` for `amocrm`, `bitrix24`, `bitrix24_onprem`, `1c_odata`) and `CRMOutbox` models. Use `JSONField` matching `db_models`.
- [ ] **T2.2**: Register models inside `init_database_tables()` in `api/db/db_models.py` via lazy import.
- [ ] **T2.3**: Add test verifying import order in both directions (`import crm_models; import db_models` and `import db_models; import crm_models`).
- [ ] **T2.4**: Define abstract contract `CRMProviderBase` (`api/crm/base.py`) with `create_lead`, `find_contact`, `refresh_auth`, `check_stock`.
- [ ] **T2.5**: Implement custom `api/crm/transport.py` wrapping `common/ssrf_guard.py` with DNS pinning, blocking private IPs, and disabling redirects (`allow_redirects=False`). External libraries permitted only if routed through this transport; otherwise thin clients mandatory.
- [ ] **T2.6**: Create `api/db/services/crm_service.py` (`CRMConnectionService`, `CRMOutboxService`) with strict `tenant_id` query filtering.
- [ ] **T2.7**: Implement AES-256-GCM encryption (`enc:v2:`) on `CRMConnection.config` with `get_decrypted_config()` helper.
- [ ] **T2.8**: Implement fail-closed licensing gate: strictly verify `"crm"` in license `features` (`"crm" in license.get("features", [])`). License `type: "commercial"` or `type: "enterprise"` alone DOES NOT grant access and must fail closed with `PERMISSION_ERROR`.
- [ ] **T2.9**: Add unit tests for `CRMService`, `crm_models`, license fail-closed gate, and SSRF transport guard with mutation tests.

---

### [ ] Phase T3: amoCRM Provider 1 Adapter & Fenced Distributed Token Refresh Engine
- [ ] **T3.1**: Implement `api/crm/clients/amocrm.py` thin client over `transport.py` implementing `CRMProviderBase` (contact lookup `GET /api/v4/contacts?query=...`, contact creation, open deal lookup, and lead creation).
- [ ] **T3.2**: Enforce amoCRM/Kommo domain boundary allowlisting: strictly match `*.amocrm.ru`, `*.amocrm.com`, and `*.kommo.com` `[VERIFY по документации Kommo и по реальному URL аккаунта заказчика]`; ensure exact domain boundary verification and strictly disable HTTP redirects (`allow_redirects=False`).
- [ ] **T3.3**: Implement distributed refresh lock using Redis: `crm:lock:refresh:{connection_id}` (timeout=30s) with Lua-based ownership release.
- [ ] **T3.4**: Implement double-checked database read inside lock: if token was updated while waiting for lock, use fresh token without calling amoCRM OAuth endpoint.
- [ ] **T3.5**: Implement **fencing token validation**: commit new tokens using atomic compare-and-swap (`WHERE id = :id AND token_version = :read_version`). Reject commit if version has changed. Every write to `config` increments `token_version`.
- [ ] **T3.6**: Implement recovery read for `invalid_grant`: re-read record from MySQL; if `token_version` increased, use new token; if unchanged, transition `CRMConnection.status` to `reauth_required`.
- [ ] **T3.7**: Sanitize all URLs, headers, and logs (mask phone numbers dynamically preserving prefix and last 2 digits, credentials as `********`).
- [ ] **T3.8**: Add unit and concurrency tests: 5 parallel workers result in exactly 1 API call; stale worker with outdated token_version is fenced out; revoked token sets `reauth_required`.

---

### [ ] Phase T4: Bitrix24 Provider 2 Inbound Webhook Adapter (Cloud & On-Premise)
- [ ] **T4.1**: Implement `api/crm/clients/bitrix24.py` thin client over `transport.py` implementing `CRMProviderBase` (`create_lead` via `crm.lead.add`, `find_contact` via `crm.contact.list`, `refresh_auth` via `crm.lead.fields`). OAuth app flow is strictly **OUT OF SCOPE for v1**; inbound webhook requires minimal `crm` scope.
- [ ] **T4.2**: Enforce Bitrix24 Cloud hostname validation:
  - Parse URL via `urllib.parse.urlsplit(url)`:
    - Scheme must be strictly `https`.
    - Userinfo (`username` / `password`) must be `None` (rejects `https://user:pass@portal.bitrix24.com/`).
    - Custom port must be `None` or `443` (rejects `:8080`).
    - Hostname normalized to lowercase.
    - Reject leading/trailing dots (`.portal.bitrix24.com`, `portal.bitrix24.com.`).
    - Reject punycode / IDN (`xn--...`).
  - Match hostname using `re.escape` with `re.fullmatch`:
    - Allowed zones dynamically loaded from `RAGFLOW_CRM_B24_ZONES`. Confirmed defaults [VERIFY]: `ru,kz,by,uz,com,eu,de,es,fr,it,pl,in,cn,jp,id,vn,ae,mx,uk,com.tr`. Unverified/custom zones (`com.br,ua,co,cl`) are excluded from default and configurable by platform administrator via `RAGFLOW_CRM_B24_ZONES`. Reject lookalikes (`x.bitrix24.evil.com`, `bitrix24.com.evil.net`) and raise explicit error on unknown zone: `"Unsupported Bitrix24 cloud zone '<zone>'. Allowed zones: ..."`
- [ ] **T4.3**: Enforce Bitrix24 On-Premise validation (`crm_type: bitrix24_onprem`): strictly HTTPS (`https://`), public IPs via `ssrf_guard` + DNS-pinning, no redirects; private IPs (`127.0.0.1`, `169.254.169.254`, `10.0.0.1`, `192.168.x`, `172.16.x`, `0.0.0.0`, DNS-rebinding, redirect to private) all rejected fail-closed unless included in platform admin allowlist `RAGFLOW_CRM_PRIVATE_ALLOWLIST_CIDR`.
- [ ] **T4.4**: Implement automatic redaction of webhook secret in URL path `/rest/<id>/<key>/` -> `/rest/<id>/********/` in all logs and HTTP error traces, with mutation test verifying test failure if redaction is bypassed.
- [ ] **T4.5**: Implement centralized rate limiting (~2 req/s per portal) via Redis (`crm:ratelimit:b24:{portal_host}`) with fail-open fallback to local in-memory token-bucket limiter on Redis outage, and handle `QUERY_LIMIT_EXCEEDED` (HTTP 503 / 429) / 5xx as transient with minimum 500ms pause and exponential backoff with jitter.
- [ ] **T4.6**: Implement international phone normalization to E.164 via `phonenumbers` (Apache-2.0, bundled v9.0.24) with configurable `default_phone_region` and generic dynamic length masking (no hardcoded country prefixes).
- [ ] **T4.7**: Add comprehensive unit tests and mutation tests covering all Bitrix24 cloud/onprem (including explicit tests for 127.0.0.1, 169.254.169.254, 10.0.0.1, 192.168.x, DNS-rebinding, redirect to private, userinfo, custom port, punycode, trailing dot), rate limit, redaction, and normalization gates.

---

### [ ] Phase T5: Canvas Lead Tool & Leased Outbox Worker
- [ ] **T5.1**: Implement `agent/tools/create_incoming_lead.py` inheriting from `ToolBase` (native implementation).
- [ ] **T5.2**: Enforce rate limits: strictly **1 lead write per turn** (tracked directly in Canvas graph turn state, independent of Redis, resetting per turn and strictly isolated per session) and **100 leads/hour per tenant** (Redis-backed; [OPEN DECISION for owner]: on Redis outage: fail-open with in-memory fallback for authenticated sessions vs fail-closed).
- [ ] **T5.3**: Enforce scoped anonymous access: check `self._canvas.get_channel()`; if Webhook or Embed (`AUTH_BETA`), execute ONLY if `security.allow_anonymous = True`.
- [ ] **T5.4**: Enforce input validation: E.164 phone regex (`^\+[1-9]\d{1,14}$`), max 128 chars for name, 2000 chars for text, control char stripping.
- [ ] **T5.5**: Implement deduplication: compute `business_key = HMAC_SHA256(server_secret_key, f"{tenant_id}:{connection_id}:{e164_phone}")`, acquire short dedup lock, check 24h sliding window in MySQL.
- [ ] **T5.6**: Implement outbox background worker in `rag/svr/crm_outbox_worker.py`: 5-minute atomic lease, search-before-create contact, open deal lookup, lead creation, dispatching via `CRMProviderRegistry`, exponential backoff, dead-letter after 5 tries.
- [ ] **T5.7**: Integrate worker supervision into `docker/entrypoint.sh` and `launch_backend_service.sh` with health status checks and structured logging alert on lag $>15\text{m}$.
- [ ] **T5.8**: Implement PII retention worker: scheduled cleanup purging customer PII and nulling `business_key` on records older than 30 days.
- [ ] **T5.9**: Add integration tests for tool execution, turn-limit violation, anonymous restrictions, 24h deduplication, and outbox state machine.

---

### [ ] Phase T6: Phase 2 / Provider 3: 1C:Enterprise Stock Checker Tool
- [ ] **T6.1**: Implement `agent/tools/check_stock.py` for querying 1C:Enterprise inventory balances over OData using thin client on `transport.py`.
- [ ] **T6.2**: Restrict HTTP methods strictly to `GET` to prevent state modifications in 1C.
- [ ] **T6.3**: Enforce 5-second strict timeout and SSRF guard with platform admin private IP allowlist (`RAGFLOW_CRM_1C_ALLOWLIST_CIDR`).
- [ ] **T6.4**: Enforce least privilege: accessible from anonymous channels only when `security.allow_anonymous = True`.
- [ ] **T6.5**: Add unit tests for stock checking with mock 1C OData responses.

---

### [ ] Phase T8: Docker Packaging, Migration & Rollout Verification
- [ ] **T8.1**: Verify automated table creation via Peewee `create_tables([CRMConnection, CRMOutbox], safe=True)` in `init_database_tables()`.
- [ ] **T8.2**: Integrate `crm_outbox` into `docker/launch_backend_service.sh` and `docker/entrypoint.sh` with supervisor restart controls.
- [ ] **T8.3**: Update `docker/.env-go` to include `RAGFLOW_SECRET_KEY=${RAGFLOW_SECRET_KEY}`, and add CRM configuration variables (`RAGFLOW_CRM_HOURLY_LIMIT=100`, `RAGFLOW_CRM_B24_ZONES=`, `RAGFLOW_CRM_PRIVATE_ALLOWLIST_CIDR=`).
- [ ] **T8.4**: Verify Docker Compose multi-container and unified deployment setups and rollback drills without automated startup backup (Бэкап только вручную перед деплоем).
- [ ] **T8.5**: Verify `phonenumbers>=9.0.24` dependency in `pyproject.toml` and `uv.lock` via `uv lock --check`, and verify container runtime via `docker run <image> python -c "import phonenumbers"`.

---

## STOP GATE NOTICE
> **USER DIRECTIVE**: STOP IMMEDIATELY after emitting `tasks.md`.  
> NO implementation code for CRM will be written until explicit approval is provided by the user.
