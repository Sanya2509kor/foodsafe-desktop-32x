# ui/blocked_dialog.py
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

import settings
from ui.styles import build_qss


class BlockedDialog(QDialog):
    """
    Модальное окно, если заведение заблокировано.
    Закрыть можно, но приложение останется недоступным.
    """

    def __init__(self, parent, establishment, reason='expired'):
        super().__init__(parent)
        self.est = establishment
        self.reason = reason

        self.setWindowTitle('Подписка истекла')
        theme = settings.load_config().get('theme', 'light')
        self.setStyleSheet(build_qss(theme, 1.2))  # крупный шрифт
        self.setMinimumWidth(520)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(16)

        # --- Иконка-замок ---
        icon = QLabel('🔒')
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet('font-size: 64px;')
        layout.addWidget(icon)

        # --- Заголовок ---
        title = QLabel('Доступ к заведению приостановлен')
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet('font-size: 22px; font-weight: 800; color: #dc3545;')
        title.setWordWrap(True)
        layout.addWidget(title)

        # --- Название заведения ---
        name = QLabel(f'Заведение: «{establishment["name"]}»')
        name.setAlignment(Qt.AlignCenter)
        name.setStyleSheet('font-size: 16px; color: #495057;')
        name.setWordWrap(True)
        layout.addWidget(name)

        # --- Пояснение ---
        if reason == 'expired':
            if establishment.get('paid_until'):
                text = (f'Подписка закончилась '
                        f'{establishment["paid_until"]}.\n'
                        f'Обратитесь к владельцу заведения или '
                        f'продлите подписку на сайте.')
            else:
                text = ('Подписка на это заведение не активна.\n'
                        'Продлите её на сайте.')
        else:
            text = 'Заведение заблокировано.'

        msg = QLabel(text)
        msg.setAlignment(Qt.AlignCenter)
        msg.setStyleSheet('font-size: 14px; color: #6c757d;')
        msg.setWordWrap(True)
        layout.addWidget(msg)

        # --- Кнопки ---
        btns = QHBoxLayout()
        btns.addStretch()

        sync_btn = QPushButton('🔄 Проверить ещё раз')
        sync_btn.setProperty('class', 'secondary')
        sync_btn.setMinimumHeight(44)
        sync_btn.clicked.connect(self.reject)

        btns.addWidget(sync_btn)

        close_btn = QPushButton('Закрыть')
        close_btn.setProperty('class', 'secondary')
        close_btn.setMinimumHeight(44)
        close_btn.clicked.connect(self.reject)
        btns.addWidget(close_btn)

        btns.addStretch()
        layout.addLayout(btns)