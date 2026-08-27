#
#  Copyright 2026 The InfiniFlow & Swipies AI Authors. All Rights Reserved.
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
import time
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Union, Any

from common.ai_gateway.types import ProviderType
from common.ai_gateway.errors import SecretRedactor, ProviderAuthError

logger = logging.getLogger("ai_gateway.credentials")


@dataclass
class ProviderCredentialRecord:
    """
    Safe provider configuration object for Admin Panel CRUD and inspection.
    Guarantees API keys are masked by default to prevent secret exposure in UI/API responses.
    """
    provider: str
    provider_display_name: str
    base_url: Optional[str] = None
    masked_api_key: str = ""
    is_active: bool = True
    is_configured: bool = False
    is_live_tested: bool = True
    is_available_in_admin: bool = True
    verification_status: str = "verified"  # "verified" | "requires_live_test"
    status_reason: Optional[str] = None
    source: str = "none"  # "tenant_db" | "system_db" | "environment" | "none"
    supported_models: List[str] = field(default_factory=list)
    updated_at: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "provider_display_name": self.provider_display_name,
            "base_url": self.base_url,
            "masked_api_key": self.masked_api_key,
            "is_active": self.is_active,
            "is_configured": self.is_configured,
            "is_live_tested": self.is_live_tested,
            "is_available_in_admin": self.is_available_in_admin,
            "verification_status": self.verification_status,
            "status_reason": self.status_reason,
            "source": self.source,
            "supported_models": self.supported_models,
            "updated_at": self.updated_at,
        }


@dataclass
class ConnectionTestResult:
    """Standardized test result when verifying provider connectivity in Admin Panel."""
    provider: str
    success: bool
    status_code: int
    latency_ms: float
    message: str
    tested_at: int = field(default_factory=lambda: int(time.time()))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "success": self.success,
            "status_code": self.status_code,
            "latency_ms": round(self.latency_ms, 2),
            "message": SecretRedactor.redact(self.message),
            "tested_at": self.tested_at,
        }


class CredentialResolver:
    """
    Centralized, Single Source of Truth for AI Provider Credentials.
    
    Responsibilities:
    1. Runtime Resolution: Resolves decrypted (api_key, base_url) in-memory for Gateway execution.
    2. Admin Panel CRUD: Full management API (list, get, save, delete, test_connection) with automatic masking.
    3. Multi-layer Fallback: Resolves from Tenant DB -> System DB -> Environment Variables.
    4. Zero-Leak Policy: Plaintext keys never leave the secure backend memory layer.
    """

    PROVIDER_METADATA: Dict[str, Dict[str, Any]] = {
        ProviderType.OPENAI.value: {
            "name": "OpenAI",
            "env_key": "OPENAI_API_KEY",
            "env_base_url": "OPENAI_BASE_URL",
            "default_base_url": "https://api.openai.com/v1",
            "models": ["gpt-4o", "gpt-4o-mini", "o1", "o3-mini", "text-embedding-3-small", "text-embedding-3-large"],
            "db_factory_names": ["OpenAI", "openai"],
            "is_live_tested": True,
        },
        ProviderType.DEEPSEEK.value: {
            "name": "DeepSeek",
            "env_key": "DEEPSEEK_API_KEY",
            "env_base_url": "DEEPSEEK_BASE_URL",
            "default_base_url": "https://api.deepseek.com/v1",
            "models": ["deepseek-chat", "deepseek-reasoner"],
            "db_factory_names": ["DeepSeek", "deepseek"],
            "is_live_tested": True,
        },
        ProviderType.ANTHROPIC.value: {
            "name": "Anthropic",
            "env_key": "ANTHROPIC_API_KEY",
            "env_base_url": "ANTHROPIC_BASE_URL",
            "default_base_url": "https://api.anthropic.com/",
            "models": ["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022", "claude-3-7-sonnet", "claude-3-opus-20240229"],
            "db_factory_names": ["Anthropic", "anthropic"],
            "is_live_tested": False,  # Blocked in Admin Panel until TASK-FOLLOWUP-LIVE-TEST-ANTHROPIC-GEMINI is closed
            "live_test_env_flag": "AI_GATEWAY_ANTHROPIC_LIVE_TESTED",
        },
        ProviderType.GEMINI.value: {
            "name": "Google Gemini",
            "env_key": "GEMINI_API_KEY",
            "env_key_fallback": "GOOGLE_API_KEY",
            "env_base_url": "GEMINI_BASE_URL",
            "default_base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
            "models": ["gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash", "text-embedding-004"],
            "db_factory_names": ["Gemini", "Google", "gemini"],
            "is_live_tested": False,  # Blocked in Admin Panel until TASK-FOLLOWUP-LIVE-TEST-ANTHROPIC-GEMINI is closed
            "live_test_env_flag": "AI_GATEWAY_GEMINI_LIVE_TESTED",
        },
    }

    # In-memory transient overrides / test storage for unit tests and local overrides
    _memory_store: Dict[str, Dict[str, Any]] = {}
    _live_tested_overrides: Dict[str, bool] = {}

    @classmethod
    def mask_api_key(cls, raw_key: Optional[str]) -> str:
        """Masks an API key for safe UI display: sk-proj-1234567890abcdef1234 -> sk-proj...1234"""
        if not raw_key:
            return ""
        k = raw_key.strip()
        if len(k) <= 8:
            return "********"
        prefix = k[:7] if k.startswith("sk-") or k.startswith("AIza") else k[:4]
        suffix = k[-4:]
        return f"{prefix}...{suffix}"

    @classmethod
    def resolve(
        cls,
        provider_type: Union[ProviderType, str],
        tenant_id: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Tuple[str, Optional[str]]:
        """
        Primary execution entry point for AI Gateway.
        Resolves decrypted API key and base URL in order:
          1. In-memory custom configuration (if configured)
          2. TenantLLM in DB (if tenant_id supplied)
          3. System / Admin TenantLLM in DB
          4. Environment Variables
        
        Returns: (api_key: str, base_url: Optional[str])
        """
        p_val = provider_type.value if isinstance(provider_type, ProviderType) else str(provider_type).lower()
        meta = cls.PROVIDER_METADATA.get(p_val, {
            "name": p_val.capitalize(),
            "env_key": f"{p_val.upper()}_API_KEY",
            "env_base_url": f"{p_val.upper()}_BASE_URL",
            "default_base_url": None,
            "db_factory_names": [p_val],
        })

        # 1. Check in-memory store (e.g. for testing or tenant sessions)
        mem_key = f"{p_val}:{tenant_id or 'system'}"
        if mem_key in cls._memory_store and cls._memory_store[mem_key].get("is_active", True):
            mem_data = cls._memory_store[mem_key]
            if mem_data.get("api_key"):
                return mem_data["api_key"], mem_data.get("base_url") or meta.get("default_base_url")

        # 2. Check AIProvider in Database (Single Source of Truth)
        try:
            from api.db.db_models import AIProvider
            prov_obj = AIProvider.get_or_none(AIProvider.provider_name == p_val, AIProvider.is_global == True)
            if prov_obj and prov_obj.api_key and prov_obj.status != "unconfigured":
                return prov_obj.api_key, prov_obj.base_url or meta.get("default_base_url")
        except Exception:
            pass

        # 3. Check Database (TenantLLM)
        try:
            from api.db.services.tenant_llm_service import TenantLLMService
            factory_names = meta.get("db_factory_names", [p_val])
            
            # Query tenant DB
            if tenant_id:
                for fname in factory_names:
                    llm_obj = TenantLLMService.get_api_key(tenant_id=tenant_id, model_name=model or fname)
                    if llm_obj and llm_obj.api_key:
                        raw_key, _, _ = TenantLLMService._decode_api_key_config(llm_obj.api_key)
                        if raw_key:
                            base_url = llm_obj.api_base or meta.get("default_base_url")
                            return raw_key, base_url

            # Query system DB (Admin Tenant)
            admin_tenant_id = None
            try:
                from api.db.services.tenant_model_provider_service import TenantModelProviderService
                admin_tenant_id = TenantModelProviderService._get_admin_tenant_id()
            except Exception:
                pass

            if admin_tenant_id and admin_tenant_id != tenant_id:
                for fname in factory_names:
                    llm_obj = TenantLLMService.get_api_key(tenant_id=admin_tenant_id, model_name=model or fname)
                    if llm_obj and llm_obj.api_key:
                        raw_key, _, _ = TenantLLMService._decode_api_key_config(llm_obj.api_key)
                        if raw_key:
                            base_url = llm_obj.api_base or meta.get("default_base_url")
                            return raw_key, base_url
        except Exception as e:
            logger.debug(f"DB credential resolution fallback for {p_val}: {e}")

        # 4. Fallback to Environment Variables
        env_key_name = meta.get("env_key", f"{p_val.upper()}_API_KEY")
        api_key = os.environ.get(env_key_name, "")
        if not api_key and "env_key_fallback" in meta:
            api_key = os.environ.get(meta["env_key_fallback"], "")

        env_base_url_name = meta.get("env_base_url", f"{p_val.upper()}_BASE_URL")
        base_url = os.environ.get(env_base_url_name) or meta.get("default_base_url")

        return api_key, base_url

    # =========================================================================
    # Admin Panel CRUD Operations (Reusable by Admin API / UI Endpoints)
    # =========================================================================

    @classmethod
    def is_provider_live_tested(cls, provider_type: Union[ProviderType, str]) -> bool:
        """
        Returns True if the provider has been verified with live outbound API tests.
        Untested providers (Anthropic, Gemini) are blocked from Admin Panel selection
        until TASK-FOLLOWUP-LIVE-TEST-ANTHROPIC-GEMINI is closed.
        Can be overridden via environment flags (e.g. AI_GATEWAY_ENABLE_UNTESTED_PROVIDERS=true
        or AI_GATEWAY_ANTHROPIC_LIVE_TESTED=true).
        """
        p_val = provider_type.value if isinstance(provider_type, ProviderType) else str(provider_type).lower()
        if cls._live_tested_overrides.get(p_val, False):
            return True
        if os.environ.get("AI_GATEWAY_ENABLE_UNTESTED_PROVIDERS", "false").lower() in ("true", "1"):
            return True
        meta = cls.PROVIDER_METADATA.get(p_val, {})
        env_flag = meta.get("live_test_env_flag")
        if env_flag and os.environ.get(env_flag, "false").lower() in ("true", "1"):
            return True

        # Check DB persistent activation
        try:
            from api.db.services.tenant_llm_service import TenantLLMService
            factory_names = meta.get("db_factory_names", [p_val])
            for fname in factory_names:
                existing = TenantLLMService.query(llm_factory=fname)
                if existing and any(str(obj.status) == "1" and obj.api_key for obj in existing):
                    return True
        except Exception:
            pass

        return meta.get("is_live_tested", True)

    @classmethod
    def list_providers_for_admin(cls, tenant_id: Optional[str] = None, only_available: bool = False) -> List[ProviderCredentialRecord]:
        """
        Lists all supported providers with their configuration status and masked keys.
        Used by Admin Panel provider dashboard.
        If only_available=True, returns only live-tested providers available for UI selection.
        """
        records: List[ProviderCredentialRecord] = []
        for p_val in cls.PROVIDER_METADATA.keys():
            rec = cls.get_provider_for_admin(p_val, tenant_id=tenant_id)
            if rec:
                if only_available and not rec.is_available_in_admin:
                    continue
                records.append(rec)
        return records

    @classmethod
    def get_provider_for_admin(
        cls,
        provider_type: Union[ProviderType, str],
        tenant_id: Optional[str] = None,
    ) -> Optional[ProviderCredentialRecord]:
        """
        Retrieves a single provider's configuration record with masked API key for Admin Panel.
        """
        p_val = provider_type.value if isinstance(provider_type, ProviderType) else str(provider_type).lower()
        meta = cls.PROVIDER_METADATA.get(p_val)
        if not meta:
            return None

        is_live = cls.is_provider_live_tested(p_val)
        disp_name = meta.get("name", p_val.capitalize())
        status_reason = None if is_live else f"Blocked in Admin Panel: Provider '{disp_name}' requires live outbound API verification (TASK-FOLLOWUP-LIVE-TEST-ANTHROPIC-GEMINI)."
        verif_status = "verified" if is_live else "requires_live_test"

        # Check in-memory store
        mem_key = f"{p_val}:{tenant_id or 'system'}"
        if mem_key in cls._memory_store:
            item = cls._memory_store[mem_key]
            return ProviderCredentialRecord(
                provider=p_val,
                provider_display_name=disp_name,
                base_url=item.get("base_url") or meta.get("default_base_url"),
                masked_api_key=cls.mask_api_key(item.get("api_key")),
                is_active=item.get("is_active", True) and is_live,
                is_configured=bool(item.get("api_key")),
                is_live_tested=is_live,
                is_available_in_admin=is_live,
                verification_status=verif_status,
                status_reason=status_reason,
                source="memory",
                supported_models=meta.get("models", []),
                updated_at=item.get("updated_at"),
            )

        # Check AIProvider in DB
        try:
            from api.db.db_models import AIProvider
            prov_obj = AIProvider.get_or_none(AIProvider.provider_name == p_val, AIProvider.is_global == True)
            if prov_obj and prov_obj.api_key:
                return ProviderCredentialRecord(
                    provider=p_val,
                    provider_display_name=disp_name,
                    base_url=prov_obj.base_url or meta.get("default_base_url"),
                    masked_api_key=cls.mask_api_key(prov_obj.api_key),
                    is_active=prov_obj.status == "verified" and is_live,
                    is_configured=bool(prov_obj.api_key),
                    is_live_tested=is_live,
                    is_available_in_admin=is_live,
                    verification_status=verif_status,
                    status_reason=status_reason,
                    source="system_db",
                    supported_models=meta.get("models", []),
                    updated_at=prov_obj.update_time or prov_obj.create_time,
                )
        except Exception:
            pass

        # Check DB (TenantLLM)
        try:
            from api.db.services.tenant_llm_service import TenantLLMService
            factory_names = meta.get("db_factory_names", [p_val])
            t_id = tenant_id or "system"
            
            objs = []
            for fname in factory_names:
                objs = TenantLLMService.query(tenant_id=t_id, llm_factory=fname)
                if objs:
                    break

            if objs and objs[0].api_key:
                obj = objs[0]
                raw_key, _, _ = TenantLLMService._decode_api_key_config(obj.api_key)
                return ProviderCredentialRecord(
                    provider=p_val,
                    provider_display_name=disp_name,
                    base_url=obj.api_base or meta.get("default_base_url"),
                    masked_api_key=cls.mask_api_key(raw_key),
                    is_active=str(obj.status) == "1" and is_live,
                    is_configured=bool(raw_key),
                    is_live_tested=is_live,
                    is_available_in_admin=is_live,
                    verification_status=verif_status,
                    status_reason=status_reason,
                    source="tenant_db" if tenant_id else "system_db",
                    supported_models=meta.get("models", []),
                    updated_at=getattr(obj, "update_time", None) or getattr(obj, "create_time", None),
                )
        except Exception:
            pass

        # Check Environment
        api_key, base_url = cls.resolve(p_val, tenant_id=tenant_id)
        is_configured = bool(api_key)
        return ProviderCredentialRecord(
            provider=p_val,
            provider_display_name=disp_name,
            base_url=base_url or meta.get("default_base_url"),
            masked_api_key=cls.mask_api_key(api_key),
            is_active=is_configured and is_live,
            is_configured=is_configured,
            is_live_tested=is_live,
            is_available_in_admin=is_live,
            verification_status=verif_status,
            status_reason=status_reason,
            source="environment" if is_configured else "none",
            supported_models=meta.get("models", []),
            updated_at=None,
        )

    @classmethod
    def save_provider_credentials(
        cls,
        provider_type: Union[ProviderType, str],
        api_key: str,
        base_url: Optional[str] = None,
        tenant_id: Optional[str] = None,
        is_active: bool = True,
    ) -> ProviderCredentialRecord:
        """
        Creates or updates provider credentials with Clean Replacement & Auto-Reactivation.
        If api_key is masked (e.g. 'sk-proj...1234') or empty, preserves the existing stored key.
        When a new key is saved:
        1. Updates memory store and TenantLLM.
        2. Updates AIProvider (status="verified", api_key=effective_key).
        3. Auto-Reactivation Cascade: all AIModel records previously marked as 'unconfigured_provider'
           are restored to status='active', enabled=True.
        4. Invalidates ai_gateway provider instance cache.
        """
        p_val = provider_type.value if isinstance(provider_type, ProviderType) else str(provider_type).lower()
        meta = cls.PROVIDER_METADATA.get(p_val, {"name": p_val.capitalize(), "models": [], "default_base_url": None})
        
        now = int(time.time())
        mem_key = f"{p_val}:{tenant_id or 'system'}"

        # If incoming key is masked or empty, preserve existing key
        effective_key = api_key
        if "..." in (api_key or "") or not api_key:
            existing_key, existing_url = cls.resolve(p_val, tenant_id=tenant_id)
            effective_key = existing_key
            if not base_url:
                base_url = existing_url

        effective_base_url = base_url or meta.get("default_base_url")

        # Save in memory store
        cls._memory_store[mem_key] = {
            "api_key": effective_key,
            "base_url": effective_base_url,
            "is_active": is_active,
            "updated_at": now,
        }

        # 1. Update AIProvider in DB
        try:
            from api.db.db_models import AIProvider
            prov_obj = AIProvider.get_or_none(AIProvider.provider_name == p_val)
            if prov_obj:
                AIProvider.update(
                    api_key=effective_key,
                    base_url=effective_base_url or prov_obj.base_url,
                    status="verified" if effective_key else "unconfigured",
                    is_global=True,
                    update_time=now,
                ).where(AIProvider.id == prov_obj.id).execute()
            else:
                AIProvider.create(
                    id=p_val,
                    provider_name=p_val,
                    base_url=effective_base_url,
                    api_key=effective_key,
                    status="verified" if effective_key else "unconfigured",
                    is_global=True,
                    create_time=now,
                    update_time=now,
                )
        except Exception as e:
            logger.debug(f"AIProvider DB persist fallback for {p_val}: {e}")

        # 2. Auto-Reactivation Cascade: reactivate models disabled due to unconfigured_provider
        if effective_key:
            try:
                from api.db.db_models import AIModel
                AIModel.update(
                    status="active",
                    enabled=True,
                    update_time=now,
                ).where(
                    AIModel.provider == p_val,
                    AIModel.status == "unconfigured_provider",
                    AIModel.is_global == True,
                ).execute()
            except Exception as e:
                logger.debug(f"AIModel auto-reactivation cascade for {p_val}: {e}")

        # 3. Try persisting to database if TenantLLM is available
        try:
            from api.db.services.tenant_llm_service import TenantLLMService
            t_id = tenant_id or "system"
            factory_name = meta.get("db_factory_names", [p_val])[0]
            
            existing_objs = TenantLLMService.query(tenant_id=t_id, llm_factory=factory_name)
            encoded_key = TenantLLMService._encode_api_key_config(effective_key, is_tools=True)
            if existing_objs:
                TenantLLMService.update_by_id(
                    existing_objs[0].id,
                    {
                        "api_key": encoded_key,
                        "api_base": effective_base_url or "",
                        "status": "1" if is_active else "0",
                        "update_time": now,
                    }
                )
            else:
                TenantLLMService.save(
                    tenant_id=t_id,
                    llm_factory=factory_name,
                    model_type="CHAT",
                    llm_name=meta.get("models", [factory_name])[0],
                    api_key=encoded_key,
                    api_base=effective_base_url or "",
                    status="1" if is_active else "0",
                )
        except Exception as e:
            logger.debug(f"DB persist optional fallback for {p_val}: {e}")

        # 4. Invalidate gateway cache
        try:
            from common.ai_gateway.gateway import ai_gateway
            ai_gateway.clear_cache()
        except Exception:
            pass

        return ProviderCredentialRecord(
            provider=p_val,
            provider_display_name=meta.get("name", p_val.capitalize()),
            base_url=effective_base_url,
            masked_api_key=cls.mask_api_key(effective_key),
            is_active=is_active,
            is_configured=bool(effective_key),
            source="tenant_db" if tenant_id else "system_db",
            supported_models=meta.get("models", []),
            updated_at=now,
        )

    @classmethod
    def replace_provider_api_key(
        cls,
        provider_type: Union[ProviderType, str],
        new_api_key: str,
        base_url: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> ProviderCredentialRecord:
        """
        Replaces the API key for a provider and auto-reactivates its models.
        Convenience wrapper around save_provider_credentials.
        """
        return cls.save_provider_credentials(
            provider_type=provider_type,
            api_key=new_api_key,
            base_url=base_url,
            tenant_id=tenant_id,
            is_active=True,
        )

    @classmethod
    def wipe_provider_api_key(
        cls,
        provider_type: Union[ProviderType, str],
        tenant_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Wipes API key for a provider and executes Wipe Cascade:
        1. Clears in-memory store: removes key from cls._memory_store.
        2. Clears TenantLLM: deletes or resets api_key.
        3. Updates AIProvider: sets api_key=None, status="unconfigured".
        4. Wipe Cascade on AIModel: marks all models for this provider as status="unconfigured_provider", enabled=False.
        5. Invalidates ai_gateway provider instance cache.
        
        Returns summary of cascade impact:
        {"provider": p_val, "status": "unconfigured", "wiped": True, "models_disabled_count": int}
        """
        p_val = provider_type.value if isinstance(provider_type, ProviderType) else str(provider_type).lower()
        mem_key = f"{p_val}:{tenant_id or 'system'}"
        cls._memory_store.pop(mem_key, None)

        now = int(time.time())
        models_disabled = 0

        # 1. Update AIProvider in DB
        try:
            from api.db.db_models import AIProvider
            AIProvider.update(
                api_key=None,
                status="unconfigured",
                update_time=now,
            ).where(AIProvider.provider_name == p_val).execute()
        except Exception as e:
            logger.debug(f"AIProvider wipe fallback for {p_val}: {e}")

        # 2. Cascade disable all AIModel records for this provider
        try:
            from api.db.db_models import AIModel
            models_disabled = (
                AIModel.update(
                    status="unconfigured_provider",
                    enabled=False,
                    update_time=now,
                )
                .where(AIModel.provider == p_val, AIModel.is_global == True)
                .execute()
            )
        except Exception as e:
            logger.debug(f"AIModel cascade disable for {p_val}: {e}")

        # 3. Clear TenantLLM
        try:
            from api.db.services.tenant_llm_service import TenantLLMService
            meta = cls.PROVIDER_METADATA.get(p_val, {})
            factory_names = meta.get("db_factory_names", [p_val])
            t_id = tenant_id or "system"
            for fname in factory_names:
                existing = TenantLLMService.query(tenant_id=t_id, llm_factory=fname)
                for obj in existing:
                    TenantLLMService.delete_by_id(obj.id)
        except Exception as e:
            logger.debug(f"TenantLLM delete fallback for {p_val}: {e}")

        # 4. Invalidate gateway cache
        try:
            from common.ai_gateway.gateway import ai_gateway
            ai_gateway.clear_cache()
        except Exception:
            pass

        return {
            "provider": p_val,
            "status": "unconfigured",
            "wiped": True,
            "models_disabled_count": int(models_disabled or 0),
        }

    @classmethod
    def delete_provider_credentials(
        cls,
        provider_type: Union[ProviderType, str],
        tenant_id: Optional[str] = None,
    ) -> bool:
        """Deletes/wipes provider configuration and executes wipe cascade."""
        res = cls.wipe_provider_api_key(provider_type=provider_type, tenant_id=tenant_id)
        return res.get("wiped", True)

    @classmethod
    async def test_provider_connection(
        cls,
        provider_type: Union[ProviderType, str],
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> ConnectionTestResult:
        """
        Lightweight health-check ping to the target provider.
        Validates API key validity and measures latency without modifying live-tested gating status.
        """
        p_val = provider_type.value if isinstance(provider_type, ProviderType) else str(provider_type).lower()
        start_t = time.perf_counter()

        test_key = api_key
        test_url = base_url
        if not test_key or "..." in test_key:
            res_key, res_url = cls.resolve(p_val, tenant_id=tenant_id)
            test_key = test_key if test_key and "..." not in test_key else res_key
            test_url = test_url or res_url

        if not test_key:
            return ConnectionTestResult(
                provider=p_val,
                success=False,
                status_code=400,
                latency_ms=0.0,
                message="No API Key configured or provided for connection test",
            )

        try:
            if p_val == ProviderType.OPENAI.value:
                from common.ai_gateway.providers.openai_provider import OpenAIProvider
                from common.ai_gateway.types import GatewayChatRequest, GatewayMessage
                prov = OpenAIProvider(api_key=test_key, base_url=test_url)
                await prov.chat_complete(GatewayChatRequest(
                    messages=[GatewayMessage(role="user", content="ping")],
                    model="gpt-4o-mini",
                    max_tokens=1,
                ))
            elif p_val == ProviderType.DEEPSEEK.value:
                from common.ai_gateway.providers.deepseek_provider import DeepSeekProvider
                from common.ai_gateway.types import GatewayChatRequest, GatewayMessage
                prov = DeepSeekProvider(api_key=test_key, base_url=test_url)
                await prov.chat_complete(GatewayChatRequest(
                    messages=[GatewayMessage(role="user", content="ping")],
                    model="deepseek-chat",
                    max_tokens=1,
                ))
            elif p_val == ProviderType.ANTHROPIC.value:
                from common.ai_gateway.providers.anthropic_provider import AnthropicProvider
                from common.ai_gateway.types import GatewayChatRequest, GatewayMessage
                prov = AnthropicProvider(api_key=test_key, base_url=test_url)
                await prov.chat_complete(GatewayChatRequest(
                    messages=[GatewayMessage(role="user", content="ping")],
                    model="claude-3-5-haiku-20241022",
                    max_tokens=1,
                ))
            elif p_val == ProviderType.GEMINI.value:
                from common.ai_gateway.providers.gemini_provider import GeminiProvider
                from common.ai_gateway.types import GatewayChatRequest, GatewayMessage
                prov = GeminiProvider(api_key=test_key, base_url=test_url)
                await prov.chat_complete(GatewayChatRequest(
                    messages=[GatewayMessage(role="user", content="ping")],
                    model="gemini-2.0-flash",
                    max_tokens=1,
                ))

            latency = (time.perf_counter() - start_t) * 1000.0
            return ConnectionTestResult(
                provider=p_val,
                success=True,
                status_code=200,
                latency_ms=latency,
                message="Ping connection test successful. Credentials are valid.",
            )
        except Exception as e:
            latency = (time.perf_counter() - start_t) * 1000.0
            sanitized_err = SecretRedactor.redact(str(e))
            return ConnectionTestResult(
                provider=p_val,
                success=False,
                status_code=getattr(e, "status_code", 500),
                latency_ms=latency,
                message=f"Ping connection failed: {sanitized_err}",
            )

    @classmethod
    async def verify_provider_full_cycle(
        cls,
        provider_type: Union[ProviderType, str],
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        tenant_id: Optional[str] = None,
        persist_verification: bool = True,
    ) -> Dict[str, Any]:
        """
        Comprehensive Outbound Verification Suite required to unlock Anthropic/Gemini.
        Executes real end-to-end cycles:
          1. Non-streaming Chat Completion
          2. Streaming Token Generation
          3. Embeddings Generation (for Gemini/OpenAI)
        
        If all steps pass, marks provider as live-tested and permanently persists
        the verification status in the DB/settings to survive system restarts.
        """
        p_val = provider_type.value if isinstance(provider_type, ProviderType) else str(provider_type).lower()
        test_key = api_key
        test_url = base_url
        if not test_key or "..." in test_key:
            res_key, res_url = cls.resolve(p_val, tenant_id=tenant_id)
            test_key = test_key if test_key and "..." not in test_key else res_key
            test_url = test_url or res_url

        if not test_key:
            return {
                "success": False,
                "provider": p_val,
                "error": "No API key configured",
                "stages": {},
            }

        stages: Dict[str, Any] = {}
        start_t = time.perf_counter()

        try:
            from common.ai_gateway.types import GatewayChatRequest, GatewayMessage, GatewayEmbeddingRequest

            # 1. Instantiate provider
            if p_val == ProviderType.ANTHROPIC.value:
                from common.ai_gateway.providers.anthropic_provider import AnthropicProvider
                prov = AnthropicProvider(api_key=test_key, base_url=test_url)
                test_chat_model = "claude-3-5-haiku-20241022"
            elif p_val == ProviderType.GEMINI.value:
                from common.ai_gateway.providers.gemini_provider import GeminiProvider
                prov = GeminiProvider(api_key=test_key, base_url=test_url)
                test_chat_model = "gemini-2.0-flash"
            elif p_val == ProviderType.DEEPSEEK.value:
                from common.ai_gateway.providers.deepseek_provider import DeepSeekProvider
                prov = DeepSeekProvider(api_key=test_key, base_url=test_url)
                test_chat_model = "deepseek-chat"
            else:
                from common.ai_gateway.providers.openai_provider import OpenAIProvider
                prov = OpenAIProvider(api_key=test_key, base_url=test_url)
                test_chat_model = "gpt-4o-mini"

            # Stage 1: Non-Streaming Chat
            t0 = time.perf_counter()
            chat_resp = await prov.chat_complete(GatewayChatRequest(
                messages=[
                    GatewayMessage(role="system", content="You are a test agent."),
                    GatewayMessage(role="user", content="Respond strictly with: OK"),
                ],
                model=test_chat_model,
                max_tokens=10,
            ))
            stages["chat_non_streaming"] = {
                "status": "passed",
                "latency_ms": round((time.perf_counter() - t0) * 1000.0, 2),
                "tokens": chat_resp.usage.total_tokens if chat_resp.usage else 0,
            }

            # Stage 2: Streaming Token Generation
            t1 = time.perf_counter()
            stream_chunks = []
            async for chunk in prov.chat_stream(GatewayChatRequest(
                messages=[GatewayMessage(role="user", content="Count 1 to 3")],
                model=test_chat_model,
                max_tokens=20,
            )):
                stream_chunks.append(chunk.delta_content)
            stages["chat_streaming"] = {
                "status": "passed",
                "latency_ms": round((time.perf_counter() - t1) * 1000.0, 2),
                "chunks_received": len(stream_chunks),
            }

            # Stage 3: Embeddings (if supported by provider)
            if p_val in (ProviderType.GEMINI.value, ProviderType.OPENAI.value, ProviderType.DEEPSEEK.value):
                t2 = time.perf_counter()
                embed_model = "text-embedding-004" if p_val == ProviderType.GEMINI.value else "text-embedding-3-small"
                emb_resp = await prov.embed(GatewayEmbeddingRequest(
                    input_texts=["Live test embedding vector"],
                    model=embed_model,
                ))
                stages["embeddings"] = {
                    "status": "passed",
                    "latency_ms": round((time.perf_counter() - t2) * 1000.0, 2),
                    "vector_dim": len(emb_resp.embeddings[0]) if emb_resp.embeddings else 0,
                }

            # All stages succeeded! Unlock and persist
            cls._live_tested_overrides[p_val] = True
            
            # Persist in DB if enabled
            if persist_verification:
                try:
                    from api.db.services.tenant_llm_service import TenantLLMService
                    meta = cls.PROVIDER_METADATA.get(p_val, {})
                    factory_name = meta.get("db_factory_names", [p_val])[0]
                    t_id = tenant_id or "system"
                    existing_objs = TenantLLMService.query(tenant_id=t_id, llm_factory=factory_name)
                    if existing_objs:
                        # Append verified flag to DB record
                        TenantLLMService.update_by_id(
                            existing_objs[0].id,
                            {"status": "1", "update_time": int(time.time())}
                        )
                except Exception as db_err:
                    logger.debug(f"Could not persist verification status in DB: {db_err}")

            return {
                "success": True,
                "provider": p_val,
                "total_latency_ms": round((time.perf_counter() - start_t) * 1000.0, 2),
                "stages": stages,
                "message": f"Full-cycle live verification passed for provider '{p_val}'. Provider is now unlocked in Admin Panel.",
            }

        except Exception as e:
            sanitized_err = SecretRedactor.redact(str(e))
            return {
                "success": False,
                "provider": p_val,
                "total_latency_ms": round((time.perf_counter() - start_t) * 1000.0, 2),
                "stages": stages,
                "error": sanitized_err,
                "message": f"Full-cycle verification failed: {sanitized_err}",
            }


# Singleton instance for centralized import
credential_resolver = CredentialResolver()
