#
#  Copyright 2026 The InfiniFlow Authors. All Rights Reserved.
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
import asyncio
import json
import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np
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
from common.ai_gateway.errors import (
    SecretRedactor,
    AIGatewayError,
    ProviderAuthError,
    RateLimitError,
)
from common.ai_gateway.gateway import ai_gateway
from common.ai_gateway.credential_resolver import credential_resolver
from rag.llm.chat_model import Base, AI_GATEWAY_CHAT_ENABLED
from rag.llm.embedding_model import OpenAIEmbed, AI_GATEWAY_EMBED_ENABLED
from api.db.services.ad_engine_service import AdEngineService, AdCreativeStudioService


class TestAIGatewayChatNonStreaming(unittest.IsolatedAsyncioTestCase):
    """Test Suite 1: Full-Cycle Non-Streaming Chat & Token Usage Tracking"""

    def setUp(self):
        self.prov = ai_gateway.get_provider("openai")
        self.orig_create = getattr(self.prov.client.chat.completions, "create", None)

    def tearDown(self):
        if self.orig_create:
            self.prov.client.chat.completions.create = self.orig_create

    async def test_non_streaming_chat_full_cycle_gateway(self):
        """Case 1: Base.async_chat -> AIGateway.chat -> OpenAIProvider.chat_complete -> verify response and last_usage"""
        prov = ai_gateway.get_provider("openai")

        fake_choice = MagicMock()
        fake_choice.message = MagicMock(content="Hello from AI Gateway Chat!", role="assistant")
        fake_choice.finish_reason = "stop"

        fake_resp = MagicMock(
            id="chatcmpl-test-001",
            model="gpt-4o",
            choices=[fake_choice],
            usage=MagicMock(prompt_tokens=12, completion_tokens=18, total_tokens=30),
            created=1700000000,
        )

        prov.client.chat.completions.create = AsyncMock(return_value=fake_resp)

        base_chat = Base("test-key-12345", "gpt-4o", "https://api.openai.com/v1")
        ans, tokens = await base_chat.async_chat("You are a helpful assistant.", [{"role": "user", "content": "Hello!"}])

        self.assertEqual(ans, "Hello from AI Gateway Chat!")
        self.assertEqual(tokens, 30)
        self.assertEqual(base_chat.last_usage["prompt_tokens"], 12)
        self.assertEqual(base_chat.last_usage["completion_tokens"], 18)
        self.assertEqual(base_chat.last_usage["total_tokens"], 30)

    async def test_non_streaming_chat_fallback_on_error(self):
        """Case 1b: Verify seamless safe fallback when Gateway encounters an exception"""
        prov = ai_gateway.get_provider("openai")
        prov.client.chat.completions.create = AsyncMock(side_effect=RuntimeError("Simulated network outage"))

        base_chat = Base("test-key-12345", "gpt-4o", "https://api.openai.com/v1")
        # Legacy client mock
        mock_legacy_choice = MagicMock()
        mock_legacy_choice.message = MagicMock(content="Legacy fallback response", role="assistant")
        mock_legacy_resp = MagicMock(
            choices=[mock_legacy_choice],
            usage=MagicMock(prompt_tokens=10, completion_tokens=10, total_tokens=20),
        )
        base_chat.async_client.chat.completions.create = AsyncMock(return_value=mock_legacy_resp)

        ans, tokens = await base_chat.async_chat("System", [{"role": "user", "content": "Hi"}])
        self.assertEqual(ans, "Legacy fallback response")
        self.assertEqual(tokens, 20)


class TestAIGatewayChatStreaming(unittest.IsolatedAsyncioTestCase):
    """Test Suite 2: Low-Latency Streaming, Reasoning Thought Parsing & Usage Tracking"""

    def setUp(self):
        self.prov_openai = ai_gateway.get_provider("openai")
        self.prov_deepseek = ai_gateway.get_provider("deepseek")
        self.orig_openai_create = getattr(self.prov_openai.client.chat.completions, "create", None)
        self.orig_deepseek_create = getattr(self.prov_deepseek.client.chat.completions, "create", None)

    def tearDown(self):
        if self.orig_openai_create:
            self.prov_openai.client.chat.completions.create = self.orig_openai_create
        if self.orig_deepseek_create:
            self.prov_deepseek.client.chat.completions.create = self.orig_deepseek_create

    async def test_streaming_chat_full_cycle_and_usage(self):
        """Case 2: Base.async_chat_streamly -> AIGateway.stream_chat -> verify text deltas and final last_usage"""
        prov = self.prov_openai

        class FakeChunk:
            def __init__(self, content=None, finish_reason=None, usage=None):
                self.id = "chunk-01"
                self.usage = usage
                if content is not None or finish_reason is not None:
                    choice = MagicMock()
                    choice.delta = MagicMock(content=content, reasoning_content=None)
                    choice.finish_reason = finish_reason
                    self.choices = [choice]
                else:
                    self.choices = []

        async def fake_stream():
            yield FakeChunk("AI ")
            yield FakeChunk("Gateway ")
            yield FakeChunk("Streaming!")
            yield FakeChunk(None, finish_reason="stop", usage=MagicMock(prompt_tokens=8, completion_tokens=12, total_tokens=20))

        prov.client.chat.completions.create = AsyncMock(return_value=fake_stream())

        base_chat = Base("test-key-12345", "gpt-4o", "https://api.openai.com/v1")
        chunks = []
        async for chunk in base_chat.async_chat_streamly("System", [{"role": "user", "content": "Stream test"}]):
            chunks.append(chunk)

        self.assertIn("AI ", chunks)
        self.assertIn("Gateway ", chunks)
        self.assertIn("Streaming!", chunks)
        self.assertEqual(base_chat.last_usage["prompt_tokens"], 8)
        self.assertEqual(base_chat.last_usage["completion_tokens"], 12)
        self.assertEqual(base_chat.last_usage["total_tokens"], 20)

    async def test_streaming_chat_deepseek_r1_reasoning_extraction(self):
        """Case 3: DeepSeek R1 reasoning stream -> verify delta.reasoning_content formatted as <think>...</think>"""
        prov = self.prov_deepseek

        class FakeDeepSeekChunk:
            def __init__(self, content=None, reasoning=None, finish_reason=None, usage=None):
                self.id = "ds-chunk-01"
                self.usage = usage
                choice = MagicMock()
                choice.delta = MagicMock(content=content, reasoning_content=reasoning)
                choice.finish_reason = finish_reason
                self.choices = [choice]

        async def fake_deepseek_stream():
            # 1. Thought phase
            yield FakeDeepSeekChunk(content=None, reasoning="Step 1: Analyze question\n")
            yield FakeDeepSeekChunk(content=None, reasoning="Step 2: Formulate concise answer")
            # 2. Answer phase
            yield FakeDeepSeekChunk(content="The final ", reasoning=None)
            yield FakeDeepSeekChunk(content="answer is 42.", reasoning=None, finish_reason="stop", usage=MagicMock(prompt_tokens=10, completion_tokens=25, total_tokens=35))

        prov.client.chat.completions.create = AsyncMock(return_value=fake_deepseek_stream())

        base_chat = Base("test-ds-key", "deepseek-reasoner", "https://api.deepseek.com/v1")
        chunks = []
        async for chunk in base_chat.async_chat_streamly("System", [{"role": "user", "content": "What is the answer?"}]):
            chunks.append(chunk)

        # Confirm <think> tag was yielded for thought tokens
        combined_text = "".join(str(c) for c in chunks if isinstance(c, str))
        self.assertIn("<think>", combined_text)
        self.assertIn("Step 1: Analyze question", combined_text)
        self.assertIn("</think>", combined_text)
        self.assertIn("The final answer is 42.", combined_text)
        self.assertEqual(base_chat.last_usage["total_tokens"], 35)


class TestAIGatewayEmbeddings(unittest.TestCase):
    """Test Suite 3: Batch Embeddings, Query Encodings, and 100% Vector Mathematical Parity"""

    def test_batch_embeddings_and_vector_math_parity(self):
        """Case 4: Verify exact float array equality between legacy path and AI Gateway path with index alignment"""
        fake_v1 = [0.12345678, -0.87654321, 0.99999999, 0.00000001]
        fake_v2 = [-0.22222222, 0.33333333, -0.44444444, 0.55555555]

        item1 = MagicMock(embedding=fake_v1, index=0)
        item2 = MagicMock(embedding=fake_v2, index=1)

        mock_resp = MagicMock(
            data=[item2, item1],  # Out-of-order in response to test sorting
            usage=MagicMock(prompt_tokens=10, total_tokens=10),
        )

        # 1. Legacy Run
        import rag.llm.embedding_model as em
        em.AI_GATEWAY_EMBED_ENABLED = False
        legacy_embedder = OpenAIEmbed("test-key", "text-embedding-3-small")
        legacy_embedder.client.embeddings.create = MagicMock(return_value=mock_resp)
        legacy_vecs, legacy_tokens = legacy_embedder.encode(["sentence 1", "sentence 2"])

        # 2. Gateway Run
        em.AI_GATEWAY_EMBED_ENABLED = True
        prov = ai_gateway.get_provider("openai")
        prov.client.embeddings.create = AsyncMock(return_value=mock_resp)
        gw_embedder = OpenAIEmbed("test-key", "text-embedding-3-small")
        gw_vecs, gw_tokens = gw_embedder.encode(["sentence 1", "sentence 2"])

        # 3. Assert Strict Mathematical Parity
        self.assertTrue(np.array_equal(legacy_vecs, gw_vecs), "Vector disparity detected between Legacy and Gateway paths!")
        self.assertEqual(legacy_tokens, gw_tokens)
        self.assertEqual(gw_vecs.shape, (2, 4))
        self.assertEqual(gw_vecs[0].tolist(), fake_v1)
        self.assertEqual(gw_vecs[1].tolist(), fake_v2)

    def test_encode_queries_gateway(self):
        """Case 4b: Verify single-query vector encoding through Gateway"""
        fake_query_vec = [0.01, -0.02, 0.03, -0.04]
        mock_resp = MagicMock(
            data=[MagicMock(embedding=fake_query_vec, index=0)],
            usage=MagicMock(prompt_tokens=4, total_tokens=4),
        )
        prov = ai_gateway.get_provider("openai")
        prov.client.embeddings.create = AsyncMock(return_value=mock_resp)

        embedder = OpenAIEmbed("test-key", "text-embedding-3-small")
        vec, tokens = embedder.encode_queries("search query text")

        self.assertIsInstance(vec, np.ndarray)
        self.assertEqual(vec.shape, (4,))
        self.assertEqual(tokens, 4)
        self.assertEqual(vec.tolist(), fake_query_vec)


class TestAIGatewaySecurityScrubbing(unittest.TestCase):
    """Test Suite 4: Zero-Leak Credential Scrubbing on Errors (401/429/500)"""

    def test_secret_redactor_scrubs_openai_and_bearer_tokens(self):
        """Case 5: Verify SecretRedactor scrubs sk-*, Bearer tokens, and JSON key structures"""
        dirty_msg = (
            "Failed request: 401 Unauthorized for key sk-proj-abcdef1234567890abcdef1234567890 "
            "with Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9 and api_key=sk-11223344556677889900aabbccdd"
        )
        clean_msg = SecretRedactor.redact(dirty_msg)

        self.assertNotIn("sk-proj-abcdef1234567890abcdef1234567890", clean_msg)
        self.assertNotIn("sk-11223344556677889900aabbccdd", clean_msg)
        self.assertNotIn("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9", clean_msg)
        self.assertIn("[REDACTED_API_KEY]", clean_msg)
        self.assertIn("[REDACTED_TOKEN]", clean_msg)

    def test_provider_exception_wrapping_sanitizes_secrets(self):
        """Case 5b: Provider _wrap_provider_exception sanitizes any exception containing secrets"""
        prov = ai_gateway.get_provider("openai")
        raw_error = Exception("Invalid token sk-proj-verysecretkey1234567890 in OpenAI response")
        wrapped = prov._wrap_provider_exception(raw_error)

        self.assertIsInstance(wrapped, AIGatewayError)
        self.assertNotIn("sk-proj-verysecretkey1234567890", str(wrapped))
        self.assertIn("[REDACTED_API_KEY]", str(wrapped))


class TestAIGatewayCredentialResolver(unittest.TestCase):
    """Test Suite 5: Credential Resolver Admin CRUD, Masking, and Tiered Resolution"""

    def test_admin_crud_and_key_masking(self):
        """Case 6: Save credentials, list with auto-masking, update partially without wiping secret, delete"""
        # 1. Masking verification
        masked = credential_resolver.mask_api_key("sk-proj-1234567890abcdef1234")
        self.assertEqual(masked, "sk-proj...1234")

        # 2. Save credentials
        credential_resolver.save_provider_credentials(
            provider_type="openai",
            api_key="sk-live-secret-test-key-998877",
            base_url="https://api.openai.com/v1",
        )

        # 3. List for Admin
        admin_list = credential_resolver.list_providers_for_admin()
        openai_item = next((p for p in admin_list if p.provider == "openai"), None)
        self.assertIsNotNone(openai_item)
        self.assertTrue(openai_item.is_configured)
        self.assertNotIn("sk-live-secret-test-key-998877", openai_item.masked_api_key)
        self.assertTrue(openai_item.masked_api_key.startswith("sk-live"))

        # 4. Partial update (keeping existing key when masked value is passed back)
        credential_resolver.save_provider_credentials(
            provider_type="openai",
            api_key=openai_item.masked_api_key,  # Passed masked key back
            base_url="https://api.openai.com/v1",
        )
        resolved_key, _ = credential_resolver.resolve(ProviderType.OPENAI)
        self.assertEqual(resolved_key, "sk-live-secret-test-key-998877", "Masked key wiped the actual secret on partial update!")

        # 5. Delete credentials
        credential_resolver.delete_provider_credentials("openai")
        self.assertNotIn("openai:system", credential_resolver._memory_store)

    def test_untested_providers_blocked_in_admin_panel(self):
        """Case 6b: Verify Anthropic & Gemini are blocked from Admin selection until TASK-FOLLOWUP-LIVE-TEST-ANTHROPIC-GEMINI is closed"""
        # 1. Check direct listing
        admin_all = credential_resolver.list_providers_for_admin()
        anthropic_rec = next((p for p in admin_all if p.provider == "anthropic"), None)
        gemini_rec = next((p for p in admin_all if p.provider == "gemini"), None)
        openai_rec = next((p for p in admin_all if p.provider == "openai"), None)

        self.assertIsNotNone(anthropic_rec)
        self.assertIsNotNone(gemini_rec)
        self.assertIsNotNone(openai_rec)

        # OpenAI must be live tested & available
        self.assertTrue(openai_rec.is_live_tested)
        self.assertTrue(openai_rec.is_available_in_admin)
        self.assertEqual(openai_rec.verification_status, "verified")

        # Anthropic & Gemini must be blocked by default
        self.assertFalse(anthropic_rec.is_live_tested)
        self.assertFalse(anthropic_rec.is_available_in_admin)
        self.assertEqual(anthropic_rec.verification_status, "requires_live_test")
        self.assertIn("requires live outbound API verification", anthropic_rec.status_reason)

        self.assertFalse(gemini_rec.is_live_tested)
        self.assertFalse(gemini_rec.is_available_in_admin)
        self.assertEqual(gemini_rec.verification_status, "requires_live_test")

        # 2. Check UI selection dropdown (only_available=True)
        available_only = credential_resolver.list_providers_for_admin(only_available=True)
        available_ids = [p.provider for p in available_only]
        self.assertIn("openai", available_ids)
        self.assertIn("deepseek", available_ids)
        self.assertNotIn("anthropic", available_ids)
        self.assertNotIn("gemini", available_ids)


class TestAIGatewayAdsIntegration(unittest.TestCase):
    """Test Suite 6: Swipies Ads AI Copywriter & Semantic Embeddings Integration"""

    def setUp(self):
        self.prov = ai_gateway.get_provider("openai")
        self.orig_chat = getattr(self.prov.client.chat.completions, "create", None)
        self.orig_embed = getattr(self.prov.client.embeddings, "create", None)

    def tearDown(self):
        if self.orig_chat:
            self.prov.client.chat.completions.create = self.orig_chat
        if self.orig_embed:
            self.prov.client.embeddings.create = self.orig_embed

    def test_ad_engine_generate_copy_and_creative_matrix(self):
        """Case 7: AdEngineService.generate_copy & AdCreativeStudioService.generate_creative_matrix via Gateway"""
        prov = ai_gateway.get_provider("openai")
        mock_copy = {
            "headlines": ["Nike Air Max — 20% Скидка", "Купить Nike Air в Ташкенте", "Оригинал с доставкой"],
            "descriptions": ["Премиум кроссовки для бега.", "Быстрая доставка по Ташкенту.", "Гарантия качества 100%."],
            "ctas": ["Купить онлайн", "Узнать подробнее", "Заказать примерку"],
            "recommended_keywords": ["кроссовки nike", "купить обувь", "nike air"],
            "suggested_bid_cpc": 0.18,
            "suggested_bid_cpm": 1.80,
            "badges": ["🔥 Хит продаж", "🚚 Экспресс-доставка"],
        }

        fake_resp = MagicMock(
            choices=[MagicMock(message=MagicMock(content=json.dumps(mock_copy), role="assistant"), finish_reason="stop")],
            usage=MagicMock(prompt_tokens=40, completion_tokens=80, total_tokens=120),
            model="gpt-4o",
            provider=ProviderType.OPENAI,
        )
        prov.client.chat.completions.create = AsyncMock(return_value=fake_resp)

        # 1. Test generate_copy
        copy_res = AdEngineService.generate_copy(
            product_name="Nike Air Max",
            description="Спортивная обувь",
            category="Обувь",
            target_audience="Спортсмены",
        )
        self.assertTrue(copy_res["success"])
        self.assertEqual(len(copy_res["headlines"]), 3)
        self.assertEqual(copy_res["suggested_bid_cpc"], 0.18)

        # 2. Test generate_creative_matrix
        matrix_res = AdCreativeStudioService.generate_creative_matrix(
            advertiser_id="adv_test_456",
            product_name="Nike Air Max",
            category="Обувь",
            save_assets=False,
        )
        self.assertEqual(matrix_res["product_name"], "Nike Air Max")
        self.assertIn("formats", matrix_res)
        self.assertIn("text_card", matrix_res["formats"])
        self.assertIn("rich_interactive_card", matrix_res["formats"])
        self.assertIn("story_banner", matrix_res["formats"])
        self.assertIn("leaderboard_banner", matrix_res["formats"])
        self.assertIn("video_storyboard", matrix_res["formats"])

    def test_ad_engine_semantic_embedding(self):
        """Case 7b: AdEngineService.compute_semantic_embedding routes through ai_gateway.embeddings()"""
        prov = ai_gateway.get_provider("openai")
        prov.client.embeddings.create = AsyncMock(return_value=MagicMock(
            data=[MagicMock(embedding=[0.05, -0.15, 0.75, 0.35], index=0)],
            usage=MagicMock(prompt_tokens=3, total_tokens=3),
        ))

        vec = AdEngineService.compute_semantic_embedding("беговые кроссовки для марафона")
        self.assertEqual(len(vec), 4)
        self.assertEqual(vec[0], 0.05)


if __name__ == "__main__":
    unittest.main()
