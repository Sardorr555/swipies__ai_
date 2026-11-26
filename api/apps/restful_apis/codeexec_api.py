"""Authenticated platform CodeExec API; automatically discovered by MCP."""
import asyncio
import base64
import json
from quart import request
from api.apps import current_user, login_required
from api.utils.api_utils import get_json_result

@manager.route('/codeexec/status',methods=['GET'])
@login_required
async def codeexec_status():
    """GET /api/v1/codeexec/status. Return readiness and enforced runtime limits; no provider credentials or settings."""
    from agent.sandbox.client import get_provider_info
    info=await asyncio.to_thread(get_provider_info)
    return get_json_result(data={'ready':info.get('provider_type')=='isolated' and info.get('healthy',False),
        'languages':['python'],'timeout_seconds':30,'memory_mb':512,'max_file_bytes':10485760,
        'max_concurrent_per_account':2,'max_concurrent_platform':3,'network_allowlist':['api.telegram.org:443']})

@manager.route('/codeexec/execute',methods=['POST'])
@login_required
async def codeexec_execute():
    """POST /api/v1/codeexec/execute. JSON: {code: Python defining main(**arguments), arguments: object, timeout: 1..30}. Multipart: code, arguments (JSON), timeout, file (up to 10 MiB). Files appear in arguments.attachments as {filename,mime_type,data_uri}; return JSON-serializable value from main. Optional telegram_delivery: {channel_id,recipient_id} uses only an owned encrypted channel credential; main returns {attachment:base64 data URI, filename, caption, kind:photo|document}. Success requires exit_code=0; delivery success requires result.ok=true. Current account quotas and concurrency limits apply. No global configuration writes are exposed."""
    try:
        if request.content_length and request.content_length>16*1024*1024:
            return get_json_result(code=413,message='CodeExec input exceeds 16 MiB')
        if request.mimetype=='multipart/form-data':
            form=await request.form
            body={'code':form.get('code',''),'arguments':json.loads(form.get('arguments','{}')),'timeout':int(form.get('timeout',30))}
            uploads=await request.files
            attachments=[]; total=0
            from api.db.services.codeexec_service import attachment
            for upload in uploads.getlist('file'):
                raw=upload.read(10*1024*1024+1); total+=len(raw)
                if total>10*1024*1024: raise ValueError('Attachments exceed 10 MiB')
                uri='data:'+str(upload.mimetype or 'application/octet-stream')+';base64,'+base64.b64encode(raw).decode()
                _,name,mime=attachment(uri,upload.filename)
                attachments.append({'filename':name,'mime_type':mime,'data_uri':uri})
            if attachments: body['arguments']['attachments']=attachments
            if form.get('telegram_delivery'): body['telegram_delivery']=json.loads(form['telegram_delivery'])
        else: body=await request.get_json()
        from api.db.services.codeexec_service import execute_for_account
        result=await asyncio.to_thread(execute_for_account,current_user.id,body['code'],body.get('arguments'),
            body.get('timeout',30),body.get('language','python'),body.get('telegram_delivery'))
        return get_json_result(data={'exit_code':result.exit_code,'stdout':result.stdout,'stderr':result.stderr,
            'result':result.metadata.get('result_value'),'artifacts':result.metadata.get('artifacts',[]),
            'execution_time':result.execution_time})
    except PermissionError as error: return get_json_result(code=429,message=str(error))
    except (ValueError,KeyError,TypeError): return get_json_result(code=400,message='Invalid CodeExec input; main() and bounded attachments are required')
    except TimeoutError: return get_json_result(code=408,message='CodeExec execution timed out')
    except Exception: return get_json_result(code=503,message='CodeExec is temporarily unavailable; retry later')
