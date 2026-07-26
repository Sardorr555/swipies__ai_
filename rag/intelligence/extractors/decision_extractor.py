#
#  Copyright 2026 The InfiniFlow Authors. All Rights Reserved.
#
import json
import logging
from typing import Dict, Any
from rag.intelligence.extractors.base import BaseKnowledgeExtractor


class DecisionExtractorPlugin(BaseKnowledgeExtractor):
    @property
    def plugin_name(self) -> str:
        return "decision_and_action_item_extractor"

    @property
    def version(self) -> str:
        return "1.0.0"

    def extract(self, text_content: str, metadata: Dict[str, Any], llm_client: Any = None) -> Dict[str, Any]:
        prompt = f"""
You are an Enterprise Assistant. Analyze the following conversation transcript:

---
{text_content}
---

Extract:
1. Architectural or business decisions made.
2. Action items / tasks (with assigned owner and deadline if mentioned).
3. Unresolved questions or technical risks.

Return ONLY a JSON object:
{{
    "summary": "Concise high-level summary",
    "decisions": [{{"decision": "Text", "owner": "Name", "confidence": 0.9}}],
    "action_items": [{{"task": "Task description", "owner": "Assignee", "deadline": "2026-08-01"}}],
    "unresolved_questions": [{{"question": "Question string", "risk_level": "medium"}}]
}}
"""
        if not llm_client:
            return {
                "summary": "Transcript processed.",
                "decisions": [],
                "action_items": [],
                "unresolved_questions": []
            }

        try:
            res_str = llm_client.chat(prompt)
            return json.loads(res_str)
        except Exception as e:
            logging.error(f"[DecisionExtractorPlugin] Extraction failed: {e}")
            return {
                "summary": "Extraction error",
                "decisions": [],
                "action_items": [],
                "unresolved_questions": []
            }
