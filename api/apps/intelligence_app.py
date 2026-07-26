#
#  Copyright 2026 The InfiniFlow Authors. All Rights Reserved.
#
import logging
from quart import Blueprint, request
from api.apps import login_required, current_user
from api.db.services.intelligence_service import (
    KnowledgeEntityService,
    KnowledgeRelationService,
    EnterpriseSearchService,
    ExecutiveDigestService,
    ExpertiseService,
    SummaryService,
)
from api.utils.api_utils import get_json_result, server_error_response
from common.constants import RetCode

# manager is injected dynamically by api.apps.register_page() before this module is exec'd.
try:
    manager
except NameError:
    manager = Blueprint("intelligence", __name__)


@manager.route("/graph/full", methods=["GET"])
@login_required
async def get_full_graph():
    """Retrieve full force-directed knowledge graph for tenant."""
    tenant_id = getattr(current_user, "tenant_id", None) or getattr(current_user, "id", "")
    try:
        graph_data = KnowledgeRelationService.get_full_graph(tenant_id)
        return get_json_result(data=graph_data)
    except Exception as e:
        return server_error_response(e)


@manager.route("/graph/query", methods=["POST"])
@login_required
async def query_knowledge_graph():
    """Query connected nodes and edges in the knowledge graph for a given entity."""
    tenant_id = getattr(current_user, "tenant_id", None) or getattr(current_user, "id", "")
    req = await request.get_json() or {}
    entity_id = req.get("entity_id")
    depth = req.get("depth", 2)

    if not entity_id:
        return get_json_result(data={"nodes": [], "edges": []})

    try:
        graph_data = KnowledgeRelationService.get_graph_neighborhood(tenant_id, entity_id, max_depth=depth)
        return get_json_result(data=graph_data)
    except Exception as e:
        return server_error_response(e)


@manager.route("/search", methods=["POST"])
@login_required
async def search_enterprise():
    """Hybrid AI Natural Language Search ('Google for Enterprise')."""
    tenant_id = getattr(current_user, "tenant_id", None) or getattr(current_user, "id", "")
    req = await request.get_json() or {}
    query_text = req.get("query", "")

    try:
        search_results = EnterpriseSearchService.search(tenant_id, query_text)
        return get_json_result(data=search_results)
    except Exception as e:
        return server_error_response(e)


@manager.route("/dashboard/executive", methods=["GET"])
@login_required
async def get_executive_dashboard():
    """Retrieve Executive Intelligence Digest stats."""
    tenant_id = getattr(current_user, "tenant_id", None) or getattr(current_user, "id", "")
    try:
        digest_data = ExecutiveDigestService.get_executive_digest(tenant_id)
        return get_json_result(data=digest_data)
    except Exception as e:
        return server_error_response(e)


@manager.route("/experts/search", methods=["GET"])
@login_required
async def search_experts():
    """Search organization expertise based on topic and minimum confidence score."""
    tenant_id = getattr(current_user, "tenant_id", None) or getattr(current_user, "id", "")
    topic = request.args.get("topic", "")
    min_confidence = float(request.args.get("min_confidence", 0.5))

    try:
        experts = ExpertiseService.find_experts_by_topic(tenant_id, topic, min_confidence)
        return get_json_result(data={"topic": topic, "experts": experts})
    except Exception as e:
        return server_error_response(e)


@manager.route("/dashboard/stats", methods=["GET"])
@login_required
async def get_dashboard_stats():
    """Retrieve enterprise intelligence dashboard statistics."""
    tenant_id = getattr(current_user, "tenant_id", None) or getattr(current_user, "id", "")
    try:
        stats = KnowledgeEntityService.get_dashboard_aggregations(tenant_id)
        return get_json_result(data=stats)
    except Exception as e:
        return server_error_response(e)


@manager.route("/summaries/list", methods=["GET"])
@login_required
async def list_summaries():
    """Retrieve list of generated enterprise summaries."""
    tenant_id = getattr(current_user, "tenant_id", None) or getattr(current_user, "id", "")
    summary_type = request.args.get("summary_type")
    try:
        kwargs = {"tenant_id": tenant_id}
        if summary_type:
            kwargs["summary_type"] = summary_type
        summaries = SummaryService.query(**kwargs)
        return get_json_result(data=[s.to_dict() for s in summaries])
    except Exception as e:
        return server_error_response(e)
