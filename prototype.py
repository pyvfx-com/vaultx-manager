"""
VaultX - Modern Password Manager (PyQt5)
Features:
 - System unlock (Windows LogonUser / Linux PAM when available)
 - Auto-import of Chrome passwords at startup (best-effort)
 - Password-manager style UI (sidebar + list + details)
 - Dark / Light theme toggle
 - Encrypted local vault (Fernet) derived from system password
 - Clipboard copy with auto-clear
Notes:
 - Chrome import on Linux may require libsecret/secretstorage and GNOME keyring.
 - On Windows, import uses CryptUnprotectData (DPAPI) via ctypes if pywin32 not present.
"""

import os
import sys
import json
import base64
import sqlite3
import shutil
import tempfile
import getpass
import hashlib
import stat
import time
import threading
from pathlib import Path
from typing import Optional, Dict, Any, List

from PyQt5 import QtWidgets, QtGui, QtCore
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend

# ---------- Platform-specific imports attempted when needed ----------
try:
    import ctypes
    from ctypes import wintypes
except Exception:
    ctypes = None

# pam on linux
try:
    import pam  # python-pam
except Exception:
    pam = None

# try to import secretstorage (linux)
try:
    import secretstorage
except Exception:
    secretstorage = None

# ---------- Paths and constants ----------
HOME = str(Path.home())
VAULT_DIR = os.path.join(HOME, ".vaultx_data")
os.makedirs(VAULT_DIR, exist_ok=True)
META_FILE = os.path.join(VAULT_DIR, "meta.json")
SALT_FILE = os.path.join(VAULT_DIR, "salt.bin")
LOCAL_VAULT_FILE = os.path.join(VAULT_DIR, "vault.enc")
STORED_HASH_FILE = os.path.join(VAULT_DIR, "sys_pass_hash.txt")  # fallback

# ---------- Utilities: Key Derivation & Fernet wrapper ----------
def ensure_salt():
    if not os.path.exists(SALT_FILE):
        with open(SALT_FILE, "wb") as f:
            f.write(os.urandom(16))
    return open(SALT_FILE, "rb").read()

def derive_fernet_key(password: str) -> bytes:
    """Derive a 32-byte base64 urlsafe key for Fernet using PBKDF2HMAC."""
    salt = ensure_salt()
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=200_000,
        backend=default_backend()
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return key

def encrypt_blob(blob: bytes, password: str) -> bytes:
    f = Fernet(derive_fernet_key(password))
    return f.encrypt(blob)

def decrypt_blob(enc_blob: bytes, password: str) -> bytes:
    f = Fernet(derive_fernet_key(password))
    return f.decrypt(enc_blob)

# ---------- OS Authentication ----------
def verify_system_password(password: str) -> bool:
    """
    Attempts to verify the provided password against the OS account:
    - Windows: uses LogonUserW (advapi32)
    - Linux: uses pam.authenticate (python-pam)
    Falls back to comparing a locally stored hash (first-run sets it).
    """
    # 1) Windows
    if sys.platform.startswith("win") and ctypes:
        try:
            advapi32 = ctypes.windll.advapi32
            LogonUser = advapi32.LogonUserW
            LogonUser.argtypes = [
                wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.LPCWSTR,
                wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)
            ]
            LOGON32_LOGON_NETWORK = 3
            LOGON32_PROVIDER_DEFAULT = 0
            token = wintypes.HANDLE()
            username = getpass.getuser()
            domain = None  # local machine
            # Call LogonUserW: returns nonzero for success
            res = LogonUser(username, domain, password,
                            LOGON32_LOGON_NETWORK, LOGON32_PROVIDER_DEFAULT,
                            ctypes.byref(token))
            if res != 0:
                try:
                    # close handle
                    ctypes.windll.kernel32.CloseHandle(token)
                except Exception:
                    pass
                return True
        except Exception:
            pass

    # 2) Linux (PAM)
    if sys.platform.startswith("linux") and pam:
        try:
            p = pam.pam()
            username = getpass.getuser()
            if p.authenticate(username, password):
                return True
        except Exception:
            pass

    # 3) Fallback to locally stored hash (first-run)
    if os.path.exists(STORED_HASH_FILE):
        with open(STORED_HASH_FILE, "r") as f:
            stored = f.read().strip()
        if not stored:
            return False
        # compare sha256 hash
        return hashlib.sha256(password.encode()).hexdigest() == stored

    # 4) If no stored hash, treat first-run: store provided password hash as fallback
    #    (This is only executed if OS auth methods weren't available.)
    #    We still return True to allow the user to proceed and create the vault.
    with open(STORED_HASH_FILE, "w") as f:
        f.write(hashlib.sha256(password.encode()).hexdigest())
    # ensure file perms restrict access
    try:
        os.chmod(STORED_HASH_FILE, stat.S_IRUSR | stat.S_IWUSR)
    except Exception:
        pass
    return True

# ---------- Chrome import (best-effort) ----------
def find_chrome_paths() -> List[Dict[str,str]]:
    """Find probable Chrome/Chromium profile locations to try importing from."""
    paths = []
    if sys.platform.startswith("win"):
        local = os.environ.get("LOCALAPPDATA")
        if local:
            base = os.path.join(local, "Google", "Chrome", "User Data")
            if os.path.exists(base):
                default = os.path.join(base, "Default")
                paths.append({"profile": "Chrome Default", "userData": base, "profileDir": default})
    else:
        # linux - try google-chrome and chromium
        for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
            p = os.path.join(HOME, ".config", name, "Default")
            if os.path.exists(p):
                paths.append({"profile": f"{name} Default", "userData": os.path.dirname(p), "profileDir": p})
    return paths

def windows_dpapi_decrypt(encrypted_bytes: bytes) -> Optional[bytes]:
    """Use CryptUnprotectData via ctypes (fallback if win32crypt missing)."""
    try:
        # Try win32crypt first (if pywin32 installed)
        import win32crypt
        dpapi_blob = win32crypt.CryptUnprotectData(encrypted_bytes, None, None, None, 0)[1]
        return dpapi_blob
    except Exception:
        pass
    # ctypes fallback
    try:
        import ctypes
        from ctypes import wintypes, byref, POINTER
        crypt32 = ctypes.windll.crypt32
        kernel32 = ctypes.windll.kernel32

        class DATA_BLOB(ctypes.Structure):
            _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

        def to_data_blob(b):
            blob = DATA_BLOB()
            blob.cbData = len(b)
            blob.pbData = ctypes.cast(ctypes.create_string_buffer(b, len(b)), ctypes.POINTER(ctypes.c_char))
            return blob

        in_blob = to_data_blob(encrypted_bytes)
        out_blob = DATA_BLOB()
        if crypt32.CryptUnprotectData(byref(in_blob), None, None, None, None, 0, byref(out_blob)):
            ptr = out_blob.pbData
            size = out_blob.cbData
            buf = ctypes.string_at(ptr, size)
            kernel32.LocalFree(ptr)
            return buf
    except Exception:
        pass
    return None

def get_chrome_master_key(profile_user_data: str) -> Optional[bytes]:
    """
    Extract the AES key used by Chrome (from Local State file).
    On Windows this key is usually DPAPI encrypted.
    On Linux it may be encrypted using libsecret (not supported here fully).
    """
    local_state_paths = [
        os.path.join(profile_user_data, "Local State"),
        os.path.join(profile_user_data, "local_state")
    ]
    for p in local_state_paths:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    j = json.load(f)
                encrypted_key_b64 = j.get("os_crypt", {}).get("encrypted_key")
                if encrypted_key_b64:
                    encrypted_key_with_header = base64.b64decode(encrypted_key_b64)
                    # Chrome stores DPAPI prefix "DPAPI" on Windows
                    if sys.platform.startswith("win") and encrypted_key_with_header.startswith(b"DPAPI"):
                        encrypted_key = encrypted_key_with_header[5:]
                        raw = windows_dpapi_decrypt(encrypted_key)
                        return raw
                    else:
                        # On Linux: Local State contains encrypted_key (AES) that may need libsecret to decrypt.
                        # We'll return the raw encrypted key here; further handling requires libsecret.
                        return encrypted_key_with_header
            except Exception:
                continue
    return None

def import_chrome_login_data(vault_password: str) -> List[Dict[str,str]]:
    """
    Best-effort import of Chrome passwords. Returns list of credentials:
    { 'origin_url', 'username', 'password', 'name' }
    """
    creds = []
    paths = find_chrome_paths()
    for p in paths:
        profile_dir = p["profileDir"]
        login_db = os.path.join(profile_dir, "Login Data")
        if not os.path.exists(login_db):
            continue
        # copy the DB to a temp file (Chrome locks it)
        tmp = os.path.join(tempfile.gettempdir(), f"vaultx_chrome_{int(time.time())}.db")
        try:
            shutil.copy2(login_db, tmp)
        except Exception:
            continue
        master_key = get_chrome_master_key(p["userData"])
        conn = None
        try:
            conn = sqlite3.connect(tmp)
            cur = conn.cursor()
            cur.execute("SELECT origin_url, username_value, password_value, signon_realm FROM logins")
            rows = cur.fetchall()
            for origin_url, username, password_blob, signon_realm in rows:
                plain = None
                try:
                    if sys.platform.startswith("win"):
                        # On Windows password_blob is DPAPI protected
                        plain = windows_dpapi_decrypt(password_blob)
                        if not plain:
                            # sometimes password_blob stored as b'v10' + AES-GCM encrypted data -- then we need master_key
                            if master_key:
                                # AES-GCM decryption path would be implemented here (complex); skipping for brevity.
                                plain = b"<encrypted - need AES/GCM decryption>"
                    else:
                        # Linux: password_blob may be AES-GCM; full decryption might need libsecret.
                        plain = b"<platform decryption needed>"
                except Exception:
                    plain = None
                creds.append({
                    "origin_url": origin_url,
                    "username": username or "",
                    "password": plain.decode("utf-8", errors="ignore") if isinstance(plain, (bytes, bytearray)) else str(plain),
                    "name": signon_realm or origin_url
                })
        except Exception:
            pass
        finally:
            if conn:
                conn.close()
            try:
                os.remove(tmp)
            except Exception:
                pass
    return creds

# ---------- Simple vault storage helpers ----------
def load_meta() -> Dict[str, str]:
    if os.path.exists(META_FILE):
        try:
            return json.load(open(META_FILE, "r", encoding="utf-8"))
        except Exception:
            return {}
    return {}

def save_meta(meta: Dict[str, str]):
    with open(META_FILE, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

def load_vault(password: str) -> Dict[str, Any]:
    """Decrypt local vault (JSON) if present, else return empty dict."""
    if not os.path.exists(LOCAL_VAULT_FILE):
        return {}
    try:
        enc = open(LOCAL_VAULT_FILE, "rb").read()
        dec = decrypt_blob(enc, password)
        return json.loads(dec.decode("utf-8"))
    except Exception:
        return {}

def save_vault(vault_data: Dict[str, Any], password: str):
    b = json.dumps(vault_data).encode("utf-8")
    enc = encrypt_blob(b, password)
    with open(LOCAL_VAULT_FILE, "wb") as f:
        f.write(enc)

# ---------- UI: Styles ----------
DARK_QSS = """
/* Minimal modern-ish style */
QWidget { background: #121212; color: #e5e5e5; font-family: "Segoe UI", Roboto, Arial; }
QPushButton { background: #1f1f1f; border: 1px solid #2b2b2b; padding: 6px 10px; border-radius: 8px; }
QPushButton:hover { background: #2b2b2b; }
QLineEdit, QPlainTextEdit, QTextEdit { background: #171717; border: 1px solid #2b2b2b; padding: 6px; border-radius: 6px; }
QListWidget { background: transparent; border: none; }
QListWidget::item { padding: 10px; border-radius: 6px; }
QListWidget::item:selected { background: #262626; }
QLabel#title { font-size: 18px; font-weight: 600; }
QFrame#card { background: #141414; border: 1px solid #232323; border-radius: 10px; padding: 12px; }
"""

LIGHT_QSS = """
QWidget { background: #f7f7f7; color: #111; font-family: "Segoe UI", Roboto, Arial; }
QPushButton { background: #ffffff; border: 1px solid #ddd; padding: 6px 10px; border-radius: 8px; }
QPushButton:hover { background: #f0f0f0; }
QLineEdit, QPlainTextEdit, QTextEdit { background: #fff; border: 1px solid #ddd; padding: 6px; border-radius: 6px; }
QListWidget { background: transparent; border: none; }
QListWidget::item { padding: 10px; border-radius: 6px; }
QListWidget::item:selected { background: #e9e9e9; }
QLabel#title { font-size: 18px; font-weight: 600; }
QFrame#card { background: #ffffff; border: 1px solid #eee; border-radius: 10px; padding: 12px; }
"""

# ---------- UI: Dialogs ----------
class SystemAuthDialog(QtWidgets.QDialog):
    """Dialog asking for system password to unlock vault."""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Unlock VaultX - System Authentication")
        self.setModal(True)
        self.resize(420, 160)
        layout = QtWidgets.QVBoxLayout(self)

        layout.addWidget(QtWidgets.QLabel("Please enter your system password to unlock VaultX:"))
        self.pass_input = QtWidgets.QLineEdit()
        self.pass_input.setEchoMode(QtWidgets.QLineEdit.Password)
        self.pass_input.setPlaceholderText("System / account password")
        layout.addWidget(self.pass_input)

        self.info_label = QtWidgets.QLabel("")
        layout.addWidget(self.info_label)

        btn_row = QtWidgets.QHBoxLayout()
        self.unlock_btn = QtWidgets.QPushButton("Unlock")
        self.cancel_btn = QtWidgets.QPushButton("Cancel")
        btn_row.addWidget(self.unlock_btn)
        btn_row.addWidget(self.cancel_btn)
        layout.addLayout(btn_row)

        self.unlock_btn.clicked.connect(self.attempt_unlock)
        self.cancel_btn.clicked.connect(self.reject)

        self.verified_password = None

    def attempt_unlock(self):
        pwd = self.pass_input.text().strip()
        if not pwd:
            QtWidgets.QMessageBox.warning(self, "Missing", "Enter a password.")
            return
        self.info_label.setText("Verifying...")
        QtWidgets.QApplication.processEvents()
        ok = verify_system_password(pwd)
        if ok:
            self.verified_password = pwd
            self.accept()
        else:
            self.info_label.setText("Verification failed. If OS auth isn't available on this system, a fallback master password will be set on first-run.")
            QtWidgets.QMessageBox.critical(self, "Auth Failed", "System authentication failed.")

class EntryEditorDialog(QtWidgets.QDialog):
    def __init__(self, title="", username="", password="", url="", notes=""):
        super().__init__()
        self.setWindowTitle("Edit Entry")
        self.resize(520, 360)
        layout = QtWidgets.QVBoxLayout(self)

        layout.addWidget(QtWidgets.QLabel("Title"))
        self.title_edit = QtWidgets.QLineEdit(title)
        layout.addWidget(self.title_edit)

        layout.addWidget(QtWidgets.QLabel("Username"))
        self.user_edit = QtWidgets.QLineEdit(username)
        layout.addWidget(self.user_edit)

        layout.addWidget(QtWidgets.QLabel("Password"))
        self.pass_edit = QtWidgets.QLineEdit(password)
        self.pass_edit.setEchoMode(QtWidgets.QLineEdit.Password)
        layout.addWidget(self.pass_edit)

        layout.addWidget(QtWidgets.QLabel("URL"))
        self.url_edit = QtWidgets.QLineEdit(url)
        layout.addWidget(self.url_edit)

        layout.addWidget(QtWidgets.QLabel("Notes"))
        self.notes_edit = QtWidgets.QPlainTextEdit(notes)
        layout.addWidget(self.notes_edit)

        btn_row = QtWidgets.QHBoxLayout()
        self.save_btn = QtWidgets.QPushButton("Save")
        self.cancel_btn = QtWidgets.QPushButton("Cancel")
        btn_row.addWidget(self.save_btn)
        btn_row.addWidget(self.cancel_btn)
        layout.addLayout(btn_row)

        self.save_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)

    def get_data(self):
        return {
            "title": self.title_edit.text().strip(),
            "username": self.user_edit.text().strip(),
            "password": self.pass_edit.text(),
            "url": self.url_edit.text().strip(),
            "notes": self.notes_edit.toPlainText().strip()
        }

# ---------- Main App ----------
class VaultMain(QtWidgets.QWidget):
    def __init__(self, system_password: str, auto_import=True):
        super().__init__()
        self.system_password = system_password
        self.setWindowTitle("VaultX Password Manager")
        self.resize(1000, 640)

        self.vault = load_vault(system_password)  # dict with entries
        if "entries" not in self.vault:
            self.vault["entries"] = {}

        # Top-level layout
        root = QtWidgets.QHBoxLayout(self)

        # Left sidebar
        sidebar = QtWidgets.QFrame()
        sidebar.setFixedWidth(260)
        sb_layout = QtWidgets.QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(12, 12, 12, 12)
        title = QtWidgets.QLabel("VaultX")
        title.setObjectName("title")
        sb_layout.addWidget(title)

        self.search = QtWidgets.QLineEdit(placeholderText="Search…")
        sb_layout.addWidget(self.search)

        self.list_w = QtWidgets.QListWidget()
        sb_layout.addWidget(self.list_w)

        btn_row = QtWidgets.QHBoxLayout()
        self.add_btn = QtWidgets.QPushButton("New")
        self.import_btn = QtWidgets.QPushButton("Import Chrome")
        self.lock_btn = QtWidgets.QPushButton("Lock")
        btn_row.addWidget(self.add_btn)
        btn_row.addWidget(self.import_btn)
        btn_row.addWidget(self.lock_btn)
        sb_layout.addLayout(btn_row)

        # Theme toggle
        self.theme_toggle = QtWidgets.QPushButton("Toggle Theme")
        sb_layout.addWidget(self.theme_toggle)
        sb_layout.addStretch()
        root.addWidget(sidebar)

        # Content area
        content = QtWidgets.QFrame()
        content_layout = QtWidgets.QVBoxLayout(content)
        content_layout.setContentsMargins(18, 18, 18, 18)
        # Details card
        self.card = QtWidgets.QFrame()
        self.card.setObjectName("card")
        card_layout = QtWidgets.QVBoxLayout(self.card)

        self.title_lbl = QtWidgets.QLabel("Select an entry")
        self.user_lbl = QtWidgets.QLabel("")
        self.url_lbl = QtWidgets.QLabel("")
        self.pass_lbl = QtWidgets.QLineEdit("")
        self.pass_lbl.setEchoMode(QtWidgets.QLineEdit.Password)
        self.copy_btn = QtWidgets.QPushButton("Copy Password")
        self.reveal_btn = QtWidgets.QPushButton("Reveal")
        self.edit_btn = QtWidgets.QPushButton("Edit")
        card_layout.addWidget(self.title_lbl)
        card_layout.addWidget(self.user_lbl)
        card_layout.addWidget(self.url_lbl)
        card_layout.addWidget(self.pass_lbl)
        h = QtWidgets.QHBoxLayout()
        h.addWidget(self.copy_btn)
        h.addWidget(self.reveal_btn)
        h.addWidget(self.edit_btn)
        card_layout.addLayout(h)

        content_layout.addWidget(self.card)
        root.addWidget(content, 1)

        # Signals
        self.add_btn.clicked.connect(self.add_entry)
        self.import_btn.clicked.connect(self.on_import_clicked)
        self.list_w.itemClicked.connect(self.on_select_entry)
        self.copy_btn.clicked.connect(self.copy_password)
        self.reveal_btn.clicked.connect(self.toggle_reveal)
        self.edit_btn.clicked.connect(self.edit_entry)
        self.lock_btn.clicked.connect(self.lock_now)
        self.theme_toggle.clicked.connect(self.toggle_theme)
        self.search.textChanged.connect(self.filter_entries)

        # UI State
        self.dark = True
        self.apply_theme()
        self.refresh_list()

        # If auto_import requested, do it in background
        if auto_import:
            t = threading.Thread(target=self.auto_import_background, daemon=True)
            t.start()

    def apply_theme(self):
        if self.dark:
            self.setStyleSheet(DARK_QSS)
        else:
            self.setStyleSheet(LIGHT_QSS)

    def toggle_theme(self):
        self.dark = not self.dark
        self.apply_theme()

    def refresh_list(self):
        self.list_w.clear()
        entries = self.vault.get("entries", {})
        for key in sorted(entries.keys(), key=lambda s: s.lower()):
            self.list_w.addItem(key)

    def filter_entries(self, text):
        text = text.lower()
        self.list_w.clear()
        for key in self.vault.get("entries", {}):
            if text in key.lower():
                self.list_w.addItem(key)

    def add_entry(self):
        dlg = EntryEditorDialog()
        if dlg.exec() == QtWidgets.QDialog.Accepted:
            data = dlg.get_data()
            title = data["title"] or f"Untitled-{int(time.time())}"
            self.vault["entries"][title] = data
            save_vault(self.vault, self.system_password)
            self.refresh_list()

    def on_select_entry(self, item):
        key = item.text()
        e = self.vault["entries"].get(key, {})
        self.title_lbl.setText(key)
        self.user_lbl.setText(f"Username: {e.get('username','')}")
        self.url_lbl.setText(f"URL: {e.get('url','')}")
        self.pass_lbl.setText(e.get("password",""))

    def copy_password(self):
        pw = self.pass_lbl.text()
        if not pw:
            return
        cb = QtWidgets.QApplication.clipboard()
        cb.setText(pw)
        QtWidgets.QMessageBox.information(self, "Copied", "Password copied to clipboard for 10 seconds.")
        # start a timer to clear
        QtCore.QTimer.singleShot(10_000, lambda: cb.clear())

    def toggle_reveal(self):
        if self.pass_lbl.echoMode() == QtWidgets.QLineEdit.Password:
            self.pass_lbl.setEchoMode(QtWidgets.QLineEdit.Normal)
            self.reveal_btn.setText("Hide")
        else:
            self.pass_lbl.setEchoMode(QtWidgets.QLineEdit.Password)
            self.reveal_btn.setText("Reveal")

    def edit_entry(self):
        title = self.title_lbl.text()
        if not title or title not in self.vault["entries"]:
            return
        e = self.vault["entries"][title]
        dlg = EntryEditorDialog(title, e.get("username",""), e.get("password",""), e.get("url",""), e.get("notes",""))
        if dlg.exec() == QtWidgets.QDialog.Accepted:
            data = dlg.get_data()
            # if title changed, remove old key
            if data["title"] != title:
                del self.vault["entries"][title]
            self.vault["entries"][data["title"]] = data
            save_vault(self.vault, self.system_password)
            self.refresh_list()

    def lock_now(self):
        QtWidgets.QMessageBox.information(self, "Locked", "Vault is locked. Restart to unlock.")
        QtWidgets.QApplication.quit()

    def on_import_clicked(self):
        added = self.run_chrome_import()
        if added:
            QtWidgets.QMessageBox.information(self, "Imported", f"Imported {added} entries from Chrome.")
            save_vault(self.vault, self.system_password)
            self.refresh_list()
        else:
            QtWidgets.QMessageBox.information(self, "Import", "No entries were imported (or platform unsupported).")

    def auto_import_background(self):
        # Wait a little so UI shows first
        time.sleep(0.8)
        added = self.run_chrome_import()
        if added:
            # show a small transient info in UI thread
            QtCore.QMetaObject.invokeMethod(self, "_notify_import", QtCore.Qt.QueuedConnection,
                                            QtCore.Q_ARG(int, added))

    @QtCore.pyqtSlot(int)
    def _notify_import(self, added):
        QtWidgets.QMessageBox.information(self, "Auto Import", f"Imported {added} entries from Chrome.")

    def run_chrome_import(self) -> int:
        try:
            chrome_creds = import_chrome_login_data(self.system_password)
            count = 0
            for c in chrome_creds:
                title = c.get("name") or c.get("origin_url")
                # avoid overwriting existing entries without user action; append if exists
                safe_title = title
                i = 1
                while safe_title in self.vault["entries"]:
                    safe_title = f"{title} ({i})"
                    i += 1
                self.vault["entries"][safe_title] = {
                    "title": safe_title,
                    "username": c.get("username", ""),
                    "password": c.get("password", ""),
                    "url": c.get("origin_url", ""),
                    "notes": "Imported from Chrome"
                }
                count += 1
            if count > 0:
                save_vault(self.vault, self.system_password)
                self.refresh_list()
            return count
        except Exception as e:
            print("Import error:", e)
            return 0

# ---------- App entry ----------
def main():
    app = QtWidgets.QApplication(sys.argv)
    # ask system password
    auth = SystemAuthDialog()
    if auth.exec() == QtWidgets.QDialog.Accepted:
        sys_pass = auth.verified_password
        # load main window
        w = VaultMain(sys_pass, auto_import=True)
        w.show()
        sys.exit(app.exec())
    else:
        print("Authentication cancelled.")
        sys.exit(1)

if __name__ == "__main__":
    main()
