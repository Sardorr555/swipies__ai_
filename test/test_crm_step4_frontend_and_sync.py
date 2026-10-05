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
"""Tests for Step 4: CRM Data Source settings, entities parsing, batch size, and sync worker robustness."""

from __future__ import annotations

import warnings
warnings.filterwarnings("ignore", message=".*doesn't match a supported version.*")
warnings.filterwarnings("ignore", category=ResourceWarning)

import pytest
from unittest.mock import MagicMock, patch

from api.db.db_models import DB
DB.connect = lambda *a, **kw: True
DB.connection_context = lambda: (lambda fn: fn)

from common.constants import FileSource
from common.data_source.bitrix24_connector import Bitrix24Connector
from common.data_source.amocrm_connector import AmoCRMConnector
from common.data_source.hubspot_connector import HubSpotConnector
from common.data_source.onec_connector import OneCConnector
from api.crm.schema import (
    is_crm_source,
    get_crm_field_map,
    CRM_SOURCES,
    CRM_SOURCE_FIELD_MAPS,
)
import importlib
import sys


def _import_sync_module():
    """Import rag.svr.sync_data_source, stubbing optional third-party deps that
    are not installed locally (they are present in the Docker image)."""
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
Kommo = _sync.Kommo
OneC = _sync.OneC


class TestCRMConnectorStep4Settings:
    """Test connector parameter handling, batch size bounds, and entity parsing."""

    def test_onec_connector_catalogs_init_and_alias(self):
        # Initializing with catalogs parameter
        c1 = OneCConnector(
            base_url="https://1c.example.com/odata/",
            username="admin",
            password="pwd",
            catalogs="Catalog_Номенклатура, Document_ЗаказКлиента",
            batch_size=75,
        )
        assert c1.entity_paths == ["Catalog_Номенклатура", "Document_ЗаказКлиента"]
        assert c1.catalogs == ["Catalog_Номенклатура", "Document_ЗаказКлиента"]
        assert c1.batch_size == 75

        # Initializing with entity_path parameter
        c2 = OneCConnector(
            base_url="https://1c.example.com/odata/",
            username="admin",
            password="pwd",
            entity_path=["Catalog_Товары"],
            batch_size=500,  # should be clamped to 200
        )
        assert c2.entity_paths == ["Catalog_Товары"]
        assert c2.catalogs == ["Catalog_Товары"]
        assert c2.batch_size == 200

    def test_onec_build_connector_with_catalogs_and_odata_base_url(self):
        config = {
            "catalogs": "Catalog_Склады, Catalog_Цены",
            "batch_size": 30,
            "credentials": {
                "odata_base_url": "https://1c.example.com/odata/",
                "username": "u1",
                "password": "p1",
            },
        }
        conn = OneCConnector.build_connector(config)
        assert conn.catalogs == ["Catalog_Склады", "Catalog_Цены"]
        assert conn.base_url == "https://1c.example.com/odata"
        assert conn.batch_size == 30

    def test_bitrix24_connector_batch_size_and_entities(self):
        c = Bitrix24Connector(
            domain="corp.bitrix24.com",
            webhook_url="https://corp.bitrix24.com/rest/1/key/",
            entities="deal, lead, custom_entity",
            batch_size=100,  # Bitrix clamp is 50
        )
        assert c.batch_size == 50
        assert "deal" in c.entities
        assert "lead" in c.entities
        assert "custom_entity" in c.entities

    def test_amocrm_and_kommo_connector_settings(self):
        amo = AmoCRMConnector(
            subdomain="test.amocrm.ru",
            client_id="cid",
            client_secret="sec",
            entities="leads, contacts",
            batch_size=150,
            is_kommo=False,
        )
        assert amo.is_kommo is False
        assert amo.batch_size == 150
        assert amo.entities == ["leads", "contacts"]

        kommo = AmoCRMConnector(
            subdomain="test.kommo.com",
            client_id="cid",
            client_secret="sec",
            entities=["leads", "companies"],
            batch_size=300,  # clamped to 250
            is_kommo=True,
        )
        assert kommo.is_kommo is True
        assert kommo.batch_size == 250
        assert kommo.entities == ["leads", "companies"]

    def test_hubspot_connector_batch_size_and_entities(self):
        hs = HubSpotConnector(
            access_token="pat-na1-12345",
            entities="deals, contacts, products",
            batch_size=150,  # clamped to 100
        )
        assert hs.batch_size == 100
        assert hs.entities == ["deals", "contacts", "products"]


class TestCRMSyncWorkerStep4Robustness:
    """Test sync worker initialization, logging, and error resistance."""

    @pytest.mark.asyncio
    async def test_onec_sync_worker_generation(self):
        worker = OneC({
            "catalogs": "Catalog_Номенклатура, Catalog_Склады",
            "batch_size": 40,
            "credentials": {
                "base_url": "https://1c.example.com/odata/",
                "username": "user",
                "password": "pwd",
            },
        })
        task = {
            "kb_id": "kb_1c_test",
            "connector_id": "conn_1c_test",
            "tenant_id": "t1",
            "poll_range_start": None,
            "reindex": "1",
        }

        with patch.object(OneCConnector, "validate_connector_settings", return_value=True), \
             patch.object(OneCConnector, "load_from_state", return_value=(iter([]))), \
             patch.object(worker, "log_connection") as mock_log:
            gen = await worker._generate(task)
            assert gen is not None
            assert worker.connector.catalogs == ["Catalog_Номенклатура", "Catalog_Склады"]
            assert mock_log.called

    @pytest.mark.asyncio
    async def test_kommo_sync_worker_generation(self):
        worker = Kommo({
            "entities": "leads, contacts",
            "batch_size": 25,
            "credentials": {
                "subdomain": "myteam.kommo.com",
                "client_id": "cid",
                "client_secret": "csec",
            },
        })
        task = {
            "kb_id": "kb_kommo_test",
            "connector_id": "conn_kommo_test",
            "tenant_id": "t1",
            "poll_range_start": None,
            "reindex": "1",
        }

        with patch.object(AmoCRMConnector, "validate_connector_settings", return_value=True), \
             patch.object(AmoCRMConnector, "load_from_state", return_value=(iter([]))), \
             patch.object(worker, "log_connection") as mock_log:
            gen = await worker._generate(task)
            assert gen is not None
            assert worker.connector.is_kommo is True
            assert worker.connector.entities == ["leads", "contacts"]
            assert mock_log.called


class TestSalesforceSchemaExtension:
    """Test Salesforce inclusion in CRM schema and Text-to-SQL auto field map."""

    def test_salesforce_is_crm_source(self):
        assert is_crm_source("salesforce") is True
        assert is_crm_source(FileSource.SALESFORCE) is True

    def test_salesforce_field_map(self):
        fm = get_crm_field_map("salesforce")
        assert "id" in fm
        assert "name" in fm
        assert "amount" in fm
        assert "stage_name" in fm
        assert "close_date" in fm

