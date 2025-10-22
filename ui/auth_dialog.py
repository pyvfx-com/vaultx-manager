from PyQt5 import QtWidgets
from utils.system_auth import verify_system_password


class SystemAuthDialog(QtWidgets.QDialog):
    """Dialog asking for system password to unlock the vault."""

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
        """Check the entered system password."""
        password = self.pass_input.text().strip()
        if not password:
            QtWidgets.QMessageBox.warning(self, "Missing", "Enter a password.")
            return

        self.info_label.setText("Verifying...")
        QtWidgets.QApplication.processEvents()

        if verify_system_password(password):
            self.verified_password = password
            self.accept()
        else:
            self.info_label.setText("System authentication failed.")
            QtWidgets.QMessageBox.critical(self, "Auth Failed", "System authentication failed.")
