#
#  Copyright 2026 The InfiniFlow Authors. All Rights Reserved.
#
from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseKnowledgeExtractor(ABC):
    """Abstract Base Class for all AI Extractor Plugins in the Enterprise Intelligence Layer."""

    @property
    @abstractmethod
    def plugin_name(self) -> str:
        """Unique name of the plugin."""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """Plugin version string."""
        pass

    @abstractmethod
    def extract(self, text_content: str, metadata: Dict[str, Any], llm_client: Any = None) -> Dict[str, Any]:
        """Runs knowledge extraction on text content and returns structured JSON output."""
        pass
