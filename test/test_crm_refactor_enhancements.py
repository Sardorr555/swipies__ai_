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
import warnings
warnings.filterwarnings("ignore", message=".*doesn't match a supported version.*")
warnings.filterwarnings("ignore", category=ResourceWarning)

import pytest
from unittest.mock import MagicMock, patch

from api.db.db_models import DB
DB.connection_context = lambda: (lambda fn: fn)
DB.connect = lambda *a, **kw: True
DB.close = lambda *a, **kw: None
DB.is_closed = lambda: False

from api.crm.base import CRMProviderRegistry
from api.crm.clients.amocrm import AmoCRMClient, AmoCRMDomainError
from api.crm.clients.bitrix24 import Bitrix24Client, Bitrix24DomainError
from api.db.crm_models import CRMConnection
from api.db.services.crm_service import CRMConnectionService


class TestCRMRefactorEnhancements:

    def test_provider_registry_supports_kommo(self):
        client = CRMProviderRegistry.get("kommo")
        assert isinstance(client, AmoCRMClient)

        client_amo = CRMProviderRegistry.get("amocrm")
        assert isinstance(client_amo, AmoCRMClient)

    def test_amocrm_subdomain_normalization(self):
        client = AmoCRMClient()

        # 1. Plain subdomain
        url = client._get_base_url({"subdomain": "mycompany"})
        assert url == "https://mycompany.amocrm.ru"

        # 2. Subdomain with full amocrm.ru domain
        url2 = client._get_base_url({"subdomain": "mycompany.amocrm.ru"})
        assert url2 == "https://mycompany.amocrm.ru"

        # 3. Subdomain with kommo.com domain
        url3 = client._get_base_url({"subdomain": "mycompany.kommo.com"})
        assert url3 == "https://mycompany.kommo.com"

        # 4. Subdomain with explicit https:// prefix
        url4 = client._get_base_url({"subdomain": "https://mycompany.amocrm.ru/"})
        assert url4 == "https://mycompany.amocrm.ru"

        # 5. Invalid domain should be rejected
        with pytest.raises(AmoCRMDomainError):
            client._get_base_url({"subdomain": "evil.attacker.com"})

    def test_bitrix24_domain_and_token_normalization(self):
        client = Bitrix24Client()

        # 1. Direct webhook URL
        url1 = client._get_validated_webhook_base_url({
            "webhook_url": "https://company.bitrix24.ru/rest/1/abc123secret/"
        })
        assert url1 == "https://company.bitrix24.ru/rest/1/abc123secret"

        # 2. Portal domain + access_token containing user_id
        url2 = client._get_validated_webhook_base_url({
            "domain": "company.bitrix24.ru",
            "access_token": "1/abc123secret",
        })
        assert url2 == "https://company.bitrix24.ru/rest/1/abc123secret"

        # 3. Portal domain + access_token without user_id (defaults to 1)
        url3 = client._get_validated_webhook_base_url({
            "domain": "company.bitrix24.ru",
            "access_token": "abc123secret",
        })
        assert url3 == "https://company.bitrix24.ru/rest/1/abc123secret"

        # 4. Invalid cloud domain rejected
        with pytest.raises(Bitrix24DomainError):
            client._get_validated_webhook_base_url({
                "domain": "company.notbitrix24.com",
                "access_token": "abc123secret",
            })

    def test_resolve_active_connection_with_management_check(self, monkeypatch):
        mock_conn = MagicMock()
        mock_conn.status = "active"
        mock_conn.name = "Test amoCRM"
        mock_conn.id = "conn-123"

        monkeypatch.setattr(CRMConnectionService, "get_by_id_and_tenant", lambda c_id, t_id: (True, mock_conn))

        # Case 1: management enabled
        monkeypatch.setattr(CRMConnectionService, "is_management_enabled", lambda c: True)
        ok, conn = CRMConnectionService.resolve_active_connection("tenant-1", "conn-123", require_management=True)
        assert ok is True
        assert conn == mock_conn

        # Case 2: management disabled with require_management=True -> returns False, None
        monkeypatch.setattr(CRMConnectionService, "is_management_enabled", lambda c: False)
        ok2, conn2 = CRMConnectionService.resolve_active_connection("tenant-1", "conn-123", require_management=True)
        assert ok2 is False
        assert conn2 is None

        # Case 3: management disabled with require_management=False -> returns True, conn (for read queries)
        ok3, conn3 = CRMConnectionService.resolve_active_connection("tenant-1", "conn-123", require_management=False)
        assert ok3 is True
        assert conn3 == mock_conn
