import os
import sys
import requests
from base64 import b64encode
from nacl import encoding, public

# Target repository info
TARGET_OWNER = "Sardorr555"
TARGET_REPO = "Swipies_docs"
GITHUB_TOKEN = "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"

# Secrets to copy: source_name -> target_name
SECRETS_MAP = {
    "EC2_HOST": "AWS_HOST",
    "EC2_SSH_KEY": "AWS_SSH_KEY",
}

def encrypt(public_key: str, secret_value: str) -> str:
    public_key_obj = public.PublicKey(public_key.encode("utf-8"), encoding.Base64Encoder)
    sealed_box = public.SealedBox(public_key_obj)
    encrypted = sealed_box.encrypt(secret_value.encode("utf-8"))
    return b64encode(encrypted).decode("utf-8")

def main():
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

    # 1. Get target repository public key
    pubkey_url = f"https://api.github.com/repos/{TARGET_OWNER}/{TARGET_REPO}/actions/secrets/public-key"
    r = requests.get(pubkey_url, headers=headers)
    if r.status_code != 200:
        print(f"Failed to get public key: {r.status_code} {r.text}")
        sys.exit(1)

    pubkey_data = r.json()
    key_id = pubkey_data["key_id"]
    public_key = pubkey_data["key"]

    # 2. Encrypt and set each secret
    for src_name, target_name in SECRETS_MAP.items():
        secret_value = os.environ.get(src_name)
        if not secret_value:
            print(f"Warning: Source secret {src_name} not found in environment")
            continue

        print(f"Encrypting and setting {target_name}...")
        encrypted_value = encrypt(public_key, secret_value)

        secret_url = f"https://api.github.com/repos/{TARGET_OWNER}/{TARGET_REPO}/actions/secrets/{target_name}"
        payload = {
            "encrypted_value": encrypted_value,
            "key_id": key_id
        }
        r = requests.put(secret_url, json=payload, headers=headers)
        if r.status_code in (201, 204):
            print(f"Successfully set secret {target_name}")
        else:
            print(f"Failed to set secret {target_name}: {r.status_code} {r.text}")

if __name__ == "__main__":
    main()
