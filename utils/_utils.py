import os, sys, json, base64, sqlite3, shutil, tempfile, getpass, hashlib, stat
from pathlib import Path
from typing import Dict, Any, List, Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend

try:
    import ctypes
    from ctypes import wintypes
except ImportError:
    ctypes = None

try:
    import pam
except ImportError:
    pam = None

# ========== CONSTANTS ==========
HOME = str(Path.home())
VAULT_DIR = os.path.join(HOME, ".vaultx_data")
META_FILE = os.path.join(VAULT_DIR, "meta.json")
SALT_FILE = os.path.join(VAULT_DIR, "salt.bin")
LOCAL_VAULT_FILE = os.path.join(VAULT_DIR, "vault.enc")
STORED_HASH_FILE = os.path.join(VAULT_DIR, "sys_pass_hash.txt")

os.makedirs(VAULT_DIR, exist_ok=True)

# ========== ENCRYPTION HELPERS ==========
def ensure_salt() -> bytes:
    if not os.path.exists(SALT_FILE):
        with open(SALT_FILE, "wb") as f:
            f.write(os.urandom(16))
    return open(SALT_FILE, "rb").read()

def derive_fernet_key(password: str) -> bytes:
    salt = ensure_salt()
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(), length=32, salt=salt, iterations=200000, backend=default_backend()
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))

def encrypt_blob(blob: bytes, password: str) -> bytes:
    return Fernet(derive_fernet_key(password)).encrypt(blob)

def decrypt_blob(blob: bytes, password: str) -> bytes:
    return Fernet(derive_fernet_key(password)).decrypt(blob)

# ========== SYSTEM AUTH ==========
def verify_system_password(password: str) -> bool:
    """Try native auth; fallback to stored hash"""
    # Windows
    if sys.platform.startswith("win") and ctypes:
        try:
            advapi32 = ctypes.windll.advapi32
            token = wintypes.HANDLE()
            res = advapi32.LogonUserW(getpass.getuser(), None, password, 3, 0, ctypes.byref(token))
            if res != 0:
                ctypes.windll.kernel32.CloseHandle(token)
                return True
        except Exception:
            pass
    # Linux PAM
    if sys.platform.startswith("linux") and pam:
        try:
            if pam.pam().authenticate(getpass.getuser(), password):
                return True
        except Exception:
            pass
    # Fallback
    if os.path.exists(STORED_HASH_FILE):
        stored = open(STORED_HASH_FILE).read().strip()
        return hashlib.sha256(password.encode()).hexdigest() == stored
    else:
        with open(STORED_HASH_FILE, "w") as f:
            f.write(hashlib.sha256(password.encode()).hexdigest())
        os.chmod(STORED_HASH_FILE, stat.S_IRUSR | stat.S_IWUSR)
        return True

# ========== VAULT FILE OPS ==========
def load_vault(password: str) -> Dict[str, Any]:
    if not os.path.exists(LOCAL_VAULT_FILE):
        return {"entries": {}}
    try:
        data = decrypt_blob(open(LOCAL_VAULT_FILE, "rb").read(), password)
        return json.loads(data.decode())
    except Exception:
        return {"entries": {}}

def save_vault(vault: Dict[str, Any], password: str):
    data = json.dumps(vault, indent=2).encode()
    with open(LOCAL_VAULT_FILE, "wb") as f:
        f.write(encrypt_blob(data, password))

def backup_vault(dest_path: str):
    shutil.copy2(LOCAL_VAULT_FILE, dest_path)

def restore_vault(src_path: str):
    shutil.copy2(src_path, LOCAL_VAULT_FILE)

# ========== CHROME IMPORT (simplified) ==========
def import_chrome_login_data(dummy_pass="") -> List[Dict[str, str]]:
    creds = []
    local = os.environ.get("LOCALAPPDATA") if sys.platform.startswith("win") else None
    if local:
        chrome_db = os.path.join(local, "Google", "Chrome", "User Data", "Default", "Login Data")
        if not os.path.exists(chrome_db):
            return creds
        tmp = os.path.join(tempfile.gettempdir(), "vaultx_temp.db")
        shutil.copy2(chrome_db, tmp)
        conn = sqlite3.connect(tmp)
        cur = conn.cursor()
        try:
            cur.execute("SELECT origin_url, username_value, password_value FROM logins")
            for url, user, password_blob in cur.fetchall():
                creds.append({"url": url, "username": user, "password": "<encrypted>", "name": url})
        except Exception:
            pass
        conn.close()
        os.remove(tmp)
    return creds
