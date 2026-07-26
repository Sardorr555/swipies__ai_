#
#  Copyright 2026 The InfiniFlow Authors. All Rights Reserved.
#
import json
import time
from typing import Dict, Any, Optional
from common.misc_utils import get_uuid


class EventTypes:
    CONVERSATION_CREATED = "ConversationCreated"
    MESSAGE_SENT = "MessageSent"
    CONVERSATION_FINISHED = "ConversationFinished"
    DOCUMENT_UPLOADED = "DocumentUploaded"
    DATASET_INDEXED = "DatasetIndexed"
    WORKFLOW_EXECUTED = "WorkflowExecuted"
    AGENT_INVOKED = "AgentInvoked"
    TOOL_CALLED = "ToolCalled"
    TASK_CREATED = "TaskCreated"
    DECISION_EXTRACTED = "DecisionExtracted"
    KNOWLEDGE_UPDATED = "KnowledgeUpdated"


class EnterpriseEvent:
    def __init__(self, event_type: str, tenant_id: str, payload: Dict[str, Any], user_id: Optional[str] = None):
        self.event_id = get_uuid()
        self.event_type = event_type
        self.tenant_id = tenant_id
        self.user_id = user_id or "system"
        self.payload = payload
        self.timestamp = int(time.time() * 1000)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "payload": json.dumps(self.payload),
            "timestamp": str(self.timestamp),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EnterpriseEvent":
        event = cls(
            event_type=data.get("event_type", "Unknown"),
            tenant_id=data.get("tenant_id", ""),
            payload=json.loads(data.get("payload", "{}")),
            user_id=data.get("user_id"),
        )
        event.event_id = data.get("event_id", get_uuid())
        event.timestamp = int(data.get("timestamp", int(time.time() * 1000)))
        return event
