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
import asyncio
import os
import sys
import types
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Stub out heavy C-extensions/optional database driver dependencies if not present on host
from sqlalchemy.types import TypeEngine

class _ArrayClass(TypeEngine):
    def __init__(self, *args, **kwargs):
        super().__init__()

class _VectorClass(TypeEngine):
    def __init__(self, *args, **kwargs):
        super().__init__()

pyob = types.ModuleType("pyobvector")
pyob.ARRAY = _ArrayClass
pyob.VECTOR = _VectorClass
pyob.ObVecClient = MagicMock()
pyob.FtsIndexParam = MagicMock()
pyob.FtsParser = MagicMock()
sys.modules["pyobvector"] = pyob

valkey_mod = types.ModuleType("valkey")
valkey_mod.__path__ = []
valkey_mod.Redis = MagicMock()
valkey_mod.StrictRedis = MagicMock()
valkey_mod.ConnectionPool = MagicMock()
valkey_lock = types.ModuleType("valkey.lock")
valkey_lock.Lock = MagicMock()
valkey_mod.lock = valkey_lock
sys.modules["valkey"] = valkey_mod
sys.modules["valkey.lock"] = valkey_lock

redis_mod = types.ModuleType("redis")
redis_mod.__path__ = []
redis_mod.Redis = MagicMock()
redis_mod.StrictRedis = MagicMock()
redis_mod.ConnectionPool = MagicMock()
redis_lock = types.ModuleType("redis.lock")
redis_lock.Lock = MagicMock()
redis_mod.lock = redis_lock
sys.modules["redis"] = redis_mod
sys.modules["redis.lock"] = redis_lock

opendal_mod = types.ModuleType("opendal")
opendal_mod.Operator = MagicMock()
sys.modules["opendal"] = opendal_mod

opensearch_mod = types.ModuleType("opensearchpy")
opensearch_mod.OpenSearch = MagicMock()
opensearch_mod.NotFoundError = Exception
opensearch_mod.BadRequestError = Exception
opensearch_mod.ConnectionTimeout = Exception
opensearch_mod.UpdateByQuery = MagicMock()
opensearch_mod.Q = MagicMock()
opensearch_mod.Search = MagicMock()
opensearch_mod.Index = MagicMock()
opensearch_mod.Mapping = MagicMock()
opensearch_mod.__version__ = (2, 0, 0)
opensearch_mod.__path__ = []
opensearch_mod.helpers = types.ModuleType("opensearchpy.helpers")
opensearch_mod.helpers.bulk = MagicMock()
opensearch_mod.client = types.ModuleType("opensearchpy.client")
opensearch_mod.client.IndicesClient = MagicMock()
sys.modules["opensearchpy"] = opensearch_mod
sys.modules["opensearchpy.helpers"] = opensearch_mod.helpers
sys.modules["opensearchpy.client"] = opensearch_mod.client

es_mod = types.ModuleType("elasticsearch")
es_mod.__path__ = []
es_mod.Elasticsearch = MagicMock()
es_mod.NotFoundError = Exception
es_mod.BadRequestError = Exception
es_mod.ConnectionTimeout = Exception
es_mod.__version__ = (8, 0, 0)
es_dsl = types.ModuleType("elasticsearch.dsl")
es_dsl.UpdateByQuery = MagicMock()
es_dsl.Q = MagicMock()
es_dsl.Search = MagicMock()
es_dsl.Index = MagicMock()
es_dsl.Mapping = MagicMock()
es_mod.dsl = es_dsl
es_mod.helpers = types.ModuleType("elasticsearch.helpers")
es_mod.helpers.bulk = MagicMock()
es_mod.client = types.ModuleType("elasticsearch.client")
es_mod.client.IndicesClient = MagicMock()
sys.modules["elasticsearch"] = es_mod
sys.modules["elasticsearch.dsl"] = es_dsl
sys.modules["elasticsearch.helpers"] = es_mod.helpers
sys.modules["elasticsearch.client"] = es_mod.client

az_mod = types.ModuleType("azure")
az_mod.__path__ = []
az_storage = types.ModuleType("azure.storage")
az_storage.__path__ = []
az_blob = types.ModuleType("azure.storage.blob")
az_blob.ContainerClient = MagicMock()
az_blob.BlobServiceClient = MagicMock()
az_storage.blob = az_blob
az_datalake = types.ModuleType("azure.storage.filedatalake")
az_datalake.FileSystemClient = MagicMock()
az_storage.filedatalake = az_datalake
az_id = types.ModuleType("azure.identity")
az_id.ClientSecretCredential = MagicMock()
az_id.AzureAuthorityHosts = MagicMock()
az_mod.identity = az_id
az_mod.storage = az_storage
sys.modules["azure"] = az_mod
sys.modules["azure.storage"] = az_storage
sys.modules["azure.storage.blob"] = az_blob
sys.modules["azure.storage.filedatalake"] = az_datalake
sys.modules["azure.identity"] = az_id

gcs_mod = types.ModuleType("google")
gcs_mod.__path__ = []
gcs_cloud = types.ModuleType("google.cloud")
gcs_cloud.__path__ = []
gcs_storage = types.ModuleType("google.cloud.storage")
gcs_storage.Client = MagicMock()
gcs_cloud.storage = gcs_storage
gcs_mod.cloud = gcs_cloud
gcs_api_core = types.ModuleType("google.api_core")
gcs_api_core.__path__ = []
gcs_exceptions = types.ModuleType("google.api_core.exceptions")
gcs_exceptions.NotFound = Exception
gcs_api_core.exceptions = gcs_exceptions
gcs_mod.api_core = gcs_api_core
sys.modules["google"] = gcs_mod
sys.modules["google.cloud"] = gcs_cloud
sys.modules["google.cloud.storage"] = gcs_storage
sys.modules["google.api_core"] = gcs_api_core
sys.modules["google.api_core.exceptions"] = gcs_exceptions

oss2_mod = types.ModuleType("oss2")
oss2_mod.Auth = MagicMock()
oss2_mod.Bucket = MagicMock()
oss2_mod.BucketIterator = MagicMock()
sys.modules["oss2"] = oss2_mod

boto3_mod = types.ModuleType("boto3")
boto3_mod.client = MagicMock()
boto3_mod.session = MagicMock()
sys.modules["boto3"] = boto3_mod

botocore_mod = types.ModuleType("botocore")
botocore_mod.__path__ = []
botocore_mod.client = types.ModuleType("botocore.client")
botocore_mod.client.Config = MagicMock()
botocore_config = types.ModuleType("botocore.config")
botocore_config.Config = MagicMock()
botocore_mod.config = botocore_config
botocore_exceptions = types.ModuleType("botocore.exceptions")
botocore_exceptions.ClientError = Exception
botocore_mod.exceptions = botocore_exceptions
sys.modules["botocore"] = botocore_mod
sys.modules["botocore.client"] = botocore_mod.client
sys.modules["botocore.config"] = botocore_config
sys.modules["botocore.exceptions"] = botocore_exceptions

minio_mod = types.ModuleType("minio")
minio_mod.__path__ = []
minio_mod.Minio = MagicMock()
minio_mod.commonconfig = types.ModuleType("minio.commonconfig")
minio_mod.commonconfig.CopySource = MagicMock()
minio_mod.error = types.ModuleType("minio.error")
minio_mod.error.S3Error = Exception
minio_mod.error.ServerError = Exception
minio_mod.error.InvalidResponseError = Exception
minio_mod.error.ResponseError = Exception
sys.modules["minio"] = minio_mod
sys.modules["minio.commonconfig"] = minio_mod.commonconfig
sys.modules["minio.error"] = minio_mod.error

class _StubRagTokenizer:
    def tokenize(self, text):
        return []
    def fine_grained_tokenize(self, text):
        return []
    def tag(self, text):
        return []
    def freq(self, text):
        return 0
    def _tradi2simp(self, text):
        return text
    def _strQ2B(self, text):
        return text

inf_pkg = types.ModuleType("infinity")
inf_pkg.__path__ = []
inf_rag = types.ModuleType("infinity.rag_tokenizer")
inf_rag.RagTokenizer = _StubRagTokenizer
inf_rag.is_chinese = lambda s: False
inf_rag.is_number = lambda s: False
inf_rag.is_alphabet = lambda s: True
inf_rag.naive_qie = lambda txt: [txt]
inf_pkg.rag_tokenizer = inf_rag
inf_common = types.ModuleType("infinity.common")
inf_common.InfinityException = Exception
inf_common.SortType = MagicMock()
inf_common.ConflictType = MagicMock()
inf_pkg.common = inf_common
inf_index = types.ModuleType("infinity.index")
inf_index.IndexInfo = MagicMock()
inf_index.IndexType = MagicMock()
inf_pkg.index = inf_index
inf_errors = types.ModuleType("infinity.errors")
inf_errors.ErrorCode = MagicMock()
inf_pkg.errors = inf_errors
inf_rpc = types.ModuleType("infinity.remote_thrift.infinity_thrift_rpc")
inf_rpc.ttypes = types.ModuleType("infinity.remote_thrift.infinity_thrift_rpc.ttypes")
sys.modules["infinity"] = inf_pkg
sys.modules["infinity.rag_tokenizer"] = inf_rag
sys.modules["infinity.common"] = inf_common
sys.modules["infinity.index"] = inf_index
sys.modules["infinity.errors"] = inf_errors
sys.modules["infinity.remote_thrift"] = types.ModuleType("infinity.remote_thrift")
sys.modules["infinity.remote_thrift.infinity_thrift_rpc"] = inf_rpc
sys.modules["infinity.remote_thrift.infinity_thrift_rpc.ttypes"] = inf_rpc.ttypes

langfuse_mod = types.ModuleType("langfuse")
langfuse_mod.Langfuse = MagicMock()
langfuse_mod.propagate_attributes = MagicMock()
sys.modules["langfuse"] = langfuse_mod

jr_mod = types.ModuleType("json_repair")
jr_mod.repair_json = lambda s, *a, **kw: s
jr_mod.loads = lambda s, *a, **kw: {}
jr_mod.json_repair = jr_mod
sys.modules["json_repair"] = jr_mod

bt_mod = types.ModuleType("beartype")
bt_claw = types.ModuleType("beartype.claw")
bt_claw.beartype_this_package = lambda *a, **kw: None
bt_mod.claw = bt_claw
sys.modules["beartype"] = bt_mod
sys.modules["beartype.claw"] = bt_claw

cv2_mod = types.ModuleType("cv2")
cv2_mod.INTER_LINEAR = 1
cv2_mod.INTER_CUBIC = 2
cv2_mod.BORDER_CONSTANT = 0
cv2_mod.BORDER_REPLICATE = 1
cv2_mod.COLOR_BGR2RGB = 0
cv2_mod.COLOR_BGR2GRAY = 1
cv2_mod.COLOR_GRAY2BGR = 2
cv2_mod.IMREAD_IGNORE_ORIENTATION = 128
cv2_mod.IMREAD_COLOR = 1
cv2_mod.RETR_LIST = 1
cv2_mod.CHAIN_APPROX_SIMPLE = 2
cv2_mod.__getattr__ = lambda name: 0 if name.isupper() else MagicMock()
sys.modules["cv2"] = cv2_mod

class _StubModule(types.ModuleType):
    def __getattr__(self, name):
        m = MagicMock()
        setattr(self, name, m)
        return m

class _AutoStubLoader:
    def create_module(self, spec):
        m = _StubModule(spec.name)
        m.__path__ = []
        return m

    def exec_module(self, module):
        pass

class _AutoStubFinder:
    def __init__(self, prefixes):
        self.prefixes = tuple(prefixes)

    def find_spec(self, fullname, path, target=None):
        for p in self.prefixes:
            if fullname == p or fullname.startswith(p + "."):
                from importlib.machinery import ModuleSpec
                spec = ModuleSpec(fullname, _AutoStubLoader(), is_package=True)
                return spec
        return None

_auto_stubs = [
    "markdown", "markdown_to_json", "docx", "pdfplumber", "pypdf", "ebooklib", "openpyxl", "bs4", "pptx",
    "xgboost", "tavily", "duckduckgo_search", "pyclipper", "shapely", "onnxruntime",
    "paddleocr", "pypdfium2", "PIL", "timm", "nltk", "spacy", "PIL.Image", "PIL.ImageDraw"
]
for mod_name in _auto_stubs:
    if mod_name not in sys.modules:
        m = _StubModule(mod_name)
        m.__path__ = []
        if mod_name == "markdown":
            m.markdown = lambda s, *a, **kw: s
        sys.modules[mod_name] = m

sys.meta_path.insert(0, _AutoStubFinder(_auto_stubs))

from api.utils.sensitive_data_utils import (
    _build_rule_pattern,
    anonymize_text,
    deanonymize_text,
    anonymize_messages,
    StreamingDeanonymizer,
)


class TestSensitiveDataReplacement(unittest.TestCase):
    """
    Comprehensive verification suite for Sensitive Data Replacement and Stream Deanonymization.
    Covers Word Boundaries (\b), Custom Regex, Streaming Token Splitting, Forced Flush,
    Zero-delay Latency, async_chat_solo execution, and Conversation DB persistence.
    """

    def test_01_plaintext_word_boundary_isolation(self):
        """TEST-01: Plaintext rule 'cat' -> '[ANIMAL]' must not replace inside 'category' or 'bobcat'."""
        rules = [
            {"search": "cat", "replace": "[ANIMAL]", "case_sensitive": False, "is_regex": False}
        ]
        text = "The cat sat in category and bobcat was scattered."
        anon = anonymize_text(text, rules)
        self.assertEqual(anon, "The [ANIMAL] sat in category and bobcat was scattered.")

        # Deanonymize back
        deanon = deanonymize_text(anon, rules)
        self.assertEqual(deanon, text)

    def test_02_plaintext_symbols_and_punctuation(self):
        """TEST-02: Plaintext rules with symbols (e.g. '$100', 'user@domain.com') match cleanly."""
        rules = [
            {"search": "$100", "replace": "[PRICE]", "case_sensitive": False, "is_regex": False},
            {"search": "user@acme.corp", "replace": "[EMAIL]", "case_sensitive": False, "is_regex": False},
        ]
        text = "Please send $100 to user@acme.corp today. Note that $1000 is too much."
        anon = anonymize_text(text, rules)
        self.assertEqual(anon, "Please send [PRICE] to [EMAIL] today. Note that $1000 is too much.")

        deanon = deanonymize_text(anon, rules)
        self.assertEqual(deanon, text)

    def test_03_custom_regex_mode(self):
        """TEST-03: is_regex=True supports arbitrary regex patterns without forced \b wrapping."""
        rules = [
            {"search": r"\b\d{4}-\d{4}-\d{4}\b", "replace": "[CARD_NUM]", "case_sensitive": False, "is_regex": True}
        ]
        text = "My card is 1234-5678-9012, while 12-34 is not a card."
        anon = anonymize_text(text, rules)
        self.assertEqual(anon, "My card is [CARD_NUM], while 12-34 is not a card.")

        # Deanonymize replaces placeholder back
        deanon = deanonymize_text(anon, [{"search": "1234-5678-9012", "replace": "[CARD_NUM]"}])
        self.assertEqual(deanon, "My card is 1234-5678-9012, while 12-34 is not a card.")

    def test_04_case_sensitivity_toggles(self):
        """TEST-04: case_sensitive=False matches any case; case_sensitive=True requires exact case."""
        rules_insensitive = [
            {"search": "SecretCode", "replace": "[CODE]", "case_sensitive": False, "is_regex": False}
        ]
        text = "secretcode, SECRETCODE, and SecretCode."
        self.assertEqual(anonymize_text(text, rules_insensitive), "[CODE], [CODE], and [CODE].")

        rules_sensitive = [
            {"search": "SecretCode", "replace": "[CODE]", "case_sensitive": True, "is_regex": False}
        ]
        self.assertEqual(anonymize_text(text, rules_sensitive), "secretcode, SECRETCODE, and [CODE].")

    def test_05_rule_collision_priority(self):
        """TEST-05: Longer search phrases take precedence over shorter substrings."""
        rules = [
            {"search": "Ivan", "replace": "[FIRST_NAME]", "case_sensitive": False, "is_regex": False},
            {"search": "Ivan Ivanov", "replace": "[FULL_NAME]", "case_sensitive": False, "is_regex": False},
        ]
        text = "Contact Ivan Ivanov and Ivan separately."
        anon = anonymize_text(text, rules)
        self.assertEqual(anon, "Contact [FULL_NAME] and [FIRST_NAME] separately.")

        deanon = deanonymize_text(anon, rules)
        self.assertEqual(deanon, text)

    def test_06_streaming_chunk_boundary_splitting(self):
        """TEST-06: StreamingDeanonymizer buffering across 2, 3, or 4 split chunks with 0 placeholder leaks."""
        rules = [
            {"search": "Ivan Ivanov", "replace": "[CLIENT_NAME]", "case_sensitive": False, "is_regex": False}
        ]
        deanonymizer = StreamingDeanonymizer(rules)

        # Token stream where [CLIENT_NAME] is split into ["[CL", "IENT", "_NA", "ME]"]
        chunks = [
            "Hello, ",
            "[CL",
            "IENT",
            "_NA",
            "ME]",
            "! How are you?"
        ]

        emitted = []
        for chunk in chunks:
            out = deanonymizer.feed(chunk)
            emitted.append(out)

        # Chunks 2, 3, 4 should buffer and emit empty string until full match on chunk 5
        self.assertEqual(emitted[0], "Hello, ")
        self.assertEqual(emitted[1], "")  # '[CL' buffered
        self.assertEqual(emitted[2], "")  # '[CLIENT' buffered
        self.assertEqual(emitted[3], "")  # '[CLIENT_NA' buffered
        self.assertEqual(emitted[4], "Ivan Ivanov")  # '[CLIENT_NAME]' completed and replaced!
        self.assertEqual(emitted[5], "! How are you?")

        final_out = deanonymizer.flush(final=True)
        self.assertEqual(final_out, "")

        assembled = "".join(emitted) + final_out
        self.assertEqual(assembled, "Hello, Ivan Ivanov! How are you?")
        self.assertNotIn("[CLIENT_NAME]", assembled)

    def test_07_streaming_forced_flush_on_uncompleted_prefix(self):
        """TEST-07: Incomplete prefix at stream end is flushed cleanly without character loss."""
        rules = [
            {"search": "Ivan Ivanov", "replace": "[CLIENT_NAME]", "case_sensitive": False, "is_regex": False}
        ]
        deanonymizer = StreamingDeanonymizer(rules)

        out1 = deanonymizer.feed("The value is [CLI")
        self.assertEqual(out1, "The value is ")
        self.assertEqual(deanonymizer.buffer, "[CLI")

        # Stream abruptly ends without completing placeholder
        flushed = deanonymizer.flush(final=True)
        self.assertEqual(flushed, "[CLI")
        self.assertEqual(deanonymizer.buffer, "")

    def test_08_streaming_zero_delay_latency_benchmark(self):
        """TEST-08: Long response without placeholders emits each chunk immediately with 0 buffering lag."""
        rules = [
            {"search": "Confidential", "replace": "[REDACTED]", "case_sensitive": False, "is_regex": False}
        ]
        deanonymizer = StreamingDeanonymizer(rules)

        # 100 consecutive chunks of regular prose
        words = ["This", " is", " a", " normal", " sentence", " streamed", " word", " by", " word", "."] * 10

        for w in words:
            out = deanonymizer.feed(w)
            # Must emit immediately on each step
            self.assertEqual(out, w)
            self.assertEqual(deanonymizer.buffer, "")

        self.assertEqual(deanonymizer.flush(final=True), "")

    def test_09_async_chat_solo_integration(self):
        """TEST-09: async_chat_solo executes without NameError in streaming and non-streaming modes."""
        from api.db.services.dialog_service import async_chat_solo

        mock_dialog = MagicMock()
        mock_dialog.tenant_id = "tenant_test_123"
        mock_dialog.llm_id = "test_model"
        mock_dialog.llm_setting = {}
        mock_dialog.kb_ids = []
        mock_dialog.prompt_config = {
            "system": "You are a helpful assistant.",
            "sensitive_data_replacement": {
                "enabled": True,
                "rules": [
                    {"search": "MySecret", "replace": "[SECRET_PLACEHOLDER]", "case_sensitive": False, "is_regex": False}
                ]
            }
        }

        messages = [
            {"role": "user", "content": "Tell me about MySecret please."}
        ]

        async def _run_solo_test():
            with patch("api.db.services.dialog_service.get_model_type_by_name", return_value=["chat"]), \
                 patch("api.db.services.dialog_service.get_model_config_from_provider_instance", return_value={"model_type": "chat", "llm_factory": "openai"}), \
                 patch("api.db.services.dialog_service.LLMBundle") as mock_bundle_cls:

                # Setup mock LLMBundle stream generator
                mock_bundle = MagicMock()
                mock_bundle.trace_context = {}

                async def _mock_stream(*args, **kwargs):
                    yield "Response for [SECRET_"
                    yield "PLACEHOLDER] is done."

                async def _mock_chat(*args, **kwargs):
                    return "Non-stream response for [SECRET_PLACEHOLDER]."

                mock_bundle.async_chat_streamly_delta = _mock_stream
                mock_bundle.async_chat = AsyncMock(side_effect=_mock_chat)
                mock_bundle_cls.return_value = mock_bundle

                # 1. Test Streaming mode
                streamed_deltas = []
                async for ans in async_chat_solo(mock_dialog, messages, stream=True):
                    if ans.get("answer"):
                        streamed_deltas.append(ans["answer"])

                full_stream_text = "".join(streamed_deltas)
                self.assertIn("MySecret", full_stream_text)
                self.assertNotIn("[SECRET_PLACEHOLDER]", full_stream_text)

                # 2. Test Non-streaming mode
                non_stream_results = []
                async for ans in async_chat_solo(mock_dialog, messages, stream=False):
                    non_stream_results.append(ans)

                self.assertEqual(len(non_stream_results), 1)
                self.assertIn("MySecret", non_stream_results[0]["answer"])
                self.assertNotIn("[SECRET_PLACEHOLDER]", non_stream_results[0]["answer"])

        asyncio.run(_run_solo_test())

    def test_10_async_chat_kb_parity_integration(self):
        """TEST-10: async_chat with knowledge base retrieval maintains parity with StreamingDeanonymizer."""
        from api.db.services.dialog_service import async_chat

        mock_dialog = MagicMock()
        mock_dialog.tenant_id = "tenant_test_456"
        mock_dialog.llm_id = "test_model"
        mock_dialog.llm_setting = {}
        mock_dialog.kb_ids = ["kb_123"]
        mock_dialog.rerank_id = None
        mock_dialog.prompt_config = {
            "system": "You are a helpful assistant with KB. {knowledge}",
            "parameters": [{"key": "knowledge", "optional": False}],
            "sensitive_data_replacement": {
                "enabled": True,
                "rules": [
                    {"search": "ProjectOmega", "replace": "[OMEGA_CODE]", "case_sensitive": False, "is_regex": False}
                ]
            }
        }

        messages = [
            {"role": "user", "content": "What is ProjectOmega?"}
        ]

        async def _run_kb_test():
            mock_retriever = MagicMock()
            mock_retriever.retrieval = MagicMock(return_value={"chunks": [], "doc_aggs": [], "total": 0})

            with patch("api.db.services.dialog_service.get_model_type_by_name", return_value=["chat"]), \
                 patch("api.db.services.dialog_service.get_model_config_from_provider_instance", return_value={"model_type": "chat", "llm_factory": "openai", "llm_name": "test_model"}), \
                 patch("api.db.services.dialog_service.get_models") as mock_get_models, \
                 patch("api.db.services.dialog_service.KnowledgebaseService.get_field_map", return_value={}), \
                 patch("api.db.services.dialog_service.KnowledgebaseService.get_by_ids", return_value=[]), \
                 patch("common.settings.retriever", mock_retriever), \
                 patch("api.db.services.dialog_service.TenantLangfuseService.filter_by_tenant", return_value=None):

                mock_chat_mdl = MagicMock()
                async def _mock_stream(*args, **kwargs):
                    yield "Details regarding [OMEGA_"
                    yield "CODE] found in knowledge."

                mock_chat_mdl.async_chat_streamly_delta = _mock_stream
                mock_get_models.return_value = ([], None, None, mock_chat_mdl, None)

                streamed_deltas = []
                async for ans in async_chat(mock_dialog, messages, stream=True):
                    if ans.get("answer"):
                        streamed_deltas.append(ans["answer"])

                full_text = "".join(streamed_deltas)
                self.assertIn("ProjectOmega", full_text)
                self.assertNotIn("[OMEGA_CODE]", full_text)

        asyncio.run(_run_kb_test())

    def test_11_multiturn_conversation_db_persistence(self):
        """TEST-11: Conversation DB persistence stores original Word A for user & restored Word A for assistant."""
        from api.db.services.conversation_service import structure_answer

        class MockConversation:
            def __init__(self):
                self.id = "conv_123"
                self.message = [
                    # User question saved with original Word A
                    {"role": "user", "content": "My name is John Doe and PIN is 4321.", "id": "msg_user_1"}
                ]
                self.reference = []

        conv = MockConversation()

        # Simulate streaming delta event containing deanonymized text (Word A)
        ans_chunk_1 = {"answer": "Hello John Doe, ", "reference": {}, "final": False}
        structure_answer(conv, ans_chunk_1, "msg_asst_1", "conv_123")

        self.assertEqual(len(conv.message), 2)
        self.assertEqual(conv.message[-1]["role"], "assistant")
        self.assertEqual(conv.message[-1]["content"], "Hello John Doe, ")

        # Simulate second chunk
        ans_chunk_2 = {"answer": "your PIN 4321 is safe.", "reference": {}, "final": False}
        structure_answer(conv, ans_chunk_2, "msg_asst_1", "conv_123")
        self.assertEqual(conv.message[-1]["content"], "Hello John Doe, your PIN 4321 is safe.")

        # Simulate final answer completion
        ans_final = {"answer": "Hello John Doe, your PIN 4321 is safe.", "reference": {}, "final": True}
        structure_answer(conv, ans_final, "msg_asst_1", "conv_123")

        # Verify DB representation contains Word A throughout
        self.assertIn("John Doe", conv.message[0]["content"])
        self.assertIn("John Doe", conv.message[1]["content"])
        self.assertIn("4321", conv.message[1]["content"])


if __name__ == "__main__":
    unittest.main()
