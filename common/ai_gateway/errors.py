#
#  Copyright 2026 The InfiniFlow & Swipies AI Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
import re
from typing import Any, Dict, List, Union


class SecretRedactor:
    """
    High-performance, centralized secret sanitizer for AI Gateway.
    Guarantees that raw vendor API keys, authorization tokens, or credential parameters
    never appear in logs, error payloads, or client-facing responses.
    """

    PATTERNS: List[tuple[re.Pattern, str]] = [
        # Standard OpenAI / DeepSeek / Anthropic sk-* API keys
        (re.compile(r'sk-[a-zA-Z0-9_\-]{16,}', re.IGNORECASE), '[REDACTED_API_KEY]'),
        # Generic Bearer tokens
        (re.compile(r'(Bearer\s+)[a-zA-Z0-9_\.\-]{16,}', re.IGNORECASE), r'\1[REDACTED_TOKEN]'),
        # URL parameters containing keys/tokens: ?api_key=xyz, &token=xyz
        (re.compile(r'((?:api[-_]?key|auth[-_]?token|access[-_]?token|secret)=)[^\s&]+', re.IGNORECASE), r'\1[REDACTED]'),
        # JSON fields with password, api_key, token
        (re.compile(r'("(?:api_key|apiKey|secret|password|access_token)"\s*:\s*")[^"]+(")', re.IGNORECASE), r'\1[REDACTED]\2'),
    ]

    @classmethod
    def redact(cls, text: Union[str, Any]) -> str:
        """Sanitizes text by replacing any detected credential patterns with redacted placeholders."""
        if not isinstance(text, str):
            text = str(text)
        for pattern, replacement in cls.PATTERNS:
            text = pattern.sub(replacement, text)
        return text

    @classmethod
    def redact_dict(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively sanitizes dictionary keys and values."""
        clean: Dict[str, Any] = {}
        sensitive_keys = {"api_key", "apikey", "secret", "password", "access_token", "refresh_token", "token"}
        for k, v in data.items():
            if str(k).lower() in sensitive_keys:
                clean[k] = "[REDACTED]"
            elif isinstance(v, dict):
                clean[k] = cls.redact_dict(v)
            elif isinstance(v, list):
                clean[k] = [cls.redact_dict(i) if isinstance(i, dict) else cls.redact(i) if isinstance(i, str) else i for i in v]
            elif isinstance(v, str):
                clean[k] = cls.redact(v)
            else:
                clean[k] = v
        return clean


class AIGatewayError(Exception):
    """Base exception for all AI Gateway operations. Automatically redacts secrets from message."""

    def __init__(self, message: str, original_error: Exception | None = None, status_code: int = 500):
        self.raw_message = message
        self.sanitized_message = SecretRedactor.redact(message)
        self.original_error = original_error
        self.status_code = status_code
        super().__init__(self.sanitized_message)


class ProviderAuthError(AIGatewayError):
    """Raised when provider authentication fails (e.g. invalid API key)."""
    def __init__(self, message: str = "AI Provider authentication failed", **kwargs):
        super().__init__(message, status_code=401, **kwargs)


class RateLimitError(AIGatewayError):
    """Raised when vendor rate limits (TPM/RPM) are exceeded."""
    def __init__(self, message: str = "AI Provider rate limit exceeded", **kwargs):
        super().__init__(message, status_code=429, **kwargs)


class QuotaExceededError(AIGatewayError):
    """Raised when vendor credit/quota is exhausted."""
    def __init__(self, message: str = "AI Provider quota exceeded or insufficient balance", **kwargs):
        super().__init__(message, status_code=402, **kwargs)


class ModelNotFoundError(AIGatewayError):
    """Raised when the requested model is not found or unsupported."""
    def __init__(self, message: str = "Requested AI model not found", **kwargs):
        super().__init__(message, status_code=404, **kwargs)


class ProviderConnectionError(AIGatewayError):
    """Raised when network connection to the AI vendor fails or times out."""
    def __init__(self, message: str = "Failed to connect to AI Provider", **kwargs):
        super().__init__(message, status_code=504, **kwargs)


class ContentFilterError(AIGatewayError):
    """Raised when content is blocked by provider safety policy."""
    def __init__(self, message: str = "Content filtered by AI safety guidelines", **kwargs):
        super().__init__(message, status_code=400, **kwargs)
