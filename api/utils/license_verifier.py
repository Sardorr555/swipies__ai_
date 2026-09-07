import base64
import hmac
import hashlib
import json
from datetime import datetime
import requests
import logging

# RSA Modulus from swipies_26 (standard license keypair)
RSA_N_26 = 116763369543673489555816179013579831032334948554884325089127113514438773601645323323610087949316382292668692922885479767179141736388273782636803297906260057958938769092740178739296200115666702708644785196695767856579195476396536846303623302269363644292776482712509280919139914373243538644062519021212759271469
# RSA Modulus v2 (rotation keypair)
RSA_N_V2 = 24341483587221741967054036518520868159282023123376268832476428015635164473385814553972730172259110113270121877516035282731242344945143073648891517860070951376718443478354815113166584174043560323731769117025109368560500955263266528910085909652795916403263944690074293725972106229788355637701757713181675424137226230873831829644812077232541685638413317250508770417615041455470114691777505019823686146942923443279981992922766043672658980022682462384408027153149775768826948411493732628951051736745383264816184167225530720129059877050910988017519968668477726055714217185328014168835798479792502398874386749495260575624949

RSA_N = RSA_N_26
RSA_E = 65537

SUPPORTED_RSA_N = [RSA_N_26, RSA_N_V2]

def decode_license(license_key: str) -> dict | None:
    try:
        cleaned_key = license_key.strip()
        if cleaned_key.startswith("SWIPIES-ACT-"):
            encoded = cleaned_key.replace("SWIPIES-ACT-", "")
            raw = base64.b64decode(encoded.encode())
            payload = json.loads(raw.decode())
            if isinstance(payload, dict) and payload.get("expiry"):
                return payload
            return None

        raw = base64.b64decode(cleaned_key.encode())
        parts = raw.rsplit(b".", 1)
        if len(parts) != 2:
            return None
        payload_bytes, sig_hex = parts[0], parts[1].decode()
        
        # Verify RSA Signature against supported moduli
        sig_int = int(sig_hex, 16)
        hash_bytes = hashlib.sha256(payload_bytes).digest()
        hash_int = int.from_bytes(hash_bytes, byteorder="big")
        
        valid_sig = False
        for n in SUPPORTED_RSA_N:
            if pow(sig_int, RSA_E, n) == hash_int:
                valid_sig = True
                break
        if not valid_sig:
            return None
            
        payload = json.loads(payload_bytes.decode())
        if not isinstance(payload, dict) or not payload.get("expiry"):
            return None
        return payload
    except Exception:
        return None

def verify_license_online(license_key: str) -> bool:
    if license_key.strip().startswith("SWIPIES-ACT-"):
        return True
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
