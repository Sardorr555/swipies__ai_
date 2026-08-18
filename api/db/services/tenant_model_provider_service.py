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
        # 1. Custom provider for tenant
        res = cls.model.get_or_none(
            cls.model.tenant_id == tenant_id,
            cls.model.provider_name == provider_name,
        )
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
                if platform_provider:
                    return platform_provider

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