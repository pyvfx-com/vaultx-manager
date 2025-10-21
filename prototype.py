import os
import sys
import json
import hashlib
import base64
from PySide2 import QtWidgets, QtCore, QtGui


# -----------------------------
# Simple Encryption (XOR + Base64)
# -----------------------------
def simple_encrypt(data: str, pin: str) -> str:
    key = hashlib.sha256(pin.encode()).digest()
    enc = bytes([b ^ key[i % len(key)] for i, b in enumerate(data.encode())])
    return base64.b64encode(enc).decode()


def simple_decrypt(data: str, pin: str) -> str:
    key = hashlib.sha256(pin.encode()).digest()
    dec = base64.b64decode(data)
    out = bytes([b ^ key[i % len(key)] for i, b in enumerate(dec)])
    return out.decode()


def get_pin_hash(pin):
    return hashlib.sha256(pin.encode()).hexdigest()


def verify_pin(pin, stored_hash):
    return get_pin_hash(pin) == stored_hash


# -----------------------------
# PIN Dialog with Show/Hide Toggle
# -----------------------------
class PinDialog(QtWidgets.QDialog):
    def __init__(self, pin_file, mode="enter"):
        super().__init__()
        self.pin_file = pin_file
        self.setWindowTitle("🔐 Enter PIN")
        self.setFixedSize(300, 130)

        layout = QtWidgets.QVBoxLayout(self)
        self.label = QtWidgets.QLabel()
        layout.addWidget(self.label)

        pin_layout = QtWidgets.QHBoxLayout()
        self.pin_edit = QtWidgets.QLineEdit()
        self.pin_edit.setEchoMode(QtWidgets.QLineEdit.Password)
        self.show_pin_btn = QtWidgets.QToolButton()
        self.show_pin_btn.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_DialogYesButton))
        self.show_pin_btn.setCheckable(True)
        self.show_pin_btn.setToolTip("Show/Hide PIN")
        self.show_pin_btn.toggled.connect(self.toggle_pin_visibility)
        pin_layout.addWidget(self.pin_edit)
        pin_layout.addWidget(self.show_pin_btn)
        layout.addLayout(pin_layout)

        self.ok_button = QtWidgets.QPushButton("OK")
        layout.addWidget(self.ok_button)

        self.ok_button.clicked.connect(self.accept)

        if not os.path.exists(pin_file):
            self.label.setText("Set a new 4-digit PIN:")
            self.new_pin_mode = True
        else:
            self.new_pin_mode = False
            self.label.setText("Enter PIN:" if mode == "enter" else "Re-enter PIN to unlock:")

    def toggle_pin_visibility(self, checked):
        self.pin_edit.setEchoMode(QtWidgets.QLineEdit.Normal if checked else QtWidgets.QLineEdit.Password)
        icon = self.style().standardIcon(
            QtWidgets.QStyle.SP_DialogNoButton if checked else QtWidgets.QStyle.SP_DialogYesButton
        )
        self.show_pin_btn.setIcon(icon)

    def get_pin(self):
        return self.pin_edit.text()


# -----------------------------
# Note Editor
# -----------------------------
class NoteEditor(QtWidgets.QDialog):
    def __init__(self, title="", content=""):
        super().__init__()
        self.setWindowTitle(title or "New Note")
        layout = QtWidgets.QVBoxLayout(self)
        self.text_edit = QtWidgets.QPlainTextEdit(content)
        self.save_button = QtWidgets.QPushButton("Save")
        layout.addWidget(self.text_edit)
        layout.addWidget(self.save_button)
        self.save_button.clicked.connect(self.accept)

    def get_content(self):
        return self.text_edit.toPlainText()


# -----------------------------
# Change PIN Dialog
# -----------------------------
class ChangePinDialog(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Change PIN")
        self.setFixedSize(300, 200)
        layout = QtWidgets.QFormLayout(self)

        self.old_pin = QtWidgets.QLineEdit()
        self.old_pin.setEchoMode(QtWidgets.QLineEdit.Password)
        self.new_pin = QtWidgets.QLineEdit()
        self.new_pin.setEchoMode(QtWidgets.QLineEdit.Password)
        self.confirm_pin = QtWidgets.QLineEdit()
        self.confirm_pin.setEchoMode(QtWidgets.QLineEdit.Password)
        self.ok_button = QtWidgets.QPushButton("Change")

        layout.addRow("Current PIN:", self.old_pin)
        layout.addRow("New PIN:", self.new_pin)
        layout.addRow("Confirm New PIN:", self.confirm_pin)
        layout.addWidget(self.ok_button)

        self.ok_button.clicked.connect(self.accept)

    def get_pins(self):
        return self.old_pin.text(), self.new_pin.text(), self.confirm_pin.text()


# -----------------------------
# Main Vault App
# -----------------------------
class VaultApp(QtWidgets.QWidget):
    def __init__(self, pin):
        super().__init__()
        self.pin = pin
        self.vault_dir = os.path.join(os.path.expanduser("~"), ".vault_data")
        os.makedirs(self.vault_dir, exist_ok=True)
        self.meta_file = os.path.join(self.vault_dir, "meta.json")
        self.load_meta()

        self.setWindowTitle("🔐 Secure Vault")
        self.resize(750, 480)

        # Layouts
        main_layout = QtWidgets.QVBoxLayout(self)
        top_bar = QtWidgets.QHBoxLayout()
        content_layout = QtWidgets.QHBoxLayout()

        # Top bar widgets
        self.search_bar = QtWidgets.QLineEdit()
        self.search_bar.setPlaceholderText("Search...")
        self.change_pin_button = QtWidgets.QPushButton("Change PIN")
        top_bar.addWidget(self.search_bar)
        top_bar.addWidget(self.change_pin_button)

        # Main content widgets
        self.list_widget = QtWidgets.QListWidget()
        self.create_button = QtWidgets.QPushButton("Create Note")

        # Right-click context menu for list
        self.list_widget.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self.show_context_menu)

        content_layout.addWidget(self.list_widget, 2)
        content_layout.addWidget(self.create_button, 1)

        main_layout.addLayout(top_bar)
        main_layout.addLayout(content_layout)

        # Connections
        self.create_button.clicked.connect(self.create_note)
        self.list_widget.itemDoubleClicked.connect(self.open_note)
        self.search_bar.textChanged.connect(self.filter_notes)
        self.change_pin_button.clicked.connect(self.change_pin)

        self.refresh_list()

    # -----------------------------
    # Metadata
    # -----------------------------
    def load_meta(self):
        if os.path.exists(self.meta_file):
            with open(self.meta_file, "r") as f:
                self.meta = json.load(f)
        else:
            self.meta = {}

    def save_meta(self):
        with open(self.meta_file, "w") as f:
            json.dump(self.meta, f, indent=2)

    def refresh_list(self, filter_text=""):
        self.list_widget.clear()
        for title in sorted(self.meta.keys()):
            if filter_text.lower() in title.lower():
                self.list_widget.addItem(title)

    def filter_notes(self, text):
        self.refresh_list(text)

    # -----------------------------
    # Context Menu
    # -----------------------------
    def show_context_menu(self, pos):
        item = self.list_widget.itemAt(pos)
        if not item:
            return
        menu = QtWidgets.QMenu()
        open_action = menu.addAction("Open")
        delete_action = menu.addAction("Delete")
        action = menu.exec_(self.list_widget.mapToGlobal(pos))
        if action == open_action:
            self.open_note(item)
        elif action == delete_action:
            self.delete_note(item)

    # -----------------------------
    # Create Note
    # -----------------------------
    def create_note(self):
        editor = NoteEditor()
        if editor.exec_():
            content = editor.get_content()
            title, ok = QtWidgets.QInputDialog.getText(self, "Save Note", "Enter title:")
            if ok and title:
                note_path = os.path.join(self.vault_dir, f"{title}.dat")
                enc = simple_encrypt(content, self.pin)
                with open(note_path, "w") as f:
                    f.write(enc)
                self.meta[title] = note_path
                self.save_meta()
                self.refresh_list()

    # -----------------------------
    # Open Note
    # -----------------------------
    def open_note(self, item):
        title = item.text()
        pin_dialog = PinDialog(PIN_FILE, mode="unlock")
        if pin_dialog.exec_():
            entered_pin = pin_dialog.get_pin()
            stored_hash = open(PIN_FILE).read().strip()
            if verify_pin(entered_pin, stored_hash):
                with open(self.meta[title], "r") as f:
                    enc = f.read()
                try:
                    content = simple_decrypt(enc, entered_pin)
                except Exception:
                    QtWidgets.QMessageBox.warning(self, "Error", "Decryption failed.")
                    return
                editor = NoteEditor(title, content)
                editor.exec_()
            else:
                QtWidgets.QMessageBox.warning(self, "Error", "Incorrect PIN.")

    # -----------------------------
    # Delete Note
    # -----------------------------
    def delete_note(self, item):
        title = item.text()
        confirm = QtWidgets.QMessageBox.question(
            self, "Delete Note", f"Are you sure you want to delete '{title}'?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        if confirm == QtWidgets.QMessageBox.Yes:
            if title in self.meta:
                try:
                    os.remove(self.meta[title])
                except Exception:
                    pass
                del self.meta[title]
                self.save_meta()
                self.refresh_list()

    # -----------------------------
    # Change PIN
    # -----------------------------
    def change_pin(self):
        dialog = ChangePinDialog()
        if dialog.exec_():
            old_pin, new_pin, confirm_pin = dialog.get_pins()
            if not all([old_pin, new_pin, confirm_pin]):
                QtWidgets.QMessageBox.warning(self, "Error", "All fields are required.")
                return
            stored_hash = open(PIN_FILE).read().strip()
            if not verify_pin(old_pin, stored_hash):
                QtWidgets.QMessageBox.warning(self, "Error", "Current PIN incorrect.")
                return
            if new_pin != confirm_pin:
                QtWidgets.QMessageBox.warning(self, "Error", "New PINs do not match.")
                return

            for title, path in self.meta.items():
                with open(path, "r") as f:
                    old_enc = f.read()
                content = simple_decrypt(old_enc, old_pin)
                new_enc = simple_encrypt(content, new_pin)
                with open(path, "w") as f:
                    f.write(new_enc)

            with open(PIN_FILE, "w") as f:
                f.write(get_pin_hash(new_pin))
            self.pin = new_pin
            QtWidgets.QMessageBox.information(self, "Success", "PIN changed successfully!")


# -----------------------------
# App Entry
# -----------------------------
PIN_FILE = os.path.join(os.path.expanduser("~"), ".vault_pin")


def main():
    app = QtWidgets.QApplication(sys.argv)

    # Keep asking for PIN until correct or user cancels
    while True:
        pin_dialog = PinDialog(PIN_FILE)
        pin_dialog.setWindowModality(QtCore.Qt.ApplicationModal)
        result = pin_dialog.exec_()

        if result == QtWidgets.QDialog.Accepted:
            pin = pin_dialog.get_pin()

            # --- First-time setup ---
            if pin_dialog.new_pin_mode:
                confirm, ok = QtWidgets.QInputDialog.getText(
                    None, "Confirm PIN", "Re-enter PIN:", QtWidgets.QLineEdit.Password
                )
                if ok and confirm == pin:
                    with open(PIN_FILE, "w") as f:
                        f.write(get_pin_hash(pin))
                    QtWidgets.QMessageBox.information(None, "Success", "PIN set successfully!")
                    break
                else:
                    QtWidgets.QMessageBox.warning(None, "Error", "PINs do not match. Try again.")
                    continue

            # --- Existing user ---
            if not os.path.exists(PIN_FILE):
                QtWidgets.QMessageBox.warning(None, "Error", "PIN file missing. Please reset vault.")
                continue

            stored_hash = open(PIN_FILE).read().strip()
            if verify_pin(pin, stored_hash):
                break
            else:
                QtWidgets.QMessageBox.warning(None, "Incorrect PIN", "Please try again.")
                continue
        else:
            return  # User cancelled

    # Launch main window
    window = VaultApp(pin)
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
