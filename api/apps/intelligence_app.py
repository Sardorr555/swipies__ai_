#
#  Copyright 2026 The InfiniFlow Authors. All Rights Reserved.
#
import logging
from quart import Blueprint, request
from api.apps import login_required
from api.db.services.intelligence_service import (
    KnowledgeEntityService,
    KnowledgeRelationService,
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


@manager.route("/graph/query", methods=["POST"])
@login_required
async def query_knowledge_graph(tenant_id):
    """Query connected nodes and edges in the knowledge graph for a given entity."""
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


@manager.route("/experts/search", methods=["GET"])
@login_required
async def search_experts(tenant_id):
    """Search organization expertise based on topic and minimum confidence score."""
    topic = request.args.get("topic", "")
    min_confidence = float(request.args.get("min_confidence", 0.5))

    try:
        experts = ExpertiseService.find_experts_by_topic(tenant_id, topic, min_confidence)
        return get_json_result(data={"topic": topic, "experts": experts})
    except Exception as e:
        return server_error_response(e)


@manager.route("/dashboard/stats", methods=["GET"])
@login_required
async def get_dashboard_stats(tenant_id):
    """Retrieve enterprise intelligence dashboard statistics."""
    try:
        stats = KnowledgeEntityService.get_dashboard_aggregations(tenant_id)
        return get_json_result(data=stats)
    except Exception as e:
        return server_error_response(e)


@manager.route("/summaries/list", methods=["GET"])
@login_required
async def list_summaries(tenant_id):
    """Retrieve list of generated enterprise summaries."""
    summary_type = request.args.get("summary_type")
    try:
        kwargs = {"tenant_id": tenant_id}
        if summary_type:
            kwargs["summary_type"] = summary_type
        summaries = SummaryService.query(**kwargs)
        return get_json_result(data=[s.to_dict() for s in summaries])
    except Exception as e:
        return server_error_response(e)
