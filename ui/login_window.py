# ui/login_window.py
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox,
)

import settings
import local_db
from api_client import ApiClient, ApiError
from sync import sync_all
import settings
from ui.styles import MAIN_QSS, DARK_QSS


class LoginWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.api = None
        self.user_data = None
        self.offline_mode = False
        self.config = settings.load_config()
        local_db.init_db()
        self._build_ui()

    def _build_ui(self):
        self.setWindowTitle('FoodSafe — Подключение')
        self.setMinimumWidth(520)
        theme = settings.load_config().get('theme', 'light')
        self.setStyleSheet(DARK_QSS if theme == 'dark' else MAIN_QSS)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(30, 30, 30, 30)

        title = QLabel('FoodSafe')
        title.setProperty('class', 'title')
        layout.addWidget(title)

        subtitle = QLabel(
            'Введите API-ключ из личного кабинета на сайте. '
            'Данные будут загружены один раз и сохранены локально.'
        )
        subtitle.setProperty('class', 'subtitle')
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        layout.addSpacing(8)

        layout.addWidget(QLabel('Адрес сервера'))
        self.url_input = QLineEdit(self.config['api_url'])
        layout.addWidget(self.url_input)

        layout.addWidget(QLabel('API-ключ'))
        self.key_input = QLineEdit(self.config['api_key'])
        self.key_input.setPlaceholderText('Вставьте ключ, скопированный на сайте')
        layout.addWidget(self.key_input)

        self.status = QLabel('')
        self.status.setWordWrap(True)
        self.status.setStyleSheet('color: #0d6efd; font-size: 12px;')
        layout.addWidget(self.status)

        buttons = QHBoxLayout()

        paste_btn = QPushButton('Вставить из буфера')
        paste_btn.setProperty('class', 'secondary')
        paste_btn.clicked.connect(self._paste_from_clipboard)
        buttons.addWidget(paste_btn)

        # Кнопка "Продолжить оффлайн" — только если есть сохранённые данные
        has_local = bool(local_db.get_establishments())
        if has_local:
            offline_btn = QPushButton('Продолжить оффлайн')
            offline_btn.setProperty('class', 'secondary')
            offline_btn.clicked.connect(self._continue_offline)
            buttons.addWidget(offline_btn)

        buttons.addStretch()

        self.connect_btn = QPushButton('Подключиться и синхронизировать')
        self.connect_btn.clicked.connect(self._connect)
        buttons.addWidget(self.connect_btn)

        layout.addLayout(buttons)

        # Если есть сохранённые данные, покажем последнюю синхронизацию
        if has_local:
            last = local_db.last_sync() or 'никогда'
            info = QLabel(f'Локальные данные от: {last}')
            info.setStyleSheet('color: #6c757d; font-size: 11px;')
            layout.addWidget(info)

        self.key_input.returnPressed.connect(self._connect)

    def _paste_from_clipboard(self):
        from PyQt5.QtWidgets import QApplication
        cb = QApplication.clipboard()
        self.key_input.setText(cb.text().strip())

    def _continue_offline(self):
        self.offline_mode = True
        self.accept()

    def _connect(self):
        url = self.url_input.text().strip()
        key = self.key_input.text().strip()
        if not url or not key:
            self.status.setStyleSheet('color: #dc3545; font-size: 12px;')
            self.status.setText('Заполните оба поля')
            return

        self.connect_btn.setEnabled(False)
        self.status.setStyleSheet('color: #0d6efd; font-size: 12px;')

        try:
            client = ApiClient(url, key)
            client.me()  # проверка ключа
        except ApiError as e:
            self.status.setStyleSheet('color: #dc3545; font-size: 12px;')
            self.status.setText(str(e))
            self.connect_btn.setEnabled(True)
            return

        # Сохраняем конфиг
        self.config['api_url'] = url
        self.config['api_key'] = key
        settings.save_config(self.config)

        # Синхронизация
        try:
            sync_all(client, status_cb=self._set_status)
        except ApiError as e:
            self.status.setStyleSheet('color: #dc3545; font-size: 12px;')
            self.status.setText(f'Ошибка синхронизации: {e}')
            self.connect_btn.setEnabled(True)
            return

        self.api = client
        self.accept()

    def _set_status(self, text):
        self.status.setStyleSheet('color: #0d6efd; font-size: 12px;')
        self.status.setText(text)
        self.repaint()