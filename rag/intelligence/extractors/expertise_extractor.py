#
#  Copyright 2026 The InfiniFlow Authors. All Rights Reserved.
#
import json
import logging
from typing import Dict, Any
from rag.intelligence.extractors.base import BaseKnowledgeExtractor


class ExpertiseExtractorPlugin(BaseKnowledgeExtractor):
    @property
    def plugin_name(self) -> str:
        return "expertise_signal_extractor"

    @property
    def version(self) -> str:
        return "1.0.0"

    def extract(self, text_content: str, metadata: Dict[str, Any], llm_client: Any = None) -> Dict[str, Any]:
        """Estimates domain expertise signals from detailed responses or technical contributions."""
        prompt = f"""
Analyze the contribution below to estimate knowledge signals (NOT HR performance evaluation).
Focus on technical depth and domain familiarity.

---
{text_content}
---

Return ONLY JSON:
{{
    "expertise_signals": [
        {{
            "domain_topic": "Vector Databases",
            "depth_level": "Advanced",
            "confidence": 0.85,
            "reasoning": "Provided deep explanation of HNSW indexing principles."
        }}
    ]
}}
"""
        if not llm_client:
            return {"expertise_signals": []}

        try:
            res_str = llm_client.chat(prompt)
            return json.loads(res_str)
        except Exception as e:
            logging.error(f"[ExpertiseExtractorPlugin] Extraction failed: {e}")
            return {"expertise_signals": []}
