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

import logging
import os
from typing import Optional

from common.constants import LLMType, RetCode
from api.db.joint_services.tenant_model_service import get_tenant_default_model_by_type
from api.db.services.llm_service import LLMBundle

LOGGER = logging.getLogger(__name__)

SUPPORTED_AUDIO_EXTENSIONS = {
    ".wav",
    ".mp3",
    ".m4a",
    ".aac",
    ".flac",
    ".ogg",
    ".oga",
    ".opus",
    ".webm",
    ".wma",
}

MAX_AUDIO_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB max
MAX_TELEGRAM_AUDIO_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB max
MAX_TELEGRAM_DURATION_SECONDS = 300  # 5 minutes


class AudioTranscriptionService:
    """Unified service for speech-to-text / ASR operations across HTTP API, MCP, and Channels."""

    @staticmethod
    def validate_audio_file(
        file_path: str,
        filename: Optional[str] = None,
        max_size_bytes: int = MAX_AUDIO_SIZE_BYTES,
    ) -> tuple[bool, str, int]:
        """
        Validate audio file presence, format, and size limit.
        Returns (is_valid, error_message, ret_code).
        """
        if not file_path or not os.path.exists(file_path):
            return False, "Audio file not found or upload was empty.", RetCode.ARGUMENT_ERROR

        try:
            size = os.path.getsize(file_path)
        except OSError as e:
            return False, f"Could not determine audio file size: {e}", RetCode.OPERATING_ERROR

        if size == 0:
            return False, "Uploaded audio file is empty (0 bytes).", RetCode.ARGUMENT_ERROR

        if size > max_size_bytes:
            mb_limit = max_size_bytes // (1024 * 1024)
            return (
                False,
                f"Audio file size ({size} bytes) exceeds the maximum allowed limit ({mb_limit} MB).",
                RetCode.ARGUMENT_ERROR,
            )

        effective_name = filename or os.path.basename(file_path)
        ext = os.path.splitext(effective_name)[1].lower()
        if ext and ext not in SUPPORTED_AUDIO_EXTENSIONS:
            allowed = ", ".join(sorted(SUPPORTED_AUDIO_EXTENSIONS))
            return (
                False,
                f"Unsupported audio format '{ext}'. Supported formats: {allowed}.",
                RetCode.ARGUMENT_ERROR,
            )

        return True, "", RetCode.SUCCESS

    @staticmethod
    def check_voice_subscription_access(
        tenant_id: str,
        sender_id: Optional[str] = None,
        channel_config: Optional[dict] = None,
    ) -> tuple[bool, str]:
        """
        Check if voice message recognition is authorized for the given tenant and sender.
        Returns (allowed: bool, reason: str).
        """
        try:
            from api.db.services.ai_policy_service import AIPolicyManager
            plan = AIPolicyManager.get_user_plan(tenant_id)
            plan_id = str(plan.get("id", "free")).lower()
        except Exception as e:
            LOGGER.warning("Could not resolve tenant plan for voice access check: %s", e)
            plan_id = "free"

        cfg = channel_config or {}

        # 1. Tenant plan check: free tier bots cannot utilize paid voice ASR
        # unless explicitly permitted in test or channel config
        allow_free_voice = cfg.get("allow_free_voice", False)
        if plan_id in ("free", "") and not allow_free_voice:
            return (
                False,
                "Распознавание голосовых сообщений доступно только по платной подписке. "
                "Вы можете продолжить общение текстовыми сообщениями.",
            )

        # 2. Channel-level end-user subscriber whitelist (if configured)
        require_subscriber = cfg.get("require_subscriber_for_voice", False)
        if require_subscriber:
            allowed_subscribers = {str(uid).strip() for uid in cfg.get("voice_subscribers", []) if uid}
            if sender_id and str(sender_id).strip() not in allowed_subscribers:
                return (
                    False,
                    "Распознавание голосовых сообщений доступно только по платной подписке. "
                    "Вы можете продолжить общение текстовыми сообщениями.",
                )

        return True, ""

    @classmethod
    def transcribe_audio(
        cls,
        tenant_id: str,
        audio_path: str,
        user_id: Optional[str] = None,
        language: Optional[str] = None,
        prompt: Optional[str] = None,
    ) -> tuple[bool, str, int]:
        """
        Transcribe an audio file using the tenant's default ASR model.
        Returns (success: bool, text_or_error: str, ret_code: int).
        """
        val_ok, val_err, val_code = cls.validate_audio_file(audio_path)
        if not val_ok:
            return False, val_err, val_code

        # 1. Resolve default ASR model configuration
        try:
            default_asr_config = get_tenant_default_model_by_type(tenant_id, LLMType.ASR)
        except Exception as e:
            LOGGER.error("Failed to resolve ASR model for tenant %s: %s", tenant_id, e)
            return False, f"Failed to resolve ASR model configuration: {e}", RetCode.DATA_ERROR

        if not default_asr_config:
            return (
                False,
                "No default ASR/speech-to-text model configured for this account. "
                "Please configure an ASR model (e.g. OpenAI whisper-1) in Models Settings.",
                RetCode.NOT_FOUND,
            )

        model_name = default_asr_config.get("llm_name") or "whisper-1"

        # 2. Check policy & quota
        try:
            from api.db.services.ai_policy_service import AIPolicyManager
            allowed, msg, status_code, err_code = AIPolicyManager.check_model_access_extended(
                tenant_id=tenant_id,
                model_name=model_name,
                model_type="asr",
                user_id=user_id or tenant_id,
            )
            if not allowed:
                ret_code = RetCode.PERMISSION_ERROR if status_code == 403 else RetCode.OPERATING_ERROR
                return False, f"ASR access restriction ({err_code}): {msg}", ret_code
        except Exception as pe:
            LOGGER.debug("AIPolicyManager check skipped/warning: %s", pe)

        # 3. Perform transcription via LLMBundle
        try:
            asr_mdl = LLMBundle(tenant_id, default_asr_config)
            transcription_kwargs = {}
            if language:
                transcription_kwargs["language"] = language
            if prompt:
                transcription_kwargs["prompt"] = prompt

            transcription_result = asr_mdl.transcription(audio_path, **transcription_kwargs)
            if not transcription_result:
                return False, "Transcription returned empty result.", RetCode.DATA_ERROR

            if isinstance(transcription_result, tuple):
                text = transcription_result[0]
            else:
                text = str(transcription_result)

            text = text.strip()
            if "**ERROR**" in text:
                clean_err = text.replace("**ERROR**:", "").strip()
                return False, f"ASR provider error: {clean_err}", RetCode.SERVER_ERROR

            return True, text, RetCode.SUCCESS

        except Exception as exc:
            LOGGER.error("Audio transcription failed for tenant %s: %s", tenant_id, exc)
            return False, f"Transcription service error: {exc}", RetCode.SERVER_ERROR
