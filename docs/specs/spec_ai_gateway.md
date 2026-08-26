# Spec: AI Gateway — Unified Central Entry Point for Platform AI Requests

**Document Status:** Ready for Review  
**Version:** 1.0.0  
**Feature:** AI Gateway (Core LLM & Embedding Centralization)  
**Author:** AI Architecture Team / Antigravity Assistant  
**Date:** 2026-08-26  

---

## 1. Executive Summary & Objective

### 1.1 Context & Problem Statement
Currently, platform interactions with Large Language Models (LLMs) and embedding providers are distributed across multiple service layers (e.g., chat services, RAG retrieval modules, AI copy generation in Swipies Ads, background jobs). This fragmentation introduces several key vulnerabilities and architectural bottlenecks:
- **Security & Secret Leakage Risks:** Direct instantiation of provider clients or exposing raw configuration objects creates risks of API keys leaking into frontend responses, debug logs, or error stack traces.
- **Logic Duplication:** Each caller independently configures timeouts, retry policies, streaming chunk parsing, and token consumption tracking.
- **Inability to Enforce Global Platform Governance:** Enforcing system-wide policies (e.g., global token quotas, model access whitelists, request rate limiting, content safety filters, and downstream dynamic advertising context injection) requires modifying dozens of disparate endpoints.
- **High Friction for Provider Onboarding:** Integrating a new provider (e.g., Anthropic, Google Gemini, local Ollama, vLLM) currently requires cross-cutting changes across chat controllers, assistant engines, and database services.

### 1.2 Objective
Build a unified, decoupled backend subsystem — **AI Gateway** — that acts as the single mandatory entry point for all platform AI requests (`chat completion`, `streaming chat`, `embeddings`, and `token counting`). 

**Key Guarantees:**
1. **Frontend Isolation:** The frontend never communicates directly with external LLM providers and never has access to provider API keys, credentials, or raw vendor payloads.
2. **Pluggable Provider Extensibility:** Provider-specific implementations are encapsulated behind a unified abstract interface (`AIProvider`). Adding new providers in the future requires zero changes to the Gateway core, chat handlers, or assistant workflows.
3. **Zero Credential Exposure:** API keys and credentials reside strictly in secure backend environments, sanitized before logging, and are never serialized into client responses (including error states).
4. **Preserved UX & Zero Regressions:** Existing SSE streaming, conversation IDs, chat histories, RAG retrieval flows, and assistant behaviors remain 100% backward compatible without performance degradation.

---

## 2. User Stories & Acceptance Criteria

### 2.1 User Stories
- **US-1 (End User):** *As a user chatting with an AI assistant or searching knowledge bases, I receive high-speed streaming responses and accurate embeddings without having access to or visibility into underlying provider API keys or infrastructure details.*
- **US-2 (Platform Developer):** *As a platform developer, I can onboard a new AI provider (e.g., Anthropic Claude, Google Gemini, Ollama) by implementing a single standardized `AIProvider` class and registering it in the Gateway factory, without modifying chat, RAG, or billing business logic.*
- **US-3 (Security & System Administrator):** *As an administrator, I am mathematically and architecturally assured that external API keys never appear in client-facing HTTP/SSE payloads, error logs, or frontend state objects.*

### 2.2 Key Acceptance Criteria (Gated Checklist)
- [ ] **AC-1 (Unified Interface):** A standardized backend abstract interface (`AIProvider`) is defined with concrete async/sync methods for:
  - `chat_complete(request: GatewayChatRequest) -> GatewayChatResponse`
  - `chat_stream(request: GatewayChatRequest) -> AsyncIterator[GatewayStreamChunk]`
  - `embed(request: GatewayEmbeddingRequest) -> GatewayEmbeddingResponse`
  - `count_tokens(text_or_messages: Union[str, List[dict]], model: str) -> int`
- [ ] **AC-2 (Standard Provider Implementations):** Minimum two standard providers are implemented and fully compliant with `AIProvider`:
  - `OpenAIProvider` (supporting `gpt-4o`, `gpt-4o-mini`, `o1`, `text-embedding-3-*`)
  - `DeepSeekProvider` (supporting `deepseek-chat`, `deepseek-reasoner` with `<think>` stream handling)
- [ ] **AC-3 (Complete Migration & Bypass Prevention):** All direct external API calls across chat completion, streaming, and embeddings are routed exclusively through `AIGateway`. No direct `openai.OpenAI` or vendor SDK invocations remain in application controllers.
- [ ] **AC-4 (Strict Secret Sanitization):** API keys and bearer tokens are strictly isolated in memory and backend storage. Error handlers, logger middleware, and response serializers have automated redaction (`[REDACTED_SECRET]`) ensuring credentials never leak.
- [ ] **AC-5 (Sanitized Client Payload):** Frontend API responses only contain sanitized result fields (`content`, `role`, `finish_reason`, `usage: {prompt_tokens, completion_tokens, total_tokens}`, `model_id`), with no vendor auth headers or raw client configs.
- [ ] **AC-6 (Seamless Streaming & Reasoning Support):** Server-Sent Events (SSE) and WebSocket chat streaming maintain sub-millisecond per-chunk forwarding latency and support deep reasoning thoughts (`<think>...</think>`).
- [ ] **AC-7 (Zero Downtime & State Preservation):** All existing conversation IDs, session context memory, document embedding caches, and prompt templates continue functioning seamlessly without data migration or breaking schema changes.

---

## 3. System Architecture & Workflow

```mermaid
flowchart TD
    subgraph Client Tier
        UI[Web / Mobile Frontend Client]
    end

    subgraph Platform Backend
        Controller[Chat / RAG / Assistant API Controllers]
        
        subgraph "AI Gateway (Central Core)"
            GW[AIGateway Service / Registry]
            Sanitizer[Security Sanitizer & Redactor]
            PolEng[Platform Policy Engine]
            
            subgraph "Provider Abstraction Layer"
                BaseProv["<<interface>>\nAIProvider"]
                OpenAIProv[OpenAIProvider]
                DeepSeekProv[DeepSeekProvider]
                FutureProv["Future Providers\n(Anthropic, Gemini, Ollama...)"]
            end
        end
        
        SecretStore[(Backend Secure Credential Store)]
    end

    subgraph External LLM Vendors
        ExtOpenAI[OpenAI Cloud API]
        ExtDeepSeek[DeepSeek API]
        ExtFuture[Other Cloud / Self-Hosted LLMs]
    end

    UI -->|1. User Prompt / Query (No Keys)| Controller
    Controller -->|2. GatewayChatRequest| GW
    GW -->|3. Validate & Authorize| PolEng
    GW -->|4. Resolve Credentials (Internal Only)| SecretStore
    GW -->|5. Forward to Provider Adapter| BaseProv
    
    BaseProv --> OpenAIProv
    BaseProv --> DeepSeekProv
    BaseProv --> FutureProv

    OpenAIProv -->|6a. HTTPS / SSE| ExtOpenAI
    DeepSeekProv -->|6b. HTTPS / SSE| ExtDeepSeek
    FutureProv -->|6c. API| ExtFuture

    ExtOpenAI -->|7. Raw Stream / Response| OpenAIProv
    ExtDeepSeek -->|7. Raw Stream / Response| DeepSeekProv
    
    OpenAIProv -->|8. Standardized GatewayStreamChunk| GW
    DeepSeekProv -->|8. Standardized GatewayStreamChunk| GW
    
    GW -->|9. Sanitize & Strip Secrets| Sanitizer
    Sanitizer -->|10. Stream / Response with Token Usage| Controller
    Controller -->|11. SSE Stream / JSON (Clean Result)| UI
```

---

## 4. Detailed Design & Interface Contracts

### 4.1 Data Models (`common/ai_gateway/types.py`)

```python
from dataclasses import dataclass, field
from enum import StrEnum
from typing import List, Dict, Any, Optional, AsyncIterator, Union

class ProviderType(StrEnum):
    OPENAI = "openai"
    DEEPSEEK = "deepseek"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    OLLAMA = "ollama"
    CUSTOM = "custom"

class ModelCapability(StrEnum):
    CHAT = "chat"
    STREAMING = "streaming"
    REASONING = "reasoning"
    EMBEDDING = "embedding"
    VISION = "vision"
    FUNCTION_CALLING = "function_calling"

@dataclass(frozen=True)
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

@dataclass
class GatewayMessage:
    role: str  # "system" | "user" | "assistant" | "tool"
    content: str
    name: Optional[str] = None
    tool_call_id: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None

@dataclass
class GatewayChatRequest:
    messages: List[GatewayMessage]
    model: str
    provider: Optional[ProviderType] = None
    temperature: float = 0.7
    top_p: float = 1.0
    max_tokens: Optional[int] = None
    stream: bool = False
    stop: Optional[List[str]] = None
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None
    response_format: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class GatewayChatResponse:
    id: str
    model: str
    provider: ProviderType
    content: str
    role: str = "assistant"
    finish_reason: Optional[str] = None
    reasoning_content: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    usage: TokenUsage = field(default_factory=TokenUsage)
    created_at: int = 0

@dataclass
class GatewayStreamChunk:
    id: str
    delta_content: str
    delta_reasoning: Optional[str] = None
    finish_reason: Optional[str] = None
    tool_calls_chunk: Optional[List[Dict[str, Any]]] = None
    usage: Optional[TokenUsage] = None

@dataclass
class GatewayEmbeddingRequest:
    input_texts: List[str]
    model: str
    provider: Optional[ProviderType] = None
    dimensions: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class GatewayEmbeddingResponse:
    model: str
    provider: ProviderType
    embeddings: List[List[float]]
    usage: TokenUsage = field(default_factory=TokenUsage)
```

---

### 4.2 Abstract Provider Interface (`common/ai_gateway/base.py`)

```python
from abc import ABC, abstractmethod
from typing import AsyncIterator, List, Union
from common.ai_gateway.types import (
    GatewayChatRequest,
    GatewayChatResponse,
    GatewayStreamChunk,
    GatewayEmbeddingRequest,
    GatewayEmbeddingResponse,
    ProviderType,
)

class AIProvider(ABC):
    """
    Standardized abstract base class for all AI model providers.
    Every LLM vendor integration MUST inherit from this class.
    """

    def __init__(self, api_key: str, base_url: Optional[str] = None, **kwargs):
        self._api_key = api_key
        self._base_url = base_url
        self._extra_config = kwargs

    @property
    @abstractmethod
    def provider_type(self) -> ProviderType:
        """Returns the enum identifier of the provider."""
        pass

    @abstractmethod
    async def chat_complete(self, request: GatewayChatRequest) -> GatewayChatResponse:
        """Execute a standard non-streaming chat completion."""
        pass

    @abstractmethod
    async def chat_stream(self, request: GatewayChatRequest) -> AsyncIterator[GatewayStreamChunk]:
        """Execute a streaming chat completion yielding GatewayStreamChunk chunks."""
        pass

    @abstractmethod
    async def embed(self, request: GatewayEmbeddingRequest) -> GatewayEmbeddingResponse:
        """Compute vector embeddings for a list of input texts."""
        pass

    @abstractmethod
    def count_tokens(self, text_or_messages: Union[str, List[GatewayMessage]], model: str) -> int:
        """Accurately count tokens for given text or chat messages."""
        pass
```

---

### 4.3 Central Gateway Manager (`common/ai_gateway/gateway.py`)

```python
import logging
from typing import Dict, Type, Optional, AsyncIterator
from common.ai_gateway.base import AIProvider
from common.ai_gateway.types import (
    GatewayChatRequest,
    GatewayChatResponse,
    GatewayStreamChunk,
    GatewayEmbeddingRequest,
    GatewayEmbeddingResponse,
    ProviderType,
)

logger = logging.getLogger("ai_gateway")

class AIGateway:
    """
    Singleton AI Gateway service responsible for:
    1. Provider registry and resolution
    2. Secure credential injection from server environment
    3. Input validation and policy enforcement
    4. Credential stripping & error sanitization
    """
    _providers: Dict[ProviderType, Type[AIProvider]] = {}

    @classmethod
    def register_provider(cls, ptype: ProviderType, provider_cls: Type[AIProvider]):
        cls._providers[ptype] = provider_cls
        logger.info(f"Registered AI Provider: {ptype.value}")

    def __init__(self):
        self._instances: Dict[str, AIProvider] = {}

    def get_provider(self, provider_type: ProviderType, tenant_id: Optional[str] = None) -> AIProvider:
        """Resolves or instantiates a provider with securely resolved backend credentials."""
        if provider_type not in self._providers:
            raise ValueError(f"Unsupported AI Provider: {provider_type}")
        
        # Resolve credentials strictly on backend from Tenant / System Secret Manager
        api_key, base_url = self._resolve_credentials(provider_type, tenant_id)
        cache_key = f"{provider_type.value}:{tenant_id or 'system'}"
        
        if cache_key not in self._instances:
            prov_cls = self._providers[provider_type]
            self._instances[cache_key] = prov_cls(api_key=api_key, base_url=base_url)
            
        return self._instances[cache_key]

    def _resolve_credentials(self, provider_type: ProviderType, tenant_id: Optional[str]) -> tuple[str, Optional[str]]:
        # Secure backend resolution: Environment variable or DB TenantLLM decrypted key
        # Never exposed to frontend or logged
        from api.db.services.llm_service import LLMService
        return LLMService.get_internal_credentials(provider_type, tenant_id)

    async def chat(self, request: GatewayChatRequest, tenant_id: Optional[str] = None) -> GatewayChatResponse:
        provider = self.get_provider(request.provider or ProviderType.OPENAI, tenant_id)
        try:
            return await provider.chat_complete(request)
        except Exception as e:
            self._handle_and_sanitize_exception(e)

    async def stream_chat(self, request: GatewayChatRequest, tenant_id: Optional[str] = None) -> AsyncIterator[GatewayStreamChunk]:
        provider = self.get_provider(request.provider or ProviderType.OPENAI, tenant_id)
        try:
            async for chunk in provider.chat_stream(request):
                yield chunk
        except Exception as e:
            self._handle_and_sanitize_exception(e)

    async def embeddings(self, request: GatewayEmbeddingRequest, tenant_id: Optional[str] = None) -> GatewayEmbeddingResponse:
        provider = self.get_provider(request.provider or ProviderType.OPENAI, tenant_id)
        try:
            return await provider.embed(request)
        except Exception as e:
            self._handle_and_sanitize_exception(e)

    def _handle_and_sanitize_exception(self, exc: Exception):
        err_msg = str(exc)
        # Automated redaction of potential API keys matching sk-*, bearer tokens, or query params
        sanitized_msg = self._redact_secrets(err_msg)
        logger.error(f"[AI Gateway Error] {sanitized_msg}")
        raise RuntimeError(f"AI Gateway request failed: {sanitized_msg}")

    @staticmethod
    def _redact_secrets(text: str) -> str:
        import re
        text = re.sub(r'sk-[a-zA-Z0-9_\-]{20,}', '[REDACTED_API_KEY]', text)
        text = re.sub(r'Bearer\s+[a-zA-Z0-9_\.\-]+', 'Bearer [REDACTED_TOKEN]', text, flags=re.IGNORECASE)
        return text
```

---

## 5. Concrete Providers Implementation Details

### 5.1 OpenAI Provider (`common/ai_gateway/providers/openai_provider.py`)
- **Backend Client:** Uses `AsyncOpenAI` client initialized with internal `api_key` and optional custom `base_url`.
- **Chat & Streaming:** Maps `GatewayChatRequest` messages and tools into OpenAI API format.
- **Reasoning Handling:** Captures `o1` / `o3` reasoning tokens and standard token usage metadata.
- **Embeddings:** Invokes `client.embeddings.create` with batching support for large document arrays.

### 5.2 DeepSeek Provider (`common/ai_gateway/providers/deepseek_provider.py`)
- **Backend Client:** Uses `AsyncOpenAI` client pointing to `https://api.deepseek.com/v1`.
- **Reasoning Stream Extraction:** Captures `delta.reasoning_content` from `deepseek-reasoner` responses and streams it in `GatewayStreamChunk.delta_reasoning`, cleanly separating thought tokens from final content.
- **Cost & Token Tracking:** Computes exact input/output tokens according to DeepSeek tokenizer rules.

---

## 6. Security, Isolation & Secret Governance

| Security Concern | Risk | AI Gateway Defense Mechanism |
|---|---|---|
| **Frontend Key Exposure** | Malicious users inspect network requests or state to steal API keys. | Keys are **strictly kept in backend memory/DB**. The frontend only talks to `/v1/chat` and `/v1/gateway/*` endpoints with user JWT tokens. |
| **Error Log Leakage** | API errors from OpenAI/DeepSeek containing auth header dumps written to disk. | Central `_redact_secrets` regex filter intercepts all gateway logs and exception messages before propagation. |
| **Response Payload Sanitization** | Accidental serialization of internal provider objects into client JSON. | Strict Dataclass return types (`GatewayChatResponse`, `GatewayStreamChunk`) that omit internal client references. |
| **Direct Bypass (Shadow AI Calls)** | New developers make direct `requests.post("https://api.openai.com")` in business logic. | Architectural rule + static code analysis (Linter/Lefthook) ensuring all LLM calls pass through `AIGateway`. |

---

## 7. Migration Plan & Call-Site Transformation

### Phase 1: Gateway Core & Provider Implementation
1. Create `common/ai_gateway/` package with interfaces, types, and core gateway logic.
2. Implement `OpenAIProvider` and `DeepSeekProvider`.
3. Write isolated unit tests with mock HTTP responses for sync, streaming, reasoning, and embeddings.

### Phase 2: Refactoring Internal Services to Gateway
1. **Chat & Assistant Services (`api/apps/sdk/chat.py`, `rag/llm/chat_model.py`):** Route standard completions and SSE generation through `AIGateway().stream_chat()`.
2. **Knowledge Base Embedding (`rag/llm/embedding_model.py`, `rag/nlp/search.py`):** Replace direct embedding calls with `AIGateway().embeddings()`.
3. **Swipies Ads AI Copywriter (`api/db/services/ad_engine_service.py`):** Update `generate_copy` and `generate_ad_creative` to invoke the Gateway.

### Phase 3: Verification & Regression Testing
1. Run full automated test suite (`test_swipies_ads_system.py`, `test_e2e_ads_and_billing.py`).
2. Run end-to-end chat conversation tests ensuring streaming tokens and `<think>` tags render smoothly.
3. Validate secret redaction by throwing artificial 401/429 provider errors and confirming zero credential leaks in logs and responses.

---

## 8. Testing Strategy & Verification Scenarios

| Test ID | Focus Area | Test Scenario | Expected Outcome |
|---|---|---|---|
| **TEST-GW-01** | Chat Completion | Send standard prompt via `OpenAIProvider` and `DeepSeekProvider` | Returns `GatewayChatResponse` with accurate content and `TokenUsage`. |
| **TEST-GW-02** | SSE Streaming | Stream 500-word response via `AIGateway.stream_chat` | Yields sequence of `GatewayStreamChunk` with sub-10ms chunk latency; stream terminates cleanly. |
| **TEST-GW-03** | DeepSeek Reasoning | Stream prompt using `deepseek-reasoner` | `delta_reasoning` chunks stream thoughts first, followed by `delta_content`. |
| **TEST-GW-04** | Vector Embeddings | Compute embeddings for 10 document chunks via `AIGateway.embeddings` | Returns correct dimension vectors (e.g. 1536 float array) and usage stats. |
| **TEST-GW-05** | Credential Scrubbing | Simulate failed vendor call returning `Invalid API Key sk-proj-1234567890abcdef12345678` | Exception thrown and logged contains `[REDACTED_API_KEY]` with zero plaintext key fragments. |
| **TEST-GW-06** | Backward Compatibility | Execute existing conversation tests | All conversation IDs, history preservation, and prompt templates remain unchanged and operational. |

---

## 9. Boundaries & Governance

### 9.1 Always Do:
- Always use `AIGateway` for any outbound LLM or embedding calls.
- Always use asynchronous generators (`AsyncIterator`) for streaming endpoints to preserve server concurrency.
- Always redact sensitive API keys and tokens in any log output.
- Always return standardized `TokenUsage` objects for billing and quota tracking.

### 9.2 Ask First:
- Modifying default model fallbacks or routing rules.
- Adding third-party network dependencies or changing HTTP client libraries.

### 9.3 Never Do:
- **NEVER** expose, return, or serialize raw API keys or provider bearer tokens to the frontend client.
- **NEVER** make direct, unmonitored HTTP requests to AI providers bypassing the `AIGateway`.
- **NEVER** break or alter existing database schemas or conversation history formats.

---

## 10. Out of Scope (Scheduled for Future Phases)
The following items are intentionally excluded from this foundational spec and will be delivered as separate follow-up features:
- Admin UI for dynamic provider and model management (CRUD, test connection buttons).
- Subscription-tier model binding, user token quotas, and automated usage billing tracking.
- Custom Bring-Your-Own-Key (BYOK) providers for PRO users.
- Advanced multi-provider automatic failover and load balancing.
