"""Load current platform settings per call; account code may use only isolation."""
import json
from api.db.services.system_settings_service import SystemSettingsService
from agent.sandbox.providers import ProviderManager

def get_provider_manager():
    from agent.sandbox.providers import (SelfManagedProvider,LocalProvider,SSHProvider,E2BProvider,
        AliyunCodeInterpreterProvider,TenkiProvider,UCloudAgentSandboxProvider)
    from agent.sandbox.providers.isolated import IsolatedProvider
    manager=ProviderManager()
    rows=SystemSettingsService.get_by_name('sandbox.provider_type')
    kind=rows[0].value if rows else 'isolated'
    rows=SystemSettingsService.get_by_name('sandbox.'+kind)
    config=json.loads(rows[0].value) if rows else {}
    cls={'isolated':IsolatedProvider,'self_managed':SelfManagedProvider,'local':LocalProvider,
         'ssh':SSHProvider,'e2b':E2BProvider,'aliyun_codeinterpreter':AliyunCodeInterpreterProvider,
         'tenki':TenkiProvider,'ucloud_agent_sandbox':UCloudAgentSandboxProvider}.get(kind)
    if cls:
        provider=cls()
        if provider.initialize(config): manager.set_provider(kind,provider)
    return manager

def reload_provider():
    pass

def execute_code(code,language='python',timeout=30,arguments=None,tenant_id=None):
    manager=get_provider_manager()
    if not manager.is_configured(): raise RuntimeError('CodeExec is temporarily unavailable; retry later')
    provider=manager.get_provider()
    if tenant_id and manager.get_provider_name()!='isolated':
        raise RuntimeError('The isolated CodeExec runtime is temporarily unavailable')
    instance=provider.create_instance(template=language)
    try:
        if manager.get_provider_name()=='isolated':
            return provider.execute_for_account(instance.instance_id,code,language,timeout,arguments,tenant_id)
        return provider.execute_code(instance.instance_id,code,language,timeout,arguments)
    finally:
        provider.destroy_instance(instance.instance_id)

def health_check(): return get_provider_info()['healthy']

def get_provider_info():
    try:
        manager=get_provider_manager()
        ready=manager.is_configured()
        return {'provider_type':manager.get_provider_name(),'configured':ready,
                'healthy':bool(ready and manager.get_provider().health_check())}
    except Exception:
        return {'provider_type':None,'configured':False,'healthy':False}
