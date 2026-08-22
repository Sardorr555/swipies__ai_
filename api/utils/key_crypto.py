#
#  Copyright 2026 The InfiniFlow Authors. All Rights Reserved.
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
import base64
import hashlib
import hmac
import os
import secrets
SENSITIVE_KEY_PATTERNS = {"api_key", "secret_key", "password", "token", "access_token", "private_key", "key"}


def _get_master_secret() -> str:
    try:
        from common import settings
        secret = settings.get_secret_key()
        if isinstance(secret, str) and secret:
            return secret
    except Exception:
        pass
    return os.environ.get("SECRET_KEY", "ragflow_single_global_instance_master_secret_2026")


def _derive_keys(secret: str):
    k_enc = hashlib.sha256((secret + ":enc").encode("utf-8")).digest()
    k_mac = hashlib.sha256((secret + ":mac").encode("utf-8")).digest()
    return k_enc, k_mac


def _keystream(key: bytes, iv: bytes, length: int) -> bytes:
    stream = bytearray()
    counter = 0
    while len(stream) < length:
        block = hashlib.sha256(key + iv + counter.to_bytes(4, "big")).digest()
        stream.extend(block)
        counter += 1
    return bytes(stream[:length])


def encrypt_api_key(raw_text: str, secret: str = None) -> str:
    """Encrypt an API key string at rest using authenticated HMAC-SHA256 CTR stream cipher."""
    if not raw_text:
        return ""
    raw_str = str(raw_text).strip()
    if raw_str.startswith("enc:v1:"):
        return raw_str
    
    master_secret = secret or _get_master_secret()
    k_enc, k_mac = _derive_keys(master_secret)
    iv = secrets.token_bytes(16)
    data = raw_str.encode("utf-8")
    ks = _keystream(k_enc, iv, len(data))
    ct = bytes(a ^ b for a, b in zip(data, ks))
    tag = hmac.new(k_mac, iv + ct, hashlib.sha256).digest()[:16]
    payload = base64.b64encode(iv + tag + ct).decode("ascii")
    return "enc:v1:" + payload


def decrypt_api_key(enc_text: str, secret: str = None) -> str:
    """Decrypt an API key string server-side for AI provider calls."""
    if not enc_text:
        return ""
    enc_str = str(enc_text).strip()
    if not enc_str.startswith("enc:v1:"):
        return enc_str
    
    try:
        master_secret = secret or _get_master_secret()
        payload = base64.b64decode(enc_str[7:].encode("ascii"))
        iv, tag, ct = payload[:16], payload[16:32], payload[32:]
        k_enc, k_mac = _derive_keys(master_secret)
        expected_tag = hmac.new(k_mac, iv + ct, hashlib.sha256).digest()[:16]
        if not hmac.compare_digest(tag, expected_tag):
            return enc_str
        ks = _keystream(k_enc, iv, len(ct))
        pt = bytes(a ^ b for a, b in zip(ct, ks))
        return pt.decode("utf-8")
    except Exception:
        return enc_str


def mask_api_key(raw_or_enc: str, secret: str = None) -> str:
    """Mask an API key for safe frontend display (e.g. sk-...abcd). Never reveals full key."""
    if not raw_or_enc:
        return ""
    plain = decrypt_api_key(raw_or_enc, secret)
    if not plain:
        return ""
    if len(plain) <= 8:
        return "********"
    prefix = plain[:3] if len(plain) >= 7 else plain[:2]
    suffix = plain[-4:]
    return f"{prefix}...{suffix}"


def sanitize_sensitive_dict(data: dict) -> dict:
    """Sanitizes sensitive fields like api_key or tokens from dictionaries before logging or returning."""
    if not isinstance(data, dict):
        return data
    sanitized = {}
    for k, v in data.items():
        k_lower = str(k).lower()
        if any(p in k_lower for p in SENSITIVE_KEY_PATTERNS):
            sanitized[k] = mask_api_key(str(v)) if v else ""
        elif isinstance(v, dict):
            sanitized[k] = sanitize_sensitive_dict(v)
        elif isinstance(v, list):
            sanitized[k] = [sanitize_sensitive_dict(item) if isinstance(item, dict) else item for item in v]
        else:
            sanitized[k] = v
    return sanitized
