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
from datetime import datetime, timezone
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

import warnings
warnings.filterwarnings("ignore", message=".*doesn't match a supported version.*")

from common.constants import FileSource
from common.data_source.config import DocumentSource
from common.data_source.exceptions import (
    ConnectorMissingCredentialError,
    ConnectorValidationError,
)
from common.data_source.models import Document, SlimDocument
from common.data_source.bitrix24_connector import Bitrix24Connector
from common.data_source.amocrm_connector import AmoCRMConnector
from common.data_source.hubspot_connector import HubSpotConnector
from common.data_source.onec_connector import OneCConnector


class TestBitrix24Connector(unittest.TestCase):
    def setUp(self):
        self.config = {
            "credentials": {
                "domain": "test-company.bitrix24.com",
                "webhook_url": "https://test-company.bitrix24.com/rest/1/test_token/",
            },
            "entities": ["deal", "lead"],
            "batch_size": 2,
        }

    def test_build_connector_and_credentials(self):
        connector = Bitrix24Connector.build_connector(self.config)
        self.assertEqual(connector.domain, "test-company.bitrix24.com")
        self.assertEqual(connector.webhook_url, "https://test-company.bitrix24.com/rest/1/test_token/")
        self.assertEqual(connector.entities, ["deal", "lead"])
        self.assertEqual(connector.batch_size, 2)

    def test_validate_connector_settings_missing_credentials(self):
        connector = Bitrix24Connector(domain="test.bitrix24.com", webhook_url="")
        with self.assertRaises(ConnectorMissingCredentialError):
            connector.validate_connector_settings()

    @patch("common.data_source.bitrix24_connector.validate_crm_url_and_resolve", return_value=("test-company.bitrix24.com", "93.184.216.34"))
    @patch("common.data_source.bitrix24_connector.CRMTransport.post")
    def test_validate_connector_settings_success(self, mock_post, mock_val):
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"result": {"ID": {"type": "integer"}}}
        mock_post.return_value = mock_resp

        connector = Bitrix24Connector.build_connector(self.config)
        connector.validate_connector_settings()
        mock_post.assert_called_once()

    @patch("common.data_source.bitrix24_connector.CRMTransport.post")
    def test_load_from_state_and_formatting(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.status_code = 200
        mock_resp.json.side_effect = [
            # deals page 1
            {
                "result": [
                    {
                        "ID": "101",
                        "TITLE": "License Renewal 2026",
                        "OPPORTUNITY": 50000,
                        "CURRENCY_ID": "RUB",
                        "STAGE_ID": "WON",
                        "DATE_MODIFY": "2026-10-01T12:00:00+00:00",
                    },
                    {
                        "ID": "102",
                        "TITLE": "New Client Onboarding",
                        "OPPORTUNITY": 120000,
                        "CURRENCY_ID": "RUB",
                        "STAGE_ID": "IN_PROGRESS",
                        "DATE_MODIFY": "2026-10-02T15:30:00+00:00",
                    },
                ],
                "next": None,
            },
            # leads page 1 (empty)
            {"result": [], "next": None},
        ]
        mock_post.return_value = mock_resp

        connector = Bitrix24Connector.build_connector(self.config)
        batches = list(connector.load_from_state())
        self.assertEqual(len(batches), 1)
        docs = batches[0]
        self.assertEqual(len(docs), 2)
        doc1 = docs[0]
        self.assertIsInstance(doc1, Document)
        self.assertEqual(doc1.id, "bitrix24:test-company.bitrix24.com:deal:101")
        self.assertEqual(doc1.source, DocumentSource.BITRIX24)
        self.assertEqual(doc1.semantic_identifier, "Bitrix24 Deal: License Renewal 2026")
        self.assertIn("License Renewal 2026", doc1.blob.decode("utf-8"))
        self.assertIn("50000", doc1.blob.decode("utf-8"))
        self.assertEqual(doc1.metadata["entity"], "deal")

    @patch("common.data_source.bitrix24_connector.CRMTransport.post")
    def test_retrieve_all_slim_docs(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.status_code = 200
        mock_resp.json.side_effect = [
            {"result": [{"ID": "101"}, {"ID": "102"}], "next": None},
            {"result": [{"ID": "201"}], "next": None},
        ]
        mock_post.return_value = mock_resp

        connector = Bitrix24Connector.build_connector(self.config)
        slim_batches = list(connector.retrieve_all_slim_docs_perm_sync())
        all_slims = [doc for b in slim_batches for doc in b]
        self.assertEqual(len(all_slims), 3)
        self.assertIsInstance(all_slims[0], SlimDocument)
        self.assertEqual(all_slims[0].id, "bitrix24:test-company.bitrix24.com:deal:101")
        self.assertEqual(all_slims[2].id, "bitrix24:test-company.bitrix24.com:lead:201")


class TestAmoCRMConnector(unittest.TestCase):
    def setUp(self):
        self.config = {
            "credentials": {
                "subdomain": "testcompany.amocrm.ru",
                "access_token": "valid_mock_token_123",
            },
            "entities": ["leads", "contacts"],
            "batch_size": 2,
        }

    def test_build_connector_and_credentials(self):
        connector = AmoCRMConnector.build_connector(self.config)
        self.assertEqual(connector.subdomain, "testcompany.amocrm.ru")
        self.assertEqual(connector.access_token, "valid_mock_token_123")
        self.assertFalse(connector.is_kommo)
        self.assertEqual(connector.entities, ["leads", "contacts"])

    def test_kommo_detection(self):
        kommo_cfg = {
            "credentials": {
                "subdomain": "myteam.kommo.com",
                "access_token": "token_abc",
            },
        }
        connector = AmoCRMConnector.build_connector(kommo_cfg)
        self.assertTrue(connector.is_kommo)

    @patch("common.data_source.amocrm_connector.is_valid_amocrm_url", return_value=(True, "valid"))
    @patch("common.data_source.amocrm_connector.CRMTransport.get")
    def test_validate_connector_settings_success(self, mock_get, mock_val):
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": 12345, "name": "Test Company"}
        mock_get.return_value = mock_resp

        connector = AmoCRMConnector.build_connector(self.config)
        connector.validate_connector_settings()
        mock_get.assert_called_once()

    @patch("common.data_source.amocrm_connector.CRMTransport.get")
    def test_load_from_state_and_custom_fields(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.status_code = 200
        mock_resp.json.side_effect = [
            # leads
            {
                "_embedded": {
                    "leads": [
                        {
                            "id": 501,
                            "name": "Big Deal with Partner",
                            "price": 300000,
                            "status_id": 142,
                            "created_at": 1727784000,
                            "updated_at": 1727785000,
                            "custom_fields_values": [
                                {
                                    "field_name": "City",
                                    "values": [{"value": "Moscow"}],
                                }
                            ],
                        }
                    ]
                }
            },
            # contacts
            {
                "_embedded": {
                    "contacts": []
                }
            },
        ]
        mock_get.return_value = mock_resp

        connector = AmoCRMConnector.build_connector(self.config)
        batches = list(connector.load_from_state())
        self.assertEqual(len(batches), 1)
        docs = batches[0]
        self.assertEqual(len(docs), 1)
        doc = docs[0]
        self.assertEqual(doc.id, "amocrm:testcompany.amocrm.ru:leads:501")
        self.assertEqual(doc.source, DocumentSource.AMOCRM)
        self.assertIn("Big Deal with Partner", doc.semantic_identifier)
        text = doc.blob.decode("utf-8")
        self.assertIn("300000", text)
        self.assertIn("Moscow", text)


class TestHubSpotConnector(unittest.TestCase):
    def setUp(self):
        self.config = {
            "credentials": {
                "access_token": "pat-na1-mock-12345",
            },
            "entities": ["deals"],
            "batch_size": 2,
        }

    def test_build_connector_and_credentials(self):
        connector = HubSpotConnector.build_connector(self.config)
        self.assertEqual(connector.access_token, "pat-na1-mock-12345")
        self.assertEqual(connector.entities, ["deals"])

    @patch("common.data_source.hubspot_connector.CRMTransport.get")
    def test_validate_connector_settings(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"results": [{"id": "1"}]}
        mock_get.return_value = mock_resp

        connector = HubSpotConnector.build_connector(self.config)
        connector.validate_connector_settings()
        mock_get.assert_called_once()

    @patch("common.data_source.hubspot_connector.CRMTransport.get")
    def test_load_from_state(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "results": [
                {
                    "id": "deal-999",
                    "properties": {
                        "dealname": "Enterprise Subscription",
                        "amount": "25000",
                        "dealstage": "contractsent",
                        "hs_lastmodifieddate": "2026-10-01T10:00:00.000Z",
                    },
                }
            ],
            "paging": {},
        }
        mock_get.return_value = mock_resp

        connector = HubSpotConnector.build_connector(self.config)
        batches = list(connector.load_from_state())
        self.assertEqual(len(batches), 1)
        docs = batches[0]
        self.assertEqual(len(docs), 1)
        doc = docs[0]
        self.assertEqual(doc.id, "hubspot:deals:deal-999")
        self.assertEqual(doc.source, DocumentSource.HUBSPOT)
        self.assertIn("Enterprise Subscription", doc.semantic_identifier)
        self.assertIn("25000", doc.blob.decode("utf-8"))


class TestOneCConnector(unittest.TestCase):
    def setUp(self):
        self.config = {
            "credentials": {
                "base_url": "https://1c.myenterprise.com/base/odata/standard.odata/",
                "username": "odata_user",
                "password": "secret_password",
                "entity_path": "Catalog_Номенклатура",
            },
            "batch_size": 2,
        }

    def test_build_connector_and_credentials(self):
        connector = OneCConnector.build_connector(self.config)
        self.assertEqual(connector.base_url, "https://1c.myenterprise.com/base/odata/standard.odata")
        self.assertEqual(connector.username, "odata_user")
        self.assertEqual(connector.password, "secret_password")
        self.assertEqual(connector.entity_paths, ["Catalog_Номенклатура"])

    @patch("common.data_source.onec_connector.validate_crm_url_and_resolve", return_value=("1c.myenterprise.com", "93.184.216.34"))
    @patch("common.data_source.onec_connector.CRMTransport.get")
    def test_validate_connector_settings(self, mock_get, mock_val):
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"value": [{"Ref_Key": "abc-123"}]}
        mock_get.return_value = mock_resp

        connector = OneCConnector.build_connector(self.config)
        connector.validate_connector_settings()
        mock_get.assert_called_once()

    @patch("common.data_source.onec_connector.CRMTransport.get")
    def test_load_from_state(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "value": [
                {
                    "Ref_Key": "00000001-aaaa-bbbb-cccc-000000000001",
                    "Code": "ART-7788",
                    "Description": "Сервер 2U Rackmount Xeon",
                    "ВидНоменклатуры": "Оборудование",
                    "БазоваяЕдиницаИзмерения": "шт",
                }
            ]
        }
        mock_get.return_value = mock_resp

        connector = OneCConnector.build_connector(self.config)
        batches = list(connector.load_from_state())
        self.assertEqual(len(batches), 1)
        docs = batches[0]
        self.assertEqual(len(docs), 1)
        doc = docs[0]
        self.assertEqual(doc.id, "1c:1c.myenterprise.com:Catalog_Номенклатура:00000001-aaaa-bbbb-cccc-000000000001")
        self.assertEqual(doc.source, DocumentSource.ONE_C)
        self.assertIn("Сервер 2U Rackmount Xeon", doc.semantic_identifier)
        self.assertIn("ART-7788", doc.blob.decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
