import os, json
from .crypto import encrypt_blob, decrypt_blob, VAULT_DIR

META_FILE = os.path.join(VAULT_DIR, "meta.json")
LOCAL_VAULT_FILE = os.path.join(VAULT_DIR, "vault.enc")

def load_meta():
    if os.path.exists(META_FILE):
        try:
            return json.load(open(META_FILE, "r"))
        except Exception:
            pass
    return {}

def save_meta(meta):
    json.dump(meta, open(META_FILE, "w"), indent=2)

def load_vault(password: str):
    if not os.path.exists(LOCAL_VAULT_FILE):
        return {}
    try:
        enc = open(LOCAL_VAULT_FILE, "rb").read()
        dec = decrypt_blob(enc, password)
        return json.loads(dec.decode())
    except Exception:
        return {}

def save_vault(vault_data, password: str):
    enc = encrypt_blob(json.dumps(vault_data).encode(), password)
    open(LOCAL_VAULT_FILE, "wb").write(enc)
