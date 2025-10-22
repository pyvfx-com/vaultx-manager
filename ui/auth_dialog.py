from PyQt5 import QtWidgets
from utils.system_auth import verify_system_password

class SystemAuthDialog(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Unlock VaultX")
        self.resize(420, 160)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel("Enter your system password:"))
        self.pass_input = QtWidgets.QLineEdit()
        self.pass_input.setEchoMode(QtWidgets.QLineEdit.Password)
        layout.addWidget(self.pass_input)
        self.info_label = QtWidgets.QLabel("")
        layout.addWidget(self.info_label)

        btns = QtWidgets.QHBoxLayout()
        self.unlock_btn = QtWidgets.QPushButton("Unlock")
        self.cancel_btn = QtWidgets.QPushButton("Cancel")
        btns.addWidget(self.unlock_btn)
        btns.addWidget(self.cancel_btn)
        layout.addLayout(btns)

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
        if verify_system_password(pwd):
            self.verified_password = pwd
            self.accept()
        else:
            QtWidgets.QMessageBox.critical(self, "Auth Failed", "Verification failed.")
