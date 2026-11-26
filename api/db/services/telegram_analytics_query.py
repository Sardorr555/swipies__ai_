"""Timezone-correct bot aggregates. Never reads platform subscription payments."""
from datetime import datetime,date,time,timedelta,timezone
from decimal import Decimal
from zoneinfo import ZoneInfo,ZoneInfoNotFoundError
from peewee import fn,Case,JOIN
from api.db.db_models import DB,ChatChannel,UserTenant
from api.db.telegram_analytics_models import (
    TelegramAnalyticsBot as Bot,TelegramAnalyticsUser as User,TelegramAnalyticsChat as Chat,
    TelegramAnalyticsEvent as Event,TelegramAnalyticsPayment as Payment,
    TelegramAnalyticsRefund as Refund,TelegramAnalyticsPaymentSource as Source,
    TelegramAnalyticsConnection as Connection,
)
from api.db.services.telegram_analytics_ingest import ACTIVITY_KINDS
from api.channels.telegram.analytics import utc
from api.channels.telegram.currency import exponent

METRICS={'users_total','users_active','users_new','messages_in','messages_out','payers','payments','revenue','refunds'}
MONEY_METRICS={'revenue','refunds'}

class AnalyticsAccessDenied(PermissionError): pass

def channel_for_user(channel_id,user_id,manage=False):
    channel=ChatChannel.get_or_none(ChatChannel.id==channel_id,ChatChannel.channel=='telegram')
    if not channel: raise AnalyticsAccessDenied('Аналитика недоступна')
    if channel.tenant_id==user_id: return channel
    member=UserTenant.get_or_none(UserTenant.tenant_id==channel.tenant_id,
        UserTenant.user_id==user_id,UserTenant.status=='1',UserTenant.role.in_(['owner','admin']))
    if not member: raise AnalyticsAccessDenied('Недостаточно прав для аналитики канала')
    return channel

def current_bot(channel):
    # Runtime marks the active bot identity; a replacement token cannot merge two bots.
    connection=Connection.get_or_none(Connection.channel_id==channel.id)
    bid=connection.bot_id if connection else None
    if bid:
        bot=Bot.get_or_none(Bot.id==bid,Bot.channel_id==channel.id,Bot.tenant_id==channel.tenant_id)
        if bot: return bot
    return Bot.select().where(Bot.channel_id==channel.id,Bot.tenant_id==channel.tenant_id).order_by(Bot.started_at.desc()).first()

def period_range(options,now=None):
    name=str(options.get('period','7d'))
    zone=str(options.get('timezone','Asia/Tashkent'))
    try: tz=ZoneInfo(zone)
    except (ZoneInfoNotFoundError,ValueError): raise ValueError('Неизвестный часовой пояс') from None
    today=(now or datetime.now(timezone.utc)).astimezone(tz).date()
    if name=='today': start=end=today
    elif name=='yesterday': start=end=today-timedelta(days=1)
    elif name=='7d': start,end=today-timedelta(days=6),today
    elif name=='30d': start,end=today-timedelta(days=29),today
    elif name=='custom':
        try: start,end=date.fromisoformat(str(options['start'])),date.fromisoformat(str(options['end']))
        except (KeyError,ValueError): raise ValueError('Укажите корректные начальную и конечную даты') from None
    else: raise ValueError('Неизвестный период')
    if end<start or (end-start).days>365: raise ValueError('Период должен содержать от 1 до 366 дней')
    if start>today: raise ValueError('Дата начала не может быть в будущем')
    lower=datetime.combine(start,time.min,tzinfo=tz).astimezone(timezone.utc).replace(tzinfo=None)
    upper=datetime.combine(end+timedelta(days=1),time.min,tzinfo=tz).astimezone(timezone.utc).replace(tzinfo=None)
    return {'period':name,'timezone':zone,'start':start.isoformat(),'end':end.isoformat(),
            'start_utc':lower.isoformat()+'Z','end_utc_exclusive':upper.isoformat()+'Z'},lower,upper,tz

def _events(bot_id,lower,upper):
    return Event.select().where(Event.bot_id==bot_id,Event.processed==True,Event.rejected==False,
        Event.occurred_at>=lower,Event.occurred_at<upper)

def _counts(bot,lower,upper):
    events=_events(bot.id,lower,upper)
    active=events.where(Event.kind.in_(ACTIVITY_KINDS),Event.user_key.is_null(False))
    return {'users_active':active.select(fn.COUNT(Event.user_key.distinct())).scalar() or 0,
        'users_new':User.select().where(User.bot_id==bot.id,User.first_seen>=lower,User.first_seen<upper).count(),
        'messages_in':events.where(Event.kind=='incoming').count(),
        'messages_out':events.where(Event.kind=='outgoing').count()}

def amount_text(amount,currency):
    precision=exponent(currency)
    return f'{Decimal(int(amount))/(Decimal(10)**precision):.{precision}f}'

def _payments(bot,lower=None,upper=None):
    payments=Payment.select().where(Payment.bot_id==bot.id)
    refunds=Refund.select().where(Refund.bot_id==bot.id,Refund.accepted==True)
    if lower is not None:
        payments=payments.where(Payment.paid_at>=lower,Payment.paid_at<upper)
        refunds=refunds.where(Refund.refunded_at>=lower,Refund.refunded_at<upper)
    currencies={}
    for row in payments.select(Payment.currency,fn.SUM(Payment.amount_minor).alias('gross'),fn.COUNT(Payment.id).alias('count')).group_by(Payment.currency).dicts():
        currencies[row['currency']]={'currency':row['currency'],'amount_minor':str(int(row['gross'] or 0)),
            'amount':amount_text(row['gross'] or 0,row['currency']),'payments':int(row['count']),
            'refund_minor':'0','refund_amount':amount_text(0,row['currency'])}
    for row in refunds.select(Refund.currency,fn.SUM(Refund.amount_minor).alias('refunds')).group_by(Refund.currency).dicts():
        item=currencies.setdefault(row['currency'],{'currency':row['currency'],'amount_minor':'0',
            'amount':amount_text(0,row['currency']),'payments':0})
        item.update(refund_minor=str(int(row['refunds'] or 0)),refund_amount=amount_text(row['refunds'] or 0,row['currency']))
    return {'payers':payments.select(fn.COUNT(Payment.user_key.distinct())).scalar() or 0,
            'payments':payments.count(),'currencies':sorted(currencies.values(),key=lambda v:v['currency'])}

def summary(bot,options,now=None):
    period,lower,upper,tz=period_range(options,now)
    has_events=_events(bot.id,lower,upper).exists()
    coverage='unavailable' if upper<=bot.started_at and not has_events else ('partial' if lower<bot.started_at else 'available')
    connected=bool(bot.native_payments_seen or Source.select().where(Source.bot_id==bot.id,Source.status=='active').exists()
        or Payment.select().where(Payment.bot_id==bot.id).exists())
    payment_start=bot.started_at if bot.native_payments_seen else (Source.select(fn.MIN(Source.verified_at)).where(Source.bot_id==bot.id,Source.verified_at.is_null(False)).scalar())
    if connected and payment_start is None:
        payment_start=Payment.select(fn.MIN(Payment.paid_at)).where(Payment.bot_id==bot.id).scalar()
    payment_coverage=('unavailable' if payment_start and upper<=payment_start else 'partial' if payment_start and lower<payment_start else 'available') if connected else 'unavailable'
    counts=_counts(bot,lower,upper)
    counts['users_total']=User.select().where(User.bot_id==bot.id).count()
    if coverage=='unavailable':
        for key in ('users_active','users_new','messages_in','messages_out'): counts[key]=None
    selected=_payments(bot,lower,upper) if connected else None
    lifetime=_payments(bot) if connected else None
    active=_events(bot.id,lower,upper).where(Event.kind.in_(ACTIVITY_KINDS),Event.user_key.is_null(False)).select(Event.user_key).distinct()
    converted=Payment.select(fn.COUNT(Payment.user_key.distinct())).where(Payment.bot_id==bot.id,
        Payment.paid_at>=lower,Payment.paid_at<upper,Payment.user_key.in_(active)).scalar() or 0
    denominator=counts['users_active']
    series=[]
    day=date.fromisoformat(period['start']); last=date.fromisoformat(period['end'])
    while day<=last:
        a=datetime.combine(day,time.min,tzinfo=tz).astimezone(timezone.utc).replace(tzinfo=None)
        b=datetime.combine(day+timedelta(days=1),time.min,tzinfo=tz).astimezone(timezone.utc).replace(tzinfo=None)
        daily=_counts(bot,a,b)
        if b<=bot.started_at and not _events(bot.id,a,b).exists(): daily={k:None for k in daily}
        series.append({'date':day.isoformat(),**daily,'payments':_payments(bot,a,b) if connected and not (payment_start and b<=payment_start) else None})
        day+=timedelta(days=1)
    pending=Event.select().where(Event.bot_id==bot.id,Event.processed==False).count()
    return {'bot':{'id':bot.id,'name':bot.name,'username':bot.username},'period':period,
        'collection_started_at':bot.started_at.isoformat()+'Z','coverage':coverage,
        'updated_at':utc().isoformat()+'Z','last_event_at':bot.last_event_at.isoformat()+'Z' if bot.last_event_at else None,
        'last_processed_at':bot.last_processed_at.isoformat()+'Z' if bot.last_processed_at else None,
        'pending_events':pending,'metrics':counts,'payment_tracking':'connected' if connected else 'not_connected',
        'payments_period':selected if coverage!='unavailable' and payment_coverage!='unavailable' else None,'payments_all_time':lifetime,
        'payment_collection_started_at':payment_start.isoformat()+'Z' if payment_start else None,'payment_coverage':payment_coverage,
        'conversion':{'numerator':int(converted),'denominator':denominator,
            'percent':round(converted/denominator*100,2) if connected and denominator and coverage=='available' and payment_coverage=='available' else None,
            'formula':'Оплатившие среди активных за выбранный период / активные за тот же период × 100'},
        'unmatched_refunds':Refund.select().where(Refund.bot_id==bot.id,Refund.accepted==False).count(),
        'series':series,
        'audience_note':'Это замеченные ботом пользователи, а не все участники групп или подписчики. Telegram не предоставляет полный состав аудитории.'}

def chat_table(bot,options):
    _,lower,upper,_=period_range(options)
    try: page=max(1,int(options.get('page',1))); size=min(100,max(1,int(options.get('page_size',20))))
    except ValueError: raise ValueError('Некорректная пагинация') from None
    search=str(options.get('search','')).strip()[:100]
    incoming=Case(None,[(Event.kind=='incoming',1)],0)
    actor=Case(None,[(Event.kind.in_(ACTIVITY_KINDS),Event.user_key)],None)
    query=(Chat.select(Chat.id,Chat.label,Chat.kind,fn.MAX(Event.occurred_at).alias('last_activity'),
        fn.COUNT(actor.distinct()).alias('active_users'),fn.SUM(incoming).alias('messages'))
        .join(Event,JOIN.LEFT_OUTER,on=((Event.bot_id==Chat.bot_id)&(Event.chat_key==Chat.chat_key)&
            (Event.processed==True)&(Event.rejected==False)&(Event.occurred_at>=lower)&(Event.occurred_at<upper)))
        .where(Chat.bot_id==bot.id))
    if search: query=query.where((Chat.label.contains(search))|(Chat.id.contains(search)))
    query=query.group_by(Chat.id,Chat.label,Chat.kind)
    total=query.count()
    fields={'active_users':fn.COUNT(actor.distinct()),'messages':fn.SUM(incoming),'last_activity':fn.MAX(Event.occurred_at),'name':Chat.label}
    order=fields.get(str(options.get('sort','last_activity')),fn.MAX(Event.occurred_at))
    query=query.order_by(order.asc() if options.get('direction')=='asc' else order.desc(),Chat.id)
    items=[]
    known=not (upper<=bot.started_at and not _events(bot.id,lower,upper).exists())
    tracking=bool(bot.native_payments_seen or Source.select().where(Source.bot_id==bot.id,Source.status=='active').exists() or Payment.select().where(Payment.bot_id==bot.id).exists())
    payment_start=bot.started_at if bot.native_payments_seen else Source.select(fn.MIN(Source.verified_at)).where(Source.bot_id==bot.id,Source.verified_at.is_null(False)).scalar()
    payment_known=tracking and known and not (payment_start and upper<=payment_start)
    for row in query.paginate(page,size).dicts():
        chat=Chat.get_by_id(row['id'])
        payment=Payment.select().where(Payment.bot_id==bot.id,Payment.chat_key==chat.chat_key,
            Payment.paid_at>=lower,Payment.paid_at<upper)
        items.append({'id':row['id'],'name':row['label'] or 'Личный диалог '+row['id'][-6:],
            'type':row['kind'],'active_users':int(row['active_users'] or 0) if known else None,'messages':int(row['messages'] or 0) if known else None,
            'last_activity':row['last_activity'].isoformat()+'Z' if row['last_activity'] else None,'payments':payment.count() if payment_known else None,
            'member_count':None,'member_count_reason':'Telegram не передаёт боту полный список участников или подписчиков.'})
    return {'items':items,'page':page,'page_size':size,'total':total}
