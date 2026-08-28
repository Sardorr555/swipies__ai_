import base64
import hmac
import hashlib
import json
from datetime import datetime
import requests
import logging

RSA_N = 24341483587221741967054036518520868159282023123376268832476428015635164473385814553972730172259110113270121877516035282731242344945143073648891517860070951376718443478354815113166584174043560323731769117025109368560500955263266528910085909652795916403263944690074293725972106229788355637701757713181675424137226230873831829644812077232541685638413317250508770417615041455470114691777505019823686146942923443279981992922766043672658980022682462384408027153149775768826948411493732628951051736745383264816184167225530720129059877050910988017519968668477726055714217185328014168835798479792502398874386749495260575624949
RSA_E = 65537

def decode_license(license_key: str) -> dict | None:
    try:
        cleaned_key = license_key.strip()
        raw = base64.b64decode(cleaned_key.encode())
        parts = raw.rsplit(b".", 1)
        if len(parts) != 2:
            return None
        payload_bytes, sig_hex = parts[0], parts[1].decode()
        
        # Verify RSA Signature
        sig_int = int(sig_hex, 16)
        hash_bytes = hashlib.sha256(payload_bytes).digest()
        hash_int = int.from_bytes(hash_bytes, byteorder="big")
        
        recovered_hash = pow(sig_int, RSA_E, RSA_N)
        if hash_int != recovered_hash:
            return None
            
        payload = json.loads(payload_bytes.decode())
        if not isinstance(payload, dict) or payload.get("ver") != 2:
            return None
        return payload
    except Exception:
        return None

def verify_license_online(license_key: str) -> bool:
    import os
    api_url = os.getenv("LICENSING_SERVER_URL") or os.getenv("SWIPIES_API_URL") or "https://api.swipies.io"
    # Ensure URL ends without trailing slash when constructing route
    api_url = api_url.rstrip("/")
    try:
        # Request verification to Swipies backend server
        resp = requests.post(f"{api_url}/v1/licenses/verify", json={"license_key": license_key}, timeout=3.0)
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
