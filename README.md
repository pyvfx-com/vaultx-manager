# 🔐 VaultX Password Manager

**VaultX** is a modern, cross-platform password manager built with **Python + PyQt5**.  
It securely stores credentials locally using strong AES encryption (via `cryptography.Fernet`),  
authenticates using your **system login password**, and can **auto-import saved passwords from Google Chrome**.

---

## ✨ Features

✅ **System Authentication**

- Unlocks using your Windows or Linux system password.
- Uses native APIs (`LogonUserW` on Windows, `pam` on Linux).

✅ **End-to-End Encryption**

- AES-256 (Fernet) encryption derived from your system password using PBKDF2.

✅ **Modern UI (PyQt5)**

- Dark / Light themes
- Organized sidebar and details panel
- Fade-in animations using `QPropertyAnimation`

✅ **Chrome Password Import**

- Automatically reads and decrypts saved Chrome credentials.
- Optional auto-import on startup.

✅ **Vault Management**

- Add, edit, delete, and search stored credentials.
- Copy password with auto-clear clipboard (10s timeout).
- Auto-lock after inactivity (configurable).

✅ **Backup & Restore**

- Export your encrypted `.vaultx` file safely.
- Restore from a previous backup anytime.

✅ **Cross-Platform Support**

- 🪟 Windows 10/11
- 🐧 Linux (Ubuntu, Fedora, etc.)
- macOS (limited support, pending keychain integration)

---

## 📦 Installation

Clone the repository and install dependencies.

```bash
git clone https://github.com/<your-username>/vaultx.git
cd vaultx
pip install -r requirements.txt
```

## 📦 Requirements

```bash
PyQt5>=5.15.9
cryptography>=42.0.5
secretstorage>=3.3.3; sys_platform == "linux"
dbus-python>=1.3.2; sys_platform == "linux"
python-pam>=2.0.2; sys_platform == "linux"
pywin32>=306; sys_platform == "win32"
```
