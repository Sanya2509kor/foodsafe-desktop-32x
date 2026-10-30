from PyQt5.QtWidgets import (
    QLineEdit, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QPushButton, QListWidget, QListWidgetItem,
    QScrollArea, QFrame, QMessageBox, QGridLayout, QSizePolicy,
    QInputDialog, QProgressDialog
)
from PyQt5.QtWidgets import QSystemTrayIcon, QMenu, QAction, QStyle
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QTimer, QSize, QEvent, QObject, QThreadPool
from datetime import datetime, timedelta

import settings
import local_db
from api_client import ApiClient, ApiError
from sync import sync_all
from printer import list_printers, get_default_printer, print_image_tspl
from ui.styles import MAIN_QSS
from ui.label_card import LabelCard
from ui.cart_window import CartWindow
import os
import tempfile
from ui.styles import MAIN_QSS, DARK_QSS
from ui.create_label_dialog import CreateLabelDialog
from label_renderer import render_label_pixmap
from typing import Optional
from ui.icons import icon
from ui.styles import build_qss


class MainWindow(QMainWindow):
    def __init__(self, api: Optional[ApiClient], offline: bool = False):
        super().__init__()
        self.api = api
        self.offline = offline
        self.config = settings.load_config()
        self.current_est = None
        self.categories = []
        self.labels = []
        self.selected_category = 'all'
        self.search_text = ''
        
        # Таймер "тишины" — 2 секунды без действий = можно опрашивать сервер
        self._idle_timer = QTimer(self)
        self._idle_timer.setSingleShot(True)
        self._idle_timer.setInterval(2000)   # 2 секунды
        self._idle_timer.timeout.connect(self._on_idle)
        
        self._thread_pool = QThreadPool.globalInstance()
        self._poll_in_progress = False   # защита от параллельных опросов
        
        # Запускаем сразу — если пользователь ничего не делает, опрос начнётся через 2 секунды
        self._idle_timer.start()
        
        # Устанавливаем фильтр событий на приложение, чтобы ловить клики и ввод
        from PyQt5.QtWidgets import QApplication
        QApplication.instance().installEventFilter(self)
        
        # Таймер debounce для поиска
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(250)  # 250 мс
        self._search_timer.timeout.connect(self._apply_search)
        self._init_tray()

        self._build_ui()
        self._apply_theme()
        title = 'FoodSafe — Маркировки'
        if offline:
            title += ' (оффлайн)'
        self.setWindowTitle(title)
        self.resize(1280, 800)
        
        # Таймер опроса заданий
        self._print_timer = QTimer(self)
        self._print_timer.setInterval(3000)
        self._print_timer.timeout.connect(self._poll_print_jobs)
        self._print_timer.start()
        
        if self.offline:
            self._ensure_api_silent()

        self._load_establishments()
        
        # Проверяем подписку
        if not self._check_subscription():
            # Блокируем всё, кроме синхронизации и настроек
            self._set_blocked_ui()
            
            
        
        

    def _build_ui(self):
        central = QWidget()
        central.setObjectName('centralWidget')
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ============ ВЕРХНЯЯ ПАНЕЛЬ — СТРОКА 1 ============
        top = QFrame()
        top.setObjectName('topbar')
        top_layout = QHBoxLayout(top)
        top_layout.setContentsMargins(10, 6, 10, 6)
        top_layout.setSpacing(6)

        # Бренд (короткий)
        brand = QLabel(' FoodSafe')
        brand.setPixmap(icon('tag', '#0d6efd', 22).pixmap(22, 22))
        brand.setObjectName('brand')
        top_layout.addWidget(brand)

        # --- Заведение ---
        top_layout.addWidget(QLabel('Заведение'))
        self.est_combo = QComboBox()
        self.est_combo.setMinimumWidth(140)
        self.est_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.est_combo.currentIndexChanged.connect(self._on_establishment_changed)
        top_layout.addWidget(self.est_combo, 1)

        # --- Сотрудник ---
        top_layout.addWidget(QLabel('Сотрудник'))
        self.emp_combo = QComboBox()
        self.emp_combo.setMinimumWidth(120)
        self.emp_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.emp_combo.currentIndexChanged.connect(self._on_employee_changed)
        top_layout.addWidget(self.emp_combo, 1)

        # Кнопки-иконки
        self.toggle_cats_btn = QPushButton()
        self.toggle_cats_btn.setIcon(icon('menu'))
        self.toggle_cats_btn.setProperty('class', 'icon-btn')
        self.toggle_cats_btn.setCheckable(True)
        self.toggle_cats_btn.setChecked(True)
        self.toggle_cats_btn.setToolTip('Скрыть/показать категории')
        self.toggle_cats_btn.clicked.connect(self._toggle_categories)
        top_layout.addWidget(self.toggle_cats_btn)

        theme_btn = QPushButton()
        theme_btn.setIcon(icon('sun'))
        theme_btn.setProperty('class', 'icon-btn')
        theme_btn.setToolTip('Тема')
        theme_btn.clicked.connect(self._toggle_theme)
        top_layout.addWidget(theme_btn)
        
        scale_btn = QPushButton('A+')
        scale_btn.setProperty('class', 'icon-btn')
        scale_btn.setToolTip('Размер интерфейса')
        scale_btn.clicked.connect(self._toggle_scale)
        top_layout.addWidget(scale_btn)

        # Кнопка «Ещё» — меню с остальными действиями
        self.more_btn = QPushButton()
        self.more_btn.setIcon(icon('more'))
        self.more_btn.setProperty('class', 'icon-btn')
        self.more_btn.setToolTip('Ещё')
        self.more_btn.clicked.connect(self._show_more_menu)
        top_layout.addWidget(self.more_btn)

        root.addWidget(top)

        # ============ ВЕРХНЯЯ ПАНЕЛЬ — СТРОКА 2 (поиск + главные действия) ============
        top2 = QFrame()
        top2.setObjectName('topbar2')
        top2_layout = QHBoxLayout(top2)
        top2_layout.setContentsMargins(10, 6, 10, 6)
        top2_layout.setSpacing(6)

        search_icon = QLabel('🔍')
        search_icon.setStyleSheet('font-size: 14px;')
        top2_layout.addWidget(search_icon)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText('Поиск...')
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._on_search_changed)
        top2_layout.addWidget(self.search_input, 1)

        # Главные действия — компактно
        self.sync_btn = QPushButton(' Синхронизация')
        self.sync_btn.setIcon(icon('refresh', color='#ffffff', size=20))
        self.sync_btn.setIconSize(QSize(20, 20))
        self.sync_btn.setProperty('class', 'secondary')
        self.sync_btn.setToolTip('Синхронизация')
        self.sync_btn.clicked.connect(self._sync)
        top2_layout.addWidget(self.sync_btn)

        create_btn = QPushButton('➕')
        create_btn.setProperty('class', 'success')
        create_btn.setToolTip('Создать маркировку')
        create_btn.clicked.connect(self._create_label)
        top2_layout.addWidget(create_btn)

        self.cart_btn = QPushButton('🛒')
        self.cart_btn.setProperty('class', 'secondary')
        self.cart_btn.setToolTip('Корзина')
        self.cart_btn.clicked.connect(self._open_cart)
        top2_layout.addWidget(self.cart_btn)

        # Подпись синхронизации — в статус-бар, а не сюда
        root.addWidget(top2)
        
        self.warn_banner = QLabel('')
        self.warn_banner.setAlignment(Qt.AlignCenter)
        self.warn_banner.setStyleSheet(
            'background: #fff3cd; color: #856404; '
            'padding: 8px 16px; font-weight: 600; '
            'border-bottom: 1px solid #ffc107;'
        )
        self.warn_banner.setVisible(False)
        root.addWidget(self.warn_banner)


        # ============ ОСНОВНАЯ ЧАСТЬ ============
        body = QHBoxLayout()
        body.setContentsMargins(16, 16, 16, 16)
        body.setSpacing(14)

        # Левая колонка — категории
        left = QFrame()
        left.setObjectName('sidebar')
        left.setFixedWidth(240)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.setSpacing(6)
        self.left_panel = left

        cat_title = QLabel('Категории')
        cat_title.setStyleSheet('font-weight: 700; padding: 4px 6px; font-size: 14px;')
        left_layout.addWidget(cat_title)

        self.cat_list = QListWidget()
        self.cat_list.itemClicked.connect(self._on_category_clicked)
        left_layout.addWidget(self.cat_list)

        body.addWidget(left)

        # Правая часть — карточки
        right = QScrollArea()
        right.setWidgetResizable(True)

        self.grid_container = QWidget()
        self.grid_container.setObjectName('centralWidget')
        self.grid = QGridLayout(self.grid_container)
        self.grid.setSpacing(12)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setAlignment(Qt.AlignTop)
        right.setWidget(self.grid_container)

        body.addWidget(right, 1)

        body_widget = QWidget()
        body_widget.setObjectName('centralWidget')
        body_widget.setLayout(body)
        root.addWidget(body_widget, 1)

        # Статусбар
        self.status_label = QLabel('')
        self.statusBar().addWidget(self.status_label)

        # Подпись синхронизации — в правом углу статусбара
        self.sync_label = QLabel('')
        self.sync_label.setProperty('class', 'hint')
        self.statusBar().addPermanentWidget(self.sync_label)
        self._update_sync_label()
        
        self.remote_label = QLabel('')
        self.remote_label.setProperty('class', 'hint')
        self.statusBar().addPermanentWidget(self.remote_label)

        # Настройки
        visible = self.config.get('categories_visible', True)
        self.toggle_cats_btn.setChecked(visible)
        self.left_panel.setVisible(visible)

        # Хоткеи
        from PyQt5.QtWidgets import QShortcut
        from PyQt5.QtGui import QKeySequence
        QShortcut(QKeySequence('Ctrl+F'), self, activated=self.search_input.setFocus)
        QShortcut(QKeySequence('Escape'), self.search_input, activated=self.search_input.clear)
        QShortcut(QKeySequence('Ctrl+B'), self, activated=self.toggle_cats_btn.toggle)
        QShortcut(QKeySequence('Ctrl+W'), self, activated=self.hide)
        
    def _update_remote_label(self):
        if not self.config.get('remote_print_enabled', True):
            self.remote_label.setText('🖨  Приём с сайта: выкл')
            return

        if self.offline or not self.api:
            self.remote_label.setText('🖨  Приём с сайта: нет связи')
        else:
            self.remote_label.setText('🖨  Приём с сайта: вкл')

    # ---------- Данные ----------

    def _load_establishments(self):
        """Заполняет combo заведений и загружает первое."""
        self.est_combo.blockSignals(True)
        self.est_combo.clear()
        for est in local_db.get_establishments():
            self.est_combo.addItem(est['name'], userData=est['id'])
        self.est_combo.blockSignals(False)

        if self.est_combo.count() > 0:
            self.est_combo.setCurrentIndex(0)
            self._load_establishment(self.est_combo.itemData(0))

        # Баннер, если осталось мало дней
        self._update_warn_banner()
                
                
    def _show_blocked_placeholder(self):
        while self.grid.count():
            child = self.grid.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        blocked = QLabel(
            '🔒  Заведение заблокировано.\n'
            'Продлите подписку на сайте и нажмите «Синхронизация»\n'
            'или выберите другое заведение.'
        )
        blocked.setAlignment(Qt.AlignCenter)
        blocked.setStyleSheet(
            'font-size: 18px; color: #dc3545; padding: 60px; line-height: 1.6;'
        )
        self.grid.addWidget(blocked, 0, 0)

    def _on_establishment_changed(self, idx):
        est_id = self.est_combo.itemData(idx)
        if est_id:
            self._load_establishment(est_id)

    def _load_establishment(self, est_id):
        """Загружает данные конкретного заведения."""
        self.current_est = next(
            (e for e in local_db.get_establishments() if e['id'] == est_id),
            None
        )
        if not self.current_est:
            return

        # --- Проверка подписки именно этого заведения ---
        if int(self.current_est.get('is_paid') or 0) != 1:
            from ui.blocked_dialog import BlockedDialog
            BlockedDialog(self, self.current_est, reason='expired').exec_()
            self.categories = []
            self.labels = []
            self._render_categories()
            self._show_blocked_placeholder()
            return

        # Категории и метки
        self.categories = [
            c for c in local_db.get_categories(est_id)
            if int(c.get('is_active') or 0) == 1
        ]
        self.labels = local_db.get_labels(est_id)
        self.selected_category = 'all'

        # Сотрудники
        self._load_employees(est_id)

        self._render_categories()
        self._render_labels()
        self._update_cart_counter()
        self._update_warn_banner()
        
    def _load_employees(self, est_id):
        """Заполняет combo сотрудников и восстанавливает сохранённый выбор."""
        employees = local_db.get_employees(est_id)
        # Оставляем только активных
        employees = [e for e in employees if int(e.get('is_active') or 0) == 1]
        
        self.emp_combo.blockSignals(True)
        self.emp_combo.clear()

        # Пункт «не выбрано» — печатается имя владельца
        self.emp_combo.addItem('— не выбрано —', userData=None)

        for emp in employees:
            label = emp['name']
            if emp.get('position'):
                label += f" ({emp['position']})"
            self.emp_combo.addItem(label, userData=emp['id'])

        # Восстанавливаем сохранённый выбор для этого заведения
        saved_id = settings.get_selected_employee(est_id)
        if saved_id is not None:
            found = False
            for i in range(self.emp_combo.count()):
                if self.emp_combo.itemData(i) == saved_id:
                    self.emp_combo.setCurrentIndex(i)
                    found = True
                    break
            if not found:
                # Сохранённый сотрудник недоступен — сбрасываем выбор
                self.emp_combo.setCurrentIndex(0)
                settings.set_selected_employee(est_id, None)
        else:
            self.emp_combo.setCurrentIndex(0)

        self.emp_combo.blockSignals(False)
        
    def _on_employee_changed(self, idx):
        if not self.current_est:
            return
        emp_id = self.emp_combo.itemData(idx)
        settings.set_selected_employee(self.current_est['id'], emp_id)

        if emp_id is None:
            self.status_label.setText('Сотрудник не выбран')
        else:
            name = self.emp_combo.currentText()
            self.status_label.setText(f'Сотрудник: {name}')


    def _current_employee_name(self):
        """Возвращает имя выбранного сотрудника или None."""
        if not self.current_est:
            return None
        emp_id = self.emp_combo.currentData()
        if not emp_id:
            return None
        emp = local_db.get_employee(emp_id)
        return emp['name'] if emp else None

    def _render_categories(self):
        self.cat_list.clear()

        all_item = QListWidgetItem(f"Все ({len(self.labels)})")
        all_item.setData(Qt.UserRole, 'all')
        self.cat_list.addItem(all_item)

        uncat = [l for l in self.labels if not l.get('category_id')]
        uncat_item = QListWidgetItem(f"Без категории ({len(uncat)})")
        uncat_item.setData(Qt.UserRole, 'uncategorized')
        self.cat_list.addItem(uncat_item)

        for c in self.categories:
            count = len([
                l for l in self.labels
                if l.get('category_id') == c['id']
            ])
            item = QListWidgetItem(f"{c['name']} ({count})")
            item.setData(Qt.UserRole, c['id'])
            self.cat_list.addItem(item)

        self.cat_list.setCurrentRow(0)

    def _on_category_clicked(self, item):
        self.selected_category = item.data(Qt.UserRole)
        self._render_labels()

    def _render_labels(self):
        while self.grid.count():
            child = self.grid.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Фильтр по категории
        if self.selected_category == 'all':
            filtered = self.labels
        elif self.selected_category == 'uncategorized':
            filtered = [l for l in self.labels if not l.get('category_id')]
        else:
            filtered = [l for l in self.labels
                        if l.get('category_id') == self.selected_category]

        # Фильтр по поиску
        if self.search_text:
            filtered = [l for l in filtered
                        if self.search_text in (l.get('name') or '').lower()]

        if not filtered:
            text = ('Ничего не найдено по запросу' if self.search_text
                    else 'Маркировок нет. Создайте их на сайте и синхронизируйте.')
            empty = QLabel(text)
            empty.setStyleSheet('color: #6c757d; padding: 40px; font-size: 16px;')
            empty.setAlignment(Qt.AlignCenter)
            self.grid.addWidget(empty, 0, 0)
            return

        from PyQt5.QtWidgets import QApplication
        screen_w = self.width()
        if screen_w < 1000:
            cols = 2
        elif screen_w < 1300:
            cols = 3
        elif screen_w < 1700:
            cols = 4
        else:
            cols = 5
        for i, label in enumerate(filtered):
            card = LabelCard(label)
            card.print_requested.connect(self._print_label)
            card.add_to_cart_requested.connect(self._add_to_cart)   # <-- новое
            self.grid.addWidget(card, i // cols, i % cols)

    # ---------- Синхронизация ----------

    def _update_sync_label(self):
        last = local_db.last_sync() or 'никогда'
        self.sync_label.setText(f'Синхр.: {last}')

    def _sync(self):
        if self.offline or not self.api:
            # Попробуем создать клиент из сохранённого конфига
            url = self.config.get('api_url')
            key = self.config.get('api_key')
            if not url or not key:
                QMessageBox.warning(
                    self, 'Нет данных для синхронизации',
                    'Введите ключ на экране входа'
                )
                return
            try:
                client = ApiClient(url, key)
                client.me()
            except ApiError as e:
                QMessageBox.warning(self, 'Нет связи', str(e))
                return
            self.api = client

        # Прогресс-диалог
        dlg = QProgressDialog('Синхронизация...', 'Отмена', 0, 0, self)
        dlg.setWindowTitle('Синхронизация')
        dlg.setWindowModality(Qt.WindowModal)
        dlg.setMinimumWidth(400)
        dlg.show()
        # После синхронизации — перезагрузить список заведений
        self._load_establishments()

        def report(msg):
            dlg.setLabelText(msg)
            from PyQt5.QtWidgets import QApplication
            QApplication.processEvents()

        try:
            sync_all(self.api, status_cb=report)
        except ApiError as e:
            dlg.close()
            QMessageBox.warning(self, 'Ошибка синхронизации', str(e))
            return
        finally:
            dlg.close()

        self._update_sync_label()
        # Перезагружаем заведения (могли появиться новые)
        current_id = self.current_est['id'] if self.current_est else None
        self._load_establishments()

        # Вернуть выбор на то же заведение, если оно есть
        if current_id:
            for i in range(self.est_combo.count()):
                if self.est_combo.itemData(i) == current_id:
                    self.est_combo.setCurrentIndex(i)
                    break

        QMessageBox.information(
            self, 'Готово',
            f'Данные обновлены. Последняя синхронизация: {local_db.last_sync()}'
        )
        
        # После успешной синхронизации — перепроверить подписку
        if self._check_subscription():
            # Разблокируем UI
            self._load_establishments()
        else:
            self._set_blocked_ui()

    # ---------- Печать ----------
    
    def _print_label(self, label):
        printer = self.config.get('printer_name') or get_default_printer()
        if not printer:
            QMessageBox.warning(self, 'Принтер не выбран',
                                'Выберите принтер в настройках')
            return
        data = self._build_label_data(label)
        pm = render_label_pixmap(data)
        import tempfile, os
        tmp = os.path.join(tempfile.gettempdir(),
                        f'label_{label.get("id", 0)}.png')
        pm.save(tmp, 'PNG')
        try:
            print_image_tspl(printer, tmp)
            local_db.log_print(label.get('id'), label['name'], printer)
            self.status_label.setText(f"✅ Напечатано: {label['name']}")
        except Exception as e:
            QMessageBox.warning(self, 'Ошибка печати', str(e))
                

    # ---------- Настройки принтера ----------

    def _select_printer(self):
        printers = list_printers()
        if not printers:
            QMessageBox.warning(self, 'Принтеры не найдены',
                                'В системе нет установленных принтеров')
            return

        current = self.config.get('printer_name') or get_default_printer()
        try:
            idx = printers.index(current)
        except ValueError:
            idx = 0

        name, ok = QInputDialog.getItem(
            self, 'Выбор принтера',
            'Принтер по умолчанию:', printers, idx, False
        )
        if ok and name:
            self.config['printer_name'] = name
            settings.save_config(self.config)
            self.status_label.setText(f'Принтер: {name}')

    # ---------- Корзина ----------

    def _open_cart(self):
        if not self.current_est:
            return
        items = local_db.get_cart(self.current_est['id'])
        total = sum(i['quantity'] for i in items)
        cart_data = {
            'items': items,
            'total_count': total,
            'unique_count': len(items),
        }
        dlg = CartWindow(
            self,
            cart_data,
            self.current_est,
            print_callback=self._print_label,
            print_batch_callback=self._print_batch,
            sync_callback=self._sync_cart,   # <-- новый колбэк
        )
        dlg.exec_()
        self._update_cart_counter()
        
    def _print_batch(self, labels):
        if not labels:
            return
        printer = self.config.get('printer_name') or get_default_printer()
        if not printer:
            QMessageBox.warning(self, 'Принтер не выбран',
                                'Выберите принтер в настройках')
            return

        import os
        import tempfile

        # Собираем все PNG
        image_paths = []
        for i, label in enumerate(labels):
            data = self._build_label_data(label)
            pm = render_label_pixmap(data)
            tmp = os.path.join(
                tempfile.gettempdir(),
                f'label_{label.get("id", 0)}_{i}.png'
            )
            pm.save(tmp, 'PNG')
            image_paths.append(tmp)

        try:
            from printer import print_batch_tspl
            delay_ms = int(self.config.get('print_delay_ms', 300))
            print_batch_tspl(printer, image_paths, delay_ms=delay_ms)
            local_db.log_print(None, f'{len(labels)} labels', printer)
            self.status_label.setText(f'✅ Напечатано {len(labels)} этикеток')
        except Exception as e:
            QMessageBox.warning(self, 'Ошибка печати', str(e))
        finally:
            for path in image_paths:
                try:
                    os.remove(path)
                except OSError:
                    pass
        
    # поиск
    def _on_search_changed(self, text):
        """Вызывается на каждое нажатие клавиши в поиске.
        Запускает таймер — реальная фильтрация будет через 250 мс
        после последнего нажатия."""
        self.search_text = text.strip().lower()
        self._search_timer.start()  # перезапустить таймер

    def _apply_search(self):
        """Применить фильтр поиска к карточкам."""
        self._render_labels()
        
    # бургер
    def _toggle_categories(self):
        visible = self.toggle_cats_btn.isChecked()
        self.left_panel.setVisible(visible)
        self.config['categories_visible'] = visible
        settings.save_config(self.config)
        
    # трее
    def _init_tray(self):
        from PyQt5.QtGui import QIcon
        from paths import icon_file

        icon_path = icon_file()
        if icon_path.exists():
            icon = QIcon(str(icon_path))
        else:
            # fallback на стандартную
            icon = self.style().standardIcon(QStyle.SP_ComputerIcon)

        self.tray = QSystemTrayIcon(icon, self)
        self.tray.setToolTip('FoodSafe — маркировки')

        menu = QMenu()
        
        theme_action = QAction('Переключить тему', self)
        theme_action.triggered.connect(self._toggle_theme)
        menu.addAction(theme_action)
        
        show_action = QAction('Развернуть', self)
        show_action.triggered.connect(self._show_from_tray)
        menu.addAction(show_action)

        sync_action = QAction('Синхронизация', self)
        sync_action.triggered.connect(self._sync)
        menu.addAction(sync_action)

        menu.addSeparator()

        quit_action = QAction('Выход', self)
        quit_action.triggered.connect(self._quit_app)
        menu.addAction(quit_action)

        self.tray.setContextMenu(menu)

        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

        # Флаг: при закрытии окна сворачивать в трей
        self.tray_hint_shown = False


    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self._show_from_tray()


    def _show_from_tray(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()


    def _quit_app(self):
        self.tray.hide()
        from PyQt5.QtWidgets import QApplication
        QApplication.instance().quit()
        
    # переопределил закрытие окна
    def closeEvent(self, event):
        """Сворачиваем в трей вместо закрытия."""
        if self.tray.isVisible():
            event.ignore()
            self.hide()
            if not self.tray_hint_shown:
                self.tray.showMessage(
                    'FoodSafe',
                    'Приложение свёрнуто в трей. Двойной клик — развернуть.',
                    QSystemTrayIcon.Information,
                    3000
                )
                self.tray_hint_shown = True
        else:
            event.accept()
            
    # смена темы 
    SCALE_VALUES = {
        'normal': 1.0,
        'large':  1.25,
        'xlarge': 1.5,
    }
    SCALE_CYCLE = ['normal', 'large', 'xlarge']

    def _apply_theme(self):
        theme = self.config.get('theme', 'light')
        scale_name = self.config.get('ui_scale', 'normal')
        scale = self.SCALE_VALUES.get(scale_name, 1.0)
        qss = build_qss(theme, scale)
        self.setStyleSheet(qss)


    def _toggle_theme(self):
        self.config['theme'] = 'dark' if self.config.get('theme', 'light') == 'light' else 'light'
        settings.save_config(self.config)
        self._apply_theme()
        
        
        
    def _create_label(self):
        """Открывает диалог создания маркировки и отправляет на сервер."""
        if not self.current_est:
            QMessageBox.warning(self, 'Нет заведения',
                                'Сначала выберите заведение')
            return

        # Проверка связи — нужен рабочий клиент
        if not self.api or self.offline:
            # попробуем создать клиент из сохранённого конфига
            url = self.config.get('api_url')
            key = self.config.get('api_key')
            if not url or not key:
                QMessageBox.warning(self, 'Нет подключения',
                                    'Введите API-ключ на экране входа')
                return
            try:
                client = ApiClient(url, key)
                client.me()
                self.api = client
                self.offline = False
            except ApiError as e:
                QMessageBox.warning(self, 'Нет связи', str(e))
                return

        # Готовим данные для диалога
        categories = local_db.get_categories(self.current_est['id'])
        employees = local_db.get_employees(self.current_est['id'])
        current_emp_id = self.emp_combo.currentData()

        dlg = CreateLabelDialog(
            self,
            establishment=self.current_est,
            categories=categories,
            employees=employees,
            current_employee_id=current_emp_id,
        )
        if dlg.exec_() != CreateLabelDialog.Accepted:
            return

        data = dlg.result_data

        # Отправляем на сервер
        try:
            result = self.api.label_create(
                establishment_id=self.current_est['id'],
                name=data['name'],
                storage_duration=data['storage_duration'],
                duration_unit=data['duration_unit'],
                storage_temperature=data['storage_temperature'],
                category_id=data['category_id'],
                employee_id=data['employee_id'],
            )
        except ApiError as e:
            QMessageBox.critical(self, 'Ошибка создания', str(e))
            return

        # Добавляем локально, чтобы не ждать синхронизации
        server_label = result['label']
        self._insert_label_locally(server_label)

        self.status_label.setText(f"✅ Создано: {server_label['name']}")


    def _insert_label_locally(self, server_label):
        local_db.insert_label(self.current_est['id'], server_label)
        self.labels = local_db.get_labels(self.current_est['id'])
        self._render_categories()
        self._render_labels()
        
        
    # добавление и удаление из корзины
    def _add_to_cart(self, label):
        """Добавляет маркировку в локальную корзину и обновляет счётчик."""
        if not self.current_est:
            return

        local_db.cart_add(self.current_est['id'], label)
        self._update_cart_counter()
        self.status_label.setText(f"🛒 Добавлено: {label['name']}")


    def _update_cart_counter(self):
        """Обновляет текст кнопки корзины в верхней панели."""
        if not self.current_est:
            self.cart_btn.setText('🛒  Корзина')
            return

        count = local_db.cart_count(self.current_est['id'])
        if count > 0:
            self.cart_btn.setText(f'🛒  Корзина ({count})')
        else:
            self.cart_btn.setText('🛒  Корзина')
            
            
    def _sync_cart(self):
        """
        Синхронизирует корзину текущего заведения с сервером.
        Локальные позиции при этом удаляются (перезаписываются серверными).
        """
        if not self.current_est:
            return

        # Проверим клиента
        if not self.api or self.offline:
            url = self.config.get('api_url')
            key = self.config.get('api_key')
            if not url or not key:
                QMessageBox.warning(self, 'Нет подключения',
                                    'Введите API-ключ на экране входа')
                return
            try:
                client = ApiClient(url, key)
                client.me()
                self.api = client
                self.offline = False
            except ApiError as e:
                QMessageBox.warning(self, 'Нет связи', str(e))
                return

        try:
            from sync import sync_cart_for_establishment
            count = sync_cart_for_establishment(self.api, self.current_est['id'])
        except ApiError as e:
            QMessageBox.warning(self, 'Ошибка синхронизации корзины', str(e))
            return
        except Exception as e:
            QMessageBox.warning(self, 'Ошибка', str(e))
            return

        self._update_cart_counter()
        self.status_label.setText(f'🛒 Корзина синхронизирована: {count} позиций')


    def _update_cart_counter(self):
        if not self.current_est:
            self.cart_btn.setText('🛒  Корзина')
            return
        count = local_db.cart_count(self.current_est['id'])
        if count > 0:
            self.cart_btn.setText(f'🛒  Корзина ({count})')
        else:
            self.cart_btn.setText('🛒  Корзина')
            
    
    def _build_label_data(self, label):
        """Собирает dict для рендера/печати с подстановкой времени."""
        marked_by = self._current_employee_name() or label.get('marked_by', '')

        now = datetime.now()
        minutes = (now.minute // 15) * 15
        print_time = now.replace(minute=minutes, second=0, microsecond=0)

        duration = label.get('storage_duration') or 0
        unit = label.get('duration_unit') or 'hours'
        if unit == 'hours':
            expiration = print_time + timedelta(hours=duration)
        else:
            expiration = print_time + timedelta(days=duration)

        return {
            'name': label['name'],
            'print_time_str': print_time.strftime('%d.%m.%Y %H:%M'),
            'expiration_time_str': expiration.strftime('%d.%m.%Y %H:%M'),
            'storage_temperature': label.get('storage_temperature', ''),
            'storage_period_text': label.get('storage_period_text', ''),
            'marked_by': marked_by,
        }
        
        
    def _open_settings(self):
        from ui.settings_dialog import SettingsDialog
        dlg = SettingsDialog(self, self.config)
        if dlg.exec_() == SettingsDialog.Accepted:
            # Обновим конфиг и применим тему
            self.config = settings.load_config()
            self._apply_theme()
            self._update_remote_label()
            self.status_label.setText(
                f"Настройки сохранены. Принтер: "
                f"{self.config.get('printer_name', '—')}, пауза: "
                f"{self.config.get('print_delay_ms', 300)} мс"
            )
            
            
    def _show_more_menu(self):
        """Выпадающее меню с дополнительными действиями."""
        menu = QMenu(self)

        act_sync = QAction('🔄  Синхронизация', self)
        act_sync.triggered.connect(self._sync)
        menu.addAction(act_sync)

        act_create = QAction('➕  Создать маркировку', self)
        act_create.triggered.connect(self._create_label)
        menu.addAction(act_create)

        act_cart = QAction('🛒  Корзина', self)
        act_cart.triggered.connect(self._open_cart)
        menu.addAction(act_cart)

        menu.addSeparator()
        
        act_employees = QAction('👥  Сотрудники', self)
        act_employees.triggered.connect(self._open_employees)
        menu.addAction(act_employees)
        

        act_categories = QAction('🏷  Категории', self)
        act_categories.triggered.connect(self._open_categories)
        menu.addAction(act_categories)

        menu.addSeparator()
        
        act_printer = QAction('⚙  Настройки', self)
        act_printer.triggered.connect(self._open_settings)
        menu.addAction(act_printer)

        # Показать меню рядом с кнопкой
        pos = self.more_btn.mapToGlobal(self.more_btn.rect().bottomLeft())
        menu.exec_(pos)
        
        
    def _open_employees(self):
        if not self.current_est:
            QMessageBox.warning(self, 'Нет заведения', 'Выберите заведение')
            return
        if not self._ensure_api():
            return
        from ui.employees_dialog import EmployeesDialog
        dlg = EmployeesDialog(self, self.api, self.current_est)
        dlg.exec_()
        self._load_establishment(self.current_est['id'])

    def _open_categories(self):
        if not self.current_est:
            QMessageBox.warning(self, 'Нет заведения', 'Выберите заведение')
            return
        if not self._ensure_api():
            return
        from ui.categories_dialog import CategoriesDialog
        dlg = CategoriesDialog(self, self.api, self.current_est)
        dlg.exec_()
        self._load_establishment(self.current_est['id'])

    def _ensure_api(self):
        """Возвращает True, если есть рабочий API-клиент."""
        if self.api and not self.offline:
            return True
        url = self.config.get('api_url')
        key = self.config.get('api_key')
        if not url or not key:
            QMessageBox.warning(self, 'Нет подключения', 'Введите ключ на входе')
            return False
        try:
            client = ApiClient(url, key)
            client.me()
            self.api = client
            self.offline = False
            return True
        except ApiError as e:
            QMessageBox.warning(self, 'Нет связи', str(e))
            return False
        
        
    def _toggle_scale(self):
        current = self.config.get('ui_scale', 'normal')
        idx = self.SCALE_CYCLE.index(current) if current in self.SCALE_CYCLE else 0
        new = self.SCALE_CYCLE[(idx + 1) % len(self.SCALE_CYCLE)]
        self.config['ui_scale'] = new
        settings.save_config(self.config)
        self._apply_theme()
        labels = {'normal': 'обычный', 'large': 'крупный', 'xlarge': 'очень крупный'}
        self.status_label.setText(f'Размер интерфейса: {labels[new]}')
        
        
    def _check_subscription(self):
        """
        Проверяет оплату заведений. Возвращает True,
        если есть хотя бы одно активное заведение.
        """
        ests = local_db.get_establishments()
        if not ests:
            return True   # нет заведений — нечего проверять

        active = [e for e in ests if int(e.get('is_paid') or 0) == 1]
        if active:
            return True

        # Все заведения заблокированы — показать диалог
        from ui.blocked_dialog import BlockedDialog
        # показываем для первого в списке
        dlg = BlockedDialog(self, ests[0], reason='expired')
        dlg.exec_()
        return False
    
    
    def _set_blocked_ui(self):
        """Оставляет доступными только кнопки синхронизации и настроек."""
        # Отключаем главные действия
        for attr in ('toggle_cats_btn', 'cart_btn', 'search_input',
                    'est_combo', 'emp_combo'):
            w = getattr(self, attr, None)
            if w is not None:
                w.setEnabled(False)

        # Прячем карточки
        while self.grid.count():
            child = self.grid.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Заглушка по центру
        blocked = QLabel(
            '🔒  Заведение заблокировано.\n'
            'Продлите подписку на сайте и нажмите «Синхронизация».'
        )
        blocked.setAlignment(Qt.AlignCenter)
        blocked.setStyleSheet(
            'font-size: 18px; color: #dc3545; padding: 60px; line-height: 1.6;'
        )
        self.grid.addWidget(blocked, 0, 0)
        
        
    def _update_warn_banner(self):
        """Показывает/скрывает баннер о скором окончании подписки."""
        if not self.current_est:
            self.warn_banner.setVisible(False)
            return
        days = self.current_est.get('days_left')
        if days is not None and 0 <= days <= 7:
            self.warn_banner.setText(
                f'⚠ Подписка на «{self.current_est["name"]}» закончится '
                f'через {days} дн. Продлите на сайте.'
            )
            self.warn_banner.setVisible(True)
        else:
            self.warn_banner.setVisible(False)
            
            
    # печать с сайта на планшете    
    def _poll_print_jobs(self):
        """Проверяет очередь заданий на печать (в фоне)."""
        # Отключено пользователем
        if not self.config.get('remote_print_enabled', True):
            return
        if not self.current_est:
            return

        # Уже идёт опрос — не запускаем второй
        if self._poll_in_progress:
            return

        # Пытаемся тихо поднять API-клиент (тоже быстрое)
        if not self._ensure_api_silent():
            return

        self._poll_in_progress = True

        from ui.print_poller import PollRunnable
        task = PollRunnable(self.api, self.current_est['id'])
        task.signals.finished.connect(self._on_poll_finished)
        task.signals.error.connect(self._on_poll_error)
        self._thread_pool.start(task)


    def _execute_remote_print(self, job):
        """Печатает одну этикетку из задания."""
        printer = self.config.get('printer_name') or get_default_printer()
        if not printer:
            self._report_print_job(job['id'], 'error', 'Принтер не выбран')
            return

        try:
            payload = job['payload']
            data = {
                'name': payload.get('name', ''),
                'print_time_str': payload.get('print_time_str', ''),
                'expiration_time_str': payload.get('expiration_time_str', ''),
                'storage_temperature': payload.get('storage_temperature', ''),
                'storage_period_text': payload.get('storage_period_text', ''),
                'marked_by': payload.get('marked_by', ''),
            }

            pm = render_label_pixmap(data)
            tmp = os.path.join(tempfile.gettempdir(), f"remote_{job['id']}.png")
            pm.save(tmp, 'PNG')

            print_image_tspl(printer, tmp)
            os.remove(tmp)

            self._report_print_job(job['id'], 'done')
            self.status_label.setText(f"✅ Удалённая печать: {payload.get('name', '')}")

        except Exception as e:
            self._report_print_job(job['id'], 'error', str(e))
            self.status_label.setText(f"❌ Ошибка удалённой печати: {e}")


    def _report_print_job(self, job_id, status, error=''):
        try:
            self.api.print_complete(job_id, status, error)
        except ApiError:
            pass
        
        
    def _ensure_api_silent(self):
        if self.api and not self.offline:
            return True

        url = self.config.get('api_url')
        key = self.config.get('api_key')
        if not url or not key:
            return False

        try:
            client = ApiClient(url, key)
            client.me_fast()   # ← быстрый
        except ApiError:
            return False

        self.api = client
        self.offline = False
        return True
    

    def eventFilter(self, obj, event):
        """
        Ловим любые действия пользователя и сбрасываем таймер тишины.
        Пока таймер не сработал — не опрашиваем сервер.
        """
        # Нас интересуют только действия: клики, клавиши, колесо, движение мыши
        if event.type() in (
            QEvent.MouseButtonPress,
            QEvent.MouseButtonRelease,
            QEvent.KeyPress,
            QEvent.Wheel,
            QEvent.TouchBegin,
            QEvent.TouchUpdate,
        ):
            # Сбрасываем таймер — пользователь активен
            if hasattr(self, '_idle_timer'):
                self._idle_timer.start()  # перезапускает с нуля
        return super().eventFilter(obj, event)
    
    def _on_idle(self):
        """
        Вызывается, когда пользователь 2 секунды ничего не делал.
        Здесь и запускаем опрос сервера.
        """
        self._poll_print_jobs()
        
    def _on_poll_finished(self, jobs):
        """Вызывается в GUI-потоке, когда фоновый запрос завершился."""
        self._poll_in_progress = False

        if not jobs:
            return

        for job in jobs:
            self._execute_remote_print(job)


    def _on_poll_error(self, error_message):
        """Ошибка сети — переключаемся в оффлайн."""
        self._poll_in_progress = False
        self.offline = True
        self._update_remote_label()
        # Не показываем QMessageBox — это фоновая ошибка