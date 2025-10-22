"""
utils/chrome_import.py

Best-effort, defensive Chrome / Chromium login data importer.
Implements:
 - find_chrome_paths()
 - windows_dpapi_decrypt()
 - get_chrome_master_key()
 - import_chrome_login_data(password: str) -> List[Dict[str,str]]

Notes:
 - This file does not attempt to fully implement AES-GCM decryption of Chrome's
   password blobs on Linux/macOS (these often require libsecret / Keychain access).
 - On Windows we attempt win32crypt.CryptUnprotectData first and fall back to
   a ctypes-based DPAPI call if pywin32 isn't available.
"""

import os
import sys
import json
import base64
import sqlite3
import shutil
import tempfile
import time
from pathlib import Path
from typing import List, Dict, Optional

HOME = str(Path.home())


def find_chrome_paths() -> List[Dict[str, str]]:
    """
    Find likely Chrome/Chromium profile directories for the current platform.
    Returns a list of dicts: { "profile": str, "userData": str, "profileDir": str }
    """
    paths: List[Dict[str, str]] = []
    if sys.platform.startswith("win"):
        local = os.environ.get("LOCALAPPDATA")
        if local:
            base = os.path.join(local, "Google", "Chrome", "User Data")
            if os.path.exists(base):
                default = os.path.join(base, "Default")
                paths.append({"profile": "Chrome Default", "userData": base, "profileDir": default})
            # also check for Chrome Canary or other channels
            for channel in ("Chrome SxS",):
                # optional: extend as needed
                pass
    else:
        # Linux: search common config locations for chrome/chromium
        for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
            p = os.path.join(HOME, ".config", name, "Default")
            if os.path.exists(p):
                paths.append({"profile": f"{name} Default", "userData": os.path.dirname(p), "profileDir": p})
    return paths


def windows_dpapi_decrypt(encrypted_bytes: bytes) -> Optional[bytes]:
    """
    Try to decrypt a DPAPI blob on Windows.
    First attempt uses win32crypt (pywin32). If not available, use a ctypes fallback.
    Returns plaintext bytes or None.
    """
    # Attempt win32crypt (pywin32) if available
    try:
        import win32crypt  # type: ignore
        _, decrypted = win32crypt.CryptUnprotectData(encrypted_bytes, None, None, None, 0)
        return decrypted
    except Exception:
        pass

    # ctypes fallback for CryptUnprotectData
    try:
        import ctypes
        from ctypes import wintypes, byref

        crypt32 = ctypes.windll.crypt32
        kernel32 = ctypes.windll.kernel32

        class DATA_BLOB(ctypes.Structure):
            _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

        def to_data_blob(b: bytes) -> DATA_BLOB:
            blob = DATA_BLOB()
            blob.cbData = len(b)
            # create_string_buffer requires bytes length passed
            buf = ctypes.create_string_buffer(b, len(b))
            blob.pbData = ctypes.cast(buf, ctypes.POINTER(ctypes.c_char))
            return blob

        in_blob = to_data_blob(encrypted_bytes)
        out_blob = DATA_BLOB()
        if crypt32.CryptUnprotectData(byref(in_blob), None, None, None, None, 0, byref(out_blob)):
            ptr = out_blob.pbData
            size = out_blob.cbData
            res = ctypes.string_at(ptr, size)
            kernel32.LocalFree(ptr)
            return res
    except Exception:
        pass

    return None


def get_chrome_master_key(profile_user_data: str) -> Optional[bytes]:
    """
    Reads 'Local State' JSON under profile_user_data and extracts the encrypted key.
    On Windows the key is DPAPI-protected; we attempt to decrypt it.
    On non-Windows we return the raw encrypted_key bytes (handling requires libsecret).
    """
    local_state_candidates = [
        os.path.join(profile_user_data, "Local State"),
        os.path.join(profile_user_data, "local_state"),
    ]
    for p in local_state_candidates:
        if not os.path.exists(p):
            continue
        try:
            with open(p, "r", encoding="utf-8") as fh:
                j = json.load(fh)
            enc_key_b64 = j.get("os_crypt", {}).get("encrypted_key")
            if not enc_key_b64:
                continue
            encrypted_key_with_header = base64.b64decode(enc_key_b64)
            if sys.platform.startswith("win") and encrypted_key_with_header.startswith(b"DPAPI"):
                encrypted_key = encrypted_key_with_header[5:]
                key = windows_dpapi_decrypt(encrypted_key)
                return key
            else:
                # On Linux/macOS this blob is often an AES key encrypted for the OS
                # returning raw bytes; full handling is out-of-scope here.
                return encrypted_key_with_header
        except Exception:
            continue
    return None


def import_chrome_login_data(vault_password: str) -> List[Dict[str, str]]:
    """
    Best-effort import of Chrome 'Login Data'.
    Returns list of credentials: { 'origin_url', 'username', 'password', 'name' }

    Notes:
     - This function copies the SQLite DB to a temp file (Chrome locks the original).
     - Passwords on Windows may be DPAPI-protected and can often be decrypted.
     - On Linux/macOS the function will place a placeholder indicating further OS-specific
       decryption (libsecret / keyring) would be necessary.
    """
    creds: List[Dict[str, str]] = []
    paths = find_chrome_paths()

    for p in paths:
        profile_dir = p.get("profileDir")
        user_data = p.get("userData")
        if not profile_dir or not os.path.exists(profile_dir):
            continue

        login_db = os.path.join(profile_dir, "Login Data")
        if not os.path.exists(login_db):
            continue

        tmp_db = os.path.join(tempfile.gettempdir(), f"vaultx_chrome_{int(time.time())}.db")
        try:
            shutil.copy2(login_db, tmp_db)
        except Exception:
            # cannot copy, skip this profile
            continue

        master_key = get_chrome_master_key(user_data or "")
        conn = None
        try:
            conn = sqlite3.connect(tmp_db)
            cur = conn.cursor()
            # column names differ slightly across Chrome versions; this is common set
            cur.execute("SELECT origin_url, username_value, password_value, signon_realm FROM logins")
            rows = cur.fetchall()
            for origin_url, username, password_blob, signon_realm in rows:
                plain: Optional[bytes] = None
                try:
                    if sys.platform.startswith("win"):
                        # Many Windows builds store DPAPI-protected password blobs
                        try:
                            plain = windows_dpapi_decrypt(password_blob)
                        except Exception:
                            plain = None

                        # If windows_dpapi_decrypt returned None and we do have a master_key,
                        # sometimes the blob uses the 'v10' + AES-GCM format which needs AES-GCM using master_key.
                        # That implementation is platform-specific and omitted here.
                        if plain is None and master_key:
                            plain = b"<encrypted - AES/GCM; need master_key decryption>"
                    else:
                        # On Linux/macOS usually password_blob uses AES-GCM with 'v10' prefix and requires libsecret
                        plain = b"<platform decryption required (libsecret / keyring)>"
                except Exception:
                    plain = None

                password_text = ""
                if isinstance(plain, (bytes, bytearray)):
                    try:
                        password_text = plain.decode("utf-8", errors="ignore")
                    except Exception:
                        password_text = str(plain)
                else:
                    password_text = str(plain)

                creds.append({
                    "origin_url": origin_url or "",
                    "username": username or "",
                    "password": password_text,
                    "name": signon_realm or origin_url or "Unknown"
                })
        except Exception:
            # ignore inaccessible DB schemas or read issues
            pass
        finally:
            if conn:
                conn.close()
            try:
                os.remove(tmp_db)
            except Exception:
                pass

    return creds
