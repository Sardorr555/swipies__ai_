#
#  Copyright 2026 The InfiniFlow & Swipies AI Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
import hashlib
import logging
from typing import AsyncIterator, Dict, List, Optional, Type, Union

from common.ai_gateway.base import AIProvider
from common.ai_gateway.credential_resolver import CredentialResolver
from common.ai_gateway.errors import AIGatewayError, ModelNotFoundError, SecretRedactor
from common.ai_gateway.providers.openai_provider import OpenAIProvider
from common.ai_gateway.providers.deepseek_provider import DeepSeekProvider
from common.ai_gateway.providers.anthropic_provider import AnthropicProvider
from common.ai_gateway.providers.gemini_provider import GeminiProvider
from common.ai_gateway.types import (
    ProviderType,
    GatewayChatRequest,
    GatewayChatResponse,
    GatewayStreamChunk,
    GatewayEmbeddingRequest,
    GatewayEmbeddingResponse,
    GatewayMessage,
)

logger = logging.getLogger("ai_gateway")


class AIGateway:
    """
    Central AI Gateway for all platform AI interactions (chat completion, streaming, embeddings, and token counting).
    
    Guarantees:
    1. Single Unified Entry Point: All requests route through this gateway without direct vendor bypass.
    2. Dynamic Provider Registry: New providers register dynamically via register_provider().
    3. Seamless Credential Resolution: Injects credentials from CredentialResolver securely in-memory.
    4. Zero-Leak Error Sanitization: All logs and exceptions are passed through SecretRedactor.
    """

    _registry: Dict[ProviderType, Type[AIProvider]] = {}

    @classmethod
    def register_provider(cls, provider_type: ProviderType, provider_cls: Type[AIProvider]) -> None:
        """Registers a concrete AIProvider class with the Gateway."""
        cls._registry[provider_type] = provider_cls
        logger.info(f"[AI Gateway] Registered provider adapter: {provider_type.value}")

    def __init__(self):
        self._instances: Dict[str, AIProvider] = {}
        self._bootstrap_default_providers()

    def _bootstrap_default_providers(self) -> None:
        """Initializes default built-in providers."""
        self.register_provider(ProviderType.OPENAI, OpenAIProvider)
        self.register_provider(ProviderType.DEEPSEEK, DeepSeekProvider)
        self.register_provider(ProviderType.ANTHROPIC, AnthropicProvider)
        self.register_provider(ProviderType.GEMINI, GeminiProvider)

    def resolve_provider_for_model(self, model_name: str) -> ProviderType:
        """
        Infers the target provider based on model name prefix/family
        if not explicitly specified in the request.
        """
        m_lower = (model_name or "").lower()
        if any(p in m_lower for p in ["gpt-", "text-embedding-3", "o1", "o3", "davinci", "curie"]):
            return ProviderType.OPENAI
        elif any(p in m_lower for p in ["deepseek", "deepseek-chat", "deepseek-reasoner", "r1", "v3"]):
            return ProviderType.DEEPSEEK
        elif any(p in m_lower for p in ["claude-", "anthropic"]):
            return ProviderType.ANTHROPIC
        elif any(p in m_lower for p in ["gemini-", "text-embedding-004"]):
            return ProviderType.GEMINI
        elif "ollama" in m_lower:
            return ProviderType.OLLAMA
        return ProviderType.OPENAI

    def get_provider(
        self,
        provider_type: Optional[Union[ProviderType, str]] = None,
        tenant_id: Optional[str] = None,
        model: Optional[str] = None,
    ) -> AIProvider:
        """
        Resolves, instantiates, and caches an AIProvider adapter with secure backend credentials.
        """
        # Determine provider enum
        if provider_type is None and model:
            p_enum = self.resolve_provider_for_model(model)
        elif isinstance(provider_type, ProviderType):
            p_enum = provider_type
        elif isinstance(provider_type, str):
            try:
                p_enum = ProviderType(provider_type.lower())
            except ValueError:
                p_enum = ProviderType.OPENAI
        else:
            p_enum = ProviderType.OPENAI

        if p_enum not in self._registry:
            raise ModelNotFoundError(f"No provider adapter registered for '{p_enum.value}'")

        # Resolve credentials securely via CredentialResolver
        api_key, base_url = CredentialResolver.resolve(p_enum, tenant_id=tenant_id, model=model)
        
        # Instance cache key based on provider, tenant, and key hash
        key_hash = hashlib.md5((api_key or "").encode()).hexdigest()[:8]
        cache_key = f"{p_enum.value}:{tenant_id or 'system'}:{key_hash}"

        if cache_key not in self._instances:
            prov_cls = self._registry[p_enum]
            self._instances[cache_key] = prov_cls(api_key=api_key, base_url=base_url)

        return self._instances[cache_key]

    async def chat(
        self,
        request: GatewayChatRequest,
        tenant_id: Optional[str] = None,
    ) -> GatewayChatResponse:
        """
        Executes a standard non-streaming chat completion through the appropriate AI provider.
        """
        provider = self.get_provider(request.provider, tenant_id=tenant_id, model=request.model)
        try:
            return await provider.chat_complete(request)
        except Exception as e:
            self._handle_and_sanitize_exception(e, request.model)

    async def stream_chat(
        self,
        request: GatewayChatRequest,
        tenant_id: Optional[str] = None,
    ) -> AsyncIterator[GatewayStreamChunk]:
        """
        Executes a streaming chat completion yielding GatewayStreamChunk chunks in real-time.
        """
        provider = self.get_provider(request.provider, tenant_id=tenant_id, model=request.model)
        try:
            async for chunk in provider.chat_stream(request):
                yield chunk
        except Exception as e:
            self._handle_and_sanitize_exception(e, request.model)

    async def embeddings(
        self,
        request: GatewayEmbeddingRequest,
        tenant_id: Optional[str] = None,
    ) -> GatewayEmbeddingResponse:
        """
        Computes dense vector embeddings for input texts through the appropriate provider.
        """
        provider = self.get_provider(request.provider, tenant_id=tenant_id, model=request.model)
        try:
            return await provider.embed(request)
        except Exception as e:
            self._handle_and_sanitize_exception(e, request.model)

    def count_tokens(
        self,
        text_or_messages: Union[str, List[GatewayMessage]],
        model: str,
        provider: Optional[Union[ProviderType, str]] = None,
    ) -> int:
        """
        Accurately calculates token count for prompt text or message lists.
        """
        p = self.get_provider(provider, model=model)
        return p.count_tokens(text_or_messages, model)

    def _handle_and_sanitize_exception(self, exc: Exception, model_name: str) -> None:
        """
        Intercepts exceptions, guarantees secret redaction, and re-raises typed AIGatewayError.
        """
        sanitized_err = SecretRedactor.redact(str(exc))
        logger.error(f"[AI Gateway Exception] (model: {model_name}) {sanitized_err}")
        if isinstance(exc, AIGatewayError):
            raise exc
        raise AIGatewayError(f"AI Gateway request failed for model '{model_name}': {sanitized_err}", original_error=exc)


# Global Singleton AI Gateway Instance
ai_gateway = AIGateway()
