import re
import logging
from copy import deepcopy

logger = logging.getLogger(__name__)


def _parse_bool(val) -> bool:
    """Safely converts string or boolean representations to bool."""
    if isinstance(val, str):
        return val.lower() in ("true", "1", "yes")
    return bool(val)


def _build_rule_pattern(term: str, is_regex: bool = False) -> str:
    """
    Constructs a regular expression pattern for a search or replace term.
    If is_regex is False, escapes special characters and automatically wraps
    word boundaries (\b) around alphanumeric / word-character edges to prevent
    partial substring corruption (e.g. 'cat' matching inside 'category').
    """
    if not term:
        return ""
    if is_regex:
        return term

    escaped = re.escape(term)
    prefix = r"\b" if re.match(r"^\w", term, re.UNICODE) else ""
    suffix = r"\b" if re.search(r"\w$", term, re.UNICODE) else ""
    return f"{prefix}{escaped}{suffix}"


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

        case_sensitive = _parse_bool(rule.get("case_sensitive", False))
        is_regex = _parse_bool(rule.get("is_regex", False))
        flags = 0 if case_sensitive else re.IGNORECASE

        pattern = _build_rule_pattern(search_val, is_regex=is_regex)
        if not pattern:
            continue

        try:
            # Use lambda replacement to avoid backslash escaping issues in replacement values
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

        case_sensitive = _parse_bool(rule.get("case_sensitive", False))
        flags = 0 if case_sensitive else re.IGNORECASE

        pattern = _build_rule_pattern(replace_val, is_regex=False)
        if not pattern:
            continue

        try:
            # Use lambda replacement to avoid backslash escaping issues in search values
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
    Stateful streaming buffer that prevents technical placeholders (Word B) from leaking
    into client SSE chunks when LLM token generation splits placeholder strings across
    chunk boundaries.

    Non-matching text is emitted immediately in O(1) time without artificial buffering delay.
    """

    def __init__(self, rules: list):
        self.rules = [
            r for r in rules
            if isinstance(r, dict) and r.get("search") is not None and r.get("replace") is not None
        ] if rules else []
        self.buffer = ""

        # Precompute placeholder prefix matching metadata
        self._prefix_targets = []
        max_len = 0
        for r in self.rules:
            replace_val = str(r.get("replace", ""))
            if not replace_val:
                continue
            case_sensitive = _parse_bool(r.get("case_sensitive", False))
            ends_with_word_char = bool(re.search(r"\w$", replace_val, re.UNICODE))
            self._prefix_targets.append({
                "target": replace_val if case_sensitive else replace_val.lower(),
                "case_sensitive": case_sensitive,
                "length": len(replace_val),
                "ends_with_word_char": ends_with_word_char,
            })
            # If the placeholder ends with a word character (e.g. 'john'), we must buffer
            # up to the full length of the placeholder until a non-word char or EOF arrives,
            # preventing 'john' + 'ny' from turning into 'sardorny'.
            needed_len = len(replace_val) if ends_with_word_char else len(replace_val) - 1
            if needed_len > max_len:
                max_len = needed_len

        self._max_prefix_len = max_len

    def feed(self, chunk: str) -> str:
        """
        Feeds an incoming stream token chunk into the buffer.
        Returns the safe deanonymized text to emit immediately.
        """
        if not chunk:
            return ""
        if not self.rules:
            return chunk

        self.buffer += chunk

        if not self._prefix_targets or self._max_prefix_len <= 0:
            to_emit = deanonymize_text(self.buffer, self.rules)
            self.buffer = ""
            return to_emit

        buf_len = len(self.buffer)
        check_limit = min(buf_len, self._max_prefix_len)
        longest_match_len = 0

        for suffix_len in range(check_limit, 0, -1):
            candidate_suffix = self.buffer[-suffix_len:]
            candidate_suffix_lower = candidate_suffix.lower()

            for target_info in self._prefix_targets:
                target_str = target_info["target"]
                test_suffix = candidate_suffix if target_info["case_sensitive"] else candidate_suffix_lower

                # Suffix is a partial prefix of placeholder
                if suffix_len < target_info["length"] and target_str.startswith(test_suffix):
                    longest_match_len = suffix_len
                    break
                # Suffix is full placeholder that ends with word char (needs next token to confirm word boundary)
                elif suffix_len == target_info["length"] and target_info["ends_with_word_char"] and test_suffix == target_str:
                    longest_match_len = suffix_len
                    break

            if longest_match_len > 0:
                break

        if longest_match_len > 0:
            safe_part = self.buffer[:-longest_match_len]
            self.buffer = self.buffer[-longest_match_len:]
            to_emit = deanonymize_text(safe_part, self.rules) if safe_part else ""
            return to_emit
        else:
            to_emit = deanonymize_text(self.buffer, self.rules)
            self.buffer = ""
            return to_emit

    def flush(self, final: bool = True) -> str:
        """
        Flushes any remaining characters from the buffer upon stream completion or exit.
        Ensures zero dropped characters even if stream terminated with uncompleted prefix.
        """
        if not self.buffer:
            return ""

        # Perform final deanonymize pass on whatever remains in buffer
        drained = deanonymize_text(self.buffer, self.rules) if self.rules else self.buffer
        self.buffer = ""
        return drained
