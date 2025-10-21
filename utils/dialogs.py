from PyQt5 import QtWidgets, QtCore
from ._utils import verify_system_password

class SystemAuthDialog(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Unlock VaultX")
        self.resize(400, 160)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel("Enter your system password:"))
        self.input = QtWidgets.QLineEdit()
        self.input.setEchoMode(QtWidgets.QLineEdit.Password)
        layout.addWidget(self.input)
        btns = QtWidgets.QHBoxLayout()
        ok = QtWidgets.QPushButton("Unlock")
        cancel = QtWidgets.QPushButton("Cancel")
        btns.addWidget(ok); btns.addWidget(cancel)
        layout.addLayout(btns)
        ok.clicked.connect(self.verify)
        cancel.clicked.connect(self.reject)
        self.verified_password = None

    def verify(self):
        pwd = self.input.text().strip()
        if verify_system_password(pwd):
            self.verified_password = pwd
            self.accept()
        else:
            QtWidgets.QMessageBox.critical(self, "Error", "Invalid system password")

class SettingsDialog(QtWidgets.QDialog):
    def __init__(self, timeout=180, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        layout = QtWidgets.QFormLayout(self)
        self.timeout_spin = QtWidgets.QSpinBox()
        self.timeout_spin.setRange(30, 3600)
        self.timeout_spin.setValue(timeout)
        layout.addRow("Auto-lock (seconds):", self.timeout_spin)
        self.anim_check = QtWidgets.QCheckBox("Enable animations")
        self.anim_check.setChecked(True)
        layout.addRow("", self.anim_check)
        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        layout.addWidget(btns)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)

    def get_settings(self):
        return {"auto_lock": self.timeout_spin.value(), "animations": self.anim_check.isChecked()}

class EntryDialog(QtWidgets.QDialog):
    def __init__(self, title="", user="", pwd="", url="", notes=""):
        super().__init__()
        self.setWindowTitle("Add/Edit Entry")
        layout = QtWidgets.QFormLayout(self)
        self.t = QtWidgets.QLineEdit(title)
        self.u = QtWidgets.QLineEdit(user)
        self.p = QtWidgets.QLineEdit(pwd)
        self.p.setEchoMode(QtWidgets.QLineEdit.Password)
        self.url = QtWidgets.QLineEdit(url)
        self.n = QtWidgets.QPlainTextEdit(notes)
        layout.addRow("Title:", self.t)
        layout.addRow("Username:", self.u)
        layout.addRow("Password:", self.p)
        layout.addRow("URL:", self.url)
        layout.addRow("Notes:", self.n)
        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        layout.addWidget(btns)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)

    def get_data(self):
        return dict(title=self.t.text(), username=self.u.text(), password=self.p.text(), url=self.url.text(), notes=self.n.toPlainText())
