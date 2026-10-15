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
from datetime import datetime, timezone
import json
import logging
from typing import Any, Dict, Generator, List, Optional
from urllib.parse import urlsplit

import requests

from common.data_source.config import DocumentSource, INDEX_BATCH_SIZE
from common.data_source.exceptions import (
    ConnectorMissingCredentialError,
    ConnectorValidationError,
    InsufficientPermissionsError,
    UnexpectedValidationError,
)
from common.data_source.interfaces import (
    LoadConnector,
    PollConnector,
    SecondsSinceUnixEpoch,
    SlimConnectorWithPermSync,
)
from common.data_source.models import Document, SlimDocument
from api.crm.transport import CRMTransport, validate_crm_url_and_resolve
from api.crm.clients.amocrm import is_valid_amocrm_url

logger = logging.getLogger("AmoCRMConnector")

DEFAULT_ENTITIES = ["leads", "contacts", "companies"]


class AmoCRMConnector(LoadConnector, PollConnector, SlimConnectorWithPermSync):
    """amoCRM and Kommo data source connector for indexing CRM entities into Knowledge Bases."""

    def __init__(
        self,
        subdomain: str = "",
        access_token: str = "",
        client_id: str = "",
        client_secret: str = "",
        entities: Optional[List[str] | str] = None,
        batch_size: int = 50,
        is_kommo: bool = False,
    ) -> None:
        self.subdomain = (subdomain or "").strip().lower()
        self.access_token = (access_token or "").strip()
        self.client_id = (client_id or "").strip()
        self.client_secret = (client_secret or "").strip()
        if isinstance(entities, str):
            self.entities = [e.strip().lower() for e in entities.split(",") if e.strip()]
        elif isinstance(entities, list):
            self.entities = [str(e).strip().lower() for e in entities if str(e).strip()]
        else:
            self.entities = list(DEFAULT_ENTITIES)
        self.batch_size = max(1, min(int(batch_size or 50), 250))
        self.is_kommo = is_kommo
        self.transport = CRMTransport(
            private_cidr_allowlist_env="RAGFLOW_CRM_PRIVATE_ALLOWLIST_CIDR",
            allowed_schemes=frozenset({"https"}),
            default_timeout=20.0,
        )

    @classmethod
    def build_connector(cls, config: Dict[str, Any]) -> "AmoCRMConnector":
        creds = config.get("credentials") or config
        subdomain = creds.get("subdomain") or creds.get("base_domain") or ""
        token = creds.get("access_token") or ""
        client_id = creds.get("client_id") or ""
        client_secret = creds.get("client_secret") or ""
        entities = config.get("entities") or creds.get("entities")
        batch_size = int(config.get("batch_size") or 50)
        is_kommo = "kommo.com" in subdomain or config.get("source") == "kommo"
        connector = cls(
            subdomain=subdomain,
            access_token=token,
            client_id=client_id,
            client_secret=client_secret,
            entities=entities,
            batch_size=batch_size,
            is_kommo=is_kommo,
        )
        connector.load_credentials(creds)
        return connector

    def load_credentials(self, credentials: Dict[str, Any]) -> Dict[str, Any] | None:
        subdomain = credentials.get("subdomain") or credentials.get("base_domain")
        if subdomain:
            self.subdomain = subdomain.strip().lower()
        token = credentials.get("access_token")
        if token:
            self.access_token = token.strip()
        cid = credentials.get("client_id")
        if cid:
            self.client_id = cid.strip()
        csec = credentials.get("client_secret")
        if csec:
            self.client_secret = csec.strip()
        if "kommo.com" in self.subdomain:
            self.is_kommo = True
        return None

    def _get_base_url(self) -> str:
        domain = self.subdomain.strip()
        if not domain:
            raise ConnectorMissingCredentialError("amoCRM: Subdomain/domain is required")
        if not domain.startswith("http://") and not domain.startswith("https://"):
            domain = f"https://{domain}"
        parsed = urlsplit(domain)
        host = (parsed.hostname or domain).lower()
        if not ("." in host):
            suffix = "kommo.com" if self.is_kommo else "amocrm.ru"
            host = f"{host}.{suffix}"
        return f"https://{host}"

    def _call_api(self, endpoint_path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not self.access_token:
            raise ConnectorMissingCredentialError("amoCRM: Access token is missing")
        base_url = self._get_base_url()
        url = f"{base_url}{endpoint_path}"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "User-Agent": "RAGFlow-CRM-Sync/1.0",
        }
        try:
            resp = self.transport.get(url, headers=headers, params=params or {}, timeout=25.0)
        except Exception as e:
            raise ConnectorValidationError(f"amoCRM network error on {endpoint_path}: {e}") from e

        if resp.status_code == 204:
            return {}
        if resp.status_code == 401:
            raise ConnectorMissingCredentialError("amoCRM access token is invalid or expired (HTTP 401)")
        if resp.status_code == 403:
            raise InsufficientPermissionsError("amoCRM access denied (HTTP 403)")
        if not resp.ok:
            raise UnexpectedValidationError(f"amoCRM API returned HTTP {resp.status_code}: {resp.text[:200]}")

        try:
            return resp.json()
        except Exception as e:
            raise ConnectorValidationError(f"amoCRM returned invalid JSON: {e}")

    def validate_connector_settings(self) -> None:
        base_url = self._get_base_url()
        is_valid, err = is_valid_amocrm_url(base_url)
        if not is_valid:
            raise ConnectorValidationError(f"Invalid amoCRM/Kommo URL: {err}")

        # Probe account endpoint
        res = self._call_api("/api/v4/account")
        if not isinstance(res, dict) or "id" not in res:
            raise ConnectorValidationError("amoCRM validation failed: unexpected response from /api/v4/account")

    def _format_item_text(self, entity: str, item: Dict[str, Any]) -> str:
        name = item.get("name") or item.get("title") or item.get("id")
        lines = [f"# {('Kommo' if self.is_kommo else 'amoCRM')} {entity.upper()}: {name}"]
        for k in ("id", "name", "price", "status_id", "pipeline_id", "responsible_user_id", "created_at", "updated_at"):
            if k in item and item[k] is not None:
                val = item[k]
                if "created_at" in k or "updated_at" in k:
                    try:
                        val = datetime.fromtimestamp(int(val), tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
                    except Exception:
                        pass
                lines.append(f"- **{k}**: {val}")

        # Format custom fields if present
        cf_list = item.get("custom_fields_values")
        if isinstance(cf_list, list):
            lines.append("## Custom Fields:")
            for cf in cf_list:
                fname = cf.get("field_name") or f"Field_{cf.get('field_id')}"
                values = [v.get("value") for v in cf.get("values", []) if "value" in v]
                val_str = ", ".join(str(v) for v in values if v is not None)
                if val_str:
                    lines.append(f"- **{fname}**: {val_str}")

        return "\n".join(lines)

    def _fetch_entity_records(
        self,
        entity: str,
        start_ts: Optional[float] = None,
        end_ts: Optional[float] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        endpoint = f"/api/v4/{entity}"
        page = 1

        while True:
            params: Dict[str, Any] = {
                "page": page,
                "limit": self.batch_size,
            }
            if start_ts is not None and start_ts > 0:
                params["filter[updated_at][from]"] = int(start_ts)
            if end_ts is not None:
                params["filter[updated_at][to]"] = int(end_ts)

            res = self._call_api(endpoint, params=params)
            if not res or "_embedded" not in res:
                break
            records = res["_embedded"].get(entity, [])
            if not isinstance(records, list) or not records:
                break

            for rec in records:
                yield rec

            # amoCRM provides links.next or we stop if records < limit
            if len(records) < self.batch_size:
                break
            page += 1

    def _iter_documents(
        self,
        start_ts: Optional[float] = None,
        end_ts: Optional[float] = None,
    ) -> Generator[List[Document], None, None]:
        batch: List[Document] = []
        domain_tag = urlsplit(self._get_base_url()).hostname or self.subdomain
        source_name = DocumentSource.KOMMO if self.is_kommo else DocumentSource.AMOCRM

        for entity in self.entities:
            try:
                for item in self._fetch_entity_records(entity, start_ts, end_ts):
                    item_id = str(item.get("id") or "")
                    if not item_id:
                        continue
                    name = item.get("name") or f"{entity} #{item_id}"
                    updated_ts = item.get("updated_at") or item.get("created_at") or 0
                    try:
                        updated_at = datetime.fromtimestamp(int(updated_ts), tz=timezone.utc)
                    except Exception:
                        updated_at = datetime.now(timezone.utc)

                    text = self._format_item_text(entity, item)
                    blob = text.encode("utf-8")

                    doc = Document(
                        id=f"{('kommo' if self.is_kommo else 'amocrm')}:{domain_tag}:{entity}:{item_id}",
                        source=source_name,
                        semantic_identifier=f"{('Kommo' if self.is_kommo else 'amoCRM')} {entity.capitalize()}: {name}",
                        extension="md",
                        blob=blob,
                        doc_updated_at=updated_at,
                        size_bytes=len(blob),
                        metadata={
                            "crm": "kommo" if self.is_kommo else "amocrm",
                            "domain": domain_tag,
                            "entity": entity,
                            "record_id": item_id,
                            "title": name,
                        },
                    )
                    batch.append(doc)
                    if len(batch) >= self.batch_size:
                        yield batch
                        batch = []
            except Exception as e:
                logger.error("Error fetching amoCRM entity %s: %s", entity, e)

        if batch:
            yield batch

    def load_from_state(self) -> Generator[List[Document], None, None]:
        """Perform full load of configured amoCRM entities."""
        return self._iter_documents(start_ts=None, end_ts=None)

    def poll_source(
        self,
        start: SecondsSinceUnixEpoch,
        end: SecondsSinceUnixEpoch,
    ) -> Generator[List[Document], None, None]:
        """Poll amoCRM for updated entities within [start, end]."""
        return self._iter_documents(start_ts=start, end_ts=end)

    def retrieve_all_slim_docs_perm_sync(
        self,
        callback: Any = None,
    ) -> Generator[List[SlimDocument], None, None]:
        """Retrieve lightweight document identifiers for prune sync."""
        del callback
        batch: List[SlimDocument] = []
        domain_tag = urlsplit(self._get_base_url()).hostname or self.subdomain
        prefix = "kommo" if self.is_kommo else "amocrm"

        for entity in self.entities:
            try:
                for item in self._fetch_entity_records(entity):
                    item_id = str(item.get("id") or "")
                    if not item_id:
                        continue
                    batch.append(SlimDocument(id=f"{prefix}:{domain_tag}:{entity}:{item_id}"))
                    if len(batch) >= self.batch_size:
                        yield batch
                        batch = []
            except Exception as e:
                logger.warning("Error fetching amoCRM slim IDs for %s: %s", entity, e)

        if batch:
            yield batch
