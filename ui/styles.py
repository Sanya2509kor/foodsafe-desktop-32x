# ui/styles.py

# ---------- Общая база (светлая) ----------
BASE_LIGHT = """
* { font-family: 'Segoe UI', Arial; font-size: 14px; }

QMainWindow, QWidget#centralWidget {
    background-color: #f5f7fa;
    color: #212529;
}

QFrame#topbar {
    background-color: #ffffff;
    border-bottom: 1px solid #e9ecef;
}
QFrame#topbar2 {
    background-color: #ffffff;
    border-bottom: 1px solid #e9ecef;
}

QFrame#sidebar {
    background-color: #ffffff;
    border: 1px solid #e9ecef;
    border-radius: 10px;
}

QLabel#brand {
    color: #0d6efd;
    font-size: 20px;
    font-weight: 800;
    padding-right: 10px;
}

QLabel.field-label {
    color: #6c757d;
    font-size: 12px;
    font-weight: 600;
    padding-left: 4px;
}

QLabel.hint {
    color: #6c757d;
    font-size: 11px;
}

QLabel.empty {
    color: #6c757d;
    font-size: 15px;
    padding: 40px;
}

QPushButton {
    background-color: #0d6efd;
    color: white;
    border: none;
    padding: 8px 14px;
    border-radius: 8px;
    font-weight: 600;
}
QPushButton:hover { background-color: #0b5ed7; }
QPushButton:pressed { background-color: #0a58ca; }
QPushButton:disabled { background-color: #b6c2cf; color: #f2f4f7; }

QPushButton.secondary {
    background-color: #eef1f5;
    color: #212529;
}
QPushButton.secondary:hover { background-color: #e2e6ea; }
QPushButton.secondary:checked {
    background-color: #d0e2ff;
    color: #0a58ca;
}

QPushButton.success { background-color: #198754; }
QPushButton.success:hover { background-color: #157347; }

QPushButton.danger { background-color: #dc3545; }
QPushButton.danger:hover { background-color: #bb2d3b; }

QPushButton.icon-btn {
    min-width: 36px;
    max-width: 36px;
    min-height: 34px;
    padding: 4px;
    font-size: 16px;
}

QLineEdit, QComboBox, QSpinBox, QPlainTextEdit, QDateEdit, QDateTimeEdit {
    background-color: #ffffff;
    border: 1px solid #ced4da;
    border-radius: 8px;
    padding: 6px 10px;
    selection-background-color: #0d6efd;
    selection-color: white;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
    border-color: #86b7fe;
}
QComboBox::drop-down { border: none; width: 24px; }
QComboBox QAbstractItemView {
    background: #ffffff;
    border: 1px solid #ced4da;
    selection-background-color: #e7f1ff;
    selection-color: #0d6efd;
    outline: none;
}

QListWidget {
    background: #ffffff;
    border: none;
    padding: 4px;
    outline: none;
}
QListWidget::item {
    padding: 8px 12px;
    border-radius: 6px;
    color: #212529;
}
QListWidget::item:hover { background: #f1f5fb; }
QListWidget::item:selected {
    background: #e7f1ff;
    color: #0d6efd;
    font-weight: 600;
}

QScrollArea { border: none; background: transparent; }

QStatusBar {
    background: #ffffff;
    border-top: 1px solid #e9ecef;
    color: #6c757d;
}

QProgressDialog {
    background: #ffffff;
}

QDialog {
    background-color: #f5f7fa;
    color: #212529;
}

QFrame.card {
    background: #ffffff;
    border: 1px solid #e9ecef;
    border-radius: 10px;
}
QFrame.card:hover {
    border-color: #0d6efd;
    background: #f8fbff;
}
QLabel.card-title {
    font-size: 15px;
    font-weight: 700;
    color: #212529;
}
QLabel.card-meta {
    font-size: 12px;
    color: #6c757d;
}
"""

MAIN_QSS = BASE_LIGHT

CARD_QSS = """
QFrame.card {
    background: #ffffff;
    border: 1px solid #e9ecef;
    border-radius: 10px;
}
QFrame.card:hover {
    border-color: #0d6efd;
    background: #f8fbff;
}
QLabel.card-title {
    font-size: 15px;
    font-weight: 700;
    color: #212529;
}
QLabel.card-meta {
    font-size: 12px;
    color: #6c757d;
}
"""

CART_QSS = """
QFrame.cart-item {
    background: #ffffff;
    border: 1px solid #e9ecef;
    border-radius: 8px;
}
"""


# ---------- Тёмная тема ----------
DARK_QSS = """
* { font-family: 'Segoe UI', Arial; font-size: 14px; }

QMainWindow, QWidget#centralWidget {
    background-color: #1a1d21;
    color: #e6e8eb;
}

QFrame#topbar {
    background-color: #24282e;
    border-bottom: 1px solid #343a40;
}
QFrame#topbar2 {
    background-color: #24282e;
    border-bottom: 1px solid #343a40;
}

QFrame#sidebar {
    background-color: #24282e;
    border: 1px solid #343a40;
    border-radius: 10px;
}

QLabel#brand {
    color: #4dabf7;
    font-size: 20px;
    font-weight: 800;
    padding-right: 10px;
}

QLabel {
    color: #e6e8eb;
    background: transparent;
}

QLabel.field-label {
    color: #9aa4af;
    font-size: 12px;
    font-weight: 600;
    padding-left: 4px;
}

QLabel.hint {
    color: #9aa4af;
    font-size: 11px;
}

QLabel.empty {
    color: #9aa4af;
    font-size: 15px;
    padding: 40px;
}

QPushButton {
    background-color: #0d6efd;
    color: white;
    border: none;
    padding: 8px 14px;
    border-radius: 8px;
    font-weight: 600;
}
QPushButton:hover { background-color: #0b5ed7; }
QPushButton:pressed { background-color: #0a58ca; }
QPushButton:disabled { background-color: #3a3f46; color: #7d868e; }

QPushButton.secondary {
    background-color: #343a40;
    color: #e6e8eb;
}
QPushButton.secondary:hover { background-color: #3d444d; }
QPushButton.secondary:checked {
    background-color: #1c4b8e;
    color: #d0e2ff;
}

QPushButton.success { background-color: #198754; }
QPushButton.success:hover { background-color: #157347; }

QPushButton.danger { background-color: #dc3545; }
QPushButton.danger:hover { background-color: #bb2d3b; }

QPushButton.icon-btn {
    min-width: 36px;
    max-width: 36px;
    min-height: 34px;
    padding: 4px;
    font-size: 16px;
}

QLineEdit, QComboBox, QSpinBox, QPlainTextEdit, QDateEdit, QDateTimeEdit {
    background-color: #2f343b;
    border: 1px solid #454c55;
    border-radius: 8px;
    padding: 6px 10px;
    color: #e6e8eb;
    selection-background-color: #0d6efd;
    selection-color: white;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
    border-color: #4dabf7;
}
QLineEdit::placeholder { color: #7d868e; }
QComboBox::drop-down { border: none; width: 24px; }
QComboBox QAbstractItemView {
    background: #2f343b;
    border: 1px solid #454c55;
    selection-background-color: #1c4b8e;
    selection-color: #d0e2ff;
    color: #e6e8eb;
    outline: none;
}

QListWidget {
    background: #24282e;
    border: none;
    padding: 4px;
    color: #e6e8eb;
    outline: none;
}
QListWidget::item {
    padding: 8px 12px;
    border-radius: 6px;
    color: #e6e8eb;
}
QListWidget::item:hover { background: #2f343b; }
QListWidget::item:selected {
    background: #1c4b8e;
    color: #d0e2ff;
    font-weight: 600;
}

QScrollArea { border: none; background: transparent; }

QStatusBar {
    background: #24282e;
    border-top: 1px solid #343a40;
    color: #9aa4af;
}

QProgressDialog {
    background: #24282e;
    color: #e6e8eb;
}

QDialog {
    background-color: #1a1d21;
    color: #e6e8eb;
}

QFrame.card {
    background: #24282e;
    border: 1px solid #343a40;
    border-radius: 10px;
}
QFrame.card:hover {
    border-color: #4dabf7;
    background: #2b3037;
}
QLabel.card-title {
    font-size: 15px;
    font-weight: 700;
    color: #f1f3f5;
}
QLabel.card-meta {
    font-size: 12px;
    color: #9aa4af;
}

QFrame.cart-item {
    background: #24282e;
    border: 1px solid #343a40;
    border-radius: 8px;
}

QMessageBox {
    background-color: #24282e;
}
QMessageBox QLabel { color: #e6e8eb; }
QMessageBox QPushButton { min-width: 80px; }

QToolTip {
    background-color: #2f343b;
    color: #e6e8eb;
    border: 1px solid #454c55;
    padding: 4px;
}
"""