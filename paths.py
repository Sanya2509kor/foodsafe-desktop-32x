# paths.py
import sys
from pathlib import Path


def app_dir() -> Path:
    """
    Папка приложения.
    - В обычном запуске (python main.py) — папка со скриптом.
    - В собранном .exe (PyInstaller) — папка с .exe, а не временная распаковка.
    """
    if getattr(sys, 'frozen', False):
        # PyInstaller onefile/onedir — sys.executable указывает на .exe
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


def data_dir() -> Path:
    """Папка для данных: config.json, data.db и т.п."""
    d = app_dir() / 'data'
    d.mkdir(exist_ok=True)
    return d


def config_file() -> Path:
    return data_dir() / 'config.json'


def db_file() -> Path:
    return data_dir() / 'data.db'


def logs_dir() -> Path:
    d = data_dir() / 'logs'
    d.mkdir(exist_ok=True)
    return d


def _resource_dir() -> Path:
    """
    Папка для встроенных ресурсов.
    - В обычном запуске (python main.py) — папка со скриптом.
    - В PyInstaller onedir — папка _internal, где лежат assets.
    - Если assets нет в _internal — fallback на папку с .exe.
    """
    if getattr(sys, 'frozen', False):
        exe_dir = Path(sys.executable).parent
        internal = exe_dir / '_internal'
        if internal.exists():
            return internal
        return exe_dir
    return Path(__file__).resolve().parent

def assets_dir() -> Path:
    """
    Ищет папку assets:
    1) рядом с .exe (если пользователь кинул туда вручную);
    2) внутри _internal (куда PyInstaller кладёт --add-data).
    Возвращает первый существующий вариант.
    """
    candidates = [
        app_dir() / 'assets',          # рядом с .exe
        _resource_dir() / 'assets',    # внутри _internal
    ]
    for c in candidates:
        if c.exists():
            return c
    # Если ничего не нашли — возвращаем первый как fallback,
    # чтобы код не падал, а иконка просто не нашлась
    return candidates[0]


def icon_file() -> Path:
    """Путь к иконке приложения (assets/icon.ico)."""
    return assets_dir() / 'icon.ico'