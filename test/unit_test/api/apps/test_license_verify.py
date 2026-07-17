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
"""Unit tests for the online license verification endpoint (/v1/licenses/verify)."""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
import pytest
from datetime import datetime, timedelta
from quart import Quart


class _PassthroughManager:
    def route(self, *_args, **_kwargs):
        return lambda func: func


def _stub(monkeypatch, name, **attrs):
    mod = ModuleType(name)
    for key, value in attrs.items():
        setattr(mod, key, value)
    monkeypatch.setitem(sys.modules, name, mod)
    return mod


def _load_backward_compat(monkeypatch, mock_license_key_service=None):
    _stub(monkeypatch, "api.apps", login_required=lambda func: func)
    
    # Stub api.db.services.license_key_service
    if mock_license_key_service is None:
        mock_license_key_service = SimpleNamespace()
    _stub(monkeypatch, "api.db.services.license_key_service", LicenseKeyService=mock_license_key_service)
    
    # Stub other restful_apis imported in backward_compat.py
    _stub(monkeypatch, "api.apps.restful_apis", 
          agent_api=SimpleNamespace(), 
          chat_api=SimpleNamespace(), 
          chunk_api=SimpleNamespace(), 
          dataset_api=SimpleNamespace(), 
          document_api=SimpleNamespace(), 
          file2document_api=SimpleNamespace(), 
          file_api=SimpleNamespace(), 
          openai_api=SimpleNamespace())
          
    _stub(monkeypatch, "api.apps.restful_apis.system_api", run_health_checks=lambda: ({}, True))
    _stub(monkeypatch, "api.apps.services", dataset_api_service=SimpleNamespace(), file_api_service=SimpleNamespace())
    _stub(monkeypatch, "api.utils.api_utils", 
          add_tenant_id_to_kwargs=lambda func: func,
          get_data_error_result=lambda message: {"code": 102, "message": message},
          get_json_result=lambda data: {"code": 0, "data": data},
          get_request_json=lambda: {})

    repo_root = Path(__file__).resolve().parents[4]
    module_path = repo_root / "api" / "apps" / "backward_compat.py"
    spec = importlib.util.spec_from_file_location("test_license_verify_backward_compat", module_path)
    module = importlib.util.module_from_spec(spec)
    module.manager = _PassthroughManager()
    module.legacy_v1_manager = _PassthroughManager()
    monkeypatch.setitem(sys.modules, "test_license_verify_backward_compat", module)
    spec.loader.exec_module(module)
    return module


@pytest.mark.asyncio
async def test_verify_license_missing_key(monkeypatch):
    class MockRequest:
        async def get_json(self):
            return {}
            
    module = _load_backward_compat(monkeypatch)
    monkeypatch.setattr(module, "request", MockRequest())
    
    app = Quart(__name__)
    async with app.app_context():
        response, status_code = await module.verify_license()
        json_data = await response.json
        
    assert status_code == 400
    assert json_data["valid"] is False
    assert "Missing license_key" in json_data["message"]


@pytest.mark.asyncio
async def test_verify_license_not_found(monkeypatch):
    class MockRequest:
        async def get_json(self):
            return {"license_key": "some-nonexistent-key"}
            
    mock_service = SimpleNamespace(
        query=lambda **kwargs: []
    )
    
    module = _load_backward_compat(monkeypatch, mock_license_key_service=mock_service)
    monkeypatch.setattr(module, "request", MockRequest())
    
    app = Quart(__name__)
    async with app.app_context():
        response, status_code = await module.verify_license()
        json_data = await response.json
        
    assert status_code == 200
    assert json_data["valid"] is False
    assert "License not found" in json_data["message"]


@pytest.mark.asyncio
async def test_verify_license_active_valid(monkeypatch):
    class MockRequest:
        async def get_json(self):
            return {"license_key": "valid-key"}
            
    mock_lic = SimpleNamespace(
        status="active",
        is_paid=True,
        expiry_date=datetime.now() + timedelta(days=30)
    )
    
    mock_service = SimpleNamespace(
        query=lambda **kwargs: [mock_lic]
    )
    
    module = _load_backward_compat(monkeypatch, mock_license_key_service=mock_service)
    monkeypatch.setattr(module, "request", MockRequest())
    
    app = Quart(__name__)
    async with app.app_context():
        response, status_code = await module.verify_license()
        json_data = await response.json
        
    assert status_code == 200
    assert json_data["valid"] is True


@pytest.mark.asyncio
async def test_verify_license_expired(monkeypatch):
    class MockRequest:
        async def get_json(self):
            return {"license_key": "expired-key"}
            
    mock_lic = SimpleNamespace(
        status="active",
        is_paid=True,
        expiry_date=datetime.now() - timedelta(days=1)
    )
    
    mock_service = SimpleNamespace(
        query=lambda **kwargs: [mock_lic]
    )
    
    module = _load_backward_compat(monkeypatch, mock_license_key_service=mock_service)
    monkeypatch.setattr(module, "request", MockRequest())
    
    app = Quart(__name__)
    async with app.app_context():
        response, status_code = await module.verify_license()
        json_data = await response.json
        
    assert status_code == 200
    assert json_data["valid"] is False
    assert "License expired" in json_data["message"]


@pytest.mark.asyncio
async def test_verify_license_revoked(monkeypatch):
    class MockRequest:
        async def get_json(self):
            return {"license_key": "revoked-key"}
            
    mock_lic = SimpleNamespace(
        status="revoked",
        is_paid=True,
        expiry_date=datetime.now() + timedelta(days=30)
    )
    
    mock_service = SimpleNamespace(
        query=lambda **kwargs: [mock_lic]
    )
    
    module = _load_backward_compat(monkeypatch, mock_license_key_service=mock_service)
    monkeypatch.setattr(module, "request", MockRequest())
    
    app = Quart(__name__)
    async with app.app_context():
        response, status_code = await module.verify_license()
        json_data = await response.json
        
    assert status_code == 200
    assert json_data["valid"] is False
    assert "License status is revoked" in json_data["message"]
