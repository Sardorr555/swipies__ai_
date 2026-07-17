import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from api.utils.license_verifier import decode_license, verify_license_online, check_license
from generate_license import generate_license

def test_decode_license_valid():
    # Generate a key dynamically using the current branch generator
    owner = "client@swipies.app"
    expiry = "2029-12-31"
    lic_type = "yearly"
    
    key = generate_license(owner, expiry, lic_type)
    
    payload = decode_license(key)
    assert payload is not None
    assert payload["owner"] == owner
    assert payload["expiry"] == expiry
    assert payload["type"] == lic_type

def test_decode_license_invalid_sig():
    owner = "client@swipies.app"
    expiry = "2029-12-31"
    lic_type = "yearly"
    key = generate_license(owner, expiry, lic_type)
    
    # Tamper with the key (e.g. change the last character of payload)
    import base64
    raw = base64.b64decode(key.encode())
    parts = raw.rsplit(b".", 1)
    # Modify payload_bytes
    tampered_payload = parts[0] + b"x"
    tampered_key = base64.b64encode(tampered_payload + b"." + parts[1]).decode()
    
    payload = decode_license(tampered_key)
    assert payload is None

def test_verify_license_online_env(monkeypatch):
    # Set custom verification server env variables
    monkeypatch.setenv("LICENSING_SERVER_URL", "http://test-server.local/")
    
    owner = "client@swipies.app"
    expiry = "2029-12-31"
    lic_type = "yearly"
    key = generate_license(owner, expiry, lic_type)
    
    with patch("requests.post") as mock_post:
        # Mock successful response from the custom server
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"valid": True}
        mock_post.return_value = mock_response
        
        valid = verify_license_online(key)
        assert valid is True
        
        # Verify it constructed the URL correctly (without double slashes)
        mock_post.assert_called_once_with(
            "http://test-server.local/v1/licenses/verify",
            json={"license_key": key},
            timeout=3.0
        )

@patch("api.db.services.system_settings_service.SystemSettingsService.get_by_name")
def test_check_license_no_key(mock_get_by_name):
    # Mock database returning no key
    mock_get_by_name.return_value = []
    
    is_valid, msg, payload = check_license()
    assert is_valid is False
    assert "No license activated" in msg
    assert payload is None

@patch("api.db.services.system_settings_service.SystemSettingsService.get_by_name")
def test_check_license_expired(mock_get_by_name):
    # Create an expired license key
    owner = "client@swipies.app"
    expiry = "2020-01-01"  # Long expired
    lic_type = "6_months"
    key = generate_license(owner, expiry, lic_type)
    
    mock_setting = MagicMock()
    mock_setting.value = key
    mock_get_by_name.return_value = [mock_setting]
    
    is_valid, msg, payload = check_license()
    assert is_valid is False
    assert "expired" in msg
    assert payload is not None
    assert payload["owner"] == owner

@patch("api.db.services.system_settings_service.SystemSettingsService.get_by_name")
@patch("api.utils.license_verifier.verify_license_online")
def test_check_license_valid(mock_verify_online, mock_get_by_name):
    # Create a valid license key
    owner = "client@swipies.app"
    expiry = (datetime.now() + timedelta(days=100)).strftime("%Y-%m-%d")
    lic_type = "yearly"
    key = generate_license(owner, expiry, lic_type)
    
    mock_setting = MagicMock()
    mock_setting.value = key
    mock_get_by_name.return_value = [mock_setting]
    
    mock_verify_online.return_value = True
    
    is_valid, msg, payload = check_license()
    assert is_valid is True
    assert "active" in msg.lower()
    assert payload is not None
    assert payload["owner"] == owner
