# ui/create_label_dialog.py
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QComboBox, QSpinBox, QPushButton,
    QMessageBox, QCheckBox, QDateTimeEdit,
)
from PyQt5.QtCore import Qt, QDateTime

import settings
from ui.styles import MAIN_QSS, DARK_QSS


class CreateLabelDialog(QDialog):
    """
    Диалог создания маркировки.
    Возвращает dict с данными при accept().
    """

    def __init__(self, parent, establishment, categories, employees,
                 current_employee_id=None):
        super().__init__(parent)
        self.establishment = establishment
        self.categories = categories        # список dict
        self.employees = employees          # список dict
        self.current_employee_id = current_employee_id

        self.setWindowTitle(f'Новая маркировка — {establishment["name"]}')
        theme = settings.load_config().get('theme', 'light')
        self.setStyleSheet(DARK_QSS if theme == 'dark' else MAIN_QSS)
        self.setMinimumWidth(480)

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        title = QLabel('Новая маркировка')
        title.setProperty('class', 'title')
        layout.addWidget(title)

        subtitle = QLabel(f'Заведение: {self.establishment["name"]}')
        subtitle.setProperty('class', 'subtitle')
        layout.addWidget(subtitle)

        layout.addSpacing(8)

        form = QFormLayout()
        form.setSpacing(10)

        # --- Название ---
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText('Например: Салат Цезарь')
        self.name_input.setMaxLength(200)
        form.addRow('Название *', self.name_input)

        # --- Категория ---
        self.category_combo = QComboBox()
        self.category_combo.addItem('Без категории', userData=None)
        for c in self.categories:
            self.category_combo.addItem(c['name'], userData=c['id'])
        form.addRow('Категория', self.category_combo)

        # --- Температура ---
        self.temp_input = QLineEdit('+4°C до +6°C')
        self.temp_input.setMaxLength(50)
        form.addRow('Темп. хранения', self.temp_input)

        # --- Срок хранения ---
        row = QHBoxLayout()
        self.duration_input = QSpinBox()
        self.duration_input.setRange(1, 10000)
        self.duration_input.setValue(24)
        self.duration_input.setMinimumWidth(100)
        row.addWidget(self.duration_input)

        self.unit_combo = QComboBox()
        self.unit_combo.addItem('часов', userData='hours')
        self.unit_combo.addItem('суток', userData='days')
        row.addWidget(self.unit_combo)
        row.addStretch()
        form.addRow('Срок хранения *', row)

        # --- Сотрудник (кто маркирует) ---
        self.employee_combo = QComboBox()
        self.employee_combo.addItem('— не выбран —', userData=None)
        for e in self.employees:
            label = e['name']
            if e.get('position'):
                label += f" ({e['position']})"
            self.employee_combo.addItem(label, userData=e['id'])

        # Предустановить текущего сотрудника
        if self.current_employee_id:
            for i in range(self.employee_combo.count()):
                if self.employee_combo.itemData(i) == self.current_employee_id:
                    self.employee_combo.setCurrentIndex(i)
                    break
        form.addRow('Создал', self.employee_combo)

        layout.addLayout(form)

        layout.addSpacing(10)

        # Кнопки
        btns = QHBoxLayout()
        btns.addStretch()

        cancel_btn = QPushButton('Отмена')
        cancel_btn.setProperty('class', 'secondary')
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(cancel_btn)

        self.create_btn = QPushButton('✅ Создать')
        self.create_btn.setProperty('class', 'success')
        self.create_btn.clicked.connect(self._on_create)
        btns.addWidget(self.create_btn)

        layout.addLayout(btns)

        self.name_input.setFocus()
        self.name_input.returnPressed.connect(self._on_create)

    def _on_create(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, 'Заполните поле',
                                'Название не может быть пустым')
            self.name_input.setFocus()
            return

        duration = self.duration_input.value()
        if duration <= 0:
            QMessageBox.warning(self, 'Ошибка',
                                'Срок хранения должен быть больше 0')
            return

        self.result_data = {
            'name': name,
            'category_id': self.category_combo.currentData(),
            'storage_temperature': self.temp_input.text().strip() or '+4°C до +6°C',
            'storage_duration': duration,
            'duration_unit': self.unit_combo.currentData(),
            'employee_id': self.employee_combo.currentData(),
        }
        self.accept()