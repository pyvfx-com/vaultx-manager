import os
import time
import threading
from PyQt5 import QtWidgets, QtCore, QtGui

from ui.entry_editor import EntryEditorDialog
from ui.style import DARK_QSS, LIGHT_QSS
from utils.vault_storage import load_vault, save_vault
from utils.chrome_import import import_chrome_login_data


class VaultMain(QtWidgets.QWidget):
    """VaultX main window — frameless with custom title bar."""
    def __init__(self, system_password: str, auto_import=True):
        super().__init__()
        self._normal_geometry = None
        self.system_password = system_password
        self.setWindowTitle("VaultX Password Manager")

        # Frameless, translucent, resizable window
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowSystemMenuHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.resize(1180, 740)

        # Track dragging
        self._drag_pos = None
        self._maximized = False

        # Load vault
        self.vault = load_vault(system_password)
        if "entries" not in self.vault:
            self.vault["entries"] = {}

        # Outer layout
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)

        # Shadow frame for rounded window
        self.shadow_frame = QtWidgets.QFrame()
        self.shadow_frame.setObjectName("mainFrame")
        self.shadow_frame.setStyleSheet("""
            QFrame#mainFrame {
                background-color: #121212;
                border-radius: 14px;
                border: 1px solid #2A2A2A;
            }
        """)
        outer.addWidget(self.shadow_frame)

        main_layout = QtWidgets.QVBoxLayout(self.shadow_frame)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- Custom Title Bar ---
        title_bar = self._create_title_bar()
        main_layout.addWidget(title_bar)

        # --- Main Content Area ---
        content_area = QtWidgets.QHBoxLayout()
        content_area.setContentsMargins(0, 0, 0, 0)
        sidebar = self._create_sidebar()
        view = self._create_content_view()
        content_area.addWidget(sidebar)
        content_area.addWidget(view, 1)
        main_layout.addLayout(content_area)

        # Theme and initial setup
        self.dark = True
        self.apply_theme()
        self.refresh_list()

        if auto_import:
            threading.Thread(target=self.auto_import_background, daemon=True).start()

    # ====================== TITLE BAR ======================
    def _create_title_bar(self):
        bar = QtWidgets.QFrame()
        bar.setFixedHeight(48)
        bar.setObjectName("titleBar")
        bar.setStyleSheet("""
            QFrame#titleBar {
                background-color: #1A1A1A;
                border-top-left-radius: 14px;
                border-top-right-radius: 14px;
            }
        """)

        layout = QtWidgets.QHBoxLayout(bar)
        layout.setContentsMargins(12, 0, 12, 0)

        # Left: app icon
        icon_label = QtWidgets.QLabel()
        icon_path = os.path.join("icons", "vault.png")
        if os.path.exists(icon_path):
            pixmap = QtGui.QPixmap(icon_path).scaled(28, 28, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
            icon_label.setPixmap(pixmap)
        layout.addWidget(icon_label)

        # Center: title
        self.title_label = QtWidgets.QLabel("VaultX Password Manager")
        self.title_label.setAlignment(QtCore.Qt.AlignCenter)
        self.title_label.setStyleSheet("font-size:16px; color:#FFA726; font-weight:600;")
        layout.addWidget(self.title_label, 1)

        # Right: window buttons
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.setSpacing(6)

        self.min_btn = self._title_button("—")
        self.max_btn = self._title_button("⬜")
        self.close_btn = self._title_button("✖")

        btn_layout.addWidget(self.min_btn)
        btn_layout.addWidget(self.max_btn)
        btn_layout.addWidget(self.close_btn)

        layout.addLayout(btn_layout)

        # Button actions
        self.min_btn.clicked.connect(self.showMinimized)
        self.max_btn.clicked.connect(self.toggle_maximize)
        self.close_btn.clicked.connect(QtWidgets.QApplication.quit)

        # Allow drag
        bar.mousePressEvent = self.mousePressEvent
        bar.mouseMoveEvent = self.mouseMoveEvent
        bar.mouseReleaseEvent = self.mouseReleaseEvent

        return bar

    @staticmethod
    def _title_button(text):
        btn = QtWidgets.QPushButton(text)
        btn.setFixedSize(28, 28)
        btn.setCursor(QtCore.Qt.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #222;
                border: none;
                border-radius: 6px;
                color: #AAA;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #333; color: #FFA726; }
            QPushButton:pressed { background-color: #444; }
        """)
        return btn

    # ====================== Frameless Window Dragging ======================
    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() == QtCore.Qt.LeftButton and not self._maximized:
            self.move(event.globalPos() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def toggle_maximize(self):
        if not self._maximized:
            self._normal_geometry = self.geometry()
            self.showMaximized()
            self._maximized = True
            self.max_btn.setText("🗗")
        else:
            self.setGeometry(self._normal_geometry)
            self.showNormal()
            self._maximized = False
            self.max_btn.setText("⬜")

    # ====================== Sidebar ======================
    def _create_sidebar(self):
        sidebar = QtWidgets.QFrame()
        sidebar.setFixedWidth(280)
        sidebar.setStyleSheet("""
            QFrame {
                background-color: #181818;
                border-right: 1px solid #222;
            }
        """)
        layout = QtWidgets.QVBoxLayout(sidebar)
        layout.setContentsMargins(16, 18, 16, 16)
        layout.setSpacing(10)

        self.search = QtWidgets.QLineEdit()
        self.search.setPlaceholderText("🔍 Search entries...")
        self.search.setStyleSheet("""
            QLineEdit {
                background-color: #202020;
                border: 1px solid #2E2E2E;
                border-radius: 8px;
                color: #DDD;
                padding: 6px 8px;
            }
            QLineEdit:focus { border: 1px solid #FFA726; }
        """)
        layout.addWidget(self.search)

        self.list_w = QtWidgets.QListWidget()
        self.list_w.setStyleSheet("""
            QListWidget {
                background-color: #181818;
                border: none;
                color: #EEE;
                selection-background-color: #FFA726;
                selection-color: #121212;
                outline: none;
            }
            QListWidget::item {
                padding: 8px 10px;
                border-radius: 6px;
            }
            QListWidget::item:hover { background-color: #242424; }
        """)
        layout.addWidget(self.list_w, 1)

        btn_row = QtWidgets.QHBoxLayout()
        self.add_btn = self._side_button("➕ New")
        self.import_btn = self._side_button("🌐 Import")
        self.lock_btn = self._side_button("🔒 Lock")
        for b in (self.add_btn, self.import_btn, self.lock_btn):
            btn_row.addWidget(b)
        layout.addLayout(btn_row)

        self.theme_toggle = self._side_button("🌓 Theme")
        layout.addWidget(self.theme_toggle)

        # Signals
        self.add_btn.clicked.connect(self.add_entry)
        self.import_btn.clicked.connect(self.on_import_clicked)
        self.list_w.itemClicked.connect(self.on_select_entry)
        self.lock_btn.clicked.connect(self.lock_now)
        self.theme_toggle.clicked.connect(self.toggle_theme)
        self.search.textChanged.connect(self.filter_entries)
        return sidebar

    @staticmethod
    def _side_button(text):
        btn = QtWidgets.QPushButton(text)
        btn.setCursor(QtCore.Qt.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #222;
                border: 1px solid #333;
                color: #DDD;
                border-radius: 8px;
                padding: 6px 8px;
            }
            QPushButton:hover { background-color: #2A2A2A; color: #FFA726; }
        """)
        return btn

    # ====================== Content / View ======================
    def _create_content_view(self):
        content = QtWidgets.QFrame()
        content.setStyleSheet("background-color: #141414; border: none;")
        layout = QtWidgets.QVBoxLayout(content)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(18)

        self.title_lbl = QtWidgets.QLabel("Select an entry")
        self.title_lbl.setStyleSheet("font-size: 22px; font-weight: 600; color: #FFA726;")
        layout.addWidget(self.title_lbl)

        self.user_lbl = self._info_label("👤 Username: —")
        self.url_lbl = self._info_label("🌐 URL: —")
        layout.addWidget(self.user_lbl)
        layout.addWidget(self.url_lbl)

        layout.addWidget(QtWidgets.QLabel("🔑 Password:"))
        self.pass_lbl = QtWidgets.QLineEdit("")
        self.pass_lbl.setEchoMode(QtWidgets.QLineEdit.Password)
        self.pass_lbl.setReadOnly(True)
        self.pass_lbl.setStyleSheet("""
            QLineEdit {
                background-color: #1E1E1E;
                border: 1px solid #333;
                border-radius: 8px;
                padding: 6px;
                color: #FFA726;
                font-size: 15px;
            }
        """)
        layout.addWidget(self.pass_lbl)

        layout.addWidget(QtWidgets.QLabel("📝 Notes:"))
        self.notes_area = QtWidgets.QTextEdit()
        self.notes_area.setReadOnly(True)
        self.notes_area.setStyleSheet("""
            QTextEdit {
                background-color: #1A1A1A;
                border: 1px solid #333;
                border-radius: 10px;
                padding: 8px;
                color: #DDD;
                font-size: 14px;
            }
        """)
        layout.addWidget(self.notes_area, 1)

        btn_row = QtWidgets.QHBoxLayout()
        btn_row.addStretch()
        self.copy_btn = self._styled_btn("📋 Copy")
        self.reveal_btn = self._styled_btn("👁 Reveal")
        self.edit_btn = self._styled_btn("✏️ Edit")
        for b in (self.copy_btn, self.reveal_btn, self.edit_btn):
            btn_row.addWidget(b)
        layout.addLayout(btn_row)

        self.copy_btn.clicked.connect(self.copy_password)
        self.reveal_btn.clicked.connect(self.toggle_reveal)
        self.edit_btn.clicked.connect(self.edit_entry)
        return content

    @staticmethod
    def _styled_btn(text):
        btn = QtWidgets.QPushButton(text)
        btn.setCursor(QtCore.Qt.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #222;
                border: 1px solid #333;
                border-radius: 8px;
                padding: 6px 14px;
                color: #EEE;
            }
            QPushButton:hover { background-color: #2E2E2E; color: #FFA726; }
        """)
        return btn

    @staticmethod
    def _info_label(text):
        lbl = QtWidgets.QLabel(text)
        lbl.setStyleSheet("font-size: 15px; color: #DDD; padding: 3px;")
        return lbl

    # ====================== Logic (unchanged core) ======================
    def apply_theme(self): self.setStyleSheet(DARK_QSS if self.dark else LIGHT_QSS)
    def toggle_theme(self): self.dark = not self.dark; self.apply_theme()
    def refresh_list(self):
        self.list_w.clear()
        for key in sorted(self.vault.get("entries", {}), key=str.lower):
            self.list_w.addItem(key)
    def filter_entries(self, text):
        text = text.lower().strip()
        self.list_w.clear()
        for k in self.vault.get("entries", {}):
            if text in k.lower():
                self.list_w.addItem(k)
        if self.list_w.count() == 0:
            item = QtWidgets.QListWidgetItem("(No matches found)")
            item.setFlags(QtCore.Qt.NoItemFlags)
            self.list_w.addItem(item)
    def add_entry(self):
        dlg = EntryEditorDialog()
        if dlg.exec() == QtWidgets.QDialog.Accepted:
            data = dlg.get_data()
            title = data["title"] or f"Untitled-{int(time.time())}"
            self.vault["entries"][title] = data
            save_vault(self.vault, self.system_password)
            self.refresh_list()
    def on_select_entry(self, item):
        key = item.text()
        e = self.vault["entries"].get(key, {})
        self.title_lbl.setText(e.get("title", key))
        self.user_lbl.setText(f"👤 Username: <b>{e.get('username','')}</b>")
        self.url_lbl.setText(f"🌐 URL: <a href='{e.get('url','')}'>{e.get('url','')}</a>")
        self.url_lbl.setOpenExternalLinks(True)
        self.pass_lbl.setText(e.get("password",""))
        self.notes_area.setText(e.get("notes",""))
    def edit_entry(self):
        title = self.title_lbl.text()
        if not title or title not in self.vault["entries"]: return
        e = self.vault["entries"][title]
        dlg = EntryEditorDialog(title, e.get("username",""), e.get("password",""), e.get("url",""), e.get("notes",""))
        if dlg.exec() == QtWidgets.QDialog.Accepted:
            data = dlg.get_data()
            if data["title"] != title:
                del self.vault["entries"][title]
            self.vault["entries"][data["title"]] = data
            save_vault(self.vault, self.system_password)
            self.refresh_list()
    def copy_password(self):
        pw = self.pass_lbl.text()
        if not pw: return
        cb = QtWidgets.QApplication.clipboard()
        cb.setText(pw)
        QtWidgets.QMessageBox.information(self, "Copied", "✅ Password copied for 10 seconds.")
        QtCore.QTimer.singleShot(10_000, cb.clear)
    def toggle_reveal(self):
        if self.pass_lbl.echoMode() == QtWidgets.QLineEdit.Password:
            self.pass_lbl.setEchoMode(QtWidgets.QLineEdit.Normal)
            self.reveal_btn.setText("🙈 Hide")
        else:
            self.pass_lbl.setEchoMode(QtWidgets.QLineEdit.Password)
            self.reveal_btn.setText("👁 Reveal")
    def on_import_clicked(self):
        added = self.run_chrome_import()
        msg = f"✅ Imported {added} entries." if added else "No entries found."
        QtWidgets.QMessageBox.information(self, "Import Chrome", msg)
    def run_chrome_import(self):
        count = 0
        for c in import_chrome_login_data(self.system_password):
            title = c.get("name") or c.get("origin_url") or f"Imported-{int(time.time())}"
            safe_title = title
            i = 1
            while safe_title in self.vault["entries"]:
                safe_title = f"{title} ({i})"; i += 1
            self.vault["entries"][safe_title] = {
                "title": safe_title, "username": c.get("username",""),
                "password": c.get("password",""), "url": c.get("origin_url",""),
                "notes": "Imported from Chrome"
            }; count += 1
        if count: save_vault(self.vault, self.system_password); self.refresh_list()
        return count
    def auto_import_background(self):
        time.sleep(0.5)
        added = self.run_chrome_import()
        if added: QtCore.QMetaObject.invokeMethod(self, "_notify_import", QtCore.Qt.QueuedConnection, QtCore.Q_ARG(int, added))
    @QtCore.pyqtSlot(int)
    def _notify_import(self, added):
        QtWidgets.QMessageBox.information(self, "Auto Import", f"Imported {added} entries from Chrome.")
    def lock_now(self):
        QtWidgets.QMessageBox.information(self, "Locked", "🔒 Vault locked. Restart to unlock.")
        QtWidgets.QApplication.quit()
