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
from api.crm.transport import CRMTransport

logger = logging.getLogger("HubSpotConnector")

DEFAULT_ENTITIES = ["deals", "contacts", "companies", "products"]


class HubSpotConnector(LoadConnector, PollConnector, SlimConnectorWithPermSync):
    """HubSpot CRM data source connector for indexing CRM entities into Knowledge Bases."""

    BASE_URL = "https://api.hubapi.com"

    def __init__(
        self,
        access_token: str = "",
        entities: Optional[List[str] | str] = None,
        batch_size: int = 50,
    ) -> None:
        self.access_token = (access_token or "").strip()
        if isinstance(entities, str):
            self.entities = [e.strip().lower() for e in entities.split(",") if e.strip()]
        elif isinstance(entities, list):
            self.entities = [str(e).strip().lower() for e in entities if str(e).strip()]
        else:
            self.entities = list(DEFAULT_ENTITIES)
        self.batch_size = max(1, min(int(batch_size or 50), 100))
        self.transport = CRMTransport(
            private_cidr_allowlist_env="RAGFLOW_CRM_PRIVATE_ALLOWLIST_CIDR",
            allowed_schemes=frozenset({"https"}),
            default_timeout=25.0,
        )

    @classmethod
    def build_connector(cls, config: Dict[str, Any]) -> "HubSpotConnector":
        creds = config.get("credentials") or config
        token = creds.get("access_token") or ""
        entities = config.get("entities") or creds.get("entities")
        batch_size = int(config.get("batch_size") or 50)
        connector = cls(
            access_token=token,
            entities=entities,
            batch_size=batch_size,
        )
        connector.load_credentials(creds)
        return connector

    def load_credentials(self, credentials: Dict[str, Any]) -> Dict[str, Any] | None:
        token = credentials.get("access_token")
        if token:
            self.access_token = token.strip()
        return None

    def _headers(self) -> Dict[str, str]:
        if not self.access_token:
            raise ConnectorMissingCredentialError("HubSpot: Access token is missing")
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "User-Agent": "RAGFlow-HubSpot-Sync/1.0",
        }

    def _call_api(self, method: str, endpoint: str, params: Optional[Dict[str, Any]] = None, json_body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.BASE_URL}{endpoint}"
        headers = self._headers()
        try:
            if method.upper() == "POST":
                resp = self.transport.post(url, headers=headers, json=json_body or {}, timeout=25.0)
            else:
                resp = self.transport.get(url, headers=headers, params=params or {}, timeout=25.0)
        except Exception as e:
            raise ConnectorValidationError(f"HubSpot network error on {endpoint}: {e}") from e

        if resp.status_code == 401:
            raise ConnectorMissingCredentialError("HubSpot access token is invalid or expired (HTTP 401)")
        if resp.status_code == 403:
            raise InsufficientPermissionsError("HubSpot access denied (HTTP 403). Check Private App scopes.")
        if not resp.ok:
            raise UnexpectedValidationError(f"HubSpot API returned HTTP {resp.status_code}: {resp.text[:200]}")

        try:
            return resp.json()
        except Exception as e:
            raise ConnectorValidationError(f"HubSpot returned invalid JSON: {e}")

    def validate_connector_settings(self) -> None:
        if not self.access_token:
            raise ConnectorMissingCredentialError("HubSpot: Access token is required")
        res = self._call_api("GET", "/crm/v3/objects/contacts", params={"limit": 1})
        if not isinstance(res, dict) or "results" not in res:
            raise ConnectorValidationError("HubSpot validation failed: unexpected response from /crm/v3/objects/contacts")

    def _parse_datetime(self, val: Any) -> datetime:
        if not val:
            return datetime.now(timezone.utc)
        if isinstance(val, (int, float)):
            # HubSpot uses ms timestamps
            ts = val / 1000.0 if val > 1e11 else val
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        val_str = str(val).strip()
        for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(val_str, fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc)
            except ValueError:
                pass
        return datetime.now(timezone.utc)

    def _format_item_text(self, entity: str, item: Dict[str, Any]) -> str:
        props = item.get("properties") or {}
        item_id = item.get("id")
        name = (
            props.get("dealname")
            or props.get("name")
            or f"{props.get('firstname', '')} {props.get('lastname', '')}".strip()
            or f"{entity} #{item_id}"
        )
        lines = [f"# HubSpot {entity.upper()}: {name}", f"- **ID**: {item_id}"]
        for k in sorted(props.keys()):
            val = props[k]
            if val is None or val == "":
                continue
            lines.append(f"- **{k}**: {val}")
        return "\n".join(lines)

    def _fetch_entity_records(
        self,
        entity: str,
        start_ts: Optional[float] = None,
        end_ts: Optional[float] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        if start_ts is not None and start_ts > 0:
            # Incremental search using search API
            search_endpoint = f"/crm/v3/objects/{entity}/search"
            start_ms = int(start_ts * 1000)
            filters = [
                {
                    "propertyName": "hs_lastmodifieddate",
                    "operator": "GTE",
                    "value": str(start_ms),
                }
            ]
            if end_ts is not None:
                end_ms = int(end_ts * 1000)
                filters.append(
                    {
                        "propertyName": "hs_lastmodifieddate",
                        "operator": "LTE",
                        "value": str(end_ms),
                    }
                )

            after = "0"
            while True:
                payload = {
                    "filterGroups": [{"filters": filters}],
                    "limit": self.batch_size,
                    "after": after,
                }
                res = self._call_api("POST", search_endpoint, json_body=payload)
                records = res.get("results", [])
                if not isinstance(records, list) or not records:
                    break

                for rec in records:
                    yield rec

                paging = res.get("paging", {}).get("next", {})
                after = paging.get("after")
                if not after:
                    break
        else:
            # Full sync using standard GET with pagination
            endpoint = f"/crm/v3/objects/{entity}"
            after = None
            while True:
                params: Dict[str, Any] = {"limit": self.batch_size}
                if after:
                    params["after"] = after
                res = self._call_api("GET", endpoint, params=params)
                records = res.get("results", [])
                if not isinstance(records, list) or not records:
                    break

                for rec in records:
                    yield rec

                paging = res.get("paging", {}).get("next", {})
                after = paging.get("after")
                if not after:
                    break

    def _iter_documents(
        self,
        start_ts: Optional[float] = None,
        end_ts: Optional[float] = None,
    ) -> Generator[List[Document], None, None]:
        batch: List[Document] = []

        for entity in self.entities:
            try:
                for item in self._fetch_entity_records(entity, start_ts, end_ts):
                    item_id = str(item.get("id") or "")
                    if not item_id:
                        continue
                    props = item.get("properties") or {}
                    name = (
                        props.get("dealname")
                        or props.get("name")
                        or f"{props.get('firstname', '')} {props.get('lastname', '')}".strip()
                        or f"{entity} #{item_id}"
                    )
                    updated_at = self._parse_datetime(
                        props.get("hs_lastmodifieddate") or item.get("updatedAt") or item.get("createdAt")
                    )
                    text = self._format_item_text(entity, item)
                    blob = text.encode("utf-8")

                    doc = Document(
                        id=f"hubspot:{entity}:{item_id}",
                        source=DocumentSource.HUBSPOT,
                        semantic_identifier=f"HubSpot {entity.capitalize()}: {name}",
                        extension="md",
                        blob=blob,
                        doc_updated_at=updated_at,
                        size_bytes=len(blob),
                        metadata={
                            "crm": "hubspot",
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
                logger.error("Error fetching HubSpot entity %s: %s", entity, e)

        if batch:
            yield batch

    def load_from_state(self) -> Generator[List[Document], None, None]:
        """Perform full load of configured HubSpot entities."""
        return self._iter_documents(start_ts=None, end_ts=None)

    def poll_source(
        self,
        start: SecondsSinceUnixEpoch,
        end: SecondsSinceUnixEpoch,
    ) -> Generator[List[Document], None, None]:
        """Poll HubSpot for updated entities within [start, end]."""
        return self._iter_documents(start_ts=start, end_ts=end)

    def retrieve_all_slim_docs_perm_sync(
        self,
        callback: Any = None,
    ) -> Generator[List[SlimDocument], None, None]:
        """Retrieve lightweight document identifiers for prune sync."""
        del callback
        batch: List[SlimDocument] = []

        for entity in self.entities:
            try:
                for item in self._fetch_entity_records(entity):
                    item_id = str(item.get("id") or "")
                    if not item_id:
                        continue
                    batch.append(SlimDocument(id=f"hubspot:{entity}:{item_id}"))
                    if len(batch) >= self.batch_size:
                        yield batch
                        batch = []
            except Exception as e:
                logger.warning("Error fetching HubSpot slim IDs for %s: %s", entity, e)

        if batch:
            yield batch
