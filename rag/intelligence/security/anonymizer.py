#
#  Copyright 2026 The InfiniFlow Authors. All Rights Reserved.
#
import re
from typing import Dict, Any, Tuple


class PIIAnonymizer:
    """Enterprise PII Anonymizer and Privacy Control Engine."""

    EMAIL_REGEX = re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+')
    PHONE_REGEX = re.compile(r'\+?\d{1,4}?[-.\s]?\(?\d{1,3}?\)?[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}')
    SSN_REGEX = re.compile(r'\b\d{3}-\d{2}-\d{4}\b')

    @classmethod
    def sanitize(cls, text: str) -> Tuple[str, Dict[str, Any]]:
        """Sanitizes text by masking sensitive PII tokens."""
        if not text:
            return "", {}

        anonymized_text = text
        masks_applied = 0

        anonymized_text, count_email = cls.EMAIL_REGEX.subn('[ANONYMIZED_EMAIL]', anonymized_text)
        masks_applied += count_email

        anonymized_text, count_phone = cls.PHONE_REGEX.subn('[ANONYMIZED_PHONE]', anonymized_text)
        masks_applied += count_phone

        anonymized_text, count_ssn = cls.SSN_REGEX.subn('[ANONYMIZED_SSN]', anonymized_text)
        masks_applied += count_ssn

        metadata = {
            "pii_detected": masks_applied > 0,
            "masks_count": masks_applied
        }

        return anonymized_text, metadata
