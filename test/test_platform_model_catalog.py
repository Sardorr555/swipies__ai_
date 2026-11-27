"""Integration regression tests, executed only in the dedicated existing QA schema."""
import asyncio
import json
import secrets
import unittest
from unittest.mock import patch, AsyncMock

from api.db.db_models import DB, User, Tenant, AIModel, AIProvider, SubscriptionPlan, SubscriptionAIPolicy, UserTokenLimit, TokenUsageLog
from api.db.services.ai_policy_service import AIModelService, AIPolicyManager
from api.db.services.platform_model_catalog_service import PlatformModelCatalogService, model_capability
from api.apps.services.models_api_service import list_tenant_added_models, set_tenant_default_models
from api.db.joint_services.tenant_model_service import resolve_model_config
from api.utils.key_crypto import encrypt_api_key


class PlatformCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        assert DB.database == 'swipies_tg_analytics_stage_20261126'
        DB.create_tables([User, Tenant, AIModel, AIProvider, SubscriptionPlan, SubscriptionAIPolicy, UserTokenLimit, TokenUsageLog], safe=True)

    def setUp(self):
        self.uid = secrets.token_hex(16)
        self.provider_name = 'CatalogQA' + secrets.token_hex(4)
        self.provider = AIProvider.create(id=secrets.token_hex(16), provider_name=self.provider_name, status='active',
            api_key=encrypt_api_key('synthetic-qa-key'), is_global=True)
        User.create(id=self.uid, email=self.uid+'@catalog.invalid', access_token=secrets.token_hex(16), is_superuser=False, is_active='1', status='1')
        Tenant.create(id=self.uid, name='Catalog test', llm_id='', embd_id='', asr_id='', img2txt_id='', rerank_id='', parser_ids='')
        self.model_id = self.provider_name.lower()+'/api-only-model'
        self.plan = {'id':'plus','name':'PLUS','daily_token_limit':0,'monthly_token_limit':0,
                     'daily_request_limit':0,'monthly_request_limit':0,'requests_per_minute':0}
        self.plan_patch = patch.object(AIPolicyManager, 'get_user_plan', side_effect=lambda *a, **kw: self.plan)
        self.plan_patch.start()
        self.discover()

    def tearDown(self):
        self.plan_patch.stop()
        SubscriptionAIPolicy.delete().where(SubscriptionAIPolicy.model_id.startswith(self.provider_name.lower()+'/')).execute()
        AIModel.delete().where(AIModel.provider == self.provider_name).execute()
        AIProvider.delete().where(AIProvider.id == self.provider.id).execute()
        User.delete().where(User.id == self.uid).execute()
        Tenant.delete().where(Tenant.id == self.uid).execute()

    def discover(self):
        return PlatformModelCatalogService.sync_provider(self.provider, [{'model_name':'api-only-model','model_type':'CHAT','max_tokens':32000}])

    def grant(self, plan='plus', enabled=True):
        SubscriptionAIPolicy.update(enabled=enabled).where(SubscriptionAIPolicy.plan_id == plan, SubscriptionAIPolicy.model_id == self.model_id).execute()

    def available(self):
        ok, models = list_tenant_added_models(self.uid, 'chat')
        self.assertTrue(ok)
        return {m['model_id'] for m in models}

    def test_api_catalog_does_not_require_tenant_installation(self):
        self.grant()
        self.assertIn(self.model_id, self.available())

    def test_plus_and_pro_have_independent_access(self):
        self.grant('pro')
        self.assertNotIn(self.model_id, self.available())
        self.plan = {**self.plan,'id':'pro','name':'PRO'}
        self.assertIn(self.model_id, self.available())

    def test_new_catalog_model_is_not_implicitly_granted(self):
        self.assertNotIn(self.model_id, self.available())
        self.assertEqual(SubscriptionAIPolicy.select().where(SubscriptionAIPolicy.model_id == self.model_id, SubscriptionAIPolicy.enabled == True).count(), 0)

    def test_refresh_preserves_kill_switch_pricing_and_grants(self):
        self.grant('plus')
        AIModel.update(enabled=False, status='disabled', input_token_price=7.25).where(AIModel.id == self.model_id).execute()
        self.discover()
        model=AIModel.get_by_id(self.model_id)
        self.assertFalse(model.enabled)
        self.assertEqual(model.status,'disabled')
        self.assertEqual(model.input_token_price,7.25)
        self.assertTrue(SubscriptionAIPolicy.get(SubscriptionAIPolicy.model_id == self.model_id, SubscriptionAIPolicy.plan_id == 'plus').enabled)

    def test_admin_catalog_includes_disabled_models(self):
        AIModel.update(enabled=False,status='disabled').where(AIModel.id == self.model_id).execute()
        self.assertIn(self.model_id,{m['id'] for m in AIModelService.get_platform_models(include_disabled=True)})
        self.assertNotIn(self.model_id,{m['id'] for m in AIModelService.get_platform_models()})

    def test_catalog_never_returns_credentials(self):
        row=next(m for m in AIModelService.get_platform_models() if m['id'] == self.model_id)
        self.assertNotIn('api_key',row)
        self.assertNotIn('synthetic-qa-key',json.dumps(row))

    def test_missing_plan_policy_is_denied(self):
        SubscriptionAIPolicy.delete().where(SubscriptionAIPolicy.model_id == self.model_id).execute()
        allowed,_,_,code=AIPolicyManager.check_model_access_extended(self.uid,self.model_id,check_quotas=False)
        self.assertFalse(allowed)
        self.assertEqual(code,'PLAN_RESTRICTED')

    def test_disabled_policy_overrides_plan_default(self):
        self.plan['default_llm_id']=self.model_id
        self.assertNotIn(self.model_id,self.available())

    def test_api_only_model_can_be_selected_as_default(self):
        self.grant()
        ok,_=set_tenant_default_models(self.uid,'','','','chat',self.model_id)
        self.assertTrue(ok)
        self.assertEqual(Tenant.get_by_id(self.uid).tenant_llm_id,self.model_id)

    def test_api_only_composite_default_selection(self):
        self.grant()
        ok,_=set_tenant_default_models(self.uid,self.provider_name,'default','api-only-model','chat')
        self.assertTrue(ok)
        self.assertEqual(Tenant.get_by_id(self.uid).tenant_llm_id,self.model_id)

    def test_runtime_uses_subscription_default_for_new_tenant(self):
        from api.db.joint_services.tenant_model_service import get_tenant_default_model_by_type
        from api.db.services.global_instance_service import GlobalInstanceService
        self.grant()
        self.plan['default_llm_id']=self.model_id
        with patch.object(GlobalInstanceService,'get_instance_stats',return_value={}):
            config=get_tenant_default_model_by_type(self.uid,'chat')
        self.assertEqual(config['llm_name'],'api-only-model')
        self.assertEqual(config['api_key'],'synthetic-qa-key')

    def test_denied_selection_does_not_change_default(self):
        ok,_=set_tenant_default_models(self.uid,'','','','chat',self.model_id)
        self.assertFalse(ok)
        self.assertFalse(Tenant.get_by_id(self.uid).tenant_llm_id)

    def test_denied_id_cannot_fall_back_to_provider_credentials(self):
        with self.assertRaises(PermissionError):
            resolve_model_config(self.uid,'chat',self.model_id)

    def test_denied_composite_cannot_bypass_plan(self):
        with self.assertRaises(PermissionError):
            resolve_model_config(self.uid,'chat',f'api-only-model@default@{self.provider_name}')

    def test_unpublished_model_cannot_use_global_provider_key(self):
        with self.assertRaises(PermissionError):
            resolve_model_config(self.uid,'chat',f'unpublished-model@default@{self.provider_name}')

    def test_model_capabilities_do_not_offer_audio_or_images_as_chat(self):
        for name,expected in [('gpt-image-1','IMAGE_GENERATION'),('gpt-4o-mini-tts','TTS'),
                              ('gpt-4o-transcribe','SPEECH2TEXT'),('gpt-realtime','REALTIME'),
                              ('text-embedding-3-small','EMBEDDING'),('gpt-4.1','CHAT')]:
            self.assertEqual(model_capability(name),expected)

    def test_downgrade_removes_pro_model_from_picker(self):
        self.grant('pro')
        self.plan={**self.plan,'id':'pro','name':'PRO'}
        self.assertIn(self.model_id,self.available())
        self.plan={**self.plan,'id':'plus','name':'PLUS'}
        self.assertNotIn(self.model_id,self.available())

    def test_explicit_user_allow_override_is_preserved(self):
        UserTokenLimit.create(user_id=self.uid,enabled=True,extra={'model_overrides':{self.model_id:{'access_type':'ALLOW','enabled':True}}})
        try:
            self.assertIn(self.model_id,self.available())
        finally:
            UserTokenLimit.delete().where(UserTokenLimit.user_id == self.uid).execute()

    def test_admin_policy_update_changes_picker_without_duplicate_rows(self):
        from api.apps import app
        SubscriptionAIPolicy.create(id=secrets.token_hex(16), plan_id='plus', model_id=self.model_id, enabled=True)
        User.update(is_superuser=True).where(User.id == self.uid).execute()
        async def update():
            client=app.test_client()
            response=await client.put('/v1/admin/ai/policies',headers={'Authorization':User.get_by_id(self.uid).get_id()},
                json={'plan_id':'plus','policies':[{'model_id':self.model_id,'enabled':False}]})
            self.assertEqual((await response.get_json())['code'],0)
        asyncio.run(update())
        User.update(is_superuser=False).where(User.id == self.uid).execute()
        self.assertEqual(SubscriptionAIPolicy.select().where(SubscriptionAIPolicy.model_id == self.model_id, SubscriptionAIPolicy.plan_id == 'plus').count(),2)
        self.assertNotIn(self.model_id,self.available())

    def test_ordinary_user_cannot_sync_platform_catalog(self):
        from api.apps import app
        async def run():
            response=await app.test_client().post('/v1/admin/ai/models/sync',headers={'Authorization':User.get_by_id(self.uid).get_id()},json={})
            self.assertNotEqual((await response.get_json())['code'],0)
        with patch.object(PlatformModelCatalogService,'refresh',new_callable=AsyncMock) as refresh:
            asyncio.run(run())
            refresh.assert_not_awaited()

    def test_admin_model_assignment_does_not_grant_other_plans(self):
        from api.apps import app
        User.update(is_superuser=True).where(User.id == self.uid).execute()
        async def run():
            response=await app.test_client().post('/v1/admin/ai/models',headers={'Authorization':User.get_by_id(self.uid).get_id()},
                json={'provider':self.provider_name,'model_name':'new-pro-only','allowed_plans':['pro']})
            self.assertEqual((await response.get_json())['code'],0)
        asyncio.run(run())
        rows=list(SubscriptionAIPolicy.select().where(SubscriptionAIPolicy.model_id == self.provider_name.lower()+'/new-pro-only'))
        self.assertEqual({r.plan_id for r in rows if r.enabled},{'pro'})

    def test_quota_does_not_hide_models_but_blocks_inference(self):
        self.grant()
        self.plan['monthly_token_limit']=1
        with patch.object(AIPolicyManager,'get_tenant_total_tokens_used',return_value=2):
            self.assertIn(self.model_id,self.available())
            self.assertEqual(AIPolicyManager.check_model_access_extended(self.uid,self.model_id)[3],'QUOTA_EXCEEDED')

    def test_paginated_provider_catalog_includes_every_page(self):
        from requests import Response
        from api.db.services.ai_provider_service import _catalog_response
        def response(body):
            result=Response(); result.status_code=200; result._content=json.dumps(body).encode(); return result
        pages=[response({'data':[{'id':'one'}],'has_more':True,'last_id':'one'}),
               response({'data':[{'id':'two'}],'has_more':False,'last_id':'two'})]
        with patch('api.db.services.ai_provider_service.requests.get',side_effect=pages) as request:
            result=asyncio.run(_catalog_response('https://api.example.test/models',{'x-api-key':'synthetic'},'data','last_id','after_id'))
            self.assertEqual([m['id'] for m in result.json()['data']],['one','two'])
            self.assertEqual(request.call_args.kwargs['params'],{'after_id':'one'})

    def test_refresh_does_not_return_provider_exception_or_key(self):
        from api.db.services.ai_provider_service import AIProviderService
        with patch.object(AIProviderService,'async_discover_live_provider_models',side_effect=RuntimeError('synthetic-qa-key')):
            result=asyncio.run(PlatformModelCatalogService.refresh(self.provider_name))
        self.assertFalse(result[0]['success'])
        self.assertNotIn('synthetic-qa-key',json.dumps(result))
