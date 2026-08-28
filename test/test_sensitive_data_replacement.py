import asyncio
import os
import sys
import unittest
from unittest.mock import MagicMock, patch, AsyncMock

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import types
from importlib.machinery import ModuleSpec
from sqlalchemy.types import UserDefinedType


class AutoMockModule(types.ModuleType):
    def __getattr__(self, name):
        if name in ("__path__", "__file__", "__spec__", "__loader__", "__package__"):
            raise AttributeError(name)
        # Return a dynamically usable type/module
        val = type(name, (object,), {
            "__getattr__": lambda self, attr: MagicMock(),
            "__call__": lambda self, *a, **k: MagicMock(),
            "__mro_entries__": lambda self, bases: (object,),
        })()
        setattr(self, name, val)
        return val

    def __call__(self, *args, **kwargs):
        return MagicMock()

    def __mro_entries__(self, bases):
        return (object,)


class DummyRagTokenizer:
    def __init__(self, *args, **kwargs):
        self.freq = MagicMock()
        self._tradi2simp = MagicMock()
        self._strQ2B = MagicMock()

    def tokenize(self, text):
        return text.split()

    def fine_grained_tokenize(self, text):
        return text.split()

    def tag(self, text):
        return []


class DummyARRAY(UserDefinedType):
    def __init__(self, *args, **kwargs):
        pass


TARGET_MOCKS = {
    "infinity",
    "pyobvector",
    "opendal",
    "opensearchpy",
    "azure",
    "google",
    "minio",
    "oss2",
    "valkey",
    "boto3",
    "botocore",
    "langfuse",
    "json_repair",
    "beartype",
    "docx",
    "pptx",
    "openpyxl",
    "fitz",
    "pdfplumber",
    "deepdoc",
    "litellm",
    "openai",
    "anthropic",
    "dashscope",
    "zhipuai",
    "ollama",
    "xinference",
    "qianfan",
    "volcengine",
    "ormsgpack",
    "markdown_to_json",
    "duckduckgo_search",
    "seaborn",
    "matplotlib",
    "plotly",
    "tavily",
    "markdown",
}


class AutoMockFinder:
    def find_spec(self, fullname, path, target=None):
        root = fullname.split(".")[0]
        if root.startswith("_"):
            return None
        if root in TARGET_MOCKS:
            return ModuleSpec(fullname, self, is_package=True)
        return None

    def create_module(self, spec):
        mod = AutoMockModule(spec.name)
        if spec.name == "infinity.rag_tokenizer":
            mod.RagTokenizer = DummyRagTokenizer
        elif spec.name == "infinity.common":
            mod.InfinityException = Exception
        elif spec.name == "pyobvector":
            mod.ARRAY = DummyARRAY
        return mod

    def exec_module(self, module):
        pass


sys.meta_path.insert(0, AutoMockFinder())

from api.utils.sensitive_data_utils import (
    _build_rule_pattern,
    _parse_bool,
    anonymize_messages,
    anonymize_text,
    deanonymize_text,
    StreamingDeanonymizer,
)


class TestSensitiveDataReplacement(unittest.TestCase):
    """Comprehensive test suite for sensitive data replacement & stream deanonymization in licence_v."""

    # ==========================================
    # TASK-06: Core Unit Tests
    # ==========================================

    def test_01_word_boundary_isolation(self):
        """Plaintext rules with alphanumeric characters should not replace substrings within larger words."""
        rules = [
            {"search": "cat", "replace": "[ANIMAL]"},
            {"search": "bank", "replace": "[FINANCIAL_INSTITUTION]"},
        ]
        text = "A cat went to the category of catastrophe near the embankment banking bank."
        anon = anonymize_text(text, rules)
        self.assertEqual(
            anon,
            "A [ANIMAL] went to the category of catastrophe near the embankment banking [FINANCIAL_INSTITUTION].",
        )

        deanon = deanonymize_text(anon, rules)
        self.assertEqual(deanon, text)

    def test_02_punctuation_and_symbols(self):
        """Punctuation and symbols (e.g. $100, user@acme.corp) are properly matched without broken regex anchors."""
        rules = [
            {"search": "$100", "replace": "[PRICE]"},
            {"search": "user@acme.corp", "replace": "[EMAIL]"},
            {"search": "+1-800-555-0199", "replace": "[PHONE]"},
        ]
        text = "Cost is $100. Contact user@acme.corp or call +1-800-555-0199."
        anon = anonymize_text(text, rules)
        self.assertEqual(
            anon,
            "Cost is [PRICE]. Contact [EMAIL] or call [PHONE].",
        )

        deanon = deanonymize_text(anon, rules)
        self.assertEqual(deanon, text)

    def test_03_custom_regex_mode(self):
        """When is_regex=True, custom regex patterns are preserved without automatic \\b wrapping."""
        rules = [
            {"search": r"\b\d{4}-\d{4}\b", "replace": "[CARD_CODE]", "is_regex": True},
        ]
        text = "Code is 1234-5678, not 12-34 and not 12345-67890."
        anon = anonymize_text(text, rules)
        self.assertEqual(anon, "Code is [CARD_CODE], not 12-34 and not 12345-67890.")

    def test_04_case_sensitivity_flag(self):
        """Case sensitivity toggles work reliably in both anonymize and deanonymize phases."""
        rules_insensitive = [{"search": "SecretProject", "replace": "[PROJECT]", "case_sensitive": False}]
        rules_sensitive = [{"search": "SecretProject", "replace": "[PROJECT]", "case_sensitive": True}]

        text = "Look at secretproject, SecretProject, and SECRETPROJECT."
        anon_insens = anonymize_text(text, rules_insensitive)
        self.assertEqual(anon_insens, "Look at [PROJECT], [PROJECT], and [PROJECT].")

        anon_sens = anonymize_text(text, rules_sensitive)
        self.assertEqual(anon_sens, "Look at secretproject, [PROJECT], and SECRETPROJECT.")

    def test_05_rule_sorting_priority(self):
        """Longer search terms are matched before shorter substrings to prevent partial collisions."""
        rules = [
            {"search": "Software Engineer", "replace": "[ROLE_JUNIOR]"},
            {"search": "Senior Software Engineer", "replace": "[ROLE_SENIOR]"},
            {"search": "Lead Senior Software Engineer", "replace": "[ROLE_LEAD]"},
        ]
        text = "Hiring Lead Senior Software Engineer and Senior Software Engineer and Software Engineer."
        anon = anonymize_text(text, rules)
        self.assertEqual(anon, "Hiring [ROLE_LEAD] and [ROLE_SENIOR] and [ROLE_JUNIOR].")

        deanon = deanonymize_text(anon, rules)
        self.assertEqual(deanon, text)

    # ==========================================
    # TASK-07: StreamingDeanonymizer & Marker Tests
    # ==========================================

    def test_06_streaming_deanonymizer_token_split(self):
        """When an LLM splits a placeholder across micro-token chunks, no raw placeholder leaks."""
        rules = [{"search": "Иван Иванов", "replace": "[CLIENT_NAME]"}]
        deanonymizer = StreamingDeanonymizer(rules)

        chunks = ["Hello, [", "CLI", "ENT_", "NAME", "]! How are you?"]
        emitted = []
        for c in chunks:
            out = deanonymizer.feed(c)
            if out:
                emitted.append(out)
        tail = deanonymizer.flush(final=True)
        if tail:
            emitted.append(tail)

        full_result = "".join(emitted)
        self.assertEqual(full_result, "Hello, Иван Иванов! How are you?")
        self.assertNotIn("[CLIENT_NAME]", full_result)
        self.assertNotIn("[CLI", full_result)

    def test_07_streaming_deanonymizer_unmatched_prefix_flush(self):
        """An uncompleted tentative prefix is flushed cleanly without data loss on stream finish."""
        rules = [{"search": "Иван Иванов", "replace": "[CLIENT_NAME]"}]
        deanonymizer = StreamingDeanonymizer(rules)

        chunks = ["Looking at [", "OTHER_THING]"]
        emitted = []
        for c in chunks:
            out = deanonymizer.feed(c)
            if out:
                emitted.append(out)
        tail = deanonymizer.flush(final=True)
        if tail:
            emitted.append(tail)

        full_result = "".join(emitted)
        self.assertEqual(full_result, "Looking at [OTHER_THING]")

    def test_08_streaming_deanonymizer_latency_benchmark(self):
        """Normal text chunks without placeholders are emitted in O(1) with zero artificial delay."""
        rules = [{"search": "Иван Иванов", "replace": "[CLIENT_NAME]"}]
        deanonymizer = StreamingDeanonymizer(rules)

        chunks = [f"Word{i} " for i in range(100)]
        for c in chunks:
            out = deanonymizer.feed(c)
            # Safe text must be emitted immediately (buffer holds at most max_prefix_len)
            self.assertTrue(len(out) > 0)
        tail = deanonymizer.flush(final=True)
        self.assertEqual(tail, "")

    def test_09_streaming_think_marker_boundary_flush(self):
        """NEW scenario in licence_v: chunk split before </think> marker flushes safely without cross-section bleeding."""
        rules = [{"search": "Иван Иванов", "replace": "[CLIENT_NAME]"}]
        deanonymizer = StreamingDeanonymizer(rules)

        # 1. Feed think section chunk ending with partial prefix
        out1 = deanonymizer.feed("Thinking about [CLI")
        self.assertEqual(out1, "Thinking about ")
        self.assertEqual(deanonymizer._buffer, "[CLI")

        # 2. Marker event </think> arrives -> pre-marker flush
        marker_flush = deanonymizer.flush(final=False)
        self.assertEqual(marker_flush, "[CLI")
        self.assertEqual(deanonymizer._buffer, "")

        # 3. Answer section arrives
        out2 = deanonymizer.feed("ENT_NAME] is verified.")
        self.assertEqual(out2, "ENT_NAME] is verified.")

        tail = deanonymizer.flush(final=True)
        self.assertEqual(tail, "")

    # ==========================================
    # TASK-08: Integration & DB Persistence Tests
    # ==========================================

    def test_10_dialog_service_async_chat_solo_streaming(self):
        """Test async_chat_solo generator in dialog_service with StreamingDeanonymizer."""
        from api.db.services.dialog_service import async_chat_solo

        dialog = MagicMock()
        dialog.tenant_id = "test_tenant"
        dialog.llm_id = None
        dialog.llm_setting = {}
        dialog.prompt_config = {
            "system": "You are a helpful assistant.",
            "sensitive_data_replacement": {
                "enabled": True,
                "rules": [{"search": "Иван Иванов", "replace": "[CLIENT_NAME]"}],
            },
        }

        messages = [{"role": "user", "content": "Привет, Иван Иванов!"}]

        # Mock LLMBundle and async_chat_streamly_delta
        async def mock_stream_delta(*args, **kwargs):
            chunks = ["<think>Thinking about [CLI", "ENT_NAME]</think>", "Hello, [CLI", "ENT_NAME]!"]
            for ch in chunks:
                yield ch

        with patch("api.db.services.dialog_service.get_tenant_default_model_by_type", return_value={"model_type": "chat", "llm_factory": "OpenAI"}), \
             patch("api.db.services.dialog_service.LLMBundle") as MockBundle:
            bundle_inst = MockBundle.return_value
            bundle_inst.trace_context = {}
            bundle_inst.async_chat_streamly_delta = mock_stream_delta

            async def run_solo():
                results = []
                async for ans in async_chat_solo(dialog, messages, stream=True):
                    results.append(ans)
                return results

            results = asyncio.run(run_solo())

            # Check that results are dictionaries
            self.assertTrue(len(results) > 0)
            combined_answers = "".join(r.get("answer", "") for r in results if not r.get("final"))
            self.assertIn("Иван Иванов", combined_answers)
            self.assertNotIn("[CLIENT_NAME]", combined_answers)

    def test_11_dialog_service_async_chat_kb_streaming(self):
        """Test async_chat generator in dialog_service with KB search and StreamingDeanonymizer."""
        from api.db.services.dialog_service import async_chat

        dialog = MagicMock()
        dialog.tenant_id = "test_tenant"
        dialog.kb_ids = ["kb_1"]
        dialog.llm_id = "mock_chat"
        dialog.llm_setting = {}
        dialog.prompt_config = {
            "system": "You are a helpful assistant.",
            "sensitive_data_replacement": {
                "enabled": True,
                "rules": [{"search": "ACME_SECRET", "replace": "[SECRET_TOKEN]"}],
            },
        }

        messages = [{"role": "user", "content": "Tell me about ACME_SECRET"}]

        async def mock_stream_delta(*args, **kwargs):
            chunks = ["The secret is [SEC", "RET_TO", "KEN] exactly."]
            for ch in chunks:
                yield ch

        mock_kb = MagicMock()
        mock_kb.tenant_id = "test_tenant"
        mock_kb.embd_id = "mock_embd"
        mock_kb.parser_id = "naive"

        mock_retriever = MagicMock()
        mock_retriever.retrieval = AsyncMock(return_value={"chunks": [], "doc_aggs": [], "total": 0})

        dialog.meta_data_filter = {}
        dialog.top_n = 5

        with patch("api.db.services.dialog_service.get_model_type_by_name", return_value=["chat"]), \
             patch("api.db.services.dialog_service.get_model_config_from_provider_instance", return_value={"model_type": "chat", "llm_name": "mock_chat", "llm_factory": "OpenAI", "max_tokens": 4096}), \
             patch("api.db.services.dialog_service.TenantLangfuseService.filter_by_tenant", return_value=None), \
             patch("api.db.services.dialog_service.KnowledgebaseService.get_by_ids", return_value=[mock_kb]), \
             patch("api.db.services.dialog_service.KnowledgebaseService.get_field_map", return_value={}), \
             patch("api.db.services.dialog_service.settings.retriever", mock_retriever), \
             patch("api.db.services.dialog_service.message_fit_in", return_value=(10, [{"role": "system", "content": "sys"}, {"role": "user", "content": "Tell me about [SECRET_TOKEN]"}])), \
             patch("api.db.services.dialog_service.LLMBundle") as MockBundle:

            bundle_inst = MockBundle.return_value
            bundle_inst.trace_context = {}
            bundle_inst.async_chat_streamly_delta = mock_stream_delta

            async def run_kb():
                results = []
                async for ans in async_chat(dialog, messages, stream=True):
                    results.append(ans)
                return results

            results = asyncio.run(run_kb())
            combined = "".join(r.get("answer", "") for r in results if not r.get("final"))
            self.assertIn("ACME_SECRET", combined)
            self.assertNotIn("[SECRET_TOKEN]", combined)

    def test_12_multiturn_db_persistence_integrity(self):
        """anonymize_messages creates a deepcopy and preserves the original message list intact."""
        rules = [{"search": "ACME Corp", "replace": "[COMPANY]"}]
        original_msgs = [
            {"role": "user", "content": "I work at ACME Corp."},
            {"role": "assistant", "content": "Welcome to ACME Corp!"},
        ]

        anon_msgs = anonymize_messages(original_msgs, rules)

        # Anonymized copy has placeholders
        self.assertEqual(anon_msgs[0]["content"], "I work at [COMPANY].")
        self.assertEqual(anon_msgs[1]["content"], "Welcome to [COMPANY]!")

        # Original messages remain 100% untouched for DB persistence
        self.assertEqual(original_msgs[0]["content"], "I work at ACME Corp.")
        self.assertEqual(original_msgs[1]["content"], "Welcome to ACME Corp!")


if __name__ == "__main__":
    unittest.main(verbosity=2)
