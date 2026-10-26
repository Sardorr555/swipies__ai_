"""Subscription-only attribution policy, shared by transport-independent code."""
from datetime import datetime, timezone
import re


def branding_required(plan, expiry=None, now=None):
    if not isinstance(plan, str) or plan.lower().strip() not in {"plus", "pro"}:
        return True
    if expiry is None or expiry == "":
        return False  # Existing lifetime subscriptions have no expiry.
    try:
        if isinstance(expiry, str):
            expiry = datetime.fromisoformat(expiry.replace("Z", "+00:00"))
        if not isinstance(expiry, datetime):
            return True
        # Naive DB dates follow the same server-local convention as TenantService.
        current = now or (datetime.now(expiry.tzinfo) if expiry.tzinfo else datetime.now())
        if current.tzinfo and not expiry.tzinfo:
            current = current.astimezone().replace(tzinfo=None)
        elif expiry.tzinfo and not current.tzinfo:
            current = current.replace(tzinfo=timezone.utc)
        return expiry <= current
    except (ValueError, TypeError, OverflowError):
        return True


def attribution_present(text, line):
    """Accept the complete official footer with or without tracking parameters.

    A mention of Swipies elsewhere in a message never bypasses attribution.
    """
    def normalize(value):
        return re.sub(r"(\]\([^)?]+)\?[^)]*(\))", r"\1\2", value)
    return normalize((text or "").rstrip()).endswith(normalize(line))


async def brand_agent_events(events, suffix_for):
    """Attribute Message-only canvases as well as LLM canvases before message_end."""
    text = ""
    last = {}
    async for event in events:
        last = event
        if event.get("event") == "message":
            text += event.get("data", {}).get("content", "") or ""
        if event.get("event") in {"message_end", "workflow_finished", "user_inputs"} and text:
            suffix = suffix_for(text)
            if suffix:
                yield {**event, "event": "message", "data": {"content": suffix}}
            text = ""
        yield event
    if text:
        suffix = suffix_for(text)
        if suffix:
            yield {**last, "event": "message", "data": {"content": suffix}}
