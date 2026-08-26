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

from anthropic import AsyncAnthropic
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

logger = logging.getLogger("ai_gateway.anthropic")


class AnthropicProvider(AIProvider):
    """
    Standardized Anthropic adapter for AI Gateway.
    Supports Claude 3.5 Sonnet, Claude 3.5 Haiku, Claude 3.7 Sonnet (with hybrid thinking) and Claude 3 Opus.
    """

    def __init__(self, api_key: str = "", base_url: Optional[str] = None, **kwargs):
        super().__init__(api_key=api_key, base_url=base_url, **kwargs)
        http_client = kwargs.get("http_client") or httpx.AsyncClient(timeout=kwargs.get("timeout", 60.0))
        self.client = AsyncAnthropic(
            api_key=self._api_key or "sk-ant-dummy",
            base_url=self._base_url or None,
            http_client=http_client,
        )

    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.ANTHROPIC

    def _extract_system_and_messages(self, messages: List[GatewayMessage]) -> tuple[str, List[Dict[str, Any]]]:
        system_prompt = ""
        formatted_messages = []
        for m in messages:
            if m.role == "system":
                system_prompt += (f"\n\n{m.content}" if system_prompt else m.content)
            else:
                role = "assistant" if m.role in ["assistant", "model"] else "user"
                formatted_messages.append({"role": role, "content": m.content})
        return system_prompt, formatted_messages

    async def chat_complete(self, request: GatewayChatRequest) -> GatewayChatResponse:
        try:
            system_prompt, messages = self._extract_system_and_messages(request.messages)
            payload: Dict[str, Any] = {
                "model": request.model,
                "messages": messages,
                "max_tokens": request.max_tokens or 4096,
                "temperature": request.temperature,
                "top_p": request.top_p,
            }
            if system_prompt:
                payload["system"] = system_prompt
            if request.stop:
                payload["stop_sequences"] = request.stop

            resp = await self.client.messages.create(**payload)
            
            content_text = ""
            reasoning_text = None
            for block in resp.content:
                if getattr(block, "type", "") == "text":
                    content_text += block.text
                elif getattr(block, "type", "") == "thinking":
                    reasoning_text = (reasoning_text or "") + getattr(block, "thinking", "")

            usage = TokenUsage(
                prompt_tokens=resp.usage.input_tokens or 0,
                completion_tokens=resp.usage.output_tokens or 0,
                total_tokens=(resp.usage.input_tokens or 0) + (resp.usage.output_tokens or 0),
            )

            return GatewayChatResponse(
                id=resp.id,
                model=resp.model,
                provider=self.provider_type,
                content=content_text,
                role=resp.role or "assistant",
                finish_reason=resp.stop_reason,
                reasoning_content=reasoning_text,
                usage=usage,
                created_at=int(time.time()),
            )
        except Exception as e:
            raise self._wrap_provider_exception(e)

    async def chat_stream(self, request: GatewayChatRequest) -> AsyncIterator[GatewayStreamChunk]:
        try:
            system_prompt, messages = self._extract_system_and_messages(request.messages)
            payload: Dict[str, Any] = {
                "model": request.model,
                "messages": messages,
                "max_tokens": request.max_tokens or 4096,
                "temperature": request.temperature,
                "top_p": request.top_p,
            }
            if system_prompt:
                payload["system"] = system_prompt
            if request.stop:
                payload["stop_sequences"] = request.stop

            async with self.client.messages.stream(**payload) as stream:
                async for text in stream.text_stream:
                    yield GatewayStreamChunk(
                        id="anthropic_stream_chunk",
                        delta_content=text,
                    )
                
                # Fetch final message usage at end of stream
                final_msg = await stream.get_final_message()
                if final_msg and final_msg.usage:
                    usage = TokenUsage(
                        prompt_tokens=final_msg.usage.input_tokens or 0,
                        completion_tokens=final_msg.usage.output_tokens or 0,
                        total_tokens=(final_msg.usage.input_tokens or 0) + (final_msg.usage.output_tokens or 0),
                    )
                    yield GatewayStreamChunk(
                        id=final_msg.id,
                        delta_content="",
                        finish_reason=final_msg.stop_reason,
                        usage=usage,
                    )
        except Exception as e:
            raise self._wrap_provider_exception(e)

    async def embed(self, request: GatewayEmbeddingRequest) -> GatewayEmbeddingResponse:
        # Anthropic does not provide native vector embedding API; raise standardized error or delegate
        raise NotImplementedError("Anthropic provider does not support vector embeddings directly. Use OpenAI or Gemini embeddings.")

    def count_tokens(self, text_or_messages: Union[str, List[GatewayMessage]], model: str) -> int:
        from common.token_utils import num_tokens_from_string
        if isinstance(text_or_messages, str):
            return num_tokens_from_string(text_or_messages)
        total = 0
        for m in text_or_messages:
            total += 4 + num_tokens_from_string(m.content)
        return total
