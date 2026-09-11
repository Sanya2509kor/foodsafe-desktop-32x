# ui/categories_dialog.py
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QWidget, QFrame, QMessageBox, QInputDialog,
    QColorDialog
)
from PyQt5.QtCore import Qt

import settings
import local_db
from api_client import ApiClient, ApiError
from ui.styles import MAIN_QSS, DARK_QSS


class CategoriesDialog(QDialog):
    def __init__(self, parent, api, establishment):
        super().__init__(parent)
        self.api = api
        self.est = establishment
        self.est_id = establishment['id']

        self.setWindowTitle(f'Категории — {establishment["name"]}')
        theme = settings.load_config().get('theme', 'light')
        self.setStyleSheet(DARK_QSS if theme == 'dark' else MAIN_QSS)
        self.resize(560, 640)

        self._build_ui()
        self._reload()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        title = QLabel(f'🏷 Категории — {self.est["name"]}')
        title.setProperty('class', 'title')
        layout.addWidget(title)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.inner = QWidget()
        self.inner_layout = QVBoxLayout(self.inner)
        self.inner_layout.setSpacing(6)
        self.scroll.setWidget(self.inner)
        layout.addWidget(self.scroll, 1)

        btn_row = QHBoxLayout()
        add_btn = QPushButton('➕  Добавить')
        add_btn.setProperty('class', 'success')
        add_btn.clicked.connect(self._add_category)
        btn_row.addWidget(add_btn)

        btn_row.addStretch()

        close_btn = QPushButton('Закрыть')
        close_btn.setProperty('class', 'secondary')
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)

        layout.addLayout(btn_row)

    def _reload(self):
        cats = local_db.get_categories(self.est_id)

        while self.inner_layout.count():
            child = self.inner_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        if not cats:
            empty = QLabel('Категорий нет')
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet('color: #6c757d; padding: 40px;')
            self.inner_layout.addWidget(empty)
        else:
            for c in cats:
                self.inner_layout.addWidget(self._build_item(c))

        self.inner_layout.addStretch()

    def _build_item(self, cat):
        f = QFrame()
        f.setProperty('class', 'cart-item')
        lay = QHBoxLayout(f)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(8)

        color_dot = QLabel()
        color_dot.setFixedSize(20, 20)
        color_dot.setStyleSheet(
            f'background: {cat["color"]}; border-radius: 10px;'
        )
        lay.addWidget(color_dot)

        left = QVBoxLayout()
        name = QLabel(cat['name'])
        style = 'font-weight: 600; font-size: 15px;'
        if not cat.get('is_active'):
            style += ' color: #adb5bd;'
        name.setStyleSheet(style)
        left.addWidget(name)
        lay.addLayout(left, 1)

        status = QLabel('Активна' if cat.get('is_active') else 'Выкл.')
        status.setStyleSheet(
            'background: #198754; color: white; padding: 2px 8px; border-radius: 8px;'
            if cat.get('is_active') else
            'background: #6c757d; color: white; padding: 2px 8px; border-radius: 8px;'
        )
        lay.addWidget(status)

        toggle_btn = QPushButton('⏸' if cat.get('is_active') else '▶')
        toggle_btn.setProperty('class', 'secondary')
        toggle_btn.setFixedWidth(36)
        toggle_btn.clicked.connect(lambda: self._toggle(cat))
        lay.addWidget(toggle_btn)

        edit_btn = QPushButton('✏')
        edit_btn.setProperty('class', 'secondary')
        edit_btn.setFixedWidth(36)
        edit_btn.clicked.connect(lambda: self._edit(cat))
        lay.addWidget(edit_btn)

        del_btn = QPushButton('🗑')
        del_btn.setProperty('class', 'secondary')
        del_btn.setFixedWidth(36)
        del_btn.clicked.connect(lambda: self._delete(cat))
        lay.addWidget(del_btn)

        return f

    # ---------- Действия ----------

    def _add_category(self):
        name, ok = QInputDialog.getText(self, 'Новая категория', 'Название:')
        if not ok or not name.strip():
            return
        color = QColorDialog.getColor()
        color_hex = color.name() if color.isValid() else '#6c757d'

        try:
            self.api.category_create(self.est_id, name.strip(), color_hex, 0)
        except ApiError as e:
            QMessageBox.warning(self, 'Ошибка', str(e))
            return
        self._sync_local()
        self._reload()

    def _edit(self, cat):
        name, ok = QInputDialog.getText(
            self, 'Изменить название', 'Название:', text=cat['name']
        )
        if not ok or not name.strip():
            return

        color = QColorDialog.getColor()
        color_hex = color.name() if color.isValid() else cat['color']

        try:
            self.api.category_update(self.est_id, cat['id'], name.strip(),
                                     color_hex, cat.get('order', 0))
        except ApiError as e:
            QMessageBox.warning(self, 'Ошибка', str(e))
            return
        self._sync_local()
        self._reload()

    def _delete(self, cat):
        reply = QMessageBox.question(
            self, 'Удалить категорию?',
            f'Удалить "{cat["name"]}"?\n'
            f'У всех маркировок этой категории категория будет снята.',
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        try:
            self.api.category_delete(self.est_id, cat['id'])
        except ApiError as e:
            QMessageBox.warning(self, 'Ошибка', str(e))
            return
        self._sync_local()
        self._reload()

    def _toggle(self, cat):
        try:
            self.api.category_toggle(self.est_id, cat['id'])
        except ApiError as e:
            QMessageBox.warning(self, 'Ошибка', str(e))
            return
        self._sync_local()
        self._reload()

    def _sync_local(self):
        try:
            data = self.api.categories(self.est_id)
            local_db.save_categories(self.est_id, data['categories'])
        except ApiError:
            pass