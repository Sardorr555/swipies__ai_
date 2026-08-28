import re
import logging
from copy import deepcopy

logger = logging.getLogger(__name__)


def _parse_bool(val) -> bool:
    if isinstance(val, str):
        return val.strip().lower() in ("true", "1", "yes")
    return bool(val)


def _build_rule_pattern(term: str, is_regex: bool = False) -> str:
    """
    Builds a regex pattern for a search or replace term.
    For non-regex rules, alphanumeric boundaries (\\w) are wrapped with \\b
    to prevent partial word corruptions without breaking symbol matching ($100, etc.).
    """
    if is_regex:
        return term
    escaped = re.escape(term)
    prefix = r"\b" if re.match(r"^\w", term) else ""
    suffix = r"\b" if re.search(r"\w$", term) else ""
    return f"{prefix}{escaped}{suffix}"


def anonymize_text(text: str, rules: list) -> str:
    """Replaces sensitive user values in text with placeholders based on configured rules."""
    if not text or not isinstance(text, str) or not rules:
        return text

    # Sort rules to process longest search values first to prevent substring collisions
    sorted_rules = sorted(
        [r for r in rules if isinstance(r, dict) and r.get("search") is not None],
        key=lambda r: len(str(r.get("search"))),
        reverse=True,
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

        case_sensitive = _parse_bool(rule.get("case_sensitive", False))
        is_regex = _parse_bool(rule.get("is_regex", False))
        flags = 0 if case_sensitive else re.IGNORECASE

        try:
            pattern = _build_rule_pattern(search_val, is_regex=is_regex)
            text = re.sub(pattern, lambda _m, rv=replace_val: rv, text, flags=flags)
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
        reverse=True,
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

        case_sensitive = _parse_bool(rule.get("case_sensitive", False))
        flags = 0 if case_sensitive else re.IGNORECASE

        pattern = _build_rule_pattern(replace_val, is_regex=False)
        try:
            text = re.sub(pattern, lambda _m, sv=search_val: sv, text, flags=flags)
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
            if isinstance(content, (str, int, float)):
                msg["content"] = anonymize_text(str(content), rules)
            elif isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and part.get("type") in ("text", "input_text") and "text" in part:
                        part["text"] = anonymize_text(str(part["text"]), rules)
    return anonymized_msgs


class StreamingDeanonymizer:
    """
    Stateful lookahead sliding window buffer for stream token deanonymization.
    Buffers potential partial matches of active replacement placeholders
    while emitting non-matching prefix characters immediately with O(1) latency.
    """

    def __init__(self, rules: list):
        self.rules = []
        for r in rules or []:
            if isinstance(r, dict) and r.get("replace") and r.get("search"):
                self.rules.append({
                    "search": str(r.get("search")),
                    "replace": str(r.get("replace")),
                    "case_sensitive": _parse_bool(r.get("case_sensitive", False)),
                    "is_regex": _parse_bool(r.get("is_regex", False)),
                })

        self.rules.sort(key=lambda r: len(r["replace"]), reverse=True)
        self._buffer = ""
        self.max_prefix_len = max((len(r["replace"]) - 1 for r in self.rules), default=0)

    def feed(self, chunk: str) -> str:
        """
        Feeds an incoming stream token chunk.
        Returns clean deanonymized text safe to emit to the client immediately.
        """
        if not chunk:
            return ""
        if not self.rules:
            return chunk

        self._buffer += chunk
        self._buffer = deanonymize_text(self._buffer, self.rules)

        if not self._buffer:
            return ""

        if self.max_prefix_len == 0:
            out = self._buffer
            self._buffer = ""
            return out

        longest_suffix_match = 0
        buf_len = len(self._buffer)

        for rule in self.rules:
            rep = rule["replace"]
            case_sens = rule["case_sensitive"]
            max_k = min(len(rep) - 1, buf_len)
            for k in range(max_k, 0, -1):
                if k <= longest_suffix_match:
                    break
                suffix = self._buffer[-k:]
                target_prefix = rep[:k]
                matched = (suffix == target_prefix) if case_sens else (suffix.lower() == target_prefix.lower())
                if matched:
                    longest_suffix_match = max(longest_suffix_match, k)
                    break

        safe_len = buf_len - longest_suffix_match
        if safe_len > 0:
            emit = self._buffer[:safe_len]
            self._buffer = self._buffer[safe_len:]
            return emit

        return ""

    def flush(self, final: bool = False) -> str:
        """
        Flushes buffered characters.
        If final=True, deanonymizes and empties all remaining characters in buffer.
        If final=False, applies deanonymization to current buffer and flushes text.
        """
        if not self._buffer:
            return ""
        self._buffer = deanonymize_text(self._buffer, self.rules)
        out = self._buffer
        self._buffer = ""
        return out

