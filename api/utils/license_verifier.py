import base64
import hmac
import hashlib
import json
from datetime import datetime
import requests
import logging

SECRET_KEY = b"swipies_secret_licensing_key_2026_salt"

def decode_license(license_key: str) -> dict | None:
    try:
        raw = base64.b64decode(license_key.strip().encode())
        parts = raw.split(b".")
        if len(parts) != 2:
            return None
        payload_bytes, sig = parts[0], parts[1]
        
        # Verify HMAC
        expected_sig = hmac.new(SECRET_KEY, payload_bytes, hashlib.sha256).hexdigest().encode()
        if not hmac.compare_digest(sig, expected_sig):
            return None
            
        payload = json.loads(payload_bytes.decode())
        return payload
    except Exception:
        return None

def verify_license_online(license_key: str) -> bool:
    try:
        # Request verification to Swipies backend server
        resp = requests.post("https://api.swipies.io/v1/licenses/verify", json={"license_key": license_key}, timeout=3.0)
        if resp.status_code == 200:
            data = resp.json()
            return bool(data.get("valid", False))
    except Exception as e:
        logging.warning("License online check failed, falling back to offline check: %s", e)
    return True # fallback to offline check when offline

def check_license() -> tuple[bool, str, dict | None]:
    """
    Returns:
       is_valid: bool
       message: explanation of status
       payload: dict or None
    """
    from api.db.services.system_settings_service import SystemSettingsService
    try:
        objs = list(SystemSettingsService.get_by_name("license.key"))
        if not objs:
            return False, "No license activated. Base Version mode.", None
        license_key = objs[0].value
        if not license_key:
            return False, "No license activated. Base Version mode.", None
            
        payload = decode_license(license_key)
        if not payload:
            return False, "Invalid license signature.", None
            
        # Offline check: expiry
        expiry_str = payload.get("expiry")
        if not expiry_str:
            return False, "License is missing expiry date.", payload
            
        try:
            expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d")
        except ValueError:
            return False, "Invalid expiry date format.", payload
            
        if datetime.now() > expiry_date:
            days_expired = (datetime.now() - expiry_date).days
            return False, f"License expired {days_expired} days ago on {expiry_str}.", payload
            
        # Online check
        online_ok = verify_license_online(license_key)
        if not online_ok:
            return False, "License revoked by server.", payload
            
        days_left = (expiry_date - datetime.now()).days
        return True, f"License active. {days_left} days remaining until {expiry_str}.", payload
    except Exception as e:
        return False, f"Error verifying license: {str(e)}", None
