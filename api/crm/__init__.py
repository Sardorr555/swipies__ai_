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
from api.crm.base import CRMProviderBase
from api.crm.transport import CRMTransport, SSRFSecurityException, validate_crm_url_and_resolve
from api.crm.license_gate import check_crm_license_access, require_crm_license, CRMLicenseAccessError
from api.crm.clients.amocrm import (
    AmoCRMClient,
    AmoCRMError,
    AmoCRMAuthError,
    AmoCRMTokenRevokedError,
    AmoCRMDomainError,
    is_valid_amocrm_domain,
    is_valid_amocrm_url,
    mask_phone_dynamic,
    mask_sensitive_payload,
)
from api.crm.clients.bitrix24 import (
    Bitrix24Client,
    Bitrix24Error,
    Bitrix24DomainError,
    Bitrix24AuthError,
    Bitrix24RateLimitError,
    DEFAULT_B24_ZONES,
    get_allowed_b24_zones,
    validate_bitrix24_cloud_url,
    validate_bitrix24_onprem_url,
    redact_bitrix24_webhook_url,
    normalize_phone_to_e164,
)

__all__ = [
    "CRMProviderBase",
    "CRMTransport",
    "SSRFSecurityException",
    "validate_crm_url_and_resolve",
    "check_crm_license_access",
    "require_crm_license",
    "CRMLicenseAccessError",
    "AmoCRMClient",
    "AmoCRMError",
    "AmoCRMAuthError",
    "AmoCRMTokenRevokedError",
    "AmoCRMDomainError",
    "is_valid_amocrm_domain",
    "is_valid_amocrm_url",
    "mask_phone_dynamic",
    "mask_sensitive_payload",
    "Bitrix24Client",
    "Bitrix24Error",
    "Bitrix24DomainError",
    "Bitrix24AuthError",
    "Bitrix24RateLimitError",
    "DEFAULT_B24_ZONES",
    "get_allowed_b24_zones",
    "validate_bitrix24_cloud_url",
    "validate_bitrix24_onprem_url",
    "redact_bitrix24_webhook_url",
    "normalize_phone_to_e164",
]
