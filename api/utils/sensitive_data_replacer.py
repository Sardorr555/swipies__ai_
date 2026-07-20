import re
import logging

logger = logging.getLogger(__name__)

class SensitiveDataReplacer:
    """
    Utility class for anonymizing sensitive user data prior to sending prompts to LLM
    and de-anonymizing placeholders back to original values in the LLM response.
    """

    @staticmethod
    def apply_forward(text: str, rules: list) -> str:
        """
        Replaces original sensitive values in user text with designated replacement placeholders.
        """
        if not text or not rules or not isinstance(rules, list):
            return text

        result_text = str(text)
        for rule in rules:
            if not isinstance(rule, dict):
                continue
            search_val = rule.get("search_value")
            replace_val = rule.get("replace_value")

            if not search_val or replace_val is None:
                continue

            search_val = str(search_val)
            replace_val = str(replace_val)

            if not search_val:
                continue

            case_sensitive = bool(rule.get("case_sensitive", False))
            is_regex = bool(rule.get("is_regex", False))

            try:
                if is_regex:
                    flags = 0 if case_sensitive else re.IGNORECASE
                    result_text = re.sub(search_val, replace_val, result_text, flags=flags)
                else:
                    if case_sensitive:
                        result_text = result_text.replace(search_val, replace_val)
                    else:
                        pattern = re.compile(re.escape(search_val), re.IGNORECASE)
                        result_text = pattern.sub(replace_val, result_text)
            except Exception as e:
                logger.warning(f"Error executing sensitive data forward replacement for pattern '{search_val}': {e}")
                if case_sensitive:
                    result_text = result_text.replace(search_val, replace_val)
                else:
                    pattern = re.compile(re.escape(search_val), re.IGNORECASE)
                    result_text = pattern.sub(replace_val, result_text)

        return result_text

    @staticmethod
    def apply_reverse(text: str, rules: list) -> str:
        """
        Replaces replacement placeholders in LLM response back to original sensitive values for the user.
        """
        if not text or not rules or not isinstance(rules, list):
            return text

        result_text = str(text)
        # Reverse order of rules or process each replacement placeholder
        for rule in rules:
            if not isinstance(rule, dict):
                continue
            orig_search_val = rule.get("search_value")
            placeholder_val = rule.get("replace_value")

            if not orig_search_val or not placeholder_val:
                continue

            orig_search_val = str(orig_search_val)
            placeholder_val = str(placeholder_val)

            try:
                # Placeholders are matched exactly (case-sensitive or insensitive)
                pattern = re.compile(re.escape(placeholder_val), re.IGNORECASE)
                result_text = pattern.sub(orig_search_val, result_text)
            except Exception as e:
                logger.warning(f"Error executing sensitive data reverse replacement for placeholder '{placeholder_val}': {e}")
                result_text = result_text.replace(placeholder_val, orig_search_val)

        return result_text
