"""Small durable event append on the existing Telegram transport; no message text."""
import asyncio
import hashlib
import hmac
import logging
from datetime import datetime, timezone

LOG = logging.getLogger(__name__)

def utc(value=None):
    value=value or datetime.now(timezone.utc)
    return value.astimezone(timezone.utc).replace(tzinfo=None) if value.tzinfo else value

def digest(*parts):
    return hashlib.sha256(':'.join(str(p) for p in parts).encode()).hexdigest()

def actor_key(bot_id, telegram_id, secret):
    # Bot-scoped pseudonyms; no names, usernames or raw Telegram user/chat IDs persist.
    return hmac.new(secret.encode(),f'telegram-analytics:{bot_id}:{telegram_id}'.encode(),hashlib.sha256).hexdigest() if telegram_id is not None else None

def bot_metadata(bot):
    if isinstance(bot,dict): return bot
    return {'id':getattr(bot,'id',None),'username':getattr(bot,'username',''),
            'first_name':getattr(bot,'first_name','')}

async def capture_update(channel_id, metadata, update):
    """Await only an append, never aggregation. Failure is isolated from bot replies."""
    try:
        from api.db.services.telegram_analytics_ingest import enqueue_update
        await asyncio.to_thread(enqueue_update,channel_id,bot_metadata(metadata),update)
    except Exception:
        try:
            from api.channels.telegram.analytics_spool import put
            await asyncio.to_thread(put,'update',channel_id,bot_metadata(metadata),update)
        except Exception:
            LOG.error('Telegram analytics durable stores unavailable for channel=%s',channel_id)

async def capture_reply(channel_id, metadata, message):
    try:
        from api.db.services.telegram_analytics_ingest import enqueue_reply
        await asyncio.to_thread(enqueue_reply,channel_id,bot_metadata(metadata),message)
    except Exception:
        try:
            from api.channels.telegram.analytics_spool import put
            await asyncio.to_thread(put,'reply',channel_id,bot_metadata(metadata),message)
        except Exception:
            LOG.error('Telegram analytics durable stores unavailable for channel=%s',channel_id)

async def worker(stop_event):
    from api.db.services.telegram_analytics_ingest import drain
    while not stop_event.is_set():
        try:
            count=await asyncio.to_thread(drain,100)
        except Exception:
            count=0
        try:
            from api.channels.telegram.analytics_spool import drain as drain_spool
            await asyncio.to_thread(drain_spool,100)
        except Exception:
            pass
        await asyncio.sleep(0.05 if count==100 else 1)
