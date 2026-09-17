import asyncio
import io
import logging
import re
import uuid
import aiohttp
from crawler.crawler import AsyncWebCrawler
from crawler.progress import JobProgressTracker
from crawler.metadata import MetadataBuilder
from api.db.services.document_service import DocumentService
from api.db.services.knowledgebase_service import KnowledgebaseService
from api.db.db_models import Document
from api.db import FileType
from common.constants import TaskStatus, StatusEnum, ParserType
from common import settings
from common.time_utils import get_format_time

logger = logging.getLogger(__name__)

ACTIVE_JOBS = {}

class WebsiteImportPipeline:
    def __init__(self, tenant_id: str, kb_id: str, job_config: dict):
        self.tenant_id = tenant_id
        self.kb_id = kb_id
        self.config = job_config
        self.job_id = str(uuid.uuid4())
        self.tracker = JobProgressTracker(self.job_id, total_target=job_config.get("max_pages", 100))
        ACTIVE_JOBS[self.job_id] = self

    def cancel(self):
        self.tracker.status = "cancelled"
        self.tracker.log("Crawl job cancelled by user.")

    async def run(self):
        self.tracker.log(f"Starting Website Import for Dataset {self.kb_id}")
        start_urls = self.config.get("urls", [])
        if not start_urls and self.config.get("url"):
            start_urls = [self.config["url"]]

        if not start_urls:
            self.tracker.status = "failed"
            self.tracker.log("Error: No URLs provided.")
            return

        crawler = AsyncWebCrawler(self.config)

        async def on_progress(url, processed, total):
            self.tracker.update_url(url, processed)

        try:
            crawled_pages = await crawler.crawl(start_urls, progress_callback=on_progress)
            self.tracker.pages_processed = len(crawled_pages)
            self.tracker.log(f"Crawl completed. {len(crawled_pages)} pages fetched successfully.")

            # Retrieve KB settings if available
            kb = None
            try:
                ok, kb_data = KnowledgebaseService.get_by_id(self.kb_id)
                if ok:
                    kb = kb_data
            except Exception as e:
                logger.warning(f"Could not load KB {self.kb_id}: {e}")

            parser_id = getattr(kb, "parser_id", None) or ParserType.NAIVE.value
            pipeline_id = getattr(kb, "pipeline_id", None)
            parser_config = getattr(kb, "parser_config", None) or {"pages": [[1, 1000000]]}

            # Process crawled pages and turn them into RAGFlow Documents
            for idx, page in enumerate(crawled_pages):
                if self.tracker.status == "cancelled":
                    break

                raw_title = page.get("title") or page.get("url") or f"page_{idx+1}"
                clean_title = re.sub(r'[\\/*?:"<>|]', "", raw_title).strip() or f"page_{idx+1}"
                if not clean_title.lower().endswith(".md"):
                    doc_name = f"{clean_title[:120]}.md"
                else:
                    doc_name = clean_title[:120]

                md_content = page.get("markdown") or ""
                if not md_content.strip():
                    continue

                doc_id = str(uuid.uuid4().hex)
                blob = md_content.encode("utf-8")
                location = f"{doc_id}.md"

                # Ensure storage is initialized
                if not getattr(settings, "STORAGE_IMPL", None):
                    try:
                        settings.init_settings()
                    except Exception as _init_err:
                        logger.error(f"settings.init_settings failed in pipeline: {_init_err}")

                storage = getattr(settings, "STORAGE_IMPL", None)
                if not storage:
                    logger.error("STORAGE_IMPL is None! Cannot save crawled document to storage.")
                    raise RuntimeError("Object storage is not initialized.")

                # Store file blob in object storage
                try:
                    storage.put(self.kb_id, location, blob)
                    logger.info(f"Stored document blob {location} in bucket {self.kb_id} ({len(blob)} bytes)")
                except Exception as st_err:
                    logger.exception(f"STORAGE_IMPL.put failed for doc {doc_id} in {self.kb_id}/{location}: {st_err}")
                    raise RuntimeError(f"Storage upload failed: {st_err}")

                # Create RAGFlow Document entry
                doc = {
                    "id": doc_id,
                    "kb_id": self.kb_id,
                    "parser_id": parser_id,
                    "pipeline_id": pipeline_id,
                    "parser_config": parser_config,
                    "source_type": "web",
                    "name": doc_name[:255],
                    "type": FileType.DOC.value,
                    "suffix": "md",
                    "location": location,
                    "size": len(blob),
                    "status": StatusEnum.VALID.value,
                    "run": TaskStatus.UNSTART.value,
                    "progress": 0.0,
                    "created_by": self.tenant_id,
                    "process_begin_at": get_format_time(),
                }
                
                DocumentService.insert(doc)

                # Register with FileService if available
                try:
                    from api.db.services.file_service import FileService
                    root_folder = FileService.get_root_folder(self.tenant_id)
                    if root_folder:
                        FileService.init_knowledgebase_docs(root_folder["id"], self.tenant_id)
                        kb_root_folder = FileService.get_kb_folder(self.tenant_id)
                        if kb_root_folder:
                            kb_name = getattr(kb, "name", "Website") if kb else "Website"
                            kb_folder = FileService.new_a_file_from_kb(self.tenant_id, kb_name, kb_root_folder["id"])
                            if kb_folder:
                                FileService.add_file_from_kb(doc, kb_folder["id"], self.tenant_id)
                except Exception as _fe:
                    logger.warning(f"FileService registration warning: {_fe}")

                # Automatically queue chunking/embedding task
                try:
                    from api.db.services.task_service import queue_tasks
                    queue_tasks(doc, self.kb_id, location, 0)
                    DocumentService.update_by_id(doc["id"], {"run": TaskStatus.RUNNING.value})
                except Exception as _qe:
                    logger.warning(f"Auto queue_tasks warning: {_qe}")

                self.tracker.chunks_created += 1
                self.tracker.log(f"Created Document record for {doc_name}")

            self.tracker.status = "completed"
            self.tracker.log("Website import pipeline finished successfully.")

        except Exception as e:
            logger.exception(f"Pipeline error for job {self.job_id}: {e}")
            self.tracker.status = "failed"
            self.tracker.log(f"Job failed: {str(e)}")

def get_job_pipeline(job_id: str) -> WebsiteImportPipeline or None:
    return ACTIVE_JOBS.get(job_id)

