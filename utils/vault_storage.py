import os
import json
from utils.crypto import encrypt_blob, decrypt_blob

VAULT_DIR = os.path.expanduser("~/.vaultx_data")
VAULT_FILE = os.path.join(VAULT_DIR, "vault.enc")
META_FILE = os.path.join(VAULT_DIR, "meta.json")


def load_meta():
    """Load meta information."""
    if os.path.exists(META_FILE):
        with open(META_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_meta(meta):
    """Save meta information."""
    os.makedirs(VAULT_DIR, exist_ok=True)
    with open(META_FILE, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)


def load_vault(password: str):
    """Decrypt and load vault contents."""
    if not os.path.exists(VAULT_FILE):
        return {}
    try:
        with open(VAULT_FILE, "rb") as f:
            encrypted = f.read()
        decrypted = decrypt_blob(encrypted, password)
        return json.loads(decrypted.decode("utf-8"))
    except Exception:
        return {}


def save_vault(vault_data, password: str):
    """Encrypt and save vault data."""
    os.makedirs(VAULT_DIR, exist_ok=True)
    data = json.dumps(vault_data).encode("utf-8")
    encrypted = encrypt_blob(data, password)
    with open(VAULT_FILE, "wb") as f:
        f.write(encrypted)
