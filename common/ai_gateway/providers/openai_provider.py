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
import time
import logging
from typing import AsyncIterator, Dict, List, Optional, Union, Any

from openai import AsyncOpenAI
import httpx

from common.ai_gateway.base import AIProvider
from common.ai_gateway.types import (
    ProviderType,
    GatewayChatRequest,
    GatewayChatResponse,
    GatewayStreamChunk,
    GatewayEmbeddingRequest,
    GatewayEmbeddingResponse,
    GatewayMessage,
    TokenUsage,
)

logger = logging.getLogger("ai_gateway.openai")


class OpenAIProvider(AIProvider):
    """
    Standardized OpenAI adapter for AI Gateway.
    Supports GPT-4o, GPT-4o-mini, o1, o3-mini, and text-embedding-3-* models.
    """

    def __init__(self, api_key: str = "", base_url: Optional[str] = None, **kwargs):
        super().__init__(api_key=api_key, base_url=base_url, **kwargs)
        http_client = kwargs.get("http_client") or httpx.AsyncClient(timeout=kwargs.get("timeout", 60.0))
        self.client = AsyncOpenAI(
            api_key=self._api_key or "sk-dummy",
            base_url=self._base_url or None,
            http_client=http_client,
        )

    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.OPENAI

    def _format_messages(self, messages: List[GatewayMessage]) -> List[Dict[str, Any]]:
        formatted = []
        for m in messages:
            msg_dict: Dict[str, Any] = {"role": m.role, "content": m.content}
            if m.name:
                msg_dict["name"] = m.name
            if m.tool_call_id:
                msg_dict["tool_call_id"] = m.tool_call_id
            if m.tool_calls:
                msg_dict["tool_calls"] = m.tool_calls
            formatted.append(msg_dict)
        return formatted

    async def chat_complete(self, request: GatewayChatRequest) -> GatewayChatResponse:
        try:
            payload: Dict[str, Any] = {
                "model": request.model,
                "messages": self._format_messages(request.messages),
                "temperature": request.temperature,
                "top_p": request.top_p,
            }
            if request.max_tokens is not None:
                payload["max_completion_tokens" if "o1" in request.model or "o3" in request.model else "max_tokens"] = request.max_tokens
            if request.stop:
                payload["stop"] = request.stop
            if request.tools:
                payload["tools"] = request.tools
            if request.tool_choice:
                payload["tool_choice"] = request.tool_choice
            if request.response_format:
                payload["response_format"] = request.response_format

            resp = await self.client.chat.completions.create(**payload)
            choice = resp.choices[0]
            msg = choice.message
            
            tool_calls = None
            if msg.tool_calls:
                tool_calls = [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in msg.tool_calls
                ]

            usage = TokenUsage()
            if resp.usage:
                usage = TokenUsage(
                    prompt_tokens=resp.usage.prompt_tokens or 0,
                    completion_tokens=resp.usage.completion_tokens or 0,
                    total_tokens=resp.usage.total_tokens or 0,
                )

            return GatewayChatResponse(
                id=resp.id,
                model=resp.model,
                provider=self.provider_type,
                content=msg.content or "",
                role=msg.role or "assistant",
                finish_reason=choice.finish_reason,
                reasoning_content=getattr(msg, "reasoning_content", None),
                tool_calls=tool_calls,
                usage=usage,
                created_at=resp.created or int(time.time()),
            )
        except Exception as e:
            raise self._wrap_provider_exception(e)

    async def chat_stream(self, request: GatewayChatRequest) -> AsyncIterator[GatewayStreamChunk]:
        try:
            payload: Dict[str, Any] = {
                "model": request.model,
                "messages": self._format_messages(request.messages),
                "temperature": request.temperature,
                "top_p": request.top_p,
                "stream": True,
                "stream_options": {"include_usage": True},
            }
            if request.max_tokens is not None:
                payload["max_completion_tokens" if "o1" in request.model or "o3" in request.model else "max_tokens"] = request.max_tokens
            if request.stop:
                payload["stop"] = request.stop
            if request.tools:
                payload["tools"] = request.tools
            if request.tool_choice:
                payload["tool_choice"] = request.tool_choice
            if request.response_format:
                payload["response_format"] = request.response_format

            stream_resp = await self.client.chat.completions.create(**payload)
            async for chunk in stream_resp:
                chunk_id = chunk.id or "stream_chunk"
                usage = None
                if getattr(chunk, "usage", None):
                    usage = TokenUsage(
                        prompt_tokens=chunk.usage.prompt_tokens or 0,
                        completion_tokens=chunk.usage.completion_tokens or 0,
                        total_tokens=chunk.usage.total_tokens or 0,
                    )

                if not chunk.choices:
                    if usage:
                        yield GatewayStreamChunk(id=chunk_id, delta_content="", usage=usage)
                    continue

                choice = chunk.choices[0]
                delta = choice.delta
                delta_content = delta.content or ""
                delta_reasoning = getattr(delta, "reasoning_content", None)
                finish_reason = choice.finish_reason

                tool_calls_chunk = None
                if getattr(delta, "tool_calls", None):
                    tool_calls_chunk = [
                        {
                            "index": tc.index,
                            "id": tc.id,
                            "type": tc.type,
                            "function": {
                                "name": getattr(tc.function, "name", None),
                                "arguments": getattr(tc.function, "arguments", None),
                            },
                        }
                        for tc in delta.tool_calls
                    ]

                yield GatewayStreamChunk(
                    id=chunk_id,
                    delta_content=delta_content,
                    delta_reasoning=delta_reasoning,
                    finish_reason=finish_reason,
                    tool_calls_chunk=tool_calls_chunk,
                    usage=usage,
                )
        except Exception as e:
            raise self._wrap_provider_exception(e)

    async def embed(self, request: GatewayEmbeddingRequest) -> GatewayEmbeddingResponse:
        try:
            kwargs: Dict[str, Any] = {
                "model": request.model,
                "input": request.input_texts,
                "encoding_format": "float",
            }
            if request.dimensions is not None:
                kwargs["dimensions"] = request.dimensions

            resp = await self.client.embeddings.create(**kwargs)
            sorted_data = sorted(resp.data, key=lambda d: getattr(d, "index", 0))
            embeddings = [item.embedding for item in sorted_data]
            
            usage = TokenUsage()
            if resp.usage:
                usage = TokenUsage(
                    prompt_tokens=resp.usage.prompt_tokens or 0,
                    total_tokens=resp.usage.total_tokens or 0,
                )

            return GatewayEmbeddingResponse(
                model=request.model,
                provider=self.provider_type,
                embeddings=embeddings,
                usage=usage,
            )
        except Exception as e:
            raise self._wrap_provider_exception(e)

    def count_tokens(self, text_or_messages: Union[str, List[GatewayMessage]], model: str) -> int:
        from common.token_utils import num_tokens_from_string
        if isinstance(text_or_messages, str):
            return num_tokens_from_string(text_or_messages)
        total = 0
        for m in text_or_messages:
            total += 4 + num_tokens_from_string(m.content)
            if m.name:
                total += num_tokens_from_string(m.name)
        total += 2
        return total
