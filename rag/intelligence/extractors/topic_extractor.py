#
#  Copyright 2026 The InfiniFlow Authors. All Rights Reserved.
#
import json
import logging
from typing import Dict, Any
from rag.intelligence.extractors.base import BaseKnowledgeExtractor


class TopicExtractorPlugin(BaseKnowledgeExtractor):
    @property
    def plugin_name(self) -> str:
        return "topic_and_tech_stack_extractor"

    @property
    def version(self) -> str:
        return "1.0.0"

    def extract(self, text_content: str, metadata: Dict[str, Any], llm_client: Any = None) -> Dict[str, Any]:
        prompt = f"""
Analyze the text and extract technical topics, frameworks, libraries, APIs, and business domains discussed.

---
{text_content}
---

Return ONLY JSON:
{{
    "topics": ["Topic1", "Topic2"],
    "technologies": ["Python", "Quart", "Neo4j"],
    "tags": ["rag", "enterprise-search"]
}}
"""
        if not llm_client:
            return {"topics": [], "technologies": [], "tags": []}

        try:
            res_str = llm_client.chat(prompt)
            return json.loads(res_str)
        except Exception as e:
            logging.error(f"[TopicExtractorPlugin] Extraction failed: {e}")
            return {"topics": [], "technologies": [], "tags": []}
