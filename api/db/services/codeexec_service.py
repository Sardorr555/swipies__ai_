"""Account-bound execution, bounded attachments and trusted delivery boundary."""
import base64
import binascii
import json
import re
from contextlib import contextmanager
from pathlib import PurePosixPath

MAX_ATTACHMENT=10*1024*1024
MAX_ARGUMENTS=14*1024*1024

def attachment(value, filename='attachment.bin', content_type=None):
    if not isinstance(value,str) or not value.startswith('data:') or len(value)>MAX_ARGUMENTS:
        raise ValueError('Attachment must be a base64 data URI up to 10 MiB')
    try:
        header,encoded=value.split(',',1)
        if not header.endswith(';base64'): raise ValueError()
        mime=header[5:-7].lower()
        if mime not in {'image/png','image/jpeg','image/webp','application/pdf','text/plain',
                        'application/octet-stream','application/vnd.openxmlformats-officedocument.wordprocessingml.document'}:
            raise ValueError()
        raw=base64.b64decode(encoded,validate=True)
    except (ValueError,binascii.Error): raise ValueError('Invalid or unsupported attachment') from None
    if not raw or len(raw)>MAX_ATTACHMENT: raise ValueError('Attachment must be between 1 byte and 10 MiB')
    name=PurePosixPath(str(filename).replace('\\','/')).name
    name=re.sub(r'[^\w. -]','_',name)[:100] or 'attachment.bin'
    return raw,name,mime

def reserve_account_request(tenant_id):
    """Use current plan/overrides, existing usage and an atomic CodeExec counter."""
    from api.db.db_models import User, UserTokenLimit, TokenUsageLog
    from api.db.services.ai_policy_service import AIPolicyManager
    from rag.utils.redis_conn import REDIS_CONN
    from datetime import datetime, timezone
    user=User.get_or_none(User.id==tenant_id,User.status=='1')
    if not user: raise PermissionError('An active account is required')
    plan=AIPolicyManager.get_user_plan(tenant_id,tenant_id)
    override=UserTokenLimit.get_or_none(UserTokenLimit.user_id==tenant_id,UserTokenLimit.enabled==True)
    extra=(override.extra or {}) if override else {}
    if isinstance(extra,str): extra=json.loads(extra)
    if extra.get('codeexec_enabled') is False: raise PermissionError('CodeExec is disabled for this account')
    now=datetime.now(timezone.utc)
    date=AIPolicyManager.get_current_date_str(); month=AIPolicyManager.get_current_period()
    daily=int(extra.get('daily_request_limit',plan.get('daily_request_limit',500)))
    monthly=int(extra.get('monthly_request_limit',plan.get('monthly_request_limit',10000)))
    rpm=min(60,int(extra.get('requests_per_minute',plan.get('requests_per_minute',60))))
    daily_used=AIPolicyManager.get_tenant_daily_requests_used(tenant_id,date)
    monthly_used=AIPolicyManager.get_tenant_monthly_requests_used(tenant_id,month)
    token_cap=(override.monthly_token_limit if override and override.monthly_token_limit>0 else plan.get('monthly_token_limit',1000000))
    if token_cap>0 and AIPolicyManager.get_tenant_total_tokens_used(tenant_id,month)>=token_cap:
        raise PermissionError('Monthly account token limit reached')
    token_day=int(extra.get('daily_token_limit',plan.get('daily_token_limit',50000)))
    if token_day>0 and AIPolicyManager.get_tenant_daily_tokens_used(tenant_id,date)>=token_day:
        raise PermissionError('Daily account token limit reached')
    limits=[max(0,daily-daily_used) if daily>0 else 1000000000,
            max(0,monthly-monthly_used) if monthly>0 else 1000000000,max(0,rpm)]
    keys=[f'codeexec:usage:{tenant_id}:day:{date}',f'codeexec:usage:{tenant_id}:month:{month}',f'codeexec:usage:{tenant_id}:minute:{int(now.timestamp())//60}']
    script='''for i=1,3 do if tonumber(redis.call('GET',KEYS[i]) or '0') >= tonumber(ARGV[i]) then return 0 end end
    for i=1,3 do redis.call('INCR',KEYS[i]); redis.call('EXPIRE',KEYS[i],tonumber(ARGV[i+3])) end return 1'''
    # A Redis failure denies execution rather than silently bypassing quotas.
    if REDIS_CONN.REDIS.eval(script,3,*keys,*limits,172800,5356800,120)!=1:
        raise PermissionError('CodeExec account request limit reached')

def execute_for_account(tenant_id,code,arguments=None,timeout=30,language='python',telegram_delivery=None):
    if not isinstance(code,str) or not code.strip() or len(code.encode())>262144: raise ValueError('Provide Python code up to 256 KiB with main()')
    arguments=arguments or {}
    if not isinstance(arguments,dict) or len(json.dumps(arguments).encode())>MAX_ARGUMENTS:
        raise ValueError('Arguments exceed 14 MiB or are not an object')
    # Credentials are never accepted in the execution arguments or code.
    if re.search(r'\b\d{7,12}:[A-Za-z0-9_-]{25,}\b',code+json.dumps(arguments)):
        raise ValueError('Store Telegram credentials in the channel credential store')
    delivery=None
    if telegram_delivery:
        from api.db.services.telegram_delivery_service import authorized_channel
        delivery=authorized_channel(tenant_id,telegram_delivery.get('channel_id'))
    reserve_account_request(tenant_id)
    from agent.sandbox.client import execute_code
    result=execute_code(code,language,timeout,arguments,tenant_id=tenant_id)
    if result.exit_code!=0:
        # Runtime stderr is the user's code traceback, never provider diagnostics.
        return result
    if delivery:
        from api.db.services.telegram_delivery_service import deliver
        spec=result.metadata.get('result_value')
        if isinstance(spec,str):
            try: spec=json.loads(spec)
            except ValueError: spec={}
        if isinstance(spec,dict) and isinstance(spec.get('attachment_argument'),str):
            spec={**spec,'attachment':arguments.get(spec['attachment_argument'])}
        # The result does not choose a credential or recipient. Both are static owner configuration.
        outcome=deliver(delivery,str(telegram_delivery['recipient_id']),spec)
        result.metadata.update(result_present=True,result_value=outcome,result_type='json')
        result.stdout=''
    return result
