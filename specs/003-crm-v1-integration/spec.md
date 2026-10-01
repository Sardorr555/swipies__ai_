# Feature Specification: CRM Integration v1 (amoCRM Ingestion & Outbox Engine)

**Feature Branch**: `feat/crm-v1` (Target branch: `feat/crm-v1`, Base: `3bb88c257`)  
**Commit Author**: `Sardor <albakiev.sardorbek@gmail.com>`  
**Status**: Draft (Gated for approval; T0 and T1 completed, pending T2–T6/T8 review)  

---

## 1. Executive Summary & Problem Statement (WHAT & WHY)

### 1.1 Context & Business Motivation
Upstream Go compiler failures on the advertising codebase have necessitated the development of an isolated, Python-based CRM subsystem. The RAGFlow agent platform requires enterprise-grade capabilities to ingest customer conversation leads directly into Customer Relationship Management systems and query product stock balances. The CRM subsystem is architected around a unified, provider-agnostic interface (`CRMProviderBase`), implementing:
- **Provider 1 (amoCRM / Kommo)**: Full lead creation and contact lookup via REST API v4 with single-use OAuth 2.0 refresh token rotation.
- **Provider 2 (Bitrix24 Cloud & Bitrix24 On-Premise)**:
  - `bitrix24` (Cloud): Inbound webhook (`https://<portal>.bitrix24.<zone>/rest/<user_id>/<webhook_key>/`), where allowed zones are dynamically loaded from `RAGFLOW_CRM_B24_ZONES` (default confirmed: `ru,com,by,kz,uz,eu,de,es,fr,it,pl,in,cn,jp,id,vn,ae,mx,uk,com.tr` [VERIFY]; unconfirmed/custom zones `com.br,ua,co,cl` excluded from default and configurable by platform administrator), allowing new regional zones without code release. Host boundary validation strictly blocks lookalikes (`x.bitrix24.evil.com` and `bitrix24.com.evil.net`).
  - `bitrix24_onprem`: Dedicated self-hosted enterprise portals, strictly HTTPS (`https://`), public IPs guarded by SSRF & DNS-pinning; private subnets permitted ONLY via platform administrator allowlist (`RAGFLOW_CRM_PRIVATE_ALLOWLIST_CIDR`).
  - Webhook URL credentials are encrypted at rest with `enc:v2:`, and the token path `/rest/<user_id>/<webhook_key>/` is automatically redacted as `/rest/<user_id>/********/` in all logs, client exceptions, and telemetry. OAuth applications for Bitrix24 are strictly **OUT OF SCOPE for v1**; webhooks must be provisioned with minimal CRM-only permissions.
- **Provider 3 (1C:Enterprise)**: Read-only inventory balance queries (`check_stock`) over standard 1C OData REST interface.

To maintain platform stability, security, and rapid deployment, the CRM module is engineered with zero dependencies on advertising code.

### 1.2 Core Architectural Principles
- **Provider-Agnostic Interface**: All CRM operations route through an abstract provider contract (`CRMProviderBase`): `create_lead`, `find_contact`, `refresh_auth`, `check_stock`. Supported `crm_type` values: `amocrm`, `bitrix24`, `bitrix24_onprem`, `1c_odata`.
- **Absolute Ads Subsystem Isolation (AC-03)**: The CRM module operates in complete physical and logical isolation from the advertising module (`ad_engine_service`, `ad_policy_service`, `ad_app`, `web/src/pages/ads`). No cross-imports, shared runtime state, or circular dependencies.
- **Native Tools & Strict Custom Transport Requirement**:
  - Agent tools remain our own internal implementation (`agent/tools/create_incoming_lead.py`, `agent/tools/check_stock.py`).
  - Third-party client libraries are permitted ONLY IF all HTTP requests route strictly through our internal `transport.py` (which enforces SSRF guard, DNS pinning, and `allow_redirects=False`). If an external library cannot be cleanly injected with our transport without monkey patching, our own thin client is mandatory.
- **Model Context Protocol (MCP) Scope Boundary**:
  - MCP integration for CRM is strictly **OUT OF SCOPE for v1**.
  - Future iterations may introduce read-only MCP servers for CRM, but v1 relies exclusively on native Agent Canvas tools and direct REST outbox dispatching.
- **Zero-Trust Multi-Tenancy & RBAC**: Every data row (`CRMConnection`, `CRMOutbox`) has a non-nullable `tenant_id`. All REST endpoints utilize `@add_tenant_id_to_kwargs`. Connection management (credentials, OAuth tokens, deletion) is strictly restricted to `OWNER` and `ADMIN` tenant roles.
- **Fail-Closed Licensing (Explicit `features: ["crm"]` Required)**:
  - CRM access is strictly gated by the presence of `"crm"` in the cryptographically verified license payload's `features` list: `license_is_valid() and "crm" in license_payload.get("features", [])`.
  - License `type: "commercial"` or `type: "enterprise"` alone **DOES NOT** grant access to CRM. If `"crm"` is absent from `features`, all CRM REST endpoints, Canvas tools, and background workers fail closed immediately with `PERMISSION_ERROR`.
- **Scoping of Anonymous Channels (Webhook & Web Embed `AUTH_BETA`)**:
  - The anonymous restriction applies **strictly to CRM tools**, NOT as a global block-list for other standard agent tools.
  - Within the CRM module, **ONLY `create_incoming_lead` and `check_stock` are permitted**.
  - Tools determine the invoking channel via canvas metadata (`self._canvas.get_channel()`).
  - For public embed/webhook channels, CRM tools fail closed unless the tenant explicitly opts in by setting `security.allow_anonymous = True` in the tool's Canvas DSL configuration.
- **International Phone Sanitization & Dynamic Length Masking**:
  - Phone validation and parsing use Google's `phonenumbers` package (Apache-2.0 license, bundled as `phonenumbers 9.0.24`).
  - Configurable `default_phone_region` per connection (e.g. `"US"`, `"DE"`, `"RU"`). Parses international and national formats into standard E.164.
  - Generic phone masking for arbitrary digit lengths: masks the interior digits, preserving country prefix and last 2 digits (e.g. `+1415*****71`, `+4420*****50`, `+4930****67`), eliminating hardcoded country prefixes.
- **At-Rest & In-Flight Cryptographic Confidentiality**: All API tokens, client secrets, webhook keys, and refresh tokens are encrypted at rest using AES-256-GCM (`enc:v2:`) derived from `RAGFLOW_SECRET_KEY` via HKDF-SHA256. API responses mask credentials as `********`. URL credentials, webhook keys in path `/rest/<id>/<key>/`, and phone numbers are automatically redacted before logging.
- **Bitrix24 Rate Limits & Transient Handling**:
  - Per official Bitrix24 REST documentation ([Bitrix24 REST Limitations](https://training.bitrix24.com/rest_help/general/rest_limits.php) [VERIFY]), the platform enforces a Leaky Bucket limit of ~2 requests/second per webhook.
  - Centralized rate limit of 2 req/s per portal enforced via Redis key `crm:ratelimit:b24:{portal_host}`.
  - **Fail-Open Delivery Behavior upon Redis Outage**: If Redis becomes unreachable, outbound lead delivery fails open to a local per-worker in-memory token-bucket limiter (2 req/s) with a warning logged (`WARNING: Redis rate-limiter unreachable, falling back to local in-memory limiter`). Any temporary burst errors from Bitrix24 (`QUERY_LIMIT_EXCEEDED`, HTTP 503 / 429) or 5xx are handled as transient failures with a minimum 500ms throttling pause and exponential backoff with jitter, preventing lead drops or lost outbox records.
  - **Canvas Inbound Lead Tool Rate Limits vs Redis Failure**:
    - **1 lead/turn limit**: Enforced directly inside Canvas graph execution state (`self._canvas._turn_lead_count`), with zero dependency on Redis.
    - **100 leads/hour per tenant limit**: Tracked in Redis (`crm:ratelimit:lead:{tenant_id}`). Upon Redis failure, authenticated conversational sessions fail open with an in-memory process fallback (to prevent disrupting enterprise sales operations), while anonymous/public embed channels fail closed to protect downstream CRMs from malicious flood.
- **Outbox Architecture & amoCRM OAuth Concurrency Safety**:
  - amoCRM utilizes single-use OAuth 2.0 refresh tokens (Ref: [amoCRM OAuth Docs](https://www.amocrm.ru/developers/content/oauth/step-by-step)).
  - Token refresh is serialized via a Redis distributed lock (`crm:lock:refresh:{conn_id}`) with Lua-based ownership release.
  - Concurrency safety uses a **monotonic fencing token (`token_version`)**. If refresh fails with `invalid_grant`, the worker re-reads the record from MySQL: if `token_version` increased, another worker succeeded and the token is valid; if unchanged, status transitions to `reauth_required`. Every update to `CRMConnection.config` increments `token_version`.
  - Lead dispatch uses a persistent Outbox queue with leases, exponential backoff, jitter, and search-before-create deduplication.

---

## 2. User Scenarios & Acceptance Criteria

### User Story 1 - Secure Ingestion of Inbound Leads via Agent Canvas (Priority: P1)
As a platform tenant running a sales or support conversational agent, I want the agent to automatically register an incoming lead in my connected CRM account when contact details (phone, name, requirements) are provided in chat, without duplicate submissions or credential exposure.

**Acceptance Criteria**:
1. **Given** an agent canvas with the `create_incoming_lead` tool configured and a valid `CRMConnection`,  
   **When** the user provides contact details during a conversation,  
   **Then** the tool normalizes the phone number to E.164 using `phonenumbers` with fallback to `connection.config.default_phone_region`, sanitizes text inputs (strips control characters, enforces 128 char limit on name, 2000 on text), enqueues an outbox entry with status `PENDING`, and returns a confirmation to the conversational flow.
2. **Given** an ongoing conversational turn,  
   **When** an agent attempts to invoke `create_incoming_lead` multiple times within the same turn,  
   **Then** the tool allows strictly **1 lead creation per turn**, tracked directly in Canvas graph turn state (`self._canvas._turn_lead_count`) independently of Redis, rejecting subsequent calls with a rate-limit error code to prevent runaway agent loops. `_turn_lead_count` resets to 0 at the start of each new turn/message execution, and is strictly isolated per Canvas execution context (concurrent sessions in different threads or worker tasks have isolated instances and do not share or corrupt counters).
3. **Given** tenant-level volume,  
   **When** evaluating lead generation rate,  
   **Then** the tool enforces a limit of **100 leads/hour per tenant** backed by Redis key `crm:ratelimit:lead:{tenant_id}`.  
   **[OPEN DECISION - Product Owner Review Required]**: Behavior upon Redis outage:  
   - *Option A (Default recommendation for sales uptime)*: Authenticated conversational sessions fail open using a local in-memory fallback counter with logged warnings (avoiding loss of real customer sales opportunities), while unauthenticated anonymous/public embed channels fail closed to prevent flood attacks.  
   - *Option B (Strict fail-closed)*: All sessions fail closed immediately upon Redis connection failure, returning a temporary service unavailable error.
4. **Given** an inbound request originating from public channels (Webhook or Web Embed `AUTH_BETA`),  
   **When** the agent invokes `create_incoming_lead`,  
   **Then** execution is permitted ONLY if the tool is explicitly configured with `security.allow_anonymous = True`. Otherwise, invocation fails closed with `403 Forbidden`.

---

### User Story 2 - Deterministic Deduplication & Outbox Lease Delivery (Priority: P1)
As an operations engineer, I want lead submissions to be deduplicated over a 24-hour sliding window and dispatched via a reliable leased background worker, ensuring target CRMs do not receive duplicate leads or lost entries during downstream latency spikes.

**Acceptance Criteria**:
1. **Given** an incoming lead with a phone number,  
   **When** the lead is submitted,  
   **Then** the system computes a deterministic business key:  
   `business_key = HMAC_SHA256(server_secret_key, f"{tenant_id}:{connection_id}:{e164_phone}")`.
2. **Given** an enqueue attempt,  
   **When** checking for duplicates,  
   **Then** a short distributed lock (`crm:lock:dedup:{business_key}`, TTL 10s) guarantees atomic check-and-insert. A database query checks if a record with the same `business_key` exists within the sliding window: `created_at >= NOW() - INTERVAL 24 HOUR` with status `PENDING`, `PROCESSING`, or `SENT`. If found, enqueueing is skipped and the existing lead ID is returned.
3. **Given** outbox records in `PENDING` or expired `PROCESSING` state,  
   **When** the outbox worker polls for work,  
   **Then** it atomically claims records using a 5-minute lease:  
   `UPDATE crm_outbox SET status = 'PROCESSING', processing_started_at = NOW(), retry_count = retry_count + 1 WHERE id = :id AND (status = 'PENDING' OR (status = 'PROCESSING' AND processing_started_at < NOW() - INTERVAL 5 MINUTE) OR (status = 'FAILED' AND next_retry_at <= NOW()))`.
4. **Given** an outbox worker dispatching a lead,  
   **When** executing remote operations,  
   **Then** it dispatches to the corresponding `CRMProviderBase` implementation based on `connection.crm_type`.
5. **Given** a downstream network timeout, rate limit (`QUERY_LIMIT_EXCEEDED`), or 5xx server error,  
   **When** the outbox worker encounters the failure,  
   **Then** the outbox record is marked `FAILED` with retry counter incremented and scheduled for retry with exponential backoff: $2^n \times 10\text{s}$ with jitter. After 5 consecutive failures, the record transitions to `DEAD_LETTER`.

---

### User Story 3 - amoCRM Token Refresh with Fenced Lock & Recovery (Priority: P1)
As a tenant administrator, I want my amoCRM OAuth connection to remain active continuously without breaking when multiple concurrent worker processes attempt token refresh, even under network latency spikes or worker pauses.

**Acceptance Criteria**:
1. **Given** an expired amoCRM OAuth access token,  
   **When** an outbox worker prepares to execute an API call,  
   **Then** the worker acquires a Redis distributed lock: `crm:lock:refresh:{conn_id}` (TTL: 30s) using a unique owner UUID. Lock release is performed strictly via a Lua script checking ownership.
2. **Given** the lock is acquired,  
   **When** the worker enters the critical section,  
   **Then** it reads the current record and its `token_version` from MySQL. If another worker already refreshed the token (access token expiration > current time), the worker uses the refreshed token immediately without issuing a redundant OAuth request.
3. **Given** an unrefreshed token inside the lock,  
   **When** the worker exchanges the single-use refresh token with amoCRM,  
   **Then** the worker commits the newly issued `access_token` and `refresh_token` (encrypted with AES-256-GCM `enc:v2:`) via an atomic conditional update:  
   `UPDATE crm_connection SET config = :new_config, token_version = token_version + 1, updated_at = :now WHERE id = :conn_id AND token_version = :read_version`.
4. **Given** an amoCRM response of `invalid_grant` or HTTP 400 during refresh,  
   **When** refresh fails,  
   **Then** the worker re-reads `CRMConnection` from MySQL and checks `token_version`:
   - If `token_version > :read_version`, another worker refreshed successfully; the worker uses the new token.
   - If `token_version == :read_version`, the token was genuinely revoked; the connection status transitions to `reauth_required`, workers halt retry loops, and an alert is logged with credentials masked.

---

### User Story 4 - SSRF Protection, Strict Hostnames & Privacy Compliance (Priority: P0)
As a security auditor, I want all outbound network connections to external CRM endpoints to be strictly validated against SSRF attacks, credential leaks, and data retention rules.

**Acceptance Criteria**:
1. **Given** any external URL configured for a CRM connection,  
   **When** outbound HTTP requests are prepared,  
   **Then** the system resolves the hostname, applies `common/ssrf_guard.py` to block all private and reserved IP addresses (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `127.0.0.0/8`, `169.254.0.0/16`, `::1`, link-local, loopback). DNS-pinning binds the client to the validated IP address. HTTP redirects are strictly disabled (`allow_redirects=False`) to prevent open redirect SSRF bypass.
2. **Given** an amoCRM integration,  
   **When** target hosts are evaluated,  
   **Then** outbound requests are restricted strictly to allowlisted domains with exact domain boundary checks: `*.amocrm.ru`, `*.amocrm.com`, and `*.kommo.com` `[VERIFY]`. Boundary matching must ensure that target host is either identical to the allowlisted base domain or ends with `.` followed by the base domain (e.g. `client.amocrm.ru`, `tenant.kommo.com`), strictly rejecting lookalike prefixes/suffixes (e.g., `evilamocrm.ru` or `amocrm.ru.attacker.com`).
3. **Given** outbox records in the database,  
   **When** a record reaches an age of 30 days ($D=30\text{d}$) regardless of status (`SENT`, `FAILED`, `DEAD_LETTER`),  
   **Then** a scheduled cleanup task scrubs all PII (`lead_data`, customer name, phone number) AND sets `business_key = NULL`, retaining only anonymized telemetry (`id`, `tenant_id`, `created_at`, `status`).

---

### User Story 5 - Provider 2: Bitrix24 Cloud & On-Premise Inbound Webhook Ingestion (Priority: P1)
As a platform tenant using Bitrix24, I want the agent outbox to dispatch leads directly to my Bitrix24 portal (Cloud or On-Premise) via an inbound webhook, with the webhook secret encrypted at rest, path secrets redacted in all logs, and domain boundaries strictly enforced.

**Acceptance Criteria**:
1. **Bitrix24 Cloud Hostname Validation (`crm_type: bitrix24`)**:
   - Outbound requests must target `https://<portal>.bitrix24.<zone>/rest/<user_id>/<webhook_key>/`.
   - Allowed zones `<zone>` are parsed dynamically from platform configuration `RAGFLOW_CRM_B24_ZONES`. В официальной документации Bitrix24 единого исчерпывающего перечня всех региональных доменных зон не существует (ссылки на внутренние справочные статьи являлись пересказом регионального распределения сервиса, а не нормативной спецификацией).
   - Список зон по умолчанию сформирован по принципу строгой двойной верификации: документальное упоминание региона И успешный DNS wildcard резолв (`zz-probe-<rand>.bitrix24.<zone>`) на IP-адреса Bitrix24 / AWS:
     - **Список зон по умолчанию (20 подтверждённых зон)**: `ru, kz, by, uz, com, eu, de, pl, it, fr, uk, ae, com.tr, es, in, cn, jp, vn, id, mx`
     - **Исключены из списка по умолчанию**:
       - `com.br, co` — wildcard DNS успешно указывает на инфраструктуру Bitrix (AWS São Paulo `54.232.190.40`), но прямых нормативных цитат в документации нет; подключаются администратором платформы через `RAGFLOW_CRM_B24_ZONES` при необходимости.
       - `br, tr, ua` — DNS wildcard резолв возвращает `NXDOMAIN ([Errno 11001])` (доменная зона не обслуживает порталы Bitrix24).
       - `cl` — DNS резолв завершается сетевой ошибкой / отказом (`[Errno 11002]`, NS указывает на `hostmonster.com`).
     - Любая региональная зона может быть добавлена администратором платформы через переменную окружения `RAGFLOW_CRM_B24_ZONES` без пересборки и релиза контейнера.
   - Host validation strictly parses the URL using `urllib.parse.urlsplit(url)`:
     - Scheme must be strictly `https` (HTTP rejected).
     - `username` and `password` must be `None` (userinfo like `https://user:pass@portal.bitrix24.com/` rejected).
     - `port` must be `None` or `443` (custom ports like `:8080` rejected).
     - Hostname is normalized to lowercase; leading and trailing dots are rejected.
     - Punycode / IDN domains (`xn--...`) are rejected.
     - Regex pattern constructed safely with `re.escape` for all allowed zones:  
       `rf"^[a-z0-9](?:[a-z0-9-]{{0,61}}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{{0,61}}[a-z0-9])?)*\.bitrix24\.(?:{'|'.join(re.escape(z.strip().lower()) for z in allowed_zones)})$"`  
       evaluated via `re.fullmatch(pattern, hostname)`.
   - Lookalikes like `x.bitrix24.evil.com`, `bitrix24.com.evil.net`, or `evilbitrix24.com` are rejected fail-closed.
   - Unknown or invalid zone raises an explicit error: `"Unsupported Bitrix24 cloud zone '{zone}'. Allowed zones: {zones}. For custom domains or on-premise installations, configure as 'bitrix24_onprem'."`
2. **Bitrix24 On-Premise Validation (`crm_type: bitrix24_onprem`)**:
   - Connection URL must strictly enforce HTTPS scheme (`https://`). HTTP is forbidden.
   - Target host must pass `ssrf_guard`. Connections to private/reserved IP spaces (`127.0.0.1`, `169.254.169.254`, `10.0.0.1` / `10.0.0.0/8`, `172.16.0.1` / `172.16.0.0/12`, `192.168.x.x` / `192.168.0.0/16`, `0.0.0.0`, `::1`) fail closed unless the target IP/subnet is explicitly present in the platform administrator allowlist: `RAGFLOW_CRM_PRIVATE_ALLOWLIST_CIDR`. Tenants cannot override or define private CIDR entries.
   - DNS pinning binds the client socket directly to the validated IP, preventing DNS-rebinding attacks (where initial lookup yields public IP, but connect-time yields private IP).
   - HTTP redirects are strictly forbidden (`allow_redirects=False`). Attempts to redirect to private addresses (e.g. 301/302 returning `http://127.0.0.1/` or `http://169.254.169.254/`) fail immediately.
   - Explicit onprem test matrix verifies rejection of: `127.0.0.1`, `169.254.169.254`, `10.0.0.1`, `192.168.1.1`, `172.16.0.1`, `0.0.0.0`, DNS-rebinding, and redirect to private IP — all rejected fail-closed unless included in platform allowlist.
3. **Webhook Path Redaction in Logs & Error Traces**:
   - The webhook secret token in URL path `/rest/<user_id>/<webhook_key>/` must be sanitized in all logging statements, HTTP request dumps, and exception messages using regex replacement: `/rest/(\d+)/[a-zA-Z0-9_-]+/` -> `/rest/\1/********/`.
   - Regression test verifies that raw webhook secret tokens never appear in logs or error representations. Mutation removing this redaction immediately fails the test suite.
4. **Rate Limiting & Transient Error Backoff**:
   - Centralized rate limit of 2 req/s per portal enforced across all worker instances using Redis key `crm:ratelimit:b24:{portal_host}`.
   - Bitrix24 errors `QUERY_LIMIT_EXCEEDED` (HTTP 503 / 429) and 5xx are handled as transient with minimum 500ms pause and exponential backoff with jitter.
   - **Acceptance Criterion при отказе Redis (fail-open)**: Если Redis недоступен или выдаёт ошибку подключения, проверка рейт-лимита выполняется в режиме fail-open (запрос пропускается, отправка лида не блокируется, в системный лог пишется `WARNING: Redis rate-limiter unreachable, falling back to fail-open`).
5. **Least Privilege & Out of Scope Boundary**:
   - Bitrix24 OAuth application flows are strictly **OUT OF SCOPE for v1**.
   - User documentation specifies that inbound webhooks must be created with minimal permissions: strictly the `crm` scope.
6. **Provider Contract Implementation**:
   - `create_lead`: Invokes `crm.lead.add` (and optional contact linking via `crm.contact.list`).
   - `find_contact`: Invokes `crm.contact.list` filtering by `PHONE` / `EMAIL`.
   - `refresh_auth`: Issues a lightweight `crm.lead.fields` query to verify webhook validity without altering credentials.
7. **Phone Number International Normalization & Masking**:
   - International normalization to E.164 via `phonenumbers` library (Apache 2.0).
   - Default region configured per connection (`default_phone_region`, e.g. "US", "DE", "UZ", "RU").
   - Universal dynamic masking for any phone length: preserves country code/prefix and last 2 digits, masking all middle characters with `*` (e.g. `+1 555-***-**12`, `+49 170 ****123`, `+998 90 *** ** 12`).
   - All tests and documentation are free of hardcoded single-country (+7) assumptions, with test cases covering multiple country prefixes (+1, +44, +49, +998, +81).

---

### User Story 6 - Provider-Agnostic Interface Contract (Priority: P1)
As a software engineer, I want all CRM providers to implement a uniform contract so that Canvas tools and the Outbox worker remain decoupled from vendor-specific REST quirks.

**Acceptance Criteria**:
1. **Unified Interface (`CRMProviderBase`)**:
   - `create_lead(lead_data: dict) -> CRMLeadResult`: Accepts normalized lead payload (`name`, `phone`, `email`, `notes`), dispatches create request, returns remote IDs.
   - `find_contact(phone: str, email: str | None = None) -> CRMContactResult`: Searches existing contact by sanitized phone/email.
   - `refresh_auth(conn: CRMConnection) -> CRMAuthResult`: Handles token rotation (amoCRM OAuth 2.0 fenced refresh) or credential verification (Bitrix24/1C).
   - `check_stock(sku_or_name: str, warehouse: str | None = None) -> CRMStockResult`: Queries inventory balance (implemented by 1C OData, returns not supported for pure CRMs).
2. **Transport Compliance**:
   - Every provider client must execute outbound HTTP requests through `api.crm.transport.py` (SSRF IP filter, DNS pinning, `allow_redirects=False`). External libraries (e.g. `b24pysdk`, `fast-bitrix24`, community amoCRM packages) are prohibited unless they route 100% of network traffic through this transport; otherwise, thin clients implemented directly on `transport.py` are mandatory.
3. **MCP Scope Boundary**:
   - MCP is strictly excluded from v1. Provider implementations interface directly with internal services. Read-only MCP exposure is deferred to post-v1.

---

### User Story 7 - Phase 2 / Provider 3: 1C:Enterprise Stock Checker Tool (Priority: P3)
As a sales agent during a chat interaction, I want to query product inventory balances in 1C:Enterprise without placing orders or mutating data.

**Acceptance Criteria**:
1. **Given** an authenticated 1C:Enterprise connection with read-only credentials,  
   **When** the agent invokes `check_stock` with a product SKU or name,  
   **Then** the tool queries the 1C OData/REST interface via the SSRF-guarded HTTP client with a strict 5-second timeout and returns current stock balances across warehouses.
2. **Given** a 1C server hosted on an on-premise private network,  
   **When** evaluating SSRF protections,  
   **Then** connections to private RFC1918 IPs are permitted ONLY if the target IP/subnet is explicitly defined in the platform administrator allow-list (`RAGFLOW_CRM_1C_ALLOWLIST_CIDR`). Tenant-configured URLs cannot target arbitrary private subnets.
3. **Given** any attempt by the agent or user DSL to mutate data via `check_stock`,  
   **Then** HTTP methods are restricted strictly to `GET`, preventing state modifications in 1C.
4. **Given** an anonymous channel (Webhook or Web Embed),  
   **When** invoking `check_stock`,  
   **Then** it is permitted ONLY if `security.allow_anonymous = True`.

---

## 3. Database Schema & Architecture

### 3.1 Model Registration Without Circular Imports
To prevent circular dependencies with `api/db/db_models.py`, `CRMConnection` and `CRMOutbox` are defined in `api/db/crm_models.py`, inheriting from `DataBaseModel`. They use the exact same `JSONField` as `db_models` (from `playhouse.mysql_ext`):
```python
# api/db/crm_models.py
from api.db.db_models import DataBaseModel, JSONField
from peewee import CharField, DateTimeField, IntegerField, TextField

class CRMConnection(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    tenant_id = CharField(max_length=32, null=False, index=True)
    name = CharField(max_length=128, null=False)
    crm_type = CharField(max_length=32, null=False, default="amocrm")  # amocrm, bitrix24, bitrix24_onprem, 1c_odata
    config = JSONField(null=False, default={})                         # AES-256-GCM encrypted
    status = CharField(max_length=32, null=False, default="active")    # active, disabled, reauth_required
    token_version = IntegerField(null=False, default=1)                # Fencing token / monotonic version
    created_at = DateTimeField(null=False)
    updated_at = DateTimeField(null=False)

    class Meta:
        db_table = "crm_connection"

class CRMOutbox(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    tenant_id = CharField(max_length=32, null=False, index=True)
    connection_id = CharField(max_length=32, null=False, index=True)
    business_key = CharField(max_length=64, null=True, index=True)    # HMAC-SHA256, NULL after 30d
    crm_contact_id = CharField(max_length=64, null=True)              # Remote amoCRM/Bitrix24 contact ID
    crm_lead_id = CharField(max_length=64, null=True)                 # Remote amoCRM/Bitrix24 lead ID
    lead_data = JSONField(null=False, default={})                     # enc:v2: encrypted, purged after 30d
    status = CharField(max_length=32, null=False, default="PENDING")  # PENDING, PROCESSING, SENT, FAILED, DEAD_LETTER
    processing_started_at = DateTimeField(null=True, index=True)      # Worker lease timestamp (5 min lease)
    retry_count = IntegerField(default=0)
    next_retry_at = DateTimeField(null=True, index=True)
    last_error = TextField(null=True)
    created_at = DateTimeField(null=False, index=True)
    updated_at = DateTimeField(null=False)

    class Meta:
        db_table = "crm_outbox"
```

### 3.2 Lazy Model Registration
In `api/db/db_models.py`, `CRMConnection` and `CRMOutbox` are registered inside `init_database_tables()` via lazy import to avoid top-level circular imports:
```python
def init_database_tables():
    ...
    from api.db.crm_models import CRMConnection, CRMOutbox
    db.create_tables([..., CRMConnection, CRMOutbox])
```

---

## 4. Worker Management & Observability

### 4.1 Process Supervision
The background worker `rag/svr/crm_outbox_worker.py` is integrated into `docker/entrypoint.sh` and `launch_backend_service.sh` under service supervisor controls.

### 4.2 Metrics & Alerting
- **Telemetry & Health Reporting**:
  - Outbox worker monitoring uses structured JSON logging and health status checks.
  - Periodic database lag query: `SELECT TIMESTAMPDIFF(SECOND, MIN(created_at), NOW()) AS oldest_pending_sec FROM crm_outbox WHERE status = 'PENDING'`.
  - **Structured Log Alert**: When `oldest_pending_sec > 900` (15 minutes), the worker emits a high-priority structured error log:
    `logger.error("CRM_OUTBOX_LAG_CRITICAL: oldest_pending_seconds=%d threshold=900", lag)`
    captured by server log collectors (journald/Vector/Promtail/CloudWatch).
  - **Health Check Endpoint**: `/api/v1/crm/health` returns `{"status": "ok", "oldest_pending_seconds": lag, "active_leases": count}` for container liveness and readiness monitoring.

---

## 5. Security & Isolation Matrix

| Risk Vector | Threat Description | Architectural Mitigation |
| :--- | :--- | :--- |
| **Ads Cross-Contamination** | Broken Go upstream ads build breaks CRM | Complete isolation: zero imports of `ad_engine_service`, `ad_policy_service`, `ad_app`, `web/src/pages/ads`. |
| **MCP Cross-Tenant Ingestion** | Tenant injects foreign `mcp_id` into canvas DSL | `MCPServerService.get_by_id_and_tenant` validates tenant ownership during agent save (`agent_api.py`) and runtime (`agent_with_tools.py`). |
| **SSRF to Cloud Metadata / LAN** | Attacker configures internal webhook URL or SSRF redirect | `common/ssrf_guard.py` IP filter + DNS pinning + amoCRM/Kommo boundary allowlist (`*.amocrm.ru`, `*.amocrm.com`, `*.kommo.com` `[VERIFY]`) + `allow_redirects=False`. |
| **1C LAN Infiltration** | SSRF bypass to internal enterprise subnets | Private IPs blocked unless specifically whitelisted in platform `RAGFLOW_CRM_1C_ALLOWLIST_CIDR`. |
| **OAuth Token Collision & Stale Overwrite** | Dual workers refresh single-use amoCRM token | `RedisDistributedLock` with Lua ownership release + double-checked DB read + **monotonic fencing token (`token_version`)**. |
| **Credential Leakage in Logs** | OAuth tokens or phone numbers dumped in logs | URLs sanitized; credentials masked; phone numbers masked dynamically preserving prefix and last 2 digits (e.g. `+1 555-***-**12`, `+998 90 *** ** 12`). |
| **Runaway Agent Loop** | Agent creates 50 duplicate leads in one prompt | Strict limit: **1 `create_incoming_lead` call per turn** + **100 leads/hour per tenant**. |
| **License Bypass** | Commercial type claimed without CRM entitlement | `license_verifier.py` fail-closed check: **strictly requires `"crm"` in `features`**; `type: "commercial"` alone fails closed. |

---

## 6. Rollout & Deployment Architecture (Docker, CI/CD, Secrets)

### 6.1 Image Build and Publishing Architecture
- **Dockerfiles**:
  - `Dockerfile` (Standard / Full Stack): Multi-stage container build based on Ubuntu 24.04:
    - *Base stage*: Configures APT mirrors, installs system runtimes (OpenCV dependencies, JVM for Apache Tika, headless Chrome libraries, jemalloc, PostgreSQL client), and unpacks pretrained DeepDoc/layout models and HuggingFace assets from `infiniflow/ragflow_deps:latest`.
    - *Builder stage*: Builds frontend static assets via Vite (`npm run build` with `--max-old-space-size=8192`) and compiles Python dependencies via `uv` into a standalone virtual environment (`/ragflow/.venv`).
    - *Production stage*: Copies the prebuilt Python virtual environment, Nginx configuration files (`ragflow.conf.golang`, `ragflow.conf.python`, `ragflow.conf.hybrid`), configuration templates (`docker/service_conf.yaml.template`), frontend static assets (`/ragflow/web/dist`), migration tools (`tools/scripts/`), and entrypoints (`docker/entrypoint*.sh`). Default runtime entrypoint: `./entrypoint.sh`.
  - `Dockerfile_go` (Go-Accelerated Engine): Multi-stage container build:
    - Compiles the Go backend server (`bin/ragflow_server`) and CLI (`bin/ragflow-cli`) via `./build.sh --go`, linking C++ bindings and native libraries (PCRE2, ONNX Runtime, static pdfium and pdf_oxide).
    - Assembles the runtime image with compiled Go binaries and lightweight Python execution support. Default runtime entrypoint: `./entrypoint-go.sh`.
  - `build.sh`:
    - Shell compilation script orchestrating C++ binding compilation in `internal/binding/cpp/cmake-build-release` and static Go server compilation (`bin/ragflow_server`).
- **CI/CD Pipeline (`.github/workflows/deploy_new_server.yml`, `deploy_main.yml`, `release.yml`)**:
  - Automated deployment triggers on pushes to target release branches (`test`, `licence_v` in `deploy_new_server.yml`; `swipies_26` in `deploy_main.yml`).
  - Deploy step connects to deployment hosts (e.g. `51.20.190.248`) via SSH (`appleboy/ssh-action`), synchronizes code (`git fetch origin ${DEPLOY_BRANCH}` and `git reset --hard origin/${DEPLOY_BRANCH}`), rebuilds frontend assets (`docker compose build frontend`), restarts containers (`docker compose up -d`), verifies health status (`docker compose ps`), and executes post-deployment administrative scripts.
  - Official release images are tagged and published to Docker registries (Docker Hub / GCR mirrors) for distribution.

### 6.2 Python Runtime Services
The RAGFlow application architecture executes Python code across four core background and API services:
1. **API Web Server (`api/ragflow_server.py`)**:
   - Quart asynchronous web server handling external and internal HTTP/WebSocket traffic, RESTful API endpoints (`/v1/crm/...`), Agent Canvas executions, and MCP proxy routing.
2. **Task Executor (`rag/svr/task_executor.py`)**:
   - High-throughput asynchronous worker instances consuming document ingestion, chunking, OCR, and embedding jobs from Redis message queues.
3. **Data Sync Server (`rag/svr/sync_data_source.py`)**:
   - Background daemon managing continuous synchronization of external document connectors and repositories.
4. **CRM Outbox Worker (`rag/svr/crm_outbox_worker.py`)**:
   - Dedicated asynchronous background daemon introduced for CRM integration:
     - Leases pending outbox records from MySQL (`crm_outbox`) using 5-minute lease locks (`processing_started_at`).
     - Performs E.164 phone sanitization and checks sliding 24-hour deduplication keys (`business_key`).
     - Acquires distributed Redis locks (`crm:lock:refresh:{conn_id}`) with Lua validation for serializing single-use amoCRM OAuth 2.0 token refreshes.
     - Dispatches remote HTTP requests to amoCRM REST API v4 using client-side search-before-create logic (contacts and deals/leads).
     - Manages exponential backoff retries with jitter and dead-letter queue transitions.
     - Enforces 30-day PII retention scrubbing on expired records.

### 6.3 Outbox Worker Container Execution
- **Process Supervisor CLI (`docker/launch_backend_service.sh`)**:
  - Registered service argument `crm_outbox`:
    ```bash
    case $arg in
      ...
      crm_outbox|crm-outbox)
        START_CRM_OUTBOX=1
        SERVICE_SELECTED=1
        ;;
    ```
  - Execution block:
    ```bash
    run_crm_outbox() {
      echo "Starting CRM Outbox Worker..."
      "$PY" rag/svr/crm_outbox_worker.py
    }
    if [[ "$START_CRM_OUTBOX" -eq 1 ]]; then
      run_crm_outbox &
      PIDS+=($!)
    fi
    ```
  - Inherits supervisor signal trapping (`cleanup()` on `SIGINT`/`SIGTERM`) and retry handling (`MAX_RETRIES=5`).
- **Container Entrypoints (`docker/entrypoint.sh` & `docker/entrypoint-go.sh`)**:
  - Entrypoints support flag `--disable-crm-outbox` (default: enabled if license contains `"crm"` feature).
  - Launches worker under restart supervisor:
    ```bash
    if [[ "${ENABLE_CRM_OUTBOX}" -eq 1 ]]; then
      echo "Starting CRM outbox worker..."
      run_with_restart "CRM outbox worker" "$PY" rag/svr/crm_outbox_worker.py &
    fi
    ```
- **Compose Service Definitions (`docker/docker-compose.yml`, `docker-compose-go.yml`)**:
  - Unified deployment: Runs concurrently within the main backend container (`swipies-cpu` / `swipies-gpu`) managed by `entrypoint.sh`.
  - Dedicated worker deployment (optional profile `crm-worker`):
    ```yaml
    ragflow-crm-worker:
      container_name: swipies-crm-worker
      image: ${RAGFLOW_IMAGE}
      profiles: ["crm-worker"]
      command: ["/ragflow/docker/launch_backend_service.sh", "crm_outbox"]
      depends_on:
        mysql: { condition: service_healthy }
        redis: { condition: service_healthy }
      volumes:
        - ./service_conf.yaml.template:/ragflow/conf/service_conf.yaml.template
        - ./ragflow-logs:/ragflow/logs
      env_file: .env
      networks:
        - ragflow
      restart: unless-stopped
    ```

### 6.4 Table Lifecycle & Peewee ORM Initialization
- **Automatic Table Creation via Peewee (`init_database_tables()`)**:
  - In RAGFlow, database tables are created automatically by `init_database_tables()` in `api/db/db_models.py:1062` at backend startup (`ensure_db_init` in `docker/entrypoint.sh:261` and `docker/launch_backend_service.sh:176`).
  - `init_database_tables()` inspects all subclasses of `DataBaseModel` and executes `obj.create_table(safe=True)`.
  - `CRMConnection` and `CRMOutbox` in `api/db/crm_models.py` inherit from `DataBaseModel` and are registered in `init_database_tables()`. Therefore, tables are created automatically when backend services start.
- **Connector Credentials Migration CLI (`api/scripts/migrate_connector_credentials.py`)**:
  - The security migration CLI for existing connector credentials supports:
    - `--dry-run`: Read-only preview of unencrypted/encrypted configs without database mutations.
    - `--apply`: Encrypts plaintext credentials at rest using AES-256-GCM (`enc:v2:`).
    - `--rotate`: Re-encrypts ciphertext using a new primary key via `RAGFLOW_SECRET_KEYS_ROTATION`.

### 6.5 Security Fix Rollout Protocol (Code -> Dry-Run -> Apply -> Verification)
- **Политика резервного копирования**: Бэкап только вручную перед деплоем.
Because pushing to `test` or `licence_v` immediately triggers automated deployment via `deploy_new_server.yml`:
1. **Phase 1: Code & Isolated Verification (PR Branch)**:
   - All code, crypto tests, and mutation suites are developed and tested on an isolated feature branch (`feat/crm-v1`), never pushed directly to `test` or `licence_v`.
2. **Phase 2: Deploy via Git Push**:
   - Merge approved PR into `test`. The GitHub Actions workflow `deploy_new_server.yml` triggers automatically, pulls the commit, rebuilds the frontend, restarts containers, and initializes new schema tables via `ensure_db_init()`.
3. **Phase 3: Dry-Run Verification**:
   - Run the migration script in dry-run mode from inside the running container to inspect candidate records:
     ```bash
     docker exec -it swipies-cpu python api/scripts/migrate_connector_credentials.py --dry-run
     ```
   - Verify logs: confirm record counts, lack of errors, and valid `RAGFLOW_SECRET_KEY` configuration.
4. **Phase 4: Apply Migration**:
   - Execute the migration:
     ```bash
     docker exec -it swipies-cpu python api/scripts/migrate_connector_credentials.py --apply
     ```
5. **Phase 5: Post-Deployment Verification**:
   - Re-run `--dry-run`: confirm 0 unencrypted records remain.
   - Inspect container logs: `docker logs --tail 100 swipies-cpu`.
   - Verify connector and agent operational health.

### 6.6 Rollback Protocol (Actual Deployed Commits)
If deployment failures occur:
1. **Step 1: Rollback to Previously Deployed Commit**:
   - In this project, deployments are commit-based (pulled via git), not static version tags. Determine the previous working commit SHA from server `git log -n 5` or the previous successful CI deployment run log in GitHub Actions:
     ```bash
     PREV_COMMIT=$(git rev-parse HEAD~1)  # or specific verified SHA from deployment history
     git reset --hard "${PREV_COMMIT}"
     cd docker && docker compose down --remove-orphans && docker compose up -d
     ```

### 6.7 Environment Configuration & Secrets Management in `docker/`
- **Resolution of `${RAGFLOW_SECRET_KEY}` in tracked files `[VERIFY]`**:
  - In `docker/.env` and `docker/.env-go`: **Do NOT modify tracked `.env` or `.env-go` files in these commits**.
  - When `${RAGFLOW_SECRET_KEY}` is referenced in `docker-compose.yml`, Docker Compose interpolates the variable from the host shell environment. If the variable is unset on the host, Compose emits a warning and resolves it as an empty string `""`.
  - In `docker/launch_backend_service.sh:41`, `source $env_file` evaluates `${RAGFLOW_SECRET_KEY}`: if unset in the environment, it expands to `""`.
  - **Fail-Closed Behavior**: When `RAGFLOW_SECRET_KEY` is empty, missing, or shorter than 32 characters, `api.utils.key_crypto.validate_master_secret()` raises `InsecureSecretKeyError` immediately (Fail-Closed). Encryption operations halt rather than silently falling back to insecure defaults.
- **Key Rotation Protocol**:
  - Secret key rotation is conducted as an independent operational procedure without code changes:
    1. Define `RAGFLOW_SECRET_KEYS_ROTATION="old_key1,old_key2"` alongside the new `RAGFLOW_SECRET_KEY="new_key"`.
    2. Run `python api/scripts/migrate_connector_credentials.py --rotate --apply` to re-encrypt all stored configs with the new master key.
    3. Once completed and verified, remove old keys from `RAGFLOW_SECRET_KEYS_ROTATION`.
- **Zero Secrets in Git Policy**:
  - Master encryption keys (`RAGFLOW_SECRET_KEY`), database passwords, and OAuth client secrets MUST NEVER be committed to git.
  - Production secrets are injected exclusively via host environment variables, CI/CD secrets (`${{ secrets.RAGFLOW_SECRET_KEY }}`), or untracked `.env.local` files in `.gitignore`.

### 6.8 Known Architectural Gaps (Backlog / Future Scope)
- **Known wiring gap: `canvas_owner_tenant` propagation**:
  В текущей реализации `agent_chat_completion`, `_webhook_impl`, и `bot_api.begin_inputs` не передают `canvas_owner_tenant` от владельца холста к сессиям командного доступа (в `_webhook_impl` устранена тавтология присвоения). Полная проводка владельца для этих трёх точек входа зафиксирована как известный архитектурный пробел и задача бэклога следующей итерации.
