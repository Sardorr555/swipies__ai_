#
#  Copyright 2026 The InfiniFlow Authors. All Rights Reserved.
#
import json
import logging
from typing import Dict, Any
from rag.intelligence.extractors.base import BaseKnowledgeExtractor


class EntityExtractorPlugin(BaseKnowledgeExtractor):
    @property
    def plugin_name(self) -> str:
        return "entity_and_relationship_extractor"

    @property
    def version(self) -> str:
        return "1.0.0"

    def extract(self, text_content: str, metadata: Dict[str, Any], llm_client: Any = None) -> Dict[str, Any]:
        prompt = f"""
You are an Enterprise Knowledge Graph Extractor. Analyze the text below:

---
{text_content}
---

Extract all named entities and relationships.
Entity types allowed: Person, Project, Tech, Doc, Org, Customer, Decision, Repository, Bug.
Predicate types allowed: OWNS, USES, CREATED, DISCUSSED, FIXES, BELONGS_TO, EXPERT_IN.

Return ONLY a JSON object with this exact structure:
{{
    "entities": [
        {{"name": "Entity Name", "type": "Person", "description": "Brief description"}}
    ],
    "relations": [
        {{"src_name": "Subject Entity", "predicate": "CREATED", "dst_name": "Object Entity", "confidence": 0.95}}
    ]
}}
"""
        if not llm_client:
            return {"entities": [], "relations": []}

        try:
            res_str = llm_client.chat(prompt)
            return json.loads(res_str)
        except Exception as e:
            logging.error(f"[EntityExtractorPlugin] Extraction failed: {e}")
            return {"entities": [], "relations": []}
