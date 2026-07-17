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
"""Tests for user deactivation (api/apps/restful_apis/user_api.py)."""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest


class _PassthroughManager:
    def route(self, *_args, **_kwargs):
        return lambda func: func


def _stub(monkeypatch, name, **attrs):
    mod = ModuleType(name)
    for key, value in attrs.items():
        setattr(mod, key, value)
    monkeypatch.setitem(sys.modules, name, mod)
    return mod


def _load_user_api(monkeypatch, update_calls=None, logout_calls=None):
    """Load api/apps/restful_apis/user_api.py with minimal stubs."""
    update_calls = update_calls if update_calls is not None else []
    logout_calls = logout_calls if logout_calls is not None else []

    def _update_by_id(user_id, update_dict):
        update_calls.append((user_id, update_dict))
        return True

    def _logout_user():
        logout_calls.append(True)
        return True

    _stub(
        monkeypatch,
        "api.apps",
        current_user=SimpleNamespace(id="user-123", is_superuser=False),
        login_required=lambda func: func,
        login_user=lambda *args, **kwargs: True,
        logout_user=_logout_user,
    )
    _stub(
        monkeypatch,
        "api.apps.auth",
        get_auth_client=lambda *args, **kwargs: SimpleNamespace()
    )
    _stub(
        monkeypatch,
        "api.db",
        FileType=SimpleNamespace(),
        UserTenantRole=SimpleNamespace()
    )
    _stub(
        monkeypatch,
        "api.db.db_models",
        Lead=SimpleNamespace()
    )
    _stub(
        monkeypatch,
        "api.db.services.file_service",
        FileService=SimpleNamespace()
    )
    _stub(
        monkeypatch,
        "api.db.services.user_service",
        TenantService=SimpleNamespace(),
        UserService=SimpleNamespace(update_by_id=_update_by_id),
        UserTenantService=SimpleNamespace()
    )
    _stub(
        monkeypatch,
        "api.db.services.lead_service",
        LeadService=SimpleNamespace()
    )
    _stub(
        monkeypatch,
        "common.time_utils",
        current_timestamp=lambda: 1234567890,
        datetime_format=lambda: "2026-07-17 12:00:00",
        get_format_time=lambda: "2026-07-17 12:00:00"
    )
    # Let real common.misc_utils load normally
    # Let real common.constants load normally
    _stub(
        monkeypatch,
        "common.connection_utils",
        construct_response=lambda *args, **kwargs: None
    )
    _stub(
        monkeypatch,
        "api.utils.api_utils",
        get_data_error_result=lambda message="Sorry": {"code": 100, "message": message, "data": None},
        get_json_result=lambda code=0, message="", data=None: {"code": code, "message": message, "data": data},
        get_request_json=lambda: {},
        server_error_response=lambda exc: {"code": 500, "message": str(exc)},
        validate_request=lambda *_a, **_k: lambda func: func,
    )
    _stub(
        monkeypatch,
        "api.utils.nickname_validation",
        validate_nickname=lambda *args, **kwargs: (True, None)
    )
    _stub(
        monkeypatch,
        "api.utils.crypt",
        decrypt=lambda *args, **kwargs: "decrypted"
    )
    _stub(
        monkeypatch,
        "rag.utils.redis_conn",
        REDIS_CONN=SimpleNamespace()
    )
    _stub(
        monkeypatch,
        "api.utils.web_utils",
        send_email_html=lambda *args, **kwargs: None,
        OTP_LENGTH=6,
        OTP_TTL_SECONDS=300,
        ATTEMPT_LIMIT=5,
        ATTEMPT_LOCK_SECONDS=300,
        RESEND_COOLDOWN_SECONDS=60,
        otp_keys=SimpleNamespace(),
        hash_code=lambda *args, **kwargs: "hashed",
        captcha_key=lambda *args, **kwargs: "captcha",
    )
    _stub(monkeypatch, "common.settings")

    repo_root = Path(__file__).resolve().parents[5]
    module_path = repo_root / "api" / "apps" / "restful_apis" / "user_api.py"
    spec = importlib.util.spec_from_file_location("test_user_deactivation_user_api", module_path)
    module = importlib.util.module_from_spec(spec)
    module.manager = _PassthroughManager()
    monkeypatch.setitem(sys.modules, "test_user_deactivation_user_api", module)
    spec.loader.exec_module(module)
    return module, update_calls, logout_calls


@pytest.mark.p1
class TestUserDeactivation:
    """Tests user deactivation endpoint (soft delete)."""

    @pytest.mark.p1
    @pytest.mark.asyncio
    async def test_deactivate_user_success(self, monkeypatch):
        module, update_calls, logout_calls = _load_user_api(monkeypatch)

        result = await module.delete_user()

        assert result == {
            "code": 0,
            "message": "",
            "data": True
        }
        assert len(update_calls) == 1
        user_id, update_dict = update_calls[0]
        assert user_id == "user-123"
        assert update_dict["is_active"] == "0"
        assert update_dict["status"] == "0"
        assert update_dict["access_token"].startswith("DEACTIVATED_")
        assert len(logout_calls) == 1
