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

import os
import sys
import tempfile
import types
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Stub out heavy storage / search / init_settings dependencies before importing
import common.settings
common.settings.init_settings = lambda *a, **kw: None
common.settings.docStoreConn = MagicMock()

from common.constants import LLMType, RetCode
from api.apps.services.models_api_service import (
    MODEL_TYPE_TO_FIELD,
    MODEL_TYPE_TO_TENANT_ID_FIELD,
    normalize_model_type,
)
from api.db.joint_services.tenant_model_service import get_tenant_default_model_by_type
from api.db.services.audio_service import (
    AudioTranscriptionService,
    SUPPORTED_AUDIO_EXTENSIONS,
)
from api.channels.telegram.channel import TelegramAccount, TelegramChannel
from rag.llm.sequence2txt_model import GPTSeq2txt


# ---------------------------------------------------------------------------
# 1. Enum and Model Type Alignment Tests
# ---------------------------------------------------------------------------
def test_llm_type_enum_attributes_and_aliases():
    """Verify LLMType has SPEECH2TEXT and IMAGE2TEXT without throwing AttributeError."""
    assert hasattr(LLMType, "SPEECH2TEXT")
    assert hasattr(LLMType, "IMAGE2TEXT")
    assert hasattr(LLMType, "ASR")
    assert hasattr(LLMType, "VISION")

    assert LLMType.SPEECH2TEXT.value == "speech2text"
    assert LLMType.ASR.value == "asr"
    assert LLMType.IMAGE2TEXT.value == "image2text"
    assert LLMType.VISION.value == "vision"

    # Verify lookup via constructor
    assert LLMType("asr") == LLMType.ASR
    assert LLMType("speech2text") == LLMType.SPEECH2TEXT
    assert LLMType("SPEECH2TEXT") == LLMType.SPEECH2TEXT
    assert LLMType("image2text") == LLMType.IMAGE2TEXT
    assert LLMType("vision") == LLMType.VISION


def test_model_type_normalization_and_fields():
    """Verify canonical mapping for asr/speech2text and vision/image2text."""
    assert normalize_model_type("asr") == "asr"
    assert normalize_model_type("speech2text") == "asr"
    assert normalize_model_type("SPEECH2TEXT") == "asr"
    assert normalize_model_type("vision") == "vision"
    assert normalize_model_type("image2text") == "vision"
    assert normalize_model_type("chat") == "chat"

    # Both asr and speech2text resolve to asr_id
    assert MODEL_TYPE_TO_FIELD.get("asr") == "asr_id"
    assert MODEL_TYPE_TO_FIELD.get("speech2text") == "asr_id"
    assert MODEL_TYPE_TO_TENANT_ID_FIELD.get("asr") == "tenant_asr_id"
    assert MODEL_TYPE_TO_TENANT_ID_FIELD.get("speech2text") == "tenant_asr_id"

    # Both vision and image2text resolve to img2txt_id
    assert MODEL_TYPE_TO_FIELD.get("vision") == "img2txt_id"
    assert MODEL_TYPE_TO_FIELD.get("image2text") == "img2txt_id"


def test_tenant_default_model_by_type_matches_asr_and_speech2text():
    """Verify pattern matching in get_tenant_default_model_by_type does not crash."""
    mock_tenant = MagicMock()
    mock_tenant.asr_id = "whisper-1@default@OpenAI"
    mock_tenant.tenant_asr_id = "t_asr_123"

    with patch("api.db.services.user_service.TenantService.get_by_id", return_value=(True, mock_tenant)), \
         patch("api.db.joint_services.tenant_model_service.get_model_config_by_id", return_value={"llm_name": "whisper-1", "llm_factory": "OpenAI", "model_type": "asr"}):
        
        cfg_enum = get_tenant_default_model_by_type("tenant_test", LLMType.ASR)
        assert cfg_enum is not None
        assert cfg_enum["model_type"] == "asr"

        cfg_s2t_enum = get_tenant_default_model_by_type("tenant_test", LLMType.SPEECH2TEXT)
        assert cfg_s2t_enum is not None
        assert cfg_s2t_enum["model_type"] == "asr"

        cfg_str_asr = get_tenant_default_model_by_type("tenant_test", "asr")
        assert cfg_str_asr is not None
        assert cfg_str_asr["model_type"] == "asr"

        cfg_str_s2t = get_tenant_default_model_by_type("tenant_test", "speech2text")
        assert cfg_str_s2t is not None
        assert cfg_str_s2t["model_type"] == "asr"


# ---------------------------------------------------------------------------
# 2. Whisper Adapter Audio Format & Parameter Handling Tests
# ---------------------------------------------------------------------------
def test_whisper_transcription_normalizes_opus_and_passes_params():
    """Verify Base.transcription maps .opus/.oga to .ogg and forwards language."""
    adapter = GPTSeq2txt(key="fake_key", model_name="whisper-1")
    adapter.client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.text = "Здравствуйте, это тестовое голосовое сообщение"
    adapter.client.audio.transcriptions.create.return_value = mock_resp

    with tempfile.NamedTemporaryFile(suffix=".opus", delete=False) as f:
        f.write(b"OggS\x00\x02fake_opus_content")
        temp_opus = f.name

    try:
        text, tokens = adapter.transcription(temp_opus, language="ru")
        assert text == "Здравствуйте, это тестовое голосовое сообщение"
        assert tokens > 0

        # Check call arguments
        call_kwargs = adapter.client.audio.transcriptions.create.call_args.kwargs
        assert call_kwargs["model"] == "whisper-1"
        assert call_kwargs["language"] == "ru"
        file_tuple = call_kwargs["file"]
        assert file_tuple[0].endswith(".ogg")
        assert file_tuple[1] == b"OggS\x00\x02fake_opus_content"
    finally:
        if os.path.exists(temp_opus):
            os.remove(temp_opus)


# ---------------------------------------------------------------------------
# 3. AudioTranscriptionService Validation and Quota Tests
# ---------------------------------------------------------------------------
def test_audio_file_validation():
    """Test validation of file existence, empty file, size limit, and extensions."""
    # 1. Non-existent file
    ok, err, code = AudioTranscriptionService.validate_audio_file("non_existent_file.wav")
    assert not ok
    assert code == RetCode.ARGUMENT_ERROR

    # 2. Empty file (0 bytes)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        empty_path = f.name

    try:
        ok, err, code = AudioTranscriptionService.validate_audio_file(empty_path)
        assert not ok
        assert "empty" in err.lower()
        assert code == RetCode.ARGUMENT_ERROR
    finally:
        if os.path.exists(empty_path):
            os.remove(empty_path)

    # 3. Unsupported format
    with tempfile.NamedTemporaryFile(suffix=".exe", delete=False) as f:
        f.write(b"MZ\x90\x00")
        invalid_path = f.name

    try:
        ok, err, code = AudioTranscriptionService.validate_audio_file(invalid_path)
        assert not ok
        assert "unsupported" in err.lower()
        assert code == RetCode.ARGUMENT_ERROR
    finally:
        if os.path.exists(invalid_path):
            os.remove(invalid_path)

    # 4. Valid formats
    for ext in [".wav", ".ogg", ".opus", ".mp3", ".m4a", ".oga"]:
        assert ext in SUPPORTED_AUDIO_EXTENSIONS


def test_voice_subscription_access_control():
    """Verify access control for free users vs paid subscribers."""
    # 1. Free tenant plan -> denied with polite message
    with patch("api.db.services.ai_policy_service.AIPolicyManager.get_user_plan", return_value={"id": "free"}):
        allowed, msg = AudioTranscriptionService.check_voice_subscription_access(
            tenant_id="tenant_free_123",
            sender_id="user_999",
            channel_config={},
        )
        assert not allowed
        assert "Распознавание голосовых сообщений доступно только по платной подписке" in msg
        assert "Вы можете продолжить общение текстовыми сообщениями" in msg

    # 2. Paid tenant plan (PRO) -> allowed
    with patch("api.db.services.ai_policy_service.AIPolicyManager.get_user_plan", return_value={"id": "pro"}):
        allowed, msg = AudioTranscriptionService.check_voice_subscription_access(
            tenant_id="tenant_pro_123",
            sender_id="user_999",
            channel_config={},
        )
        assert allowed
        assert msg == ""

    # 3. Paid tenant plan with end-user whitelist restriction
    with patch("api.db.services.ai_policy_service.AIPolicyManager.get_user_plan", return_value={"id": "pro"}):
        cfg = {"require_subscriber_for_voice": True, "voice_subscribers": ["user_111", "user_222"]}
        # Disallowed sender
        allowed, msg = AudioTranscriptionService.check_voice_subscription_access(
            tenant_id="tenant_pro_123",
            sender_id="user_999",
            channel_config=cfg,
        )
        assert not allowed
        assert "Распознавание голосовых сообщений доступно только по платной подписке" in msg

        # Allowed sender
        allowed, msg = AudioTranscriptionService.check_voice_subscription_access(
            tenant_id="tenant_pro_123",
            sender_id="user_111",
            channel_config=cfg,
        )
        assert allowed
        assert msg == ""


def test_audio_transcription_end_to_end_mock():
    """Verify transcription execution and error reporting."""
    mock_bundle = MagicMock()
    mock_bundle.transcription.return_value = "Привет, помоги мне с заказом"

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00")
        test_wav = f.name

    try:
        with patch("api.db.services.audio_service.get_tenant_default_model_by_type", return_value={"llm_name": "whisper-1", "llm_factory": "OpenAI"}), \
             patch("api.db.services.ai_policy_service.AIPolicyManager.check_model_access_extended", return_value=(True, "OK", 200, "OK")), \
             patch("api.db.services.audio_service.LLMBundle", return_value=mock_bundle):

            ok, text, code = AudioTranscriptionService.transcribe_audio("tenant_123", test_wav)
            assert ok
            assert text == "Привет, помоги мне с заказом"
            assert code == RetCode.SUCCESS

    finally:
        if os.path.exists(test_wav):
            os.remove(test_wav)


# ---------------------------------------------------------------------------
# 4. Telegram Bot Voice Message Handling and Deduplication Tests
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_telegram_channel_deduplication():
    """Verify duplicate update_ids are dropped."""
    channel = TelegramChannel(TelegramAccount(account_id="acc_1", token="dummy:token"))
    channel._dispatch = AsyncMock()

    update = MagicMock()
    update.update_id = 12345
    update.effective_message = MagicMock()
    update.effective_message.from_user.is_bot = False
    update.effective_message.text = "Hello"
    update.effective_message.chat.id = 9876
    update.effective_message.message_id = 555
    update.effective_message.from_user.id = 4321

    # First update delivery
    await channel._on_update(update, MagicMock())
    assert channel._dispatch.call_count == 1

    # Duplicate redelivery with same update_id
    await channel._on_update(update, MagicMock())
    assert channel._dispatch.call_count == 1  # Not dispatched again!


@pytest.mark.asyncio
async def test_telegram_voice_message_pipeline():
    """Verify end-to-end telegram voice note processing and assistant dispatch."""
    channel = TelegramChannel(TelegramAccount(account_id="acc_1", token="dummy:token"))
    channel._dispatch = AsyncMock()
    channel._send_reply = AsyncMock()

    mock_chat_channel = MagicMock()
    mock_chat_channel.tenant_id = "tenant_test"
    mock_chat_channel.config = {}

    update = MagicMock()
    update.update_id = 99901
    msg = MagicMock()
    msg.from_user.is_bot = False
    msg.from_user.id = 777
    msg.chat.id = 888
    msg.message_id = 321
    msg.text = None
    msg.caption = None

    voice = MagicMock()
    voice.file_id = "voice_file_abc"
    voice.duration = 15
    voice.file_size = 4096
    msg.voice = voice
    msg.audio = None
    update.effective_message = msg

    ctx = MagicMock()
    tg_file = AsyncMock()
    async def fake_download(custom_path):
        with open(custom_path, "wb") as f:
            f.write(b"voice_binary_data")
    tg_file.download_to_drive = fake_download
    ctx.bot.get_file = AsyncMock(return_value=tg_file)

    with patch("api.db.services.chat_channel_service.ChatChannelService.get_by_id", return_value=(True, mock_chat_channel)), \
         patch("api.db.services.audio_service.AudioTranscriptionService.check_voice_subscription_access", return_value=(True, "")), \
         patch("api.db.services.audio_service.AudioTranscriptionService.transcribe_audio", return_value=(True, "Какая завтра погода?", RetCode.SUCCESS)):

        await channel._on_update(update, ctx)

        # Assert dispatch was called with transcribed text and original chat context
        assert channel._dispatch.call_count == 1
        dispatched_msg = channel._dispatch.call_args[0][0]
        assert dispatched_msg.text == "Какая завтра погода?"
        assert dispatched_msg.chat_id == "888"
        assert dispatched_msg.sender_id == "777"
        assert dispatched_msg.message_id == "321"


@pytest.mark.asyncio
async def test_telegram_voice_free_user_rejection():
    """Verify free bot users receive subscription rejection message."""
    channel = TelegramChannel(TelegramAccount(account_id="acc_1", token="dummy:token"))
    channel._dispatch = AsyncMock()
    channel._send_reply = AsyncMock()

    mock_chat_channel = MagicMock()
    mock_chat_channel.tenant_id = "tenant_free"
    mock_chat_channel.config = {}

    update = MagicMock()
    update.update_id = 99902
    msg = MagicMock()
    msg.from_user.is_bot = False
    msg.from_user.id = 777
    msg.chat.id = 888
    msg.message_id = 322
    msg.text = None
    msg.caption = None
    msg.voice = MagicMock(duration=10, file_size=2048)
    msg.audio = None
    update.effective_message = msg

    ctx = MagicMock()

    with patch("api.db.services.chat_channel_service.ChatChannelService.get_by_id", return_value=(True, mock_chat_channel)), \
         patch("api.db.services.audio_service.AudioTranscriptionService.check_voice_subscription_access", return_value=(False, "Распознавание голосовых сообщений доступно только по платной подписке. Вы можете продолжить общение текстовыми сообщениями.")):

        await channel._on_update(update, ctx)

        # Dispatch should NOT be called
        assert channel._dispatch.call_count == 0
        # Subscription notice should be replied
        assert channel._send_reply.call_count == 1
        reply_text = channel._send_reply.call_args[0][1]
        assert "платной подписке" in reply_text
