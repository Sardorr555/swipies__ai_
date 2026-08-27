# Technical Implementation Plan: Admin Panel — AI Providers & Models Management

**Specification Reference:** [`docs/specs/spec_admin_ai_management.md`](file:///D:/ragflow/swipies_25/ragflow/docs/specs/spec_admin_ai_management.md)  
**Status:** Draft / Ready for Review  
**Version:** 1.0.0  
**Target Branch:** `test`  
**Plan Key:** `plan_admin_ai_management`  

---

## 1. Architecture & Dependency Graph

```mermaid
graph TD
    subgraph Phase 1: Backend Admin API Modernization
        API_PROV[1.1 Provider Endpoints & CredentialResolver Wiring<br/>GET /providers, POST /providers, DELETE /providers]
        API_TEST[1.2 Dual Testing Endpoints<br/>POST /test-connection & POST /verify-live]
        API_MODELS[1.3 Model Registry Endpoints<br/>GET /models, POST /models, DELETE /models]
        AUTH[1.4 Superuser RBAC Guard<br/>require_superuser() in ai_management_app.py]
        AUTH --> API_PROV
        AUTH --> API_TEST
        AUTH --> API_MODELS
    end

    subgraph Phase 2: Frontend Service Layer
        TS_TYPES[2.1 TypeScript Interfaces & DTOs<br/>AIProviderRecord, ModelItem, VerificationResult]
        SVC[2.2 Admin AI Management Service Client<br/>web/src/services/ai-management-service.ts]
        TS_TYPES --> SVC
    end

    subgraph Phase 3: Frontend UI Components
        UI_PROV[3.1 Providers Management Tab<br/>Cards/Table, Masked Keys, Status Badges]
        UI_MODAL[3.2 Live Verification Modal<br/>Real-time 3-Stage Progress: Chat -> Stream -> Embed]
        UI_MODELS[3.3 LLM & Embedding Models Tab<br/>CHAT & EMBEDDING filters, Context limits, Pricing]
        SVC --> UI_PROV
        SVC --> UI_MODAL
        SVC --> UI_MODELS
    end

    subgraph Phase 4: Automated Testing & Security Audit
        TEST_API[4.1 Admin AI API Unit & Integration Tests<br/>test/test_admin_ai_management.py]
        TEST_LEAK[4.2 Secret Masking & Zero-Leak Audit Tests]
        TEST_GATING[4.3 Zero-Trust Gating Enforcement Tests]
        API_PROV --> TEST_API
        API_TEST --> TEST_API
        TEST_API --> TEST_LEAK
        TEST_API --> TEST_GATING
    end

    subgraph Phase 5: Build & Platform Regression
        BUILD[5.1 Frontend Build Compilation<br/>cd web && npm run build]
        REG[5.2 Full Platform Test Suite<br/>45+ tests including AI Gateway & Ads]
        UI_PROV --> BUILD
        UI_MODELS --> BUILD
        TEST_API --> REG
    end
```

---

## 2. Implementation Phases & Vertical Slices

### Phase 1: Backend Admin API Modernization (`api/apps/ai_management_app.py`)
**Objective:** Connect the Admin API directly to the centralized `CredentialResolver` and `AIGateway`, strictly enforcing superuser authorization and zero secret leakage.

> [!NOTE]
> **Database Schema Status:** All required database models (`AIProvider` / `ai_provider`, `AIModel` / `ai_model`, `TenantLLM` / `tenant_llm`) **already exist** in [`api/db/db_models.py`](file:///D:/ragflow/swipies_25/ragflow/api/db/db_models.py#L1521). **Zero new database migrations are required** for this feature.

- **Task 1.1: Provider Management Endpoints (`/v1/admin/ai/providers`)**
  - Modernize `admin_get_providers`: call `credential_resolver.list_providers_for_admin()` to return full provider records including `masked_api_key`, `is_active`, `is_configured`, `is_live_tested`, `is_available_in_admin`, `verification_status`, and `status_reason`.
  - Modernize `admin_save_provider`: call `credential_resolver.save_provider_credentials(provider, api_key, base_url, is_active)`. Automatically preserve existing secrets if incoming key is masked or empty.
  - Modernize `admin_delete_provider`: call `credential_resolver.delete_provider_credentials(provider)`.
  - Enforce `require_superuser()` on all routes.

- **Task 1.2: Dual Testing Endpoints (`/test-connection` & `/verify-live`)**
  - Modernize `POST /v1/admin/ai/providers/<provider>/test-connection`: call `credential_resolver.test_provider_connection(provider, api_key, base_url)`. Returns `{ success, status_code, latency_ms, message }`. Does *not* alter verification gating status.
  - Implement `POST /v1/admin/ai/providers/<provider>/verify-live`: call `credential_resolver.verify_provider_full_cycle(provider, api_key, base_url, persist_verification=True)`. Returns multi-stage benchmark results (`chat_non_streaming`, `chat_streaming`, `embeddings`), unlocks provider in DB upon 100% success.

- **Task 1.3: Model Registry Endpoints (`/v1/admin/ai/models`)**
  - Modernize `admin_get_models`: filter and return platform models strictly bounded to **`CHAT`** and **`EMBEDDING`** model types. Include provider linkage (`provider`), context limits (`max_tokens`), token pricing (`input_token_price`, `output_token_price`), and status (`enabled`).
  - Modernize `admin_save_model`: validate model type (reject unsupported types like RERANK/VISION in this phase), persist in `AIModelService` / `TenantLLM`.
  - Modernize `admin_delete_model`: soft or hard delete model from catalog.

---

### Phase 2: Frontend Service Layer & TypeScript Contracts
**Objective:** Implement strict TypeScript types and clean HTTP API client methods in `web/src/services/ai-management-service.ts`.

- **Task 2.1: TypeScript DTOs & Interfaces**
  - Update `AIProviderItem` to include `is_live_tested: boolean`, `is_available_in_admin: boolean`, `verification_status: 'verified' | 'requires_live_test'`, `status_reason?: string`, `supported_models: string[]`.
  - Define `ConnectionTestResult` and `LiveVerificationResult` (with `stages: { chat_non_streaming, chat_streaming, embeddings }`).
  - Update `AIModelItem` restricting `model_type` to `'CHAT' | 'EMBEDDING'`.

- **Task 2.2: API Service Methods**
  - Implement `getAdminProviders(onlyAvailable?: boolean): Promise<ResponseData<AIProviderItem[]>>`.
  - Implement `saveAdminProvider(payload: SaveProviderRequest): Promise<ResponseData<AIProviderItem>>`.
  - Implement `deleteAdminProvider(provider: string): Promise<ResponseData<boolean>>`.
  - Implement `testAdminProviderConnection(provider: string, data?: object): Promise<ResponseData<ConnectionTestResult>>`.
  - Implement `verifyAdminProviderLive(provider: string, data?: object): Promise<ResponseData<LiveVerificationResult>>`.
  - Implement `getAdminModels(provider?: string, modelType?: string): Promise<ResponseData<AIModelItem[]>>`.
  - Implement `saveAdminModel(payload: SaveModelRequest): Promise<ResponseData<AIModelItem>>`.
  - Implement `deleteAdminModel(modelId: string): Promise<ResponseData<boolean>>`.

---

### Phase 3: Frontend UI Components (`web/src/pages/admin/ai-management/`)
**Objective:** Deliver an intuitive, responsive React UI in the Admin Panel with clear visual badges, dual test buttons, and a live progress modal.

> [!IMPORTANT]
> **Non-Destructive UI Refactoring Scope:** [`web/src/pages/admin/ai-management/index.tsx`](file:///D:/ragflow/swipies_25/ragflow/web/src/pages/admin/ai-management/index.tsx) is an existing 1,742-line production dashboard with 6 tabs (`instance`, `models`, `subscriptions`, `byok`, `analytics`, `audit`). Phase 3 performs a **targeted refactoring of only the Providers section (under `instance`) and Models tab (`models`)**, connecting them to the new `CredentialResolver` backend while keeping all other tabs (`subscriptions`, `byok`, `analytics`, `audit`) **100% intact and operational**.

- **Task 3.1: "AI Management → Providers" Tab**
  - Table / Card view displaying all supported providers (OpenAI, DeepSeek, Anthropic, Gemini, etc.).
  - Status Badges:
    - 🟢 **`Verified`**: Provider has passed live tests; active for platform routing.
    - 🟡 **`Requires Live Test`**: Configured but awaiting outbound live verification.
    - ⚪ **`Unconfigured`**: No API key provided.
    - 🔴 **`Connection Error`**: Last ping or test failed.
  - Action Controls:
    - **`[Edit Credentials]`**: Modal with masked key display, URL override, active toggle.
    - **`[Test Connection]`**: Triggers fast 1-token ping with instant toast feedback showing latency in ms.
    - **`[⚡ Live Verify]`**: Prominently displayed for `requires_live_test` providers (Anthropic, Gemini). Opens live benchmark modal.
    - **`[Toggle Active]`**: Instant toggle switch.

- **Task 3.2: Live Verification Modal Component**
  - Step-by-step progress indicator executing:
    - 1. *Non-Streaming Chat Completion* (latency & token check).
    - 2. *Streaming Token Flow* (delta chunk reception check).
    - 3. *Embedding Vector Generation* (for Gemini/OpenAI).
  - Clear success feedback upon passing all benchmarks; automatic badge refresh on the main table.

- **Task 3.3: "AI Management → LLM Models" Tab**
  - Filter bar: Filter by Provider (`All`, `OpenAI`, `DeepSeek`, `Anthropic`, `Gemini`) and Type (`All`, `CHAT`, `EMBEDDING`).
  - Table columns: Model Identifier, Provider, Type, Context / Max Tokens, Token Pricing (In/Out), Active Switch, Actions (`Edit`, `Delete`).
  - Add/Edit Model Dialog: Form with validation, provider selection dropdown, model name input, and parameter inputs.

---

### Phase 4: Automated Testing & Security Audit
**Objective:** Guarantee complete coverage of all admin API endpoints, zero-leak credential protection, and superuser RBAC.

- **Task 4.1: Admin AI API Unit & Integration Tests (`test/test_admin_ai_management.py`)**
  - Test 1: `GET /v1/admin/ai/providers` returns all metadata with masked keys.
  - Test 2: `POST /v1/admin/ai/providers` saves and partially updates keys without secret erasure.
  - Test 3: `POST /v1/admin/ai/providers/<p>/test-connection` executes fast ping and redacts any errors.
  - Test 4: `POST /v1/admin/ai/providers/<p>/verify-live` runs full multi-stage benchmark and persists verification in DB.
  - Test 5: `GET /v1/admin/ai/models` and `POST /v1/admin/ai/models` strictly validate `CHAT` and `EMBEDDING` types.
  - Test 6: Non-superuser requests receive `RetCode.AUTHENTICATION_ERROR` / HTTP 401.

- **Task 4.2: Zero-Leak Security Audit**
  - Verify that no API response from `/v1/admin/ai/*` contains raw `sk-*` or Bearer tokens.

---

### Phase 5: Verification, Build Integrity & Platform Regression
**Objective:** Validate that the entire platform builds and passes all tests with zero regressions.

- **Task 5.1: Backend Test Suite Execution**
  - Run `test_admin_ai_management.py` + `test_ai_gateway.py` + `test_swipies_ads_system.py` + `test_e2e_ads_and_billing.py` (all tests must pass cleanly).
- **Task 5.2: Frontend Production Build**
  - Run `npm run build` in `web/` to confirm zero TypeScript compilation errors or broken imports.

---

## 3. Risks & Mitigation Matrix

| Risk / Edge Case | Likelihood | Impact | Mitigation Strategy |
|---|---|---|---|
| **Accidental Overwrite of Secret Key on Edit** | High | Critical | `CredentialResolver.save_provider_credentials` checks if incoming key contains `...` or is empty, and automatically preserves the existing raw secret. |
| **Timeout during Live Verification** | Medium | Medium | `verify_provider_full_cycle` sets explicit per-step timeouts (10s) and catches network exceptions with automated `SecretRedactor` sanitization. |
| **Model Type Ambiguity (Rerank/Vision)** | Low | High | API rejects model creation requests with types other than `CHAT` and `EMBEDDING` with a clear validation error. |
| **Non-Admin Access to Provider Credentials** | Low | Critical | `require_superuser()` is enforced at the top of every endpoint handler in `ai_management_app.py`. |

---

## 4. Verification Checkpoints & Commands

```powershell
# 1. Run Admin AI Management Unit & Security Tests
python -m unittest test/test_admin_ai_management.py

# 2. Run Full Platform Regression Suite
python -m unittest test/test_admin_ai_management.py test/test_ai_gateway.py test/test_swipies_ads_system.py test/test_e2e_ads_and_billing.py

# 3. Verify Frontend Compilation & TypeScript Check
cd D:\ragflow\swipies_25\ragflow\web ; npm run build

# 4. Check Git Status
git status
```

---

## 5. Definition of Done (DoD)

- [ ] All endpoints in `api/apps/ai_management_app.py` modernized and wired to `CredentialResolver`.
- [ ] TypeScript interfaces and service methods implemented in `web/src/services/ai-management-service.ts`.
- [ ] React UI tabs (`Providers` and `LLM Models`) fully functional with status badges and live verification modal.
- [ ] Untested providers (`Anthropic`, `Gemini`) badged as `requires_live_test` and unlocked only upon running `Live Verification`.
- [ ] Models management strictly restricted to `CHAT` and `EMBEDDING` types.
- [ ] Automated test suite `test/test_admin_ai_management.py` created and passing.
- [ ] All platform regression tests passing (`OK`, 0 errors).
- [ ] Frontend `npm run build` succeeds cleanly.
