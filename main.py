# main.py
import sys
import logging
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
import local_db
import settings
from ui.login_window import LoginWindow
from ui.main_window import MainWindow
from paths import data_dir, logs_dir, icon_file


def setup_logging():
    log_file = logs_dir() / 'app.log'
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(),
        ]
    )
    logging.info('App started, data dir: %s', data_dir())


def main():
    setup_logging()
    
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName('FoodSafe')
    app.setQuitOnLastWindowClosed(False)
    
    # Устанавливаем иконку приложения (видна в панели задач и в трее)
    icon_path = icon_file()
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    else:
        logging.warning('Иконка не найдена: %s', icon_path)

    # Инициализация локальной БД
    local_db.init_db()

    cfg = settings.load_config()
    has_local = bool(local_db.get_establishments())

    # Если есть сохранённые данные и стоит автосинхронизация — попробуем без входа
    if has_local and cfg.get('auto_sync_on_start') and cfg.get('api_key'):
        # можно сразу переходить в главное окно и там запустить синхронизацию
        window = MainWindow(api=None, offline=True)
        window.show()
        QApplication.processEvents()
        window._sync()  # тихо синхронизируется, если получится
        return app.exec_()

    login = LoginWindow()
    if login.exec_() != LoginWindow.Accepted:
        return 0

    window = MainWindow(login.api, offline=login.offline_mode)
    window.show()
    return app.exec_()


if __name__ == '__main__':
    sys.exit(main())