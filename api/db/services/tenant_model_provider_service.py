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
import os
import logging
from api.db.db_models import DB, TenantModelProvider
from api.db.services.common_service import CommonService

logger = logging.getLogger(__name__)

_ADMIN_TENANT_ID_CACHE = None


class TenantModelProviderService(CommonService):
    model = TenantModelProvider

    @classmethod
    def _get_admin_tenant_id(cls, current_tenant_id=None):
        global _ADMIN_TENANT_ID_CACHE
        if _ADMIN_TENANT_ID_CACHE:
            return _ADMIN_TENANT_ID_CACHE

        try:
            from api.db.db_models import User
            admin_email = os.getenv("DEFAULT_SUPERUSER_EMAIL", "admin@ragflow.io").strip().lower()
            admin_user = User.get_or_none(User.email.fn.LOWER() == admin_email)
            if not admin_user:
                admin_user = User.get_or_none(User.is_superuser == True)
            if admin_user:
                _ADMIN_TENANT_ID_CACHE = admin_user.id
                return admin_user.id
        except Exception as e:
            logger.warning(f"_get_admin_tenant_id failed: {e}")
        return None

    @classmethod
    def _is_pro_or_enterprise(cls, tenant_id):
        if not tenant_id:
            return False
        admin_tenant_id = cls._get_admin_tenant_id()
        if admin_tenant_id and tenant_id == admin_tenant_id:
            return True
        try:
            from api.db.db_models import User, Tenant
            user = User.get_or_none(User.id == tenant_id)
            if user and getattr(user, "is_superuser", False):
                return True
            tenant = Tenant.get_or_none(Tenant.id == tenant_id)
            if tenant:
                plan_type = (getattr(tenant, "plan_type", None) or "").lower()
                if plan_type in ["pro", "enterprise"]:
                    return True
        except Exception as e:
            logger.warning(f"_is_pro_or_enterprise check error: {e}")
        return False

    @classmethod
    @DB.connection_context()
    def get_by_tenant_id_and_provider_name(cls, tenant_id, provider_name, fallback_admin=True):
        if not provider_name:
            return None

        # 1. Custom provider for tenant
        res = cls.model.get_or_none(
            cls.model.tenant_id == tenant_id,
            cls.model.provider_name == provider_name,
        )
        if not res:
            for p in cls.model.select().where(cls.model.tenant_id == tenant_id):
                if p.provider_name.lower() == provider_name.lower():
                    res = p
                    break
        if res:
            return res

        # 2. Platform instance (system admin) if fallback_admin is True
        if fallback_admin:
            admin_tenant_id = cls._get_admin_tenant_id()
            if admin_tenant_id and admin_tenant_id != tenant_id:
                platform_provider = cls.model.get_or_none(
                    cls.model.tenant_id == admin_tenant_id,
                    cls.model.provider_name == provider_name,
                )
                if not platform_provider:
                    for ap in cls.model.select().where(cls.model.tenant_id == admin_tenant_id):
                        if ap.provider_name.lower() == provider_name.lower():
                            platform_provider = ap
                            break
                if platform_provider:
                    return platform_provider

            # 3. Fallback to Global AIProvider table
            try:
                from api.db.db_models import AIProvider
                from common.misc_utils import get_uuid
                from api.utils.key_crypto import decrypt_api_key
                import json

                gp = AIProvider.get_or_none(AIProvider.provider_name == provider_name, AIProvider.is_global == True)
                if not gp:
                    for g in AIProvider.select().where(AIProvider.is_global == True):
                        if g.provider_name.lower() == provider_name.lower():
                            gp = g
                            break
                if gp and gp.api_key:
                    target_tenant = admin_tenant_id or tenant_id
                    p_obj = cls.model.get_or_none(cls.model.tenant_id == target_tenant, cls.model.provider_name == gp.provider_name)
                    if not p_obj:
                        p_id = get_uuid()
                        cls.insert(id=p_id, tenant_id=target_tenant, provider_name=gp.provider_name)
                        p_obj = cls.model.get_or_none(cls.model.id == p_id)
                    if p_obj:
                        from api.db.services.tenant_model_instance_service import TenantModelInstanceService
                        from api.db.services.tenant_model_service import TenantModelService
                        from common.settings import FACTORY_LLM_INFOS
                        from common.constants import ActiveStatusEnum

                        inst = TenantModelInstanceService.get_by_provider_id_and_instance_name(p_obj.id, "default")
                        if not inst:
                            inst = TenantModelInstanceService.create_instance(
                                provider_id=p_obj.id,
                                instance_name="default",
                                api_key=decrypt_api_key(gp.api_key),
                                extra=json.dumps({"base_url": gp.base_url or ""}),
                            )
                        if inst:
                            fac_entry = next((f for f in (FACTORY_LLM_INFOS or []) if f.get("name", "").lower() == gp.provider_name.lower()), None)
                            if fac_entry and fac_entry.get("llm"):
                                for llm in fac_entry["llm"]:
                                    m_name = llm.get("llm_name") or llm.get("name", "")
                                    m_types = llm.get("model_type", ["chat"])
                                    if not isinstance(m_types, list):
                                        m_types = [m_types]
                                    for m_type in m_types:
                                        m_obj = TenantModelService.get_by_provider_id_and_instance_id_and_model_type_and_model_name(
                                            p_obj.id, inst.id, m_type, m_name
                                        )
                                        if not m_obj:
                                            TenantModelService.insert(
                                                id=get_uuid(),
                                                model_name=m_name,
                                                provider_id=p_obj.id,
                                                instance_id=inst.id,
                                                model_type=m_type,
                                                extra=json.dumps({"max_tokens": llm.get("max_tokens", 8192) or 8192}),
                                                status=ActiveStatusEnum.ACTIVE.value,
                                            )
                        return p_obj
            except Exception as gp_err:
                logger.warning(f"Fallback to AIProvider in TenantModelProviderService error: {gp_err}")

        return None

    @classmethod
    @DB.connection_context()
    def get_by_tenant_id_and_provider_id(cls, tenant_id, provider_id, fallback_admin=True):
        if cls._is_pro_or_enterprise(tenant_id):
            custom_res = cls.model.get_or_none(
                cls.model.tenant_id == tenant_id,
                cls.model.id == provider_id,
            )
            if custom_res:
                return custom_res

        if fallback_admin:
            admin_tenant_id = cls._get_admin_tenant_id(tenant_id)
            if admin_tenant_id:
                platform_provider = cls.model.get_or_none(
                    cls.model.tenant_id == admin_tenant_id,
                    cls.model.id == provider_id,
                )
                if platform_provider:
                    return platform_provider

        return cls.model.get_or_none(
            cls.model.tenant_id == tenant_id,
            cls.model.id == provider_id,
        )

    @classmethod
    @DB.connection_context()
    def get_by_tenant_id(cls, tenant_id, include_admin=True):
        providers = list(cls.model.select().where(cls.model.tenant_id == tenant_id))
        if include_admin:
            admin_tenant_id = cls._get_admin_tenant_id(tenant_id)
            if admin_tenant_id:
                existing_names = {p.provider_name for p in providers}
                admin_providers = cls.model.select().where(cls.model.tenant_id == admin_tenant_id)
                for ap in admin_providers:
                    if ap.provider_name not in existing_names:
                        providers.append(ap)
        return providers

    @classmethod
    @DB.connection_context()
    def delete_by_tenant_id(cls, tenant_id):
        return cls.model.delete().where(cls.model.tenant_id == tenant_id).execute()

    @classmethod
    @DB.connection_context()
    def delete_by_tenant_id_and_provider_name(cls, tenant_id, provider_name):
        return cls.model.delete().where(
            cls.model.tenant_id == tenant_id,
            cls.model.provider_name == provider_name,
        ).execute()

    @classmethod
    @DB.connection_context()
    def list_provider_names_by_tenant_id(cls, tenant_id, include_admin=True):
        names = set(row.provider_name for row in cls.model.select(cls.model.provider_name).where(cls.model.tenant_id == tenant_id))
        if include_admin:
            admin_tenant_id = cls._get_admin_tenant_id(tenant_id)
            if admin_tenant_id:
                admin_names = [row.provider_name for row in cls.model.select(cls.model.provider_name).where(cls.model.tenant_id == admin_tenant_id)]
                names.update(admin_names)
        return list(names)