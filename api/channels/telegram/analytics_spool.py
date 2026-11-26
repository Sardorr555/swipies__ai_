"""Existing Redis queue as a protected fallback while the SQL outbox is unavailable."""
import json
from datetime import datetime
from types import SimpleNamespace as NS
from api.channels.telegram.analytics import utc

READY='swipies:telegram-analytics:ready'
INFLIGHT='swipies:telegram-analytics:inflight'
LOCK_KEY='swipies:telegram-analytics:spool-lock'

def _message(message):
    if not message: return None
    user=getattr(message,'from_user',None); chat=getattr(message,'chat',None)
    def payment(value):
        if not value: return None
        return {k:getattr(value,k,None) for k in ('currency','total_amount','telegram_payment_charge_id')}
    return {'message_id':getattr(message,'message_id',None),'date':utc(getattr(message,'date',None)).isoformat(),
        'user':{'id':getattr(user,'id',None),'is_bot':bool(getattr(user,'is_bot',False))} if user else None,
        'chat':{'id':getattr(chat,'id',None),'type':str(getattr(chat,'type','unknown')),
                'title':str(getattr(chat,'title','') or '')[:160]},
        'has_content':any(getattr(message,k,None) for k in ('text','caption','photo','document','voice','audio','video','video_note','sticker','location','contact','poll','animation')),
        'successful_payment':payment(getattr(message,'successful_payment',None)),
        'refunded_payment':payment(getattr(message,'refunded_payment',None))}

def put(kind,channel,metadata,value):
    from rag.utils.redis_conn import REDIS_CONN
    from api.utils.key_crypto import encrypt_api_key
    if kind=='update':
        callback=getattr(value,'callback_query',None)
        user=getattr(callback,'from_user',None)
        value={'update_id':getattr(value,'update_id',None),'message':_message(getattr(value,'effective_message',None)),
            'edited':bool(getattr(value,'edited_message',None) or getattr(value,'edited_channel_post',None)),
            'callback':{'id':callback.id,'user':{'id':user.id,'is_bot':bool(user.is_bot)}} if callback and user else None}
    else: value=_message(value)
    sealed=encrypt_api_key(json.dumps({'kind':kind,'channel':channel,'metadata':metadata,'value':value},ensure_ascii=False))
    # Lists are durable across application restarts. Redis itself must have AOF
    # enabled, as documented for the existing queue deployment.
    REDIS_CONN.REDIS.lpush(READY,sealed)

def drain(limit=100):
    from rag.utils.redis_conn import REDIS_CONN
    from api.utils.key_crypto import decrypt_api_key
    from api.db.services.telegram_analytics_ingest import enqueue_update,enqueue_reply
    client=REDIS_CONN.REDIS
    # One lease for the fallback queue across API processes. SQL event IDs still
    # provide correctness if an interrupted consumer is retried after its lease.
    with client.lock(LOCK_KEY,timeout=30,blocking_timeout=0.01):
        count=0
        while count<limit:
            sealed=client.lindex(INFLIGHT,-1) or client.rpoplpush(READY,INFLIGHT)
            if not sealed: break
            body=json.loads(decrypt_api_key(sealed.decode() if isinstance(sealed,bytes) else sealed))
            value=body['value']
            def message(raw):
                if raw is None: return None
                return NS(message_id=raw['message_id'],date=datetime.fromisoformat(raw['date']),
                    from_user=NS(**raw['user']) if raw['user'] else None,chat=NS(**raw['chat']),
                    text='1' if raw['has_content'] else None,
                    successful_payment=NS(**raw['successful_payment']) if raw['successful_payment'] else None,
                    refunded_payment=NS(**raw['refunded_payment']) if raw['refunded_payment'] else None)
            if body['kind']=='update':
                callback=value.get('callback')
                update=NS(update_id=value['update_id'],effective_message=message(value['message']),
                    edited_message=True if value['edited'] else None,
                    callback_query=NS(id=callback['id'],from_user=NS(**callback['user'])) if callback else None)
                enqueue_update(body['channel'],body['metadata'],update)
            else: enqueue_reply(body['channel'],body['metadata'],message(value))
            client.lrem(INFLIGHT,1,sealed)
            count+=1
        return count
