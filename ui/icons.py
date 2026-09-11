# ui/icons.py
import os
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor
from PyQt5.QtCore import QSize, Qt, QByteArray
from PyQt5.QtSvg import QSvgRenderer

from paths import app_dir


def _icons_dir():
    """Папка с SVG-иконками."""
    candidates = [
        app_dir() / 'assets' / 'icons',
        app_dir() / '_internal' / 'assets' / 'icons',
    ]
    for c in candidates:
        if c.exists():
            return c
    return candidates[0]


# Кэш иконок, чтобы не перерисовывать
_CACHE = {}


def icon(name: str, color: str = '#212529', size: int = 24) -> QIcon:
    """
    Загружает SVG-иконку и красит её в нужный цвет.
    name — без .svg, например 'printer'.
    """
    key = (name, color, size)
    if key in _CACHE:
        return _CACHE[key]

    path = _icons_dir() / f'{name}.svg'
    if not path.exists():
        # Fallback — пустая иконка
        icon_obj = QIcon()
        _CACHE[key] = icon_obj
        return icon_obj

    # Загружаем SVG, красим, отдаём в QIcon
    with open(path, 'rb') as f:
        svg_data = f.read()

    # Заменяем все currentColor / stroke="..." на наш цвет
    svg_text = svg_data.decode('utf-8')
    svg_text = svg_text.replace('currentColor', color)
    # Если SVG не использует currentColor — красим через QPainter
    svg_bytes = QByteArray(svg_text.encode('utf-8'))

    renderer = QSvgRenderer(svg_bytes)
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()

    # Если SVG монохромный — перекрасим через маску
    if color != '#212529':
        tinted = QPixmap(pixmap.size())
        tinted.fill(Qt.transparent)
        painter = QPainter(tinted)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.drawPixmap(0, 0, pixmap)
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        painter.fillRect(pixmap.rect(), QColor(color))
        painter.end()
        pixmap = tinted

    icon_obj = QIcon(pixmap)
    _CACHE[key] = icon_obj
    return icon_obj