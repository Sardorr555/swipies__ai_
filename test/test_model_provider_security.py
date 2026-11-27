"""Integration checks in the existing dedicated QA schema; no extra containers."""
import sys,logging,unittest,asyncio,json,secrets
from unittest.mock import patch
# Run only against the dedicated QA schema in an initialized environment.
logging.disable(logging.CRITICAL)
from common.config_utils import CONFIGS
STAGE_DB='swipies_tg_analytics_stage_20261126'; CONFIGS['mysql']['name']=STAGE_DB
from common import settings
settings.DATABASE['name']=STAGE_DB
from api.apps import app
from api.db.db_models import (DB,User,Tenant,UserTenant,TenantModelProvider,TenantModelInstance,TenantModel,AIProvider,AIModel)
assert DB.database==STAGE_DB
from api.apps.services import provider_api_service as providers,models_api_service as models
from api.db.services.tenant_model_provider_service import TenantModelProviderService as PS
import api.db.services.tenant_model_provider_service as ps_module
from api.db.joint_services import tenant_model_service as runtime
from api.db.services.ai_policy_service import AIPolicyManager
from api.utils.key_crypto import encrypt_api_key

class MainHotfixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        DB.create_tables([User,Tenant,UserTenant,TenantModelProvider,TenantModelInstance,TenantModel,AIProvider,AIModel],safe=True)
    def setUp(self):
        self.owner=secrets.token_hex(16); self.normal=secrets.token_hex(16); self.stranger=secrets.token_hex(16)
        for uid,admin in [(self.owner,True),(self.normal,False),(self.stranger,False)]:
            User.create(id=uid,email=uid+'@hotfix.invalid',nickname='QA',access_token=secrets.token_hex(16),is_superuser=admin,is_active='1',status='1')
            Tenant.create(id=uid,name='QA',llm_id='',embd_id='',asr_id='',img2txt_id='',rerank_id='',parser_ids='')
        self.factory='OpenAI'
        self.platform=TenantModelProvider.create(id=secrets.token_hex(16),tenant_id=self.owner,provider_name=self.factory)
        self.own=TenantModelProvider.create(id=secrets.token_hex(16),tenant_id=self.normal,provider_name='DeepSeek')
        self.instance=TenantModelInstance.create(id=secrets.token_hex(16),provider_id=self.platform.id,instance_name='default',api_key='qa-platform-secret',extra='{}',status='1')
        self.personal=TenantModelInstance.create(id=secrets.token_hex(16),provider_id=self.own.id,instance_name='default',api_key='qa-personal-secret',extra='{}',status='1')
        self.model=AIModel.create(id='qa/'+secrets.token_hex(8),provider='OpenAI',model_name='qa-'+secrets.token_hex(5),model_type='CHAT',api_key=encrypt_api_key('qa-platform-secret'),enabled=True,is_global=True,status='active')
        self.legacy=TenantModel.create(id=secrets.token_hex(16),provider_id=self.platform.id,instance_id=self.instance.id,model_name=self.model.model_name,model_type=1,extra='{}',status='1')
        self.cache=patch.object(ps_module,'_ADMIN_TENANT_ID_CACHE',self.owner); self.cache.start()
        self.policy=patch.object(AIPolicyManager,'check_model_access',return_value=(True,'OK',200)); self.policy.start()
        self.catalog_policy=patch.object(AIPolicyManager,'check_model_access_extended',return_value=(True,'OK',200,'OK')); self.catalog_policy.start()
    def tearDown(self):
        self.policy.stop(); self.catalog_policy.stop(); self.cache.stop()
        AIModel.delete().where(AIModel.id==self.model.id).execute()
        TenantModel.delete().where(TenantModel.provider_id.in_([self.platform.id,self.own.id])).execute()
        TenantModelInstance.delete().where(TenantModelInstance.provider_id.in_([self.platform.id,self.own.id])).execute()
        TenantModelProvider.delete().where(TenantModelProvider.id.in_([self.platform.id,self.own.id])).execute()
        User.delete().where(User.id.in_([self.owner,self.normal,self.stranger])).execute()
        Tenant.delete().where(Tenant.id.in_([self.owner,self.normal,self.stranger])).execute()
    def test_platform_key_denied_by_name_and_id(self):
        for identifier in [self.factory,self.platform.id]:
            ok,result=providers.show_provider_instance(self.normal,identifier,self.instance.id)
            self.assertFalse(ok); self.assertNotIn('qa-platform-secret',str(result))
    def test_platform_instances_not_exposed(self):
        self.assertFalse(providers.list_provider_instances(self.normal,self.platform.id)[0])
    def test_platform_delete_cannot_modify_admin(self):
        self.assertFalse(providers.delete_provider(self.normal,self.platform.id)[0])
        self.assertTrue(TenantModelInstance.get_or_none(TenantModelInstance.id==self.instance.id))
    def test_platform_update_is_denied(self):
        result=asyncio.run(providers.update_provider_instance(self.normal,self.platform.id,self.instance.id,'default','attacker-key','','',verify=False))
        self.assertFalse(result[0]); self.assertEqual(TenantModelInstance.get_by_id(self.instance.id).api_key,'qa-platform-secret')
    def test_normal_user_own_key_is_write_only(self):
        ok,result=providers.show_provider_instance(self.normal,self.own.id,self.personal.id)
        self.assertTrue(ok); self.assertEqual(result['api_key'],''); self.assertTrue(result['has_api_key'])
    def test_admin_saved_key_is_also_write_only(self):
        ok,result=providers.show_provider_instance(self.owner,self.platform.id,self.instance.id)
        self.assertTrue(ok); self.assertEqual(result['api_key'],''); self.assertTrue(result['has_api_key'])
    def test_stranger_cannot_read_personal_key(self):
        self.assertFalse(providers.show_provider_instance(self.stranger,self.own.id,self.personal.id)[0])
    def test_blank_update_preserves_server_key(self):
        result=asyncio.run(providers.update_provider_instance(self.owner,self.platform.id,self.instance.id,'default','','','',model_info=[],verify=False))
        self.assertTrue(result[0])
        self.assertEqual(TenantModelInstance.get_by_id(self.instance.id).api_key,'qa-platform-secret')
        self.assertEqual(runtime.get_model_config_by_id(self.normal,'chat',self.model.id)['api_key'],'qa-platform-secret')
    def test_admin_http_does_not_return_stored_key(self):
        async def run():
            client=app.test_client()
            response=await client.get(f'/api/v1/providers/{self.platform.id}/instances/{self.instance.id}',
                headers={'Authorization':User.get_by_id(self.owner).get_id()})
            body=await response.get_json()
            self.assertEqual(body['code'],0)
            self.assertEqual(body['data']['api_key'],'')
            self.assertNotIn('qa-platform-secret',json.dumps(body))
        asyncio.run(run())
    def test_platform_model_id_resolves_for_chat(self):
        result=runtime.get_model_config_by_id(self.normal,'chat',self.model.id)
        self.assertEqual(result['llm_name'],self.model.model_name); self.assertEqual(result['api_key'],'qa-platform-secret')
    def test_legacy_published_model_id_resolves(self):
        self.assertEqual(runtime.get_model_config_by_id(self.normal,'chat',self.legacy.id)['llm_name'],self.model.model_name)
    def test_platform_model_respects_plan_denial(self):
        with patch.object(AIPolicyManager,'check_model_access',return_value=(False,'restricted',403)):
            with self.assertRaises(PermissionError): runtime.get_model_config_by_id(self.normal,'chat',self.model.id)
    def test_platform_model_type_checked(self):
        with self.assertRaises(LookupError): runtime.get_model_config_by_id(self.normal,'embedding',self.model.id)
    def test_disabled_platform_model_rejected(self):
        AIModel.update(enabled=False).where(AIModel.id==self.model.id).execute()
        with self.assertRaises(LookupError): runtime.get_model_config_by_id(self.normal,'chat',self.model.id)
    def test_private_admin_model_not_published_rejected(self):
        TenantModel.update(model_name='private-'+secrets.token_hex(5)).where(TenantModel.id==self.legacy.id).execute()
        with self.assertRaises(LookupError): runtime.get_model_config_by_id(self.normal,'chat',self.legacy.id)
    def test_composite_and_platform_id_agree(self):
        name=runtime.get_composite_model_name_by_id(self.model.id)
        self.assertEqual(runtime.resolve_model_id(self.normal,'chat',name),self.model.id)
    def test_platform_default_has_model_id(self):
        result=models._get_model_info(self.normal,self.model.id,'chat')
        self.assertEqual(result['model_id'],self.model.id)
    def test_real_http_denies_platform_secrets(self):
        async def run():
            client=app.test_client()
            response=await client.get(f'/api/v1/providers/{self.platform.id}/instances/{self.instance.id}',headers={'Authorization':User.get_by_id(self.normal).get_id()})
            body=await response.get_json(); self.assertNotEqual(body['code'],0); self.assertNotIn('qa-platform-secret',json.dumps(body))
        asyncio.run(run())
    def test_chat_model_normalization_accepts_selected_platform_id(self):
        from api.apps.restful_apis.chat_api import _normalize_model_pair
        request={'tenant_llm_id':self.model.id,'llm_id':runtime.get_composite_model_name_by_id(self.model.id)}
        self.assertIsNone(asyncio.run(_normalize_model_pair(request,self.normal,'llm_id','tenant_llm_id','chat')))
    def test_actual_chat_creation_with_platform_model(self):
        from api.db.db_models import Dialog
        from api.db.services.user_service import TenantLimitService
        DB.create_tables([Dialog],safe=True)
        async def run():
            client=app.test_client()
            response=await client.post('/api/v1/chats',headers={'Authorization':User.get_by_id(self.normal).get_id()},
                json={'name':'QA model selection','tenant_llm_id':self.model.id,'llm_id':runtime.get_composite_model_name_by_id(self.model.id)})
            body=await response.get_json(); self.assertEqual(body['code'],0,body)
            row=Dialog.get_or_none(Dialog.tenant_id==self.normal)
            self.assertIsNotNone(row); self.assertEqual(row.tenant_llm_id,self.model.id)
            Dialog.delete().where(Dialog.tenant_id==self.normal).execute()
        with patch.object(TenantLimitService,'check_apps_limit',return_value=(True,'')):
            asyncio.run(run())

if __name__ == '__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(MainHotfixTests))
    raise SystemExit(not result.wasSuccessful())
