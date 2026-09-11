# ui/cart_window.py
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QWidget, QFrame, QMessageBox, QSpinBox
)
from PyQt5.QtCore import Qt

import settings
import local_db
from ui.styles import MAIN_QSS, DARK_QSS


class CartWindow(QDialog):
    def __init__(self, parent, cart_data, establishment,
                 print_callback, print_batch_callback, sync_callback=None):
        super().__init__(parent)
        self.cart_data = cart_data
        self.establishment = establishment
        self.print_callback = print_callback
        self.print_batch_callback = print_batch_callback
        self.sync_callback = sync_callback

        theme = settings.load_config().get('theme', 'light')
        self.setStyleSheet(DARK_QSS if theme == 'dark' else MAIN_QSS)
        self.setWindowTitle(f"Корзина — {establishment['name']}")
        self.resize(720, 620)

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel(f"🛒 Корзина — {self.establishment['name']}")
        title.setProperty('class', 'title')
        layout.addWidget(title)

        self.subtitle = QLabel()
        self.subtitle.setProperty('class', 'subtitle')
        layout.addWidget(self.subtitle)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.inner = QWidget()
        self.inner_layout = QVBoxLayout(self.inner)
        self.inner_layout.setSpacing(8)
        self.scroll.setWidget(self.inner)
        layout.addWidget(self.scroll, 1)

        # Кнопки
        btn_row = QHBoxLayout()
        
        # Синхронизация корзины с сервером
        sync_btn = QPushButton('🔄 Синхронизировать с сервером')
        sync_btn.setProperty('class', 'secondary')
        sync_btn.clicked.connect(self._sync_from_server)
        btn_row.addWidget(sync_btn)

        clear_btn = QPushButton('🗑 Очистить')
        clear_btn.setProperty('class', 'danger')
        clear_btn.clicked.connect(self._clear_cart)
        btn_row.addWidget(clear_btn)

        btn_row.addStretch()

        close_btn = QPushButton('Закрыть')
        close_btn.setProperty('class', 'secondary')
        close_btn.clicked.connect(self.reject)
        btn_row.addWidget(close_btn)

        self.print_all_btn = QPushButton('🖨 Печать всех')
        self.print_all_btn.setProperty('class', 'success')
        self.print_all_btn.clicked.connect(self._print_all)
        btn_row.addWidget(self.print_all_btn)

        layout.addLayout(btn_row)

        self._reload()

    # ---------- Список ----------

    def _reload(self):
        """Перечитывает корзину из БД и перерисовывает список."""
        items = local_db.get_cart(self.establishment['id'])
        total = sum(i['quantity'] for i in items)
        self.cart_data = {
            'items': items,
            'total_count': total,
            'unique_count': len(items),
        }

        self.subtitle.setText(
            f"Всего: {total} шт. ({len(items)} видов)"
        )
        self.print_all_btn.setEnabled(total > 0)

        # Очищаем
        while self.inner_layout.count():
            child = self.inner_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        if not items:
            empty = QLabel('Корзина пуста')
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet('color: #6c757d; padding: 40px;')
            self.inner_layout.addWidget(empty)
        else:
            for item in items:
                self.inner_layout.addWidget(self._build_item(item))

        self.inner_layout.addStretch()

    def _build_item(self, item):
        f = QFrame()
        f.setProperty('class', 'cart-item')
        lay = QHBoxLayout(f)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(10)

        left = QVBoxLayout()
        name = QLabel(item['name'])
        name.setStyleSheet('font-weight: 600; font-size: 15px;')
        left.addWidget(name)

        meta = QLabel(
            f"{item.get('storage_temperature', '')}  •  "
            f"{item.get('storage_period_text', '')}"
        )
        meta.setProperty('class', 'card-meta')
        left.addWidget(meta)
        lay.addLayout(left, 1)

        # Количество
        qty = QSpinBox()
        qty.setRange(0, 999)
        qty.setValue(item['quantity'])
        qty.setMinimumWidth(70)
        qty.valueChanged.connect(
            lambda val, iid=item['id']: self._on_quantity_changed(iid, val)
        )
        lay.addWidget(qty)

        # Печать одной позиции (все штуки)
        print_btn = QPushButton('Печать')
        print_btn.setProperty('class', 'success')
        print_btn.clicked.connect(lambda: self._print_one(item))
        lay.addWidget(print_btn)

        # Удалить
        del_btn = QPushButton('🗑')
        del_btn.setProperty('class', 'secondary')
        del_btn.setFixedWidth(40)
        del_btn.setToolTip('Удалить из корзины')
        del_btn.clicked.connect(lambda: self._remove_item(item['id']))
        lay.addWidget(del_btn)

        return f

    # ---------- Действия ----------

    def _on_quantity_changed(self, item_id, value):
        local_db.cart_update_quantity(item_id, value)
        # обновим заголовок без полной перерисовки
        items = local_db.get_cart(self.establishment['id'])
        total = sum(i['quantity'] for i in items)
        self.subtitle.setText(f"Всего: {total} шт. ({len(items)} видов)")
        self.print_all_btn.setEnabled(total > 0)

    def _remove_item(self, item_id):
        local_db.cart_remove(item_id)
        self._reload()

    def _clear_cart(self):
        if not self.cart_data.get('items'):
            return
        reply = QMessageBox.question(
            self, 'Очистить корзину?',
            'Удалить все позиции из корзины?',
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            local_db.cart_clear(self.establishment['id'])
            self._reload()

    def _print_one(self, item):
        label = self._cart_item_to_label(item)
        # печатаем столько раз, сколько quantity
        for _ in range(item['quantity']):
            self.print_callback(label)

    def _print_all(self):
        items = self.cart_data.get('items', [])
        if not items:
            QMessageBox.information(self, 'Корзина пуста', 'Нечего печатать')
            return

        labels = []
        for item in items:
            for _ in range(item['quantity']):
                labels.append(self._cart_item_to_label(item))

        self.print_batch_callback(labels)

    def _cart_item_to_label(self, item):
        return {
            'id': item.get('label_id'),
            'name': item['name'],
            'storage_temperature': item.get('storage_temperature', ''),
            'storage_period_text': item.get('storage_period_text', ''),
            'storage_duration': item.get('storage_duration') or 0,
            'duration_unit': item.get('duration_unit') or 'hours',
            'marked_by': item.get('marked_by', ''),
        }
        
    def _sync_from_server(self):
        """Перезаписывает локальную корзину серверной."""
        reply = QMessageBox.question(
            self, 'Синхронизировать корзину?',
            'Локальные позиции будут удалены, корзина заменится той, '
            'что на сервере. Продолжить?',
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        if self.sync_callback is None:
            QMessageBox.warning(self, 'Недоступно',
                                'Синхронизация недоступна')
            return

        # Колбэк делает свою работу (в т.ч. показывает ошибки при необходимости)
        self.sync_callback()

        # Перечитываем корзину из БД — она уже обновлена
        self._reload()