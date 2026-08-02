import asyncio
import io
import logging
import uuid
import aiohttp
from crawler.crawler import AsyncWebCrawler
from crawler.progress import JobProgressTracker
from crawler.metadata import MetadataBuilder
from api.db.services.document_service import DocumentService
from api.db.services.knowledgebase_service import KnowledgebaseService
from api.db.db_models import Document, ParserType
from common.constants import TaskStatus

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

            # Process crawled pages and turn them into RAGFlow Documents
            for idx, page in enumerate(crawled_pages):
                if self.tracker.status == "cancelled":
                    break

                doc_name = f"{page['title'] or page['url']}.md"
                md_content = page["markdown"]
                if not md_content.strip():
                    continue

                # Create RAGFlow Document entry
                doc_id = str(uuid.uuid4().hex)
                doc = {
                    "id": doc_id,
                    "kb_id": self.kb_id,
                    "parser_id": ParserType.NAIVE.value,
                    "pipeline_id": None,
                    "name": doc_name[:255],
                    "type": "web",
                    "location": page["url"],
                    "size": len(md_content.encode('utf-8')),
                    "status": TaskStatus.RUNNING.value,
                    "progress": 0.0,
                    "created_by": self.tenant_id,
                    "process_begin_at": DocumentService.date_now(),
                }
                
                DocumentService.insert(doc)
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
