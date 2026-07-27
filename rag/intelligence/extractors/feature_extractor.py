#
#  Copyright 2026 The InfiniFlow Authors. All Rights Reserved.
#
import logging
from typing import Dict, Any, List
from rag.intelligence.extractors.base import BaseExtractor


class FeatureRequestExtractorPlugin(BaseExtractor):
    """Mines product feature requests and integration needs directly from user chats."""

    name = "feature_extractor"

    def extract(self, text: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        text_lower = text.lower()
        feature_triggers = ["хотелось бы", "добавьте", "было бы круто", "нужна интеграция", "планируете ли", "feature request", "feature"]

        requests: List[str] = []
        lines = text.split("\n")
        for line in lines:
            if any(tr in line.lower() for tr in feature_triggers):
                cleaned = line.strip()
                if len(cleaned) > 10:
                    requests.append(cleaned)

        return {
            "has_feature_request": len(requests) > 0,
            "extracted_feature_requests": requests,
        }
