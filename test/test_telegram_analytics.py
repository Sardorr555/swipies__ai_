"""Integration tests against the dedicated QA MySQL schema, never production."""
import asyncio,hashlib,hmac,io,json,secrets,time,unittest
from datetime import datetime,timedelta,timezone
from types import SimpleNamespace as NS
from unittest.mock import patch,AsyncMock
from PIL import Image

from api.db.db_models import DB,User as Account,Tenant,UserTenant,ChatChannel
from api.db.telegram_analytics_models import (TABLES,TelegramAnalyticsBot as Bot,TelegramAnalyticsConnection as Connection,
    TelegramAnalyticsUser as Audience,TelegramAnalyticsEvent as Event,TelegramAnalyticsPayment as Payment,
    TelegramAnalyticsRefund as Refund,TelegramAnalyticsShare as Share)
from api.db.services import telegram_analytics_ingest as ingest,telegram_analytics_query as query
from api.db.services import telegram_analytics_share as sharing,telegram_analytics_payments as payments
from api.channels.telegram.analytics import actor_key
from api.utils.key_crypto import encrypt_connector_config,decrypt_api_key

BASE=datetime(2026,6,1,12)
PERIOD={'period':'custom','start':'2026-06-01','end':'2026-06-03','timezone':'UTC'}

def message_update(uid=100,chat=10,mid=1,when=BASE,kind='private',charge=None,refund=False,currency='UZS',amount=10000000):
    payment=NS(currency=currency,total_amount=amount,telegram_payment_charge_id=charge) if charge else None
    msg=NS(message_id=mid,date=when,chat=NS(id=chat,type=kind,title='QA Group' if kind!='private' else None),
        from_user=NS(id=uid,is_bot=False),text=None if payment else 'PRIVATE TEXT MUST NEVER PERSIST',
        successful_payment=None if refund else payment,refunded_payment=payment if refund else None)
    return NS(update_id=mid,effective_message=msg,callback_query=None,edited_message=None)

class TelegramAnalyticsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        assert DB.database=='swipies_tg_analytics_stage_20261126','Refusing a non-QA database'
    def setUp(self):
        with DB.connection_context():
            for model in reversed(TABLES): model.delete().execute()
            ChatChannel.delete().execute(); UserTenant.delete().execute(); Account.delete().execute(); Tenant.delete().execute()
            self.owner=secrets.token_hex(16); self.admin=secrets.token_hex(16); self.member=secrets.token_hex(16); self.outsider=secrets.token_hex(16)
            for uid in [self.owner,self.admin,self.member,self.outsider]:
                Account.create(id=uid,nickname='QA',email=uid+'@analytics.invalid',access_token=secrets.token_hex(16),
                    is_active='1',status='1',is_superuser=False)
            Tenant.create(id=self.owner,name='QA organization',llm_id='',embd_id='',asr_id='',img2txt_id='',rerank_id='',parser_ids='')
            for uid,role in [(self.owner,'owner'),(self.admin,'admin'),(self.member,'normal')]:
                UserTenant.create(id=secrets.token_hex(16),user_id=uid,tenant_id=self.owner,role=role,invited_by=self.owner,status='1')
            self.channel=ChatChannel.create(id=secrets.token_hex(16),tenant_id=self.owner,name='QA bot',channel='telegram',status=1,
                config=encrypt_connector_config({'credential':{'token':'qa-placeholder-not-a-real-token'}}))
        self.meta={'id':'123456789','first_name':'ТЕСТОВЫЙ Telegram-бот','username':'swipies_qa_bot'}
        self.bot=ingest.register_bot(self.channel.id,self.meta)
        Bot.update(started_at=datetime(2026,5,1)).where(Bot.id==self.bot.id).execute()
        self.bot=Bot.get_by_id(self.bot.id)
    def event(self,**kwargs): ingest.enqueue_update(self.channel.id,self.meta,message_update(**kwargs))
    def stats(self,period=None): return query.summary(Bot.get_by_id(self.bot.id),period or PERIOD)
    def token(self,uid): return Account.get_by_id(uid).get_id()
    def share(self,**extra):
        return sharing.create(self.bot,self.owner,{**PERIOD,'title':'ТЕСТОВЫЕ ДАННЫЕ','metrics':['users_total'],'show_revenue':False,**extra})
    def test_ten_messages_are_one_user(self):
        for i in range(10): self.event(mid=i+1)
        ingest.drain(); data=self.stats()
        self.assertEqual(data['metrics']['users_total'],1); self.assertEqual(data['metrics']['messages_in'],10)
    def test_same_user_across_groups_counted_once(self):
        self.event(mid=1,chat=-10,kind='group'); self.event(mid=2,chat=-20,kind='supergroup')
        ingest.drain(); self.assertEqual(self.stats()['metrics']['users_active'],1)
        chats=query.chat_table(self.bot,PERIOD)
        self.assertEqual(chats['total'],2); self.assertEqual([r['active_users'] for r in chats['items']],[1,1])
    def test_duplicate_updates_do_not_duplicate_messages(self):
        self.event(); self.event(); ingest.drain(); ingest.drain()
        self.assertEqual(self.stats()['metrics']['messages_in'],1)
    def test_no_message_text_or_raw_user_id_in_ledger(self):
        self.event(uid=987654321); ingest.drain()
        payload=json.dumps(list(Event.select().dicts()),default=str)
        self.assertNotIn('PRIVATE TEXT',payload); self.assertNotIn('987654321',payload)
    def test_three_purchases_one_payer(self):
        for charge in ['charge-a','charge-b','charge-c']: self.event(charge=charge)
        ingest.drain(); paid=self.stats()['payments_period']
        self.assertEqual((paid['payers'],paid['payments']),(1,3)); self.assertEqual(paid['currencies'][0]['amount'],'300000.00')
    def test_duplicate_payment_charge_not_recounted(self):
        self.event(charge='same',mid=1); self.event(charge='same',mid=2)
        ingest.drain(); self.assertEqual(self.stats()['payments_period']['payments'],1)
    def test_refund_is_separate_and_idempotent(self):
        self.event(charge='paid'); self.event(charge='paid',refund=True,mid=2); self.event(charge='paid',refund=True,mid=3)
        ingest.drain(); currency=self.stats()['payments_period']['currencies'][0]
        self.assertEqual(currency['amount'],'100000.00'); self.assertEqual(currency['refund_amount'],'100000.00')
        self.assertEqual(Refund.select().count(),1)
    def test_verified_native_refund_without_old_payment_is_not_zero(self):
        self.event(charge='historical',refund=True)
        ingest.drain(); currency=self.stats()['payments_period']['currencies'][0]
        self.assertEqual(currency['refund_amount'],'100000.00'); self.assertEqual(currency['payments'],0)
    def test_currencies_and_stars_never_added_together(self):
        for charge,currency,amount in [('a','UZS',10000000),('b','USD',1025),('c','XTR',7)]:
            self.event(charge=charge,currency=currency,amount=amount)
        ingest.drain(); currencies={r['currency']:r['amount'] for r in self.stats()['payments_period']['currencies']}
        self.assertEqual(currencies,{'USD':'10.25','UZS':'100000.00','XTR':'7'})
    def test_payment_unconfigured_is_unknown(self):
        self.event(); ingest.drain(); data=self.stats()
        self.assertEqual(data['payment_tracking'],'not_connected'); self.assertIsNone(data['payments_period']); self.assertIsNone(data['payments_all_time'])
    def test_timezone_boundaries_and_first_seen(self):
        self.event(mid=1,when=datetime(2026,6,1,18,59)); self.event(mid=2,when=datetime(2026,6,1,19,1))
        ingest.drain(); period={**PERIOD,'timezone':'Asia/Tashkent','end':'2026-06-02'}
        data=self.stats(period); a,b=data['series']
        self.assertEqual((a['messages_in'],b['messages_in']),(1,1)); self.assertEqual((a['users_new'],b['users_new']),(1,0))
    def test_dst_day_is_23_hours(self):
        _,a,b,_=query.period_range({'period':'custom','start':'2026-03-29','end':'2026-03-29','timezone':'Europe/Berlin'},datetime(2026,11,26,tzinfo=timezone.utc))
        self.assertEqual(b-a,timedelta(hours=23))
    def test_before_collection_is_not_zero(self):
        data=self.stats({'period':'custom','start':'2026-01-01','end':'2026-01-01','timezone':'UTC'})
        self.assertEqual(data['coverage'],'unavailable'); self.assertIsNone(data['metrics']['users_active'])
    def test_out_of_order_events_correct_first_seen(self):
        self.event(mid=2,when=BASE+timedelta(days=1)); ingest.drain()
        self.event(mid=1,when=BASE); ingest.drain()
        self.assertEqual(Audience.get().first_seen,BASE)
    def test_connection_rebind_keeps_bot_analytics(self):
        self.event(); ingest.drain()
        ChatChannel.update(agent_id='new-agent',chat_id=None).where(ChatChannel.id==self.channel.id).execute()
        self.assertEqual(self.stats()['metrics']['users_total'],1)
    def test_replacing_bot_does_not_merge_audience(self):
        self.event(); ingest.drain()
        other=ingest.register_bot(self.channel.id,{**self.meta,'id':'987654321'})
        self.assertNotEqual(other.id,self.bot.id)
        self.assertEqual(query.current_bot(ChatChannel.get_by_id(self.channel.id)).id,other.id)
        ingest.register_bot(self.channel.id,self.meta)
        self.assertEqual(query.current_bot(ChatChannel.get_by_id(self.channel.id)).id,self.bot.id)
    def test_owner_and_org_admin_allowed_normal_member_denied(self):
        query.channel_for_user(self.channel.id,self.owner); query.channel_for_user(self.channel.id,self.admin)
        for uid in [self.member,self.outsider]:
            with self.assertRaises(PermissionError): query.channel_for_user(self.channel.id,uid)
    def test_public_projection_contains_only_allowed_metrics(self):
        self.event(charge='secret-money'); ingest.drain(); share=self.share()
        value=sharing.public_data(share['token']); text=json.dumps(value)
        self.assertEqual(set(value['metrics']),{'users_total'})
        for word in ['payments_period','amount_minor','chat_key','user_key','tenant_id','secret_ciphertext','telegram_bot_id','100000.00']:
            self.assertNotIn(word,text)
    def test_share_secret_is_hashed_and_not_listed(self):
        share=self.share(); stored=Share.get_by_id(share['id'])
        self.assertNotEqual(stored.token_hash,share['token']); self.assertNotIn(share['token'],json.dumps(sharing.list_shares(self.bot)))
    def test_revoke_and_expiry_deny_future_reads(self):
        share=self.share(); Share.update(revoked_at=datetime.utcnow()).where(Share.id==share['id']).execute()
        with self.assertRaises(sharing.ShareUnavailable): sharing.public_data(share['token'])
        share=self.share(); Share.update(expires_at=datetime(2020,1,1)).where(Share.id==share['id']).execute()
        with self.assertRaises(sharing.ShareUnavailable): sharing.public_data(share['token'])
    def test_hidden_revenue_removed_even_when_selected(self):
        share=self.share(metrics=['users_total','revenue','refunds'],show_revenue=False)
        self.assertEqual(share['settings']['metrics'],['users_total'])
    def test_chat_search_sort_and_pagination(self):
        for i in range(3): self.event(uid=100+i,chat=-10-i,kind='group',mid=i+1)
        ingest.drain(); result=query.chat_table(self.bot,{**PERIOD,'search':'QA','page_size':1,'page':2,'sort':'messages'})
        self.assertEqual(result['total'],3); self.assertEqual(len(result['items']),1); self.assertIsNone(result['items'][0]['member_count'])
    def test_successful_bot_reply_only_recorded_once(self):
        message=message_update().effective_message
        ingest.enqueue_reply(self.channel.id,self.meta,message); ingest.enqueue_reply(self.channel.id,self.meta,message)
        ingest.drain(); self.assertEqual(self.stats()['metrics']['messages_out'],1)
    def test_events_persist_between_connections(self):
        self.event(); DB.close(); DB.connect(reuse_if_open=True)
        self.assertEqual(Event.select().where(Event.processed==False).count(),1)
        ingest.drain(); self.assertEqual(self.stats()['metrics']['users_total'],1)
    def test_callback_interaction_not_counted_as_message(self):
        update=message_update(); update.callback_query=NS(id='callback-1',from_user=NS(id=100,is_bot=False))
        ingest.enqueue_update(self.channel.id,self.meta,update); ingest.drain()
        data=self.stats({'period':'today','timezone':'UTC'})['metrics']; self.assertEqual(data['users_active'],1); self.assertEqual(data['messages_in'],0)
    def test_redis_fallback_recovers_without_message_text(self):
        from api.channels.telegram import analytics_spool as spool
        from rag.utils.redis_conn import REDIS_CONN
        suffix=secrets.token_hex(8); ready='qa:tg-analytics:ready:'+suffix; inflight='qa:tg-analytics:inflight:'+suffix
        with patch.object(spool,'READY',ready),patch.object(spool,'INFLIGHT',inflight),patch.object(spool,'LOCK_KEY',ready+':lock'):
            try:
                spool.put('update',self.channel.id,self.meta,message_update())
                sealed=REDIS_CONN.REDIS.lindex(ready,0)
                text=sealed.decode() if isinstance(sealed,bytes) else sealed
                raw=decrypt_api_key(text); self.assertNotIn('PRIVATE TEXT',raw)
                self.assertTrue(text.startswith('enc:v2:'))
                spool.drain(); ingest.drain()
                self.assertEqual(self.stats()['metrics']['messages_in'],1)
                self.assertEqual(REDIS_CONN.REDIS.llen(inflight),0)
            finally: REDIS_CONN.REDIS.delete(ready,inflight,ready+':lock')
    def test_platform_subscription_orders_are_not_a_source(self):
        # No subscription table can contribute to bot aggregates. Owner actions
        # and invoice-like user text remain ordinary messages.
        update=message_update(); update.effective_message.text='Оплатил подписку Swipies 40 USD'
        ingest.enqueue_update(self.channel.id,self.meta,update); ingest.drain()
        self.assertEqual(Payment.select().count(),0); self.assertEqual(self.stats()['payment_tracking'],'not_connected')
    def test_failed_send_not_counted_as_reply(self):
        from api.channels.telegram.channel import TelegramChannel,TelegramAccount
        channel=TelegramChannel(TelegramAccount(account_id=self.channel.id,token='qa-placeholder'))
        channel._app=NS(bot=NS(send_message=AsyncMock(side_effect=RuntimeError('synthetic failure'))))
        with self.assertRaises(RuntimeError): asyncio.run(channel._send_message(chat_id=10,text='test'))
        self.assertEqual(Event.select().where(Event.kind=='outgoing').count(),0)
    def signed_source(self):
        source=payments.source_create(self.bot,{'name':'QA provider','secret':'q'*40})
        raw=json.dumps({'type':'verification'}).encode(); stamp=str(int(time.time()))
        signature=hmac.new(b'q'*40,stamp.encode()+b'.'+raw,hashlib.sha256).hexdigest()
        payments.notification(source['id'],raw,stamp,signature)
        return source
    def notify(self,source,body):
        raw=json.dumps(body).encode(); stamp=str(int(time.time()))
        signature=hmac.new(b'q'*40,stamp.encode()+b'.'+raw,hashlib.sha256).hexdigest()
        return payments.notification(source['id'],raw,stamp,signature)
    def test_external_source_requires_verification_and_server_order(self):
        self.event(); ingest.drain(); source=self.signed_source()
        order=payments.order_create(self.bot,{'source_id':source['id'],'telegram_user_id':'100','telegram_chat_id':'10','currency':'USD','amount_minor':1000})
        self.assertEqual(self.stats({'period':'today','timezone':'UTC'})['payments_period']['payments'],0)
        body={'type':'payment_succeeded','event_id':'evt1','order_id':order['id'],'transaction_id':'tx1','currency':'USD','amount_minor':1000}
        self.notify(source,body); self.notify(source,body); ingest.drain()
        self.assertEqual(self.stats({'period':'today','timezone':'UTC'})['payments_period']['payments'],1)
        self.notify(source,{**body,'event_id':'refund1','type':'refund_succeeded','amount_minor':300}); ingest.drain()
        self.assertEqual(self.stats({'period':'today','timezone':'UTC'})['payments_period']['currencies'][0]['refund_amount'],'3.00')
    def test_external_signature_and_wrong_order_amount_rejected(self):
        source=self.signed_source()
        with self.assertRaises(PermissionError): payments.notification(source['id'],b'{}',str(int(time.time())),'wrong')
        with self.assertRaises(PermissionError): payments.notification(source['id'],b'{}','1','wrong')
        self.event(); ingest.drain()
        order=payments.order_create(self.bot,{'source_id':source['id'],'telegram_user_id':'100','currency':'USD','amount_minor':1000})
        with self.assertRaises(ValueError): self.notify(source,{'type':'payment_succeeded','event_id':'e','order_id':order['id'],'transaction_id':'t','currency':'USD','amount_minor':2000})
    def test_before_external_source_connection_is_unknown_not_zero(self):
        self.signed_source()
        self.assertIsNone(self.stats()['payments_period'])
        self.assertEqual(self.stats()['payment_coverage'],'unavailable')
    def test_conversion_uses_same_period_cohort(self):
        self.event(uid=100,mid=1); self.event(uid=200,mid=2); self.event(uid=100,charge='p')
        ingest.drain(); data=self.stats()
        self.assertEqual(data['conversion']['percent'],50.0)
    def test_external_order_cannot_be_paid_twice_and_refunds_are_capped(self):
        self.event(); ingest.drain(); source=self.signed_source()
        order=payments.order_create(self.bot,{'source_id':source['id'],'telegram_user_id':'100','currency':'USD','amount_minor':1000})
        body={'type':'payment_succeeded','event_id':'pay1','order_id':order['id'],'transaction_id':'tx1','currency':'USD','amount_minor':1000}
        self.notify(source,body); ingest.drain()
        self.notify(source,{**body,'event_id':'pay2','transaction_id':'tx2'}); ingest.drain()
        self.assertEqual(Payment.select().count(),1)
        for identifier in ['refund1','refund2']:
            self.notify(source,{**body,'type':'refund_succeeded','event_id':identifier,'amount_minor':600}); ingest.drain()
        self.assertEqual(self.stats({'period':'today','timezone':'UTC'})['payments_period']['currencies'][0]['refund_amount'],'6.00')
    def test_migration_is_dry_run_and_idempotent(self):
        from api.scripts.migrate_telegram_analytics import migrate
        before=set(DB.get_tables()); result=migrate()
        self.assertEqual(result['mode'],'dry-run'); self.assertEqual(before,set(DB.get_tables()))
        self.assertEqual(migrate(True)['tables_to_create'],[])
    def test_public_http_rejects_oversized_and_nonobject_bodies(self):
        from api.apps import app
        async def run():
            client=app.test_client()
            response=await client.post('/api/v1/telegram-analytics/public',data=b'x'*65537)
            self.assertEqual(response.status_code,413)
            response=await client.post('/api/v1/telegram-analytics/public',json=[])
            self.assertEqual(response.status_code,400)
        asyncio.run(run())
    def test_png_exact_dimensions(self):
        from api.db.services.telegram_analytics_export import render_png
        self.event(); ingest.drain()
        settings=sharing.validate_settings({**PERIOD,'metrics':list(query.METRICS),'show_revenue':True})
        data=sharing.project(self.stats(),settings,'ТЕСТОВЫЕ ДАННЫЕ')
        for shape,size in [('square',(1080,1080)),('story',(1080,1920))]:
            raw=render_png(data,shape,'https://example.invalid/analytics')
            image=Image.open(io.BytesIO(raw)); self.assertEqual(image.size,size); self.assertEqual(image.format,'PNG')
    def test_private_and_public_http_permissions_and_cache(self):
        from api.apps import app
        self.event(); ingest.drain(); share=self.share()
        async def run():
            client=app.test_client(); path=f'/api/v1/chat-channels/{self.channel.id}/analytics'
            for uid,status in [(self.owner,200),(self.admin,200),(self.member,403),(self.outsider,403)]:
                response=await client.get(path,headers={'Authorization':self.token(uid)},query_string=PERIOD)
                self.assertEqual(response.status_code,status,await response.get_json())
            public=await client.post('/api/v1/telegram-analytics/public',json={'token':share['token']})
            self.assertEqual(public.status_code,200,await public.get_json())
            self.assertIn('no-store',public.headers['Cache-Control']); self.assertIn('noindex',public.headers['X-Robots-Tag'])
            revoked=await client.delete(f'/api/v1/chat-channels/{self.channel.id}/analytics/shares/{share["id"]}',headers={'Authorization':self.token(self.owner)})
            self.assertEqual(revoked.status_code,200)
            public=await client.post('/api/v1/telegram-analytics/public',json={'token':share['token']})
            self.assertEqual(public.status_code,410)
        asyncio.run(run())
