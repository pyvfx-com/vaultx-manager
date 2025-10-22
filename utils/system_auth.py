import sys, os, hashlib, getpass, stat
from pathlib import Path

try:
    import ctypes
    from ctypes import wintypes
except Exception:
    ctypes = None

try:
    import pam
except Exception:
    pam = None

HOME = str(Path.home())
VAULT_DIR = os.path.join(HOME, ".vaultx_data")
os.makedirs(VAULT_DIR, exist_ok=True)
STORED_HASH_FILE = os.path.join(VAULT_DIR, "sys_pass_hash.txt")

def verify_system_password(password: str) -> bool:
    """Verify using OS or fallback stored hash."""
    if sys.platform.startswith("win") and ctypes:
        try:
            advapi32 = ctypes.windll.advapi32
            LogonUser = advapi32.LogonUserW
            LogonUser.argtypes = [
                wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.LPCWSTR,
                wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)
            ]
            token = wintypes.HANDLE()
            username = getpass.getuser()
            res = LogonUser(username, None, password, 3, 0, ctypes.byref(token))
            if res != 0:
                ctypes.windll.kernel32.CloseHandle(token)
                return True
        except Exception:
            pass

    if sys.platform.startswith("linux") and pam:
        try:
            if pam.pam().authenticate(getpass.getuser(), password):
                return True
        except Exception:
            pass

    if os.path.exists(STORED_HASH_FILE):
        with open(STORED_HASH_FILE, "r") as f:
            stored = f.read().strip()
        return hashlib.sha256(password.encode()).hexdigest() == stored

    with open(STORED_HASH_FILE, "w") as f:
        f.write(hashlib.sha256(password.encode()).hexdigest())
    try:
        os.chmod(STORED_HASH_FILE, stat.S_IRUSR | stat.S_IWUSR)
    except Exception:
        pass
    return True
