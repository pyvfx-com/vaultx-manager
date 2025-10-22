DARK_QSS = """
QWidget {
    background: #121212;
    color: #e5e5e5;
    font-family: "Segoe UI", Roboto, Arial;
}
QPushButton {
    background: #1f1f1f;
    border: 1px solid #2b2b2b;
    padding: 6px 10px;
    border-radius: 8px;
}
QPushButton:hover {
    background: #2b2b2b;
}
QLineEdit, QPlainTextEdit, QTextEdit {
    background: #171717;
    border: 1px solid #2b2b2b;
    padding: 6px;
    border-radius: 6px;
}
QListWidget {
    background: transparent;
    border: none;
}
QListWidget::item {
    padding: 10px;
    border-radius: 6px;
}
QListWidget::item:selected {
    background: #262626;
}
QLabel#title {
    font-size: 18px;
    font-weight: 600;
}
QFrame#card {
    background: #141414;
    border: 1px solid #232323;
    border-radius: 10px;
    padding: 12px;
}
"""

LIGHT_QSS = """
QWidget {
    background: #f7f7f7;
    color: #111;
    font-family: "Segoe UI", Roboto, Arial;
}
QPushButton {
    background: #ffffff;
    border: 1px solid #ddd;
    padding: 6px 10px;
    border-radius: 8px;
}
QPushButton:hover {
    background: #f0f0f0;
}
QLineEdit, QPlainTextEdit, QTextEdit {
    background: #fff;
    border: 1px solid #ddd;
    padding: 6px;
    border-radius: 6px;
}
QListWidget {
    background: transparent;
    border: none;
}
QListWidget::item {
    padding: 10px;
    border-radius: 6px;
}
QListWidget::item:selected {
    background: #e9e9e9;
}
QLabel#title {
    font-size: 18px;
    font-weight: 600;
}
QFrame#card {
    background: #ffffff;
    border: 1px solid #eee;
    border-radius: 10px;
    padding: 12px;
}
"""
