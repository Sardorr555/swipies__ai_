#
#  Copyright 2026 The InfiniFlow Authors. All Rights Reserved.
#
import logging
import time
from typing import Dict, Any
from common.misc_utils import get_uuid
from rag.intelligence.security.anonymizer import PIIAnonymizer
from rag.intelligence.resolution.entity_resolver import EntityResolver
from rag.intelligence.extractors.entity_extractor import EntityExtractorPlugin
from rag.intelligence.extractors.decision_extractor import DecisionExtractorPlugin
from rag.intelligence.extractors.topic_extractor import TopicExtractorPlugin
from rag.intelligence.extractors.expertise_extractor import ExpertiseExtractorPlugin
from api.db.db_models import (
    KnowledgeRelation,
    ConversationMetadata,
    ExpertiseProfile,
    EILAuditLog,
)


class EILBackgroundWorker:
    """Asynchronous Intelligence Processing Worker."""

    def __init__(self):
        self.entity_plugin = EntityExtractorPlugin()
        self.decision_plugin = DecisionExtractorPlugin()
        self.topic_plugin = TopicExtractorPlugin()
        self.expertise_plugin = ExpertiseExtractorPlugin()

    def process_conversation_event(self, tenant_id: str, conversation_id: str, user_id: str, text_transcript: str, llm_client: Any = None) -> bool:
        """Processes conversation transcript through privacy filters and AI extractors."""
        try:
            # 1. Privacy & PII Sanitization
            clean_text, pii_meta = PIIAnonymizer.sanitize(text_transcript)

            # 2. Extract Entities & Relations
            entity_data = self.entity_plugin.extract(clean_text, {}, llm_client)

            # 3. Extract Decisions, Actions, Questions
            decision_data = self.decision_plugin.extract(clean_text, {}, llm_client)

            # 4. Extract Topics & Tech Stack
            topic_data = self.topic_plugin.extract(clean_text, {}, llm_client)

            # 5. Extract Expertise Signals
            expertise_data = self.expertise_plugin.extract(clean_text, {}, llm_client)

            # 6. Entity Resolution & Graph Storage
            entity_map = {}
            for ent in entity_data.get("entities", []):
                name = ent.get("name")
                e_type = ent.get("type", "Thing")
                if name:
                    resolved = EntityResolver.resolve_or_create(tenant_id, name, e_type, ent.get("description"))
                    entity_map[name] = resolved.id

            for rel in entity_data.get("relations", []):
                src_name = rel.get("src_name")
                dst_name = rel.get("dst_name")
                pred = rel.get("predicate", "DISCUSSED")

                if src_name in entity_map and dst_name in entity_map:
                    KnowledgeRelation.create(
                        id=get_uuid(),
                        tenant_id=tenant_id,
                        src_entity_id=entity_map[src_name],
                        predicate=pred,
                        dst_entity_id=entity_map[dst_name],
                        confidence_score=float(rel.get("confidence", 1.0)),
                        conversation_id=conversation_id,
                        source_snippet=clean_text[:255]
                    )

            # 7. Store Conversation Metadata
            ConversationMetadata.create(
                id=get_uuid(),
                conversation_id=conversation_id,
                tenant_id=tenant_id,
                user_id=user_id,
                topics=topic_data.get("topics", []),
                tags=topic_data.get("tags", []),
                summary=decision_data.get("summary", ""),
                decisions_json=decision_data.get("decisions", []),
                action_items_json=decision_data.get("action_items", []),
                unresolved_questions=decision_data.get("unresolved_questions", []),
                duration_seconds=0
            )

            # 8. Store Expertise Signals
            now = int(time.time() * 1000)
            for sig in expertise_data.get("expertise_signals", []):
                topic = sig.get("domain_topic")
                if topic and user_id:
                    ExpertiseProfile.create(
                        id=get_uuid(),
                        tenant_id=tenant_id,
                        user_id=user_id,
                        domain_topic=topic,
                        confidence_score=float(sig.get("confidence", 0.5)),
                        depth_level=sig.get("depth_level", "Intermediate"),
                        evidence_summary=sig.get("reasoning", ""),
                        last_active_at=now
                    )

            # 9. Log Audit Trail
            EILAuditLog.create(
                id=get_uuid(),
                tenant_id=tenant_id,
                operator_id=user_id or "system",
                action="CONVERSATION_KNOWLEDGE_EXTRACTED",
                resource_type="Conversation",
                resource_id=conversation_id,
                details={"pii": pii_meta, "entities_count": len(entity_map)}
            )

            logging.info(f"[EILBackgroundWorker] Finished processing conversation {conversation_id}")
            return True

        except Exception as e:
            logging.error(f"[EILBackgroundWorker] Worker failed for conversation {conversation_id}: {e}")
            return False
