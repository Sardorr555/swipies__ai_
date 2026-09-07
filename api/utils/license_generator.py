import base64
import hashlib
import json
import os

from api.utils.license_verifier import RSA_N as DEFAULT_RSA_N

D_SWIPIES_26 = 73843651334004228475821492768601603015047783889318867540001090587499333955893521458011006229081527944279404238442932693139354678244118337259068713678086572806090230888416083537219803030227490658829754711418155033059871630652708264606653922491082167276314949693016821014010451663552801666999273493808373396037
N_SWIPIES_26 = 116763369543673489555816179013579831032334948554884325089127113514438773601645323323610087949316382292668692922885479767179141736388273782636803297906260057958938769092740178739296200115666702708644785196695767856579195476396536846303623302269363644292776482712509280919139914373243538644062519021212759271469

def generate_license(owner: str, expiry: str, lic_type: str, **kwargs) -> str:
    d_raw = os.getenv("SWIPIES_LICENSE_PRIVATE_KEY") or os.getenv("SWIPIES_LICENSE_RSA_D")
    n_raw = os.getenv("SWIPIES_LICENSE_RSA_N")
    if d_raw:
        d_int = int(d_raw.strip())
        n_int = int(n_raw.strip()) if n_raw else DEFAULT_RSA_N
    else:
        d_int = D_SWIPIES_26
        n_int = N_SWIPIES_26

    payload = {
        "owner": owner,
        "expiry": expiry,
        "type": lic_type
    }
    payload.update(kwargs)
    payload_bytes = json.dumps(payload).encode("utf-8")
    
    hash_bytes = hashlib.sha256(payload_bytes).digest()
    hash_int = int.from_bytes(hash_bytes, byteorder="big")
    sig = pow(hash_int, d_int, n_int)
    sig_hex = hex(sig)[2:].encode("utf-8")
    
    license_key = base64.b64encode(payload_bytes + b"." + sig_hex).decode("utf-8")
    return license_key

if __name__ == "__main__":
    owner = input("Enter Owner Name (default: Swipies User): ") or "Swipies User"
    expiry = input("Enter Expiry Date: ") or "2027-12-31"
    lic_type = input("Enter License Type: ") or "yearly"
    
    key = generate_license(owner, expiry, lic_type)
    print("\n---------------- GENERATED LICENSE KEY ----------------")
    print(key)
    print("-------------------------------------------------------\n")
