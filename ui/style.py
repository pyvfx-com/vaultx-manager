DARK_QSS = """
QWidget {
    background-color: #111;
    color: #E0E0E0;
    font-family: "Segoe UI", Roboto, Arial;
    font-size: 14px;
}

QFrame#card {
    background-color: #1B1B1B;
    border-radius: 12px;
    border: 1px solid #2A2A2A;
    padding: 16px;
}

QPushButton {
    background-color: #232323;
    border: 1px solid #333;
    padding: 6px 10px;
    border-radius: 8px;
}
QPushButton:hover { background-color: #303030; }
QPushButton:pressed { background-color: #383838; }

QLineEdit, QPlainTextEdit {
    background-color: #1A1A1A;
    border: 1px solid #333;
    padding: 6px;
    border-radius: 6px;
    selection-background-color: #555;
}

QListWidget {
    background-color: #161616;
    border: none;
    outline: none;
}

QListWidget::item {
    padding: 8px 10px;
    border-radius: 6px;
}

QListWidget::item:selected {
    background-color: #2A2A2A;
    color: #FFA726;
}

QLabel#title {
    font-size: 20px;
    font-weight: 600;
    color: #FFA726;
}
"""

LIGHT_QSS = """
QWidget {
    background-color: #FAFAFA;
    color: #111;
    font-family: "Segoe UI", Roboto, Arial;
    font-size: 14px;
}

QFrame#card {
    background-color: #FFFFFF;
    border-radius: 12px;
    border: 1px solid #DDD;
    padding: 16px;
}

QPushButton {
    background-color: #FFFFFF;
    border: 1px solid #CCC;
    padding: 6px 10px;
    border-radius: 8px;
}
QPushButton:hover { background-color: #F2F2F2; }
QPushButton:pressed { background-color: #E8E8E8; }

QLineEdit, QPlainTextEdit {
    background-color: #FFF;
    border: 1px solid #CCC;
    padding: 6px;
    border-radius: 6px;
    selection-background-color: #E0E0E0;
}

QListWidget {
    background-color: transparent;
    border: none;
    outline: none;
}

QListWidget::item {
    padding: 8px 10px;
    border-radius: 6px;
}

QListWidget::item:selected {
    background-color: #E3E3E3;
    color: #FF6F00;
}

QLabel#title {
    font-size: 20px;
    font-weight: 600;
    color: #FF6F00;
}
"""
