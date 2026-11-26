"""Verified external payment bridge. Never imports Swipies subscription orders."""
import hashlib,hmac,json,secrets,time
from api.db.db_models import DB
from api.db.telegram_analytics_models import (TelegramAnalyticsPaymentSource as Source,
    TelegramAnalyticsOrder as Order,TelegramAnalyticsUser as User,TelegramAnalyticsPayment as Payment,
    TelegramAnalyticsEvent as Event)
from api.db.services.telegram_analytics_ingest import append,_validate_money
from api.channels.telegram.analytics import utc,digest,actor_key
from api.utils.key_crypto import encrypt_api_key,decrypt_api_key

def source_create(bot,body):
    secret=body.get('secret','')
    if not isinstance(secret,str) or not 32<=len(secret)<=200:
        raise ValueError('Ключ подписи должен содержать 32–200 символов')
    name=str(body.get('name','Внешняя оплата')).strip()[:100]
    identity=secrets.token_hex(16)
    Source.create(id=identity,bot_id=bot.id,name=name,secret_ciphertext=encrypt_api_key(secret))
    return {'id':identity,'name':name,'status':'pending',
        'notification_path':'/api/v1/telegram-analytics/payment-notifications/'+identity}

def order_create(bot,body):
    source=Source.get_or_none(Source.id==body.get('source_id'),Source.bot_id==bot.id,Source.status=='active')
    if not source: raise ValueError('Сначала подтвердите источник оплаты подписанным серверным уведомлением')
    currency,amount=_validate_money(body)
    tg_user=str(body.get('telegram_user_id',''))
    tg_chat=str(body.get('telegram_chat_id',''))
    if not tg_user.isdigit() or (tg_chat and not tg_chat.lstrip('-').isdigit()): raise ValueError('Некорректные Telegram-идентификаторы')
    secret=decrypt_api_key(bot.identity_secret_ciphertext)
    user=actor_key(bot.id,tg_user,secret)
    if not User.select().where(User.bot_id==bot.id,User.user_key==user).exists():
        raise ValueError('Пользователь ещё не замечен этим ботом')
    order=Order.create(id=secrets.token_hex(16),bot_id=bot.id,source_id=source.id,
        user_key=user,chat_key=actor_key(bot.id,tg_chat,secret) if tg_chat else None,
        currency=currency,amount_minor=amount)
    return {'id':order.id,'currency':currency,'amount_minor':str(amount),'status':'created'}

def notification(source_id,raw,timestamp,signature,now=None):
    if len(raw)>65536: raise ValueError('Уведомление превышает допустимый размер')
    source=Source.get_or_none(Source.id==source_id,Source.status.in_(['pending','active']))
    if not source: raise PermissionError('Неверная подпись')
    try: moment=int(timestamp)
    except (TypeError,ValueError): raise PermissionError('Неверная подпись') from None
    if abs((now or time.time())-moment)>300: raise PermissionError('Уведомление просрочено')
    expected=hmac.new(decrypt_api_key(source.secret_ciphertext).encode(),str(moment).encode()+b'.'+raw,hashlib.sha256).hexdigest()
    if not isinstance(signature,str) or not hmac.compare_digest(expected,signature.lower()): raise PermissionError('Неверная подпись')
    body=json.loads(raw)
    if not isinstance(body,dict): raise ValueError('Некорректное уведомление')
    if body.get('type')=='verification':
        Source.update(status='active',verified_at=utc()).where(Source.id==source.id).execute()
        return {'accepted':True,'source_verified':True}
    if source.status!='active': raise ValueError('Источник не подтверждён')
    order=Order.get_or_none(Order.id==body.get('order_id'),Order.source_id==source.id)
    if not order: raise ValueError('Неизвестный серверный заказ')
    currency,amount=_validate_money(body)
    if currency!=order.currency: raise ValueError('Валюта не соответствует заказу')
    kind={'payment_succeeded':'purchase','refund_succeeded':'refund'}.get(body.get('type'))
    event_id=str(body.get('event_id','')); transaction=str(body.get('transaction_id',''))
    if not kind or not event_id or len(event_id)>160 or not transaction or len(transaction)>200:
        raise ValueError('Укажите тип, событие и идентификатор транзакции')
    if kind=='purchase' and amount!=order.amount_minor: raise ValueError('Сумма не соответствует заказу')
    charge=digest(source.id,transaction)
    if kind=='refund':
        payment=Payment.get_or_none(Payment.order_id==order.id,Payment.charge_key==charge)
        if not payment or amount>payment.amount_minor: raise ValueError('Возврат не соответствует подтверждённой оплате')
    # Only server timestamps are trusted for external callbacks. A verified
    # provider cannot inject arbitrary historical periods through this endpoint.
    payload={'source_id':source.id,'currency':currency,'amount_minor':amount,
        'charge_key':charge,'order_id':order.id,'refund_id':event_id,'chat_kind':'unknown','chat_label':''}
    Event.insert(id=digest(source.id,kind,event_id),bot_id=order.bot_id,kind=kind,user_key=order.user_key,
        chat_key=order.chat_key,occurred_at=utc(),payload=payload).on_conflict_ignore().execute()
    return {'accepted':True}
