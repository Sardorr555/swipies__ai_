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
import base64
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

logger = logging.getLogger("OneCConnector")

DEFAULT_ENTITY = "Catalog_Номенклатура"


class OneCConnector(LoadConnector, PollConnector, SlimConnectorWithPermSync):
    """1C:Enterprise OData data source connector for indexing ERP catalogs and documents into Knowledge Bases."""

    def __init__(
        self,
        base_url: str = "",
        username: str = "",
        password: str = "",
        entity_path: Optional[str | List[str]] = None,
        catalogs: Optional[str | List[str]] = None,
        batch_size: int = 50,
    ) -> None:
        self.base_url = (base_url or "").strip().rstrip("/")
        self.username = (username or "").strip()
        self.password = password or ""
        raw_path = entity_path if entity_path is not None else catalogs
        if isinstance(raw_path, str):
            self.entity_paths = [p.strip() for p in raw_path.split(",") if p.strip()]
        elif isinstance(raw_path, list):
            self.entity_paths = [str(p).strip() for p in raw_path if str(p).strip()]
        else:
            self.entity_paths = [DEFAULT_ENTITY]
        self.catalogs = list(self.entity_paths)
        self.batch_size = max(1, min(int(batch_size or 50), 200))
        self.transport = CRMTransport(
            private_cidr_allowlist_env="RAGFLOW_CRM_PRIVATE_ALLOWLIST_CIDR",
            allowed_schemes=frozenset({"https", "http"}),
            default_timeout=30.0,
        )

    @classmethod
    def build_connector(cls, config: Dict[str, Any]) -> "OneCConnector":
        creds = config.get("credentials") or config
        base_url = creds.get("base_url") or ""
        username = creds.get("username") or ""
        password = creds.get("password") or ""
        entity_path = (
            config.get("catalogs")
            or config.get("entity_path")
            or creds.get("catalogs")
            or creds.get("entity_path")
            or DEFAULT_ENTITY
        )
        batch_size = int(config.get("batch_size") or 50)
        connector = cls(
            base_url=base_url,
            username=username,
            password=password,
            entity_path=entity_path,
            batch_size=batch_size,
        )
        connector.load_credentials(creds)
        return connector

    def load_credentials(self, credentials: Dict[str, Any]) -> Dict[str, Any] | None:
        url = credentials.get("base_url") or credentials.get("odata_base_url")
        if url:
            self.base_url = url.strip().rstrip("/")
        user = credentials.get("username")
        if user:
            self.username = user.strip()
        pwd = credentials.get("password")
        if pwd is not None:
            self.password = pwd
        epath = credentials.get("catalogs") or credentials.get("entity_path")
        if epath:
            if isinstance(epath, str):
                self.entity_paths = [p.strip() for p in epath.split(",") if p.strip()]
            elif isinstance(epath, list):
                self.entity_paths = [str(p).strip() for p in epath if str(p).strip()]
            self.catalogs = list(self.entity_paths)
        return None

    def _headers(self) -> Dict[str, str]:
        if not self.base_url:
            raise ConnectorMissingCredentialError("1C:Enterprise: Base OData URL is missing")
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "RAGFlow-1C-OData-Sync/1.0",
        }
        if self.username or self.password:
            auth_str = f"{self.username}:{self.password}"
            b64_auth = base64.b64encode(auth_str.encode("utf-8")).decode("ascii")
            headers["Authorization"] = f"Basic {b64_auth}"
        return headers

    def _call_odata(self, endpoint_url: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        headers = self._headers()
        try:
            resp = self.transport.get(endpoint_url, headers=headers, params=params or {}, timeout=30.0)
        except Exception as e:
            raise ConnectorValidationError(f"1C OData network error on {endpoint_url}: {e}") from e

        if resp.status_code == 401:
            raise ConnectorMissingCredentialError("1C OData authentication failed (HTTP 401)")
        if resp.status_code == 403:
            raise InsufficientPermissionsError("1C OData access forbidden (HTTP 403)")
        if not resp.ok:
            raise UnexpectedValidationError(f"1C OData returned HTTP {resp.status_code}: {resp.text[:200]}")

        try:
            return resp.json()
        except Exception as e:
            raise ConnectorValidationError(f"1C OData returned invalid JSON: {e}")

    def validate_connector_settings(self) -> None:
        if not self.base_url:
            raise ConnectorMissingCredentialError("1C:Enterprise: Base OData URL is required")
        try:
            validate_crm_url_and_resolve(
                self.base_url,
                allowed_schemes=frozenset({"https", "http"}),
                private_cidr_env="RAGFLOW_CRM_PRIVATE_ALLOWLIST_CIDR",
            )
        except Exception as e:
            raise ConnectorValidationError(f"1C Base URL failed validation: {e}") from e

        # Probe first entity
        target_entity = self.entity_paths[0] if self.entity_paths else DEFAULT_ENTITY
        probe_url = f"{self.base_url}/{target_entity}"
        res = self._call_odata(probe_url, params={"$top": 1, "$format": "json"})
        if not isinstance(res, dict) or "value" not in res:
            raise ConnectorValidationError(f"1C validation failed: unexpected response structure from {probe_url}")

    def _format_item_text(self, entity: str, item: Dict[str, Any]) -> str:
        name = item.get("Description") or item.get("Наименование") or item.get("Code") or item.get("Ref_Key") or "Item"
        lines = [f"# 1С {entity}: {name}"]
        for k in sorted(item.keys()):
            if k.startswith("odata.") or "@" in k:
                continue
            val = item[k]
            if val is None or val == "":
                continue
            if isinstance(val, (dict, list)):
                val = json.dumps(val, ensure_ascii=False)
            lines.append(f"- **{k}**: {val}")
        return "\n".join(lines)

    def _fetch_entity_records(
        self,
        entity: str,
        start_ts: Optional[float] = None,
        end_ts: Optional[float] = None,
        select_fields: Optional[str] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        url = f"{self.base_url}/{entity}"
        skip = 0

        while True:
            params: Dict[str, Any] = {
                "$top": self.batch_size,
                "$skip": skip,
                "$format": "json",
            }
            if select_fields:
                params["$select"] = select_fields

            # Add date filter if requested and possible
            filters = []
            if start_ts is not None and start_ts > 0:
                start_iso = datetime.fromtimestamp(start_ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
                filters.append(f"Period ge datetime'{start_iso}'")
            if end_ts is not None:
                end_iso = datetime.fromtimestamp(end_ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
                filters.append(f"Period le datetime'{end_iso}'")
            if filters:
                params["$filter"] = " and ".join(filters)

            try:
                res = self._call_odata(url, params=params)
            except Exception as e:
                # If $filter=Period fails (e.g. catalog doesn't have Period field), retry without filter
                if filters and "$filter" in params:
                    params.pop("$filter", None)
                    res = self._call_odata(url, params=params)
                else:
                    raise e

            records = res.get("value", [])
            if not isinstance(records, list) or not records:
                break

            for rec in records:
                yield rec

            if len(records) < self.batch_size:
                break
            skip += len(records)

    def _iter_documents(
        self,
        start_ts: Optional[float] = None,
        end_ts: Optional[float] = None,
    ) -> Generator[List[Document], None, None]:
        batch: List[Document] = []
        parsed_url = urlsplit(self.base_url)
        host_tag = parsed_url.hostname or "1c"

        for entity in self.entity_paths:
            try:
                for item in self._fetch_entity_records(entity, start_ts, end_ts):
                    item_id = str(item.get("Ref_Key") or item.get("Code") or item.get("ID") or "")
                    if not item_id:
                        continue
                    name = item.get("Description") or item.get("Наименование") or f"{entity} #{item_id}"
                    updated_at = datetime.now(timezone.utc)
                    for date_key in ("Period", "Date", "Дата", "ДатаИзменения"):
                        if item.get(date_key):
                            try:
                                d_val = str(item[date_key])[:19]
                                updated_at = datetime.strptime(d_val, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
                                break
                            except Exception:
                                pass

                    text = self._format_item_text(entity, item)
                    blob = text.encode("utf-8")

                    doc = Document(
                        id=f"1c:{host_tag}:{entity}:{item_id}",
                        source=DocumentSource.ONE_C,
                        semantic_identifier=f"1C {entity}: {name}",
                        extension="md",
                        blob=blob,
                        doc_updated_at=updated_at,
                        size_bytes=len(blob),
                        metadata={
                            "crm": "1c_odata",
                            "host": host_tag,
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
                logger.error("Error fetching 1C entity %s: %s", entity, e)

        if batch:
            yield batch

    def load_from_state(self) -> Generator[List[Document], None, None]:
        """Perform full load of configured 1C OData entities."""
        return self._iter_documents(start_ts=None, end_ts=None)

    def poll_source(
        self,
        start: SecondsSinceUnixEpoch,
        end: SecondsSinceUnixEpoch,
    ) -> Generator[List[Document], None, None]:
        """Poll 1C OData for updated entities within [start, end]."""
        return self._iter_documents(start_ts=start, end_ts=end)

    def retrieve_all_slim_docs_perm_sync(
        self,
        callback: Any = None,
    ) -> Generator[List[SlimDocument], None, None]:
        """Retrieve lightweight document identifiers for prune sync."""
        del callback
        batch: List[SlimDocument] = []
        parsed_url = urlsplit(self.base_url)
        host_tag = parsed_url.hostname or "1c"

        for entity in self.entity_paths:
            try:
                for item in self._fetch_entity_records(entity, select_fields="Ref_Key,Code"):
                    item_id = str(item.get("Ref_Key") or item.get("Code") or "")
                    if not item_id:
                        continue
                    batch.append(SlimDocument(id=f"1c:{host_tag}:{entity}:{item_id}"))
                    if len(batch) >= self.batch_size:
                        yield batch
                        batch = []
            except Exception as e:
                logger.warning("Error fetching 1C slim IDs for %s: %s", entity, e)

        if batch:
            yield batch
