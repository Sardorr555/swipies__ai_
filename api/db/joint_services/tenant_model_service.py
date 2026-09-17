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
import logging
import os
import enum
import json
from common import settings
from common.constants import (
    ActiveStatusEnum,
    LLMType,
    ModelTypeBinary,
    MINERU_DEFAULT_CONFIG,
    MINERU_ENV_KEYS,
    MISTRAL_OCR_DEFAULT_CONFIG,
    MISTRAL_OCR_ENV_KEYS,
    OPENDATALOADER_DEFAULT_CONFIG,
    OPENDATALOADER_ENV_KEYS,
    PADDLEOCR_DEFAULT_CONFIG,
    PADDLEOCR_ENV_KEYS,
    SOMARK_DEFAULT_CONFIG,
    SOMARK_ENV_KEYS,
)
from api.db.services.tenant_llm_service import TenantService
from api.db.services.tenant_model_provider_service import TenantModelProviderService
from api.db.services.tenant_model_instance_service import TenantModelInstanceService
from api.db.services.tenant_model_service import TenantModelService
from api.utils.model_utils import calculate_model_type, get_model_type_human

logger = logging.getLogger(__name__)


def _factory_model_types(llm: dict) -> list[str]:
    model_type = llm.get("model_type")
    if isinstance(model_type, list):
        return model_type
    return [model_type] if model_type else []


def _lookup_factory_llm_info(provider_name: str, pure_model_name: str, extra_fields: dict) -> dict | None:
    region = extra_fields.get("region", "default")
    if region == "intl" and provider_name.lower() == "siliconflow":
        target_factory_name = "siliconflow_intl"
    else:
        target_factory_name = provider_name
    fac_list = [f for f in settings.FACTORY_LLM_INFOS if f["name"] == target_factory_name]
    if not fac_list:
        return None
    llm_list = [llm for llm in fac_list[0]["llm"] if llm["llm_name"] == pure_model_name]
    return llm_list[0] if llm_list else None


def _decode_api_key_config(raw_api_key: str) -> tuple[str, bool | None, str | None]:
    if not raw_api_key:
        return raw_api_key, None, None

    try:
        from api.utils.key_crypto import decrypt_api_key
        decrypted = decrypt_api_key(raw_api_key)
    except Exception:
        decrypted = raw_api_key

    try:
        parsed = json.loads(decrypted)
    except Exception:
        return decrypted, None, None

    if not isinstance(parsed, dict):
        return decrypted, None, None

    is_tools = bool(parsed["is_tools"]) if "is_tools" in parsed else None
    if set(parsed.keys()) <= {"api_key", "is_tools"}:
        return parsed.get("api_key", ""), is_tools, None

    return parsed.get("api_key", decrypted), is_tools, decrypted


def get_first_provider_model_name(tenant_id: str, provider_name: str, model_type: str | enum.Enum) -> str | None:
    model_type_bin = calculate_model_type(model_type)
    provider_obj = TenantModelProviderService.get_by_tenant_id_and_provider_name(tenant_id, provider_name)
    if not provider_obj:
        return None

    for instance_obj in TenantModelInstanceService.get_all_by_provider_id(provider_obj.id):
        if instance_obj.status != ActiveStatusEnum.ACTIVE.value:
            continue
        for model_obj in TenantModelService.get_models_by_instance_id(instance_obj.id):
            if model_obj.model_type & model_type_bin and model_obj.status == ActiveStatusEnum.ACTIVE.value:
                return f"{model_obj.model_name}@{instance_obj.instance_name}@{provider_name}"
    return None


def _collect_env_config(env_keys: list[str], default_config: dict) -> dict | None:
    config = dict(default_config)
    found = False
    for key in env_keys:
        value = os.environ.get(key)
        if value:
            found = True
            config[key] = value
    return config if found else None


def _ensure_ocr_provider_from_env(tenant_id: str, provider_name: str, model_name: str, config: dict | None) -> str | None:
    if not config:
        return None

    provider_obj = TenantModelProviderService.get_by_tenant_id_and_provider_name(tenant_id, provider_name, fallback_admin=False)
    if not provider_obj:
        TenantModelProviderService.insert(tenant_id=tenant_id, provider_name=provider_name)
        provider_obj = TenantModelProviderService.get_by_tenant_id_and_provider_name(tenant_id, provider_name, fallback_admin=False)

    api_key = json.dumps(config)
    instance_obj = TenantModelInstanceService.get_by_provider_id_and_api_key(provider_obj.id, api_key)
    if not instance_obj:
        instance_obj = TenantModelInstanceService.create_instance(
            provider_id=provider_obj.id,
            instance_name=model_name,
            api_key=api_key,
            extra="{}",
        )

    model_obj = TenantModelService.get_by_provider_id_and_instance_id_and_model_type_and_model_name(
        provider_obj.id,
        instance_obj.id,
        LLMType.OCR.value,
        model_name,
    )
    if not model_obj:
        TenantModelService.insert(
            model_name=model_name,
            provider_id=provider_obj.id,
            instance_id=instance_obj.id,
            model_type=ModelTypeBinary.OCR.value,
            extra=json.dumps({"max_tokens": 0}),
        )

    return f"{model_name}@{instance_obj.instance_name}@{provider_name}"


def ensure_mineru_from_env(tenant_id: str) -> str | None:
    return _ensure_ocr_provider_from_env(
        tenant_id,
        "MinerU",
        "mineru-from-env",
        _collect_env_config(MINERU_ENV_KEYS, MINERU_DEFAULT_CONFIG),
    )


def ensure_paddleocr_from_env(tenant_id: str) -> str | None:
    return _ensure_ocr_provider_from_env(
        tenant_id,
        "PaddleOCR",
        "paddleocr-from-env",
        _collect_env_config(PADDLEOCR_ENV_KEYS, PADDLEOCR_DEFAULT_CONFIG),
    )


def get_tenant_default_model_by_type(tenant_id: str, model_type: str | enum.Enum):
    exist, tenant = TenantService.get_by_id(tenant_id)
    model_type_val = model_type if isinstance(model_type, str) else model_type.value
    model_id: str | None = None
    model_name: str = ""
    if exist and tenant:
        match model_type_val:
            case LLMType.EMBEDDING.value:
                model_id = getattr(tenant, "tenant_embd_id", None)
                model_name = tenant.embd_id
            case LLMType.SPEECH2TEXT.value | LLMType.ASR.value:
                model_id = getattr(tenant, "tenant_asr_id", None)
                model_name = tenant.asr_id
            case LLMType.IMAGE2TEXT.value | LLMType.VISION.value:
                model_id = getattr(tenant, "tenant_img2txt_id", None)
                model_name = tenant.img2txt_id
            case LLMType.CHAT.value:
                model_id = getattr(tenant, "tenant_llm_id", None)
                model_name = tenant.llm_id
            case LLMType.RERANK.value:
                model_id = getattr(tenant, "tenant_rerank_id", None)
                model_name = tenant.rerank_id
            case LLMType.TTS.value:
                model_id = getattr(tenant, "tenant_tts_id", None)
                model_name = tenant.tts_id
            case LLMType.OCR.value:
                model_name = getattr(tenant, "ocr_id", "")

    # If tenant has no model_name or if it's empty, get from GlobalInstanceService
    if not model_name:
        try:
            from api.db.services.global_instance_service import GlobalInstanceService
            g_stats = GlobalInstanceService.get_instance_stats()
            match model_type_val:
                case LLMType.CHAT.value:
                    model_name = g_stats.get("default_chat_model") or g_stats.get("default_free_model_id")
                case LLMType.EMBEDDING.value:
                    model_name = g_stats.get("default_embd_id")
                case LLMType.RERANK.value:
                    model_name = g_stats.get("default_rerank_id")
                case LLMType.IMAGE2TEXT.value | LLMType.VISION.value:
                    model_name = g_stats.get("default_image2text_model")
                case LLMType.SPEECH2TEXT.value | LLMType.ASR.value:
                    model_name = g_stats.get("default_asr_model")
                case LLMType.TTS.value:
                    model_name = g_stats.get("default_tts_model")
        except Exception as ge:
            logger.warning(f"GlobalInstanceService fallback error: {ge}")

    if not model_name:
        # Check first available verified platform model
        try:
            from api.db.services.ai_policy_service import AIModelService
            p_models = AIModelService.get_platform_models()
            matched = [
                m for m in p_models
                if m.get("model_type", "").upper() == model_type_val.upper()
                or (model_type_val == LLMType.CHAT.value and m.get("model_type", "").upper() in ["CHAT", "IMAGE2TEXT"])
            ]
            if matched:
                model_name = matched[0].get("id") or matched[0].get("model_name")
        except Exception as pe:
            logger.warning(f"AIModelService platform models fallback error: {pe}")

    if not model_name:
        raise Exception(f"No active or configured {model_type} model is available. Please configure an API key in Admin -> AI Management.")

    # Prefer resolving by tenant_model.id when available
    if model_id:
        try:
            return get_model_config_by_id(tenant_id, model_type, model_id)
        except LookupError:
            logger.warning("tenant_model id=%s not found, falling back to model_name lookup for %s", model_id, model_name)

    try:
        return resolve_model_config(tenant_id, model_type, model_name)
    except Exception as exc:
        # If the specific model failed to resolve, try resolving any active verified platform model of this type
        try:
            from api.db.services.ai_policy_service import AIModelService
            p_models = AIModelService.get_platform_models()
            matched = [
                m for m in p_models
                if m.get("model_type", "").upper() == model_type_val.upper()
                or (model_type_val == LLMType.CHAT.value and m.get("model_type", "").upper() in ["CHAT", "IMAGE2TEXT"])
            ]
            if matched:
                alt_model = matched[0].get("id") or matched[0].get("model_name")
                logger.warning(f"Model '{model_name}' failed to resolve ({exc}). Falling back to active verified model '{alt_model}'.")
                return resolve_model_config(tenant_id, model_type, alt_model)
        except Exception:
            pass
        raise exc


def split_model_name(model_name: str):
    # Parse model_name: {model_name} or {model_name}@{factory_name} or {model_name}@{instance_name}@{factory_name}
    # Or {provider}/{model_name}
    if not model_name:
        return "", "", ""

    if "/" in model_name and "@" not in model_name:
        parts = model_name.split("/", 1)
        return parts[1], "default", parts[0]

    parts = model_name.rsplit("@", 2)
    n = len(parts)
    if n == 3:
        pure_model_name, instance_name, provider_name = parts
    elif n == 2:
        pure_model_name, provider_name = parts
        instance_name = "default"
    else:
        pure_model_name = parts[0]
        provider_name = ""
        instance_name = ""
    return pure_model_name, instance_name, provider_name


def _resolve_instance_for_model(provider_obj, instance_name: str, model_name: str):
    instance_obj = TenantModelInstanceService.get_by_provider_id_and_instance_name(provider_obj.id, instance_name)
    if instance_obj:
        return instance_obj
    if instance_name != "default":
        raise LookupError(f"Instance {instance_name} not found for model {model_name}.")

    active_instances = [inst for inst in TenantModelInstanceService.get_all_by_provider_id(provider_obj.id) if inst.status == ActiveStatusEnum.ACTIVE.value]
    if len(active_instances) == 1:
        logger.warning(
            "Model instance fallback applied for legacy default instance name",
            extra={
                "provider_name": provider_obj.provider_name,
                "requested_instance_name": instance_name,
                "resolved_instance_name": active_instances[0].instance_name,
                "model_name": model_name,
            },
        )
        return active_instances[0]

    raise LookupError(f"Instance {instance_name} not found for model {model_name}.")

def resolve_model_config(tenant_id, model_type: str | enum.Enum, model_ref: str):
    try:
        return get_model_config_by_id(tenant_id, model_type, model_ref)
    except LookupError:
        return get_model_config_from_provider_instance(tenant_id, model_type, model_ref)
def get_model_config_from_provider_instance(tenant_id, model_type: str | enum.Enum, model_name: str):
    pure_model_name, instance_name, provider_name = split_model_name(model_name)
    model_type_val = model_type if isinstance(model_type, str) else model_type.value
    # Builtin embedding model
    compose_profiles = os.getenv("COMPOSE_PROFILES", "")
    is_tei_builtin_embedding = (
        model_type_val == LLMType.EMBEDDING.value and "tei-" in compose_profiles and pure_model_name == os.getenv("TEI_MODEL", "") and (provider_name == "Builtin" or not provider_name)
    )
    if is_tei_builtin_embedding:
        # configured local embedding model
        embedding_cfg = settings.EMBEDDING_CFG
        return {
            "llm_factory": "Builtin",
            "api_key": embedding_cfg["api_key"],
            "llm_name": pure_model_name,
            "api_base": embedding_cfg["base_url"],
            "model_type": LLMType.EMBEDDING.value,
        }

    # 1. Try finding via Provider Instance architecture
    try:
        if not provider_name:
            from api.db.services.tenant_llm_service import TenantLLMService
            _, fid = TenantLLMService.split_model_name_and_factory(pure_model_name)
            if fid:
                provider_name = fid

        if provider_name:
            provider_obj = TenantModelProviderService.get_by_tenant_id_and_provider_name(tenant_id, provider_name)
            if provider_obj:
                instance_obj = _resolve_instance_for_model(provider_obj, instance_name, model_name)
                if instance_obj:
                    model_obj = TenantModelService.get_by_provider_id_and_instance_id_and_model_type_and_model_name(provider_obj.id, instance_obj.id, model_type_val, pure_model_name)
                    api_key, is_tool, api_key_payload = _decode_api_key_config(instance_obj.api_key)
                    extra_fields = json.loads(instance_obj.extra) if instance_obj.extra else {}

                    if model_obj:
                        if model_obj.status == ActiveStatusEnum.INACTIVE.value:
                            raise LookupError(f"Model {model_name} is disabled.")
                        if model_obj.status == ActiveStatusEnum.UNSUPPORTED.value:
                            raise LookupError(f"Model {model_name} cannot be used as {model_type_val} model.")

                        model_extra = json.loads(model_obj.extra) if model_obj.extra else {}
                        llm_info = _lookup_factory_llm_info(provider_obj.provider_name, pure_model_name, extra_fields)
                        max_tokens = model_extra.get("max_tokens", (llm_info or {}).get("max_tokens", 8192))
                        model_config = {
                            "llm_factory": provider_obj.provider_name,
                            "api_key": api_key,
                            "llm_name": model_obj.model_name,
                            "api_base": extra_fields.get("base_url", ""),
                            "model_type": model_obj.model_type,
                            "is_tools": model_extra.get("is_tools", is_tool),
                            "max_tokens": max_tokens,
                        }
                        if provider_name.lower() == "somark":
                            model_config["extra"] = model_extra
                        if api_key_payload is not None:
                            model_config["api_key_payload"] = api_key_payload
                        return model_config
                    else:
                        region = extra_fields.get("region", "default")
                        target_factory_name = "siliconflow_intl" if (region == "intl" and provider_name.lower() == "siliconflow") else provider_name
                        fac_list = [f for f in settings.FACTORY_LLM_INFOS if f["name"] == target_factory_name]
                        llm_info = None
                        if fac_list:
                            llm_list = [llm for llm in fac_list[0]["llm"] if llm["llm_name"] == pure_model_name]
                            if llm_list:
                                llm_info = llm_list[0]
                        model_config = {
                            "llm_factory": provider_obj.provider_name,
                            "api_key": api_key,
                            "llm_name": pure_model_name,
                            "api_base": extra_fields.get("base_url", ""),
                            "model_type": model_type_val,
                            "is_tools": (llm_info.get("is_tools") if llm_info else is_tool),
                            "max_tokens": (llm_info.get("max_tokens") if llm_info else 8192) or 8192,
                        }
                        if api_key_payload is not None:
                            model_config["api_key_payload"] = api_key_payload
                        return model_config
    except Exception as e:
        logger.warning(f"get_model_config_from_provider_instance provider instance lookup exception: {e}")

    # 2. Fallback to TenantLLMService & AIModelService
    from api.db.services.tenant_llm_service import TenantLLMService
    try:
        target_name = f"{pure_model_name}@{provider_name}" if (pure_model_name and provider_name) else (pure_model_name or model_name)
        fallback_cfg = TenantLLMService.get_model_config(tenant_id, model_type_val, target_name)
        if fallback_cfg:
            return fallback_cfg
    except Exception as fallback_e:
        logger.warning(f"TenantLLMService get_model_config fallback exception: {fallback_e}")

    # 3. Fallback to AIModel and AIProvider (Single Global Instance storage)
    try:
        from api.db.db_models import AIModel, AIProvider
        from api.utils.key_crypto import decrypt_api_key

        candidate_ids = [model_name, pure_model_name]
        if provider_name:
            candidate_ids.extend([f"{provider_name.lower()}/{pure_model_name}", f"{provider_name}/{pure_model_name}"])

        aim = None
        for cid in candidate_ids:
            aim = AIModel.get_or_none(AIModel.id == cid)
            if aim:
                break
        if not aim:
            aim = AIModel.get_or_none(AIModel.model_name == pure_model_name)

        if aim and aim.api_key and len(aim.api_key.strip()) > 0:
            return {
                "llm_factory": aim.provider,
                "api_key": decrypt_api_key(aim.api_key),
                "llm_name": aim.model_name,
                "api_base": aim.base_url or "",
                "model_type": aim.model_type,
                "is_tools": True,
                "max_tokens": aim.max_tokens or 8192,
            }

        # Check AIProvider directly
        aip = None
        if provider_name:
            for cand in AIProvider.select().where(
                AIProvider.is_global == True,
                (AIProvider.status.in_(["active", "verified"]) | (AIProvider.api_key.is_null(False) & (AIProvider.api_key != "")))
            ):
                if cand.provider_name.lower() == provider_name.lower():
                    aip = cand
                    break
        if aip and aip.api_key and len(aip.api_key.strip()) > 0:
            return {
                "llm_factory": aip.provider_name,
                "api_key": decrypt_api_key(aip.api_key),
                "llm_name": pure_model_name or model_name,
                "api_base": aip.base_url or "",
                "model_type": model_type_val,
                "is_tools": True,
                "max_tokens": 8192,
            }
    except Exception as aip_e:
        logger.warning(f"AIModel / AIProvider direct lookup error: {aip_e}")

    # 4. Safe Auto-Fallback for embedding models
    if model_type_val == LLMType.EMBEDDING.value:
        try:
            any_embd = TenantLLMService.query(tenant_id=tenant_id, model_type=LLMType.EMBEDDING.value)
            if not any_embd:
                admin_id = TenantModelProviderService._get_admin_tenant_id()
                if admin_id and admin_id != tenant_id:
                    any_embd = TenantLLMService.query(tenant_id=admin_id, model_type=LLMType.EMBEDDING.value)
            if any_embd and any_embd[0].api_key:
                return {
                    "llm_factory": any_embd[0].llm_factory,
                    "api_key": any_embd[0].api_key,
                    "llm_name": any_embd[0].llm_name,
                    "api_base": any_embd[0].api_base,
                    "model_type": LLMType.EMBEDDING.value,
                    "is_tools": False,
                    "max_tokens": any_embd[0].max_tokens or 8192,
                }
        except Exception as embd_e:
            logger.warning(f"Embedding model query fallback exception: {embd_e}")

        logger.warning(f"No configured API key found for requested embedding model '{model_name}'. Falling back to default embedding configuration.")
        embedding_cfg = getattr(settings, "EMBEDDING_CFG", {})
        return {
            "llm_factory": "BAAI",
            "api_key": getattr(embedding_cfg, "api_key", "") if isinstance(embedding_cfg, object) and not isinstance(embedding_cfg, dict) else (embedding_cfg.get("api_key", "") if isinstance(embedding_cfg, dict) else ""),
            "llm_name": pure_model_name or "bge-small-en-v1.5",
            "api_base": getattr(embedding_cfg, "base_url", "") if isinstance(embedding_cfg, object) and not isinstance(embedding_cfg, dict) else (embedding_cfg.get("base_url", "") if isinstance(embedding_cfg, dict) else ""),
            "model_type": LLMType.EMBEDDING.value,
            "is_tools": False,
            "max_tokens": 512,
        }

    # 5. Ultimate Fallback to ANY active platform model for this type
    try:
        from api.db.services.ai_policy_service import AIModelService
        from api.utils.key_crypto import decrypt_api_key
        p_models = AIModelService.get_platform_models()
        matched = [
            m for m in p_models
            if m.get("model_type", "").upper() == model_type_val.upper()
            or (model_type_val == LLMType.CHAT.value and m.get("model_type", "").upper() in ["CHAT", "IMAGE2TEXT"])
        ]
        if matched:
            selected = matched[0]
            # Fetch raw model for key decryption
            from api.db.db_models import AIModel
            raw_m = AIModel.get_or_none(AIModel.id == selected["id"])
            if raw_m and raw_m.api_key:
                logger.warning(f"Requested model '{model_name}' has no active API key. Auto-falling back to active platform model '{raw_m.model_name}'.")
                return {
                    "llm_factory": raw_m.provider,
                    "api_key": decrypt_api_key(raw_m.api_key),
                    "llm_name": raw_m.model_name,
                    "api_base": raw_m.base_url or "",
                    "model_type": raw_m.model_type,
                    "is_tools": True,
                    "max_tokens": raw_m.max_tokens or 8192,
                }
    except Exception as ultimate_e:
        logger.warning(f"Ultimate active platform model fallback error: {ultimate_e}")

    raise LookupError(f"Provider {provider_name or 'unknown'} not found or not configured for model {model_name}.")


def get_model_config_by_id(tenant_id: str, model_type: str | enum.Enum, model_id: str):
    """Get model config from tenant_model by its id (CharField PK)."""
    model_type_val = model_type if isinstance(model_type, str) else model_type.value
    model_type_bin = calculate_model_type(model_type_val)
    exist, model_obj = TenantModelService.get_by_id(model_id)
    if not exist:
        raise LookupError(f"TenantModel id={model_id} not found.")
    if model_obj.status == ActiveStatusEnum.INACTIVE.value:
        raise LookupError(f"TenantModel id={model_id} is disabled.")
    if model_obj.status == ActiveStatusEnum.UNSUPPORTED.value:
        raise LookupError(f"TenantModel id={model_id} cannot be used as {model_type_val} model.")
    if not (model_obj.model_type & model_type_bin):
        raise LookupError(f"TenantModel id={model_id} cannot be used as {model_type_val} model.")

    ok, provider_obj = TenantModelProviderService.get_by_id(model_obj.provider_id)
    if not ok:
        raise LookupError(f"Provider id={model_obj.provider_id} not found for model id={model_id}.")

    # Validate that tenant_id owns the provider or is a joined tenant of the provider's owner.
    if tenant_id != provider_obj.tenant_id:
        joined_tenants = TenantService.get_joined_tenants_by_user_id(tenant_id)
        joined_tenant_ids = [t["tenant_id"] for t in joined_tenants]
        if provider_obj.tenant_id not in joined_tenant_ids:
            raise LookupError(f"Tenant {tenant_id} has no access to provider owned by tenant {provider_obj.tenant_id}.")

    ok, instance_obj = TenantModelInstanceService.get_by_id(model_obj.instance_id)
    if not ok:
        raise LookupError(f"Instance id={model_obj.instance_id} not found for model id={model_id}.")

    api_key, is_tool, api_key_payload = _decode_api_key_config(instance_obj.api_key)
    extra_fields = json.loads(instance_obj.extra) if instance_obj.extra else {}
    model_extra = json.loads(model_obj.extra) if model_obj.extra else {}

    model_config = {
        "llm_factory": provider_obj.provider_name,
        "api_key": api_key,
        "llm_name": model_obj.model_name,
        "api_base": extra_fields.get("base_url", ""),
        "model_type": model_type_val,
        "is_tools": model_extra.get("is_tools", is_tool),
        "max_tokens": model_extra.get("max_tokens") or 8192,
    }
    if provider_obj.provider_name.lower() == "somark":
        model_config["extra"] = model_extra

    if api_key_payload is not None:
        model_config["api_key_payload"] = api_key_payload

    return model_config


def resolve_model_id(tenant_id: str, model_type: str | enum.Enum, model_name: str) -> str | None:
    """Given a tenant_id, model_type and model_name (e.g. 'model@instance@provider'),
    look up the corresponding tenant_model.id. Returns None if not found."""
    pure_model_name, instance_name, provider_name = split_model_name(model_name)
    model_type_val = model_type if isinstance(model_type, str) else model_type.value

    # Builtin TEI embedding — no tenant_model row exists
    compose_profiles = os.getenv("COMPOSE_PROFILES", "")
    is_tei_builtin_embedding = (
        model_type_val == LLMType.EMBEDDING.value and "tei-" in compose_profiles and pure_model_name == os.getenv("TEI_MODEL", "") and (provider_name == "Builtin" or not provider_name)
    )
    if is_tei_builtin_embedding:
        return None

    if not provider_name:
        raise LookupError(f"Provider name is required to resolve model id for {model_name}.")

    provider_obj = TenantModelProviderService.get_by_tenant_id_and_provider_name(tenant_id, provider_name)
    if not provider_obj:
        raise LookupError(f"Provider {provider_name} not found for model {model_name}.")

    instance_obj = _resolve_instance_for_model(provider_obj, instance_name, model_name)
    model_obj = TenantModelService.get_by_provider_id_and_instance_id_and_model_type_and_model_name(provider_obj.id, instance_obj.id, model_type_val, pure_model_name)
    if not model_obj:
        raise LookupError(f"Model {model_name} not found for type {model_type_val}.")
    return model_obj.id


# Mapping from model-name field → (LLMType, tenant_model id field)
_MODEL_NAME_TO_ID_FIELD_MAP: dict[str, tuple[str, str]] = {
    "llm_id": (LLMType.CHAT, "tenant_llm_id"),
    "embd_id": (LLMType.EMBEDDING, "tenant_embd_id"),
    "rerank_id": (LLMType.RERANK, "tenant_rerank_id"),
    "asr_id": (LLMType.ASR, "tenant_asr_id"),
    "img2txt_id": (LLMType.VISION, "tenant_img2txt_id"),
    "tts_id": (LLMType.TTS, "tenant_tts_id"),
}


def ensure_tenant_model_ids_for_params(tenant_id: str, params: dict) -> dict:
    """For each model-name field present in *params*, resolve the corresponding
    tenant_model id if the id field is not already present.

    Modifies *params* in-place (adds ``tenant_*_id`` keys) and returns it.
    Silently skips resolution when the model is not found in tenant_model
    (e.g. builtin TEI embedding).

    Typical usage at API entry points:

        req = await get_request_json()
        ensure_tenant_model_ids_for_params(current_user.id, req)
        # req now has tenant_llm_id / tenant_embd_id etc. filled in
    """
    for name_field, (model_type, id_field) in _MODEL_NAME_TO_ID_FIELD_MAP.items():
        if name_field in params and id_field not in params:
            try:
                model_name = params[name_field]
                if model_name:
                    model_id = resolve_model_id(tenant_id, model_type, model_name)
                    if model_id:
                        params[id_field] = model_id
            except LookupError as exc:
                logger.debug("Failed to resolve %s=%r to tenant_model.id: %s", name_field, params[name_field], exc)
    return params


def get_api_key(tenant_id: str, model_name: str):
    # Try direct model ID (UUID) lookup first
    exist, model_obj = TenantModelService.get_by_id(model_name)
    if exist:
        # Verify tenant ownership through the provider chain
        ok, provider_obj = TenantModelProviderService.get_by_id(model_obj.provider_id)
        if not ok:
            raise LookupError(f"Provider id={model_obj.provider_id} not found for model {model_name}.")
        if tenant_id != provider_obj.tenant_id:
            joined_tenants = TenantService.get_joined_tenants_by_user_id(tenant_id)
            joined_tenant_ids = [t["tenant_id"] for t in joined_tenants]
            if provider_obj.tenant_id not in joined_tenant_ids:
                raise LookupError(f"Tenant {tenant_id} has no access to provider owned by tenant {provider_obj.tenant_id}.")

        exist_inst, instance_obj = TenantModelInstanceService.get_by_id(model_obj.instance_id)
        if not exist_inst:
            logger.warning(
                "Direct-ID resolution: instance not found | tenant_id=%s model_id=%s instance_id=%s",
                tenant_id,
                model_name,
                model_obj.instance_id,
            )
            raise LookupError(f"Instance {model_obj.instance_id} not found for model {model_name}.")
        logger.debug(
            "Direct-ID resolution: resolved | tenant_id=%s model_id=%s instance_id=%s",
            tenant_id,
            model_name,
            model_obj.instance_id,
        )
        return instance_obj.api_key

    # Fall back to name-based resolution: model[@instance]@provider
    pure_model_name, instance_name, provider_name = split_model_name(model_name)

    if not provider_name:
        from api.db.services.tenant_llm_service import TenantLLMService
        _, fid = TenantLLMService.split_model_name_and_factory(pure_model_name)
        if fid:
            provider_name = fid

    if provider_name:
        provider_obj = TenantModelProviderService.get_by_tenant_id_and_provider_name(tenant_id, provider_name)
        if provider_obj:
            try:
                instance_obj = _resolve_instance_for_model(provider_obj, instance_name, model_name)
                if instance_obj and instance_obj.api_key:
                    return instance_obj.api_key
            except Exception:
                pass

    # Check AIProvider / AIModel
    try:
        from api.db.db_models import AIModel, AIProvider
        if provider_name:
            for p in AIProvider.select().where(AIProvider.is_global == True, AIProvider.status == "active"):
                if p.provider_name.lower() == provider_name.lower() and p.api_key:
                    return p.api_key
        aim = AIModel.get_or_none(AIModel.id == model_name) or AIModel.get_or_none(AIModel.model_name == pure_model_name)
        if aim and aim.api_key:
            return aim.api_key
    except Exception:
        pass

    raise LookupError(f"Provider {provider_name or 'unknown'} not found.")


def get_model_type_by_id(model_id: str):
    exist, model_obj = TenantModelService.get_by_id(model_id)
    if not exist:
        raise LookupError(f"TenantModel id={model_id} not found.")
    return get_model_type_human(model_obj.model_type)


def resolve_model_type(tenant_id: str, model_ref: str):
    try:
        return get_model_type_by_id(model_ref)
    except LookupError:
        return get_model_type_by_name(tenant_id, model_ref)


def get_model_type_by_name(tenant_id: str, model_name: str):
    if not model_name:
        return ["chat"]

    pure_model_name, instance_name, provider_name = split_model_name(model_name)
    # 1. Try finding via Provider Instance
    try:
        if not provider_name:
            from api.db.services.tenant_llm_service import TenantLLMService
            _, fid = TenantLLMService.split_model_name_and_factory(pure_model_name)
            if fid:
                provider_name = fid

        if provider_name:
            provider_obj = TenantModelProviderService.get_by_tenant_id_and_provider_name(tenant_id, provider_name)
            if provider_obj:
                instance_obj = TenantModelInstanceService.get_by_provider_id_and_instance_name(provider_obj.id, instance_name)
                if not instance_obj:
                    active_instances = [inst for inst in TenantModelInstanceService.get_all_by_provider_id(provider_obj.id) if inst.status == ActiveStatusEnum.ACTIVE.value]
                    if active_instances:
                        instance_obj = active_instances[0]
                if instance_obj:
                    model_obj = TenantModelService.get_by_provider_id_and_instance_id_and_model_name(provider_obj.id, instance_obj.id, pure_model_name)
                    if model_obj and model_obj.status != ActiveStatusEnum.UNSUPPORTED.value:
                        return get_model_type_human(model_obj.model_type)
    except Exception as e:
        logger.warning(f"get_model_type_by_name tenant instance lookup error: {e}")

    # 2. Check AIModel
    try:
        from api.db.db_models import AIModel
        candidate_ids = [model_name, pure_model_name, f"{provider_name.lower()}/{pure_model_name}" if provider_name else ""]
        for cid in candidate_ids:
            if cid:
                aim = AIModel.get_or_none(AIModel.id == cid)
                if aim and aim.model_type:
                    return [aim.model_type.lower()]
        aim = AIModel.get_or_none(AIModel.model_name == pure_model_name)
        if aim and aim.model_type:
            return [aim.model_type.lower()]
    except Exception as e:
        logger.warning(f"get_model_type_by_name AIModel lookup error: {e}")

    # 3. Check FACTORY_LLM_INFOS
    try:
        target_factory_name = provider_name
        fac_list = [f for f in settings.FACTORY_LLM_INFOS if f["name"].lower() == (target_factory_name or "").lower()]
        if fac_list:
            llm_list = [llm for llm in fac_list[0]["llm"] if llm["llm_name"] == pure_model_name]
            if llm_list:
                return _factory_model_types(llm_list[0])
        # Search all factories
        for f in settings.FACTORY_LLM_INFOS:
            for llm in f.get("llm", []):
                if llm.get("llm_name") == pure_model_name:
                    return _factory_model_types(llm)
    except Exception as e:
        logger.warning(f"get_model_type_by_name FACTORY_LLM_INFOS error: {e}")

    # Safe default to ["chat"]
    return ["chat"]


def delete_models_by_instance_ids(instance_ids: list[str]):
    return TenantModelService.delete_by_instance_ids(instance_ids)


def delete_instances_by_provider_ids(provider_ids: list[str]):
    return TenantModelInstanceService.delete_by_provider_ids(provider_ids)


def ensure_opendataloader_from_env(tenant_id: str) -> str | None:
    return _ensure_ocr_provider_from_env(
        tenant_id,
        "OpenDataLoader",
        "opendataloader-from-env",
        _collect_env_config(OPENDATALOADER_ENV_KEYS, OPENDATALOADER_DEFAULT_CONFIG),
    )


def ensure_somark_from_env(tenant_id: str) -> str | None:
    return _ensure_ocr_provider_from_env(
        tenant_id,
        "SoMark",
        "somark-from-env",
        _collect_env_config(SOMARK_ENV_KEYS, SOMARK_DEFAULT_CONFIG),
    )


def get_composite_model_name_by_id(model_id: str) -> str:
    """Convert a tenant_model.id to the composite model name string
    ``model_name@instance_name@provider_name``.
    Raises LookupError if the model, instance, or provider is not found.
    """
    exist, model_obj = TenantModelService.get_by_id(model_id)
    if not exist:
        raise LookupError(f"TenantModel id={model_id} not found.")

    ok, instance_obj = TenantModelInstanceService.get_by_id(model_obj.instance_id)
    if not ok:
        raise LookupError(f"Instance id={model_obj.instance_id} not found for model id={model_id}.")

    ok, provider_obj = TenantModelProviderService.get_by_id(model_obj.provider_id)
    if not ok:
        raise LookupError(f"Provider id={model_obj.provider_id} not found for model id={model_id}.")

    return f"{model_obj.model_name}@{instance_obj.instance_name}@{provider_obj.provider_name}"


def get_composite_model_name_by_ids(model_ids: list[str]) -> dict[str, str]:
    """Convert a list of tenant_model.id values to a dict mapping each id
    to its composite model name string ``model_name@instance_name@provider_name``.
    Model ids that cannot be resolved are silently skipped.
    """
    if not model_ids:
        return {}

    models = list(TenantModelService.get_by_ids(model_ids))
    if not models:
        return {}

    instance_ids = list({m.instance_id for m in models})
    provider_ids = list({m.provider_id for m in models})

    instances = list(TenantModelInstanceService.get_by_ids(instance_ids)) if instance_ids else []
    instance_map = {i.id: i for i in instances}

    providers = list(TenantModelProviderService.get_by_ids(provider_ids)) if provider_ids else []
    provider_map = {p.id: p for p in providers}

    result: dict[str, str] = {}
    for m in models:
        inst = instance_map.get(m.instance_id)
        prov = provider_map.get(m.provider_id)
        if not inst or not prov:
            continue
        result[m.id] = f"{m.model_name}@{inst.instance_name}@{prov.provider_name}"

    return result


def ensure_mistral_ocr_from_env(tenant_id: str) -> str | None:
    return _ensure_ocr_provider_from_env(
        tenant_id,
        "Mistral OCR",
        "mistral-ocr-latest",
        _collect_env_config(MISTRAL_OCR_ENV_KEYS, MISTRAL_OCR_DEFAULT_CONFIG),
    )
