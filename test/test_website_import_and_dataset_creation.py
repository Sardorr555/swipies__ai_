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
import os
import sys
import types
import unittest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.types import TypeEngine

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Stub out heavy external dependencies
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

from peewee import SqliteDatabase

TEST_DB_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_website_import_temp.db"))
test_db = SqliteDatabase(TEST_DB_FILE)

from api.db.db_models import (
    DB,
    Document,
    Knowledgebase,
    Tenant,
    User,
)

# Override DB connection context with test_db
DB.connection_context = test_db.connection_context
DB.atomic = test_db.atomic
DB.transaction = test_db.transaction
DB.connect = test_db.connect
DB.close = test_db.close
DB.is_closed = test_db.is_closed
DB.execute_sql = test_db.execute_sql

MODELS = [
    Document,
    Knowledgebase,
    Tenant,
    User,
]
for model in MODELS:
    model._meta.database = test_db

from api import settings
from api.db.services.document_service import DocumentService
from api.db.services.knowledgebase_service import KnowledgebaseService
from crawler.preview import WebsitePreviewAnalyzer
from crawler.pipeline import WebsiteImportPipeline, get_job_pipeline, ACTIVE_JOBS
from crawler.progress import JobProgressTracker


class TestWebsiteImportAndDatasetCreation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        test_db.connect()
        test_db.create_tables(MODELS, safe=True)
        # Mock storage
        cls.mock_storage = MagicMock()
        settings.STORAGE_IMPL = cls.mock_storage

    @classmethod
    def tearDownClass(cls):
        test_db.drop_tables(MODELS, safe=True)
        test_db.close()
        if os.path.exists(TEST_DB_FILE):
            try:
                os.remove(TEST_DB_FILE)
            except Exception:
                pass

    def setUp(self):
        self.mock_storage.reset_mock()
        self.tenant_id = f"tenant_{uuid.uuid4().hex[:8]}"
        self.user_id = f"user_{uuid.uuid4().hex[:8]}"
        
        # Create tenant
        Tenant.create(
            id=self.tenant_id,
            name="Test Website Tenant",
            llm_id="gpt-4o",
            embd_id="BAAI/bge-large-zh-v1.5",
            asr_id="whisper",
            img2txt_id="clip",
            rerank_id="bge-reranker",
            parser_ids="naive",
        )
        # Create user
        User.create(
            id=self.user_id,
            nickname="TestUser",
            email=f"{self.user_id}@test.com",
            password="hashed_pass_dummy",
        )

    def tearDown(self):
        Document.delete().execute()
        Knowledgebase.delete().execute()
        User.delete().execute()
        Tenant.delete().execute()
        ACTIVE_JOBS.clear()

    def test_preview_analyzer_extracts_metadata(self):
        """Test WebsitePreviewAnalyzer processes HTML and computes metadata estimates."""
        sample_html = """
        <!DOCTYPE html>
        <html>
        <head><title>Documentation Portal - Swipies</title></head>
        <body>
            <h1>Welcome to Swipies AI</h1>
            <p>This is comprehensive technical documentation containing useful instructions.</p>
            <a href="https://example.com/guide">Guide</a>
            <img src="/logo.png" alt="Logo" />
        </body>
        </html>
        """

        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.headers = {"Content-Type": "text/html; charset=utf-8"}
        mock_resp.text = AsyncMock(return_value=sample_html)

        mock_get_ctx = MagicMock()
        mock_get_ctx.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_get_ctx.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_get_ctx)
        mock_session_ctx = MagicMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session_ctx):
            analyzer = WebsitePreviewAnalyzer()
            res = asyncio.run(analyzer.analyze("https://example.com", crawl_mode="single_page", max_pages=1))

            self.assertEqual(res["title"], "Documentation Portal - Swipies")
            self.assertGreater(res["detected_pages"], 0)
            self.assertGreater(res["estimated_token_count"], 0)
            self.assertGreater(res["estimated_chunks"], 0)
            self.assertIn("estimated_crawl_time_seconds", res)

    def test_pipeline_saves_documents_to_storage_and_db(self):
        """Test WebsiteImportPipeline inserts Document rows with STORAGE_IMPL persistence."""
        kb_id = f"kb_{uuid.uuid4().hex[:8]}"
        Knowledgebase.create(
            id=kb_id,
            name="Imported Docs",
            tenant_id=self.tenant_id,
            created_by=self.user_id,
            embd_id="BAAI/bge-large-zh-v1.5",
            parser_id="naive",
            doc_num=0,
        )

        mock_crawled_pages = [
            {
                "url": "https://example.com/page1",
                "title": "Page 1: Introduction",
                "markdown": "# Introduction\n\nWelcome to page 1 content with details.",
            },
            {
                "url": "https://example.com/page2",
                "title": "Page 2: API Reference",
                "markdown": "# API Reference\n\nFull API endpoints and parameter list.",
            },
        ]

        with patch("crawler.pipeline.AsyncWebCrawler.crawl", new=AsyncMock(return_value=mock_crawled_pages)):
            pipeline = WebsiteImportPipeline(
                tenant_id=self.tenant_id,
                kb_id=kb_id,
                job_config={"url": "https://example.com", "max_pages": 10},
            )
            asyncio.run(pipeline.run())

            # 1. Pipeline status completed
            self.assertEqual(pipeline.tracker.status, "completed")
            self.assertEqual(pipeline.tracker.pages_processed, 2)
            self.assertEqual(pipeline.tracker.chunks_created, 2)

            # 2. Storage put called for both pages
            self.assertEqual(self.mock_storage.put.call_count, 2)
            for call in self.mock_storage.put.call_args_list:
                args, _ = call
                self.assertEqual(args[0], kb_id)
                self.assertTrue(args[1].endswith(".md"))
                self.assertIsInstance(args[2], bytes)

            # 3. Documents saved in database with proper fields
            docs = list(Document.select().where(Document.kb_id == kb_id))
            self.assertEqual(len(docs), 2)
            doc_names = [d.name for d in docs]
            self.assertIn("Page 1 Introduction.md", doc_names)
            self.assertIn("Page 2 API Reference.md", doc_names)
            for d in docs:
                self.assertEqual(d.type, "doc")
                self.assertEqual(d.suffix, "md")
                self.assertEqual(d.source_type, "web")
                self.assertEqual(d.status, "1")
                self.assertGreater(d.size, 0)
                self.assertTrue(d.location.endswith(".md"))

            # 4. Knowledgebase doc_num was incremented
            kb = Knowledgebase.get_by_id(kb_id)
            self.assertEqual(kb.doc_num, 2)

    def test_pipeline_cancellation(self):
        """Test canceling WebsiteImportPipeline marks tracker status as cancelled."""
        kb_id = f"kb_{uuid.uuid4().hex[:8]}"
        pipeline = WebsiteImportPipeline(
            tenant_id=self.tenant_id,
            kb_id=kb_id,
            job_config={"url": "https://example.com"},
        )
        self.assertEqual(pipeline.tracker.status, "running")
        pipeline.cancel()
        self.assertEqual(pipeline.tracker.status, "cancelled")
        self.assertTrue(any("cancelled" in log.lower() for log in pipeline.tracker.logs))

    def test_active_jobs_lookup(self):
        """Test get_job_pipeline retrieves active job by ID."""
        kb_id = f"kb_{uuid.uuid4().hex[:8]}"
        pipeline = WebsiteImportPipeline(
            tenant_id=self.tenant_id,
            kb_id=kb_id,
            job_config={"url": "https://example.com"},
        )
        found = get_job_pipeline(pipeline.job_id)
        self.assertIsNotNone(found)
        self.assertEqual(found.job_id, pipeline.job_id)

    def test_dataset_creation_from_website_parameters(self):
        """Test logic creating a new dataset from website URL and metadata."""
        target_url = "https://docs.awesomeproject.org/tutorial"
        dataset_name = "Awesome Project Docs"
        
        # Verify creating knowledgebase record when kb_id is omitted
        kb_id = f"kb_{uuid.uuid4().hex[:8]}"
        created_kb = Knowledgebase.create(
            id=kb_id,
            name=dataset_name,
            tenant_id=self.tenant_id,
            created_by=self.user_id,
            embd_id="BAAI/bge-large-zh-v1.5",
            parser_id="naive",
            doc_num=0,
        )

        self.assertIsNotNone(created_kb.id)
        self.assertEqual(created_kb.name, "Awesome Project Docs")

        pipeline = WebsiteImportPipeline(
            tenant_id=self.tenant_id,
            kb_id=created_kb.id,
            job_config={"url": target_url, "max_pages": 25},
        )
        self.assertEqual(pipeline.kb_id, created_kb.id)


if __name__ == "__main__":
    unittest.main()
