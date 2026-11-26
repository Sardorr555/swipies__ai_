"""Per-run CONNECT gateway. No credentials, arbitrary destinations or logging."""
import ipaddress
import select
import socket
import socketserver
import time
import threading
import os
import json

class Proxy(socketserver.StreamRequestHandler):
    def handle(self):
        self.connection.settimeout(5)
        line = self.rfile.readline(4096)
        total = len(line)
        while True:
            h = self.rfile.readline(4096)
            total += len(h)
            if not h or h == b'\r\n' or total > 16384:
                break
        if total > 16384 or line not in (b'CONNECT api.telegram.org:443 HTTP/1.0\r\n', b'CONNECT api.telegram.org:443 HTTP/1.1\r\n'):
            self.wfile.write(b'HTTP/1.1 403 Forbidden\r\nContent-Length: 0\r\n\r\n')
            return
        # The trusted platform resolves the fixed host before dispatch. gVisor's
        # internal network deliberately has no external DNS forwarding.
        public = [ip for ip in json.loads(os.environ.get('TELEGRAM_PUBLIC_IPS','[]'))
                  if ipaddress.IPv4Address(ip).is_global]
        if not public:
            return
        with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as remote:
            remote.settimeout(5)
            remote.connect((public[0],443))
            self.wfile.write(b'HTTP/1.1 200 Connection Established\r\n\r\n')
            self.wfile.flush()
            deadline, transferred = time.monotonic()+30, 0
            while time.monotonic() < deadline:
                readable, _, _ = select.select([remote,self.connection],[],[],1)
                for source in readable:
                    buf = source.recv(65536)
                    if not buf: return
                    transferred += len(buf)
                    if transferred > 16*1024*1024: return
                    (remote if source is self.connection else self.connection).sendall(buf)

class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

if __name__ == '__main__':
    # A controller crash must not leave an indefinitely running egress process.
    threading.Timer(90,lambda:os._exit(0)).start()
    Server(('0.0.0.0',8080),Proxy).serve_forever()
