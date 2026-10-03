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
from typing import Optional, Tuple, Dict, Any

from common.constants import RetCode
from api.utils.license_verifier import check_license


class CRMLicenseAccessError(PermissionError):
    """Raised when CRM feature access is denied by the license gate."""
    code = RetCode.PERMISSION_ERROR


def check_crm_license_access(license_payload: Optional[Dict[str, Any]] = None) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Verify that current license explicitly contains the 'crm' feature.

    Fail-closed policy:
    1. If license_payload is not provided, calls check_license().
    2. If license is invalid or payload is None -> (False, "License invalid", None)
    3. Having type: 'commercial' or 'enterprise' alone DOES NOT grant CRM access.
    4. Access is granted ONLY if 'crm' is explicitly in payload.get('features', []).
    """
    if license_payload is None:
        try:
            is_valid, msg, payload = check_license()
            if not is_valid or not isinstance(payload, dict):
                return False, f"CRM feature requires valid enterprise license: {msg}", None
        except Exception as exc:
            return False, f"CRM feature access denied: license verification failed: {exc}", None
    else:
        payload = license_payload

    if not isinstance(payload, dict):
        return False, "CRM feature access denied: invalid license payload structure", None

    features = payload.get("features", [])
    if isinstance(features, (list, tuple, set)):
        if "crm" in features:
            return True, "CRM feature authorized", payload

    return False, "CRM feature is not enabled in license features. Access denied.", payload


class CRMLicenseGate:
    """Convenience gate wrapper for CRM licensing checks."""

    @staticmethod
    def is_crm_enabled(license_payload: Optional[Dict[str, Any]] = None) -> bool:
        allowed, _, _ = check_crm_license_access(license_payload)
        return allowed


def require_crm_license() -> Dict[str, Any]:
    """Assertion helper that raises CRMLicenseAccessError if CRM is not licensed."""
    allowed, msg, payload = check_crm_license_access()
    if not allowed:
        raise CRMLicenseAccessError(msg)
    return payload or {}

