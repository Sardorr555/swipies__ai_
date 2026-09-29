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
import logging
import os
import re
import secrets
from urllib.parse import urlsplit, urlunsplit, parse_qsl

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes

logger = logging.getLogger("KeyCrypto")

SENSITIVE_KEY_PATTERNS = {"api_key", "secret_key", "password", "token", "access_token", "private_key", "key", "secret", "credential", "auth"}
DENY_BY_DEFAULT_SECTIONS = frozenset({"credentials", "auth_config", "headers"})

INSECURE_DEFAULT_KEYS = frozenset({
    "ragflow_single_global_instance_master_secret_2026",
    "ragflow",
    "infiniflow",
    "default_secret_key",
})

HKDF_SALT = b"ragflow_connector_credentials_v2_salt"
HKDF_INFO = b"ragflow:connector:aes256-gcm:v2"


class InsecureSecretKeyError(ValueError):
    """Raised when encryption is attempted with a missing, too short, or default insecure key (Fail-Closed)."""
    pass


def validate_master_secret(secret: str) -> str:
    """Validate that the secret key satisfies minimum entropy requirements. Fails closed."""
    if not secret or not isinstance(secret, str):
        raise InsecureSecretKeyError(
            "CRITICAL: RAGFLOW_SECRET_KEY is not configured. "
            "Fail-closed: Encryption rejected to prevent storing credentials under insecure defaults."
        )
    s = secret.strip()
    if len(s) < 32:
        raise InsecureSecretKeyError(
            f"CRITICAL: RAGFLOW_SECRET_KEY has insufficient length ({len(s)} chars, minimum 32 required). "
            "Fail-closed: Encryption rejected."
        )
    if s.lower() in INSECURE_DEFAULT_KEYS:
        raise InsecureSecretKeyError(
            f"CRITICAL: RAGFLOW_SECRET_KEY is set to a known insecure default '{s}'. "
            "Fail-closed: Encryption rejected. Please configure a unique 32+ character random secret."
        )
    return s


def _get_master_secret() -> str:
    if sec := os.environ.get("RAGFLOW_SECRET_KEY"):
        if sec.strip():
            return sec.strip()
    if sec := os.environ.get("SECRET_KEY"):
        if sec.strip():
            return sec.strip()
    return ""


def _get_key_candidates(secret: str = None) -> list[str]:
    """Return an ordered list of keys for decryption: primary secret first, followed by rotation keys."""
    if secret:
        return [secret]
    primary = _get_master_secret()
    candidates = [primary] if primary else []
    rotation_env = os.environ.get("RAGFLOW_SECRET_KEYS_ROTATION", "")
    if rotation_env:
        for k in rotation_env.split(","):
            k_clean = k.strip()
            if k_clean and k_clean not in candidates:
                candidates.append(k_clean)
    return candidates


def _derive_aes256_key(secret: str) -> bytes:
    """Derives a standard 32-byte (256-bit) key for AES-GCM using RFC 5869 HKDF-SHA256."""
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=HKDF_SALT,
        info=HKDF_INFO,
    )
    return hkdf.derive(secret.encode("utf-8"))


def _derive_legacy_v1_keys(secret: str):
    """Derives HMAC-SHA256 CTR keys for backward compatibility with enc:v1: ciphertexts."""
    k_enc = hashlib.sha256((secret + ":enc").encode("utf-8")).digest()
    k_mac = hashlib.sha256((secret + ":mac").encode("utf-8")).digest()
    return k_enc, k_mac


def _legacy_v1_keystream(key: bytes, iv: bytes, length: int) -> bytes:
    stream = bytearray()
    counter = 0
    while len(stream) < length:
        block = hashlib.sha256(key + iv + counter.to_bytes(4, "big")).digest()
        stream.extend(block)
        counter += 1
    return bytes(stream[:length])


def is_encrypted_key(text: str) -> bool:
    """Check if a string is encrypted with enc:v2: (AES-256-GCM) or legacy enc:v1:."""
    if not isinstance(text, str):
        return False
    trimmed = text.strip()
    return trimmed.startswith("enc:v2:") or trimmed.startswith("enc:v1:")


def has_embedded_url_credentials(url_str: str) -> bool:
    """Check if a URL string contains embedded user credentials (user:pass@) or sensitive query parameters."""
    if not isinstance(url_str, str) or "://" not in url_str:
        return False
    # Check for userinfo with password (e.g. https://user:password@host)
    if re.search(r"://([^/@]+:[^/@]+)@", url_str):
        return True
    # Check query parameters
    if "?" in url_str:
        try:
            query = url_str.split("?", 1)[1]
            for key, val in parse_qsl(query, keep_blank_values=True):
                k_lower = key.lower()
                if any(p in k_lower for p in SENSITIVE_KEY_PATTERNS) or k_lower in {"sig", "signature", "auth"}:
                    if val and not is_masked_value(val):
                        return True
        except Exception:
            pass
    return False


def sanitize_url_credentials(url_str: str) -> str:
    """Mask embedded userinfo passwords and sensitive query params in URLs."""
    if not isinstance(url_str, str) or "://" not in url_str:
        return url_str
    try:
        parts = urlsplit(url_str)
        netloc = parts.netloc
        if "@" in netloc and ":" in netloc.rsplit("@", 1)[0]:
            userinfo, host = netloc.rsplit("@", 1)
            user, _ = userinfo.split(":", 1)
            netloc = f"{user}:********@{host}"
        
        if parts.query:
            query_pairs = parse_qsl(parts.query, keep_blank_values=True)
            sanitized_parts = []
            for k, v in query_pairs:
                k_lower = k.lower()
                if any(p in k_lower for p in SENSITIVE_KEY_PATTERNS) or k_lower in {"sig", "signature", "auth"}:
                    sanitized_parts.append(f"{k}=********" if v else k)
                else:
                    sanitized_parts.append(f"{k}={v}")
            query = "&".join(sanitized_parts)
        else:
            query = parts.query
            
        return urlunsplit((parts.scheme, netloc, parts.path, query, parts.fragment))
    except Exception:
        masked = re.sub(r"(://[^/@]+:)[^/@]+(@)", r"\1********\2", url_str)
        masked = re.sub(r"([?&](?:token|api_key|secret|password|key|auth|sig)=)[^&]+", r"\1********", masked, flags=re.I)
        return masked


def has_masked_url_credentials(url_str: str) -> bool:
    """Check if a URL string contains masked user credentials or masked query parameters."""
    if not isinstance(url_str, str) or "://" not in url_str:
        return False
    # Check for masked password in userinfo (e.g. https://user:********@host or https://user:***@host)
    m = re.search(r"://([^/@]+):([^/@]+)@", url_str)
    if m and (is_masked_value(m.group(2)) or "***" in m.group(2)):
        return True
    if "?" in url_str:
        try:
            query = url_str.split("?", 1)[1]
            for key, val in parse_qsl(query, keep_blank_values=True):
                if is_masked_value(val) or "***" in val:
                    return True
        except Exception:
            pass
    return False


def merge_masked_url(existing_enc_or_plain: str, incoming_url: str, secret: str = None) -> str:
    """Merge an incoming masked URL with an existing encrypted/plain URL to restore masked credentials."""
    if not isinstance(incoming_url, str) or "://" not in incoming_url:
        return incoming_url
    existing_plain = decrypt_api_key(existing_enc_or_plain, secret) if existing_enc_or_plain else ""
    if not existing_plain or "://" not in existing_plain:
        return incoming_url

    try:
        parts_orig = urlsplit(existing_plain)
        parts_inc = urlsplit(incoming_url)

        # 1. Merge userinfo / password in netloc
        merged_netloc = parts_inc.netloc
        if "@" in parts_inc.netloc:
            inc_userinfo, inc_host = parts_inc.netloc.rsplit("@", 1)
            if ":" in inc_userinfo:
                inc_user, inc_pw = inc_userinfo.split(":", 1)
                if is_masked_value(inc_pw) or "***" in inc_pw:
                    orig_pw = ""
                    if "@" in parts_orig.netloc:
                        orig_userinfo, _ = parts_orig.netloc.rsplit("@", 1)
                        if ":" in orig_userinfo:
                            _, orig_pw = orig_userinfo.split(":", 1)
                    merged_pw = orig_pw if orig_pw else inc_pw
                else:
                    merged_pw = inc_pw
                merged_netloc = f"{inc_user}:{merged_pw}@{inc_host}" if merged_pw else f"{inc_user}@{inc_host}"

        # 2. Merge query parameters
        if parts_inc.query:
            inc_pairs = parse_qsl(parts_inc.query, keep_blank_values=True)
            orig_pairs = dict(parse_qsl(parts_orig.query, keep_blank_values=True)) if parts_orig.query else {}
            merged_parts = []
            for k, v in inc_pairs:
                if (is_masked_value(v) or "***" in v) and k in orig_pairs:
                    merged_parts.append(f"{k}={orig_pairs[k]}")
                else:
                    merged_parts.append(f"{k}={v}")
            merged_query = "&".join(merged_parts)
        else:
            merged_query = parts_inc.query

        return urlunsplit((parts_inc.scheme, merged_netloc, parts_inc.path, merged_query, parts_inc.fragment))
    except Exception as ex:
        logger.warning("Failed to merge masked URL %s with existing: %s", incoming_url, ex)
        return incoming_url



def encrypt_api_key(raw_text: str, secret: str = None) -> str:
    """Encrypt a sensitive string at rest using industry-standard AES-256-GCM (enc:v2:).
    
    Payload format: enc:v2:<base64(12-byte nonce + ciphertext + 16-byte tag)>
    Fails closed if the secret key is missing or insecure.
    """
    if not raw_text:
        return ""
    raw_str = str(raw_text).strip()
    if raw_str.startswith("enc:v2:"):
        return raw_str
    
    master_secret = validate_master_secret(secret or _get_master_secret())

    # If legacy v1, decrypt first with rotation keys then re-encrypt with current standard v2
    if raw_str.startswith("enc:v1:"):
        decrypted = decrypt_api_key(raw_str, master_secret)
        if decrypted != raw_str:
            raw_str = decrypted
        else:
            return raw_str  # Cannot decrypt with known keys, preserve as-is

    aes_key = _derive_aes256_key(master_secret)
    aesgcm = AESGCM(aes_key)
    nonce = secrets.token_bytes(12)  # Standard 96-bit nonce for GCM
    data = raw_str.encode("utf-8")
    
    ct_with_tag = aesgcm.encrypt(nonce, data, None)
    payload = base64.b64encode(nonce + ct_with_tag).decode("ascii")
    return "enc:v2:" + payload


def _decrypt_v2(payload_bytes: bytes, candidates: list[str]) -> str | None:
    if len(payload_bytes) < 28:  # 12-byte nonce + 16-byte minimum tag
        return None
    nonce = payload_bytes[:12]
    ct_with_tag = payload_bytes[12:]
    for cand in candidates:
        try:
            aes_key = _derive_aes256_key(cand)
            aesgcm = AESGCM(aes_key)
            pt = aesgcm.decrypt(nonce, ct_with_tag, None)
            return pt.decode("utf-8")
        except Exception:
            continue
    logger.error(
        "CRITICAL: Failed to decrypt credential payload (length=%d). "
        "Authentication tag verification failed with active primary key and all %d rotation key(s). "
        "Credentials undecryptable! Check RAGFLOW_SECRET_KEY.",
        len(payload_bytes), max(0, len(candidates) - 1)
    )
    return None


def _decrypt_v1(payload_bytes: bytes, candidates: list[str]) -> str | None:
    if len(payload_bytes) < 32:  # 16-byte IV + 16-byte tag
        return None
    iv, tag, ct = payload_bytes[:16], payload_bytes[16:32], payload_bytes[32:]
    for cand in candidates:
        try:
            k_enc, k_mac = _derive_legacy_v1_keys(cand)
            expected_tag = hmac.new(k_mac, iv + ct, hashlib.sha256).digest()[:16]
            if not hmac.compare_digest(tag, expected_tag):
                continue
            ks = _legacy_v1_keystream(k_enc, iv, len(ct))
            pt = bytes(a ^ b for a, b in zip(ct, ks))
            return pt.decode("utf-8")
        except Exception:
            continue
    logger.error(
        "CRITICAL: Failed to decrypt legacy v1 credential payload. "
        "HMAC tag mismatch with primary and all %d rotation key(s).",
        max(0, len(candidates) - 1)
    )
    return None


def decrypt_api_key(enc_text: str, secret: str = None) -> str:
    """Decrypt an encrypted string server-side, trying primary key then rotation keys.
    
    Supports enc:v2: (AES-256-GCM via HKDF) and backward compatibility for enc:v1: (HMAC-SHA256 CTR).
    """
    if not enc_text:
        return ""
    enc_str = str(enc_text).strip()
    if not (enc_str.startswith("enc:v2:") or enc_str.startswith("enc:v1:")):
        return enc_str

    candidates = _get_key_candidates(secret)
    if not candidates:
        logger.error("CRITICAL: decrypt_api_key called but no secret keys are configured in environment!")
        return enc_str

    try:
        if enc_str.startswith("enc:v2:"):
            payload = base64.b64decode(enc_str[7:].encode("ascii"))
            res = _decrypt_v2(payload, candidates)
            return res if res is not None else enc_str
        elif enc_str.startswith("enc:v1:"):
            payload = base64.b64decode(enc_str[7:].encode("ascii"))
            res = _decrypt_v1(payload, candidates)
            return res if res is not None else enc_str
    except Exception as ex:
        logger.error("CRITICAL: Exception in decrypt_api_key: %s", ex)
        return enc_str
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


# Strict allow-list of public/non-sensitive fields inside config.credentials.
# Any key in config.credentials NOT in this list is treated as sensitive by default (fail-safe).
PUBLIC_IDENTIFIER_FIELDS = frozenset({
    "instance_url", "url", "site_url", "container_url", "base_url", "wiki_base",
    "client_id", "account_id", "account_name", "username", "email",
    "jira_user_email", "jira_username", "zendesk_email", "zendesk_subdomain",
    "container_name", "namespace", "region", "tenant_id", "authentication_method",
    "auth_mode", "auth_type", "is_cloud", "sync_deleted_files", "version",
    "api_version", "batch_size", "objects", "folder_path", "folder", "user_ids",
    "method", "http_method", "items_path", "id_field", "content_fields", "metadata_fields",
    "pagination_type", "max_pages", "request_delay", "poll_timestamp_field"
})


def is_masked_value(val: any) -> bool:
    """Check if a string represents a masked credential placeholder."""
    if not isinstance(val, str):
        return False
    trimmed = val.strip()
    return trimmed == "********" or (("..." in trimmed or "***" in trimmed) and len(trimmed) <= 16)


def _is_sensitive_connector_key(key: str, in_deny_by_default_scope: bool = False, val: any = None) -> bool:
    """Determine whether a connector configuration key contains sensitive credentials.
    
    1. Uses deny-by-default inside config.credentials, config.auth_config, config.headers:
       everything is sensitive unless explicitly listed in PUBLIC_IDENTIFIER_FIELDS.
    2. Outside deny-by-default scope: matches against SENSITIVE_KEY_PATTERNS.
    3. Even if key is in PUBLIC_IDENTIFIER_FIELDS: if value contains embedded userinfo (user:pass@)
       or sensitive query parameters (?token=), it is treated as sensitive!
    """
    k_lower = str(key).lower().strip()
    if in_deny_by_default_scope:
        if k_lower in PUBLIC_IDENTIFIER_FIELDS:
            if isinstance(val, str) and has_embedded_url_credentials(val):
                return True
            return False
        return True
    
    if any(p in k_lower for p in SENSITIVE_KEY_PATTERNS):
        return True
    if isinstance(val, str) and has_embedded_url_credentials(val):
        return True
    return False


def encrypt_connector_config(config: dict, secret: str = None) -> dict:
    """Recursively encrypt sensitive fields in a connector config dictionary at rest."""
    if not isinstance(config, dict):
        return config

    def _encrypt_val(k: str, v: any, in_scope: bool):
        k_lower = str(k).lower()
        if isinstance(v, dict):
            sub_in_scope = in_scope or (k_lower in DENY_BY_DEFAULT_SECTIONS)
            return {sub_k: _encrypt_val(sub_k, sub_v, sub_in_scope) for sub_k, sub_v in v.items()}
        elif isinstance(v, list):
            return [_encrypt_val(k, item, in_scope) if isinstance(item, (dict, list)) else item for item in v]
        elif isinstance(v, str):
            if _is_sensitive_connector_key(k, in_scope, v):
                trimmed = v.strip()
                if trimmed and not trimmed.startswith("enc:v2:") and not is_masked_value(trimmed):
                    return encrypt_api_key(trimmed, secret)
            return v
        return v

    return {k: _encrypt_val(k, v, str(k).lower() in DENY_BY_DEFAULT_SECTIONS) for k, v in config.items()}


def decrypt_connector_config(config: dict, secret: str = None) -> dict:
    """Recursively decrypt all encrypted fields in a connector config dictionary."""
    if not isinstance(config, dict):
        return config

    def _decrypt_val(v: any):
        if isinstance(v, dict):
            return {sub_k: _decrypt_val(sub_v) for sub_k, sub_v in v.items()}
        elif isinstance(v, list):
            return [_decrypt_val(item) for item in v]
        elif isinstance(v, str):
            if is_encrypted_key(v):
                return decrypt_api_key(v, secret)
            return v
        return v

    return {k: _decrypt_val(v) for k, v in config.items()}


def mask_connector_config(config: dict, secret: str = None) -> dict:
    """Recursively mask sensitive fields in a connector config dictionary for safe UI/API responses."""
    if not isinstance(config, dict):
        return config

    def _mask_val(k: str, v: any, in_scope: bool):
        k_lower = str(k).lower()
        if isinstance(v, dict):
            sub_in_scope = in_scope or (k_lower in DENY_BY_DEFAULT_SECTIONS)
            return {sub_k: _mask_val(sub_k, sub_v, sub_in_scope) for sub_k, sub_v in v.items()}
        elif isinstance(v, list):
            return [_mask_val(k, item, in_scope) if isinstance(item, (dict, list)) else item for item in v]
        elif isinstance(v, str):
            plain_val = decrypt_api_key(v, secret) if is_encrypted_key(v) else v
            if "://" in plain_val and (has_embedded_url_credentials(plain_val) or k_lower in {"instance_url", "url", "site_url", "container_url", "base_url", "rss_url", "sitemap_url"}):
                return sanitize_url_credentials(plain_val)
            if _is_sensitive_connector_key(k, in_scope, plain_val):
                if plain_val:
                    return "********"
                return ""
            return plain_val
        return v

    return {k: _mask_val(k, v, str(k).lower() in DENY_BY_DEFAULT_SECTIONS) for k, v in config.items()}


def merge_updated_connector_config(existing_config: dict, incoming_config: dict, secret: str = None) -> dict:
    """Safely merges an updated config into an existing config, preserving existing secrets when incoming is masked."""
    if not isinstance(existing_config, dict):
        existing_config = {}
    if not isinstance(incoming_config, dict):
        return encrypt_connector_config(existing_config, secret)

    def _merge_dicts(existing: dict, incoming: dict, in_scope: bool) -> dict:
        result = dict(existing)
        for k, v in incoming.items():
            k_lower = str(k).lower()
            sub_in_scope = in_scope or (k_lower in DENY_BY_DEFAULT_SECTIONS)
            if isinstance(v, dict) and isinstance(result.get(k), dict):
                result[k] = _merge_dicts(result[k], v, sub_in_scope)
            elif is_masked_value(v):
                # Mask placeholder from UI -> retain existing encrypted secret
                if k in result and result[k]:
                    pass
                else:
                    result[k] = ""
            elif isinstance(v, str) and has_masked_url_credentials(v) and k in result and result[k]:
                # Masked URL from UI -> merge with existing decrypted URL to preserve secrets
                result[k] = merge_masked_url(str(result[k]), v, secret)
            elif isinstance(v, str) and _is_sensitive_connector_key(k, sub_in_scope, v) and not v and result.get(k):
                # Empty string on existing secret -> retain existing
                pass
            else:
                result[k] = v
        return result

    merged = _merge_dicts(existing_config, incoming_config, False)
    return encrypt_connector_config(merged, secret)


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

