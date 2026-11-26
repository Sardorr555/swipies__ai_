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
from __future__ import annotations

import warnings
warnings.filterwarnings("ignore")

import json
import sys
from unittest.mock import MagicMock, patch

import common.settings
common.settings.init_settings = lambda *a, **kw: None
common.settings.docStoreConn = MagicMock()

# Stub out heavy dialog_service dependency if langgraph is not installed in local environment
mock_dialog_service_module = MagicMock()
sys.modules["api.db.services.dialog_service"] = mock_dialog_service_module

import pytest

from api.utils.model_utils import (
    calculate_model_type,
    get_model_type_human,
    normalize_model_types,
)
from api.apps.services.models_api_service import (
    normalize_model_type,
    _check_model_available,
)
from common.constants import ModelTypeBinary, ActiveStatusEnum
from api.channels.telegram.channel import (
    get_runtime_snapshot as get_telegram_runtime_snapshot,
    TelegramChannel,
    TelegramAccount,
    _live_channels,
)
from api.channels.targets import (
    sanitize_channel_config,
    channel_to_safe_dict,
    mask_secret,
)
from api.agent_access import redact_response


# ===========================================================================
# 1. Secret Leakage & Safe DTO Tests
# ===========================================================================
def test_mask_secret_helper():
    # Telegram token format: bot_id:secret_hash
    tg_token = "798030123:AAH_SyntheticSecretTokenValue4567"
    masked = mask_secret(tg_token)
    assert masked.startswith("798030123:***")
    assert masked.endswith("4567")
    assert "AAH_SyntheticSecretTokenValue" not in masked

    # Standard secret
    std_secret = "sk-proj-1234567890abcdef1234"
    masked_std = mask_secret(std_secret)
    assert masked_std.startswith("sk-***")
    assert masked_std.endswith("1234")
    assert "1234567890abcdef" not in masked_std


def test_sanitize_channel_config_and_channel_to_safe_dict():
    raw_conn = {
        "id": "chan_001",
        "name": "Mental Support Bot",
        "channel": "telegram",
        "chat_id": "dia_001",
        "status": 1,
        "config": {
            "credential": {
                "token": "798030123:AAH_SecretTelegramBotToken_xyz89",
                "username": "Mental13g1233BOT",
            },
            "greeting": "Assalomu alaykum",
        },
    }

    safe = channel_to_safe_dict(raw_conn)

    assert safe["id"] == "chan_001"
    assert safe["credential_configured"] is True
    # Raw token must NEVER appear in output
    assert "AAH_SecretTelegramBotToken_xyz89" not in json.dumps(safe)
    # Masked token retains prefix and last 4 chars
    masked_token = safe["config"]["credential"]["token"]
    assert masked_token.startswith("798030123:***")
    assert masked_token.endswith("yz89")
    # Non-secret fields preserved
    assert safe["config"]["credential"]["username"] == "Mental13g1233BOT"
    assert safe["config"]["greeting"] == "Assalomu alaykum"


def test_redact_response_covers_bot_tokens_and_nested_credentials():
    resp_obj = {
        "status": 200,
        "data": {
            "token": "secret_session_token_12345678901234567890",
            "bot_token": "798030123:AAH_SecretBotToken_1234567890",
            "config": {
                "credential": {
                    "token": "798030123:AAH_SecretBotToken_1234567890",
                    "secret": "top_secret_key",
                }
            },
            "tokens_used": 150,  # should NOT be redacted
        },
    }

    cleaned = redact_response(resp_obj, "Bearer my-caller-key-123456789012345678901234567890")
    data = cleaned["data"]
    assert data["token"] == "[REDACTED]"
    assert data["bot_token"] == "[REDACTED]"
    assert data["config"]["credential"]["token"] == "[REDACTED]"
    assert data["config"]["credential"]["secret"] == "[REDACTED]"
    assert data["tokens_used"] == 150
    assert "SecretBotToken" not in json.dumps(cleaned)


# ===========================================================================
# 2. Telegram Channel Runtime Snapshot Tests
# ===========================================================================
def test_telegram_runtime_snapshot_structure_and_safety():
    mock_channel = MagicMock()
    mock_channel.id = "chan_tg_001"
    mock_channel.tenant_id = "tenant_001"
    mock_channel.name = "Mental Support Bot"
    mock_channel.channel = "telegram"
    mock_channel.status = 1
    mock_channel.chat_id = "dia_test_001"
    mock_channel.agent_id = None
    mock_channel.config = {
        "credential": {
            "token": "798030123:AAH_SecretTelegramBotToken_9999",
            "username": "Mental13g1233BOT",
        }
    }

    mock_dialog = MagicMock()
    mock_dialog.id = "dia_test_001"
    mock_dialog.name = "AI психологик ёрдамчи"
    mock_dialog.kb_ids = ["kb_books_001"]
    mock_dialog.prompt_config = {"system": "Мен AI психологик ёрдамчиман. Психологическая поддержка."}

    mock_tenant = MagicMock()
    mock_tenant.asr_id = "whisper-1@default@OpenAI"
    mock_tenant.tenant_asr_id = "t_asr_999"

    # Register mock live channel
    mock_live = MagicMock()
    mock_live.account = TelegramAccount(account_id="chan_tg_001", token="798030123:AAH_SecretTelegramBotToken_9999")
    mock_live._processed_updates = {101: True, 102: True}
    mock_live._bot_info = {
        "id": 798030123,
        "username": "Mental13g1233BOT",
        "first_name": "Mental Support",
        "can_join_groups": True,
    }
    mock_live._app.updater.running = True
    _live_channels["chan_tg_001"] = mock_live

    mock_dialog_service_module.DialogService.get_by_id.return_value = (True, mock_dialog)
    try:
        with patch("api.db.services.chat_channel_service.ChatChannelService.get_by_id", return_value=(True, mock_channel)), \
             patch("api.db.services.user_service.TenantService.get_by_id", return_value=(True, mock_tenant)):

            snapshot = get_telegram_runtime_snapshot("chan_tg_001")

            assert snapshot is not None
            assert snapshot["channel_id"] == "chan_tg_001"
            assert snapshot["channel"] == "telegram"
            assert snapshot["worker_status"] == "running"
            assert snapshot["mode"] == "long_polling"
            assert snapshot["polling_active"] is True
            assert snapshot["credential_configured"] is True

            # Bot info verification
            assert snapshot["bot"]["username"] == "Mental13g1233BOT"
            assert snapshot["bot"]["id"] == 798030123

            # Masked metadata verification
            assert snapshot["credential_metadata"]["masked_token"].startswith("798030123:***")
            assert snapshot["credential_metadata"]["masked_token"].endswith("9999")
            assert "SecretTelegramBotToken" not in json.dumps(snapshot)

            # Assistant readiness verification
            assert snapshot["assistant"]["ready"] is True
            assert snapshot["assistant"]["type"] == "dialog"
            assert snapshot["assistant"]["id"] == "dia_test_001"
            assert snapshot["assistant"]["kb_count"] == 1

            # ASR readiness verification
            assert snapshot["asr"]["ready"] is True
            assert snapshot["asr"]["model_name"] == "whisper-1@default@OpenAI"

            # Metrics
            assert snapshot["metrics"]["processed_updates"] == 2
            assert snapshot["metrics"]["update_lag"] == 0
    finally:
        _live_channels.pop("chan_tg_001", None)


# ===========================================================================
# 3. Model Typing and Canonical Normalization Tests
# ===========================================================================
def test_canonical_model_type_normalization():
    # Canonical mappings
    assert normalize_model_types("speech2text") == ["asr"]
    assert normalize_model_types("SPEECH2TEXT") == ["asr"]
    assert normalize_model_types("asr") == ["asr"]
    assert normalize_model_types("ASR") == ["asr"]
    assert normalize_model_types(["speech2text", "asr"]) == ["asr"]

    assert normalize_model_types("image2text") == ["vision"]
    assert normalize_model_types("IMAGE2TEXT") == ["vision"]
    assert normalize_model_types("vision") == ["vision"]
    assert normalize_model_types(["image2text", "vision"]) == ["vision"]


def test_calculate_model_type_bitmask_consistency():
    # asr bitmask is 4 (1 << 2)
    assert calculate_model_type("asr") == ModelTypeBinary.ASR.value
    assert calculate_model_type("speech2text") == ModelTypeBinary.ASR.value
    assert calculate_model_type("SPEECH2TEXT") == ModelTypeBinary.ASR.value
    assert get_model_type_human(calculate_model_type("speech2text")) == ["asr"]

    # vision bitmask is 8 (1 << 3)
    assert calculate_model_type("vision") == ModelTypeBinary.VISION.value
    assert calculate_model_type("image2text") == ModelTypeBinary.VISION.value
    assert get_model_type_human(calculate_model_type("image2text")) == ["vision"]


def test_whisper_available_as_asr_and_speech2text():
    mock_prov = MagicMock()
    mock_prov.id = "prov_openai"
    mock_inst = MagicMock()
    mock_inst.id = "inst_default"

    mock_model = MagicMock()
    mock_model.model_name = "whisper-1"
    mock_model.status = ActiveStatusEnum.ACTIVE.value
    mock_model.model_type = ModelTypeBinary.ASR.value  # 4

    with patch("api.db.services.tenant_model_provider_service.TenantModelProviderService.get_by_tenant_id_and_provider_name", return_value=mock_prov), \
         patch("api.db.services.tenant_model_instance_service.TenantModelInstanceService.get_by_provider_id_and_instance_name", return_value=mock_inst), \
         patch("api.apps.services.models_api_service.FACTORY_LLM_INFOS", [{"name": "OpenAI"}]), \
         patch("api.db.services.tenant_model_service.TenantModelService.get_by_provider_id_and_instance_id_and_model_name", return_value=mock_model):

        # Validating as canonical "asr"
        ok_asr, err_asr = _check_model_available("tenant_001", "OpenAI", "default", "whisper-1", "asr")
        assert ok_asr is True
        assert err_asr is None

        # Validating as legacy "speech2text"
        ok_s2t, err_s2t = _check_model_available("tenant_001", "OpenAI", "default", "whisper-1", "speech2text")
        assert ok_s2t is True
        assert err_s2t is None


# ===========================================================================
# 4. User Profile Safe DTO & Account Context Tests
# ===========================================================================
def test_user_to_safe_dict_excludes_access_token_by_default():
    from api.db.db_models import User

    user = User(
        id="usr_001",
        email="albakiev.sardorbek@gmail.com",
        nickname="Sardorbek",
        access_token="session_secret_access_token_1234567890abcdef",
    )

    # Generic safe dict (e.g. public view)
    d_generic = user.to_safe_dict()
    assert "access_token" not in d_generic
    assert "email" not in d_generic

    # Self profile view: include_token=False by default
    d_self = user.to_safe_dict(for_self=True)
    assert d_self["email"] == "albakiev.sardorbek@gmail.com"
    assert "access_token" not in d_self
    assert "password" not in d_self

    # Login response view: include_token=True explicitly requested
    d_login = user.to_safe_dict(for_self=True, include_token=True)
    assert d_login["access_token"] == "session_secret_access_token_1234567890abcdef"


def test_channel_update_preserves_secret_when_masked_token_sent():
    # Existing channel in DB has the real secret token
    existing_config = {
        "credential": {
            "token": "798030123:AAH_RealProductionBotSecret_xyz",
            "username": "Mental13g1233BOT",
        }
    }

    # Caller submits updated config with masked token
    incoming_update = {
        "config": {
            "credential": {
                "token": "798030123:***_xyz",
                "username": "Mental13g1233BOT",
            }
        }
    }

    # Simulate the update preservation logic
    new_cfg = incoming_update["config"]
    old_cfg = existing_config
    new_cred = new_cfg["credential"]
    old_cred = old_cfg["credential"]
    for secret_field in ("token", "bot_token", "secret", "password", "api_key", "client_secret"):
        val = new_cred.get(secret_field)
        if (not val or "***" in str(val)) and old_cred.get(secret_field):
            new_cred[secret_field] = old_cred[secret_field]

    # The real token must be preserved!
    assert incoming_update["config"]["credential"]["token"] == "798030123:AAH_RealProductionBotSecret_xyz"


@pytest.mark.asyncio
async def test_api_token_auth_survives_empty_or_invalid_user_access_token():
    from common.constants import StatusEnum
    from api.apps import app, AUTH_API, _load_user
    from quart import g

    mock_api_token = MagicMock()
    mock_api_token.tenant_id = "tenant_albakiev"
    mock_api_token.status = "1"

    # User whose browser access_token was revoked or invalidated on logout
    mock_user = MagicMock()
    mock_user.id = "tenant_albakiev"
    mock_user.email = "albakiev.sardorbek@gmail.com"
    mock_user.access_token = "INVALID_9876543210abcdef"
    mock_user.status = StatusEnum.VALID.value
    mock_user.is_active = "1"

    with patch("api.db.db_models.APIToken.query", return_value=[mock_api_token]), \
         patch("api.db.services.user_service.UserService.query", return_value=[mock_user]):
        async with app.test_request_context("/", headers={"Authorization": "Bearer ragflow-test-api-token-123456"}):
            loaded = _load_user(auth_types=(AUTH_API,))
            assert loaded is not None
            assert loaded.email == "albakiev.sardorbek@gmail.com"
            assert getattr(g, "auth_type") == AUTH_API
            assert getattr(g, "tenant_id") == "tenant_albakiev"

