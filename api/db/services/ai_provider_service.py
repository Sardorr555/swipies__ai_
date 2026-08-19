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
from common.misc_utils import get_uuid
from common.constants import ActiveStatusEnum
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
    async def async_verify_provider_connection(
        cls, provider_name: str, raw_api_key: str, base_url: str = "", extra_params: dict = None
    ) -> tuple[bool, str, list[dict]]:
        """
        Verify API Key using RAGFlow's core provider_api_service.verify_api_key,
        and dynamically discover supported models for that provider.
        """
        if not raw_api_key:
            return False, "API key is required for verification.", []

        if raw_api_key.startswith("enc:v1:"):
            try:
                raw_api_key = decrypt_api_key(raw_api_key)
            except Exception as de:
                return False, f"Decryption error: {de}", []

        extra_params = extra_params or {}
        region = extra_params.get("region", "default")
        model_info = extra_params.get("model_info", None)

        from api.apps.services.provider_api_service import verify_api_key
        from common.settings import FACTORY_LLM_INFOS

        success, msg = await verify_api_key(
            provider_id_or_name=provider_name,
            api_key=raw_api_key,
            base_url=base_url,
            region=region,
            model_info=model_info,
        )

        discovered_models = []
        if success:
            target_factory_name = "siliconflow_intl" if (region == "intl" and provider_name.lower() == "siliconflow") else provider_name
            fac_entry = next((f for f in (FACTORY_LLM_INFOS or []) if f.get("name") == target_factory_name), None)
            if not fac_entry:
                fac_entry = next((f for f in (FACTORY_LLM_INFOS or []) if f.get("name", "").lower() == provider_name.lower()), None)
            if fac_entry and fac_entry.get("llm"):
                for llm in fac_entry["llm"]:
                    m_type = llm.get("model_type", "chat")
                    if isinstance(m_type, list):
                        m_type = m_type[0] if m_type else "chat"
                    discovered_models.append({
                        "model_name": llm.get("llm_name") or llm.get("name", ""),
                        "model_type": str(m_type).upper(),
                        "max_tokens": llm.get("max_tokens", 8192) or 8192,
                    })

        return success, msg, discovered_models

    @classmethod
    @DB.connection_context()
    def save_global_provider(cls, data: dict, admin_user_id: str = "system") -> dict:
        """
        Create or update a global AI provider with encrypted API key.
        Uses core provider instance architecture and dynamically populates
        only verified models into AIModel & TenantModel.
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

        # Sync to RAGFlow TenantModelProvider / TenantModelInstance & dynamically add available models
        try:
            from api.db.services.tenant_model_provider_service import TenantModelProviderService
            from api.db.services.tenant_model_instance_service import TenantModelInstanceService
            from api.db.services.tenant_model_service import TenantModelService
            from api.db.services.tenant_llm_service import TenantLLMService
            from api.db.services.ai_policy_service import AIModelService, SubscriptionAIPolicyService
            from common.settings import FACTORY_LLM_INFOS

            admin_tenant_id = TenantModelProviderService._get_admin_tenant_id()
            if admin_tenant_id:
                p_obj = TenantModelProviderService.get_by_tenant_id_and_provider_name(admin_tenant_id, provider_name, fallback_admin=False)
                if not p_obj:
                    p_id = get_uuid()
                    TenantModelProviderService.insert(id=p_id, tenant_id=admin_tenant_id, provider_name=provider_name)
                    p_obj = TenantModelProviderService.get_by_tenant_id_and_provider_name(admin_tenant_id, provider_name, fallback_admin=False)

                if p_obj:
                    inst_obj = TenantModelInstanceService.get_by_provider_id_and_instance_name(p_obj.id, "default")
                    extra_data = {"base_url": base_url, "organization": org, "api_version": version}
                    decrypted_key = decrypt_api_key(enc_key) if enc_key else ""
                    if not inst_obj:
                        inst_obj = TenantModelInstanceService.create_instance(
                            provider_id=p_obj.id,
                            instance_name="default",
                            api_key=decrypted_key,
                            extra=json.dumps(extra_data),
                        )
                    else:
                        TenantModelInstanceService.filter_update(
                            [TenantModelInstanceService.model.id == inst_obj.id],
                            {"api_key": decrypted_key, "extra": json.dumps(extra_data), "status": ActiveStatusEnum.ACTIVE.value},
                        )

                    # Populate models from FACTORY_LLM_INFOS for this provider
                    fac_entry = next((f for f in (FACTORY_LLM_INFOS or []) if f.get("name") == provider_name or f.get("name", "").lower() == provider_name.lower()), None)
                    if fac_entry and fac_entry.get("llm") and decrypted_key:
                        for llm in fac_entry["llm"]:
                            m_name = llm.get("llm_name") or llm.get("name", "")
                            raw_types = llm.get("model_type", ["chat"])
                            m_types = raw_types if isinstance(raw_types, list) else [raw_types]
                            max_tok = llm.get("max_tokens", 8192) or 8192
                            m_id = f"{provider_name.lower()}/{m_name}"

                            for m_type in m_types:
                                # 1. TenantLLM for admin
                                TenantLLMService.filter_update(
                                    [
                                        TenantLLMService.model.tenant_id == admin_tenant_id,
                                        TenantLLMService.model.llm_factory == provider_name,
                                        TenantLLMService.model.llm_name == m_name,
                                    ],
                                    {"api_key": enc_key, "api_base": base_url, "max_tokens": max_tok},
                                )

                                # 2. TenantModel
                                m_obj = TenantModelService.get_by_provider_id_and_instance_id_and_model_type_and_model_name(
                                    p_obj.id, inst_obj.id, m_type, m_name
                                )
                                if not m_obj:
                                    TenantModelService.insert(
                                        id=get_uuid(),
                                        model_name=m_name,
                                        provider_id=p_obj.id,
                                        instance_id=inst_obj.id,
                                        model_type=m_type,
                                        extra=json.dumps({"max_tokens": max_tok}),
                                        status=ActiveStatusEnum.ACTIVE.value,
                                    )
                                else:
                                    TenantModelService.filter_update(
                                        [TenantModelService.model.id == m_obj.id],
                                        {"status": ActiveStatusEnum.ACTIVE.value},
                                    )

                            # 3. AIModel table
                            existing_aimodel = AIModelService.query(id=m_id)
                            aimodel_data = {
                                "id": m_id,
                                "provider": provider_name,
                                "model_name": m_name,
                                "model_type": str(m_types[0]).upper() if m_types else "CHAT",
                                "base_url": base_url,
                                "api_key": enc_key,
                                "max_tokens": max_tok,
                                "enabled": True,
                                "is_global": True,
                                "is_custom": False,
                                "global_instance_id": GLOBAL_INSTANCE_ID,
                                "status": "active",
                                "update_time": now,
                            }
                            if existing_aimodel:
                                AIModelService.filter_update([AIModelService.model.id == m_id], aimodel_data)
                            else:
                                aimodel_data["create_time"] = now
                                AIModelService.save(**aimodel_data)

                            # 4. Access Policies for FREE, PLUS, PRO
                            for plan_id in ["free", "plus", "pro"]:
                                pol_id = f"{plan_id}_{m_id}"
                                if not SubscriptionAIPolicyService.query(id=pol_id):
                                    SubscriptionAIPolicyService.save(
                                        id=pol_id,
                                        plan_id=plan_id,
                                        model_id=m_id,
                                        model_token_limit=0,
                                        enabled=True,
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
