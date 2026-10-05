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
"""Step 5: Comprehensive Unit & Integration Tests for all 5 CRM Connectors as RAG Data Sources."""

from __future__ import annotations

import warnings
warnings.filterwarnings("ignore", message=".*doesn't match a supported version.*")
warnings.filterwarnings("ignore", category=ResourceWarning)

import json
from unittest.mock import MagicMock, patch
import pytest

from api.db.db_models import DB
DB.connect = lambda *a, **kw: True
DB.connection_context = lambda: (lambda fn: fn)

from common.constants import FileSource
from common.data_source.config import DocumentSource
from common.data_source.exceptions import (
    ConnectorMissingCredentialError,
    ConnectorValidationError,
    InsufficientPermissionsError,
    UnexpectedValidationError,
)
from common.data_source.bitrix24_connector import Bitrix24Connector
from common.data_source.amocrm_connector import AmoCRMConnector
from common.data_source.hubspot_connector import HubSpotConnector
from common.data_source.onec_connector import OneCConnector

import importlib
import sys


def _import_sync_module():
    for _ in range(30):
        try:
            return importlib.import_module("rag.svr.sync_data_source")
        except ModuleNotFoundError as exc:
            missing = exc.name or ""
            if not missing or missing.split(".")[0] in {"rag", "api", "common", "agent"}:
                raise
            parts = missing.split(".")
            for i in range(1, len(parts) + 1):
                sys.modules.setdefault(".".join(parts[:i]), MagicMock())
            for key in [k for k in sys.modules if k.startswith("rag.svr.sync_data_source")]:
                sys.modules.pop(key, None)
    raise ImportError("Could not import rag.svr.sync_data_source")


_sync = _import_sync_module()
Bitrix24Worker = _sync.Bitrix24
AmoCRMWorker = _sync.AmoCRM
KommoWorker = _sync.Kommo
HubSpotWorker = _sync.HubSpot
OneCWorker = _sync.OneC


class TestBitrix24ConnectorDeep:
    """Deep validation of Bitrix24Connector: validation, paging, mapping, incremental sync, slim docs."""

    def test_missing_credentials_validation(self):
        c = Bitrix24Connector()
        with pytest.raises(ConnectorMissingCredentialError):
            c.validate_connector_settings()

    def test_ssrf_attempt_rejected(self):
        c = Bitrix24Connector(webhook_url="http://169.254.169.254/rest/1/webhook/")
        with pytest.raises(ConnectorValidationError):
            c.validate_connector_settings()

    def test_api_auth_errors_handling(self):
        c = Bitrix24Connector(webhook_url="https://test.bitrix24.com/rest/1/key/")

        # 401
        mock_resp_401 = MagicMock(status_code=401, ok=False)
        with patch.object(c.transport, "post", return_value=mock_resp_401):
            with pytest.raises(ConnectorMissingCredentialError):
                c.validate_connector_settings()

        # 403
        mock_resp_403 = MagicMock(status_code=403, ok=False)
        with patch.object(c.transport, "post", return_value=mock_resp_403):
            with pytest.raises(InsufficientPermissionsError):
                c.validate_connector_settings()

        # 500
        mock_resp_500 = MagicMock(status_code=500, ok=False, text="Server Error")
        with patch.object(c.transport, "post", return_value=mock_resp_500):
            with pytest.raises(UnexpectedValidationError):
                c.validate_connector_settings()

    def test_successful_validation(self):
        c = Bitrix24Connector(webhook_url="https://test.bitrix24.com/rest/1/key/")
        mock_resp = MagicMock(status_code=200, ok=True)
        mock_resp.json.return_value = {"result": {"ID": {"type": "integer"}}}
        with patch.object(c.transport, "post", return_value=mock_resp):
            c.validate_connector_settings()  # Should succeed without error

    def test_load_from_state_paging_and_mapping(self):
        c = Bitrix24Connector(
            domain="test.bitrix24.com",
            webhook_url="https://test.bitrix24.com/rest/1/key/",
            entities=["deal"],
            batch_size=2,
        )

        page1 = {
            "result": [
                {"ID": "101", "TITLE": "Big Deal 1", "OPPORTUNITY": 50000, "DATE_MODIFY": "2026-03-01 12:00:00"},
                {"ID": "102", "TITLE": "Big Deal 2", "OPPORTUNITY": 75000, "DATE_MODIFY": "2026-03-02 14:00:00"},
            ],
            "next": "2",
        }
        page2 = {
            "result": [
                {"ID": "103", "TITLE": "Big Deal 3", "OPPORTUNITY": 100000, "DATE_MODIFY": "2026-03-03 16:00:00"},
            ]
        }

        mock_resp1 = MagicMock(status_code=200, ok=True)
        mock_resp1.json.return_value = page1
        mock_resp2 = MagicMock(status_code=200, ok=True)
        mock_resp2.json.return_value = page2

        with patch.object(c.transport, "post", side_effect=[mock_resp1, mock_resp2]):
            batches = list(c.load_from_state())

        assert len(batches) == 2
        # Batch 1 (size 2)
        assert len(batches[0]) == 2
        assert batches[0][0].id == "bitrix24:test.bitrix24.com:deal:101"
        assert batches[0][0].source == DocumentSource.BITRIX24
        assert "Big Deal 1" in batches[0][0].blob.decode("utf-8")
        assert batches[0][0].metadata["record_id"] == "101"

        # Batch 2 (remainder: 1)
        assert len(batches[1]) == 1
        assert batches[1][0].id == "bitrix24:test.bitrix24.com:deal:103"

    def test_poll_source_incremental_filter(self):
        c = Bitrix24Connector(
            domain="test.bitrix24.com",
            webhook_url="https://test.bitrix24.com/rest/1/key/",
            entities=["lead"],
            batch_size=50,
        )
        mock_resp = MagicMock(status_code=200, ok=True)
        mock_resp.json.return_value = {"result": [{"ID": "201", "TITLE": "New Lead"}]}

        with patch.object(c.transport, "post", return_value=mock_resp) as mock_post:
            batches = list(c.poll_source(start=1772500000, end=1772600000))

        assert len(batches) == 1
        assert batches[0][0].id == "bitrix24:test.bitrix24.com:lead:201"
        called_payload = mock_post.call_args[1]["json"]
        assert ">=DATE_MODIFY" in called_payload["filter"]
        assert "<=DATE_MODIFY" in called_payload["filter"]

    def test_retrieve_all_slim_docs(self):
        c = Bitrix24Connector(
            domain="test.bitrix24.com",
            webhook_url="https://test.bitrix24.com/rest/1/key/",
            entities=["contact"],
            batch_size=10,
        )
        mock_resp = MagicMock(status_code=200, ok=True)
        mock_resp.json.return_value = {"result": [{"ID": "301"}, {"ID": "302"}]}
        with patch.object(c.transport, "post", return_value=mock_resp):
            slims = list(c.retrieve_all_slim_docs_perm_sync())
        assert len(slims) == 1
        assert len(slims[0]) == 2
        assert slims[0][0].id == "bitrix24:test.bitrix24.com:contact:301"


class TestAmoCRMAndKommoConnectorDeep:
    """Deep validation of AmoCRMConnector (both amoCRM and Kommo modes)."""

    def test_missing_credentials_validation(self):
        c = AmoCRMConnector()
        with pytest.raises(ConnectorMissingCredentialError):
            c.validate_connector_settings()

    def test_ssrf_attempt_rejected(self):
        c = AmoCRMConnector(
            subdomain="169.254.169.254",
            access_token="tok",
        )
        with pytest.raises(ConnectorValidationError):
            c.validate_connector_settings()

    def test_auth_failure_handling(self):
        c = AmoCRMConnector(
            subdomain="mycompany.amocrm.ru",
            access_token="invalid_token",
        )
        mock_resp_401 = MagicMock(status_code=401, ok=False)
        with patch.object(c.transport, "get", return_value=mock_resp_401):
            with pytest.raises(ConnectorMissingCredentialError):
                c.validate_connector_settings()

    def test_successful_amocrm_validation(self):
        c = AmoCRMConnector(
            subdomain="mycompany.amocrm.ru",
            access_token="valid_token",
        )
        mock_resp = MagicMock(status_code=200, ok=True)
        mock_resp.json.return_value = {"id": 12345, "name": "Test Account"}
        with patch.object(c.transport, "get", return_value=mock_resp):
            c.validate_connector_settings()

    def test_kommo_load_from_state_paging_and_mapping(self):
        c = AmoCRMConnector(
            subdomain="myteam.kommo.com",
            access_token="tok",
            entities=["leads"],
            batch_size=2,
            is_kommo=True,
        )

        page1 = {
            "_embedded": {
                "leads": [
                    {"id": 501, "name": "Kommo Deal 1", "price": 12000, "updated_at": 1772500100},
                    {"id": 502, "name": "Kommo Deal 2", "price": 25000, "updated_at": 1772500200},
                ]
            }
        }
        page2 = {
            "_embedded": {
                "leads": [
                    {"id": 503, "name": "Kommo Deal 3", "price": 40000, "updated_at": 1772500300},
                ]
            }
        }

        mock_resp1 = MagicMock(status_code=200, ok=True)
        mock_resp1.json.return_value = page1
        mock_resp2 = MagicMock(status_code=200, ok=True)
        mock_resp2.json.return_value = page2
        mock_resp3 = MagicMock(status_code=204, ok=True)  # amoCRM returns 204 when no more pages

        with patch.object(c.transport, "get", side_effect=[mock_resp1, mock_resp2, mock_resp3]):
            batches = list(c.load_from_state())

        assert len(batches) == 2
        assert batches[0][0].id == "kommo:myteam.kommo.com:leads:501"
        assert batches[0][0].source == DocumentSource.KOMMO
        assert batches[0][0].metadata["crm"] == "kommo"
        assert "Kommo Deal 1" in batches[0][0].blob.decode("utf-8")

        assert len(batches[1]) == 1
        assert batches[1][0].id == "kommo:myteam.kommo.com:leads:503"

    def test_poll_source_incremental_range(self):
        c = AmoCRMConnector(
            subdomain="corp.amocrm.ru",
            access_token="tok",
            entities=["contacts"],
            batch_size=50,
        )
        mock_resp = MagicMock(status_code=200, ok=True)
        mock_resp.json.return_value = {
            "_embedded": {
                "contacts": [
                    {"id": 701, "name": "Ivan Contact", "updated_at": 1772500500}
                ]
            }
        }
        with patch.object(c.transport, "get", return_value=mock_resp) as mock_get:
            batches = list(c.poll_source(start=1772500000, end=1772600000))

        assert len(batches) == 1
        assert batches[0][0].id == "amocrm:corp.amocrm.ru:contacts:701"
        called_params = mock_get.call_args[1]["params"]
        assert called_params["filter[updated_at][from]"] == 1772500000
        assert called_params["filter[updated_at][to]"] == 1772600000


class TestHubSpotConnectorDeep:
    """Deep validation of HubSpotConnector."""

    def test_missing_token_validation(self):
        c = HubSpotConnector()
        with pytest.raises(ConnectorMissingCredentialError):
            c.validate_connector_settings()

    def test_hubspot_api_auth_errors(self):
        c = HubSpotConnector(access_token="bad_token")
        mock_401 = MagicMock(status_code=401, ok=False)
        with patch.object(c.transport, "get", return_value=mock_401):
            with pytest.raises(ConnectorMissingCredentialError):
                c.validate_connector_settings()

        mock_403 = MagicMock(status_code=403, ok=False)
        with patch.object(c.transport, "get", return_value=mock_403):
            with pytest.raises(InsufficientPermissionsError):
                c.validate_connector_settings()

    def test_successful_validation(self):
        c = HubSpotConnector(access_token="pat-valid-token")
        mock_200 = MagicMock(status_code=200, ok=True)
        mock_200.json.return_value = {"results": []}
        with patch.object(c.transport, "get", return_value=mock_200):
            c.validate_connector_settings()

    def test_load_from_state_paging_cursor(self):
        c = HubSpotConnector(
            access_token="pat-test-token",
            entities=["deals"],
            batch_size=2,
        )

        page1 = {
            "results": [
                {"id": "hs_1", "properties": {"dealname": "Deal Alpha", "amount": "15000", "hs_lastmodifieddate": "2026-03-01T10:00:00Z"}},
                {"id": "hs_2", "properties": {"dealname": "Deal Beta", "amount": "30000", "hs_lastmodifieddate": "2026-03-02T12:00:00Z"}},
            ],
            "paging": {"next": {"after": "cursor_page_2"}},
        }
        page2 = {
            "results": [
                {"id": "hs_3", "properties": {"dealname": "Deal Gamma", "amount": "45000", "hs_lastmodifieddate": "2026-03-03T15:00:00Z"}},
            ]
        }

        mock1 = MagicMock(status_code=200, ok=True)
        mock1.json.return_value = page1
        mock2 = MagicMock(status_code=200, ok=True)
        mock2.json.return_value = page2

        with patch.object(c.transport, "get", side_effect=[mock1, mock2]):
            batches = list(c.load_from_state())

        assert len(batches) == 2
        assert batches[0][0].id == "hubspot:deals:hs_1"
        assert batches[0][0].source == DocumentSource.HUBSPOT
        assert "Deal Alpha" in batches[0][0].blob.decode("utf-8")
        assert batches[1][0].id == "hubspot:deals:hs_3"


class TestOneCConnectorDeep:
    """Deep validation of OneCConnector."""

    def test_missing_base_url(self):
        c = OneCConnector()
        with pytest.raises(ConnectorMissingCredentialError):
            c.validate_connector_settings()

    def test_ssrf_attempt_rejected(self):
        c = OneCConnector(base_url="http://169.254.169.254/odata/")
        with pytest.raises(ConnectorValidationError):
            c.validate_connector_settings()

    def test_auth_failures(self):
        c = OneCConnector(
            base_url="https://1c.example.com/base/odata/standard.odata",
            username="bad_user",
            password="pwd",
        )
        mock_401 = MagicMock(status_code=401, ok=False)
        with patch("common.data_source.onec_connector.validate_crm_url_and_resolve", return_value=("https://1c.example.com/base/odata/standard.odata", "1.2.3.4", 443)), \
             patch.object(c.transport, "get", return_value=mock_401):
            with pytest.raises(ConnectorMissingCredentialError):
                c.validate_connector_settings()

        mock_403 = MagicMock(status_code=403, ok=False)
        with patch("common.data_source.onec_connector.validate_crm_url_and_resolve", return_value=("https://1c.example.com/base/odata/standard.odata", "1.2.3.4", 443)), \
             patch.object(c.transport, "get", return_value=mock_403):
            with pytest.raises(InsufficientPermissionsError):
                c.validate_connector_settings()

    def test_successful_validation(self):
        c = OneCConnector(
            base_url="https://1c.example.com/base/odata/standard.odata",
            username="odata_user",
            password="pwd",
        )
        mock_200 = MagicMock(status_code=200, ok=True)
        mock_200.json.return_value = {"value": [{"Ref_Key": "00000000-0000-0000-0000-000000000001", "Description": "Товар 1"}]}
        with patch("common.data_source.onec_connector.validate_crm_url_and_resolve", return_value=("https://1c.example.com/base/odata/standard.odata", "1.2.3.4", 443)), \
             patch.object(c.transport, "get", return_value=mock_200):
            c.validate_connector_settings()

    def test_load_from_state_odata_skip_paging(self):
        c = OneCConnector(
            base_url="https://1c.example.com/base/odata/standard.odata",
            username="user",
            password="pwd",
            catalogs="Catalog_Номенклатура",
            batch_size=2,
        )

        page1 = {
            "value": [
                {"Ref_Key": "key-01", "Description": "Сервер Dell", "Code": "001", "DeletionMark": False},
                {"Ref_Key": "key-02", "Description": "Маршрутизатор Cisco", "Code": "002", "DeletionMark": False},
            ],
            "odata.nextLink": "https://1c.example.com/base/odata/standard.odata/Catalog_Номенклатура?$skip=2",
        }
        page2 = {
            "value": [
                {"Ref_Key": "key-03", "Description": "Коммутатор HP", "Code": "003", "DeletionMark": False},
            ]
        }

        mock1 = MagicMock(status_code=200, ok=True)
        mock1.json.return_value = page1
        mock2 = MagicMock(status_code=200, ok=True)
        mock2.json.return_value = page2

        with patch.object(c.transport, "get", side_effect=[mock1, mock2]):
            batches = list(c.load_from_state())

        assert len(batches) == 2
        assert "Catalog_Номенклатура" in batches[0][0].id
        assert batches[0][0].source == DocumentSource.ONE_C
        assert "Сервер Dell" in batches[0][0].blob.decode("utf-8")
        assert batches[1][0].metadata["record_id"] == "key-03"


class TestSyncWorkersExecutionStep5:
    """Verify all 5 CRM sync workers execute, handle tasks, and emit documents properly."""

    @pytest.mark.asyncio
    async def test_all_five_crm_workers_sync_execution(self):
        configs = [
            (Bitrix24Worker, Bitrix24Connector, {"credentials": {"webhook_url": "https://test.bitrix24.com/rest/1/k/"}, "entities": "deal"}),
            (AmoCRMWorker, AmoCRMConnector, {"credentials": {"subdomain": "test.amocrm.ru", "access_token": "tok"}, "entities": "leads"}),
            (KommoWorker, AmoCRMConnector, {"credentials": {"subdomain": "test.kommo.com", "access_token": "tok"}, "entities": "leads"}),
            (HubSpotWorker, HubSpotConnector, {"credentials": {"access_token": "pat-tok"}, "entities": "deals"}),
            (OneCWorker, OneCConnector, {"credentials": {"base_url": "https://1c.example.com/odata/"}, "catalogs": "Catalog_Номенклатура"}),
        ]

        task = {
            "kb_id": "kb_step5_test",
            "connector_id": "conn_step5_test",
            "tenant_id": "tenant_1",
            "poll_range_start": None,
            "reindex": "1",
        }

        for worker_cls, conn_cls, conf in configs:
            worker = worker_cls(conf)
            with patch.object(conn_cls, "validate_connector_settings", return_value=True), \
                 patch.object(conn_cls, "load_from_state", return_value=(iter([]))), \
                 patch.object(worker, "log_connection") as mock_log:
                gen = await worker._generate(task)
                assert gen is not None
                assert mock_log.called

