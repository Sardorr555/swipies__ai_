"""Durable SQL outbox, idempotent processing, and confirmed bot payment ledger."""
import json
import uuid
import secrets
from datetime import datetime
from peewee import Case
from api.db.db_models import DB, ChatChannel
from api.db.telegram_analytics_models import (
    TelegramAnalyticsBot as Bot, TelegramAnalyticsUser as User,
    TelegramAnalyticsChat as Chat, TelegramAnalyticsEvent as Event,
    TelegramAnalyticsPayment as Payment, TelegramAnalyticsRefund as Refund,
    TelegramAnalyticsOrder as Order,
    TelegramAnalyticsConnection as Connection,
)
from api.channels.telegram.analytics import utc,digest,actor_key

ACTIVITY_KINDS=('incoming','interaction','purchase')
CHAT_KINDS={'private','group','supergroup','channel'}

def ensure_bot(channel, metadata):
    from api.utils.key_crypto import encrypt_api_key
    tid=str(metadata.get('id') or '')
    if not tid.isdigit(): raise ValueError('Verified bot identity is required')
    bid=digest(channel.id,tid)[:32]
    Bot.insert(id=bid,channel_id=channel.id,tenant_id=channel.tenant_id,telegram_bot_id=tid,
        name=str(metadata.get('first_name') or channel.name)[:160],
        username=str(metadata.get('username') or '')[:160],started_at=utc(),
        identity_secret_ciphertext=encrypt_api_key(secrets.token_urlsafe(32))).on_conflict_ignore().execute()
    Bot.update(name=str(metadata.get('first_name') or channel.name)[:160],
        username=str(metadata.get('username') or '')[:160]).where(Bot.id==bid).execute()
    return Bot.get_by_id(bid)

@DB.connection_context()
def register_bot(channel_id,metadata):
    channel=ChatChannel.get_or_none(ChatChannel.id==channel_id,ChatChannel.channel=='telegram')
    if not channel: return None
    with DB.atomic():
        bot=ensure_bot(channel,metadata)
        Connection.insert(channel_id=channel.id,bot_id=bot.id,tenant_id=channel.tenant_id).on_conflict_ignore().execute()
        Connection.update(bot_id=bot.id,tenant_id=channel.tenant_id).where(Connection.channel_id==channel.id).execute()
    return bot

def append(bot,kind,event_key,when,user_id=None,chat_id=None,chat_kind='private',title='',payload=None):
    from api.utils.key_crypto import decrypt_api_key
    secret=decrypt_api_key(bot.identity_secret_ciphertext)
    key=actor_key(bot.id,user_id,secret)
    chat=actor_key(bot.id,chat_id,secret)
    safe_kind=chat_kind if chat_kind in CHAT_KINDS else 'unknown'
    label=(str(title).strip()[:160] if safe_kind in {'group','supergroup','channel'} else '')
    clean={**(payload or {}),'chat_kind':safe_kind,'chat_label':label}
    Event.insert(id=digest(bot.id,kind,event_key),bot_id=bot.id,kind=kind,
        occurred_at=utc(when),user_key=key,chat_key=chat,payload=clean).on_conflict_ignore().execute()

@DB.connection_context()
def enqueue_update(channel_id,metadata,update):
    channel=ChatChannel.get_or_none(ChatChannel.id==channel_id,ChatChannel.channel=='telegram')
    if not channel: return
    with DB.atomic():
        bot=ensure_bot(channel,metadata)
        message=getattr(update,'effective_message',None)
        callback=getattr(update,'callback_query',None)
        if callback:
            user=getattr(callback,'from_user',None)
            if user and not getattr(user,'is_bot',False):
                chat=getattr(message,'chat',None)
                append(bot,'interaction','callback:'+str(callback.id),utc(),user.id,
                    getattr(chat,'id',None),str(getattr(chat,'type','private')),getattr(chat,'title',''))
            return
        if not message: return
        user=getattr(message,'from_user',None)
        chat=getattr(message,'chat',None)
        if not chat: return
        when=utc(getattr(message,'date',None))
        purchase=getattr(message,'successful_payment',None)
        refund=getattr(message,'refunded_payment',None)
        if purchase or refund:
            value=purchase or refund
            charge=str(getattr(value,'telegram_payment_charge_id',''))
            if not charge: return
            append(bot,'purchase' if purchase else 'refund',charge,when,
                getattr(user,'id',None) if user and not getattr(user,'is_bot',False) else None,
                chat.id,str(chat.type),getattr(chat,'title',''),{
                    'source_id':'telegram','charge_key':digest('telegram',charge),
                    'currency':str(value.currency).upper(),'amount_minor':int(value.total_amount),
                    'order_id':digest(bot.id,'telegram-order',charge)[:32],
                    'refund_id':digest('telegram-refund',charge)})
            return
        # Editing a message is not another user message. Duplicate update IDs are
        # also covered by the durable message-id key, across process restarts.
        if getattr(update,'edited_message',None) or getattr(update,'edited_channel_post',None): return
        if not user or getattr(user,'is_bot',False): return
        fields=('text','caption','photo','document','voice','audio','video','video_note','sticker','location','contact','poll','animation')
        if not any(getattr(message,name,None) for name in fields): return
        append(bot,'incoming',f'{chat.id}:{message.message_id}',when,user.id,chat.id,
               str(chat.type),getattr(chat,'title',''))

@DB.connection_context()
def enqueue_reply(channel_id,metadata,message):
    channel=ChatChannel.get_or_none(ChatChannel.id==channel_id,ChatChannel.channel=='telegram')
    if not channel or not message: return
    with DB.atomic():
        bot=ensure_bot(channel,metadata)
        chat=message.chat
        append(bot,'outgoing',f'{chat.id}:{message.message_id}',getattr(message,'date',None),
            None,chat.id,str(chat.type),getattr(chat,'title',''))

def _seen(model,identity,values,when):
    model.insert(id=identity,first_seen=when,last_seen=when,**values).on_conflict_ignore().execute()
    model.update(first_seen=Case(None,[(model.first_seen>when,when)],model.first_seen),
        last_seen=Case(None,[(model.last_seen<when,when)],model.last_seen)).where(model.id==identity).execute()

def _validate_money(payload):
    from api.channels.telegram.currency import CURRENCIES
    currency=str(payload.get('currency','')).upper()
    amount=payload.get('amount_minor')
    if currency not in CURRENCIES or isinstance(amount,bool) or not isinstance(amount,int) or not 0<amount<=10**15:
        raise ValueError('Invalid confirmed payment amount')
    return currency,amount

def _accept_refunds(bot_id,source,charge):
    payment=Payment.select().where(Payment.bot_id==bot_id,Payment.source_id==source,Payment.charge_key==charge).for_update().first()
    if not payment: return
    accepted=0
    for refund in Refund.select().where(Refund.bot_id==bot_id,Refund.source_id==source,Refund.charge_key==charge).order_by(Refund.refunded_at,Refund.id).for_update():
        valid=refund.currency==payment.currency and accepted+refund.amount_minor<=payment.amount_minor
        Refund.update(accepted=valid).where(Refund.id==refund.id).execute()
        if valid: accepted+=refund.amount_minor
    if accepted:
        Order.update(status='refunded' if accepted==payment.amount_minor else 'partially_refunded').where(Order.id==payment.order_id).execute()

def _process(event):
    payload=event.payload or {}
    when=event.occurred_at
    if event.kind in ACTIVITY_KINDS and event.user_key:
        _seen(User,digest(event.bot_id,event.user_key)[:32],
            {'bot_id':event.bot_id,'user_key':event.user_key},when)
    if event.chat_key:
        _seen(Chat,digest(event.bot_id,event.chat_key)[:32],
            {'bot_id':event.bot_id,'chat_key':event.chat_key,'kind':payload.get('chat_kind','unknown'),
             'label':payload.get('chat_label','')[:160]},when)
    if event.kind in {'purchase','refund'}:
        currency,amount=_validate_money(payload)
        source=str(payload['source_id']); charge=str(payload['charge_key'])
        if event.kind=='purchase':
            if not event.user_key: raise ValueError('A confirmed payer must be linked')
            order_id=payload['order_id']
            existing=Order.get_or_none(Order.id==order_id)
            if existing and (existing.bot_id!=event.bot_id or existing.user_key!=event.user_key or existing.currency!=currency or existing.amount_minor!=amount):
                raise ValueError('Order attribution does not match')
            Order.insert(id=order_id,bot_id=event.bot_id,source_id=source,user_key=event.user_key,
                chat_key=event.chat_key,currency=currency,amount_minor=amount,status='paid').on_conflict_ignore().execute()
            # One successful charge per server order. Repeated notifications cannot
            # turn the same order into several purchases.
            prior=Payment.select().where(Payment.order_id==order_id).for_update().first()
            payment_id=digest(event.bot_id,source,charge)
            if prior and prior.id!=payment_id: raise ValueError('Order already has a confirmed charge')
            Payment.insert(id=payment_id,bot_id=event.bot_id,source_id=source,charge_key=charge,
                order_id=order_id,user_key=event.user_key,chat_key=event.chat_key,currency=currency,
                amount_minor=amount,paid_at=when).on_conflict_ignore().execute()
            Order.update(status='paid').where(Order.id==order_id).execute()
            if source=='telegram': Bot.update(native_payments_seen=True).where(Bot.id==event.bot_id).execute()
        else:
            Refund.insert(id=digest(event.bot_id,source,payload['refund_id']),bot_id=event.bot_id,
                source_id=source,charge_key=charge,currency=currency,amount_minor=amount,
                refunded_at=when,accepted=source=='telegram').on_conflict_ignore().execute()
            if source=='telegram': Bot.update(native_payments_seen=True).where(Bot.id==event.bot_id).execute()
        _accept_refunds(event.bot_id,source,charge)
    Bot.update(last_event_at=Case(None,[((Bot.last_event_at.is_null())|(Bot.last_event_at<when),when)],Bot.last_event_at),
        last_processed_at=utc()).where(Bot.id==event.bot_id).execute()

@DB.connection_context()
def drain(limit=100):
    """Atomic claim + aggregation; retries survive worker/app restarts."""
    ids=[row.id for row in Event.select(Event.id).where(Event.processed==False).order_by(Event.created_at).limit(limit)]
    for identity in ids:
        try:
            with DB.atomic():
                claimed=Event.update(processed=True).where(Event.id==identity,Event.processed==False).execute()
                if not claimed: continue
                _process(Event.get_by_id(identity))
        except (ValueError,KeyError,TypeError):
            Event.update(processed=True,rejected=True,attempts=Event.attempts+1).where(Event.id==identity).execute()
        except Exception:
            # Leave it pending; no raw payload or user identity is logged.
            Event.update(attempts=Event.attempts+1).where(Event.id==identity).execute()
    return len(ids)
