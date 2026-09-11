# ui/employees_dialog.py
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QPushButton, QScrollArea, QWidget,
    QFrame, QMessageBox, QInputDialog
)
from PyQt5.QtCore import Qt

import settings
import local_db
from api_client import ApiClient, ApiError
from ui.styles import MAIN_QSS, DARK_QSS


class EmployeesDialog(QDialog):
    def __init__(self, parent, api, establishment):
        super().__init__(parent)
        self.api = api
        self.est = establishment
        self.est_id = establishment['id']

        self.setWindowTitle(f'Сотрудники — {establishment["name"]}')
        theme = settings.load_config().get('theme', 'light')
        self.setStyleSheet(DARK_QSS if theme == 'dark' else MAIN_QSS)
        self.resize(560, 640)

        self._build_ui()
        self._reload()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        title = QLabel(f'👥 Сотрудники — {self.est["name"]}')
        title.setProperty('class', 'title')
        layout.addWidget(title)

        # Скролл со списком
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.inner = QWidget()
        self.inner_layout = QVBoxLayout(self.inner)
        self.inner_layout.setSpacing(6)
        self.scroll.setWidget(self.inner)
        layout.addWidget(self.scroll, 1)

        # Кнопки
        btn_row = QHBoxLayout()
        add_btn = QPushButton('➕  Добавить')
        add_btn.setProperty('class', 'success')
        add_btn.clicked.connect(self._add_employee)
        btn_row.addWidget(add_btn)

        btn_row.addStretch()

        close_btn = QPushButton('Закрыть')
        close_btn.setProperty('class', 'secondary')
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)

        layout.addLayout(btn_row)

    def _reload(self):
        # Читаем из локальной БД
        employees = local_db.get_employees(self.est_id)

        while self.inner_layout.count():
            child = self.inner_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        if not employees:
            empty = QLabel('Сотрудников нет')
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet('color: #6c757d; padding: 40px;')
            self.inner_layout.addWidget(empty)
        else:
            for emp in employees:
                self.inner_layout.addWidget(self._build_item(emp))

        self.inner_layout.addStretch()

    def _build_item(self, emp):
        f = QFrame()
        f.setProperty('class', 'cart-item')
        lay = QHBoxLayout(f)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(8)

        left = QVBoxLayout()
        name = QLabel(emp['name'])
        style = 'font-weight: 600; font-size: 15px;'
        if not emp.get('is_active'):
            style += ' color: #adb5bd;'
        name.setStyleSheet(style)
        left.addWidget(name)

        if emp.get('position'):
            pos = QLabel(emp['position'])
            pos.setStyleSheet('color: #6c757d; font-size: 12px;')
            left.addWidget(pos)

        lay.addLayout(left, 1)

        # Статус
        status = QLabel('Активен' if emp.get('is_active') else 'Отключён')
        status.setStyleSheet(
            'background: #198754; color: white; padding: 2px 8px; border-radius: 8px;'
            if emp.get('is_active') else
            'background: #6c757d; color: white; padding: 2px 8px; border-radius: 8px;'
        )
        lay.addWidget(status)

        # Кнопка toggle
        toggle_btn = QPushButton('⏸' if emp.get('is_active') else '▶')
        toggle_btn.setProperty('class', 'secondary')
        toggle_btn.setFixedWidth(36)
        toggle_btn.setToolTip('Включить/отключить')
        toggle_btn.clicked.connect(lambda: self._toggle(emp))
        lay.addWidget(toggle_btn)

        # Редактировать
        edit_btn = QPushButton('✏')
        edit_btn.setProperty('class', 'secondary')
        edit_btn.setFixedWidth(36)
        edit_btn.clicked.connect(lambda: self._edit(emp))
        lay.addWidget(edit_btn)

        # Удалить
        del_btn = QPushButton('🗑')
        del_btn.setProperty('class', 'secondary')
        del_btn.setFixedWidth(36)
        del_btn.clicked.connect(lambda: self._delete(emp))
        lay.addWidget(del_btn)

        return f

    # ---------- Действия ----------

    def _add_employee(self):
        name, ok = QInputDialog.getText(self, 'Новый сотрудник', 'Имя:')
        if not ok or not name.strip():
            return
        position, ok = QInputDialog.getText(self, 'Должность', 'Должность (необязательно):')
        if not ok:
            position = ''

        try:
            self.api.employee_create(self.est_id, name.strip(), position.strip())
        except ApiError as e:
            QMessageBox.warning(self, 'Ошибка', str(e))
            return

        # Обновим локально
        self._sync_local()
        self._reload()

    def _edit(self, emp):
        name, ok = QInputDialog.getText(
            self, 'Изменить имя', 'Имя:', text=emp['name']
        )
        if not ok or not name.strip():
            return
        position, ok = QInputDialog.getText(
            self, 'Изменить должность', 'Должность:',
            text=emp.get('position', '') or ''
        )
        if not ok:
            position = emp.get('position', '')

        try:
            self.api.employee_update(self.est_id, emp['id'], name.strip(), position.strip())
        except ApiError as e:
            QMessageBox.warning(self, 'Ошибка', str(e))
            return

        self._sync_local()
        self._reload()

    def _delete(self, emp):
        reply = QMessageBox.question(
            self, 'Удалить сотрудника?',
            f'Удалить "{emp["name"]}"?',
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        try:
            self.api.employee_delete(self.est_id, emp['id'])
        except ApiError as e:
            QMessageBox.warning(self, 'Ошибка', str(e))
            return
        self._sync_local()
        self._reload()

    def _toggle(self, emp):
        try:
            self.api.employee_toggle(self.est_id, emp['id'])
        except ApiError as e:
            QMessageBox.warning(self, 'Ошибка', str(e))
            return
        self._sync_local()
        self._reload()

    def _sync_local(self):
        """Обновить сотрудников из API в локальную БД."""
        try:
            data = self.api.employees(self.est_id)
            local_db.save_employees(self.est_id, data['employees'])
        except ApiError:
            pass