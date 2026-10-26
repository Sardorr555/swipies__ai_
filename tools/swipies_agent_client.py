#!/usr/bin/env python3
"""Zero-UI stdio MCP bridge. Run once configured in Codex or another MCP host.

No dependencies beyond Python 3.10+. Credentials never go to stdout/stderr.
"""
import argparse
import base64
import hashlib
import json
import os
import re
from pathlib import Path
import secrets
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class HTTPFailure(RuntimeError):
    def __init__(self, status):
        self.status = status
        super().__init__(f"Swipies HTTP {status}")


def validate_url(value):
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in {"", "/"}:
        raise ValueError("Use an HTTPS server origin with no credentials, query or path")
    return value.rstrip("/")


def _windows_protect(value, decrypt=False):
    # Native DPAPI avoids dependencies on PowerShell editions/modules. No secret
    # is sent to a child process, command line, stdout or stderr.
    import ctypes
    from ctypes import wintypes
    class Blob(ctypes.Structure):
        _fields_ = [("size", wintypes.DWORD), ("data", ctypes.POINTER(ctypes.c_ubyte))]
    prefix = "dpapi:v1:"
    legacy = decrypt and not value.startswith(prefix)
    try:
        payload = (bytes.fromhex(value) if legacy else base64.b64decode(value[len(prefix):], validate=True)) if decrypt else value.encode("utf-8")
    except ValueError:
        raise RuntimeError("Invalid protected Windows credential") from None
    buffer = ctypes.create_string_buffer(payload)
    source = Blob(len(payload), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    target = Blob()
    crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    function = crypt32.CryptUnprotectData if decrypt else crypt32.CryptProtectData
    function.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
    function.restype = wintypes.BOOL
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    kernel32.LocalFree.restype = ctypes.c_void_p
    try:
        if not function(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(target)):
            raise RuntimeError("Windows credential protection failed")
        result = ctypes.string_at(target.data, target.size)
        if decrypt:
            return result.decode("utf-16-le" if legacy else "utf-8")
        return prefix + base64.b64encode(result).decode("ascii")
    finally:
        ctypes.memset(buffer, 0, len(payload))
        if target.data:
            ctypes.memset(target.data, 0, target.size)
            kernel32.LocalFree(ctypes.cast(target.data, ctypes.c_void_p))


def registration_secret(path):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.exists():
        if path.is_symlink() or not path.is_file():
            raise ValueError("Credential path must be a regular file")
        if os.name != "nt" and path.stat().st_mode & 0o077:
            raise ValueError("Credential file must have mode 0600")
        value = path.read_text(encoding="utf-8").strip()
        secret = _windows_protect(value, decrypt=True) if os.name == "nt" else value
        if not re.fullmatch(r"[A-Za-z0-9_-]{43,128}", secret):
            raise ValueError("Stored credential is invalid; refusing to replace an existing identity")
        return secret
    value = secrets.token_urlsafe(32)
    encoded = _windows_protect(value) if os.name == "nt" else value
    if not encoded:
        raise RuntimeError("Credential protection produced no data")
    # Publish only a fully written, durable file, without replacing another
    # process's identity. A network retry then reuses the same account.
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, prefix=".swipies-", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            return registration_secret(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return value


class Bridge:
    def __init__(self, url, state_file, name="Agent workspace"):
        self.url = validate_url(url)
        self.state_file = Path(state_file)
        self.name = name
        self.api_key = os.getenv("SWIPIES_API_KEY")
        self.opener = urllib.request.build_opener(NoRedirect())

    def post(self, path, data, authenticated=True):
        headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
        if authenticated:
            headers["Authorization"] = "Bearer " + self.api_key
        req = urllib.request.Request(self.url + path, json.dumps(data).encode(), headers=headers, method="POST")
        try:
            with self.opener.open(req, timeout=100) as response:
                raw = response.read(24 * 1024 * 1024 + 1)
                if len(raw) > 24 * 1024 * 1024:
                    raise ValueError("Server response too large")
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as exc:
            # Do not log response body, headers or request (could contain secrets).
            raise HTTPFailure(exc.code) from None

    def send(self, message):
        if not self.api_key:
            secret = registration_secret(self.state_file)
            for attempt in range(3):
                try:
                    data = self.post("/api/v1/agent-access/bootstrap", {"registration_secret": secret, "name": self.name}, authenticated=False)
                    break
                except HTTPFailure as exc:
                    if exc.status != 503 or attempt == 2:
                        raise
                except (urllib.error.URLError, TimeoutError):
                    if attempt == 2:
                        raise
                time.sleep(0.2 * (2 ** attempt))
            if not isinstance(data, dict) or not isinstance(data.get("api_key"), str):
                raise RuntimeError("Unexpected registration response")
            self.api_key = data["api_key"]
        return self.post("/api/v1/agent-access/mcp", message)


def main():
    # MCP stdio is UTF-8 regardless of the Windows console or inherited locale.
    for stream in (sys.stdin, sys.stdout):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="strict")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=os.getenv("SWIPIES_URL", "https://api.swipies.app"))
    parser.add_argument("--state-file")
    parser.add_argument("--name", default="Agent workspace")
    args = parser.parse_args()
    url = validate_url(args.url)
    server_id = hashlib.sha256(url.encode()).hexdigest()[:16]
    root = Path(os.getenv("LOCALAPPDATA", str(Path.home() / ".local" / "share")))
    bridge = Bridge(url, args.state_file or root / "swipies-agent" / (server_id + ".credential"), args.name)
    for line in sys.stdin:
        message = None
        try:
            if len(line) > 24 * 1024 * 1024:
                raise ValueError("Message too large")
            message = json.loads(line)
            if not isinstance(message, dict):
                raise ValueError("Expected an MCP object")
            result = bridge.send(message)
            if result is not None:
                print(json.dumps(result, ensure_ascii=False), flush=True)
        except Exception:
            if isinstance(message, dict) and "id" in message:
                # Never print exception text: it can contain network credentials.
                print(json.dumps({"jsonrpc": "2.0", "id": message["id"], "error": {"code": -32603, "message": "Swipies connection failed. Check server availability, registration settings and credentials."}}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
