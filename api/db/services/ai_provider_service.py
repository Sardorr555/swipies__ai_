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
from api.db.db_models import DB, AIProvider
from api.db.services.common_service import CommonService
from api.db.services.global_instance_service import GLOBAL_INSTANCE_ID
from api.db.services.ai_audit_log_service import AIAuditLogService
from api.utils.key_crypto import encrypt_api_key, decrypt_api_key, mask_api_key

logger = logging.getLogger(__name__)


class AIProviderService(CommonService):
    model = AIProvider

    @classmethod
    @DB.connection_context()
    def get_global_providers(cls) -> list[dict]:
        """Returns all global AI providers with masked API keys."""
        providers = list(cls.model.select().where(cls.model.is_global == True))
        res = []
        for p in providers:
            pd = p.to_dict()
            pd["api_key_masked"] = mask_api_key(p.api_key)
            pd["has_api_key"] = bool(p.api_key and len(p.api_key.strip()) > 0)
            del pd["api_key"]  # Never return raw/encrypted key in generic list
            res.append(pd)
        return res

    @classmethod
    @DB.connection_context()
    def get_raw_by_provider_name(cls, provider_name: str) -> AIProvider | None:
        """Fetch raw AIProvider record by name."""
        return cls.model.get_or_none(
            cls.model.provider_name == provider_name,
            cls.model.is_global == True,
        )

    @classmethod
    @DB.connection_context()
    def save_global_provider(cls, data: dict, admin_user_id: str = "system") -> dict:
        """
        Create or update a global AI provider with encrypted API key.
        Automatically syncs to TenantModelProvider / TenantModelInstance for system admin.
        """
        provider_name = data.get("provider_name")
        if not provider_name:
            raise ValueError("provider_name is required")

        provider_id = data.get("id") or f"global_{provider_name.lower().replace(' ', '_').replace('-', '_')}"
        raw_key = data.get("api_key", "")
        base_url = data.get("base_url", "")
        org = data.get("organization", "")
        version = data.get("api_version", "")
        status = data.get("status", "active")
        extra = data.get("extra", {})

        existing = cls.model.get_or_none(cls.model.id == provider_id)
        if not existing:
            existing = cls.model.get_or_none(cls.model.provider_name == provider_name, cls.model.is_global == True)

        now = current_timestamp()
        old_val = existing.to_dict() if existing else None

        # If api_key provided, encrypt it; otherwise retain existing key if updating
        if raw_key and not raw_key.startswith("enc:v1:"):
            enc_key = encrypt_api_key(raw_key)
        elif raw_key:
            enc_key = raw_key
        elif existing:
            enc_key = existing.api_key
        else:
            enc_key = ""

        provider_record = {
            "id": provider_id,
            "provider_name": provider_name,
            "base_url": base_url,
            "api_key": enc_key,
            "organization": org,
            "api_version": version,
            "status": status,
            "is_global": True,
            "owner_user_id": None,
            "global_instance_id": GLOBAL_INSTANCE_ID,
            "extra": extra,
            "update_time": now,
        }

        if existing:
            cls.model.update(**provider_record).where(cls.model.id == existing.id).execute()
        else:
            provider_record["create_time"] = now
            cls.model.create(**provider_record)

        # Audit log
        AIAuditLogService.log_action(
            user_id=admin_user_id,
            action="PROVIDER_UPDATE" if existing else "PROVIDER_CREATE",
            target_type="ai_provider",
            target_id=provider_id,
            old_val=old_val,
            new_val=provider_record,
        )

        # Sync to RAGFlow TenantModelProvider / TenantModelInstance for admin tenant
        try:
            from api.db.services.tenant_model_provider_service import TenantModelProviderService
            from api.db.services.tenant_model_instance_service import TenantModelInstanceService

            admin_tenant_id = TenantModelProviderService._get_admin_tenant_id()
            if admin_tenant_id:
                p_obj = TenantModelProviderService.get_by_tenant_id_and_provider_name(admin_tenant_id, provider_name, fallback_admin=False)
                if not p_obj:
                    TenantModelProviderService.insert(tenant_id=admin_tenant_id, provider_name=provider_name)
                    p_obj = TenantModelProviderService.get_by_tenant_id_and_provider_name(admin_tenant_id, provider_name, fallback_admin=False)

                if p_obj:
                    inst_obj = TenantModelInstanceService.get_by_provider_id_and_instance_name(p_obj.id, "default")
                    extra_data = {"base_url": base_url, "organization": org, "api_version": version}
                    if not inst_obj:
                        TenantModelInstanceService.create_instance(
                            provider_id=p_obj.id,
                            instance_name="default",
                            api_key=decrypt_api_key(enc_key) if enc_key else "",
                            extra=json.dumps(extra_data),
                        )
                    else:
                        TenantModelInstanceService.filter_update(
                            [TenantModelInstanceService.model.id == inst_obj.id],
                            {"api_key": decrypt_api_key(enc_key) if enc_key else "", "extra": json.dumps(extra_data)},
                        )
        except Exception as sync_e:
            logger.warning("AIProviderService sync to core provider instance warning: %s", sync_e)

        return cls.get_provider_safe(provider_id)

    @classmethod
    @DB.connection_context()
    def get_provider_safe(cls, provider_id: str) -> dict | None:
        p = cls.model.get_or_none(cls.model.id == provider_id)
        if not p:
            return None
        pd = p.to_dict()
        pd["api_key_masked"] = mask_api_key(p.api_key)
        pd["has_api_key"] = bool(p.api_key and len(p.api_key.strip()) > 0)
        del pd["api_key"]
        return pd

    @classmethod
    @DB.connection_context()
    def delete_global_provider(cls, provider_id: str, admin_user_id: str = "system") -> bool:
        p = cls.model.get_or_none(cls.model.id == provider_id)
        if not p:
            return False
        old_val = p.to_dict()
        cls.model.delete().where(cls.model.id == provider_id).execute()
        AIAuditLogService.log_action(
            user_id=admin_user_id,
            action="PROVIDER_DELETE",
            target_type="ai_provider",
            target_id=provider_id,
            old_val=old_val,
        )
        return True
