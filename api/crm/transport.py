#
#  Copyright 2025 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
import ipaddress
import logging
import os
import socket
from typing import Optional, Tuple
from urllib.parse import urlparse

import requests

from common.ssrf_guard import pin_dns, _effective_ip

logger = logging.getLogger(__name__)


class SSRFSecurityException(ValueError):
    """Raised when an outbound URL fails SSRF security constraints."""
    pass


def is_ip_allowed_by_cidr_list(ip_str: str, cidr_env_var: str) -> bool:
    """Check if ip_str matches any CIDR or IP in the environment variable allowlist."""
    raw = os.environ.get(cidr_env_var, "").strip()
    if not raw:
        return False
    try:
        target_ip = ipaddress.ip_address(ip_str)
        for rule in raw.split(","):
            rule = rule.strip()
            if not rule:
                continue
            if "/" in rule:
                if target_ip in ipaddress.ip_network(rule, strict=False):
                    return True
            else:
                if target_ip == ipaddress.ip_address(rule):
                    return True
    except Exception as e:
        logger.warning("Error evaluating CIDR rule %r for IP %s: %s", raw, ip_str, e)
    return False


def validate_crm_url_and_resolve(
    url: str,
    *,
    allowed_schemes: frozenset[str] = frozenset({"https"}),
    private_cidr_env: Optional[str] = None,
) -> Tuple[str, str]:
    """Validate URL safety against SSRF and return (hostname, resolved_ip).
    
    1. Enforces scheme in allowed_schemes (strictly https by default).
    2. Validates hostname exists and does not contain userinfo or credentials.
    3. Resolves all addresses; checks each address is globally routable.
    4. If private/reserved IP space is encountered, permits connection ONLY if
       explicitly included in platform administrator allowlist (e.g. RAGFLOW_CRM_PRIVATE_ALLOWLIST_CIDR).
    5. Returns (hostname, resolved_ip) for DNS pinning.
    """
    parsed = urlparse(url)
    scheme = parsed.scheme
    if scheme not in allowed_schemes:
        raise SSRFSecurityException(
            f"Disallowed URL scheme: {scheme!r}. Only {sorted(allowed_schemes)} are allowed."
        )

    hostname = parsed.hostname
    if not hostname:
        raise SSRFSecurityException(f"URL is missing hostname: {url!r}")

    if parsed.username or parsed.password:
        raise SSRFSecurityException(f"Userinfo in URL is forbidden: {url!r}")

    # Resolve all addresses
    try:
        addr_info = socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
    except socket.gaierror as e:
        raise SSRFSecurityException(f"Cannot resolve hostname {hostname!r}: {e}")

    if not addr_info:
        raise SSRFSecurityException(f"No IP addresses resolved for hostname {hostname!r}")

    resolved_ips = []
    for entry in addr_info:
        raw_ip = entry[4][0]
        ip_obj = _effective_ip(ipaddress.ip_address(raw_ip))
        resolved_ips.append((raw_ip, ip_obj))

    for raw_ip, ip_obj in resolved_ips:
        if not ip_obj.is_global:
            if private_cidr_env and is_ip_allowed_by_cidr_list(str(ip_obj), private_cidr_env):
                logger.info("Private IP %s allowed by platform allowlist %s", raw_ip, private_cidr_env)
                continue
            raise SSRFSecurityException(
                f"SSRF guard blocked access to non-global IP address {raw_ip!r} for host {hostname!r}"
            )

    return hostname, resolved_ips[0][0]


class CRMTransport:
    """Hardened HTTP transport client enforcing DNS-pinning, SSRF checks, and no-redirects."""

    def __init__(
        self,
        private_cidr_allowlist_env: Optional[str] = None,
        allowed_schemes: frozenset[str] = frozenset({"https"}),
        default_timeout: float = 15.0,
    ):
        self.private_cidr_allowlist_env = private_cidr_allowlist_env
        self.allowed_schemes = allowed_schemes
        self.default_timeout = default_timeout
        self.session = requests.Session()

    def request(self, method: str, url: str, **kwargs) -> requests.Response:
        # Enforce redirects strictly disabled fail-closed
        if kwargs.get("allow_redirects", False):
            raise SSRFSecurityException("HTTP redirects are strictly disabled on CRM transport to prevent SSRF bypass.")
        kwargs["allow_redirects"] = False

        if "timeout" not in kwargs:
            kwargs["timeout"] = self.default_timeout

        hostname, resolved_ip = validate_crm_url_and_resolve(
            url,
            allowed_schemes=self.allowed_schemes,
            private_cidr_env=self.private_cidr_allowlist_env,
        )

        with pin_dns(hostname, resolved_ip):
            return self.session.request(method=method, url=url, **kwargs)

    def get(self, url: str, **kwargs) -> requests.Response:
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs) -> requests.Response:
        return self.request("POST", url, **kwargs)

    def put(self, url: str, **kwargs) -> requests.Response:
        return self.request("PUT", url, **kwargs)

    def patch(self, url: str, **kwargs) -> requests.Response:
        return self.request("PATCH", url, **kwargs)

    def delete(self, url: str, **kwargs) -> requests.Response:
        return self.request("DELETE", url, **kwargs)
