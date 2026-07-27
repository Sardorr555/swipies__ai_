#
#  Copyright 2026 The InfiniFlow Authors. All Rights Reserved.
#
import logging
from quart import request
from api.apps import login_required, current_user
from api.db.services.intelligence_service import (
    KnowledgeEntityService,
    KnowledgeRelationService,
    EnterpriseSearchService,
    ExecutiveDigestService,
    ProactiveIntelligenceService,
    ExpertiseService,
    SummaryService,
)
from api.utils.api_utils import get_json_result, server_error_response
from common.constants import RetCode

# manager is injected dynamically by api.apps.register_page() before this module is exec'd.


@manager.route("/intelligence/graph/full", methods=["GET"])  # noqa: F821
@login_required
async def get_full_graph():
    """Retrieve full force-directed knowledge graph across all platform users."""
    is_global = request.args.get("global", "true").lower() == "true"
    tenant_id = None if is_global else (getattr(current_user, "tenant_id", None) or getattr(current_user, "id", ""))
    try:
        graph_data = KnowledgeRelationService.get_full_graph(tenant_id)
        return get_json_result(data=graph_data)
    except Exception as e:
        return server_error_response(e)


@manager.route("/intelligence/graph/query", methods=["POST"])  # noqa: F821
@login_required
async def query_knowledge_graph():
    """Query connected nodes and edges in the knowledge graph for a given entity."""
    is_global = request.args.get("global", "true").lower() == "true"
    tenant_id = None if is_global else (getattr(current_user, "tenant_id", None) or getattr(current_user, "id", ""))
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


@manager.route("/intelligence/search", methods=["POST"])  # noqa: F821
@login_required
async def search_enterprise():
    """Hybrid AI Natural Language Search across all platform chats ('Google for Enterprise')."""
    is_global = request.args.get("global", "true").lower() == "true"
    tenant_id = None if is_global else (getattr(current_user, "tenant_id", None) or getattr(current_user, "id", ""))
    req = await request.get_json() or {}
    query_text = req.get("query", "")

    try:
        search_results = EnterpriseSearchService.search(tenant_id, query_text)
        return get_json_result(data=search_results)
    except Exception as e:
        return server_error_response(e)


@manager.route("/intelligence/dashboard/executive", methods=["GET"])  # noqa: F821
@login_required
async def get_executive_dashboard():
    """Retrieve Executive Intelligence Digest stats for all platform users."""
    is_global = request.args.get("global", "true").lower() == "true"
    tenant_id = None if is_global else (getattr(current_user, "tenant_id", None) or getattr(current_user, "id", ""))
    try:
        digest_data = ExecutiveDigestService.get_executive_digest(tenant_id)
        return get_json_result(data=digest_data)
    except Exception as e:
        return server_error_response(e)


@manager.route("/intelligence/analytics/sentiment", methods=["GET"])  # noqa: F821
@login_required
async def get_sentiment_analytics():
    """Retrieve Sentiment & Frustration Index metrics."""
    is_global = request.args.get("global", "true").lower() == "true"
    tenant_id = None if is_global else (getattr(current_user, "tenant_id", None) or getattr(current_user, "id", ""))
    try:
        sentiment_data = ProactiveIntelligenceService.get_sentiment_analytics(tenant_id)
        return get_json_result(data=sentiment_data)
    except Exception as e:
        return server_error_response(e)


@manager.route("/intelligence/analytics/roi", methods=["GET"])  # noqa: F821
@login_required
async def get_roi_analytics():
    """Retrieve ROI & Hours Saved metrics and Single Point of Failure (SPOF) risks."""
    is_global = request.args.get("global", "true").lower() == "true"
    tenant_id = None if is_global else (getattr(current_user, "tenant_id", None) or getattr(current_user, "id", ""))
    try:
        roi_data = ProactiveIntelligenceService.get_roi_analytics(tenant_id)
        return get_json_result(data=roi_data)
    except Exception as e:
        return server_error_response(e)


@manager.route("/intelligence/timeline", methods=["GET"])  # noqa: F821
@login_required
async def get_decision_timeline():
    """Retrieve chronological decision evolution timeline."""
    is_global = request.args.get("global", "true").lower() == "true"
    tenant_id = None if is_global else (getattr(current_user, "tenant_id", None) or getattr(current_user, "id", ""))
    try:
        timeline_data = ProactiveIntelligenceService.get_decision_timeline(tenant_id)
        return get_json_result(data=timeline_data)
    except Exception as e:
        return server_error_response(e)


@manager.route("/intelligence/faq/generate", methods=["POST"])  # noqa: F821
@login_required
async def generate_faq_article():
    """Generate 1-click Knowledge Base FAQ article from recurring topics."""
    is_global = request.args.get("global", "true").lower() == "true"
    tenant_id = None if is_global else (getattr(current_user, "tenant_id", None) or getattr(current_user, "id", ""))
    req = await request.get_json() or {}
    topic = req.get("topic", "")
    try:
        faq_data = ProactiveIntelligenceService.generate_faq_article(tenant_id, topic)
        return get_json_result(data=faq_data)
    except Exception as e:
        return server_error_response(e)


@manager.route("/intelligence/experts/search", methods=["GET"])  # noqa: F821
@login_required
async def search_experts():
    """Search organization expertise based on topic and minimum confidence score."""
    is_global = request.args.get("global", "true").lower() == "true"
    tenant_id = None if is_global else (getattr(current_user, "tenant_id", None) or getattr(current_user, "id", ""))
    topic = request.args.get("topic", "")
    min_confidence = float(request.args.get("min_confidence", 0.5))

    try:
        experts = ExpertiseService.find_experts_by_topic(tenant_id, topic, min_confidence)
        return get_json_result(data={"topic": topic, "experts": experts})
    except Exception as e:
        return server_error_response(e)


@manager.route("/intelligence/dashboard/stats", methods=["GET"])  # noqa: F821
@login_required
async def get_dashboard_stats():
    """Retrieve enterprise intelligence dashboard statistics."""
    is_global = request.args.get("global", "true").lower() == "true"
    tenant_id = None if is_global else (getattr(current_user, "tenant_id", None) or getattr(current_user, "id", ""))
    try:
        stats = KnowledgeEntityService.get_dashboard_aggregations(tenant_id)
        return get_json_result(data=stats)
    except Exception as e:
        return server_error_response(e)
