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
import json
import logging
from common.time_utils import current_timestamp
from api.db.db_models import (
    DB,
    GlobalRagflowInstance,
    AIModel,
    AIProvider,
    User,
    TokenUsageLog,
)
from api.db.services.common_service import CommonService

logger = logging.getLogger(__name__)

GLOBAL_INSTANCE_ID = "GLOBAL"


class GlobalInstanceService(CommonService):
    model = GlobalRagflowInstance

    @classmethod
    @DB.connection_context()
    def get_global_instance(cls) -> GlobalRagflowInstance:
        """
        Single centralized entry point to retrieve the platform's Global RAGFlow Instance.
        Atomically creates the singleton record if it does not already exist.
        """
        instance = cls.model.get_or_none(cls.model.id == GLOBAL_INSTANCE_ID)
        if not instance:
            try:
                now = current_timestamp()
                instance = cls.model.create(
                    id=GLOBAL_INSTANCE_ID,
                    name="Global RAGFlow Instance",
                    status="ACTIVE",
                    default_free_model_id=None,
                    default_plus_model_id=None,
                    default_pro_model_id=None,
                    default_embd_id=None,
                    default_rerank_id=None,
                    byok_enabled=True,
                    max_byok_models=10,
                    byok_token_limit=50000000,
                    byok_request_limit=100000,
                    extra={},
                    create_time=now,
                    update_time=now,
                )
                logger.info("Initialized single Global RAGFlow Instance (%s)", GLOBAL_INSTANCE_ID)
            except Exception as e:
                # Concurrent race condition handling: re-query
                instance = cls.model.get_or_none(cls.model.id == GLOBAL_INSTANCE_ID)
                if not instance:
                    logger.exception("Failed to get or create Global RAGFlow Instance: %s", e)
                    raise e
        return instance

    @classmethod
    def getGlobalRagflowInstance(cls) -> GlobalRagflowInstance:
        """Alias matching architectural specification."""
        return cls.get_global_instance()

    @classmethod
    @DB.connection_context()
    def update_global_instance(cls, updates: dict, admin_user_id: str = "system") -> GlobalRagflowInstance:
        """
        Updates settings on the Global RAGFlow Instance, synchronizes tenant defaults
        and in-memory settings, and logs the change to AIAuditLog.
        """
        inst = cls.get_global_instance()
        old_data = inst.to_dict()
        
        allowed_fields = {
            "name",
            "status",
            "default_free_model_id",
            "default_plus_model_id",
            "default_pro_model_id",
            "default_embd_id",
            "default_rerank_id",
            "byok_enabled",
            "max_byok_models",
            "byok_token_limit",
            "byok_request_limit",
            "extra",
        }

        # Normalize extra JSON field for extended defaults
        extra_data = inst.extra or {}
        if isinstance(extra_data, str):
            try:
                extra_data = json.loads(extra_data)
            except Exception:
                extra_data = {}

        if "default_chat_model" in updates:
            updates["default_free_model_id"] = updates["default_chat_model"]
            extra_data["default_chat_model"] = updates["default_chat_model"]

        if "default_image2text_model" in updates or "default_img2txt_id" in updates:
            img_val = updates.get("default_image2text_model") or updates.get("default_img2txt_id")
            extra_data["default_image2text_model"] = img_val
            extra_data["default_img2txt_id"] = img_val

        if "default_asr_model" in updates or "default_asr_id" in updates:
            asr_val = updates.get("default_asr_model") or updates.get("default_asr_id")
            extra_data["default_asr_model"] = asr_val
            extra_data["default_asr_id"] = asr_val

        if "default_tts_model" in updates or "default_tts_id" in updates:
            tts_val = updates.get("default_tts_model") or updates.get("default_tts_id")
            extra_data["default_tts_model"] = tts_val
            extra_data["default_tts_id"] = tts_val

        updates["extra"] = extra_data

        filtered_updates = {k: v for k, v in updates.items() if k in allowed_fields}
        filtered_updates["update_time"] = current_timestamp()

        cls.model.update(**filtered_updates).where(cls.model.id == GLOBAL_INSTANCE_ID).execute()

        # Synchronize Tenant model defaults across database and in-memory settings
        try:
            from common import settings
            from api.db.db_models import Tenant
            from api.apps.services.models_api_service import parse_and_resolve_model_components

            def _to_canonical_str(val, mtype):
                if not val:
                    return ""
                m, inst, p = parse_and_resolve_model_components(val, mtype)
                return f"{m}@{inst or 'default'}@{p}" if (m and p) else val

            tenant_updates = {}

            chat_m = updates.get("default_free_model_id") or updates.get("default_chat_model")
            if chat_m:
                canonical_chat = _to_canonical_str(chat_m, "chat")
                tenant_updates["llm_id"] = canonical_chat
                settings.CHAT_MDL = canonical_chat

            embd_m = updates.get("default_embd_id")
            if embd_m:
                canonical_embd = _to_canonical_str(embd_m, "embedding")
                tenant_updates["embd_id"] = canonical_embd
                settings.EMBEDDING_MDL = canonical_embd

            rerank_m = updates.get("default_rerank_id")
            if rerank_m:
                canonical_rerank = _to_canonical_str(rerank_m, "rerank")
                tenant_updates["rerank_id"] = canonical_rerank
                settings.RERANK_MDL = canonical_rerank

            img_m = extra_data.get("default_image2text_model")
            if img_m:
                canonical_img = _to_canonical_str(img_m, "image2text")
                tenant_updates["img2txt_id"] = canonical_img
                settings.IMAGE2TEXT_MDL = canonical_img

            asr_m = extra_data.get("default_asr_model")
            if asr_m:
                canonical_asr = _to_canonical_str(asr_m, "speech2text")
                tenant_updates["asr_id"] = canonical_asr
                settings.ASR_MDL = canonical_asr

            tts_m = extra_data.get("default_tts_model")
            if tts_m:
                canonical_tts = _to_canonical_str(tts_m, "tts")
                tenant_updates["tts_id"] = canonical_tts

            if tenant_updates:
                Tenant.update(**tenant_updates).execute()
                logger.info("Synchronized tenant default models across all users: %s", tenant_updates)
        except Exception as sync_err:
            logger.warning("Tenant defaults synchronization warning: %s", sync_err)
        
        # Log to audit log
        try:
            from api.db.services.ai_audit_log_service import AIAuditLogService
            AIAuditLogService.log_action(
                user_id=admin_user_id,
                action="GLOBAL_INSTANCE_UPDATE",
                target_type="global_instance",
                target_id=GLOBAL_INSTANCE_ID,
                old_val=old_data,
                new_val=filtered_updates,
            )
        except Exception as log_e:
            logger.warning("Audit logging for global instance update failed: %s", log_e)

        return cls.get_global_instance()

    @classmethod
    @DB.connection_context()
    def get_instance_stats(cls) -> dict:
        """
        Returns full statistics and default models for the Global RAGFlow Instance.
        Normalizes model IDs so they map directly to Admin UI Select components.
        """
        inst = cls.get_global_instance()
        
        total_users = User.select().count()
        total_models = AIModel.select().where(AIModel.is_global == True, AIModel.enabled == True).count()
        total_providers = AIProvider.select().where(AIProvider.is_global == True, AIProvider.status.in_(["active", "verified"])).count()
        byok_connections = AIModel.select().where(AIModel.is_custom == True).count()

        extra_data = inst.extra or {}
        if isinstance(extra_data, str):
            try:
                extra_data = json.loads(extra_data)
            except Exception:
                extra_data = {}

        def _to_admin_model_id(val: str) -> str:
            if not val:
                return ""
            try:
                # If already an exact AIModel id
                if AIModel.select().where(AIModel.id == val).count():
                    return val
                # If composite format: model@instance@provider
                from api.apps.services.models_api_service import parse_and_resolve_model_components
                m, _, p = parse_and_resolve_model_components(val)
                if m and p:
                    aim = AIModel.get_or_none(AIModel.model_name == m, AIModel.provider == p)
                    if aim:
                        return aim.id
                    # Case-insensitive check
                    for cand in AIModel.select().where(AIModel.is_global == True):
                        if cand.model_name.lower() == m.lower() and cand.provider.lower() == p.lower():
                            return cand.id
            except Exception:
                pass
            return val
        
        return {
            "instance_id": GLOBAL_INSTANCE_ID,
            "name": inst.name,
            "status": inst.status,
            "total_users": total_users,
            "total_models": total_models,
            "total_providers": total_providers,
            "byok_connections": byok_connections,
            "default_chat_model": _to_admin_model_id(extra_data.get("default_chat_model") or inst.default_free_model_id),
            "default_free_model_id": _to_admin_model_id(inst.default_free_model_id),
            "default_plus_model_id": _to_admin_model_id(inst.default_plus_model_id),
            "default_pro_model_id": _to_admin_model_id(inst.default_pro_model_id),
            "default_embd_id": _to_admin_model_id(inst.default_embd_id),
            "default_rerank_id": _to_admin_model_id(inst.default_rerank_id),
            "default_image2text_model": _to_admin_model_id(extra_data.get("default_image2text_model", "")),
            "default_asr_model": _to_admin_model_id(extra_data.get("default_asr_model", "")),
            "default_tts_model": _to_admin_model_id(extra_data.get("default_tts_model", "")),
            "byok_enabled": inst.byok_enabled,
            "max_byok_models": inst.max_byok_models,
            "byok_token_limit": inst.byok_token_limit,
            "byok_request_limit": inst.byok_request_limit,
            "create_time": inst.create_time,
            "update_time": inst.update_time,
        }
