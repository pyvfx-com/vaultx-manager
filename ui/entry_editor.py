from PyQt5 import QtWidgets


class EntryEditorDialog(QtWidgets.QDialog):
    """Dialog for creating or editing a password entry."""
    def __init__(self, title="", username="", password="", url="", notes=""):
        super().__init__()
        self.setWindowTitle("Edit Vault Entry")
        self.resize(480, 380)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(8)

        def add_field(label, widget):
            layout.addWidget(QtWidgets.QLabel(label))
            layout.addWidget(widget)

        self.title_edit = QtWidgets.QLineEdit(title)
        self.user_edit = QtWidgets.QLineEdit(username)
        self.pass_edit = QtWidgets.QLineEdit(password)
        self.pass_edit.setEchoMode(QtWidgets.QLineEdit.Password)
        self.url_edit = QtWidgets.QLineEdit(url)
        self.notes_edit = QtWidgets.QPlainTextEdit(notes)
        self.notes_edit.setPlaceholderText("Optional notes about this entry...")

        add_field("Title", self.title_edit)
        add_field("Username", self.user_edit)
        add_field("Password", self.pass_edit)
        add_field("URL", self.url_edit)
        add_field("Notes", self.notes_edit)

        # Buttons
        btn_row = QtWidgets.QHBoxLayout()
        btn_row.addStretch()
        self.save_btn = QtWidgets.QPushButton("💾 Save")
        self.cancel_btn = QtWidgets.QPushButton("✖ Cancel")
        btn_row.addWidget(self.save_btn)
        btn_row.addWidget(self.cancel_btn)
        layout.addLayout(btn_row)

        self.save_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)

    def get_data(self):
        """Return collected data as dict."""
        return {
            "title": self.title_edit.text().strip(),
            "username": self.user_edit.text().strip(),
            "password": self.pass_edit.text(),
            "url": self.url_edit.text().strip(),
            "notes": self.notes_edit.toPlainText().strip()
        }
