from PyQt5 import QtWidgets, QtCore
from ..utils._utils import load_vault, save_vault, import_chrome_login_data
from ..utils.dialogs import EntryDialog, SettingsDialog
from ..utils.themes import DARK_QSS, LIGHT_QSS


class VaultXUI(QtWidgets.QWidget):
    def __init__(self, password: str):
        super().__init__()
        self.setWindowTitle("VaultX - Secure Password Manager")
        self.resize(1080, 680)
        self.password = password
        self.vault = load_vault(password)

        # Layout setup
        main = QtWidgets.QHBoxLayout(self)
        sidebar = QtWidgets.QFrame(); sidebar.setFixedWidth(300)
        sbl = QtWidgets.QVBoxLayout(sidebar)
        self.search = QtWidgets.QLineEdit(placeholderText="Search entries...")
        sbl.addWidget(self.search)
        self.list = QtWidgets.QListWidget()
        sbl.addWidget(self.list, 1)
        add = QtWidgets.QPushButton("➕ New")
        import_btn = QtWidgets.QPushButton("📥 Import Chrome")
        sbl.addWidget(add); sbl.addWidget(import_btn)
        main.addWidget(sidebar)

        # Right Panel
        panel = QtWidgets.QFrame(); main.addWidget(panel, 1)
        v = QtWidgets.QVBoxLayout(panel)
        self.title = QtWidgets.QLabel("Select an entry"); v.addWidget(self.title)
        self.user = QtWidgets.QLineEdit(); self.user.setReadOnly(True); v.addWidget(self.user)
        self.passw = QtWidgets.QLineEdit(); self.passw.setEchoMode(QtWidgets.QLineEdit.Password); self.passw.setReadOnly(True); v.addWidget(self.passw)
        self.notes = QtWidgets.QPlainTextEdit(); self.notes.setReadOnly(True); v.addWidget(self.notes)
        self.theme_toggle = QtWidgets.QPushButton("🌓 Toggle Theme"); v.addWidget(self.theme_toggle)
        self.dark = True
        self.setStyleSheet(DARK_QSS)

        self.refresh()
        add.clicked.connect(self.new_entry)
        import_btn.clicked.connect(self.import_chrome)
        self.list.itemClicked.connect(self.show_entry)
        self.theme_toggle.clicked.connect(self.toggle_theme)
        self.search.textChanged.connect(self.filter_entries)

    def refresh(self):
        self.list.clear()
        for t in sorted(self.vault.get("entries", {})):
            self.list.addItem(t)

    def new_entry(self):
        d = EntryDialog()
        if d.exec():
            data = d.get_data()
            self.vault["entries"][data["title"]] = data
            save_vault(self.vault, self.password)
            self.refresh()

    def import_chrome(self):
        imported = import_chrome_login_data()
        if imported:
            for e in imported:
                self.vault["entries"][e["name"]] = e
            save_vault(self.vault, self.password)
            self.refresh()
            QtWidgets.QMessageBox.information(self, "Imported", f"Imported {len(imported)} entries.")
        else:
            QtWidgets.QMessageBox.information(self, "Import", "No Chrome data found.")

    def show_entry(self, item):
        e = self.vault["entries"][item.text()]
        self.title.setText(e["title"])
        self.user.setText(e["username"])
        self.passw.setText(e["password"])
        self.notes.setPlainText(e["notes"])

    def toggle_theme(self):
        self.dark = not self.dark
        self.setStyleSheet(DARK_QSS if self.dark else LIGHT_QSS)

    def filter_entries(self, text):
        text = text.lower()
        self.list.clear()
        for t in self.vault["entries"]:
            if text in t.lower():
                self.list.addItem(t)
