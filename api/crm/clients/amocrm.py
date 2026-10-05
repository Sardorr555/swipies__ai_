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
import re
import threading
import time
import uuid
from typing import Any, Dict, Optional, Tuple, List
from urllib.parse import urlsplit, quote

from api.crm.base import CRMProviderBase
from api.crm.transport import CRMTransport, SSRFSecurityException
from api.db.services.crm_service import CRMConnectionService

logger = logging.getLogger("AmoCRMClient")

ALLOWED_AMOCRM_BASE_DOMAINS = ("amocrm.ru", "amocrm.com", "kommo.com")


class AmoCRMError(Exception):
    """Base exception for all amoCRM client errors."""
    pass


class AmoCRMDomainError(AmoCRMError):
    """Raised when amoCRM domain fails boundary validation."""
    pass


class AmoCRMAuthError(AmoCRMError):
    """Raised when authentication or token refresh fails."""
    def __init__(self, message: str, status_code: Optional[int] = None, response_body: Optional[str] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class AmoCRMTokenRevokedError(AmoCRMAuthError):
    """Raised when refresh token was revoked by provider (invalid_grant)."""
    pass


def is_valid_amocrm_domain(hostname: str) -> bool:
    """Validate that hostname strictly belongs to amoCRM or Kommo domains.
    
    Allowed domains: *.amocrm.ru, *.amocrm.com, *.kommo.com.
    Prevents lookalikes (e.g. evilamocrm.ru, amocrm.ru.attacker.com).
    """
    if not hostname or not isinstance(hostname, str):
        return False
    host = hostname.strip().lower()
    if host.startswith(".") or host.endswith(".") or ".." in host or "xn--" in host:
        return False
    for base in ALLOWED_AMOCRM_BASE_DOMAINS:
        if host == base or host.endswith("." + base):
            sub = host[: -(len(base) + 1)] if host.endswith("." + base) else ""
            if not sub:
                return True
            labels = sub.split(".")
            if all(re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", lbl) for lbl in labels):
                return True
    return False


def is_valid_amocrm_url(url: str) -> Tuple[bool, str]:
    """Validate an amoCRM URL strictly: HTTPS, standard port, no userinfo, valid domain boundary."""
    if not url or not isinstance(url, str):
        return False, "URL must be a non-empty string"
    try:
        parsed = urlsplit(url)
    except Exception as e:
        return False, f"Invalid URL format: {e}"

    if parsed.scheme.lower() != "https":
        return False, f"Scheme '{parsed.scheme}' forbidden. amoCRM strictly requires 'https'."
    if parsed.username or parsed.password:
        return False, "User credentials in URL authority are forbidden."
    if parsed.port not in (None, 443):
        return False, f"Custom port '{parsed.port}' is forbidden. Standard HTTPS port 443 required."

    hostname = (parsed.hostname or "").strip().lower()
    if not is_valid_amocrm_domain(hostname):
        return False, (
            f"Hostname '{hostname}' does not match allowed amoCRM / Kommo domain boundaries: "
            f"{', '.join(f'*.{b}' for b in ALLOWED_AMOCRM_BASE_DOMAINS)}"
        )
    return True, hostname


def mask_phone_dynamic(phone: str) -> str:
    """Mask phone preserving country code/prefix and last 2 digits, masking middle digits."""
    if not phone or not isinstance(phone, str):
        return ""
    s = phone.strip()
    if len(s) <= 4:
        return "****"
    prefix_len = 3 if s.startswith("+") else 2
    suffix_len = 2
    if len(s) <= prefix_len + suffix_len:
        return s[:2] + ("*" * (len(s) - 3)) + s[-1:]
    masked_count = len(s) - prefix_len - suffix_len
    return s[:prefix_len] + ("*" * masked_count) + s[-suffix_len:]


def mask_sensitive_payload(data: Any) -> Any:
    """Recursively mask sensitive tokens, credentials, and phones in dictionaries/lists."""
    if isinstance(data, dict):
        masked = {}
        for k, v in data.items():
            k_lower = str(k).lower()
            if any(p in k_lower for p in ("token", "secret", "password", "key", "auth")):
                masked[k] = "********"
            elif "phone" in k_lower and isinstance(v, str):
                masked[k] = mask_phone_dynamic(v)
            else:
                masked[k] = mask_sensitive_payload(v)
        return masked
    elif isinstance(data, list):
        return [mask_sensitive_payload(item) for item in data]
    return data


_LOCAL_LOCKS: Dict[str, threading.Lock] = {}
_LOCAL_LOCKS_GUARD = threading.Lock()


def _get_local_lock(conn_id: str) -> threading.Lock:
    with _LOCAL_LOCKS_GUARD:
        if conn_id not in _LOCAL_LOCKS:
            _LOCAL_LOCKS[conn_id] = threading.Lock()
        return _LOCAL_LOCKS[conn_id]


class AmoCRMRefreshLock:
    """Distributed Redis lock with Lua release and in-memory fallback for token refresh."""

    def __init__(self, connection_id: str, timeout_secs: int = 30):
        self.connection_id = connection_id
        self.timeout_secs = timeout_secs
        self.lock_key = f"crm:lock:refresh:{connection_id}"
        self.token = uuid.uuid4().hex
        self.acquired = False
        self._is_local = False
        self._local_lock = None

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()

    def acquire(self, wait_timeout: float = 15.0) -> bool:
        start = time.time()
        while time.time() - start < wait_timeout:
            try:
                from rag.utils.redis_conn import REDIS_CONN
                if REDIS_CONN and REDIS_CONN.is_alive() and REDIS_CONN.REDIS:
                    ok = REDIS_CONN.REDIS.set(self.lock_key, self.token, ex=self.timeout_secs, nx=True)
                    if ok:
                        self.acquired = True
                        self._is_local = False
                        return True
                else:
                    return self._acquire_local(wait_timeout - (time.time() - start))
            except Exception as e:
                logger.warning("Redis lock acquire failed: %s. Falling back to in-memory lock.", e)
                return self._acquire_local(wait_timeout - (time.time() - start))
            time.sleep(0.1)
        return False

    def _acquire_local(self, remaining_timeout: float) -> bool:
        self._local_lock = _get_local_lock(self.connection_id)
        timeout = max(0.1, remaining_timeout)
        acquired = self._local_lock.acquire(timeout=timeout)
        if acquired:
            self.acquired = True
            self._is_local = True
        return acquired

    def release(self):
        if not self.acquired:
            return
        if self._is_local and self._local_lock:
            try:
                self._local_lock.release()
            except Exception:
                pass
            self.acquired = False
            return

        try:
            from rag.utils.redis_conn import REDIS_CONN
            if REDIS_CONN and REDIS_CONN.is_alive() and REDIS_CONN.REDIS:
                LUA_DELETE_IF_EQUAL = """
                if redis.call("get", KEYS[1]) == ARGV[1] then
                    return redis.call("del", KEYS[1])
                else
                    return 0
                end
                """
                REDIS_CONN.REDIS.eval(LUA_DELETE_IF_EQUAL, 1, self.lock_key, self.token)
        except Exception as e:
            logger.warning("Redis lock release failed: %s", e)
        finally:
            self.acquired = False


class AmoCRMClient(CRMProviderBase):
    """Secure thin client for amoCRM / Kommo CRM platforms."""

    def __init__(self, transport: Optional[CRMTransport] = None):
        self.transport = transport or CRMTransport()

    def _get_base_url(self, config: Dict[str, Any]) -> str:
        """Resolve and validate the base HTTPS URL for the amoCRM portal."""
        if "base_url" in config and config["base_url"]:
            url = str(config["base_url"]).strip().rstrip("/")
        else:
            subdomain = str(config.get("subdomain", "")).strip().lower()
            zone = str(config.get("zone", "amocrm.ru")).strip().lower()
            if not subdomain:
                raise AmoCRMDomainError("Missing 'subdomain' or 'base_url' in amoCRM connection configuration.")
            url = f"https://{subdomain}.{zone}"

        valid, err_or_host = is_valid_amocrm_url(url)
        if not valid:
            raise AmoCRMDomainError(f"Invalid amoCRM base URL '{url}': {err_or_host}")
        return url

    def _do_oauth_refresh(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Perform OAuth2 refresh token exchange with amoCRM."""
        base_url = self._get_base_url(config)
        refresh_url = f"{base_url}/oauth2/access_token"

        client_id = config.get("client_id")
        client_secret = config.get("client_secret")
        refresh_token = config.get("refresh_token")
        redirect_uri = config.get("redirect_uri", "")

        if not client_id or not client_secret or not refresh_token:
            raise AmoCRMAuthError("Missing required OAuth parameters ('client_id', 'client_secret', 'refresh_token')")

        payload = {
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "redirect_uri": redirect_uri,
        }

        try:
            resp = self.transport.post(
                refresh_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                allow_redirects=False,
                timeout=15.0,
            )
        except Exception as e:
            logger.error("Network error during amoCRM OAuth refresh: %s", e)
            raise AmoCRMAuthError(f"Network error during amoCRM OAuth refresh: {e}") from e

        if resp.status_code == 200:
            data = resp.json()
            expires_in = int(data.get("expires_in", 86400))
            return {
                "access_token": data["access_token"],
                "refresh_token": data["refresh_token"],
                "token_type": data.get("token_type", "Bearer"),
                "expires_in": expires_in,
                "access_token_expires_at": int(time.time()) + expires_in,
            }

        err_body = resp.text
        masked_err = mask_sensitive_payload({"error": err_body, "status_code": resp.status_code})
        logger.warning("amoCRM OAuth token refresh failed: status=%s, detail=%s", resp.status_code, masked_err)
        raise AmoCRMAuthError(
            f"amoCRM OAuth refresh failed with HTTP {resp.status_code}: {err_body}",
            status_code=resp.status_code,
            response_body=err_body,
        )

    def refresh_auth(self, connection_config: Dict[str, Any]) -> Dict[str, Any]:
        """Perform distributed, double-checked, CAS-fenced amoCRM token refresh."""
        connection_id = connection_config.get("id") or connection_config.get("connection_id")
        tenant_id = connection_config.get("tenant_id")
        read_version = connection_config.get("token_version", 1)

        if not connection_id or not tenant_id:
            new_tokens = self._do_oauth_refresh(connection_config)
            updated = dict(connection_config)
            updated.update(new_tokens)
            return updated

        with AmoCRMRefreshLock(connection_id):
            # T3.4: Double-checked database read inside lock
            ok, current_record = CRMConnectionService.get_by_id_and_tenant(connection_id, tenant_id)
            if ok and current_record:
                current_config = CRMConnectionService.get_decrypted_config(current_record)
                current_expires = current_config.get("access_token_expires_at", 0)
                now = time.time()
                if current_record.token_version > read_version or current_expires > (now + 60):
                    logger.info(
                        "Token for amoCRM connection '%s' already refreshed by concurrent worker (v%s > v%s). Reusing fresh token.",
                        connection_id, current_record.token_version, read_version
                    )
                    current_config["token_version"] = current_record.token_version
                    current_config["connection_id"] = connection_id
                    current_config["tenant_id"] = tenant_id
                    return current_config

                read_version = current_record.token_version
                connection_config = current_config

            # Execute token refresh with amoCRM
            try:
                new_tokens = self._do_oauth_refresh(connection_config)
            except AmoCRMAuthError as e:
                # T3.6: Recovery read on invalid_grant / HTTP 400
                is_invalid_grant = "invalid_grant" in str(e).lower() or e.status_code == 400
                if is_invalid_grant:
                    ok, check_record = CRMConnectionService.get_by_id_and_tenant(connection_id, tenant_id)
                    if ok and check_record and check_record.token_version > read_version:
                        logger.info(
                            "amoCRM refresh got %s, but token_version increased to %s. Concurrent worker succeeded.",
                            e.status_code, check_record.token_version
                        )
                        fresh_config = CRMConnectionService.get_decrypted_config(check_record)
                        fresh_config["token_version"] = check_record.token_version
                        fresh_config["connection_id"] = connection_id
                        fresh_config["tenant_id"] = tenant_id
                        return fresh_config
                    else:
                        logger.error("amoCRM token revoked for connection '%s'. Transitioning status to reauth_required.", connection_id)
                        CRMConnectionService.update_status(connection_id, tenant_id, "reauth_required")
                        raise AmoCRMTokenRevokedError(
                            f"amoCRM OAuth refresh token revoked for connection '{connection_id}'. Status set to reauth_required."
                        ) from e
                raise

            # T3.5: Fencing token validation via atomic compare-and-swap
            updated_config = dict(connection_config)
            updated_config.update(new_tokens)

            cas_ok = CRMConnectionService.update_config(
                connection_id=connection_id,
                tenant_id=tenant_id,
                config=updated_config,
                expected_token_version=read_version,
            )
            if not cas_ok:
                logger.warning(
                    "Worker was fenced out during CAS token update for connection '%s' (version %s). Reading fresh token.",
                    connection_id, read_version
                )
                ok, fresh_record = CRMConnectionService.get_by_id_and_tenant(connection_id, tenant_id)
                if ok and fresh_record:
                    fresh_config = CRMConnectionService.get_decrypted_config(fresh_record)
                    fresh_config["token_version"] = fresh_record.token_version
                    fresh_config["connection_id"] = connection_id
                    fresh_config["tenant_id"] = tenant_id
                    return fresh_config

            updated_config["token_version"] = read_version + 1
            updated_config["connection_id"] = connection_id
            updated_config["tenant_id"] = tenant_id
            return updated_config

    def find_contact(self, connection_config: Dict[str, Any], phone: str) -> Optional[Dict[str, Any]]:
        """Look up existing amoCRM contact by phone."""
        base_url = self._get_base_url(connection_config)
        token = connection_config.get("access_token")
        if not token:
            raise AmoCRMAuthError("Missing 'access_token' in amoCRM connection configuration")

        masked_phone = mask_phone_dynamic(phone)
        logger.info("Searching amoCRM contact by phone: %s", masked_phone)

        query_val = re.sub(r"[^\d+]", "", phone.strip())
        search_url = f"{base_url}/api/v4/contacts?query={quote(query_val)}"

        resp = self.transport.get(
            search_url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            allow_redirects=False,
            timeout=15.0,
        )

        if resp.status_code == 204:
            return None
        if resp.status_code == 200:
            data = resp.json()
            contacts = data.get("_embedded", {}).get("contacts", [])
            if contacts:
                return contacts[0]
            return None
        if resp.status_code == 401:
            raise AmoCRMAuthError(f"amoCRM unauthorized (HTTP 401): {resp.text}", status_code=401)

        logger.warning("amoCRM find_contact returned HTTP %s: %s", resp.status_code, resp.text)
        return None

    def create_lead(self, connection_config: Dict[str, Any], lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create contact and lead in amoCRM, linking notes."""
        CRMProviderBase.check_management_allowed(connection_config, action_name="create_lead")
        base_url = self._get_base_url(connection_config)
        token = connection_config.get("access_token")
        if not token:
            raise AmoCRMAuthError("Missing 'access_token' in amoCRM connection configuration")

        phone = lead_data.get("phone", "")
        name = lead_data.get("name", "Incoming Lead")
        masked_phone = mask_phone_dynamic(phone)
        logger.info("Creating amoCRM lead for name='%s', phone=%s", name, masked_phone)

        # 1. Contact lookup / creation
        contact_id = None
        if phone:
            existing_contact = self.find_contact(connection_config, phone)
            if existing_contact:
                contact_id = existing_contact.get("id")

        if not contact_id:
            create_contact_url = f"{base_url}/api/v4/contacts"
            contact_payload = [
                {
                    "name": name,
                    "custom_fields_values": (
                        [{"field_code": "PHONE", "values": [{"value": phone}]}]
                        if phone else []
                    ),
                }
            ]
            resp_contact = self.transport.post(
                create_contact_url,
                json=contact_payload,
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                allow_redirects=False,
                timeout=15.0,
            )
            if resp_contact.status_code not in (200, 201):
                raise AmoCRMError(
                    f"Failed to create amoCRM contact (HTTP {resp_contact.status_code}): {resp_contact.text}"
                )
            contacts_created = resp_contact.json().get("_embedded", {}).get("contacts", [])
            if contacts_created:
                contact_id = contacts_created[0].get("id")

        # 2. Lead creation
        create_lead_url = f"{base_url}/api/v4/leads"
        title = lead_data.get("title") or f"Lead from Chat: {name}"
        price = 0
        try:
            price = int(float(lead_data.get("price") or 0))
        except (ValueError, TypeError):
            price = 0

        lead_payload_item: Dict[str, Any] = {
            "name": title,
            "price": price,
        }
        if "pipeline_id" in connection_config and connection_config["pipeline_id"]:
            try:
                lead_payload_item["pipeline_id"] = int(connection_config["pipeline_id"])
            except (ValueError, TypeError):
                pass
        elif "pipeline_id" in lead_data and lead_data["pipeline_id"]:
            try:
                lead_payload_item["pipeline_id"] = int(lead_data["pipeline_id"])
            except (ValueError, TypeError):
                pass

        if "status_id" in connection_config and connection_config["status_id"]:
            try:
                lead_payload_item["status_id"] = int(connection_config["status_id"])
            except (ValueError, TypeError):
                pass
        elif "status_id" in lead_data and lead_data["status_id"]:
            try:
                lead_payload_item["status_id"] = int(lead_data["status_id"])
            except (ValueError, TypeError):
                pass

        if contact_id:
            lead_payload_item["_embedded"] = {
                "contacts": [{"id": contact_id}]
            }

        resp_lead = self.transport.post(
            create_lead_url,
            json=[lead_payload_item],
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            allow_redirects=False,
            timeout=15.0,
        )
        if resp_lead.status_code not in (200, 201):
            raise AmoCRMError(
                f"Failed to create amoCRM lead (HTTP {resp_lead.status_code}): {resp_lead.text}"
            )
        leads_created = resp_lead.json().get("_embedded", {}).get("leads", [])
        if not leads_created:
            raise AmoCRMError("amoCRM returned 200/201 but no leads in response payload")
        lead_id = leads_created[0].get("id")

        # 3. Attach note if present
        note_text = lead_data.get("note") or lead_data.get("text")
        if note_text and lead_id:
            create_note_url = f"{base_url}/api/v4/leads/{lead_id}/notes"
            note_payload = [
                {
                    "note_type": "common",
                    "params": {"text": note_text[:2000]},
                }
            ]
            try:
                self.transport.post(
                    create_note_url,
                    json=note_payload,
                    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                    allow_redirects=False,
                    timeout=15.0,
                )
            except Exception as e:
                logger.warning("Failed to attach note to amoCRM lead %s: %s", lead_id, e)

        return {
            "crm_type": "amocrm",
            "lead_id": str(lead_id),
            "contact_id": str(contact_id) if contact_id else None,
            "status": "success",
        }

    def check_stock(self, connection_config: Dict[str, Any], item_query: str) -> Dict[str, Any]:
        """amoCRM does not support inventory or warehouse balance checking."""
        return {
            "supported": False,
            "message": "amoCRM provider does not support inventory or stock balance checks. Use 1C:Enterprise provider.",
        }

    def query_records(
        self,
        connection_config: Dict[str, Any],
        entity: str,
        query: str = "",
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Query live amoCRM / Kommo entities (leads/deals, contacts, companies)."""
        base_url = self._get_base_url(connection_config)
        token = connection_config.get("access_token")
        if not token:
            raise AmoCRMAuthError("Missing access_token in amoCRM connection configuration")

        entity_clean = entity.lower().strip().rstrip("s")
        if entity_clean in ("deal", "lead", "order"):
            endpoint = "leads"
        elif entity_clean == "contact":
            endpoint = "contacts"
        elif entity_clean == "company":
            endpoint = "companies"
        else:
            endpoint = "leads"

        max_limit = max(1, min(limit, 50))
        params: List[str] = [f"limit={max_limit}"]

        if query:
            params.append(f"query={quote(query.strip())}")

        if filters:
            if "status" in filters:
                params.append(f"filter[statuses][0][status_id]={quote(str(filters['status']))}")
            if "pipeline_id" in filters:
                params.append(f"filter[statuses][0][pipeline_id]={quote(str(filters['pipeline_id']))}")

        url = f"{base_url}/api/v4/{endpoint}?" + "&".join(params)
        logger.info("Executing amoCRM query_records url=%s", url)

        resp = self.transport.get(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            allow_redirects=False,
            timeout=15.0,
        )

        if resp.status_code == 204:
            return []
        if resp.status_code == 401:
            raise AmoCRMAuthError(f"amoCRM unauthorized (HTTP 401): {resp.text}", status_code=401)
        if resp.status_code >= 400:
            raise AmoCRMError(f"amoCRM query failed with HTTP {resp.status_code}: {resp.text}")

        data = resp.json()
        raw_items = data.get("_embedded", {}).get(endpoint, [])
        if not isinstance(raw_items, list):
            raw_items = []

        records = []
        for item in raw_items:
            phone_val = ""
            email_val = ""
            custom_fields = item.get("custom_fields_values") or []
            if isinstance(custom_fields, list):
                for cf in custom_fields:
                    code = str(cf.get("field_code") or "").upper()
                    vals = cf.get("values") or []
                    if vals and isinstance(vals, list):
                        v0 = vals[0].get("value", "")
                        if code == "PHONE" and not phone_val:
                            phone_val = str(v0)
                        elif code == "EMAIL" and not email_val:
                            email_val = str(v0)

            updated_ts = item.get("updated_at")
            updated_iso = ""
            if updated_ts:
                try:
                    import datetime
                    updated_iso = datetime.datetime.fromtimestamp(int(updated_ts), tz=datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    updated_iso = str(updated_ts)

            rec = {
                "id": str(item.get("id", "")),
                "entity": entity_clean,
                "title": item.get("name", f"{entity_clean} #{item.get('id')}"),
                "status": str(item.get("status_id") or ""),
                "price": item.get("price", 0),
                "currency": "RUB",
                "phone": phone_val,
                "email": email_val,
                "updated_at": updated_iso,
                "raw": item,
            }
            records.append(rec)
        return records
