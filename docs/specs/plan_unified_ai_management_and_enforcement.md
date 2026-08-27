# Unified Technical Implementation Plan: Admin AI Management & Subscription Enforcement

**Specifications Reference:**
- [`docs/specs/spec_admin_ai_management.md`](file:///D:/ragflow/swipies_25/ragflow/docs/specs/spec_admin_ai_management.md)
- [`docs/specs/spec_subscription_enforcement.md`](file:///D:/ragflow/swipies_25/ragflow/docs/specs/spec_subscription_enforcement.md)

**Status:** Draft / Ready for Review  
**Version:** 1.0.0  
**Target Branch:** `test`  
**Plan Key:** `plan_unified_ai_management_and_enforcement`  

---

## 1. Unified Architecture & Dependency Graph

```mermaid
graph TD
    subgraph Phase 1: Data Contracts & Typed Exceptions
        ERR[1.1 Typed Policy Exceptions<br/>AIGatewayPolicyError, ModelExcluded, GloballyDisabled, UserModelForbidden, SubscriptionModelNotAllowed, QuotaExceeded<br/>common/ai_gateway/errors.py]
        TYPES[1.2 Request DTO Extensions<br/>tenant_id & user_id in GatewayChatRequest & GatewayEmbeddingRequest<br/>common/ai_gateway/types.py]
    end

    subgraph Phase 2: 5-Tier Pre-Flight Gate in AI Gateway
        GATE[2.1 5-Tier Policy Gate<br/>AIPolicyManager.check_model_access_extended<br/>common/ai_gateway/gateway.py]
        HOOKS[2.2 Entry Hooks in chat, stream_chat, embeddings<br/>Immediate fail-fast rejection before provider network dispatch]
        ERR --> GATE
        TYPES --> GATE
        GATE --> HOOKS
    end

    subgraph Phase 3: Runtime Propagation & Safe Fallback Immunity
        PROP[3.1 Context Propagation in ChatModel & LLMBundle<br/>rag/llm/chat_model.py & api/db/services/llm_service.py]
        IMMUNE[3.2 Safe Fallback Immunity<br/>except AIGatewayPolicyError: raise<br/>Zero fallback to legacy client on policy rejections]
        HOOKS --> PROP
        PROP --> IMMUNE
    end

    subgraph Phase 4: Backend Admin API Modernization
        API_PROV[4.1 Provider Endpoints & CredentialResolver Wiring<br/>GET /providers, POST /providers, DELETE /providers/api-key]
        API_TEST[4.2 Dual Testing Endpoints<br/>POST /test-connection & POST /verify-live]
        API_MODELS[4.3 Model Governance Endpoints<br/>GET /models, POST /models, PUT /user-model-overrides]
        API_AUDIT[4.4 Security Audit Logging<br/>PROVIDER_KEY_REPLACE & PROVIDER_KEY_WIPE in AIAuditLogService]
        AUTH[4.5 Superuser RBAC Guard<br/>require_superuser() in ai_management_app.py]
        AUTH --> API_PROV
        AUTH --> API_TEST
        AUTH --> API_MODELS
        API_PROV --> API_AUDIT
    end

    subgraph Phase 5: Frontend Service Layer & DTOs
        TS_TYPES[5.1 TypeScript Interfaces & DTOs<br/>AIProviderItem, ModelItem, LiveVerificationResult, UserModelOverride]
        SVC[5.2 Admin AI Service Methods<br/>web/src/services/ai-management-service.ts]
        TS_TYPES --> SVC
    end

    subgraph Phase 6: React Admin UI Modernization
        UI_PROV[6.1 Providers Management Tab<br/>Status Badges, Masked Keys, Test Ping, Live Verify]
        UI_MODAL[6.2 Live Verification Modal<br/>3-Stage Benchmark Progress: Chat -> Stream -> Embed]
        UI_MODELS[6.3 LLM Models Governance Tab<br/>Exclusion Toggles, Global Kill-Switch, Per-User Overrides Modal]
        SVC --> UI_PROV
        SVC --> UI_MODAL
        SVC --> UI_MODELS
    end

    subgraph Phase 7: Automated Testing & Security Audit
        TEST_ENFORCE[7.1 Subscription Enforcement Tests<br/>test/test_subscription_enforcement.py (8 scenarios)]
        TEST_ADMIN[7.2 Admin AI Management Tests<br/>test/test_admin_ai_management.py (CRUD, Wipe, RBAC)]
        IMMUNE --> TEST_ENFORCE
        API_MODELS --> TEST_ADMIN
    end

    subgraph Phase 8: Platform Regression & Build Integrity
        REG[8.1 Full Test Suite Execution<br/>50+ tests: Gateway, Ads, Admin AI, Subscription Enforcement]
        BUILD[8.2 Frontend Build Compilation<br/>cd web && npm run build]
        TEST_ENFORCE --> REG
        TEST_ADMIN --> REG
        UI_MODELS --> BUILD
    end
```

---

## 2. Implementation Phases & Vertical Slices

### Phase 1: Data Contracts & Typed Policy Exceptions
**Objective:** Define the strict error hierarchy and ensure `GatewayChatRequest` carries tenant and user context.

- **Task 1.1: Implement Typed Policy Exceptions in [`common/ai_gateway/errors.py`](file:///D:/ragflow/swipies_25/ragflow/common/ai_gateway/errors.py)**
  - Base class: `AIGatewayPolicyError(AIGatewayError)` with `status_code: int = 403`, `error_code: str = "POLICY_ERROR"`.
  - Level 1: `ModelExcludedFromProviderError(AIGatewayPolicyError)` (403, `PROVIDER_EXCLUDED`).
  - Level 2: `ModelGloballyDisabledError(AIGatewayPolicyError)` (403, `GLOBALLY_DISABLED`).
  - Level 3: `UserModelForbiddenError(AIGatewayPolicyError)` (403, `USER_RESTRICTED`).
  - Level 4: `SubscriptionModelNotAllowedError(AIGatewayPolicyError)` (403, `PLAN_RESTRICTED`).
  - Level 5: `SubscriptionTokenLimitReachedError(AIGatewayPolicyError)` (429, `QUOTA_EXCEEDED`).

- **Task 1.2: Extend Gateway DTOs in [`common/ai_gateway/types.py`](file:///D:/ragflow/swipies_25/ragflow/common/ai_gateway/types.py)**
  - Add `tenant_id: Optional[str] = None` and `user_id: Optional[str] = None` to `GatewayChatRequest` and `GatewayEmbeddingRequest`.

---

### Phase 2: 5-Tier Pre-Flight Gate in AI Gateway (`common/ai_gateway/gateway.py` & `api/db/services/ai_policy_service.py`)
**Objective:** Establish the mandatory 5-tier pre-flight gate inside `AIGateway` before any outbound vendor connection is made.

- **Task 2.1: Enhance `AIPolicyManager.check_model_access_extended`**
  - Implement 5-tier evaluation in exact order of precedence:
    - 1. Provider Model Exclusion check (DB persistent exclusion list in `AIProvider.extra["excluded_models"]`).
    - 2. Global Model Kill-Switch check (`AIModel.enabled == False` or provider `is_configured == False`).
    - 3. Per-User Model Override check (`UserModelOverride` / `UserTokenLimit.extra["model_overrides"]`).
    - 4. Subscription Plan Tier `allowed_models` check.
    - 5. Daily and Monthly Token Quota checks.
  - Return `(allowed: bool, message: str, status_code: int, error_code: str)`.

- **Task 2.2: Implement `_enforce_subscription_policy` in `AIGateway`**
  - Hook at the entry of `AIGateway.chat()`, `stream_chat()`, and `embeddings()`.
  - On policy failure, instantiate and raise the corresponding typed `AIGatewayPolicyError` subclass before any provider connection is initiated.
  - Bypass for internal system calls (`tenant_id is None` or `tenant_id == "system"`) and superusers (`is_super == True`).

---

### Phase 3: Runtime Propagation & Safe Fallback Immunity (`rag/llm/chat_model.py`)
**Objective:** Pass tenant/user context from `ChatModel` down to `AIGateway` and ensure Safe Fallback never bypasses policy rejections.

- **Task 3.1: Pass `tenant_id` and `user_id` to `GatewayChatRequest`**
  - In `Base._async_chat_streamly` and `Base._async_chat`, extract `tenant_id` from `getattr(self, "tenant_id", None)` and pass it into `GatewayChatRequest`.

- **Task 3.2: Implement Safe Fallback Bypass Immunity**
  - In `Base._async_chat_streamly` and `Base._async_chat`:
    ```python
    except AIGatewayPolicyError:
        raise  # Re-raise policy errors immediately without falling back
    except Exception as gw_err:
        # Only infrastructure failures trigger fallback to legacy client
        logging.warning(f"[AI Gateway] Fallback: {SecretRedactor.redact(str(gw_err))}")
    ```

- **Task 3.3: Context Propagation in `LLMBundle`**
  - Ensure `LLMBundle` assigns `self.tenant_id` to `self.mdl`.

---

### Phase 4: Backend Admin API Modernization (`api/apps/ai_management_app.py`)
**Objective:** Wire Admin API directly to `CredentialResolver`, implement provider key wipe with cascade model deactivation, and enforce security audit logging.

- **Task 4.1: Provider Management & Key Wipe (`/v1/admin/ai/providers`)**
  - Modernize `GET /providers`: return full provider records with `masked_api_key`, `is_active`, `is_configured`, `is_live_tested`, `is_available_in_admin`, `verification_status`.
  - Modernize `POST /providers`: save/update credentials via `CredentialResolver.save_provider_credentials`. Handle partial updates and key replacement cleanly.
  - Implement `DELETE /providers/<p>/api-key`: completely wipe API key, reset provider to `is_configured=false`, `is_active=false`, and cascade deactivation to associated models in `ai_model` (`status="unconfigured_provider"`, `enabled=false`).
  - Log `PROVIDER_KEY_REPLACE` and `PROVIDER_KEY_WIPE` in `AIAuditLogService` with masked secrets.
  - Enforce `require_superuser()` on all routes.

- **Task 4.2: Dual Testing Endpoints (`/test-connection` & `/verify-live`)**
  - `POST /providers/<p>/test-connection`: lightweight 1-token health check via `CredentialResolver.test_provider_connection()`.
  - `POST /providers/<p>/verify-live`: 3-stage live benchmark (Chat -> Stream -> Embeddings) via `CredentialResolver.verify_provider_full_cycle()`. Unlocks provider in DB upon 100% pass.

- **Task 4.3: Model Governance & Per-User Overrides (`/v1/admin/ai/models`)**
  - Modernize `GET /models` and `POST /models`: bounded strictly to `CHAT` and `EMBEDDING` types.
  - Implement `PUT /v1/admin/ai/models/<id>/toggle-global`: toggle global model kill-switch (`enabled=True/False`).
  - Implement `PUT /v1/admin/ai/providers/<p>/exclude-model`: add/remove persistent model exclusions from provider discovery.
  - Implement `GET/PUT /v1/admin/ai/user-model-overrides`: manage granular per-user `ALLOW` / `DENY` model overrides.

---

### Phase 5: Frontend Service Layer & TypeScript Contracts (`web/src/services/ai-management-service.ts`)
**Objective:** Implement strict TypeScript types and clean HTTP API client methods.

- **Task 5.1: Update TypeScript DTOs**
  - Define `AIProviderItem` (with `is_live_tested`, `is_available_in_admin`, `verification_status`, `status_reason`).
  - Define `ConnectionTestResult` and `LiveVerificationResult` (3 stages).
  - Define `UserModelOverride` (`user_id`, `model_id`, `access_type: 'ALLOW' | 'DENY'`, `enabled`).

- **Task 5.2: Implement Service Methods**
  - Add `wipeAdminProviderKey(provider: string)`
  - Add `testAdminProviderConnection(provider: string, data?: object)`
  - Add `verifyAdminProviderLive(provider: string, data?: object)`
  - Add `toggleGlobalModel(modelId: string, enabled: boolean)`
  - Add `setUserModelOverride(userId: string, modelId: string, accessType: 'ALLOW' | 'DENY', enabled: boolean)`

---

### Phase 6: React Admin UI Modernization (`web/src/pages/admin/ai-management/`)
**Objective:** Deliver an intuitive, non-destructive UI refactoring in the Admin Panel.

- **Task 6.1: "AI Management → Providers" Tab Refactoring**
  - Provider table/cards with status badges: 🟢 `Verified`, 🟡 `Requires Live Test`, ⚪ `Unconfigured`, 🔴 `Error`.
  - Actions: `[Edit Credentials]`, `[Test Connection]`, `[⚡ Live Verify]`, `[Wipe API Key]`, `[Toggle Active]`.

- **Task 6.2: Live Verification Modal Component**
  - Real-time 3-stage progress indicator:
    - 1. Non-Streaming Chat Completion
    - 2. Streaming Token Flow
    - 3. Dense Vector Embeddings
  - Automatic table refresh upon passing benchmarks.

- **Task 6.3: "AI Management → LLM Models" Tab Refactoring**
  - Table with status badges: 🟢 `Active`, 🔴 `Globally Disabled`, ⚪ `Provider Unconfigured`, 🚫 `Excluded from Provider`.
  - Action toggles: Global Kill-Switch, Exclude from Provider.
  - Add Per-User Model Overrides sub-dialog/tab.

---

### Phase 7: Automated Testing & Security Audit
**Objective:** Validate all acceptance criteria across both specifications with 100% automated test coverage.

- **Task 7.1: Subscription Enforcement Tests (`test/test_subscription_enforcement.py`)**
  - Test 1: Level 1 — Provider Model Exclusion rejection (HTTP 403 `ModelExcludedFromProviderError`).
  - Test 2: Level 2 — Global Model Kill-Switch rejection (HTTP 403 `ModelGloballyDisabledError`).
  - Test 3: Level 2 — Unconfigured Provider Cascade rejection (HTTP 403).
  - Test 4: Level 3 — Per-User Explicit `DENY` rejection (HTTP 403 `UserModelForbiddenError`).
  - Test 5: Level 3 — Per-User Explicit `ALLOW` bypasses Level 4 (HTTP 200).
  - Test 6: Level 3 — Per-User Explicit `ALLOW` cannot bypass Level 1 or Level 2 (HTTP 403).
  - Test 7: Level 4 — Free plan model restriction (HTTP 403 `SubscriptionModelNotAllowedError`).
  - Test 8: Level 5 — Token quota exhaustion (HTTP 429 `SubscriptionTokenLimitReachedError`).
  - Test 9: Streaming request rejection before SSE handshake.
  - Test 10: Safe Fallback Immunity (asserts policy errors are re-raised without legacy fallback).
  - Test 11: Superuser and system health-check bypass.
  - Test 12: BYOK model quota exemption and Pro plan check.

- **Task 7.2: Admin AI Management Tests (`test/test_admin_ai_management.py`)**
  - Test 1: Superuser RBAC enforcement on all routes.
  - Test 2: Provider credential CRUD with masked key preservation.
  - Test 3: Provider API key wipe cascades deactivation to models.
  - Test 4: Key wipe and replace record audit logs in `AIAuditLogService`.
  - Test 5: Live verification unlocks Anthropic/Gemini and updates DB.

---

### Phase 8: Full Platform Regression & Frontend Build
**Objective:** Confirm platform integrity with zero build regressions.

- **Task 8.1: Run Full Test Suite**
  - Execute `test_subscription_enforcement.py` + `test_admin_ai_management.py` + `test_ai_gateway.py` + `test_swipies_ads_system.py` + `test_e2e_ads_and_billing.py`.
- **Task 8.2: Frontend Production Build**
  - Execute `cd web ; npm run build` (verify 0 TypeScript compilation errors).

---

## 3. Risks & Mitigation Matrix

| Risk / Edge Case | Likelihood | Impact | Mitigation Strategy |
|---|---|---|---|
| **Safe Fallback Bypasses Policy Block** | High | Critical | Explicit `except AIGatewayPolicyError: raise` block placed before generic `except Exception` in `chat_model.py`. |
| **Accidental Overwrite of Secret Key on Edit** | High | Critical | `CredentialResolver.save_provider_credentials` checks for masked `...` keys and preserves the existing stored secret. |
| **Unconfigured Provider Causes Late Runtime Errors** | Medium | High | Wiping a provider key immediately marks its models as `unconfigured_provider` so requests fail fast at Level 2. |
| **Per-User Override Overriding Global Kill-Switch** | Medium | High | Evaluation hierarchy is strictly ordered: Level 1 & Level 2 are checked before Level 3. |
| **Audit Log Plaintext Secret Leak** | Low | Critical | `AIAuditLogService` uses `sanitize_sensitive_dict` to automatically mask all secret fields. |

---

## 4. Verification Checkpoints & Commands

```powershell
# 1. Run Subscription Enforcement Test Suite
python -m unittest test/test_subscription_enforcement.py

# 2. Run Admin AI Management Test Suite
python -m unittest test/test_admin_ai_management.py

# 3. Run Full Platform Regression Suite
python -m unittest test/test_subscription_enforcement.py test/test_admin_ai_management.py test/test_ai_gateway.py test/test_swipies_ads_system.py test/test_e2e_ads_and_billing.py

# 4. Verify Frontend Compilation & Build
cd D:\ragflow\swipies_25\ragflow\web ; npm run build

# 5. Check Git Status
git status
```

---

## 5. Definition of Done (DoD)

- [ ] `common/ai_gateway/errors.py` includes all 6 typed policy exceptions inheriting from `AIGatewayPolicyError`.
- [ ] `AIGateway` implements 5-tier pre-flight evaluation gate in `chat()`, `stream_chat()`, and `embeddings()`.
- [ ] `rag/llm/chat_model.py` implements Safe Fallback Immunity (`except AIGatewayPolicyError: raise`).
- [ ] `CredentialResolver` and `ai_management_app.py` support clean key replacement, key wipe with cascade model deactivation, and `AIAuditLogService` logging.
- [ ] Admin Panel UI tabs (`Providers` and `LLM Models`) refactored with status badges, live verification modal, kill-switch toggles, and per-user overrides.
- [ ] Automated test suites `test_subscription_enforcement.py` and `test_admin_ai_management.py` created and passing.
- [ ] All platform regression tests passing (`OK`, 0 errors).
- [ ] Frontend `npm run build` succeeds cleanly.
