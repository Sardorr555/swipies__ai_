import warnings
warnings.filterwarnings("ignore")

import sys
import base64
import hashlib
import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import pytest

# Inject module mocks to prevent database/infinity native extension dependencies in unit tests
mock_system_settings = MagicMock()
sys.modules["api.db.services.system_settings_service"] = mock_system_settings

from api.utils.license_verifier import (
    RSA_N,
    RSA_E,
    decode_license,
    verify_license_online,
    check_license,
)

# Compromised Old Parameters for rejection tests
D_OLD = 8856372076043232873199890250626359570141648074900595304193574163914841203531393699317500057007788410260341772635414605969562768567154564883389871587340059437146522370908861277156942152865391629858348981600078028267253503527263309995166412574175399580665393275727788874603348124803730302061266009848529285097
N_OLD = 116763369543673489555816179013579831032334948554884325089127113514438773601645323323610087949316382292668692922885479767179141736388273782636803297906260057958938769092740178739296200115666702708644785196695767856579195476396536846303623302269363644292776482712509280919139914373243538644062519021212759271469

# Pre-signed Valid v2 License (generated with D_new)
VALID_V2_KEY = "eyJleHBpcnkiOiAiMjA5OS0xMi0zMSIsICJvd25lciI6ICJ0ZXN0QHN3aXBpZXMuY29tIiwgInR5cGUiOiAieWVhcmx5IiwgInZlciI6IDJ9LjEzZWNjYjIzZmY2MzUxODBiYTVkMmVhODliMDEwZjA5MzZhMzZhOWMxMzdlMzE3ZDllNzMwNjc1ZjY0MTQ2YmZlNTJlZTg3NTk4MjIyYzE2ZDFkNTczZWUyNzFlY2E5ZDE3YWNmZDNhMmE2YmFiY2YwMzMzNjY0OTQwOTViOThlYjdiODJlYmVjZjY5NjQ2ZWRmZGI3NzIyNmVlNDRlYzI3MjNmMDlmMThlNTNhZDQxN2NhOTMzM2JkMDRjMTJlOTA3MzE0NGI2ZmZiNDRiODk3NmM0ZjMwZWIzYzBkZWIyZjgxMmYxM2IzNmNkNzYyODI3MjMyYjkwMmQ0MGU3N2RiNzYwYTFkOTFhYzNmMWE2MmQ4ZDViNjhmNjVhYzczZGQxMTMxMjdjZWU5NDNhODdlYmIyMDc3MTQ0MjliM2JiMDUyMTYwYTA5MDQ3ZTE1OGZkYjYyOWYxOWFiNDc3ZWViMGQ1YzA4ZjllNDczZTU4Nzg1MWU5MDM4NmVlYTNhZGYxY2UxMDliZDhhYzA5N2YxMjQ1ODAwMzU4ODc1ODZkODlmZDM4MWE4MzQ5ZjFjZmZlMjYxZjQxYzFkYTQ0OTA5NDRmNDIxNzI0ZTZiYjM1NWM5MDliYjZjMTdkZWNlY2FmOGZjZDQxOWM5NGRhZjJmMjBhODc2YzBkZjkyMjI4"


def generate_legacy_key(payload: dict) -> str:
    """Signs a payload using the old compromised key pair (D_old, N_old)."""
    payload_bytes = json.dumps(payload, sort_keys=True).encode()
    hash_bytes = hashlib.sha256(payload_bytes).digest()
    hash_int = int.from_bytes(hash_bytes, byteorder="big")
    sig = pow(hash_int, D_OLD, N_OLD)
    sig_hex = hex(sig)[2:]
    combined = payload_bytes + b"." + sig_hex.encode()
    return base64.b64encode(combined).decode()


def test_rejection_of_old_d_old_license():
    """AC-2.4: Licenses generated with the leaked D_old must fail verification under N_new."""
    legacy_payload = {
        "ver": 1,
        "owner": "pirate@example.com",
        "expiry": "2099-12-31",
        "type": "yearly"
    }
    legacy_key = generate_legacy_key(legacy_payload)
    
    # 1. Mathematical decoding check
    decoded = decode_license(legacy_key)
    assert decoded is None, "Old legacy license must fail cryptographic decoding under N_new"

    # 2. End-to-end check_license verification
    mock_setting = MagicMock(value=legacy_key)
    mock_system_settings.SystemSettingsService.get_by_name.return_value = [mock_setting]
    
    is_valid, message, payload = check_license()
    assert not is_valid
    assert message == "Invalid license signature."
    assert payload is None


def test_rejection_of_old_d_old_license_with_v2_payload():
    """An attacker attempting to fake ver=2 with old D_old must also mathematically fail."""
    tampered_payload = {
        "ver": 2,
        "owner": "pirate@example.com",
        "expiry": "2099-12-31",
        "type": "yearly"
    }
    tampered_key = generate_legacy_key(tampered_payload)
    decoded = decode_license(tampered_key)
    assert decoded is None, "Tampered ver=2 with D_old signature must fail under N_new"


def test_acceptance_of_new_v2_license():
    """AC-2.3 & AC-2.4: Licenses signed with D_new must pass offline verification."""
    decoded = decode_license(VALID_V2_KEY)
    assert decoded is not None
    assert decoded["ver"] == 2
    assert decoded["owner"] == "test@swipies.com"
    assert decoded["expiry"] == "2099-12-31"

    # End-to-end check_license verification
    mock_setting = MagicMock(value=VALID_V2_KEY)
    mock_system_settings.SystemSettingsService.get_by_name.return_value = [mock_setting]
    with patch("api.utils.license_verifier.verify_license_online", return_value=True):
        is_valid, message, payload = check_license()
        assert is_valid
        assert "License active" in message
        assert payload["ver"] == 2


def test_rejection_of_swipies_act_bypass():
    """AC-2.5: The SWIPIES-ACT- backdoor prefix must be completely rejected."""
    fake_payload = {"ver": 2, "owner": "hacker@evil.com", "expiry": "2099-12-31"}
    b64_payload = base64.b64encode(json.dumps(fake_payload).encode()).decode()
    bypass_key = f"SWIPIES-ACT-{b64_payload}"

    decoded = decode_license(bypass_key)
    assert decoded is None, "SWIPIES-ACT- bypass key must be rejected by decode_license"

    mock_setting = MagicMock(value=bypass_key)
    mock_system_settings.SystemSettingsService.get_by_name.return_value = [mock_setting]
    
    is_valid, message, payload = check_license()
    assert not is_valid
    assert message == "Invalid license signature."


def test_online_verification_handling():
    """AC-5: Online verification handling for valid, revoked, and network failure states."""
    # 1. Server returns valid: true
    mock_resp_valid = MagicMock(status_code=200)
    mock_resp_valid.json.return_value = {"valid": True, "expiry": "2099-12-31", "code": 0}
    with patch("requests.post", return_value=mock_resp_valid):
        assert verify_license_online(VALID_V2_KEY) is True

    # 2. Server returns valid: false (Revocation / Chargeback)
    mock_resp_revoked = MagicMock(status_code=200)
    mock_resp_revoked.json.return_value = {"valid": False, "reason": "license_invalid", "code": 102}
    with patch("requests.post", return_value=mock_resp_revoked):
        assert verify_license_online(VALID_V2_KEY) is False

    # 3. Network timeout / air-gapped fallback to offline
    with patch("requests.post", side_effect=Exception("Connection timeout")):
        assert verify_license_online(VALID_V2_KEY) is True  # fallback offline check


def test_end_to_end_revocation_via_check_license():
    """AC-5: End-to-end verification that a revoked license in DB immediately fails check_license()."""
    mock_setting = MagicMock(value=VALID_V2_KEY)
    mock_system_settings.SystemSettingsService.get_by_name.return_value = [mock_setting]

    # Server explicitly returns valid: false (revoked in DB)
    mock_resp_revoked = MagicMock(status_code=200)
    mock_resp_revoked.json.return_value = {"valid": False, "reason": "license_invalid", "code": 102}

    with patch("requests.post", return_value=mock_resp_revoked):
        is_valid, message, payload = check_license()
        assert not is_valid
        assert message == "License revoked by server."
        assert payload is not None
        assert payload["ver"] == 2
