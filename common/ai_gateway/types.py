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
from dataclasses import dataclass, field, asdict
from enum import StrEnum
from typing import List, Dict, Any, Optional, Union


class ProviderType(StrEnum):
    """Enumeration of supported AI model providers."""
    OPENAI = "openai"
    DEEPSEEK = "deepseek"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    OLLAMA = "ollama"
    VLLM = "vllm"
    SILICONFLOW = "siliconflow"
    CUSTOM = "custom"


class ModelCapability(StrEnum):
    """Core capabilities supported by specific models."""
    CHAT = "chat"
    STREAMING = "streaming"
    REASONING = "reasoning"
    EMBEDDING = "embedding"
    VISION = "vision"
    FUNCTION_CALLING = "function_calling"


@dataclass(frozen=True)
class TokenUsage:
    """Standardized token consumption representation."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def to_dict(self) -> Dict[str, int]:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
        }


@dataclass
class GatewayMessage:
    """Single message item in a conversation history."""
    role: str  # "system" | "user" | "assistant" | "tool"
    content: str
    name: Optional[str] = None
    tool_call_id: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "role": self.role,
            "content": self.content,
        }
        if self.name is not None:
            d["name"] = self.name
        if self.tool_call_id is not None:
            d["tool_call_id"] = self.tool_call_id
        if self.tool_calls is not None:
            d["tool_calls"] = self.tool_calls
        return d


@dataclass
class GatewayChatRequest:
    """Unified request parameters for chat completion."""
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
    with_reasoning: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GatewayChatResponse:
    """Standardized response from a non-streaming chat completion."""
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

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "model": self.model,
            "provider": self.provider.value if isinstance(self.provider, ProviderType) else self.provider,
            "content": self.content,
            "role": self.role,
            "finish_reason": self.finish_reason,
            "reasoning_content": self.reasoning_content,
            "tool_calls": self.tool_calls,
            "usage": self.usage.to_dict(),
            "created_at": self.created_at,
        }


@dataclass
class GatewayStreamChunk:
    """Standardized single chunk yielded during chat streaming."""
    id: str
    delta_content: str = ""
    delta_reasoning: Optional[str] = None
    finish_reason: Optional[str] = None
    tool_calls_chunk: Optional[List[Dict[str, Any]]] = None
    usage: Optional[TokenUsage] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "id": self.id,
            "delta_content": self.delta_content,
        }
        if self.delta_reasoning is not None:
            d["delta_reasoning"] = self.delta_reasoning
        if self.finish_reason is not None:
            d["finish_reason"] = self.finish_reason
        if self.tool_calls_chunk is not None:
            d["tool_calls_chunk"] = self.tool_calls_chunk
        if self.usage is not None:
            d["usage"] = self.usage.to_dict()
        return d


@dataclass
class GatewayEmbeddingRequest:
    """Unified request parameters for vector embeddings calculation."""
    input_texts: List[str]
    model: str
    provider: Optional[ProviderType] = None
    dimensions: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GatewayEmbeddingResponse:
    """Standardized response from an embedding calculation."""
    model: str
    provider: ProviderType
    embeddings: List[List[float]]
    usage: TokenUsage = field(default_factory=TokenUsage)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model": self.model,
            "provider": self.provider.value if isinstance(self.provider, ProviderType) else self.provider,
            "embeddings_count": len(self.embeddings),
            "usage": self.usage.to_dict(),
        }
