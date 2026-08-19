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

import asyncio
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
    async def async_verify_provider_connection(
        cls, provider_name: str, raw_api_key: str, base_url: str = "", extra_params: dict = None
    ) -> tuple[bool, str, list[dict]]:
        """
        Verify API Key connectivity with provider using RAGFlow's LLM testers,
        and dynamically discover supported models for that provider.
        """
        if not raw_api_key:
            return False, "API key is required for verification.", []

        # If encrypted, decrypt first
        if raw_api_key.startswith("enc:v1:"):
            try:
                raw_api_key = decrypt_api_key(raw_api_key)
            except Exception as de:
                return False, f"Decryption error: {de}", []

        from rag.llm import ChatModel, EmbeddingModel, RerankModel
        from api.db.services.llm_service import LLMService
        from common.constants import LLMType

        source_llms = list(LLMService.query(fid=provider_name))
        if not source_llms:
            from common import settings
            fac_list = [f for f in (getattr(settings, "FACTORY_LLM_INFOS", []) or []) if f.get("name") == provider_name]
            if fac_list and fac_list[0].get("llm"):
                source_llms = [type("MockLLM", (), item)() for item in fac_list[0]["llm"]]

        if not source_llms:
            return False, f"No model configurations found for provider '{provider_name}'.", []

        chat_passed = False
        embd_passed = False
        rerank_passed = False
        passed_models = []
        error_msgs = []
        timeout_sec = 12

        for llm in source_llms:
            m_name = getattr(llm, "llm_name", "")
            m_type = getattr(llm, "model_type", "")
            if not m_name:
                continue

            if not chat_passed and m_type in [LLMType.CHAT.value, "CHAT"]:
                if provider_name in ChatModel:
                    try:
                        mdl = ChatModel[provider_name](raw_api_key, m_name, base_url=base_url, **(extra_params or {}))

                        async def check_chat():
                            async for chunk in mdl.async_chat_streamly(
                                None,
                                [{"role": "user", "content": "Hi"}],
                                {"temperature": 0.5},
                            ):
                                if chunk and isinstance(chunk, str) and chunk.find("**ERROR**") < 0:
                                    return True
                            return False

                        res = await asyncio.wait_for(check_chat(), timeout=timeout_sec)
                        if res:
                            chat_passed = True
                            passed_models.append(m_name)
                    except Exception as ce:
                        error_msgs.append(f"Chat ({m_name}): {ce}")

            elif not embd_passed and m_type in [LLMType.EMBEDDING.value, "EMBEDDING"]:
                if provider_name in EmbeddingModel:
                    try:
                        mdl = EmbeddingModel[provider_name](raw_api_key, m_name, base_url=base_url)
                        arr, tc = await asyncio.wait_for(
                            asyncio.to_thread(mdl.encode, ["Test connection"]),
                            timeout=timeout_sec,
                        )
                        if len(arr) > 0 and len(arr[0]) > 0:
                            embd_passed = True
                            passed_models.append(m_name)
                    except Exception as ee:
                        error_msgs.append(f"Embedding ({m_name}): {ee}")

            elif not rerank_passed and m_type in [LLMType.RERANK.value, "RERANK"]:
                if provider_name in RerankModel:
                    try:
                        mdl = RerankModel[provider_name](raw_api_key, m_name, base_url=base_url)
                        arr, tc = await asyncio.wait_for(
                            asyncio.to_thread(mdl.similarity, "Hi", ["Hello"]),
                            timeout=timeout_sec,
                        )
                        if len(arr) > 0:
                            rerank_passed = True
                            passed_models.append(m_name)
                    except Exception as re:
                        error_msgs.append(f"Rerank ({m_name}): {re}")

            if chat_passed or embd_passed or rerank_passed:
                break

        # If any test passed, return discovered models
        if chat_passed or embd_passed or rerank_passed:
            discovered_models = []
            for llm in source_llms:
                discovered_models.append({
                    "model_name": getattr(llm, "llm_name", ""),
                    "model_type": getattr(llm, "model_type", "CHAT"),
                    "max_tokens": getattr(llm, "max_tokens", 8192) or 8192,
                })
            return True, "API connection verified successfully.", discovered_models

        err_detail = "; ".join(error_msgs) if error_msgs else f"Failed to connect to provider '{provider_name}'."
        return False, err_detail, []

    @classmethod
    @DB.connection_context()
    def save_global_provider(cls, data: dict, admin_user_id: str = "system") -> dict:
        """
        Create or update a global AI provider with encrypted API key.
        Automatically syncs to TenantModelProvider / TenantModelInstance and populates
        only the verified/connected models into AIModel & TenantModel!
        """
        from common.misc_utils import get_uuid

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
            from api.db.services.llm_service import LLMService
            from api.db.services.ai_policy_service import AIModelService, SubscriptionAIPolicyService

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
                            {"api_key": decrypted_key, "extra": json.dumps(extra_data)},
                        )

                    # If API key is configured, dynamically populate and activate all models for this provider
                    if enc_key:
                        source_llms = list(LLMService.query(fid=provider_name))
                        for llm in source_llms:
                            m_name = getattr(llm, "llm_name", "")
                            m_type = getattr(llm, "model_type", "CHAT")
                            max_tok = getattr(llm, "max_tokens", 8192) or 8192
                            m_id = f"{provider_name.lower()}/{m_name}"

                            # 1. Register in TenantLLM for admin tenant
                            if not TenantLLMService.filter_update(
                                [
                                    TenantLLMService.model.tenant_id == admin_tenant_id,
                                    TenantLLMService.model.llm_factory == provider_name,
                                    TenantLLMService.model.llm_name == m_name,
                                ],
                                {"api_key": enc_key, "api_base": base_url, "max_tokens": max_tok},
                            ):
                                TenantLLMService.save(
                                    tenant_id=admin_tenant_id,
                                    llm_factory=provider_name,
                                    llm_name=m_name,
                                    model_type=m_type,
                                    api_key=enc_key,
                                    api_base=base_url,
                                    max_tokens=max_tok,
                                )

                            # 2. Register in TenantModel
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
                                    status="active",
                                )
                            else:
                                TenantModelService.filter_update(
                                    [TenantModelService.model.id == m_obj.id],
                                    {"status": "active"},
                                )

                            # 3. Register in AIModel table
                            existing_aimodel = AIModelService.query(id=m_id)
                            aimodel_data = {
                                "id": m_id,
                                "provider": provider_name,
                                "model_name": m_name,
                                "model_type": m_type,
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

                            # 4. Default Policies for FREE, PLUS, PRO plans
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
