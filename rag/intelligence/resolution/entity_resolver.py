#
#  Copyright 2026 The InfiniFlow Authors. All Rights Reserved.
#
import logging
from typing import Optional, Dict, Any
from common.misc_utils import get_uuid
from api.db.db_models import KnowledgeEntity, EntityAlias


class EntityResolver:
    """Multi-stage Entity Resolution and Deduplication Engine."""

    @staticmethod
    def normalize_name(name: str) -> str:
        """Normalizes entity name for canonical string matching."""
        return " ".join(name.strip().lower().split())

    @classmethod
    def resolve_or_create(cls, tenant_id: str, name: str, entity_type: str, description: Optional[str] = None) -> KnowledgeEntity:
        """Resolves an incoming entity to a canonical KnowledgeEntity or creates a new one."""
        norm_name = cls.normalize_name(name)

        # 1. Exact alias match check
        try:
            aliases = EntityAlias.query(tenant_id=tenant_id, alias_name=norm_name)
            if aliases:
                target_entity = KnowledgeEntity.query(id=aliases[0].entity_id)
                if target_entity:
                    return target_entity[0]
        except Exception as e:
            logging.warning(f"[EntityResolver] Alias query failed: {e}")

        # 2. Canonical entity exact name check
        try:
            entities = KnowledgeEntity.query(tenant_id=tenant_id, name=name, entity_type=entity_type)
            if entities:
                return entities[0]
        except Exception as e:
            logging.warning(f"[EntityResolver] Entity query failed: {e}")

        # 3. Create new Canonical KnowledgeEntity and primary alias
        entity_id = get_uuid()
        entity = KnowledgeEntity.create(
            id=entity_id,
            tenant_id=tenant_id,
            name=name,
            entity_type=entity_type,
            description=description or "",
            attributes={},
            confidence_score=1.0
        )

        EntityAlias.create(
            id=get_uuid(),
            tenant_id=tenant_id,
            alias_name=norm_name,
            entity_id=entity_id,
            source_type="primary"
        )

        return entity

    @classmethod
    def merge_entities(cls, tenant_id: str, source_entity_id: str, target_entity_id: str):
        """Merges source entity into target entity, remapping aliases and relations."""
        if source_entity_id == target_entity_id:
            return

        source = KnowledgeEntity.query(id=source_entity_id)
        target = KnowledgeEntity.query(id=target_entity_id)

        if not source or not target:
            return

        # Point source entity's canonical_id to target
        KnowledgeEntity.update(canonical_id=target_entity_id).where(KnowledgeEntity.id == source_entity_id).execute()

        # Update all aliases pointing to source
        EntityAlias.update(entity_id=target_entity_id).where(EntityAlias.entity_id == source_entity_id).execute()

        # Register source entity's name as alias for target
        norm_source_name = cls.normalize_name(source[0].name)
        EntityAlias.create(
            id=get_uuid(),
            tenant_id=tenant_id,
            alias_name=norm_source_name,
            entity_id=target_entity_id,
            source_type="merged_alias"
        )
        logging.info(f"[EntityResolver] Merged entity {source_entity_id} into {target_entity_id}")
