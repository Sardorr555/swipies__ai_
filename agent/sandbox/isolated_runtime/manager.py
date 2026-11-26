"""Authenticated controller, isolated from the platform. Fresh gVisor per run."""
import base64
import hmac
import json
import os
import socket
import ipaddress
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import docker

CLIENT = docker.from_env(timeout=8)
IMAGE = os.environ.get('CODEEXEC_IMAGE','swipies-codeexec:2026-11-22')
TOKEN = os.environ['CODEEXEC_MANAGER_TOKEN']
GLOBAL = threading.BoundedSemaphore(3)
LOCK = threading.Lock()
ACTIVE = {}
MAX_INPUT = 16*1024*1024
MAX_OUTPUT = 2*1024*1024

def run(payload):
    tenant = str(payload.get('tenant_id') or '')
    if not tenant or len(tenant)>128: raise ValueError('Invalid account context')
    if payload.get('language','python') not in ('python','python3'):
        raise ValueError('This isolated runtime supports Python only')
    code = base64.b64decode(payload['code_b64'],validate=True).decode()
    if len(code)>262144: raise ValueError('Code exceeds 256 KiB')
    timeout = min(30,max(1,int(payload.get('timeout',30))))
    if not GLOBAL.acquire(blocking=False): raise BlockingIOError('CodeExec is busy; retry later')
    with LOCK:
        if ACTIVE.get(tenant,0)>=2:
            GLOBAL.release()
            raise BlockingIOError('Account concurrent execution limit reached')
        ACTIVE[tenant]=ACTIVE.get(tenant,0)+1
    network = proxy = runner = None
    timer = None
    start = time.monotonic()
    expired = threading.Event()
    try:
        name='swipies-exec-'+uuid.uuid4().hex
        # A dedicated /28 per run, from the range blocked on the host INPUT chain.
        for attempt in range(8):
            slot=int(uuid.uuid4().hex[:4],16)%4096
            subnet=f'10.240.{slot//16}.{(slot%16)*16}/28'
            try:
                network=CLIENT.networks.create(name,internal=True,check_duplicate=True,
                    ipam=docker.types.IPAMConfig(pool_configs=[docker.types.IPAMPool(subnet=subnet)]),
                    labels={'swipies.codeexec':'ephemeral'})
                break
            except docker.errors.APIError:
                if attempt==7: raise
        common=dict(image=IMAGE,detach=True,user='65534:65534',read_only=True,
                    cap_drop=['ALL'],security_opt=['no-new-privileges:true'],
                    mem_limit='512m',memswap_limit='512m',nano_cpus=1000000000,
                    pids_limit=64,log_config=docker.types.LogConfig(type='none'),
                    labels={'swipies.codeexec':'ephemeral'},runtime='runsc')
        proxy=CLIENT.containers.create(name=name+'-egress',command=['python','/opt/codeexec/proxy.py'],
                    network='bridge',environment={'TELEGRAM_PUBLIC_IPS':json.dumps([
                        str(ipaddress.IPv4Address(ip)) for ip in payload.get('telegram_ips',[])[:8]
                        if ipaddress.IPv4Address(ip).is_global])},
                    **{**common,'mem_limit':'64m','memswap_limit':'64m','pids_limit':32})
        network.connect(proxy,aliases=['egress'])
        proxy.start()
        proxy.reload()
        proxy_ip=proxy.attrs['NetworkSettings']['Networks'][network.name]['IPAddress']
        runner=CLIENT.containers.create(name=name,command=['sleep','120'],network=network.name,
                    tmpfs={'/workspace':'rw,noexec,nosuid,nodev,size=64m,uid=65534,gid=65534,mode=700',
                           '/tmp':'rw,noexec,nosuid,nodev,size=16m,uid=65534,gid=65534,mode=700'},
                    working_dir='/workspace',environment={'HTTPS_PROXY':f'http://{proxy_ip}:8080',
                    'HTTP_PROXY':f'http://{proxy_ip}:8080','HOME':'/workspace','MPLCONFIGDIR':'/tmp/mpl',
                    'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1'},**common)
        def stop():
            expired.set()
            try: runner.kill()
            except Exception: pass
        timer=threading.Timer(timeout,stop)
        runner.start()
        timer.start()
        data=json.dumps({'code':code,'arguments':payload.get('arguments',{})},ensure_ascii=False).encode()
        # Docker archive writes are refused on a read-only root, even for tmpfs.
        # Transfer via a bounded stdin pipe to a trusted process inside the sandbox.
        transfer=runner.exec_run(['python','-c',
            "import sys; from pathlib import Path; Path('/workspace/input.json').write_bytes(sys.stdin.buffer.read(16777216))"],
            stdin=True,socket=True,user='65534:65534')
        stream=transfer.output
        try:
            stream._sock.settimeout(8)
            stream._sock.sendall(data)
            stream._sock.shutdown(socket.SHUT_WR)
            while stream.read(4096): pass
        finally:
            response=getattr(stream,'_response',None)
            if response is not None: response.close()
            else: stream.close()
        execution=CLIENT.api.exec_create(runner.id,['python','-u','/opt/codeexec/driver.py'],user='65534:65534',stdout=True,stderr=True)
        out,err=bytearray(),bytearray()
        for chunk in CLIENT.api.exec_start(execution['Id'],stream=True,demux=True):
            if chunk[0]: out.extend(chunk[0])
            if chunk[1]: err.extend(chunk[1])
            if len(out)+len(err)>MAX_OUTPUT:
                stop(); raise ValueError('Execution output exceeded 2 MiB')
        if expired.is_set(): raise TimeoutError('Execution timed out')
        status=CLIENT.api.exec_inspect(execution['Id'])['ExitCode']
        if status is None: raise RuntimeError('Execution failed')
        artifacts=[]
        if status==0:
            # gVisor tmpfs is intentionally invisible to Docker's host archive API.
            # The immutable collector stops all remaining user processes first.
            collector=CLIENT.api.exec_create(runner.id,['python','/opt/codeexec/collector.py'],user='65534:65534',stdout=True,stderr=True)
            collected=bytearray()
            for part in CLIENT.api.exec_start(collector['Id'],stream=True):
                collected.extend(part)
                if len(collected)>15*1024*1024: raise ValueError('Artifacts exceed 10 MiB total')
            if expired.is_set(): raise TimeoutError('Execution timed out')
            if CLIENT.api.exec_inspect(collector['Id'])['ExitCode']!=0:
                raise ValueError('Invalid artifact output')
            artifacts=json.loads(collected)
        return {'stdout':out.decode(errors='replace'),'stderr':err.decode(errors='replace'),
                'exit_code':status,'artifacts':artifacts,'status':'ok' if status==0 else 'error',
                'time_used_ms':int((time.monotonic()-start)*1000)}
    finally:
        if timer: timer.cancel()
        for container in (runner,proxy):
            if container:
                try: container.remove(force=True)
                except Exception: pass
        if network:
            try: network.remove()
            except Exception: pass
        with LOCK:
            ACTIVE[tenant]-=1
            if ACTIVE[tenant]==0: ACTIVE.pop(tenant)
        GLOBAL.release()

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def reply(self,status,body):
        data=json.dumps(body).encode()
        self.send_response(status); self.send_header('Content-Type','application/json')
        self.send_header('Content-Length',str(len(data))); self.end_headers(); self.wfile.write(data)
    def do_GET(self):
        if self.path!='/healthz': return self.reply(404,{'error':'Not found'})
        if not hmac.compare_digest(self.headers.get('Authorization',''),'Bearer '+TOKEN):
            return self.reply(401,{'error':'Unauthorized'})
        try:
            CLIENT.ping()
            ready='runsc' in CLIENT.info().get('Runtimes',{})
            CLIENT.images.get(IMAGE)
        except Exception: ready=False
        self.reply(200 if ready else 503,{'ready':ready,'isolation':'gvisor','max_concurrent':3,'timeout_seconds':30,'memory_mb':512})
    def do_POST(self):
        if not hmac.compare_digest(self.headers.get('Authorization',''),'Bearer '+TOKEN):
            return self.reply(401,{'error':'Unauthorized'})
        if self.path!='/run': return self.reply(404,{'error':'Not found'})
        try:
            size=int(self.headers.get('Content-Length','0'))
            if not 0<size<=MAX_INPUT: return self.reply(413,{'error':'Input exceeds 16 MiB'})
            self.connection.settimeout(10)
            payload=json.loads(self.rfile.read(size))
            result=run(payload)
            self.reply(200,result)
        except TimeoutError: self.reply(408,{'error':'Execution timed out after the configured limit'})
        except BlockingIOError: self.reply(429,{'error':'Concurrent execution limit reached; retry later'})
        except (ValueError,KeyError,TypeError): self.reply(400,{'error':'Invalid execution input or output limit exceeded'})
        except Exception: self.reply(503,{'error':'CodeExec runtime is temporarily unavailable'})

if __name__=='__main__':
    # This controller is the sole owner of these labels. Recover after a crash.
    for container in CLIENT.containers.list(all=True,filters={'label':'swipies.codeexec=ephemeral'}):
        container.remove(force=True)
    for network in CLIENT.networks.list(filters={'label':'swipies.codeexec=ephemeral'}):
        network.remove()
    ThreadingHTTPServer(('0.0.0.0',9385),Handler).serve_forever()
