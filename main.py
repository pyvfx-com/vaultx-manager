import sys
from PyQt5 import QtWidgets
from ui.auth_dialog import SystemAuthDialog
from ui.main_window import VaultMain


def main():
    """Entry point for VaultX."""
    app = QtWidgets.QApplication(sys.argv)
    auth = SystemAuthDialog()

    if auth.exec() == QtWidgets.QDialog.Accepted:
        sys_pass = auth.verified_password
        window = VaultMain(sys_pass, auto_import=True)
        window.show()
        sys.exit(app.exec())
    else:
        print("Authentication cancelled.")
        sys.exit(1)


if __name__ == "__main__":
    main()
