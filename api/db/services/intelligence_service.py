#
#  Copyright 2026 The InfiniFlow Authors. All Rights Reserved.
#
import logging
from typing import Dict, Any, List
from peewee import fn
from api.db.db_models import (
    KnowledgeEntity,
    KnowledgeRelation,
    ConversationMetadata,
    ExpertiseProfile,
    SummaryRegistry,
    EILAuditLog,
)
from api.db.services.common_service import CommonService


class KnowledgeEntityService(CommonService):
    model = KnowledgeEntity

    @classmethod
    def get_dashboard_aggregations(cls, tenant_id: str) -> Dict[str, Any]:
        """Retrieves aggregated knowledge stats for enterprise dashboard."""
        try:
            total_entities = cls.model.select().where(cls.model.tenant_id == tenant_id).count()
            total_relations = KnowledgeRelation.select().where(KnowledgeRelation.tenant_id == tenant_id).count()
            total_conversations = ConversationMetadata.select().where(ConversationMetadata.tenant_id == tenant_id).count()

            # Top topics
            convs = ConversationMetadata.select().where(ConversationMetadata.tenant_id == tenant_id).limit(100)
            topic_counts = {}
            for c in convs:
                for t in (c.topics or []):
                    topic_counts[t] = topic_counts.get(t, 0) + 1

            sorted_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:10]

            return {
                "total_knowledge_entities": total_entities,
                "total_relations": total_relations,
                "processed_conversations": total_conversations,
                "top_topics": [{"topic": k, "count": v} for k, v in sorted_topics],
            }
        except Exception as e:
            logging.error(f"[KnowledgeEntityService] Aggregation failed: {e}")
            return {
                "total_knowledge_entities": 0,
                "total_relations": 0,
                "processed_conversations": 0,
                "top_topics": [],
            }


class KnowledgeRelationService(CommonService):
    model = KnowledgeRelation

    @classmethod
    def get_graph_neighborhood(cls, tenant_id: str, entity_id: str, max_depth: int = 2) -> Dict[str, List[Dict[str, Any]]]:
        """Retrieves graph neighborhood (nodes and edges) starting from target entity."""
        nodes_dict = {}
        edges = []

        try:
            # Source relations
            s_rels = cls.model.select().where((cls.model.tenant_id == tenant_id) & (cls.model.src_entity_id == entity_id))
            for r in s_rels:
                edges.append({
                    "id": r.id,
                    "source": r.src_entity_id,
                    "target": r.dst_entity_id,
                    "label": r.predicate,
                    "confidence": r.confidence_score,
                })
                # Add nodes
                for n_id in [r.src_entity_id, r.dst_entity_id]:
                    if n_id not in nodes_dict:
                        ent = KnowledgeEntity.query(id=n_id)
                        if ent:
                            nodes_dict[n_id] = {
                                "id": ent[0].id,
                                "label": ent[0].name,
                                "type": ent[0].entity_type,
                            }

            # Destination relations
            d_rels = cls.model.select().where((cls.model.tenant_id == tenant_id) & (cls.model.dst_entity_id == entity_id))
            for r in d_rels:
                edges.append({
                    "id": r.id,
                    "source": r.src_entity_id,
                    "target": r.dst_entity_id,
                    "label": r.predicate,
                    "confidence": r.confidence_score,
                })
                for n_id in [r.src_entity_id, r.dst_entity_id]:
                    if n_id not in nodes_dict:
                        ent = KnowledgeEntity.query(id=n_id)
                        if ent:
                            nodes_dict[n_id] = {
                                "id": ent[0].id,
                                "label": ent[0].name,
                                "type": ent[0].entity_type,
                            }

        except Exception as e:
            logging.error(f"[KnowledgeRelationService] Failed to retrieve graph neighborhood: {e}")

        return {
            "nodes": list(nodes_dict.values()),
            "edges": edges
        }


class ExpertiseService(CommonService):
    model = ExpertiseProfile

    @classmethod
    def find_experts_by_topic(cls, tenant_id: str, topic: str, min_confidence: float = 0.5) -> List[Dict[str, Any]]:
        """Finds expert users in the specified domain topic."""
        try:
            profiles = cls.model.select().where(
                (cls.model.tenant_id == tenant_id) &
                (cls.model.domain_topic == topic) &
                (cls.model.confidence_score >= min_confidence)
            ).order_by(cls.model.confidence_score.desc())

            return [
                {
                    "user_id": p.user_id,
                    "domain_topic": p.domain_topic,
                    "confidence_score": p.confidence_score,
                    "depth_level": p.depth_level,
                    "evidence": p.evidence_summary,
                }
                for p in profiles
            ]
        except Exception as e:
            logging.error(f"[ExpertiseService] Failed to find experts: {e}")
            return []


class SummaryService(CommonService):
    model = SummaryRegistry


class AuditLogService(CommonService):
    model = EILAuditLog
