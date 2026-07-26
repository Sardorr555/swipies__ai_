#
#  Copyright 2026 The InfiniFlow Authors. All Rights Reserved.
#
import logging
from typing import Callable, Dict, List
from common.decorator import singleton
from rag.intelligence.events.schemas import EnterpriseEvent

try:
    from rag.utils.redis_conn import REDIS_CONN
except Exception:
    REDIS_CONN = None


@singleton
class EventBus:
    """Asynchronous Event Bus for publishing and consuming Enterprise Intelligence Layer events."""

    STREAM_KEY = "ragflow_eil_event_stream"
    CONSUMER_GROUP = "eil_workers_group"

    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}

    def publish(self, event: EnterpriseEvent) -> bool:
        """Publishes an event to the Redis Stream or local subscribers."""
        if REDIS_CONN:
            try:
                REDIS_CONN.queue_product(self.STREAM_KEY, event.to_dict())
                logging.info(f"[EIL EventBus] Published {event.event_type} (ID: {event.event_id}) for Tenant {event.tenant_id}")
                return True
            except Exception as e:
                logging.error(f"[EIL EventBus] Error publishing event to Redis: {e}")
        
        # Fallback to local dispatch if Redis is not available
        self.dispatch_local(event)
        return True

    def register_subscriber(self, event_type: str, handler: Callable):
        """Registers an in-memory handler for event processing."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)

    def dispatch_local(self, event: EnterpriseEvent):
        """Dispatches event to local subscribers directly."""
        handlers = self._subscribers.get(event.event_type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logging.error(f"[EIL EventBus] Error in local subscriber {handler}: {e}")
