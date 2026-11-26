"""Platform-managed gVisor provider. There is no local execution fallback."""
import base64
import os
import requests
import socket
import ipaddress
from .self_managed import SelfManagedProvider
from .base import ExecutionResult
from agent.sandbox.result_protocol import extract_structured_result

class IsolatedProvider(SelfManagedProvider):
    def initialize(self, config):
        from api.utils.key_crypto import decrypt_api_key
        self.endpoint = str(config.get('endpoint','http://swipies-codeexec-manager:9385')).rstrip('/')
        self.api_token = decrypt_api_key(config.get('api_token',''))
        self.timeout = min(30,max(1,int(config.get('timeout',30))))
        self._initialized = bool(self.api_token) and self.health_check()
        return self._initialized

    def execute_code(self, *args, **kwargs):
        raise RuntimeError('CodeExec requires an authenticated account context')

    def execute_for_account(self, instance_id, code, language, timeout=30, arguments=None, tenant_id=None):
        if not self._initialized or not tenant_id:
            raise RuntimeError('CodeExec is temporarily unavailable')
        requested = min(self.timeout,max(1,int(timeout)))
        try:
            telegram_ips=sorted({a[4][0] for a in socket.getaddrinfo('api.telegram.org',443,family=socket.AF_INET,type=socket.SOCK_STREAM)
                if ipaddress.ip_address(a[4][0]).is_global})
        except OSError: telegram_ips=[]
        try:
            r = requests.post(self.endpoint+'/run',json={'code_b64':base64.b64encode(code.encode()).decode(),
                'language':language,'arguments':arguments or {},'timeout':requested,'tenant_id':tenant_id,
                'telegram_ips':telegram_ips},
                headers={'Authorization':'Bearer '+self.api_token},timeout=(5,requested+25))
        except requests.RequestException:
            raise RuntimeError('CodeExec is temporarily unavailable; retry later') from None
        if r.status_code==408: raise TimeoutError('CodeExec execution timed out')
        if r.status_code==429: raise PermissionError('CodeExec concurrent execution limit reached; retry later')
        if r.status_code==400: raise ValueError('CodeExec input, output or artifact limit exceeded')
        if r.status_code!=200: raise RuntimeError('CodeExec could not complete the execution')
        body=r.json()
        stdout,result=extract_structured_result(body.get('stdout',''))
        return ExecutionResult(stdout,body.get('stderr',''),int(body.get('exit_code',1)),body.get('time_used_ms',0)/1000,
            {'result_present':result.get('present',False),'result_value':result.get('value'),
             'result_type':result.get('type'),'artifacts':body.get('artifacts',[]),'isolation':'gvisor'})

    def get_supported_languages(self): return ['python','python3']

    def health_check(self):
        try:
            r=requests.get(self.endpoint+'/healthz',headers={'Authorization':'Bearer '+self.api_token},timeout=5)
            data=r.json()
            return r.status_code==200 and data.get('ready') is True and data.get('isolation')=='gvisor'
        except Exception: return False

    @staticmethod
    def get_config_schema():
        return {'endpoint':{'type':'string','required':True,'default':'http://swipies-codeexec-manager:9385','label':'Isolated runtime endpoint'},
                'api_token':{'type':'string','required':True,'secret':True,'label':'Runtime service credential'},
                'timeout':{'type':'integer','required':False,'default':30,'min':1,'max':30,'label':'Maximum seconds'}}
