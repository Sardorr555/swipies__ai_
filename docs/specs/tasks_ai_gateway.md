# Atomic Implementation Tasks: AI Gateway (Centralized AI Core)

**Specification Reference:** [`docs/specs/spec_ai_gateway.md`](file:///D:/ragflow/swipies_25/ragflow/docs/specs/spec_ai_gateway.md)  
**Plan Reference:** [`docs/specs/plan_ai_gateway.md`](file:///D:/ragflow/swipies_25/ragflow/docs/specs/plan_ai_gateway.md)  
**Status:** Ready for Execution  
**Target Branch:** `test`  

---

## Task Dependency & Execution Matrix

```
[TASK-01] Types & Data Models ──────┐
                                   ├──► [TASK-03] Base Interface ──► [TASK-04] OpenAI Provider ──┐
[TASK-02] Error Hierarchy & Redactor┘                            ──► [TASK-05] DeepSeek Provider─┴─► [TASK-07] AI Gateway Engine
                                                                                                      ▲
[TASK-06] Secure Backend Credential Resolver ────────────────────────────────────────────────────────┘
                                                                                                      │
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┤
▼                                                     ▼                                               ▼
[TASK-08] Chat & SSE Streaming Migration     [TASK-09] Embeddings Migration          [TASK-10] Ads AI Copy Migration
└─────────────────────────────────────────────────────┬───────────────────────────────────────────────┘
                                                      ▼
                                       [TASK-11] Gateway Unit Tests
                                                      ▼
                                   [TASK-12] Security Audit & Platform Regression
```

---

## Phase 1: Core Foundation & Contracts

### - [x] TASK-01: Implement Gateway Data Models & Schemas
- **Description:** Create dataclasses and enums defining the unified request/response protocol for all AI interactions.
- **Acceptance Criteria:**
  - `ProviderType` (`openai`, `deepseek`, `anthropic`, `gemini`, `ollama`, `custom`) and `ModelCapability` enums defined.
  - `TokenUsage` frozen dataclass with `prompt_tokens`, `completion_tokens`, `total_tokens`.
  - `GatewayMessage`, `GatewayChatRequest`, `GatewayChatResponse` data structures defined with strict type hints.
  - `GatewayStreamChunk` with `delta_content`, `delta_reasoning`, `tool_calls_chunk`, `usage`.
  - `GatewayEmbeddingRequest` and `GatewayEmbeddingResponse` defined.
- **Verification:**
  ```powershell
  python -c "from common.ai_gateway.types import GatewayChatRequest, GatewayChatResponse, GatewayStreamChunk, TokenUsage; print('TASK-01 OK')"
  ```
- **Files:**
  - `common/ai_gateway/__init__.py`
  - `common/ai_gateway/types.py`

---

### - [x] TASK-02: Implement Error Hierarchy & Secret Redactor
- **Description:** Implement custom exception classes and a high-performance regex redactor that sanitizes API keys and tokens from all error messages and logs.
- **Acceptance Criteria:**
  - `AIGatewayError` (base), `ProviderAuthError`, `RateLimitError`, `QuotaExceededError`, `ModelNotFoundError`, `ProviderConnectionError` implemented.
  - `SecretRedactor.redact(text)` scrubs `sk-[a-zA-Z0-9_\-]{20,}` and `Bearer [token]` strings, replacing with `[REDACTED_API_KEY]`.
  - Zero plaintext key remnants remain in exception string representations.
- **Verification:**
  ```powershell
  python -c "from common.ai_gateway.errors import SecretRedactor, ProviderAuthError; assert '[REDACTED_API_KEY]' in SecretRedactor.redact('Error: sk-proj-1234567890abcdef12345678 failed'); print('TASK-02 OK')"
  ```
- **Files:**
  - `common/ai_gateway/errors.py`

---

### - [x] TASK-03: Implement Abstract Provider Base Interface
- **Description:** Create the abstract base class `AIProvider(ABC)` enforcing the standardized implementation contract for all current and future LLM providers.
- **Acceptance Criteria:**
  - Abstract property `provider_type`.
  - Abstract async method `chat_complete(request: GatewayChatRequest) -> GatewayChatResponse`.
  - Abstract async method `chat_stream(request: GatewayChatRequest) -> AsyncIterator[GatewayStreamChunk]`.
  - Abstract async method `embed(request: GatewayEmbeddingRequest) -> GatewayEmbeddingResponse`.
  - Abstract method `count_tokens(text_or_messages: Union[str, List[GatewayMessage]], model: str) -> int`.
  - Protected error-redaction wrapper `_redact_error_context(exc: Exception) -> Exception`.
- **Verification:**
  ```powershell
  python -c "from common.ai_gateway.base import AIProvider; print('TASK-03 OK')"
  ```
- **Files:**
  - `common/ai_gateway/base.py`

---

## Phase 2: Concrete Provider Adapters

### - [x] TASK-04: Implement OpenAI Provider Adapter
- **Description:** Implement `OpenAIProvider` inheriting from `AIProvider`, utilizing `openai.AsyncOpenAI` for chat completion, streaming, and embeddings.
- **Acceptance Criteria:**
  - Instantiates `AsyncOpenAI` client with internal backend credentials.
  - `chat_complete` maps messages, temperature, tools, response formats, and returns `GatewayChatResponse`.
  - `chat_stream` yields `GatewayStreamChunk` asynchronously with zero chunk buffering.
  - `embed` handles batch text embedding with `text-embedding-3-small` / `text-embedding-3-large`.
  - Captures usage metadata (`prompt_tokens`, `completion_tokens`, `total_tokens`).
- **Verification:**
  ```powershell
  python -c "from common.ai_gateway.providers.openai_provider import OpenAIProvider; print('TASK-04 OK')"
  ```
- **Files:**
  - `common/ai_gateway/providers/__init__.py`
  - `common/ai_gateway/providers/openai_provider.py`

---

### - [x] TASK-05: Implement DeepSeek Provider Adapter
- **Description:** Implement `DeepSeekProvider` supporting standard chat completion and reasoning stream extraction (`deepseek-reasoner`).
- **Acceptance Criteria:**
  - Points to `https://api.deepseek.com/v1` with `deepseek-chat` and `deepseek-reasoner` support.
  - Accurately captures thought tokens (`delta.reasoning_content`) and routes them to `GatewayStreamChunk.delta_reasoning`.
  - Preserves clean final text output in `GatewayStreamChunk.delta_content`.
  - Token counting tailored for DeepSeek tokenization.
- **Verification:**
  ```powershell
  python -c "from common.ai_gateway.providers.deepseek_provider import DeepSeekProvider; print('TASK-05 OK')"
  ```
- **Files:**
  - `common/ai_gateway/providers/deepseek_provider.py`

---

### - [x] TASK-05b: Implement Anthropic Provider Adapter
- **Description:** Implement `AnthropicProvider` for Claude 3.5 Sonnet, Claude 3.5 Haiku, and Claude 3.7 Sonnet models.
- **Acceptance Criteria:**
  - Separates system instructions from user/assistant messages.
  - Streaming via `AsyncAnthropic` client with thought/reasoning token capture.
  - Token usage mapped to `TokenUsage` metadata.
- **Files:**
  - `common/ai_gateway/providers/anthropic_provider.py`

---

### - [x] TASK-05c: Implement Google Gemini Provider Adapter
- **Description:** Implement `GeminiProvider` for Gemini 2.0 Flash, Gemini 1.5 Pro, and `text-embedding-004`.
- **Acceptance Criteria:**
  - OpenAI-compatible endpoint integration (`https://generativelanguage.googleapis.com/v1beta/openai/`).
  - Streaming, function calling tools, and vector embeddings supported.
- **Files:**
  - `common/ai_gateway/providers/gemini_provider.py`

---

## Phase 3: Central Gateway Engine & Security Core

### - [x] TASK-06: Implement Secure Backend Credential Resolver
- **Description:** Create internal credential resolver that retrieves API keys and base URLs strictly from server environments (`OPENAI_API_KEY`, `DEEPSEEK_API_KEY`) or encrypted database tables (`TenantLLM`).
- **Acceptance Criteria:**
  - `CredentialResolver.resolve(provider_type, tenant_id)` resolves in-memory credentials.
  - Full Admin Panel CRUD suite: `list_providers_for_admin()`, `get_provider_for_admin()`, `save_provider_credentials()`, `delete_provider_credentials()`, `test_provider_connection()`.
  - Credentials are never exposed outside the backend gateway layer (safe auto-masking `mask_api_key`).
  - Fallback logic to system-level defaults if tenant custom keys are not configured.
- **Verification:**
  ```powershell
  python -c "from common.ai_gateway.credential_resolver import CredentialResolver; print('TASK-06 OK')"
  ```
- **Files:**
  - `common/ai_gateway/credential_resolver.py`

---

### - [x] TASK-07: Implement Central AI Gateway Service
- **Description:** Implement the `AIGateway` dispatcher singleton managing provider registries, lifecycle caching, and centralized error redaction.
- **Acceptance Criteria:**
  - `register_provider(provider_type, provider_cls)` dynamically registers provider classes.
  - Automatically registers `OpenAIProvider`, `DeepSeekProvider`, `AnthropicProvider`, and `GeminiProvider` on initialization.
  - `chat()`, `stream_chat()`, and `embeddings()` dispatch to the appropriate adapter.
  - Central exception interceptor sanitizes all error logs and re-raised exceptions via `SecretRedactor`.
  - Export global singleton `ai_gateway = AIGateway()`.
- **Verification:**
  ```powershell
  python -c "from common.ai_gateway.gateway import AIGateway, ai_gateway; print('TASK-07 OK')"
  ```
- **Files:**
  - `common/ai_gateway/gateway.py`

---

## Phase 4: Platform Call-Site Migration (Zero-Bypass Integration)

### - [x] TASK-08: Migrate Chat & SSE Streaming to AI Gateway
- **Description:** Refactor chat completion and streaming pipelines in `rag/llm/chat_model.py` and `api/apps/restful_apis/chat_api.py` to route through `AIGateway().stream_chat()` and `ai_gateway.chat()` with fallback flag `AI_GATEWAY_CHAT_ENABLED`.
- **Acceptance Criteria:**
  - Chat streaming uses `AIGateway` while preserving existing conversation IDs, session context memory, and SSE wire protocol.
  - Support for `<think>` tag formatting in streaming output remains fully intact.
  - Zero-downtime fallback to legacy client if flag is disabled or unexpected error occurs.
- **Verification:**
  ```powershell
  python -m unittest test/test_swipies_ads_system.py
  ```
- **Files:**
  - `rag/llm/chat_model.py`

---

### - [x] TASK-09: Migrate Embedding Invocations to AI Gateway
- **Description:** Route document and query embedding requests through `AIGateway().embeddings()`.
- **Acceptance Criteria:**
  - `rag/llm/embedding_model.py` delegates embedding generation to `ai_gateway.embeddings()`.
  - Vector dimensions and batch processing maintain exact parity with existing knowledge base indices.
  - Zero-downtime fallback to legacy client via `AI_GATEWAY_EMBED_ENABLED`.
- **Verification:**
  ```powershell
  python -m unittest test/test_e2e_ads_and_billing.py
  ```
- **Files:**
  - `rag/llm/embedding_model.py`

---

### - [x] TASK-10: Migrate Swipies Ads AI Copywriter & Creative Generators to AI Gateway
- **Description:** Update AI copy generation, dynamic creative optimization, and semantic campaign embeddings in `api/db/services/ad_engine_service.py` to invoke `ai_gateway.chat()` and `ai_gateway.embeddings()`.
- **Acceptance Criteria:**
  - `AdEngineService.generate_copy` and `generate_ad_creative` call `ai_gateway.chat()` without direct vendor imports.
  - `AdEngineService.compute_semantic_embedding` routes targeting/retrieval embeddings through `ai_gateway.embeddings()`.
  - `AdCreativeStudioService.generate_creative_matrix` dynamically utilizes `AdEngineService.generate_copy` for multi-format copy generation.
  - Recommended bids, keywords, and copy variations generate correctly with zero-leak error redaction and fallback.
- **Verification:**
  ```powershell
  python -m unittest test/test_swipies_ads_system.py
  ```
- **Files:**
  - `api/db/services/ad_engine_service.py`
  - `api/apps/ad_app.py`

---

## Phase 5: Verification, Security Audit & Build Integrity

### - [x] TASK-11: Implement Comprehensive AI Gateway Unit Tests
- **Description:** Build automated unit test suite covering mock OpenAI/DeepSeek calls, streaming async generators, thought extraction, and secret redaction.
- **Acceptance Criteria (Mandatory Test Cases):**
  - **Case 1 (Non-Streaming Full Cycle):** `Base.async_chat` routes through `AIGateway.chat` -> `OpenAIProvider.chat_complete`, returning exact response and verifying `last_usage` token counts without triggering fallback.
  - **Case 2 (Streaming Full Cycle & Usage):** `Base.async_chat_streamly` routes through `AIGateway.stream_chat` -> `OpenAIProvider.chat_stream`, yielding text chunks in real-time and asserting `last_usage` (`prompt_tokens`, `completion_tokens`, `total_tokens`) at stream conclusion.
  - **Case 3 (Thought Token Extraction):** `DeepSeekProvider` stream correctly parses `delta.reasoning_content` -> `<think>...</think>` wrapper and delivers clean final answer in `delta_content`.
  - **Case 4 (Zero-Leak Secret Redaction):** Simulated 401/429/500 vendor exceptions containing fake API keys (`sk-proj-test1234567890abcdef1234`) and `Bearer` tokens are 100% sanitized to `[REDACTED_API_KEY]` / `[REDACTED_TOKEN]`.
  - **Case 5 (Credential Resolver Admin CRUD & Masking):** Saving, listing, masking (`sk-proj...1234`), updating with partial mask, and deleting provider credentials.
  - **Case 6 (Embeddings & Math Parity):** Verifying 100% vector array mathematical parity between legacy and Gateway embeddings paths, index-based response reordering, and single-query `encode_queries`.
- **Verification:**
  ```powershell
  python -m unittest test/test_ai_gateway.py
  ```
- **Files:**
  - `test/test_ai_gateway.py`
  - `common/ai_gateway/credential_resolver.py`
  - `test/test_ai_gateway.py`

---

### - [ ] TASK-12: Full Platform Regression & Frontend Build Verification
- **Description:** Execute the entire platform test suite and frontend compilation to guarantee zero regressions.
- **Acceptance Criteria:**
  - All 33 existing tests in `test_swipies_ads_system.py` and `test_e2e_ads_and_billing.py` pass cleanly (`OK`).
  - New `test_ai_gateway.py` passes cleanly (`OK`).
  - Frontend `npm run build` completes in `web/` with zero errors.
  - Changes committed and pushed to `swipies_ai test`.
- **Verification:**
  ```powershell
  python -m unittest test/test_ai_gateway.py test/test_swipies_ads_system.py test/test_e2e_ads_and_billing.py
  cd web ; npm run build
  git status
  ```

---

## Follow-up & Provider Live Testing

### - [ ] TASK-FOLLOWUP-LIVE-TEST-ANTHROPIC-GEMINI: Live Outbound API Testing for Anthropic & Gemini
- **Description:** Execute live outbound API calls with valid paid vendor API keys to `api.anthropic.com` and `generativelanguage.googleapis.com` before enabling Anthropic and Gemini as active providers in Admin Panel.
- **Prerequisite:** Provision valid `ANTHROPIC_API_KEY` and `GEMINI_API_KEY` in environment or database.
- **Note:** Current Phase 2 implementations were verified by unit contract & structural AST checks only. Live billing tests are blocked until live credentials are provided.

