import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend

SALT_FILE = os.path.expanduser("~/.vaultx_data/salt.bin")


def ensure_salt():
    """Ensure a salt file exists and return its bytes."""
    os.makedirs(os.path.dirname(SALT_FILE), exist_ok=True)
    if not os.path.exists(SALT_FILE):
        with open(SALT_FILE, "wb") as f:
            f.write(os.urandom(16))
    with open(SALT_FILE, "rb") as f:
        return f.read()


def derive_fernet_key(password: str) -> bytes:
    """Derive Fernet key using PBKDF2HMAC."""
    salt = ensure_salt()
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=200_000,
        backend=default_backend(),
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))


def encrypt_blob(blob: bytes, password: str) -> bytes:
    """Encrypt binary data using password."""
    fernet = Fernet(derive_fernet_key(password))
    return fernet.encrypt(blob)


def decrypt_blob(enc_blob: bytes, password: str) -> bytes:
    """Decrypt encrypted binary data."""
    fernet = Fernet(derive_fernet_key(password))
    return fernet.decrypt(enc_blob)
