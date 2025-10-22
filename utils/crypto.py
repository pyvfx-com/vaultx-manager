import os, base64
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend

HOME = str(Path.home())
VAULT_DIR = os.path.join(HOME, ".vaultx_data")
os.makedirs(VAULT_DIR, exist_ok=True)
SALT_FILE = os.path.join(VAULT_DIR, "salt.bin")

def ensure_salt():
    if not os.path.exists(SALT_FILE):
        with open(SALT_FILE, "wb") as f:
            f.write(os.urandom(16))
    return open(SALT_FILE, "rb").read()

def derive_fernet_key(password: str) -> bytes:
    salt = ensure_salt()
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=200_000,
        backend=default_backend()
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))

def encrypt_blob(blob: bytes, password: str) -> bytes:
    return Fernet(derive_fernet_key(password)).encrypt(blob)

def decrypt_blob(enc_blob: bytes, password: str) -> bytes:
    return Fernet(derive_fernet_key(password)).decrypt(enc_blob)
