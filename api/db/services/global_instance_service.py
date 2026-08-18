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
                    default_free_model_id="openai/gpt-4o-mini",
                    default_plus_model_id="openai/gpt-4o",
                    default_pro_model_id="anthropic/claude-3-5-sonnet-20241022",
                    default_embd_id="openai/text-embedding-3-small",
                    default_rerank_id="BAAI/bge-reranker-v2-m3",
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
        Updates settings on the Global RAGFlow Instance and logs the change to AIAuditLog.
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
        
        filtered_updates = {k: v for k, v in updates.items() if k in allowed_fields}
        filtered_updates["update_time"] = current_timestamp()

        cls.model.update(**filtered_updates).where(cls.model.id == GLOBAL_INSTANCE_ID).execute()
        
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
        Returns full statistics for the Global RAGFlow Instance.
        """
        inst = cls.get_global_instance()
        
        total_users = User.select().count()
        total_models = AIModel.select().where(AIModel.is_global == True, AIModel.enabled == True).count()
        total_providers = AIProvider.select().where(AIProvider.is_global == True, AIProvider.status == "active").count()
        byok_connections = AIModel.select().where(AIModel.is_custom == True).count()
        
        return {
            "instance_id": GLOBAL_INSTANCE_ID,
            "name": inst.name,
            "status": inst.status,
            "total_users": total_users,
            "total_models": total_models,
            "total_providers": total_providers,
            "byok_connections": byok_connections,
            "default_free_model_id": inst.default_free_model_id,
            "default_plus_model_id": inst.default_plus_model_id,
            "default_pro_model_id": inst.default_pro_model_id,
            "default_embd_id": inst.default_embd_id,
            "default_rerank_id": inst.default_rerank_id,
            "byok_enabled": inst.byok_enabled,
            "max_byok_models": inst.max_byok_models,
            "byok_token_limit": inst.byok_token_limit,
            "byok_request_limit": inst.byok_request_limit,
            "create_time": inst.create_time,
            "update_time": inst.update_time,
        }
