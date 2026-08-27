# Specification: Subscription Policy, Model Governance & Token Limit Enforcement in AI Gateway

**Feature Key:** `subscription_enforcement`  
**Target Modules:** `common/ai_gateway/`, `rag/llm/`, `api/db/services/ai_policy_service.py`  
**Status:** Updated / Enhanced Specification  
**Specification Owner:** DeepMind Antigravity Pair  

---

## 1. Executive Summary & Problem Statement

### 1.1 Architectural Context & Gaps
The Swipies AI Platform requires fine-grained, real-time control over AI models and token consumption across commercial tiers (`FREE`, `PLUS`, `PRO`).

Currently:
1. **Runtime Enforcement Missing:** Inbound AI chat and streaming requests do not pass through a blocking policy gate before calling vendor providers, allowing unauthorized model invocation and unmetered token consumption.
2. **Provider Dynamic Discovery vs Exclusion:** While providers dynamically discover live models via API (Principle I), administrators cannot persistently exclude/hide specific models from that discovery list.
3. **Global Model Kill-Switch Missing:** Administrators lack an instant, platform-wide kill-switch to disable problematic, expensive, or deprecated models across all users (including Pro and BYOK).
4. **Granular Per-User Model Overrides Missing:** Administrators cannot grant explicit model allowances or impose explicit model prohibitions on specific users independently of their subscription tier.

### 1.2 Objective
Establish a **5-tier hierarchical pre-flight policy evaluation gate** inside [`AIGateway`](file:///D:/ragflow/swipies_25/ragflow/common/ai_gateway/gateway.py) that evaluates governance rules in strict order of precedence **before any network payload is dispatched to an AI provider**.

```mermaid
flowchart TD
    REQ["Inbound AI Request<br/>(Dialog / Canvas / SDK / API)"]
    REQ --> GW["AIGateway Entry<br/>(chat / stream_chat / embeddings)"]

    subgraph PreFlightGate [5-Tier Hierarchical Policy Gate (Zero Outbound Dispatch on Failure)]
        GW --> L1{"Level 1: Provider Exclusion?<br/>(Admin persistent blacklist)"}
        L1 -->|Yes| ERR_L1["Raise ModelExcludedFromProviderError<br/>(HTTP 403: Excluded from provider)"]
        
        L1 -->|No| L2{"Level 2: Global Kill-Switch?<br/>(Model disabled platform-wide)"}
        L2 -->|Yes| ERR_L2["Raise ModelGloballyDisabledError<br/>(HTTP 403: Globally disabled)"]
        
        L2 -->|No| L3{"Level 3: Per-User Override?<br/>(Explicit user allow / deny)"}
        L3 -->|Explicit DENY| ERR_L3["Raise UserModelForbiddenError<br/>(HTTP 403: User restricted)"]
        L3 -->|Explicit ALLOW| L5
        
        L3 -->|No User Override| L4{"Level 4: Plan allowed_models?<br/>(FREE / PLUS / PRO tier matrix)"}
        L4 -->|Not in Plan| ERR_L4["Raise SubscriptionModelNotAllowedError<br/>(HTTP 403: Plan upgrade required)"]
        
        L4 -->|In Plan| L5{"Level 5: Token Quota Exhausted?<br/>(Monthly / Daily limits)"}
        L5 -->|Quota Exceeded| ERR_L5["Raise SubscriptionTokenLimitReachedError<br/>(HTTP 429: Quota reached)"]
    end

    L5 -->|All Passed: OK (200)| DISPATCH["AIProvider Outbound Dispatch<br/>(OpenAI / DeepSeek / Anthropic / Gemini)"]
    DISPATCH --> STREAM["Real-time Completion / Stream"]
    STREAM --> RECORD["AIPolicyManager.record_token_usage()<br/>(Passive accounting)"]
```

---

## 2. User Stories & Value Proposition

1. **Provider List Hygiene:**
   - *As an administrator*, I want to exclude specific models (e.g. deprecated preview checkpoints) returned by a provider's dynamic API discovery, so they are permanently hidden from users without resetting upon discovery refreshes.
2. **Emergency Platform Protection:**
   - *As an administrator*, I want to instantly disable a model globally across all plans (including Pro and BYOK) if it experiences critical vendor outages or unexpected billing spikes.
3. **Granular User Customization:**
   - *As an administrator*, I want to explicitly allow a specific Free-tier beta tester to access `gpt-4o` without changing their entire subscription tier, or block a specific abusive user from a specific model.
4. **Commercial Integrity:**
   - *As a business*, we guarantee that Free users cannot access Pro models or exceed quotas, and that all policy blocks fail closed before generating vendor API costs.

---

## 3. Technical Architecture & Pre-Flight Policy Evaluation

### 3.1 5-Tier Evaluation Order of Precedence

When `AIGateway.chat()`, `stream_chat()`, or `embeddings()` is invoked, `AIPolicyManager.check_model_access()` evaluates the request through the following strict hierarchy:

| Level | Policy Check | Scope | Overridable by User Allow? | Rejection Exception | Status Code |
|---|---|---|---|---|---|
| **Level 1** | **Provider Model Exclusion** | Model excluded from provider discovery in DB | **NO** (Provider level trumps all) | `ModelExcludedFromProviderError` | 403 |
| **Level 2** | **Global Kill-Switch & Unconfigured Provider** | Model marked `enabled=False` or provider API key wiped | **NO** (Global disable trumps all) | `ModelGloballyDisabledError` | 403 |
| **Level 3** | **Per-User Model Override** | Explicit `DENY` or `ALLOW` for `user_id` | **N/A** (`DENY` blocks; `ALLOW` bypasses Level 4) | `UserModelForbiddenError` | 403 |
| **Level 4** | **Subscription Plan Tier** | Model present in plan `allowed_models` | **YES** (Overridden if Level 3 is `ALLOW`) | `SubscriptionModelNotAllowedError` | 403 |
| **Level 5** | **Token & Request Quotas** | `monthly_token_limit`, `daily_token_limit` | **NO** (Unless superuser or BYOK) | `SubscriptionTokenLimitReachedError` | 429 |

### 3.2 Pre-Flight Implementation in `AIGateway`

```python
def _enforce_subscription_policy(
    self,
    model_name: str,
    tenant_id: Optional[str],
    user_id: Optional[str] = None,
    model_type: str = "CHAT",
) -> None:
    """
    Executes 5-tier pre-flight governance and subscription checks before vendor dispatch.
    Raises typed AIGatewayPolicyError subclasses on rejection.
    """
    if not tenant_id:
        return  # Internal system or unauthenticated bypass

    from api.db.services.ai_policy_service import AIPolicyManager
    allowed, message, status_code, error_code = AIPolicyManager.check_model_access_extended(
        tenant_id=tenant_id,
        model_name=model_name,
        model_type=model_type,
        user_id=user_id or tenant_id,
    )

    if not allowed:
        if error_code == "PROVIDER_EXCLUDED":
            raise ModelExcludedFromProviderError(message)
        elif error_code == "GLOBALLY_DISABLED":
            raise ModelGloballyDisabledError(message)
        elif error_code == "USER_RESTRICTED":
            raise UserModelForbiddenError(message)
        elif error_code == "PLAN_RESTRICTED":
            raise SubscriptionModelNotAllowedError(message)
        elif error_code == "QUOTA_EXCEEDED" or status_code == 429:
            raise SubscriptionTokenLimitReachedError(message)
        else:
            raise AIGatewayPolicyError(message, status_code=status_code)
```

### 3.3 Dynamic Model Discovery Overlay (Principle I Preservation)

- Live discovery endpoints (`async_discover_live_provider_models`) dynamically query the provider's API.
- The returned live models are merged with persistent DB records in [`AIProvider.extra["excluded_models"]`](file:///D:/ragflow/swipies_25/ragflow/api/db/db_models.py#L1532) and [`AIModel`](file:///D:/ragflow/swipies_25/ragflow/api/db/db_models.py#L1568).
- Any model marked as excluded by an administrator remains persistently excluded across discovery refreshes.

### 3.4 Typed Exception Hierarchy & Safe Fallback Immunity

In [`common/ai_gateway/errors.py`](file:///D:/ragflow/swipies_25/ragflow/common/ai_gateway/errors.py):

```python
class AIGatewayPolicyError(AIGatewayError):
    """Base exception for policy, governance, and subscription rejections."""
    def __init__(self, message: str, status_code: int = 403, error_code: str = "POLICY_ERROR"):
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code


class ModelExcludedFromProviderError(AIGatewayPolicyError):
    """Level 1: Raised when model is persistently excluded from provider by admin."""
    def __init__(self, message: str):
        super().__init__(message, status_code=403, error_code="PROVIDER_EXCLUDED")


class ModelGloballyDisabledError(AIGatewayPolicyError):
    """Level 2: Raised when model is globally killed/disabled platform-wide."""
    def __init__(self, message: str):
        super().__init__(message, status_code=403, error_code="GLOBALLY_DISABLED")


class UserModelForbiddenError(AIGatewayPolicyError):
    """Level 3: Raised when access is explicitly forbidden for a specific user."""
    def __init__(self, message: str):
        super().__init__(message, status_code=403, error_code="USER_RESTRICTED")


class SubscriptionModelNotAllowedError(AIGatewayPolicyError):
    """Level 4: Raised when model is not permitted under the user's subscription plan."""
    def __init__(self, message: str):
        super().__init__(message, status_code=403, error_code="PLAN_RESTRICTED")


class SubscriptionTokenLimitReachedError(AIGatewayPolicyError):
    """Level 5: Raised when user/tenant has exhausted daily or monthly token quota."""
    def __init__(self, message: str):
        super().__init__(message, status_code=429, error_code="QUOTA_EXCEEDED")
```

> [!CRITICAL]
> **Safe Fallback Immunity Guarantee:**  
> In [`rag/llm/chat_model.py`](file:///D:/ragflow/swipies_25/ragflow/rag/llm/chat_model.py), all subclasses of `AIGatewayPolicyError` MUST be caught in a dedicated `except AIGatewayPolicyError: raise` block and re-raised immediately. Under no circumstances may a policy rejection trigger fallback to `self.async_client` or a legacy client.

---

## 4. Key Acceptance Criteria (AC)

### AC-1: Centralized 5-Tier Pre-Flight Gate
- **Given** an AI request initiated from any source (Chat Dialog, Canvas Agent, API SDK),
- **When** `AIGateway.chat()`, `stream_chat()`, or `embeddings()` is invoked,
- **Then** the request MUST evaluate all 5 policy tiers in strict order before initiating vendor network connections.

### AC-2: Dual Resolution Path Consistency
- **Given** a model resolved via either `TenantLLMService` or `TenantModelProvider`,
- **When** the execution reaches `AIGateway`,
- **Then** identical 5-tier policy checks apply with zero path-dependent bypasses.

### AC-3: Level 1 — Provider Model Exclusion Enforcement
- **Given** an administrator excludes a model from a provider via Admin Panel,
- **When** any user attempts to query that model through that provider,
- **Then** the request is rejected with HTTP 403 (`ModelExcludedFromProviderError`) with a descriptive message indicating provider exclusion.

### AC-4: Level 2 — Global Model Kill-Switch & Unconfigured Provider Cascade
- **Given** an administrator disables a model globally (`enabled=False`) OR wipes the API key of its provider (`is_configured=False`),
- **When** any user of any plan (including Pro and BYOK) attempts to query the model,
- **Then** the request is rejected immediately at Level 2 with HTTP 403 (`ModelGloballyDisabledError`) with a clear error message (e.g. `"Model '{model}' is currently unavailable because provider '{provider}' has no configured API key."`), without late runtime timeouts.

### AC-5: Level 3 — Granular Per-User Model Overrides
- **Given** an explicit per-user policy configured by `user_id`:
  - If set to `DENY`: The user is rejected with HTTP 403 (`UserModelForbiddenError`) even if their subscription plan allows the model.
  - If set to `ALLOW`: The user is permitted to use the model even if their subscription plan does not normally include it (e.g. Free user accessing a Plus model).
  - An explicit `ALLOW` **CANNOT** bypass Level 1 (Provider Exclusion) or Level 2 (Global Kill-Switch).

### AC-6: Level 4 — Subscription Plan Tier Gating (`allowed_models`)
- **Given** a user on the `FREE` plan attempting to query an unlisted model without a per-user allow override,
- **When** the request is submitted,
- **Then** `AIGateway` rejects the request with HTTP 403 (`SubscriptionModelNotAllowedError`) without consuming vendor tokens.

### AC-7: Level 5 — Token Quota & Request Limits
- **Given** a user whose monthly or daily token usage reaches or exceeds their quota,
- **When** a request is submitted,
- **Then** `AIGateway` rejects the request with HTTP 429 (`SubscriptionTokenLimitReachedError`).

### AC-8: Streaming & Non-Streaming Parity
- **Given** any policy rejection at Levels 1-5,
- **When** invoking `stream_chat()`,
- **Then** the stream fails immediately before emitting any token chunks or opening vendor SSE streams.

### AC-9: Safe Fallback Immunity Across All Policy Errors
- **Given** any `AIGatewayPolicyError` raised during execution,
- **When** caught in `chat_model.py`,
- **Then** the exception is immediately re-raised and bubbles up directly, never triggering fallback to legacy vendor clients.

### AC-10: BYOK Quota Exemption & Tier Check
- **Given** a user-configured BYOK model (`AIModel.is_custom == True`),
- **When** evaluated by the pre-flight gate,
- **Then** platform token quotas do not apply, but Pro/Enterprise plan requirement (`allow_byok == True`) and model ownership are strictly enforced.

### AC-11: Superuser & System Health-Check Bypass
- **Given** a request with `is_superuser == True` or `tenant_id="system"`,
- **When** evaluated by the pre-flight gate,
- **Then** the request bypasses plan restrictions and token quotas.

### AC-12: Zero-Downtime Real-Time Reactivity
- **Given** an administrator alters provider exclusions, global model status, per-user overrides, or plan quotas in Admin Panel,
- **When** a user submits a request 1 millisecond later,
- **Then** the new rules apply immediately without backend redeployment or service restarts.

### AC-13: Admin Panel UI for Model Governance
- **Given** the Admin Panel `AI Management → LLM Models` tab,
- **When** an administrator inspects models,
- **Then** the UI displays live provider models with toggles for "Excluded from Provider" and "Globally Disabled", alongside a Per-User Model Overrides interface.

---

## 5. Out of Scope Boundaries

1. Dynamic vendor failover / automatic routing to fallback models on rate limits.
2. BYOK user key encryption algorithms (already implemented).
3. Billing checkout / Stripe payment processing.

---

## 6. Definition of Done (DoD)

- [ ] `common/ai_gateway/errors.py` includes `AIGatewayPolicyError`, `ModelExcludedFromProviderError`, `ModelGloballyDisabledError`, `UserModelForbiddenError`, `SubscriptionModelNotAllowedError`, and `SubscriptionTokenLimitReachedError`.
- [ ] `AIPolicyManager` implements 5-tier evaluation logic with clear error codes.
- [ ] `AIGateway` pre-flight gate calls `_enforce_subscription_policy` in `chat()`, `stream_chat()`, and `embeddings()`.
- [ ] `rag/llm/chat_model.py` implements `except AIGatewayPolicyError: raise` in both streaming and non-streaming methods.
- [ ] Admin API & UI endpoints support:
  - Provider model exclusion management.
  - Global model enable/disable toggle.
  - Granular per-user model override CRUD (`GET/PUT /v1/admin/ai/user-model-overrides`).
- [ ] Unit and integration test suite (`test/test_subscription_enforcement.py`) passes all test scenarios with 100% coverage across Levels 1-5.
- [ ] Full platform regression suite passes (45+ tests, 0 failures).
- [ ] Frontend `npm run build` compiles with zero errors.
