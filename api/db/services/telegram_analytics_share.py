"""Capability sharing: hashed tokens, explicit projection and no cached private data."""
import hashlib
import secrets
import re
from datetime import datetime,timedelta
from api.db.db_models import DB
from api.db.telegram_analytics_models import TelegramAnalyticsShare as Share,TelegramAnalyticsBot as Bot
from api.db.services.telegram_analytics_query import METRICS,MONEY_METRICS,period_range,summary
from api.channels.telegram.analytics import utc

def validate_settings(body):
    if not isinstance(body,dict): raise ValueError('Некорректные параметры виджета')
    chosen=body.get('metrics',['users_total','users_active','users_new','messages_in','messages_out'])
    if not isinstance(chosen,list) or not chosen or len(chosen)>len(METRICS) or not all(v in METRICS for v in chosen):
        raise ValueError('Выберите допустимые показатели')
    show_revenue=body.get('show_revenue',False) is True
    chosen=list(dict.fromkeys(v for v in chosen if show_revenue or v not in MONEY_METRICS))
    if not chosen: raise ValueError('Выберите хотя бы один показатель')
    options={k:body.get(k) for k in ('period','timezone','start','end') if body.get(k) is not None}
    period_range(options)
    return {**options,'metrics':chosen,'show_revenue':show_revenue,
            'include_link':body.get('include_link',False) is True}

def project(data,settings,title):
    chosen=set(settings['metrics'])
    money=settings.get('show_revenue') is True
    def payment(value):
        if value is None: return None
        result={k:value[k] for k in ('payers','payments') if k in chosen}
        if money and chosen&MONEY_METRICS:
            fields=['currency']
            if 'revenue' in chosen: fields+=['amount_minor','amount']
            if 'refunds' in chosen: fields+=['refund_minor','refund_amount']
            result['currencies']=[{k:item[k] for k in fields if k in item} for item in value['currencies']]
        return result
    result={'title':title,'bot':{k:data['bot'][k] for k in ('name','username')},
        'period':data['period'],'updated_at':data['updated_at'],'last_processed_at':data['last_processed_at'],
        'collection_started_at':data['collection_started_at'],'coverage':data['coverage'],
        'metrics':{k:v for k,v in data['metrics'].items() if k in chosen},
        'selected_metrics':list(settings['metrics']),'audience_note':data['audience_note']}
    if chosen&{'payers','payments','revenue','refunds'}:
        result.update(payment_tracking=data['payment_tracking'],payments_period=payment(data['payments_period']),
            payments_all_time=payment(data['payments_all_time']),payment_data_incomplete=bool(data['unmatched_refunds']),
            payment_collection_started_at=data['payment_collection_started_at'],payment_coverage=data['payment_coverage'])
    result['series']=[{'date':row['date'],**{k:v for k,v in row.items() if k in chosen and k!='payments'},
        **({'payments':payment(row['payments'])} if chosen&{'payers','payments','revenue','refunds'} else {})} for row in data['series']]
    return result

def create(bot,user_id,body):
    settings=validate_settings(body)
    title=' '.join(str(body.get('title') or bot.name).split())[:120]
    if not title: raise ValueError('Укажите название виджета')
    days=body.get('expires_days',7)
    if days is not None and (isinstance(days,bool) or not isinstance(days,int) or not 1<=days<=365):
        raise ValueError('Срок ссылки: от 1 до 365 дней или бессрочно')
    token=secrets.token_urlsafe(32)
    identity=secrets.token_hex(16)
    Share.create(id=identity,bot_id=bot.id,created_by=user_id,title=title,settings=settings,
        token_hash=hashlib.sha256(token.encode()).hexdigest(),
        expires_at=utc()+timedelta(days=days) if days else None)
    # Raw token is returned once to the authorized owner, never persisted.
    return {'id':identity,'token':token,'path':'/shared/telegram-analytics#'+token,
            'title':title,'settings':settings}

class ShareUnavailable(Exception):
    def __init__(self,reason='unavailable',status=410): self.reason,self.status=reason,status

def resolve(token):
    if not isinstance(token,str) or not re.fullmatch(r'[A-Za-z0-9_-]{43}',token):
        raise ShareUnavailable('unavailable',404)
    share=Share.get_or_none(Share.token_hash==hashlib.sha256(token.encode()).hexdigest())
    if not share: raise ShareUnavailable('unavailable',404)
    if share.revoked_at: raise ShareUnavailable('revoked')
    if share.expires_at and share.expires_at<=utc(): raise ShareUnavailable('expired')
    bot=Bot.get_or_none(Bot.id==share.bot_id)
    if not bot: raise ShareUnavailable('unavailable',404)
    # Deleting the channel also revokes its capabilities, without revealing why.
    from api.db.db_models import ChatChannel
    if not ChatChannel.select().where(ChatChannel.id==bot.channel_id,ChatChannel.tenant_id==bot.tenant_id).exists():
        raise ShareUnavailable('revoked')
    return share,bot

def public_data(token):
    share,bot=resolve(token)
    return project(summary(bot,share.settings),share.settings,share.title)

def list_shares(bot):
    return [{'id':s.id,'title':s.title,'settings':s.settings,'created_at':s.created_at.isoformat()+'Z',
        'expires_at':s.expires_at.isoformat()+'Z' if s.expires_at else None,
        'revoked_at':s.revoked_at.isoformat()+'Z' if s.revoked_at else None}
        for s in Share.select().where(Share.bot_id==bot.id).order_by(Share.created_at.desc()).limit(100)]
