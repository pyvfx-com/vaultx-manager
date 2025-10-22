from PyQt5 import QtWidgets


class EntryEditorDialog(QtWidgets.QDialog):
    """Dialog for creating or editing a vault entry."""

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
        """Return user-inputted entry data."""
        return {
            "title": self.title_edit.text().strip(),
            "username": self.user_edit.text().strip(),
            "password": self.pass_edit.text(),
            "url": self.url_edit.text().strip(),
            "notes": self.notes_edit.toPlainText().strip(),
        }
