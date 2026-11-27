"""Provider API catalog independent of tenant-installed models and credentials."""
import asyncio
import json

from api.db.db_models import DB, AIModel, AIProvider, SubscriptionAIPolicy
from common.time_utils import current_timestamp
from common.misc_utils import get_uuid


def model_capability(name, declared="CHAT"):
    """Prefer provider/catalog metadata; distinguish non-chat OpenAI capabilities."""
    kind = str(declared).upper()
    if kind != "CHAT":
        return {"VISION": "IMAGE2TEXT", "ASR": "SPEECH2TEXT"}.get(kind, kind)
    name = name.lower()
    if "embed" in name:
        return "EMBEDDING"
    if "rerank" in name:
        return "RERANK"
    if "tts" in name:
        return "TTS"
    if "transcrib" in name or "whisper" in name:
        return "SPEECH2TEXT"
    if "moderation" in name:
        return "MODERATION"
    if "realtime" in name or "gpt-live" in name:
        return "REALTIME"
    if "gpt-image" in name or "dall-e" in name or "chatgpt-image" in name:
        return "IMAGE_GENERATION"
    if "gpt-audio" in name:
        return "AUDIO"
    return kind


class PlatformModelCatalogService:
    @classmethod
    @DB.connection_context()
    def sync_provider(cls, provider, discovered):
        """Keep operator settings and existing grants; never install tenant models."""
        created = 0
        with DB.atomic():
            for item in discovered:
                name = item.get("model_name") or item.get("name")
                if not isinstance(name, str) or not name or len(name) > 128:
                    continue
                model_id = f"{provider.provider_name.lower()}/{name}"
                if len(model_id) > 128:
                    continue
                now = current_timestamp()
                model = AIModel.get_or_none(AIModel.id == model_id)
                # Do not overwrite custom models or a model belonging to another provider.
                if model and (not model.is_global or model.is_custom):
                    continue
                capability = model_capability(name, item.get("model_type", "CHAT"))
                if model:
                    extra = model.extra or {}
                    if isinstance(extra, str):
                        extra = json.loads(extra)
                    extra = {**extra, "catalog_source": "provider_api", "catalog_seen_at": now}
                    AIModel.update(extra=extra, model_type=capability, update_time=now).where(AIModel.id == model.id).execute()
                else:
                    AIModel.create(id=model_id, provider=provider.provider_name, model_name=name,
                        model_type=capability, base_url="", api_key="", enabled=True,
                        is_global=True, is_custom=False, status="active",
                        max_tokens=int(item.get("max_tokens") or 8192),
                        extra={"catalog_source": "provider_api", "catalog_seen_at": now},
                        create_time=now, update_time=now)
                    created += 1
                # No implicit grant to Free, Plus or Pro for newly discovered models.
                for plan in ("free", "plus", "pro"):
                    if not SubscriptionAIPolicy.select().where(
                        SubscriptionAIPolicy.plan_id == plan, SubscriptionAIPolicy.model_id == model_id
                    ).exists():
                        SubscriptionAIPolicy.create(id=get_uuid(), plan_id=plan, model_id=model_id, enabled=False)
        return created

    @classmethod
    async def refresh(cls, provider_name=None):
        from api.db.services.ai_provider_service import AIProviderService
        from api.utils.key_crypto import decrypt_api_key
        with DB.connection_context():
            providers = list(AIProvider.select().where(AIProvider.is_global == True,
                AIProvider.status.in_(["active", "verified"]), AIProvider.api_key.is_null(False), AIProvider.api_key != ""))
        if provider_name:
            providers = [p for p in providers if p.provider_name.lower() == provider_name.lower()]
        limit = asyncio.Semaphore(3)
        async def refresh_one(provider):
            async with limit:
                try:
                    ok, _, discovered = await AIProviderService.async_discover_live_provider_models(
                        provider.provider_name, decrypt_api_key(provider.api_key), provider.base_url or "")
                    if not ok:
                        return {"provider": provider.provider_name, "success": False, "count": 0}
                    created = cls.sync_provider(provider, discovered)
                    return {"provider": provider.provider_name, "success": True, "count": len(discovered), "created": created}
                except Exception:
                    # Provider exception strings can contain credential-bearing URLs.
                    return {"provider": provider.provider_name, "success": False, "count": 0}
        return list(await asyncio.gather(*(refresh_one(p) for p in providers)))
