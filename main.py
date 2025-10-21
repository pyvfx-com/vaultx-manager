import sys
from PyQt5 import QtWidgets
from utils.dialogs import SystemAuthDialog
from ui.mainUI import VaultXUI

def main():
    app = QtWidgets.QApplication(sys.argv)
    dlg = SystemAuthDialog()
    if dlg.exec():
        win = VaultXUI(dlg.verified_password)
        win.show()
        sys.exit(app.exec())
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()
