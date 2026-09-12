import asyncio
import logging
from quart import request
from api.apps import login_required, current_user
from api.utils.api_utils import get_error_data_result, get_json_result, get_result
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# Ensure repository root is in sys.path so 'crawler' module can be found
root_dir = str(Path(__file__).resolve().parent.parent.parent.parent)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

try:
    from crawler.preview import WebsitePreviewAnalyzer
    from crawler.pipeline import WebsiteImportPipeline, get_job_pipeline, ACTIVE_JOBS
except Exception as _crawler_import_err:
    logger.warning(f"Could not import crawler module: {_crawler_import_err}")
    WebsitePreviewAnalyzer = None
    WebsiteImportPipeline = None
    def get_job_pipeline(job_id):
        return None
    ACTIVE_JOBS = {}

# manager is injected dynamically by api.apps.register_page() before this module is exec'd.

@manager.route("/datasets/import/website/preview", methods=["POST"])  # noqa: F821
@login_required
async def preview_website_import():
    """
    Analyze website preview before import.
    """
    try:
        req = await request.get_json() or {}
        start_url = req.get("url")
        if not start_url:
            return get_error_data_result(message="Missing required parameter: url")

        crawl_mode = req.get("crawl_mode", "website")
        max_pages = req.get("max_pages", 50)
        auth_config = req.get("auth")

        analyzer = WebsitePreviewAnalyzer()
        result = await analyzer.analyze(start_url, crawl_mode=crawl_mode, max_pages=max_pages, auth_config=auth_config)
        return get_json_result(data=result)
    except Exception as e:
        logger.exception(e)
        return get_error_data_result(message=f"Preview analysis failed: {str(e)}")


@manager.route("/datasets/import/website", methods=["POST"])  # noqa: F821
@login_required
async def start_website_import():
    """
    Start a new website import job.
    If kb_id/dataset_id is not provided, automatically creates a new dataset
    based on the website and starts importing pages into it.
    """
    try:
        req = await request.get_json() or {}
        url = req.get("url")
        urls = req.get("urls", [])
        if not url and not urls:
            return get_error_data_result(message="Missing required parameter: url or urls")

        target_url = url or (urls[0] if urls else "")
        tenant_id = getattr(current_user, "tenant_id", None) or getattr(current_user, "id", "system")

        kb_id = req.get("kb_id") or req.get("dataset_id")
        created_dataset_info = None

        if not kb_id:
            # Create a new dataset on-the-fly based on website!
            dataset_name = req.get("dataset_name") or req.get("name")
            if not dataset_name and target_url:
                from urllib.parse import urlparse
                dataset_name = urlparse(target_url).netloc or "Website Dataset"
            elif not dataset_name:
                dataset_name = "Website Dataset"

            from api.apps.services import dataset_api_service
            create_dict = {
                "name": dataset_name,
                "embedding_model": req.get("embedding_model"),
                "parser_id": req.get("parser_id", "naive"),
                "chunk_method": req.get("chunk_method", "naive"),
            }
            success, create_res = await dataset_api_service.create_dataset(tenant_id, create_dict)
            if not success:
                return get_error_data_result(message=f"Failed to create dataset for website: {create_res}")
            
            kb_id = create_res.get("id")
            created_dataset_info = create_res

        pipeline = WebsiteImportPipeline(tenant_id=tenant_id, kb_id=kb_id, job_config=req)
        # Run pipeline in background task
        asyncio.create_task(pipeline.run())

        res_data = {
            "job_id": pipeline.job_id,
            "dataset_id": kb_id,
            "status": "running"
        }
        if created_dataset_info:
            res_data["dataset"] = created_dataset_info
            res_data["dataset_name"] = created_dataset_info.get("name", "")

        return get_json_result(data=res_data)
    except Exception as e:
        logger.exception(e)
        return get_error_data_result(message=f"Failed to start import job: {str(e)}")


@manager.route("/datasets/import/history", methods=["GET"])  # noqa: F821
@login_required
async def get_website_import_history():
    """
    Get history of website import jobs.
    """
    history = [p.tracker.to_dict() for p in ACTIVE_JOBS.values()]
    return get_json_result(data=history)


@manager.route("/datasets/import/<job_id>", methods=["GET"])  # noqa: F821
@login_required
async def get_website_import_status(job_id: str):
    """
    Get live progress and logs for a website import job.
    """
    pipeline = get_job_pipeline(job_id)
    if not pipeline:
        return get_error_data_result(message="Import job not found")
    
    return get_json_result(data=pipeline.tracker.to_dict())


@manager.route("/datasets/import/<job_id>", methods=["DELETE"])  # noqa: F821
@login_required
async def cancel_website_import(job_id: str):
    """
    Cancel an active website import job.
    """
    pipeline = get_job_pipeline(job_id)
    if not pipeline:
        return get_error_data_result(message="Import job not found")
    
    pipeline.cancel()
    return get_json_result(data={"job_id": job_id, "status": "cancelled"})
