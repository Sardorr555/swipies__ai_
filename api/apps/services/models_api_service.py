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

from api.db.joint_services.tenant_model_service import ensure_mineru_from_env, ensure_paddleocr_from_env, ensure_opendataloader_from_env
from common.constants import ActiveStatusEnum, LLMType
from common.settings import FACTORY_LLM_INFOS
from api.db.services.tenant_model_provider_service import TenantModelProviderService
from api.db.services.tenant_model_instance_service import TenantModelInstanceService
from api.db.services.tenant_model_service import TenantModelService
from api.db.services.user_service import TenantService

# Mapping from model_type string to Tenant model field name
MODEL_TYPE_TO_FIELD = {
    "chat": "llm_id",
    "embedding": "embd_id",
    "rerank": "rerank_id",
    "asr": "asr_id",
    "vision": "img2txt_id",
    "tts": "tts_id",
    "ocr": "ocr_id",
}

MODEL_TAG_TO_TYPE = {
    "chat": "chat",
    "embedding": "embedding",
    "rerank": "rerank",
    "asr": "speech2text",
    "vision": "image2text",
    "tts": "tts",
    "ocr": "ocr",
}


def normalize_model_type(m_type: str) -> str:
    if not m_type:
        return "chat"
    t = str(m_type).lower()
    mapping = {
        "chat": "chat",
        "embedding": "embedding",
        "rerank": "rerank",
        "vision": "image2text",
        "image2text": "image2text",
        "asr": "speech2text",
        "speech2text": "speech2text",
        "tts": "tts",
        "ocr": "ocr",
    }
    return mapping.get(t, t)


def _to_int(v, default=500):
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def _factory_model_types(llm: dict) -> list[str]:
    model_type = llm.get("model_type")
    if isinstance(model_type, list):
        return model_type
    return [model_type] if model_type else []


def parse_and_resolve_model_components(model_id: str, model_type: str = "chat") -> tuple[str, str, str]:
    """
    Given any format of model ID:
      - 'deepseek-chat@default@DeepSeek' (3-part composite)
      - 'deepseek-chat@DeepSeek' (2-part composite)
      - 'deepseek/deepseek-chat' (provider/model_name)
      - 'openai/text-embedding-3-small_embedding' (provider/model_name_type)
      - 'deepseek-chat' (bare model name)
    Resolves and returns: (pure_model_name, instance_name, provider_name)
    """
    if not model_id:
        return "", "", ""

    str_val = str(model_id).strip()
    if not str_val:
        return "", "", ""

    # Case 1: has '@'
    if "@" in str_val:
        parts = str_val.split("@")
        if len(parts) == 3:
            return parts[0], parts[1] or "default", parts[2]
        elif len(parts) == 2:
            return parts[0], "default", parts[1]
        elif len(parts) == 1:
            str_val = parts[0]

    # Case 2: has '/'
    if "/" in str_val:
        try:
            from api.db.db_models import AIModel
            aim = AIModel.get_or_none(AIModel.id == str_val)
            if aim:
                return aim.model_name, "default", aim.provider
        except Exception:
            pass

        prov_part, model_part = str_val.split("/", 1)
        for suffix in ["_embedding", "_chat", "_rerank", "_image2text", "_speech2text", "_tts"]:
            if model_part.endswith(suffix):
                model_part = model_part[:-len(suffix)]
                break

        provider_name = prov_part
        for fac in (FACTORY_LLM_INFOS or []):
            if fac.get("name", "").lower() == prov_part.lower():
                provider_name = fac["name"]
                break

        return model_part, "default", provider_name

    # Case 3: bare model name
    try:
        from api.db.db_models import AIModel
        aim = AIModel.get_or_none(AIModel.model_name == str_val)
        if aim:
            return aim.model_name, "default", aim.provider
        aim_id = AIModel.get_or_none(AIModel.id == str_val)
        if aim_id:
            return aim_id.model_name, "default", aim_id.provider
    except Exception:
        pass

    for fac in (FACTORY_LLM_INFOS or []):
        for llm in fac.get("llm", []):
            if llm.get("llm_name", "").lower() == str_val.lower():
                return llm.get("llm_name"), "default", fac["name"]

    return str_val, "default", ""


def _get_model_info(tenant_id: str, default_model: str, model_type: str):
    """
    Parse any composite or provider/model string and validate that the provider,
    instance, and model exist (either as a tenant custom model or a global platform model).

    Returns a dict with model info or None on error.
    """
    if not default_model:
        return None

    model_name, instance_name, provider_name = parse_and_resolve_model_components(default_model, model_type)
    if not model_name:
        return None
    instance_name = instance_name or "default"

    model_type = MODEL_TAG_TO_TYPE.get(model_type, model_type)
    # Special case: OCR with infiniflow@default@deepdoc is always enabled
    if model_type == "ocr" and (provider_name.lower() == "infiniflow" or not provider_name) and model_name == "deepdoc":
        return {
            "model_provider": "infiniflow",
            "model_instance": "default",
            "model_name": "deepdoc",
            "model_type": model_type,
            "enable": True,
        }

    # Special case: TEI Builtin embedding model
    compose_profiles = os.getenv("COMPOSE_PROFILES", "")
    tei_model = os.getenv("TEI_MODEL", "")
    if (model_type == "embedding"
        and "tei-" in compose_profiles
        and tei_model
        and model_name == tei_model
        and (not provider_name or provider_name == "Builtin")):
        return {
            "model_provider": "Builtin",
            "model_instance": "default",
            "model_name": model_name,
            "model_type": model_type,
            "enable": True,
        }

    # 1. Check Global Platform Models (AIModel & AIProvider)
    try:
        from api.db.services.ai_policy_service import AIModelService
        from api.db.db_models import AIProvider
        active_provs = {
            p.provider_name.lower(): p.provider_name
            for p in AIProvider.select().where(
                AIProvider.is_global == True,
                AIProvider.status.in_(["active", "verified"]),
                AIProvider.api_key.is_null(False),
                AIProvider.api_key != "",
            )
        }
        global_models = AIModelService.query(enabled=True)
        for gm in global_models:
            gm_prov = gm.provider or ""
            prov_match = (
                not provider_name
                or gm_prov.lower() == provider_name.lower()
                or (provider_name.lower() in active_provs and gm_prov.lower() == provider_name.lower())
            )
            name_match = (
                gm.model_name.lower() == model_name.lower()
                or gm.id.lower() == default_model.lower()
            )
            if prov_match and name_match:
                can_use = bool(gm.api_key and gm.api_key.strip()) or (gm_prov.lower() in active_provs)
                if can_use:
                    return {
                        "model_provider": gm_prov,
                        "model_instance": instance_name,
                        "model_name": gm.model_name,
                        "model_type": normalize_model_type(gm.model_type or model_type),
                        "enable": True,
                    }
    except Exception as g_err:
        logging.warning(f"_get_model_info global models check exception: {g_err}")

    # 2. Check if the provider exists for the tenant
    provider_obj = TenantModelProviderService.get_by_tenant_id_and_provider_name(tenant_id, provider_name)
    if provider_obj:
        instance_obj = TenantModelInstanceService.get_by_provider_id_and_instance_name(provider_obj.id, instance_name)
        if instance_obj:
            model_entity = TenantModelService.get_by_provider_id_and_instance_id_and_model_type_and_model_name(
                provider_obj.id, instance_obj.id, model_type, model_name
            )
            enable = model_entity is None or model_entity.status == ActiveStatusEnum.ACTIVE.value
            if enable:
                return {
                    "model_provider": provider_name,
                    "model_instance": instance_name,
                    "model_name": model_name,
                    "model_type": model_type,
                    "enable": True,
                }

    # 3. Check FACTORY_LLM_INFOS
    factory_info = [f for f in (FACTORY_LLM_INFOS or []) if f["name"].lower() == provider_name.lower()]
    if factory_info:
        llms = factory_info[0].get("llm", [])
        target_llm = [llm for llm in llms if llm["llm_name"].lower() == model_name.lower()]
        if target_llm:
            return {
                "model_provider": factory_info[0]["name"],
                "model_instance": instance_name,
                "model_name": target_llm[0]["llm_name"],
                "model_type": model_type,
                "enable": True,
            }

    # 4. Fallback: if provider_name and model_name exist
    if provider_name and model_name:
        return {
            "model_provider": provider_name,
            "model_instance": instance_name,
            "model_name": model_name,
            "model_type": model_type,
            "enable": True,
        }

    return None


def _check_model_available(tenant_id: str, provider_name: str, instance_name: str, model_name: str, model_type: str):
    """
    Validate that a model is available for the tenant:
    - Provider exists for the tenant
    - Instance exists under the provider
    - Model is in the LLM factory info for the provider
    - Model type matches
    - Model is not disabled in TenantModel table

    Returns (success, error_message).
    """
    if provider_name == "infiniflow" and instance_name == "default" and model_name == "deepdoc":
        return True, None

    if model_type == "ocr" and provider_name == "infiniflow" and instance_name == "default" and model_name == "deepdoc":
        return True, None

    compose_profiles = os.getenv("COMPOSE_PROFILES", "")
    is_tei_builtin_embedding = (
            model_type == LLMType.EMBEDDING.value
            and "tei-" in compose_profiles
            and model_name == os.getenv("TEI_MODEL", "")
            and (provider_name == "Builtin" or not provider_name)
    )
    if is_tei_builtin_embedding:
        return True, None

    # Check provider
    provider_obj = TenantModelProviderService.get_by_tenant_id_and_provider_name(tenant_id, provider_name)
    if not provider_obj:
        try:
            from api.db.services.ai_policy_service import AIModelService
            global_models = AIModelService.query(enabled=True)
            for gm in global_models:
                if gm.provider == provider_name and gm.model_name == model_name:
                    return True, None
        except Exception:
            pass
        return False, f"Provider '{provider_name}' not found"

    # Check instance
    instance_obj = TenantModelInstanceService.get_by_provider_id_and_instance_name(provider_obj.id, instance_name)
    if not instance_obj:
        return False, f"Instance '{instance_name}' not found for provider '{provider_name}'"

    # Check model schema
    factory_info = [f for f in (FACTORY_LLM_INFOS or []) if f["name"] == provider_name]
    if not factory_info:
        return False, f"Provider '{provider_name}' not found in factory info"
    model_type = MODEL_TAG_TO_TYPE.get(model_type, model_type)
    # Check if model is disabled
    model_entity = TenantModelService.get_by_provider_id_and_instance_id_and_model_type_and_model_name(
        provider_obj.id, instance_obj.id, model_type, model_name
    )
    if model_entity:
        if model_entity.status != ActiveStatusEnum.ACTIVE.value:
            return False, f"Model '{model_name}' isn't available"
        return True, None

    llms = factory_info[0].get("llm", [])
    target_llm = [llm for llm in llms if llm["llm_name"] == model_name]
    if not target_llm and not model_entity:
        return False, f"Model '{model_name}' not found for provider '{provider_name}'"

    if target_llm:
        if model_type not in _factory_model_types(target_llm[0]):
            return False, f"Model '{model_name}' isn't a {model_type} model"

    return True, None


def list_tenant_default_models(tenant_id: str):
    """
    List all default models for a tenant.

    For each model type (chat, embedding, rerank, asr, vision, tts, ocr):
    1. Reads the configured model string from the Tenant record.
    2. If missing or invalid, falls back to the Global Instance defaults set by Admin.
    3. Resolves and returns the canonical model info, and synchronizes the canonical
       format back to the Tenant record so all user components (chat, datasets, setting) work seamlessly.

    :param tenant_id: tenant ID
    :return: (success, result_or_error_message)
    """
    e, tenant = TenantService.get_by_id(tenant_id)
    if not e:
        return False, "Tenant not found"

    # Retrieve Admin Global Instance defaults
    g_stats = {}
    try:
        from api.db.services.global_instance_service import GlobalInstanceService
        g_stats = GlobalInstanceService.get_instance_stats() or {}
    except Exception as ge:
        logging.warning(f"list_tenant_default_models get_instance_stats error: {ge}")

    # Priority mapping for Admin defaults per model capability
    GLOBAL_TYPE_KEY_MAP = {
        "chat": ["default_chat_model", "default_free_model_id"],
        "embedding": ["default_embd_id"],
        "rerank": ["default_rerank_id"],
        "vision": ["default_image2text_model", "default_img2txt_id"],
        "asr": ["default_asr_model", "default_asr_id"],
        "tts": ["default_tts_model", "default_tts_id"],
    }

    models = []
    tenant_updates = {}

    for model_type, field_name in MODEL_TYPE_TO_FIELD.items():
        default_model = getattr(tenant, field_name, None)
        model_info = None

        # 1. Try resolving tenant's current field value
        if default_model:
            model_info = _get_model_info(tenant_id, default_model, model_type)

        # 2. If tenant has no valid model, fallback to Admin Global Instance default
        if not model_info:
            cand_keys = GLOBAL_TYPE_KEY_MAP.get(model_type, [])
            global_def = ""
            for ck in cand_keys:
                if g_stats.get(ck):
                    global_def = g_stats.get(ck)
                    break

            if global_def:
                model_info = _get_model_info(tenant_id, global_def, model_type)

        # 3. Fallback to any active verified platform model of this type
        if not model_info:
            try:
                from api.db.services.ai_policy_service import AIModelService
                global_models = AIModelService.query(enabled=True)
                for gm in global_models:
                    if normalize_model_type(gm.model_type) == model_type:
                        cand_str = f"{gm.model_name}@default@{gm.provider}"
                        model_info = _get_model_info(tenant_id, cand_str, model_type)
                        if model_info:
                            break
            except Exception:
                pass

        if model_info:
            models.append(model_info)
            # Synchronize canonical format string back to tenant record
            canonical_str = f"{model_info['model_name']}@{model_info['model_instance']}@{model_info['model_provider']}"
            if default_model != canonical_str:
                tenant_updates[field_name] = canonical_str

    if tenant_updates:
        try:
            TenantService.update_by_id(tenant_id, tenant_updates)
        except Exception as upd_err:
            logging.warning(f"list_tenant_default_models sync tenant warning: {upd_err}")

    return True, {"models": models}


def set_tenant_default_models(tenant_id: str, model_provider: str, model_instance: str, model_name: str, model_type: str):
    """
    Set or clear a tenant default model.

    If model_provider, model_instance, and model_name are all provided,
    validates the model and sets it as the default.
    If all three are empty, clears the default for the given model type.

    :param tenant_id: tenant ID
    :param model_provider: provider name
    :param model_instance: instance name
    :param model_name: model name
    :param model_type: model type (chat, embedding, rerank, asr, vision, tts, ocr)
    :return: (success, result_or_error_message)
    """
    field_name = MODEL_TYPE_TO_FIELD.get(model_type)
    if not field_name:
        return False, f"model type '{model_type}' is invalid"

    e, tenant = TenantService.get_by_id(tenant_id)
    if not e:
        return False, "Tenant not found"

    if not model_provider and not model_instance and not model_name:
        # Clear the default model
        default_model = ""
    elif model_provider and model_instance and model_name:
        # Validate and set the default model
        success, msg = _check_model_available(tenant_id, model_provider, model_instance, model_name, model_type)
        if not success:
            return False, msg
        default_model = f"{model_name}@{model_instance}@{model_provider}"
    else:
        return False, "model_provider, model_instance and model_name must be specified together"

    TenantService.update_by_id(tenant_id, {field_name: default_model})
    return True, "success"


def _is_instance_connected_with_key(factory_name: str, instance_record) -> bool:
    LOCAL_PROVIDERS = {"builtin", "ollama", "localai", "xinference", "vllm", "mineru", "paddleocr", "opendataloader", "somark"}
    if factory_name.lower() in LOCAL_PROVIDERS:
        return True

    if not instance_record or not instance_record.api_key:
        return False

    raw_key = instance_record.api_key.strip()
    if not raw_key or raw_key == "{}" or raw_key == '{"api_key": ""}':
        return False

    try:
        parsed = json.loads(raw_key)
        if isinstance(parsed, dict):
            key = parsed.get("api_key", "").strip()
            if not key and len(parsed.keys()) <= 1:
                return False
            return True
    except Exception:
        pass

    return len(raw_key) > 0


def list_tenant_added_models(tenant_id: str, model_type_filter: str=None):
    """
    List all added models for a tenant.

    :param tenant_id: tenant ID
    :param model_type_filter: model type filter (chat, embedding, rerank, asr, vision, tts, ocr)
    :return: (success, result_or_error_message)
    """
    e, tenant = TenantService.get_by_id(tenant_id)
    if not e:
        return False, "Tenant not found"

    ensure_mineru_from_env(tenant_id)
    ensure_paddleocr_from_env(tenant_id)
    ensure_opendataloader_from_env(tenant_id)

    if model_type_filter:
        model_type_filter = model_type_filter.lower()

    providers = TenantModelProviderService.get_by_tenant_id(tenant_id)
    provider_ids = [provider.id for provider in providers] if providers else []
    instances = TenantModelInstanceService.get_by_provider_ids(provider_ids) if provider_ids else []
    
    provider_instance_map: dict = {}
    provider_info_map = {provider.id: provider for provider in (providers or [])}
    for provider_instance_record in instances:
        provider_name = provider_info_map[provider_instance_record.provider_id].provider_name if provider_info_map.get(provider_instance_record.provider_id) else ""
        if not _is_instance_connected_with_key(provider_name, provider_instance_record):
            continue
        if provider_instance_map.get(provider_name):
            provider_instance_map[provider_name].append(provider_instance_record)
        else:
            provider_instance_map[provider_name] = [provider_instance_record]

    model_records = TenantModelService.get_models_by_provider_ids_and_instance_ids(provider_ids, list({instance.id for instance in instances})) if (provider_ids and instances) else []
    target_type_records = [record for record in model_records if record.model_type == model_type_filter] if model_type_filter else model_records
    model_record_map = {}
    for model in target_type_records:
        instance_model_key = f"{model.provider_id}@{model.instance_id}@{model.model_name}"
        if model_record_map.get(instance_model_key):
            model_record_map[instance_model_key].append(model)
        else:
            model_record_map[instance_model_key] = [model]

    added_models = []
    model_key_in_factory = []
    provider_names = [provider.provider_name for provider in (providers or [])]
    factory_rank_mapping = {factory["name"]: -_to_int(factory.get("rank", "500")) for factory in FACTORY_LLM_INFOS}
    for factory in FACTORY_LLM_INFOS:
        if factory["name"] not in provider_names:
            continue
        factory_instances = provider_instance_map.get(factory["name"])
        if not factory_instances:
            continue
        for llm in factory["llm"]:
            factory_model_types = _factory_model_types(llm)
            if model_type_filter and model_type_filter not in factory_model_types:
                continue

            for factory_instance in factory_instances:
                model_record_key = f"{factory_instance.provider_id}@{factory_instance.id}@{llm['llm_name']}"
                model_key_in_factory.append(model_record_key)
                manual_modified_models = model_record_map.get(model_record_key, [])
                active_model_types = [manual_model.model_type for manual_model in manual_modified_models if manual_model.status == ActiveStatusEnum.ACTIVE.value]
                inactive_model_types = [manual_model.model_type for manual_model in manual_modified_models if manual_model.status == ActiveStatusEnum.INACTIVE.value]
                unsupport_model_types = [manual_model.model_type for manual_model in manual_modified_models if manual_model.status == ActiveStatusEnum.UNSUPPORTED.value]
                model_types = list(set(factory_model_types + active_model_types) - set(inactive_model_types) - set(unsupport_model_types))
                if not model_types:
                    continue

                added_models.append({
                    "model_type": [normalize_model_type(mt) for mt in model_types],
                    "name": llm["llm_name"],
                    "provider_id": factory_instance.provider_id,
                    "provider_name": provider_info_map[factory_instance.provider_id].provider_name if provider_info_map.get(factory_instance.provider_id) else "",
                    "instance_id": factory_instance.id,
                    "instance_name": factory_instance.instance_name
                })

    manual_added_model_record_keys = list(set(model_record_map.keys()) - set(model_key_in_factory))
    if manual_added_model_record_keys:
        instance_info_map = {instance.id: instance for instance in instances}
        for model_record_key in manual_added_model_record_keys:
            model_records = model_record_map.get(model_record_key, [])
            if not model_records:
                continue
            provider_id, instance_id, model_name = model_record_key.split("@")
            model_types = [model.model_type for model in model_records if model.status == ActiveStatusEnum.ACTIVE.value]
            if not model_types:
                continue

            added_models.append({
                "model_type": [normalize_model_type(mt) for mt in model_types],
                "name": model_name,
                "provider_id": provider_id,
                "provider_name": provider_info_map[provider_id].provider_name if provider_info_map.get(provider_id) else "",
                "instance_id": instance_id,
                "instance_name": instance_info_map[instance_id].instance_name if instance_info_map.get(instance_id) else ""
            })

    # Add TEI Builtin embedding model if configured
    compose_profiles = os.getenv("COMPOSE_PROFILES", "")
    tei_model = os.getenv("TEI_MODEL", "")
    if "tei-" in compose_profiles and tei_model:
        if not model_type_filter or model_type_filter == "embedding":
            tei_already_added = any(
                m["provider_name"] == "Builtin" and m["name"] == tei_model
                for m in added_models
            )
            if not tei_already_added:
                added_models.append({
                    "model_type": ["embedding"],
                    "name": tei_model,
                    "provider_id": "",
                    "provider_name": "Builtin",
                    "instance_id": "",
                    "instance_name": "default",
                })

    # Include Admin-registered global AI models where provider has connected API key or model has api_key
    try:
        from api.db.services.ai_policy_service import AIModelService
        from api.db.db_models import AIProvider
        active_provs = {
            p.provider_name.lower(): p.provider_name
            for p in AIProvider.select().where(
                AIProvider.is_global == True,
                AIProvider.status.in_(["active", "verified"]),
                AIProvider.api_key.is_null(False),
                AIProvider.api_key != "",
            )
        }
        global_models = AIModelService.query(enabled=True)
        existing_model_keys = {(m["provider_name"].lower(), m["name"].lower()) for m in added_models}
        for gm in global_models:
            gm_prov = gm.provider or ""
            gm_prov_lower = gm_prov.lower()
            if (gm_prov_lower, gm.model_name.lower()) not in existing_model_keys:
                has_key = bool(gm.api_key and gm.api_key.strip()) or (gm_prov_lower in active_provs) or (gm_prov in provider_instance_map)
                if not has_key:
                    continue
                gm_type = normalize_model_type(gm.model_type)
                if model_type_filter and normalize_model_type(model_type_filter) != gm_type:
                    continue
                added_models.append({
                    "model_type": [gm_type],
                    "name": gm.model_name,
                    "provider_id": "",
                    "provider_name": gm_prov,
                    "instance_id": "",
                    "instance_name": "default"
                })
                existing_model_keys.add((gm_prov_lower, gm.model_name.lower()))
    except Exception as e:
        logging.warning(f"list_tenant_added_models global models fallback exception: {e}")

    added_models.sort(key=lambda x: (factory_rank_mapping.get(x["provider_name"], 0), x["provider_name"], x["instance_name"]))

    return True, added_models

