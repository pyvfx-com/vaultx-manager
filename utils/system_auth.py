import os
import sys
import hashlib
import getpass
import stat

try:
    import ctypes
    from ctypes import wintypes
except Exception:
    ctypes = None

try:
    import pam
except Exception:
    pam = None

STORED_HASH_FILE = os.path.expanduser("~/.vaultx_data/sys_pass_hash.txt")


def verify_system_password(password: str) -> bool:
    """Verify password using OS (Windows or Linux PAM) or local fallback."""
    # Windows
    if sys.platform.startswith("win") and ctypes:
        try:
            advapi32 = ctypes.windll.advapi32
            logon_user = advapi32.LogonUserW
            logon_user.argtypes = [
                wintypes.LPCWSTR,
                wintypes.LPCWSTR,
                wintypes.LPCWSTR,
                wintypes.DWORD,
                wintypes.DWORD,
                ctypes.POINTER(wintypes.HANDLE),
            ]
            logon32_logon_network = 3
            logon32_provider_default = 0
            token = wintypes.HANDLE()
            username = getpass.getuser()
            result = logon_user(
                username,
                None,
                password,
                logon32_logon_network,
                logon32_provider_default,
                ctypes.byref(token),
            )
            if result != 0:
                ctypes.windll.kernel32.CloseHandle(token)
                return True
        except Exception:
            pass

    # Linux PAM
    if sys.platform.startswith("linux") and pam:
        try:
            p = pam.pam()
            username = getpass.getuser()
            if p.authenticate(username, password):
                return True
        except Exception:
            pass

    # Local fallback hash
    if os.path.exists(STORED_HASH_FILE):
        with open(STORED_HASH_FILE, "r") as f:
            stored = f.read().strip()
        if stored:
            return hashlib.sha256(password.encode()).hexdigest() == stored

    # First run — create hash
    os.makedirs(os.path.dirname(STORED_HASH_FILE), exist_ok=True)
    with open(STORED_HASH_FILE, "w") as f:
        f.write(hashlib.sha256(password.encode()).hexdigest())
    os.chmod(STORED_HASH_FILE, stat.S_IRUSR | stat.S_IWUSR)
    return True
