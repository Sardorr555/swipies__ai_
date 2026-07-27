#
#  Copyright 2026 The InfiniFlow Authors. All Rights Reserved.
#
import logging
from typing import Dict, Any
from rag.intelligence.extractors.base import BaseExtractor


class SentimentExtractorPlugin(BaseExtractor):
    """Extracts user sentiment, frustration score, and friction points from conversations."""

    name = "sentiment_extractor"

    def extract(self, text: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        text_lower = text.lower()
        frustration_keywords = ["не работает", "ошибка", "сложно", "баг", "устали", "проблема", "не получается", "fail", "error", "broken"]

        matched = [kw for kw in frustration_keywords if kw in text_lower]
        frustration_score = min(1.0, len(matched) * 0.25)

        sentiment = "Neutral"
        if frustration_score > 0.5:
            sentiment = "Frustrated"
        elif any(kw in text_lower for kw in ["отлично", "спасибо", "круто", "супер", "great", "awesome", "thanks"]):
            sentiment = "Positive"

        return {
            "sentiment": sentiment,
            "frustration_score": frustration_score,
            "matched_friction_keywords": matched,
        }
