import base64
import hashlib
import json
import sys

RSA_N = 116763369543673489555816179013579831032334948554884325089127113514438773601645323323610087949316382292668692922885479767179141736388273782636803297906260057958938769092740178739296200115666702708644785196695767856579195476396536846303623302269363644292776482712509280919139914373243538644062519021212759271469
RSA_D = 73843651334004228475821492768601603015047783889318867540001090587499333955893521458011006229081527944279404238442932693139354678244118337259068713678086572806090230888416083537219803030227490658829754711418155033059871630652708264606653922491082167276314949693016821014010451663552801666999273493808373396037

def generate_license(owner: str, expiry: str, lic_type: str) -> str:
    payload = {
        "owner": owner,
        "expiry": expiry,
        "type": lic_type
    }
    payload_bytes = json.dumps(payload).encode()
    
    # Sign with private key RSA_D
    hash_bytes = hashlib.sha256(payload_bytes).digest()
    hash_int = int.from_bytes(hash_bytes, byteorder="big")
    sig_int = pow(hash_int, RSA_D, RSA_N)
    sig_hex = hex(sig_int)[2:].encode()
    
    license_key = base64.b64encode(payload_bytes + b"." + sig_hex).decode()
    return license_key

if __name__ == "__main__":
    owner = input("Enter Owner Name (default: Swipies User): ") or "Swipies User"
    expiry = input("Enter Expiry Date (YYYY-MM-DD, default: 2027-12-31): ") or "2027-12-31"
    lic_type = input("Enter License Type (yearly / 6_months, default: yearly): ") or "yearly"
    
    key = generate_license(owner, expiry, lic_type)
    print("\n---------------- GENERATED LICENSE KEY ----------------")
    print(key)
    print("-------------------------------------------------------\n")
