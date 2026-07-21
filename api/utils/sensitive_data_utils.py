import re
import logging
from copy import deepcopy

logger = logging.getLogger(__name__)

def anonymize_text(text: str, rules: list) -> str:
    """Replaces sensitive user values in text with placeholders based on configured rules."""
    if not text or not isinstance(text, str) or not rules:
        return text

    # Sort rules to process longest search values first to prevent substring collisions
    sorted_rules = sorted(
        [r for r in rules if isinstance(r, dict) and r.get("search") is not None],
        key=lambda r: len(str(r.get("search"))),
        reverse=True
    )

    for rule in sorted_rules:
        search_val = rule.get("search")
        replace_val = rule.get("replace")
        if search_val is None or replace_val is None:
            continue
        search_val = str(search_val)
        replace_val = str(replace_val)
        if not search_val or not replace_val:
            continue

        case_sensitive = rule.get("case_sensitive", False)
        if isinstance(case_sensitive, str):
            case_sensitive = case_sensitive.lower() == "true"
        else:
            case_sensitive = bool(case_sensitive)

        is_regex = rule.get("is_regex", False)
        if isinstance(is_regex, str):
            is_regex = is_regex.lower() == "true"
        else:
            is_regex = bool(is_regex)

        flags = 0 if case_sensitive else re.IGNORECASE

        try:
            if is_regex:
                text = re.sub(search_val, replace_val, text, flags=flags)
            else:
                pattern = re.escape(search_val)
                text = re.sub(pattern, replace_val, text, flags=flags)
        except Exception as e:
            logger.warning(f"Sensitive data anonymization error for pattern '{search_val}': {e}")

    return text

def deanonymize_text(text: str, rules: list) -> str:
    """Replaces placeholders back to original sensitive values in text."""
    if not text or not isinstance(text, str) or not rules:
        return text

    # Sort rules to process longest replace values first to prevent substring collisions
    sorted_rules = sorted(
        [r for r in rules if isinstance(r, dict) and r.get("replace") is not None],
        key=lambda r: len(str(r.get("replace"))),
        reverse=True
    )

    for rule in sorted_rules:
        search_val = rule.get("search")
        replace_val = rule.get("replace")
        if search_val is None or replace_val is None:
            continue
        search_val = str(search_val)
        replace_val = str(replace_val)
        if not search_val or not replace_val:
            continue

        pattern = re.escape(replace_val)
        try:
            text = re.sub(pattern, search_val, text)
        except Exception as e:
            logger.warning(f"Sensitive data deanonymization error for placeholder '{replace_val}': {e}")

    return text

def anonymize_messages(messages: list, rules: list) -> list:
    """Anonymizes user content inside chat message list for sending to LLM."""
    if not messages or not rules:
        return messages

    anonymized_msgs = deepcopy(messages)
    for msg in anonymized_msgs:
        if isinstance(msg, dict) and msg.get("role") in ("user", "system", "assistant"):
            content = msg.get("content")
            if isinstance(content, str):
                msg["content"] = anonymize_text(content, rules)
            elif isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and part.get("type") in ("text", "input_text") and "text" in part:
                        part["text"] = anonymize_text(part["text"], rules)
    return anonymized_msgs
