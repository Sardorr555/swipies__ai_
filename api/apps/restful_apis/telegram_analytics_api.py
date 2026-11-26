"""Telegram bot analytics, scoped sharing and signed external payment notifications."""
import asyncio
import hashlib
import json
from functools import wraps
from urllib.parse import urlsplit
from quart import request,Response
from api.apps import current_user,login_required
from api.db.db_models import DB
from api.db.telegram_analytics_models import (TelegramAnalyticsBot as Bot,TelegramAnalyticsShare as Share,
    TelegramAnalyticsPaymentSource as Source)
from api.db.services import telegram_analytics_query as query
from api.db.services import telegram_analytics_share as sharing
from api.channels.telegram.analytics import utc
from api.utils.api_utils import get_json_result

NO_CACHE={'Cache-Control':'no-store, private, max-age=0','Pragma':'no-cache',
    'X-Robots-Tag':'noindex, nofollow, noarchive','Referrer-Policy':'no-referrer',
    'X-Content-Type-Options':'nosniff'}

class InputTooLarge(ValueError): pass

async def read_body():
    data=bytearray()
    async for chunk in request.body:
        data.extend(chunk)
        if len(data)>65536: raise InputTooLarge('Запрос слишком большой')
    return bytes(data)

async def read_json():
    value=json.loads(await read_body())
    if not isinstance(value,dict): raise ValueError('Передайте JSON-объект')
    return value

def response(data=None,message='success',code=0,status=200):
    result=get_json_result(data=data,message=message,code=code)
    result.status_code=status
    for key,value in NO_CACHE.items(): result.headers[key]=value
    return result

def bounded(handler):
    @wraps(handler)
    async def wrapped(*args,**kwargs):
        try:
            if request.content_length and request.content_length>65536:
                return response(message='Запрос слишком большой',code=413,status=413)
            return await handler(*args,**kwargs)
        except query.AnalyticsAccessDenied as error:
            return response(message=str(error),code=403,status=403)
        except sharing.ShareUnavailable as error:
            return response(message=error.reason,code=error.status,status=error.status)
        except PermissionError:
            return response(message='Доступ запрещён',code=403,status=403)
        except InputTooLarge:
            return response(message='Запрос слишком большой',code=413,status=413)
        except (ValueError,TypeError,KeyError) as error:
            return response(message=str(error)[:200],code=400,status=400)
        except Exception:
            return response(message='Аналитика временно недоступна. Проверьте миграцию и обработчик событий.',code=503,status=503)
    return wrapped

@DB.connection_context()
def private_data(channel_id,user_id,options,table=False):
    channel=query.channel_for_user(channel_id,user_id)
    bot=query.current_bot(channel)
    if not bot: return {'initialized':False,'bot':{'name':channel.name,'username':''},'collection_started_at':None,
        'message':'Сбор начнётся после успешного подключения Telegram-бота. Исторические события не выдумываются.'}
    if table: return query.chat_table(bot,options)
    result=query.summary(bot,options)
    from api.channels.telegram.channel import get_runtime_snapshot
    snapshot=get_runtime_snapshot(channel.id) or {}
    result.update(initialized=True,connection={'enabled':bool(channel.status),
        'polling_active':bool(snapshot.get('polling_active')),'status':snapshot.get('worker_status','unknown')})
    return result

@manager.route('/chat-channels/<channel_id>/analytics',methods=['GET'])
@login_required
@bounded
async def analytics_summary(channel_id):
    """Bot aggregates. Query: period=today|yesterday|7d|30d|custom, timezone=IANA, start/end=YYYY-MM-DD. Owner/organization admin only. No subscription-owner revenue is included."""
    return response(await asyncio.to_thread(private_data,channel_id,current_user.id,dict(request.args)))

@manager.route('/chat-channels/<channel_id>/analytics/chats',methods=['GET'])
@login_required
@bounded
async def analytics_chats(channel_id):
    """Observed chats, period/timezone, search, sort=name|active_users|messages|last_activity, direction, page/page_size. Telegram audience is never presented as group membership."""
    return response(await asyncio.to_thread(private_data,channel_id,current_user.id,dict(request.args),True))

@DB.connection_context()
def manage_share(channel_id,user_id,body=None,share_id=None):
    channel=query.channel_for_user(channel_id,user_id,True)
    bot=query.current_bot(channel)
    if not bot: raise ValueError('Сначала подключите бота и начните сбор событий')
    bot_ids=Bot.select(Bot.id).where(Bot.channel_id==channel.id,Bot.tenant_id==channel.tenant_id)
    if share_id:
        changed=Share.update(revoked_at=utc()).where(Share.id==share_id,Share.bot_id.in_(bot_ids),Share.revoked_at.is_null()).execute()
        return {'revoked':bool(changed)}
    if body is not None: return sharing.create(bot,user_id,body)
    # Include old identities after replacing the bot, so their capabilities remain revocable.
    items=[]
    for old in Bot.select().where(Bot.id.in_(bot_ids)):
        items+=sharing.list_shares(old)
    return items

@manager.route('/chat-channels/<channel_id>/analytics/shares',methods=['GET','POST'])
@login_required
@bounded
async def analytics_shares(channel_id):
    """List or create read-only aggregate capabilities. POST: title, metrics[], show_revenue, period/timezone/start/end, expires_days (null=unlimited), include_link. A new unguessable token is returned only once; only its hash is stored."""
    body=await read_json() if request.method=='POST' else None
    return response(await asyncio.to_thread(manage_share,channel_id,current_user.id,body))

@manager.route('/chat-channels/<channel_id>/analytics/shares/<share_id>',methods=['DELETE'])
@login_required
@bounded
async def analytics_revoke(channel_id,share_id):
    """Immediately revoke the selected channel's public capability. Future API/PNG requests deny access and are never cached."""
    return response(await asyncio.to_thread(manage_share,channel_id,current_user.id,None,share_id))

def public_rate_limit(token,address,card=False):
    from rag.utils.redis_conn import REDIS_CONN
    import time
    key=hashlib.sha256((address or 'unknown').encode()).hexdigest()[:24]
    bucket=int(time.time())//60
    limits=[(f'tg-analytics:public:ip:{key}:{bucket}',60),
            (f'tg-analytics:public:token:{hashlib.sha256(str(token).encode()).hexdigest()}:{bucket}',600)]
    if card: limits.append((f'tg-analytics:public:png:{key}:{bucket}',10))
    for name,limit in limits:
        pipe=REDIS_CONN.REDIS.pipeline(transaction=True)
        count,_=pipe.incr(name).expire(name,120).execute()
        if count>limit: return False
    return True

@manager.route('/telegram-analytics/public',methods=['POST'])
@bounded
async def analytics_public():
    # Fragment capability: token never appears in a URL, referrer, or access log.
    body=await read_json()
    if not isinstance(body,dict) or set(body)!={'token'}: raise ValueError('Передайте только токен виджета')
    from api.db.services.agent_access_service import client_address
    address=client_address(request.remote_addr,request.headers.get('X-Real-IP'))
    if not await asyncio.to_thread(public_rate_limit,body['token'],address):
        return response(message='Слишком много запросов, повторите позже',code=429,status=429)
    @DB.connection_context()
    def read(): return sharing.public_data(body['token'])
    return response(await asyncio.to_thread(read))

@DB.connection_context()
def card_data(channel_id,user_id,body,origin):
    channel=query.channel_for_user(channel_id,user_id,True)
    bot=query.current_bot(channel)
    if not bot: raise ValueError('Данных пока нет')
    link=None
    if body.get('token'):
        share,shared_bot=sharing.resolve(body['token'])
        if shared_bot.id!=bot.id: raise query.AnalyticsAccessDenied('Виджет принадлежит другому боту')
        settings=share.settings; title=share.title
        if settings.get('include_link'): link=origin.rstrip('/')+'/shared/telegram-analytics#'+body['token']
    else:
        settings=sharing.validate_settings(body); title=str(body.get('title') or bot.name)[:120]
    data=sharing.project(query.summary(bot,settings),settings,title)
    from api.db.services.telegram_analytics_export import render_png
    return render_png(data,body.get('format','square'),link)

@manager.route('/chat-channels/<channel_id>/analytics/card',methods=['POST'])
@login_required
@bounded
async def analytics_card(channel_id):
    """Export only the chosen aggregates as PNG: format=square (1080×1080) or story (1080×1920). Optional capability token binds the card to that widget's scope and link. No automatic Instagram posting."""
    body=await read_json()
    png=await asyncio.to_thread(card_data,channel_id,current_user.id,body,request.host_url)
    return Response(png,mimetype='image/png',headers={**NO_CACHE,'Content-Disposition':'attachment; filename="swipies-telegram-'+str(body.get('format','square'))+'.png"'})

@DB.connection_context()
def payment_source(channel_id,user_id,body=None,source_id=None):
    channel=query.channel_for_user(channel_id,user_id,True); bot=query.current_bot(channel)
    if not bot: raise ValueError('Сначала подключите бота')
    if source_id:
        Source.update(status='revoked').where(Source.id==source_id,Source.bot_id==bot.id).execute()
        return {'revoked':True}
    if body is not None:
        from api.db.services.telegram_analytics_payments import source_create
        return source_create(bot,body)
    return [{'id':s.id,'name':s.name,'provider':s.provider,'status':s.status,
        'notification_path':'/api/v1/telegram-analytics/payment-notifications/'+s.id}
        for s in Source.select().where(Source.bot_id==bot.id)]

@manager.route('/chat-channels/<channel_id>/analytics/payment-sources',methods=['GET','POST'])
@login_required
@bounded
async def analytics_payment_sources(channel_id):
    """Manage a verified external-payment bridge, separately from Swipies subscriptions. POST name + 32..200-character secret; the secret is encrypted and never returned. A signed verification notification activates the source."""
    body=await read_json() if request.method=='POST' else None
    return response(await asyncio.to_thread(payment_source,channel_id,current_user.id,body))

@manager.route('/chat-channels/<channel_id>/analytics/payment-sources/<source_id>',methods=['DELETE'])
@login_required
@bounded
async def analytics_payment_source_revoke(channel_id,source_id):
    return response(await asyncio.to_thread(payment_source,channel_id,current_user.id,None,source_id))

@manager.route('/chat-channels/<channel_id>/analytics/orders',methods=['POST'])
@login_required
@bounded
async def analytics_order(channel_id):
    """Create only a bot-purchase attribution order: source_id, telegram_user_id, optional telegram_chat_id, currency, amount_minor. The user must already be observed by this bot. This creates no payment or revenue; a verified server callback is required."""
    body=await read_json(); user_id=current_user.id
    @DB.connection_context()
    def create():
        from api.db.services.telegram_analytics_payments import order_create
        return order_create(query.current_bot(query.channel_for_user(channel_id,user_id,True)),body)
    return response(await asyncio.to_thread(create))

@manager.route('/telegram-analytics/payment-notifications/<source_id>',methods=['POST'])
@bounded
async def analytics_notification(source_id):
    raw=await read_body()
    timestamp=request.headers.get('X-Swipies-Timestamp')
    signature=request.headers.get('X-Swipies-Signature')
    @DB.connection_context()
    def receive():
        from api.db.services.telegram_analytics_payments import notification
        return notification(source_id,raw,timestamp,signature)
    return response(await asyncio.to_thread(receive))
