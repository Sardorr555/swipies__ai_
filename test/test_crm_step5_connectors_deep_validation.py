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

import sys
sys.modules.setdefault("api.db.services.dialog_service", MagicMock())
sys.modules.setdefault("xgboost", MagicMock())
sys.modules.setdefault("pypdf", MagicMock())
sys.modules.setdefault("api.db.services.file_service", MagicMock())
sys.modules.setdefault("api.db.services.task_service", MagicMock())

from api.db.db_models import DB
DB.connect = lambda *a, **kw: True
DB.connection_context = lambda: (lambda fn: fn)

from peewee import SqliteDatabase
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
from api.db.crm_models import CRMConnection, CRMOutbox
from api.db.services.crm_service import CRMConnectionService, CRMOutboxService
from api.crm.base import CRMProviderBase, CRMProviderRegistry
from rag.svr.crm_outbox_worker import CRMOutboxWorker
from agent.tools.create_incoming_lead import CreateIncomingLead, CreateIncomingLeadParam

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


from agent.canvas import Canvas


class DummyStep5Canvas(Canvas):
    def __init__(self, tenant_id="tenant_step5", channel="chat"):
        self.tenant_id = tenant_id
        self._tenant_id = tenant_id
        self._canvas_owner_tenant = tenant_id
        self._channel = channel
        self._turn_lead_count = 0
        self.is_embed = False
        self._is_public = False
        self.auth_type = "AUTH_JWT"
        self.task_id = "test-task-id"
        self.dsl = {"components": {}, "history": [], "path": []}
        self.components = {}

    def get_channel(self):
        return self._channel

    def get_canvas_owner_tenant(self):
        return self._tenant_id

    def get_tenant_id(self):
        return self._tenant_id

    def is_canceled(self):
        return False

    def check_if_canceled(self, *a, **kw):
        return False


class TestCRMManagementToggleAndIsolation:
    """Validate enabling/disabling CRM management per provider while data extraction remains active."""

    def test_crm_provider_management_permission_checks(self):
        """Verify CRMProviderBase detects management_enabled flag and gates actions."""
        # 1. Defaults to True if omitted
        assert CRMProviderBase.is_management_enabled({}) is True
        assert CRMProviderBase.is_management_enabled({"foo": "bar"}) is True

        # 2. Disabled states
        assert CRMProviderBase.is_management_enabled({"management_enabled": False}) is False
        assert CRMProviderBase.is_management_enabled({"enable_management": False}) is False
        assert CRMProviderBase.is_management_enabled({"allow_write": False}) is False
        assert CRMProviderBase.is_management_enabled({"allow_crm_actions": False}) is False

        # 3. Enabled states
        assert CRMProviderBase.is_management_enabled({"management_enabled": True}) is True

        # 4. Gating check raises PermissionError on disabled
        with pytest.raises(PermissionError) as exc_info:
            CRMProviderBase.check_management_allowed({"management_enabled": False}, action_name="test_write")
        assert "CRM management is disabled" in str(exc_info.value)
        assert "Data extraction and reading remain active" in str(exc_info.value)

        # 5. Gating check passes when enabled
        CRMProviderBase.check_management_allowed({"management_enabled": True}, action_name="test_write")

    def test_all_crm_provider_clients_enforce_management_check(self):
        """Verify AmoCRM, Bitrix24, HubSpot, and 1C clients block create_lead when management is disabled."""
        disabled_cfg = {"management_enabled": False}

        for p_name in ("amocrm", "bitrix24", "hubspot", "1c_odata"):
            provider = CRMProviderRegistry.get(p_name)
            with pytest.raises(PermissionError) as exc_info:
                provider.create_lead(disabled_cfg, {"phone": "+14155552671", "name": "Alice"})
            assert "CRM management is disabled" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_data_extraction_and_sync_always_active_when_management_disabled(self):
        """Verify that all 5 CRM sync workers extract data without interruption even when management is disabled."""
        configs = [
            (Bitrix24Worker, Bitrix24Connector, {"credentials": {"webhook_url": "https://test.bitrix24.com/rest/1/k/"}, "management_enabled": False}),
            (AmoCRMWorker, AmoCRMConnector, {"credentials": {"subdomain": "test.amocrm.ru", "access_token": "tok"}, "management_enabled": False}),
            (KommoWorker, AmoCRMConnector, {"credentials": {"subdomain": "test.kommo.com", "access_token": "tok"}, "management_enabled": False}),
            (HubSpotWorker, HubSpotConnector, {"credentials": {"access_token": "pat-tok"}, "management_enabled": False}),
            (OneCWorker, OneCConnector, {"credentials": {"base_url": "https://1c.example.com/odata/"}, "management_enabled": False}),
        ]

        task = {
            "kb_id": "kb_step5_readonly",
            "connector_id": "conn_step5_readonly",
            "tenant_id": "tenant_readonly",
            "poll_range_start": None,
            "reindex": "1",
        }

        for worker_cls, conn_cls, conf in configs:
            worker = worker_cls(conf)
            with patch.object(conn_cls, "validate_connector_settings", return_value=True), \
                 patch.object(conn_cls, "load_from_state", return_value=(iter([]))), \
                 patch.object(worker, "log_connection") as mock_log:
                # Sync / extraction succeeds completely
                gen = await worker._generate(task)
                assert gen is not None
                assert mock_log.called

    def test_connection_service_and_outbox_management_lifecycle(self):
        """Verify CRMConnectionService toggling and CRMOutboxService gating."""
        import os
        os.environ["RAGFLOW_SECRET_KEY"] = "crm-super-secret-key-32bytes-ok!"
        test_db = SqliteDatabase(":memory:")
        orig_conn_db = CRMConnection._meta.database
        orig_outbox_db = CRMOutbox._meta.database
        CRMConnection._meta.database = test_db
        CRMOutbox._meta.database = test_db
        DB.atomic = lambda *a, **kw: test_db.atomic()
        test_db.bind([CRMConnection, CRMOutbox])
        test_db.connect()
        test_db.create_tables([CRMConnection, CRMOutbox], safe=True)

        tenant_id = "tenant_mgmt_test"
        try:
            # 1. Save connection with management enabled
            conn = CRMConnectionService.save_connection(
                tenant_id=tenant_id,
                name="Mgmt amoCRM",
                crm_type="amocrm",
                auth_type="oauth2",
                config={"management_enabled": True, "access_token": "tok"},
            )
            assert CRMConnectionService.is_management_enabled(conn) is True
            assert conn.is_management_enabled() is True

            # 2. Enqueue succeeds when enabled
            rec, created = CRMOutboxService.enqueue(
                tenant_id=tenant_id,
                connection_id=conn.id,
                lead_data={"phone": "+14155551111", "name": "Client 1"},
            )
            assert created is True
            assert rec.status == "PENDING"

            # 3. Disable management via set_management_enabled
            ok = CRMConnectionService.set_management_enabled(conn.id, tenant_id, False)
            assert ok is True

            _, reloaded = CRMConnectionService.get_by_id_and_tenant(conn.id, tenant_id)
            assert CRMConnectionService.is_management_enabled(reloaded) is False
            assert reloaded.is_management_enabled() is False

            # 4. Enqueue fails with PermissionError when management disabled
            with pytest.raises(PermissionError) as exc_info:
                CRMOutboxService.enqueue(
                    tenant_id=tenant_id,
                    connection_id=conn.id,
                    lead_data={"phone": "+14155552222", "name": "Client 2"},
                )
            assert "CRM management is disabled" in str(exc_info.value)
            assert "data extraction remains active" in str(exc_info.value)

            # 5. Re-enable management
            ok_re = CRMConnectionService.set_management_enabled(conn.id, tenant_id, True)
            assert ok_re is True
            _, reloaded2 = CRMConnectionService.get_by_id_and_tenant(conn.id, tenant_id)
            assert CRMConnectionService.is_management_enabled(reloaded2) is True

            # 6. Enqueue succeeds again
            rec2, created2 = CRMOutboxService.enqueue(
                tenant_id=tenant_id,
                connection_id=conn.id,
                lead_data={"phone": "+14155553333", "name": "Client 3"},
            )
            assert created2 is True
        finally:
            CRMConnection._meta.database = orig_conn_db
            CRMOutbox._meta.database = orig_outbox_db
            if not test_db.is_closed():
                test_db.close()

    def test_create_incoming_lead_tool_management_toggle(self):
        """Verify CreateIncomingLead agent tool rejects lead creation when CRM management is disabled."""
        import os
        os.environ["RAGFLOW_SECRET_KEY"] = "crm-super-secret-key-32bytes-ok!"
        test_db = SqliteDatabase("file:crm_step5_tool_mem?mode=memory&cache=shared", uri=True)
        orig_conn_db = CRMConnection._meta.database
        orig_outbox_db = CRMOutbox._meta.database
        CRMConnection._meta.database = test_db
        CRMOutbox._meta.database = test_db
        DB.atomic = lambda *a, **kw: test_db.atomic()
        test_db.bind([CRMConnection, CRMOutbox])
        test_db.connect()
        test_db.create_tables([CRMConnection, CRMOutbox], safe=True)
        orig_close = test_db.close
        test_db.close = lambda *a, **kw: None

        tenant_id = "tenant_tool_mgmt"
        canvas = DummyStep5Canvas(tenant_id=tenant_id, channel="chat")

        mock_redis = MagicMock()
        mock_redis_conn = MagicMock()
        mock_redis_conn.is_alive.return_value = True
        mock_redis_conn.REDIS = mock_redis
        mock_redis.incr.return_value = 1

        try:
            with patch("rag.utils.redis_conn.REDIS_CONN", mock_redis_conn):
                # 1. Connection with management disabled
                conn = CRMConnectionService.save_connection(
                    tenant_id=tenant_id,
                    name="Readonly amoCRM",
                    crm_type="amocrm",
                    auth_type="oauth2",
                    config={"management_enabled": False, "subdomain": "sales.amocrm.ru"},
                )

                param = CreateIncomingLeadParam()
                param.connection_id = conn.id
                tool = CreateIncomingLead(id="tool-step5", param=param, canvas=canvas)

                # Tool call fails with PermissionError
                with pytest.raises(PermissionError) as exc_info:
                    tool._invoke(phone="+14155552671", name="Bob")
                assert "CRM management is disabled" in str(exc_info.value)
                assert "Data extraction and search remain active" in str(exc_info.value)

                # 2. Enable management on connection
                CRMConnectionService.set_management_enabled(conn.id, tenant_id, True)

                # Tool call now succeeds
                res = tool._invoke(phone="+14155552671", name="Bob")
                assert res["status"] == "success"
                assert "outbox_id" in res
        finally:
            CRMConnection._meta.database = orig_conn_db
            CRMOutbox._meta.database = orig_outbox_db
            test_db.close = orig_close
            if not test_db.is_closed():
                test_db.close()

    def test_outbox_worker_parks_tasks_when_management_disabled(self):
        """Verify CRMOutboxWorker parks tasks safely without consuming retries when management is disabled."""
        import os
        import time
        os.environ["RAGFLOW_SECRET_KEY"] = "crm-super-secret-key-32bytes-ok!"
        test_db = SqliteDatabase(":memory:")
        orig_conn_db = CRMConnection._meta.database
        orig_outbox_db = CRMOutbox._meta.database
        CRMConnection._meta.database = test_db
        CRMOutbox._meta.database = test_db
        DB.atomic = lambda *a, **kw: test_db.atomic()
        test_db.bind([CRMConnection, CRMOutbox])
        test_db.connect()
        test_db.create_tables([CRMConnection, CRMOutbox], safe=True)

        tenant_id = "tenant_worker_mgmt"
        worker_id = "test-mgmt-worker-1"
        try:
            conn = CRMConnectionService.save_connection(
                tenant_id=tenant_id,
                name="Managed amoCRM",
                crm_type="amocrm",
                auth_type="oauth2",
                config={"management_enabled": False, "subdomain": "sales.amocrm.ru"},
            )

            # Insert outbox task directly with active worker lease
            task = CRMOutbox.create(
                id="outbox_task_step5_1",
                tenant_id=tenant_id,
                connection_id=conn.id,
                status="PROCESSING",
                lease_owner=worker_id,
                lease_expires_at=int(time.time() * 1000) + 300000,
                retry_count=0,
                max_retries=5,
                lead_data={"phone": "+14155559999", "name": "Parked Lead"},
            )

            worker = CRMOutboxWorker(worker_id=worker_id)
            success = worker.process_task(task)

            # Task was not dispatched, but parked without burning retry counts
            assert success is False
            reloaded_task = CRMOutbox.get_by_id(task.id)
            assert reloaded_task.status == "PARKED"
            assert reloaded_task.retry_count == 0
            assert "management is disabled" in reloaded_task.error_log.get("parked_reason", "")

            # When management is re-enabled, tasks are unparked
            CRMConnectionService.set_management_enabled(conn.id, tenant_id, True)
            unparked_task = CRMOutbox.get_by_id(task.id)
            assert unparked_task.status == "PENDING"
        finally:
            CRMConnection._meta.database = orig_conn_db
            CRMOutbox._meta.database = orig_outbox_db
            if not test_db.is_closed():
                test_db.close()


