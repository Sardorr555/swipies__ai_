import base64
import hmac
import hashlib
import json
import sys

SECRET_KEY = b"swipies_secret_licensing_key_2026_salt"

def generate_license(owner: str, expiry: str, lic_type: str) -> str:
    payload = {
        "owner": owner,
        "expiry": expiry,
        "type": lic_type
    }
    payload_bytes = json.dumps(payload).encode()
    sig = hmac.new(SECRET_KEY, payload_bytes, hashlib.sha256).hexdigest().encode()
    license_key = base64.b64encode(payload_bytes + b"." + sig).decode()
    return license_key

if __name__ == "__main__":
    owner = input("Enter Owner Name (default: Swipies User): ") or "Swipies User"
    expiry = input("Enter Expiry Date (YYYY-MM-DD, default: 2027-12-31): ") or "2027-12-31"
    lic_type = input("Enter License Type (yearly / 6_months, default: yearly): ") or "yearly"
    
    key = generate_license(owner, expiry, lic_type)
    print("\n---------------- GENERATED LICENSE KEY ----------------")
    print(key)
    print("-------------------------------------------------------\n")
