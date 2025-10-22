import sys
from PyQt5 import QtWidgets
from ui.auth_dialog import SystemAuthDialog
from ui.main_window import VaultMain

def main():
    app = QtWidgets.QApplication(sys.argv)
    auth = SystemAuthDialog()
    if auth.exec() == QtWidgets.QDialog.Accepted:
        sys_pass = auth.verified_password
        w = VaultMain(sys_pass, auto_import=True)
        w.show()
        sys.exit(app.exec())
    else:
        print("Authentication cancelled.")
        sys.exit(1)

if __name__ == "__main__":
    main()
