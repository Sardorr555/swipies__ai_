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

import sys
from unittest.mock import MagicMock

class DummyModule(MagicMock):
    __path__ = []

# Mock infinity and its submodules
sys.modules['infinity'] = DummyModule()
sys.modules['infinity.common'] = DummyModule()
sys.modules['infinity.errors'] = DummyModule()
sys.modules['infinity.rag_tokenizer'] = DummyModule()
sys.modules['infinity.index'] = DummyModule()

from types import SimpleNamespace
from api.db.services.user_service import TenantLimitService


def test_check_apps_limit(monkeypatch):
    # Mock TenantService.get_by_id
    tenant = SimpleNamespace(plan_type="free")
    monkeypatch.setattr(
        "api.db.services.user_service.TenantService.get_by_id",
        lambda tenant_id: (True, tenant)
    )

    # Mock referral count
    monkeypatch.setattr(
        TenantLimitService,
        "is_referral_enabled",
        lambda: False
    )

    # Mock count queries
    class MockQuery:
        def __init__(self, count_val):
            self.count_val = count_val

        def where(self, *args, **kwargs):
            return self

        def count(self):
            return self.count_val

    # Mock Dialog and UserCanvas select
    monkeypatch.setattr(
        "api.db.db_models.Dialog.select",
        lambda: MockQuery(2)
    )
    monkeypatch.setattr(
        "api.db.db_models.UserCanvas.select",
        lambda: MockQuery(0)
    )

    # Under free plan: limit is 3. Total apps = 2 + 0 = 2. Should pass.
    allowed, msg = TenantLimitService.check_apps_limit("tenant-1")
    assert allowed is True
    assert msg is None

    # Now simulate 3 dialogs + 1 canvas = 4 apps. Under free plan, it should fail.
    monkeypatch.setattr(
        "api.db.db_models.Dialog.select",
        lambda: MockQuery(3)
    )
    monkeypatch.setattr(
        "api.db.db_models.UserCanvas.select",
        lambda: MockQuery(1)
    )
    allowed, msg = TenantLimitService.check_apps_limit("tenant-1")
    assert allowed is False
    assert "limit of 3" in msg

    # Upgrade tenant to Plus. Limit is 50. Total apps = 4. Should pass.
    tenant.plan_type = "plus"
    allowed, msg = TenantLimitService.check_apps_limit("tenant-1")
    assert allowed is True
    assert msg is None

    # Upgrade tenant to Pro. Limit is unlimited. Should pass.
    tenant.plan_type = "pro"
    allowed, msg = TenantLimitService.check_apps_limit("tenant-1")
    assert allowed is True
    assert msg is None


def test_check_storage_limit(monkeypatch):
    tenant = SimpleNamespace(plan_type="free")
    monkeypatch.setattr(
        "api.db.services.user_service.TenantService.get_by_id",
        lambda tenant_id: (True, tenant)
    )
    monkeypatch.setattr(
        TenantLimitService,
        "is_referral_enabled",
        lambda: False
    )

    class MockDocumentQuery:
        def __init__(self, size):
            self.size = size

        def join(self, *args, **kwargs):
            return self

        def where(self, *args, **kwargs):
            return self

        def scalar(self):
            return self.size

    # Free plan limit: 0.5 GB = 536870912 bytes
    # Current size: 400 MB. New file size: 50 MB. Total = 450 MB. Should pass.
    current_size = 400 * 1024 * 1024
    new_file_size = 50 * 1024 * 1024
    monkeypatch.setattr(
        "api.db.db_models.Document.select",
        lambda *args, **kwargs: MockDocumentQuery(current_size)
    )

    allowed, msg = TenantLimitService.check_storage_limit("tenant-1", new_file_size)
    assert allowed is True
    assert msg is None

    # New file size: 200 MB. Total = 600 MB. Should exceed 0.5 GB limit.
    allowed, msg = TenantLimitService.check_storage_limit("tenant-1", 200 * 1024 * 1024)
    assert allowed is False
    assert "0.5 GB" in msg

    # Upgrade to Plus. Limit: 5.0 GB. Should pass.
    tenant.plan_type = "plus"
    allowed, msg = TenantLimitService.check_storage_limit("tenant-1", 200 * 1024 * 1024)
    assert allowed is True
    assert msg is None


def test_check_team_limit(monkeypatch):
    tenant = SimpleNamespace(plan_type="free")
    monkeypatch.setattr(
        "api.db.services.user_service.TenantService.get_by_id",
        lambda tenant_id: (True, tenant)
    )

    class MockQuery:
        def __init__(self, count_val):
            self.count_val = count_val

        def where(self, *args, **kwargs):
            return self

        def count(self):
            return self.count_val

    # Free plan limit: 1 member. Current count: 1. Should fail if we check (since member_count >= limit).
    monkeypatch.setattr(
        "api.db.db_models.UserTenant.select",
        lambda: MockQuery(1)
    )
    allowed, msg = TenantLimitService.check_team_limit("tenant-1")
    assert allowed is False
    assert "limit of 1" in msg

    # Upgrade to Plus. Limit: 5 members. Current count: 1. Should pass.
    tenant.plan_type = "plus"
    allowed, msg = TenantLimitService.check_team_limit("tenant-1")
    assert allowed is True
    assert msg is None
