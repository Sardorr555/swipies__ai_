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

logger = logging.getLogger("Bitrix24Connector")

DEFAULT_ENTITIES = ["deal", "lead", "contact", "company", "product"]


class Bitrix24Connector(LoadConnector, PollConnector, SlimConnectorWithPermSync):
    """Bitrix24 CRM data source connector for indexing CRM entities into Knowledge Bases."""

    def __init__(
        self,
        domain: str = "",
        webhook_url: str = "",
        entities: Optional[List[str] | str] = None,
        batch_size: int = 50,
    ) -> None:
        self.domain = (domain or "").strip().lower()
        self.webhook_url = (webhook_url or "").strip()
        if isinstance(entities, str):
            self.entities = [e.strip().lower() for e in entities.split(",") if e.strip()]
        elif isinstance(entities, list):
            self.entities = [str(e).strip().lower() for e in entities if str(e).strip()]
        else:
            self.entities = list(DEFAULT_ENTITIES)
        self.batch_size = max(1, min(int(batch_size or 50), 50))
        self.transport = CRMTransport(
            private_cidr_allowlist_env="RAGFLOW_CRM_PRIVATE_ALLOWLIST_CIDR",
            allowed_schemes=frozenset({"https"}),
            default_timeout=20.0,
        )

    @classmethod
    def build_connector(cls, config: Dict[str, Any]) -> "Bitrix24Connector":
        creds = config.get("credentials") or config
        webhook = creds.get("webhook_url") or creds.get("access_token") or ""
        domain = creds.get("domain") or ""
        entities = config.get("entities") or creds.get("entities")
        batch_size = int(config.get("batch_size") or 50)
        connector = cls(
            domain=domain,
            webhook_url=webhook,
            entities=entities,
            batch_size=batch_size,
        )
        connector.load_credentials(creds)
        return connector

    def load_credentials(self, credentials: Dict[str, Any]) -> Dict[str, Any] | None:
        webhook = credentials.get("webhook_url") or credentials.get("access_token") or ""
        if webhook:
            self.webhook_url = webhook.strip()
        domain = credentials.get("domain") or ""
        if domain:
            self.domain = domain.strip().lower()
        if not self.domain and self.webhook_url:
            parsed = urlsplit(self.webhook_url)
            if parsed.hostname:
                self.domain = parsed.hostname.lower()
        return None

    def _get_base_url(self) -> str:
        url = self.webhook_url.strip()
        if not url:
            if not self.domain:
                raise ConnectorMissingCredentialError("Bitrix24: Missing domain or webhook URL")
            raise ConnectorMissingCredentialError("Bitrix24: Missing webhook URL")
        return url.rstrip("/")

    def _call_api(self, method: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        base_url = self._get_base_url()
        endpoint = f"{base_url}/{method}.json"
        body = payload or {}
        try:
            resp = self.transport.post(endpoint, json=body, timeout=25.0)
        except Exception as e:
            raise ConnectorValidationError(f"Bitrix24 network error connecting to {method}: {e}") from e

        if resp.status_code == 401:
            raise ConnectorMissingCredentialError("Bitrix24 webhook authentication failed (HTTP 401)")
        if resp.status_code == 403:
            raise InsufficientPermissionsError("Bitrix24 webhook access denied (HTTP 403)")
        if not resp.ok:
            raise UnexpectedValidationError(f"Bitrix24 API returned HTTP {resp.status_code}: {resp.text[:200]}")

        try:
            data = resp.json()
        except Exception as e:
            raise ConnectorValidationError(f"Bitrix24 returned invalid JSON: {e}")

        if "error" in data:
            err = data.get("error")
            desc = data.get("error_description", "")
            if str(err).upper() in ("INVALID_CREDENTIALS", "WRONG_AUTH_TYPE", "AUTHORIZATION_ERROR"):
                raise ConnectorMissingCredentialError(f"Bitrix24 authentication error: {desc}")
            raise ConnectorValidationError(f"Bitrix24 API error ({err}): {desc}")

        return data

    def validate_connector_settings(self) -> None:
        if not self.webhook_url:
            raise ConnectorMissingCredentialError("Bitrix24 webhook URL is required")
        try:
            validate_crm_url_and_resolve(
                self.webhook_url,
                allowed_schemes=frozenset({"https"}),
                private_cidr_env="RAGFLOW_CRM_PRIVATE_ALLOWLIST_CIDR",
            )
        except Exception as e:
            raise ConnectorValidationError(f"Bitrix24 webhook URL failed validation: {e}") from e

        # Ping API with crm.deal.fields
        res = self._call_api("crm.deal.fields")
        if not isinstance(res, dict) or "result" not in res:
            raise ConnectorValidationError("Bitrix24 validation failed: unexpected response from crm.deal.fields")

    def _parse_datetime(self, val: Any) -> datetime:
        if not val:
            return datetime.now(timezone.utc)
        if isinstance(val, (int, float)):
            return datetime.fromtimestamp(val, tz=timezone.utc)
        val_str = str(val).strip()
        for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(val_str, fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc)
            except ValueError:
                pass
        return datetime.now(timezone.utc)

    def _format_item_text(self, entity: str, item: Dict[str, Any]) -> str:
        title = item.get("TITLE") or item.get("NAME") or item.get("ID")
        lines = [f"# Bitrix24 {entity.upper()}: {title}"]
        for k in sorted(item.keys()):
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
        select_fields: Optional[List[str]] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        method = f"crm.{entity}.list"
        order = {"DATE_MODIFY": "ASC"}
        filters: Dict[str, Any] = {}

        if start_ts is not None and start_ts > 0:
            start_iso = datetime.fromtimestamp(start_ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            filters[">=DATE_MODIFY"] = start_iso
        if end_ts is not None:
            end_iso = datetime.fromtimestamp(end_ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            filters["<=DATE_MODIFY"] = end_iso

        start_cursor = 0
        while True:
            payload: Dict[str, Any] = {
                "order": order,
                "start": start_cursor,
            }
            if filters:
                payload["filter"] = filters
            if select_fields:
                payload["select"] = select_fields

            res = self._call_api(method, payload)
            records = res.get("result", [])
            if not isinstance(records, list) or not records:
                break

            for rec in records:
                yield rec

            if "next" in res and res["next"]:
                start_cursor = int(res["next"])
            else:
                break

    def _iter_documents(
        self,
        start_ts: Optional[float] = None,
        end_ts: Optional[float] = None,
    ) -> Generator[List[Document], None, None]:
        batch: List[Document] = []
        domain_tag = self.domain or "portal"

        for entity in self.entities:
            try:
                for item in self._fetch_entity_records(entity, start_ts, end_ts):
                    item_id = str(item.get("ID") or "")
                    if not item_id:
                        continue
                    title = item.get("TITLE") or item.get("NAME") or f"{entity} #{item_id}"
                    updated_at = self._parse_datetime(item.get("DATE_MODIFY") or item.get("DATE_CREATE") or item.get("TIMESTAMP_X"))
                    text = self._format_item_text(entity, item)
                    blob = text.encode("utf-8")

                    doc = Document(
                        id=f"bitrix24:{domain_tag}:{entity}:{item_id}",
                        source=DocumentSource.BITRIX24,
                        semantic_identifier=f"Bitrix24 {entity.capitalize()}: {title}",
                        extension="md",
                        blob=blob,
                        doc_updated_at=updated_at,
                        size_bytes=len(blob),
                        metadata={
                            "crm": "bitrix24",
                            "domain": self.domain,
                            "entity": entity,
                            "record_id": item_id,
                            "title": title,
                        },
                    )
                    batch.append(doc)
                    if len(batch) >= self.batch_size:
                        yield batch
                        batch = []
            except Exception as e:
                logger.error("Error fetching Bitrix24 entity %s: %s", entity, e)

        if batch:
            yield batch

    def load_from_state(self) -> Generator[List[Document], None, None]:
        """Perform full load of configured Bitrix24 entities."""
        return self._iter_documents(start_ts=None, end_ts=None)

    def poll_source(
        self,
        start: SecondsSinceUnixEpoch,
        end: SecondsSinceUnixEpoch,
    ) -> Generator[List[Document], None, None]:
        """Poll Bitrix24 for updated entities within [start, end]."""
        return self._iter_documents(start_ts=start, end_ts=end)

    def retrieve_all_slim_docs_perm_sync(
        self,
        callback: Any = None,
    ) -> Generator[List[SlimDocument], None, None]:
        """Retrieve lightweight document identifiers for prune sync."""
        del callback
        batch: List[SlimDocument] = []
        domain_tag = self.domain or "portal"

        for entity in self.entities:
            try:
                for item in self._fetch_entity_records(entity, select_fields=["ID"]):
                    item_id = str(item.get("ID") or "")
                    if not item_id:
                        continue
                    batch.append(SlimDocument(id=f"bitrix24:{domain_tag}:{entity}:{item_id}"))
                    if len(batch) >= self.batch_size:
                        yield batch
                        batch = []
            except Exception as e:
                logger.warning("Error fetching Bitrix24 slim IDs for %s: %s", entity, e)

        if batch:
            yield batch
