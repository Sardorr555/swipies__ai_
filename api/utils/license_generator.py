import base64
import hashlib
import json
import os

from api.utils.license_verifier import RSA_N as DEFAULT_RSA_N

D_OLD = 8856372076043232873199890250626359570141648074900595304193574163914841203531393699317500057007788410260341772635414605969562768567154564883389871587340059437146522370908861277156942152865391629858348981600078028267253503527263309995166412574175399580665393275727788874603348124803730302061266009848529285097
N_OLD = 116763369543673489555816179013579831032334948554884325089127113514438773601645323323610087949316382292668692922885479767179141736388273782636803297906260057958938769092740178739296200115666702708644785196695767856579195476396536846303623302269363644292776482712509280919139914373243538644062519021212759271469

def generate_license(owner: str, expiry: str, lic_type: str, **kwargs) -> str:
    d_raw = os.getenv("SWIPIES_LICENSE_PRIVATE_KEY") or os.getenv("SWIPIES_LICENSE_RSA_D")
    n_raw = os.getenv("SWIPIES_LICENSE_RSA_N")
    if d_raw:
        d_int = int(d_raw.strip())
        n_int = int(n_raw.strip()) if n_raw else DEFAULT_RSA_N
        ver = 2
    else:
        d_int = D_OLD
        n_int = N_OLD
        ver = 1

    payload = {
        "ver": ver,
        "owner": owner,
        "expiry": expiry,
        "type": lic_type
    }
    payload.update(kwargs)
    payload_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
    
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
