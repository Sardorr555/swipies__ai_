"""Runs inside the disposable gVisor container; contains no platform secrets."""
import base64
import json
import os
import resource
from pathlib import Path

resource.setrlimit(resource.RLIMIT_FSIZE,(10*1024*1024,10*1024*1024))
resource.setrlimit(resource.RLIMIT_NOFILE,(64,64))
Path('/workspace/artifacts').mkdir(exist_ok=True)
payload = json.loads(Path('/workspace/input.json').read_text())
namespace = {'__name__':'codeexec_user','__file__':'/workspace/main.py'}
exec(compile(payload['code'],'/workspace/main.py','exec'),namespace)
result = namespace['main'](**payload.get('arguments',{}))
encoded = base64.b64encode(json.dumps({'present':True,'value':result,'type':'json'},ensure_ascii=False).encode()).decode()
print('__RAGFLOW_RESULT__:'+encoded,flush=True)
