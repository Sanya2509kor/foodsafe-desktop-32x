# ui/label_card.py
from PyQt5.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal

from ui.styles import CARD_QSS


class LabelCard(QFrame):
    print_requested = pyqtSignal(dict)  # передаём данные метки
    add_to_cart_requested = pyqtSignal(dict)

    def __init__(self, label):
        super().__init__()
        self.label = label
        self.setFrameShape(QFrame.StyledPanel)
        self.setProperty('class', 'card')
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.setMinimumWidth(260)
        self.setMaximumWidth(360)

        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)

        # Название
        name = QLabel(self.label['name'])
        name.setProperty('class', 'card-title')
        name.setWordWrap(True)
        layout.addWidget(name)

        # Категория
        cat = self.label.get('category')
        if cat:
            badge = QLabel(cat['name'])
            badge.setStyleSheet(
                f"background-color: {cat['color']}; color: white; "
                f"padding: 2px 8px; border-radius: 8px; font-size: 11px; "
                f"font-weight: 600;"
            )
            badge.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
            layout.addWidget(badge)

        # Мета
        temp = QLabel(f"🌡 {self.label.get('storage_temperature', '-')}")
        temp.setProperty('class', 'card-meta')
        layout.addWidget(temp)

        period = QLabel(f"⏱ {self.label.get('storage_period_text', '-')}")
        period.setProperty('class', 'card-meta')
        layout.addWidget(period)

        if self.label.get('marked_by'):
            who = QLabel(f"👤 {self.label['marked_by']}")
            who.setProperty('class', 'card-meta')
            layout.addWidget(who)

        layout.addStretch()

        # Кнопки
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        print_btn = QPushButton('🖨  Печать')
        print_btn.setProperty('class', 'success')
        print_btn.clicked.connect(lambda: self.print_requested.emit(self.label))
        btn_row.addWidget(print_btn, 1)

        cart_btn = QPushButton('🛒')
        cart_btn.setProperty('class', 'secondary')
        cart_btn.setToolTip('Добавить в корзину')
        cart_btn.setFixedWidth(42)
        cart_btn.clicked.connect(lambda: self.add_to_cart_requested.emit(self.label))
        btn_row.addWidget(cart_btn)

        layout.addLayout(btn_row)