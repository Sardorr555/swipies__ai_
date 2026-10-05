#
#  Copyright 2025 The InfiniFlow Authors. All Rights Reserved.
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
import logging
import os
import random
import re
import time
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlsplit

from api.crm.base import CRMProviderBase
from api.crm.transport import CRMTransport, SSRFSecurityException, validate_crm_url_and_resolve
from api.crm.clients.amocrm import mask_phone_dynamic, mask_sensitive_payload

logger = logging.getLogger("Bitrix24Client")

# 20 default verified zones (dual verification: doc reference + DNS wildcard resolution)
DEFAULT_B24_ZONES = [
    "ru", "kz", "by", "uz", "com", "eu", "de", "pl", "it", "fr",
    "uk", "ae", "com.tr", "es", "in", "cn", "jp", "vn", "id", "mx",
]


class Bitrix24Error(Exception):
    """Base exception for Bitrix24 provider errors."""
    pass


class Bitrix24DomainError(Bitrix24Error):
    """Raised when Bitrix24 portal URL fails hostname or zone validation."""
    pass


class Bitrix24AuthError(Bitrix24Error):
    """Raised when Bitrix24 webhook authentication fails."""
    pass


class Bitrix24RateLimitError(Bitrix24Error):
    """Raised when Bitrix24 query limit is exceeded and retries are exhausted."""
    pass


def get_allowed_b24_zones() -> List[str]:
    """Retrieve allowed Bitrix24 cloud zones from environment or defaults."""
    env_zones = os.environ.get("RAGFLOW_CRM_B24_ZONES", "")
    if env_zones.strip():
        zones = [z.strip().lower() for z in env_zones.split(",") if z.strip()]
        if zones:
            return zones
    return list(DEFAULT_B24_ZONES)


def validate_bitrix24_cloud_url(url: str, allowed_zones: Optional[List[str]] = None) -> Tuple[bool, str]:
    """Validate Bitrix24 Cloud hostname against allowed zones.
    
    Enforces strictly HTTPS, default port 443, no user credentials, no punycode,
    and exact zone boundary matching.
    """
    if not url or not isinstance(url, str):
        return False, "URL must be a non-empty string"
    try:
        parsed = urlsplit(url)
    except Exception as e:
        return False, f"Invalid URL format: {e}"

    if parsed.scheme.lower() != "https":
        return False, f"Scheme '{parsed.scheme}' is forbidden. Bitrix24 strictly requires 'https'."
    if parsed.username or parsed.password:
        return False, "User credentials in URL authority are forbidden."
    if parsed.port not in (None, 443):
        return False, f"Custom port '{parsed.port}' is forbidden. Port 443 is mandatory."

    hostname = (parsed.hostname or "").strip().lower()
    if not hostname or hostname.startswith(".") or hostname.endswith(".") or ".." in hostname or "xn--" in hostname:
        return False, f"Invalid hostname format or punycode domain: '{hostname}'"

    zones = allowed_zones if allowed_zones is not None else get_allowed_b24_zones()
    zones_regex = "|".join(re.escape(z.strip().lower()) for z in zones)
    pattern = rf"^[a-z0-9](?:[a-z0-9-]{{0,61}}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{{0,61}}[a-z0-9])?)*\.bitrix24\.(?:{zones_regex})$"

    if not re.fullmatch(pattern, hostname):
        # Check if user provided an unsupported zone
        if ".bitrix24." in hostname:
            parts = hostname.split(".bitrix24.", 1)
            candidate_zone = parts[1]
            if candidate_zone not in zones:
                return False, (
                    f"Unsupported Bitrix24 cloud zone '{candidate_zone}'. "
                    f"Allowed zones: {', '.join(zones)}. "
                    f"For custom domains or on-premise installations, configure as 'bitrix24_onprem'."
                )
        return False, f"Hostname '{hostname}' does not match allowed Bitrix24 cloud portal pattern."

    return True, hostname


def validate_bitrix24_onprem_url(url: str) -> Tuple[bool, str]:
    """Validate Bitrix24 On-Premise URL against SSRF, private CIDR allowlist and HTTPS."""
    if not url or not isinstance(url, str):
        return False, "URL must be a non-empty string"
    try:
        parsed = urlsplit(url)
    except Exception as e:
        return False, f"Invalid URL format: {e}"

    if parsed.scheme.lower() != "https":
        return False, f"Scheme '{parsed.scheme}' is forbidden. Bitrix24 on-premise strictly requires 'https'."
    if parsed.username or parsed.password:
        return False, "User credentials in URL authority are forbidden."

    try:
        hostname, resolved_ip = validate_crm_url_and_resolve(
            url,
            allowed_schemes={"https"},
            private_cidr_env="RAGFLOW_CRM_PRIVATE_ALLOWLIST_CIDR",
        )
        return True, hostname
    except SSRFSecurityException as e:
        return False, f"SSRF security violation for on-premise URL '{url}': {e}"
    except Exception as e:
        return False, f"Host resolution error for on-premise URL '{url}': {e}"


def redact_bitrix24_webhook_url(url_or_text: str) -> str:
    """Sanitize the webhook secret token in Bitrix24 URL path /rest/<user_id>/<webhook_key>/ -> /rest/<user_id>/********/."""
    if not url_or_text or not isinstance(url_or_text, str):
        return ""
    # Matches /rest/<id>/<key> and replaces key with ********
    return re.sub(r"(/rest/\d+/)[^/?#]+", r"\g<1>********", url_or_text)


def normalize_phone_to_e164(phone: str, default_region: Optional[str] = None) -> str:
    """Normalize phone number to international E.164 format via phonenumbers.
    
    Strict validation without fallback:
    - If phone has international prefix '+', it is parsed and validated internationally.
    - If phone is in national format without '+' prefix, it requires an explicit region
      configured in connection.config. Without a configured region, national format is rejected.
    """
    if not phone or not isinstance(phone, str):
        return ""
    raw = phone.strip()
    try:
        import phonenumbers
    except ImportError as e:
        raise RuntimeError(
            "The 'phonenumbers' package is required for phone validation. Please install phonenumbers>=9.0.24."
        ) from e

    region = (default_region or "").strip().upper() or None
    if not raw.startswith("+") and not region:
        raise ValueError(
            f"Invalid phone number format: '{phone}'. National format without '+' country prefix is rejected because no region is configured in connection settings."
        )

    try:
        parsed = phonenumbers.parse(raw, region)
    except Exception as e:
        raise ValueError(f"Invalid phone number format: '{phone}' could not be parsed ({e}).") from e

    if not phonenumbers.is_valid_number(parsed):
        raise ValueError(f"Invalid phone number format: '{phone}' is not a valid telephone number (region={region}).")

    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)


normalize_phone_e164 = normalize_phone_to_e164


def acquire_b24_rate_limit(portal_host: str, max_rate: int = 2) -> None:
    """Centralized rate limiting (~2 req/s) per portal using Redis with fail-open fallback."""
    key = f"crm:ratelimit:b24:{portal_host}"
    try:
        from rag.utils.redis_conn import REDIS_CONN
        if REDIS_CONN and REDIS_CONN.is_alive() and REDIS_CONN.REDIS:
            r = REDIS_CONN.REDIS
            val = r.incr(key)
            if val == 1:
                r.expire(key, 1)
            if val > max_rate:
                time.sleep(0.5)
    except Exception as e:
        logger.warning("Redis rate-limiter unreachable, falling back to fail-open: %s", e)


class Bitrix24Client(CRMProviderBase):
    """Secure thin client for Bitrix24 Cloud and On-Premise via Inbound Webhooks."""

    def __init__(self, transport: Optional[CRMTransport] = None):
        self.transport = transport or CRMTransport(
            private_cidr_allowlist_env="RAGFLOW_CRM_PRIVATE_ALLOWLIST_CIDR",
            allowed_schemes={"https"},
        )

    def _get_validated_webhook_base_url(self, config: Dict[str, Any]) -> str:
        """Resolve, validate, and return the inbound webhook base URL."""
        crm_type = config.get("crm_type", "bitrix24")
        webhook_url = config.get("webhook_url") or config.get("base_url")

        if not webhook_url:
            portal_url = config.get("portal_url", "").strip().rstrip("/")
            user_id = str(config.get("user_id", "")).strip()
            secret = str(config.get("webhook_secret") or config.get("webhook_key", "")).strip()
            if not portal_url or not user_id or not secret:
                raise Bitrix24DomainError(
                    "Missing 'webhook_url' or ('portal_url', 'user_id', 'webhook_secret') in configuration."
                )
            webhook_url = f"{portal_url}/rest/{user_id}/{secret}"

        webhook_url = webhook_url.strip().rstrip("/")

        if crm_type == "bitrix24_onprem":
            ok, err_or_host = validate_bitrix24_onprem_url(webhook_url)
            if not ok:
                redacted = redact_bitrix24_webhook_url(webhook_url)
                raise Bitrix24DomainError(f"Invalid Bitrix24 On-Premise URL '{redacted}': {err_or_host}")
        else:
            ok, err_or_host = validate_bitrix24_cloud_url(webhook_url)
            if not ok:
                redacted = redact_bitrix24_webhook_url(webhook_url)
                raise Bitrix24DomainError(f"Invalid Bitrix24 Cloud URL '{redacted}': {err_or_host}")

        return webhook_url

    def _execute_api_call(
        self,
        config: Dict[str, Any],
        method_name: str,
        payload: Optional[Dict[str, Any]] = None,
        max_retries: int = 3,
    ) -> Dict[str, Any]:
        """Execute Bitrix24 webhook call with rate limiting, error redaction, and backoff."""
        base_url = self._get_validated_webhook_base_url(config)
        endpoint_url = f"{base_url}/{method_name}.json"
        redacted_url = redact_bitrix24_webhook_url(endpoint_url)

        portal_host = urlsplit(base_url).hostname or "default"
        headers = {"Content-Type": "application/json"}
        req_body = payload or {}

        for attempt in range(max_retries + 1):
            acquire_b24_rate_limit(portal_host, max_rate=2)

            try:
                resp = self.transport.post(
                    endpoint_url,
                    json=req_body,
                    headers=headers,
                    allow_redirects=False,
                    timeout=15.0,
                )
            except SSRFSecurityException as e:
                logger.error("SSRF violation on Bitrix24 endpoint %s: %s", redacted_url, e)
                raise Bitrix24DomainError(f"SSRF violation: {e}") from e
            except Exception as e:
                redacted_msg = redact_bitrix24_webhook_url(str(e))
                logger.error("Network error calling Bitrix24 endpoint %s: %s", redacted_url, redacted_msg)
                if attempt == max_retries:
                    raise Bitrix24Error(f"Network error calling Bitrix24: {redacted_msg}") from e
                time.sleep(0.5 * (2 ** attempt) + random.uniform(0.05, 0.15))
                continue

            # Check status codes
            if resp.status_code == 200:
                try:
                    data = resp.json()
                except Exception as e:
                    raise Bitrix24Error(f"Invalid JSON response from Bitrix24: {e}")

                if "error" in data:
                    err_code = str(data.get("error")).upper()
                    err_desc = redact_bitrix24_webhook_url(str(data.get("error_description", "")))
                    if err_code in ("QUERY_LIMIT_EXCEEDED", "SLOW_PLZ") or "LIMIT" in err_code:
                        if attempt < max_retries:
                            backoff = 0.5 * (2 ** attempt) + random.uniform(0.1, 0.25)
                            logger.warning(
                                "Bitrix24 rate limit hit (%s). Backoff for %.2fs on attempt %d",
                                err_code, backoff, attempt + 1
                            )
                            time.sleep(backoff)
                            continue
                        raise Bitrix24RateLimitError(f"Bitrix24 query limit exceeded: {err_desc}")
                    if err_code in ("INVALID_CREDENTIALS", "WRONG_AUTH_TYPE", "AUTHORIZATION_ERROR"):
                        raise Bitrix24AuthError(f"Bitrix24 webhook authentication failed ({err_code}): {err_desc}")
                    raise Bitrix24Error(f"Bitrix24 API error ({err_code}): {err_desc}")

                return data

            # Handle HTTP 503 / 429
            if resp.status_code in (429, 503) or resp.status_code >= 500:
                if attempt < max_retries:
                    backoff = 0.5 * (2 ** attempt) + random.uniform(0.1, 0.25)
                    logger.warning(
                        "Bitrix24 transient error (HTTP %d). Retrying in %.2fs...", resp.status_code, backoff
                    )
                    time.sleep(backoff)
                    continue
                redacted_body = redact_bitrix24_webhook_url(resp.text)
                raise Bitrix24RateLimitError(
                    f"Bitrix24 request failed after retries with HTTP {resp.status_code}: {redacted_body}"
                )

            # 401 / 403
            if resp.status_code in (401, 403):
                redacted_body = redact_bitrix24_webhook_url(resp.text)
                raise Bitrix24AuthError(f"Bitrix24 authentication rejected (HTTP {resp.status_code}): {redacted_body}")

            redacted_body = redact_bitrix24_webhook_url(resp.text)
            raise Bitrix24Error(f"Bitrix24 request returned HTTP {resp.status_code}: {redacted_body}")

        raise Bitrix24Error("Unexpected loop exit in Bitrix24 API execution.")

    def find_contact(self, connection_config: Dict[str, Any], phone: str) -> Optional[Dict[str, Any]]:
        """Find contact by phone in Bitrix24."""
        default_region = connection_config.get("default_phone_region") or connection_config.get("phone_region") or "US"
        norm_phone = normalize_phone_to_e164(phone, default_region)
        masked_phone = mask_phone_dynamic(norm_phone)
        logger.info("Searching Bitrix24 contact for phone: %s", masked_phone)

        resp = self._execute_api_call(
            connection_config,
            "crm.contact.list",
            payload={"filter": {"PHONE": norm_phone}, "select": ["ID", "NAME", "LAST_NAME", "PHONE"]},
        )
        contacts = resp.get("result", [])
        if contacts and len(contacts) > 0:
            return contacts[0]
        return None

    def create_lead(self, connection_config: Dict[str, Any], lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create lead in Bitrix24 via crm.lead.add."""
        CRMProviderBase.check_management_allowed(connection_config, action_name="create_lead")
        default_region = connection_config.get("default_phone_region") or connection_config.get("phone_region") or "US"
        phone = lead_data.get("phone", "")
        norm_phone = normalize_phone_to_e164(phone, default_region) if phone else ""
        masked_phone = mask_phone_dynamic(norm_phone)

        name = lead_data.get("name", "Client")
        title = lead_data.get("title") or f"Lead from Chat: {name}"
        logger.info("Creating Bitrix24 lead title='%s', phone=%s", title, masked_phone)

        fields: Dict[str, Any] = {
            "TITLE": title,
            "NAME": name,
            "SOURCE_ID": "WEB",
            "STATUS_ID": connection_config.get("status_id", "NEW"),
            "COMMENTS": lead_data.get("note") or lead_data.get("text", ""),
        }

        if norm_phone:
            fields["PHONE"] = [{"VALUE": norm_phone, "VALUE_TYPE": "WORK"}]

        if "price" in lead_data:
            try:
                fields["OPPORTUNITY"] = float(lead_data["price"])
            except Exception:
                pass

        if "pipeline_id" in connection_config:
            fields["CATEGORY_ID"] = connection_config["pipeline_id"]
        elif "pipeline_id" in lead_data:
            fields["CATEGORY_ID"] = lead_data["pipeline_id"]

        resp = self._execute_api_call(
            connection_config,
            "crm.lead.add",
            payload={"fields": fields, "params": {"REGISTER_SONET_EVENT": "Y"}},
        )

        lead_id = resp.get("result")
        return {
            "crm_type": connection_config.get("crm_type", "bitrix24"),
            "lead_id": str(lead_id),
            "status": "success",
        }

    def refresh_auth(self, connection_config: Dict[str, Any]) -> Dict[str, Any]:
        """Verify Bitrix24 webhook validity via lightweight crm.lead.fields call."""
        logger.info("Validating Bitrix24 webhook authentication...")
        self._execute_api_call(connection_config, "crm.lead.fields")
        return connection_config

    def check_stock(self, connection_config: Dict[str, Any], item_query: str) -> Dict[str, Any]:
        """Bitrix24 does not support warehouse inventory / stock balance checking."""
        return {
            "supported": False,
            "message": "Bitrix24 provider does not support inventory or stock balance checks. Use 1C:Enterprise provider.",
        }

    def query_records(
        self,
        connection_config: Dict[str, Any],
        entity: str,
        query: str = "",
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Query live Bitrix24 CRM entities (deals, leads, contacts, companies, products)."""
        entity_clean = entity.lower().strip().rstrip("s")
        if entity_clean in ("deal", "order"):
            method = "crm.deal.list"
            select_fields = ["ID", "TITLE", "STAGE_ID", "OPPORTUNITY", "CURRENCY_ID", "DATE_MODIFY", "ASSIGNED_BY_ID", "COMMENTS"]
        elif entity_clean == "lead":
            method = "crm.lead.list"
            select_fields = ["ID", "TITLE", "NAME", "LAST_NAME", "STATUS_ID", "OPPORTUNITY", "PHONE", "EMAIL", "DATE_MODIFY", "COMMENTS"]
        elif entity_clean == "contact":
            method = "crm.contact.list"
            select_fields = ["ID", "NAME", "LAST_NAME", "PHONE", "EMAIL", "DATE_MODIFY", "COMMENTS"]
        elif entity_clean == "company":
            method = "crm.company.list"
            select_fields = ["ID", "TITLE", "COMPANY_TYPE", "PHONE", "EMAIL", "DATE_MODIFY"]
        elif entity_clean == "product":
            method = "crm.product.list"
            select_fields = ["ID", "NAME", "PRICE", "CURRENCY_ID", "DESCRIPTION"]
        else:
            method = "crm.deal.list"
            select_fields = ["ID", "TITLE", "STAGE_ID", "OPPORTUNITY", "CURRENCY_ID", "DATE_MODIFY"]

        b24_filter: Dict[str, Any] = {}
        if filters:
            for k, v in filters.items():
                k_upper = k.upper()
                if k_upper in ("STAGE", "STATUS", "STAGE_ID", "STATUS_ID"):
                    if "deal" in method:
                        b24_filter["STAGE_ID"] = v
                    elif "lead" in method:
                        b24_filter["STATUS_ID"] = v
                elif k_upper in ("MIN_PRICE", "MIN_OPPORTUNITY", "PRICE_GTE"):
                    b24_filter[">=OPPORTUNITY"] = v
                elif k_upper in ("MAX_PRICE", "MAX_OPPORTUNITY", "PRICE_LTE"):
                    b24_filter["<=OPPORTUNITY"] = v
                else:
                    b24_filter[k] = v

        if query:
            q_clean = query.strip()
            if entity_clean == "contact":
                if any(c.isdigit() for c in q_clean):
                    b24_filter["PHONE"] = q_clean
                elif "@" in q_clean:
                    b24_filter["EMAIL"] = q_clean
                else:
                    b24_filter["%NAME"] = q_clean
            elif entity_clean == "company":
                b24_filter["%TITLE"] = q_clean
            elif entity_clean == "product":
                b24_filter["%NAME"] = q_clean
            else:
                b24_filter["%TITLE"] = q_clean

        payload = {
            "filter": b24_filter,
            "select": select_fields,
            "order": {"DATE_MODIFY": "DESC"},
        }
        logger.info("Executing Bitrix24 query_records method=%s filter=%s", method, mask_sensitive_payload(b24_filter))
        resp = self._execute_api_call(connection_config, method, payload=payload)
        raw_items = resp.get("result", [])
        if not isinstance(raw_items, list):
            raw_items = []

        max_limit = max(1, min(limit, 50))
        raw_items = raw_items[:max_limit]

        records = []
        for item in raw_items:
            # Extract phone/email if list format
            phone_val = ""
            email_val = ""
            if isinstance(item.get("PHONE"), list) and item["PHONE"]:
                phone_val = item["PHONE"][0].get("VALUE", "")
            elif isinstance(item.get("PHONE"), str):
                phone_val = item["PHONE"]

            if isinstance(item.get("EMAIL"), list) and item["EMAIL"]:
                email_val = item["EMAIL"][0].get("VALUE", "")
            elif isinstance(item.get("EMAIL"), str):
                email_val = item["EMAIL"]

            title = item.get("TITLE") or item.get("NAME", "")
            if item.get("LAST_NAME"):
                title = f"{title} {item['LAST_NAME']}".strip()

            rec = {
                "id": str(item.get("ID", "")),
                "entity": entity_clean,
                "title": title,
                "status": item.get("STAGE_ID") or item.get("STATUS_ID", ""),
                "price": item.get("OPPORTUNITY") or item.get("PRICE", 0),
                "currency": item.get("CURRENCY_ID", "USD"),
                "phone": phone_val,
                "email": email_val,
                "updated_at": item.get("DATE_MODIFY", ""),
                "raw": item,
            }
            records.append(rec)
        return records
