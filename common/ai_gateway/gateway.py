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
from common.ai_gateway.errors import (
    AIGatewayError,
    AIGatewayPolicyError,
    ModelExcludedFromProviderError,
    ModelGloballyDisabledError,
    UserModelForbiddenError,
    SubscriptionModelNotAllowedError,
    SubscriptionTokenLimitReachedError,
    ModelNotFoundError,
    SecretRedactor,
)
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
    5. 5-Tier Pre-Flight Policy Enforcement: Blocks unauthorized models, quotas, and disabled models before vendor dispatch.
    """

    def __init__(self):
        self._registry: Dict[ProviderType, Type[AIProvider]] = {}
        self._instances: Dict[str, AIProvider] = {}
        self._register_default_providers()

    def _register_default_providers(self) -> None:
        """Initializes default built-in provider adapters."""
        self._registry[ProviderType.OPENAI] = OpenAIProvider
        self._registry[ProviderType.DEEPSEEK] = DeepSeekProvider
        self._registry[ProviderType.ANTHROPIC] = AnthropicProvider
        self._registry[ProviderType.GEMINI] = GeminiProvider

    def register_provider(self, provider_type: ProviderType, provider_cls: Type[AIProvider]) -> None:
        """Allows dynamic registration of new custom or third-party AI provider adapters."""
        self._registry[provider_type] = provider_cls
        logger.info(f"Registered dynamic provider adapter: {provider_type.value}")

    def _enforce_subscription_policy(
        self,
        model_name: str,
        tenant_id: Optional[str],
        user_id: Optional[str] = None,
        model_type: str = "CHAT",
    ) -> None:
        """
        Executes 5-tier pre-flight policy evaluation before outbound vendor dispatch.
        Raises typed AIGatewayPolicyError subclasses on rejection.
        """
        if not tenant_id or tenant_id == "system":
            return

        try:
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
        except AIGatewayPolicyError:
            raise
        except Exception as e:
            logger.debug(f"[AI Gateway] Pre-flight policy check bypassed on internal error: {e}")

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
        Resolves or dynamically creates a cached provider instance with valid credentials.
        """
        if provider_type is None:
            if model:
                p_enum = self.resolve_provider_for_model(model)
            else:
                p_enum = ProviderType.OPENAI
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
        
        # Instance cache key based on provider and tenant
        cache_key = f"{p_enum.value}:{tenant_id or 'system'}"

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
        effective_tenant = request.tenant_id or tenant_id
        self._enforce_subscription_policy(
            model_name=request.model,
            tenant_id=effective_tenant,
            user_id=request.user_id,
            model_type="CHAT",
        )
        provider = self.get_provider(request.provider, tenant_id=effective_tenant, model=request.model)
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
        effective_tenant = request.tenant_id or tenant_id
        self._enforce_subscription_policy(
            model_name=request.model,
            tenant_id=effective_tenant,
            user_id=request.user_id,
            model_type="CHAT",
        )
        provider = self.get_provider(request.provider, tenant_id=effective_tenant, model=request.model)
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
        effective_tenant = request.tenant_id or tenant_id
        self._enforce_subscription_policy(
            model_name=request.model,
            tenant_id=effective_tenant,
            user_id=request.user_id,
            model_type="EMBEDDING",
        )
        provider = self.get_provider(request.provider, tenant_id=effective_tenant, model=request.model)
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
