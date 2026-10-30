# ui/settings_dialog.py
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QHBoxLayout,
    QLabel, QSpinBox, QComboBox, QPushButton, QMessageBox, QCheckBox
)
from PyQt5.QtCore import Qt

import settings
from printer import list_printers, get_default_printer
from ui.styles import MAIN_QSS, DARK_QSS


class SettingsDialog(QDialog):
    def __init__(self, parent, config: dict):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle('Настройки приложения')
        theme = config.get('theme', 'light')
        self.setStyleSheet(DARK_QSS if theme == 'dark' else MAIN_QSS)
        self.setMinimumWidth(480)

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel('Настройки')
        title.setProperty('class', 'title')
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(10)

        # --- Принтер ---
        self.printer_combo = QComboBox()
        printers = list_printers()
        if not printers:
            self.printer_combo.addItem('— принтеры не найдены —', userData=None)
        else:
            for p in printers:
                self.printer_combo.addItem(p, userData=p)

        current = self.config.get('printer_name') or get_default_printer()
        if current in printers:
            self.printer_combo.setCurrentIndex(printers.index(current))
        form.addRow('Принтер по умолчанию:', self.printer_combo)

        # --- Пауза между этикетками ---
        self.delay_spin = QSpinBox()
        self.delay_spin.setRange(0, 5000)
        self.delay_spin.setSingleStep(50)
        self.delay_spin.setSuffix(' мс')
        self.delay_spin.setValue(int(self.config.get('print_delay_ms', 300)))
        self.delay_spin.setToolTip(
            'Пауза после каждой этикетки при печати корзины.\n'
            'Увеличьте, если принтер пропускает этикетки.'
        )
        form.addRow('Пауза между этикетками:', self.delay_spin)

        # --- Автосинхронизация (в минутах) ---
        self.auto_sync_spin = QSpinBox()
        self.auto_sync_spin.setRange(0, 1440)
        self.auto_sync_spin.setSingleStep(5)
        self.auto_sync_spin.setSuffix(' мин')
        self.auto_sync_spin.setSpecialValueText('выкл.')
        self.auto_sync_spin.setValue(int(self.config.get('auto_sync_minutes', 0)))
        form.addRow('Автосинхронизация:', self.auto_sync_spin)

        # --- Тема ---
        self.theme_combo = QComboBox()
        self.theme_combo.addItem('Светлая', userData='light')
        self.theme_combo.addItem('Тёмная', userData='dark')
        theme = self.config.get('theme', 'light')
        self.theme_combo.setCurrentIndex(0 if theme == 'light' else 1)
        form.addRow('Тема:', self.theme_combo)
        
        # --- Размер интерфейса ---
        self.scale_combo = QComboBox()
        self.scale_combo.addItem('Обычный', userData='normal')
        self.scale_combo.addItem('Крупный (для слабовидящих)', userData='large')
        self.scale_combo.addItem('Очень крупный', userData='xlarge')
        scale = self.config.get('ui_scale', 'normal')
        idx = {'normal': 0, 'large': 1, 'xlarge': 2}.get(scale, 0)
        self.scale_combo.setCurrentIndex(idx)
        form.addRow('Размер интерфейса:', self.scale_combo)
        
        # --- Удалённая печать с сайта ---
        self.remote_print_check = QCheckBox('Разрешить печать с сайта')
        self.remote_print_check.setChecked(
            bool(self.config.get('remote_print_enabled', True))
        )
        self.remote_print_check.setToolTip(
            'Если включено, планшет будет принимать задания на печать\n'
            'со страницы «Печать» на сайте (с телефона официанта и т.д.).'
        )
        form.addRow('Печать с сайта:', self.remote_print_check)

        layout.addLayout(form)

        hint = QLabel(
            'Подсказка по паузе: если при печати корзины принтер иногда\n'
            'пропускает этикетки — увеличьте до 400–600 мс.'
        )
        hint.setStyleSheet('color: #6c757d; font-size: 11px;')
        layout.addWidget(hint)

        # --- Кнопки ---
        btns = QHBoxLayout()
        btns.addStretch()

        cancel_btn = QPushButton('Отмена')
        cancel_btn.setProperty('class', 'secondary')
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(cancel_btn)

        save_btn = QPushButton('Сохранить')
        save_btn.setProperty('class', 'success')
        save_btn.clicked.connect(self._save)
        btns.addWidget(save_btn)

        layout.addLayout(btns)

    def _save(self):
        printer = self.printer_combo.currentData()
        if printer:
            self.config['printer_name'] = printer

        self.config['print_delay_ms'] = int(self.delay_spin.value())
        self.config['auto_sync_minutes'] = int(self.auto_sync_spin.value())
        self.config['theme'] = self.theme_combo.currentData()
        self.config['ui_scale'] = self.scale_combo.currentData()
        self.config['remote_print_enabled'] = bool(self.remote_print_check.isChecked())

        settings.save_config(self.config)
        self.accept()