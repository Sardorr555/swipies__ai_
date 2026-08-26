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
from abc import ABC, abstractmethod
import logging
from typing import AsyncIterator, Dict, List, Optional, Union, Any

from common.ai_gateway.types import (
    GatewayChatRequest,
    GatewayChatResponse,
    GatewayStreamChunk,
    GatewayEmbeddingRequest,
    GatewayEmbeddingResponse,
    GatewayMessage,
    ProviderType,
)
from common.ai_gateway.errors import (
    AIGatewayError,
    ProviderAuthError,
    RateLimitError,
    QuotaExceededError,
    ModelNotFoundError,
    ProviderConnectionError,
    ContentFilterError,
    SecretRedactor,
)

logger = logging.getLogger("ai_gateway")


class AIProvider(ABC):
    """
    Standardized abstract base class for all AI model providers.
    Every LLM vendor integration (OpenAI, DeepSeek, Anthropic, Gemini, Ollama, etc.)
    MUST inherit from this class and implement its abstract methods.
    """

    def __init__(self, api_key: str = "", base_url: Optional[str] = None, **kwargs):
        self._api_key = api_key
        self._base_url = base_url
        self._extra_config: Dict[str, Any] = kwargs

    @property
    @abstractmethod
    def provider_type(self) -> ProviderType:
        """Returns the ProviderType enum identifying this provider."""
        pass

    @abstractmethod
    async def chat_complete(self, request: GatewayChatRequest) -> GatewayChatResponse:
        """
        Execute a standard (non-streaming) chat completion.
        Returns a sanitized GatewayChatResponse.
        """
        pass

    @abstractmethod
    async def chat_stream(self, request: GatewayChatRequest) -> AsyncIterator[GatewayStreamChunk]:
        """
        Execute a streaming chat completion yielding GatewayStreamChunk items.
        Must support real-time token yield with zero buffering.
        """
        pass

    @abstractmethod
    async def embed(self, request: GatewayEmbeddingRequest) -> GatewayEmbeddingResponse:
        """
        Compute dense vector embeddings for the provided input texts.
        Returns a standardized GatewayEmbeddingResponse.
        """
        pass

    @abstractmethod
    def count_tokens(self, text_or_messages: Union[str, List[GatewayMessage]], model: str) -> int:
        """
        Accurately count tokens for input text or list of GatewayMessage instances.
        """
        pass

    def _wrap_provider_exception(self, exc: Exception) -> AIGatewayError:
        """
        Translates vendor-specific exceptions into typed AIGatewayError instances
        with guaranteed secret sanitization.
        """
        err_str = str(exc)
        sanitized_msg = SecretRedactor.redact(err_str)
        err_lower = err_str.lower()

        if any(w in err_lower for w in ["401", "unauthorized", "invalid api key", "authentication", "permission"]):
            return ProviderAuthError(sanitized_msg, original_error=exc)
        elif any(w in err_lower for w in ["429", "rate limit", "tpm", "rpm", "too many requests"]):
            return RateLimitError(sanitized_msg, original_error=exc)
        elif any(w in err_lower for w in ["quota", "insufficient balance", "credit", "billing"]):
            return QuotaExceededError(sanitized_msg, original_error=exc)
        elif any(w in err_lower for w in ["404", "model not found", "does not exist"]):
            return ModelNotFoundError(sanitized_msg, original_error=exc)
        elif any(w in err_lower for w in ["content filter", "safety", "policy violation", "blocked"]):
            return ContentFilterError(sanitized_msg, original_error=exc)
        elif any(w in err_lower for w in ["timeout", "timed out", "connect", "connection refused", "503", "502", "504"]):
            return ProviderConnectionError(sanitized_msg, original_error=exc)

        return AIGatewayError(sanitized_msg, original_error=exc)
