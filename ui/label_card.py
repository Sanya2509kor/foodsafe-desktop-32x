# ui/label_card.py
from PyQt5.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal

from ui.styles import CARD_QSS
from PyQt5.QtCore import QSize
from ui.icons import icon


class LabelCard(QFrame):
    print_requested = pyqtSignal(dict)  # передаём данные метки
    add_to_cart_requested = pyqtSignal(dict)

    def __init__(self, label):
        super().__init__()
        self.label = label
        self.setFrameShape(QFrame.StyledPanel)
        self.setProperty('class', 'card')
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        self.setMinimumWidth(200)
        self.setMaximumWidth(320)
        self._build()
        

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)   # компактнее
        layout.setSpacing(4)

        # Название — крупнее
        name = QLabel(self.label['name'])
        name.setProperty('class', 'card-title')
        name.setWordWrap(True)
        name.setMaximumHeight(48)   # 2 строки примерно
        name.setStyleSheet('font-size: 20px; font-weight: 700;')   # +шрифт
        name.setToolTip(self.label['name'])   # полный текст при наведении
        layout.addWidget(name)

        # Категория — крупнее
        cat = self.label.get('category')
        if cat:
            badge = QLabel(cat['name'])
            badge.setStyleSheet(
                f"background-color: {cat['color']}; color: white; "
                f"padding: 3px 10px; border-radius: 8px; "
                f"font-size: 12px; font-weight: 600;"       # +шрифт
            )
            badge.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
            layout.addWidget(badge)

        # Мета — крупнее
        temp = QLabel(f"🌡 {self.label.get('storage_temperature', '-')}")
        temp.setProperty('class', 'card-meta')
        temp.setStyleSheet('font-size: 13px;')              # +шрифт
        layout.addWidget(temp)

        period = QLabel(f"⏱ {self.label.get('storage_period_text', '-')}")
        period.setProperty('class', 'card-meta')
        period.setStyleSheet('font-size: 13px;')
        layout.addWidget(period)

        if self.label.get('marked_by'):
            who = QLabel(f"👤 {self.label['marked_by']}")
            who.setProperty('class', 'card-meta')
            who.setStyleSheet('font-size: 12px;')
            layout.addWidget(who)

        layout.addStretch()

        # Кнопки — крупнее для тача
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        print_btn = QPushButton(' Печать')
        print_btn.setIcon(icon('printer'))
        print_btn.setIconSize(QSize(18, 18))
        print_btn.setProperty('class', 'success')
        print_btn.setMinimumHeight(42)   # +высота для пальца
        print_btn.setStyleSheet('font-size: 18px;')
        print_btn.clicked.connect(lambda: self.print_requested.emit(self.label))
        btn_row.addWidget(print_btn, 1)

        cart_btn = QPushButton()
        cart_btn.setIcon(icon('shopping-cart', '#212529', 18))
        cart_btn.setIconSize(QSize(18, 18))
        cart_btn.setProperty('class', 'secondary')
        cart_btn.setToolTip('В корзину')
        cart_btn.setFixedWidth(48)
        cart_btn.setMinimumHeight(42)   # +высота
        cart_btn.setStyleSheet('font-size: 16px;')
        cart_btn.clicked.connect(lambda: self.add_to_cart_requested.emit(self.label))
        btn_row.addWidget(cart_btn)

        layout.addLayout(btn_row)