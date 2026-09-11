# label_renderer.py
from PyQt5.QtCore import Qt, QRect
from PyQt5.QtGui import (
    QPixmap, QPainter, QFont, QPen, QColor, QFontMetrics
)

# ---------- Физические размеры этикетки ----------
DPI = 203
MM_TO_PX = DPI / 25.4               # ≈ 7.99
LABEL_W_MM = 58
LABEL_H_MM = 60
LABEL_W_PX = int(round(LABEL_W_MM * MM_TO_PX))   # 464
LABEL_H_PX = int(round(LABEL_H_MM * MM_TO_PX))   # 480


def _mm(v: float) -> int:
    return int(round(v * MM_TO_PX))


def _css_px_to_mm(css_px: float) -> float:
    """CSS px (96 dpi) → мм на этикетке (203 dpi)."""
    return css_px * (203.0 / 96.0) / MM_TO_PX


def _make_font(mm_height: float, bold: bool = True) -> QFont:
    f = QFont('Arial')
    f.setPixelSize(max(1, int(round(mm_height * MM_TO_PX))))
    f.setBold(bold)
    return f


def _fit_font(text: str, base_mm: float, max_width_px: int,
              bold: bool = True, min_mm: float = 2.0) -> QFont:
    """
    Подбирает шрифт так, чтобы `text` влез в `max_width_px`.
    Начинает с base_mm и уменьшает, пока не влезет или не достигнет min_mm.
    Возвращает готовый QFont.
    """
    mm = base_mm
    while mm >= min_mm:
        f = _make_font(mm, bold=bold)
        fm = QFontMetrics(f)
        if fm.horizontalAdvance(text) <= max_width_px:
            return f
        mm -= 0.15
    return _make_font(min_mm, bold=bold)


def _elide(text: str, font: QFont, max_width_px: int) -> str:
    """Обрезает текст многоточием, если он шире max_width_px."""
    fm = QFontMetrics(font)
    if fm.horizontalAdvance(text) <= max_width_px:
        return text
    return fm.elidedText(text, Qt.ElideRight, max_width_px)


def render_label_pixmap(data: dict) -> QPixmap:
    pm = QPixmap(LABEL_W_PX, LABEL_H_PX)
    pm.fill(Qt.white)

    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, False)
    p.setRenderHint(QPainter.TextAntialiasing, True)

    black = QColor(0, 0, 0)
    p.setPen(black)

    # Отступы
    left = _mm(2)
    right = LABEL_W_PX - _mm(2)
    width = right - left
    full_width = LABEL_W_PX

    # Базовые размеры в мм (как в HTML: 15px / 11px / 12px)
    NAME_BASE_MM    = _css_px_to_mm(15)   # ≈ 3.96 мм
    NAME_MAX_MM     = _css_px_to_mm(20)   # ≈ 5.29 мм — если короткое название, можно крупнее
    VALUE_BASE_MM   = _css_px_to_mm(15)   # ≈ 3.96 мм
    LABEL_MM        = _css_px_to_mm(11)   # ≈ 2.90 мм
    FOOTER_MM       = _css_px_to_mm(11)   # ≈ 2.90 мм
    GODEN_LABEL_MM  = _css_px_to_mm(12)   # ≈ 3.17 мм

    # ================= НАЗВАНИЕ =================
    name_raw = (data.get('name') or '').upper()
    max_name_width = LABEL_W_PX - _mm(4)   # с боковыми отступами

    # Название короткое → крупнее, длинное → мельче, но не больше NAME_MAX_MM
    f_name = _make_font(NAME_MAX_MM, bold=True)
    fm_name = QFontMetrics(f_name)
    if fm_name.horizontalAdvance(name_raw) > max_name_width:
        # Уменьшаем
        f_name = _fit_font(name_raw, NAME_MAX_MM, max_name_width,
                           bold=True, min_mm=2.0)

    name = _elide(name_raw, f_name, max_name_width)

    y = _mm(1)
    p.setFont(f_name)
    p.drawText(QRect(0, y, LABEL_W_PX, _mm(7)),
               Qt.AlignHCenter | Qt.AlignVCenter, name)
    y += _mm(7.5)

    # ================= ДАТА МАРКИРОВКИ =================
    f_label = _make_font(LABEL_MM, bold=True)
    f_value = _make_font(VALUE_BASE_MM, bold=True)

    p.setFont(f_label)
    p.drawText(QRect(left, y, width, _mm(4)),
               Qt.AlignLeft | Qt.AlignVCenter,
               'Дата и время маркировки:')
    y += _mm(4)

    date_val = data.get('print_time_str', '') or ''
    # Значение по центру — макс ширина = вся этикетка минус 2 мм с каждой стороны
    f_dt = _fit_font(date_val, VALUE_BASE_MM,
                     LABEL_W_PX - _mm(4), bold=True, min_mm=2.5)
    p.setFont(f_dt)
    p.drawText(QRect(0, y, LABEL_W_PX, _mm(5.5)),
               Qt.AlignHCenter | Qt.AlignVCenter, date_val)
    y += _mm(5.5)

    # ---- Линия ----
    p.setPen(QPen(black, 2))
    p.drawLine(left, y, right, y)
    p.setPen(black)
    y += _mm(1.5)

    # ================= ТЕМПЕРАТУРА =================
    label_left = 'Темп. хранения:'
    value_temp = data.get('storage_temperature', '') or ''

    p.setFont(f_label)
    p.drawText(QRect(left, y, int(width * 0.5), _mm(4.5)),
               Qt.AlignLeft | Qt.AlignVCenter, label_left)

    # Правая часть — оставляем не более 55% ширины
    right_max = int(width * 0.55)
    f_val_temp = _fit_font(value_temp, VALUE_BASE_MM, right_max,
                           bold=True, min_mm=2.5)
    value_temp = _elide(value_temp, f_val_temp, right_max)
    p.setFont(f_val_temp)
    p.drawText(QRect(left, y, width, _mm(4.5)),
               Qt.AlignRight | Qt.AlignVCenter, value_temp)
    y += _mm(5)

    # ================= СРОК ХРАНЕНИЯ =================
    label_period = 'Срок хранения:'
    value_period = data.get('storage_period_text', '') or ''

    p.setFont(f_label)
    p.drawText(QRect(left, y, int(width * 0.5), _mm(4.5)),
               Qt.AlignLeft | Qt.AlignVCenter, label_period)

    f_val_period = _fit_font(value_period, VALUE_BASE_MM, right_max,
                             bold=True, min_mm=2.5)
    value_period = _elide(value_period, f_val_period, right_max)
    p.setFont(f_val_period)
    p.drawText(QRect(left, y, width, _mm(4.5)),
               Qt.AlignRight | Qt.AlignVCenter, value_period)
    y += _mm(5)

    # ---- Линия ----
    p.setPen(QPen(black, 2))
    p.drawLine(left, y, right, y)
    p.setPen(black)
    y += _mm(1.5)

    # ================= ГОДЕН ДО =================
    f_goden = _make_font(GODEN_LABEL_MM, bold=True)
    p.setFont(f_goden)
    p.drawText(QRect(left, y, width, _mm(4)),
               Qt.AlignLeft | Qt.AlignVCenter,
               'Годен до:')
    y += _mm(4)

    exp_val = data.get('expiration_time_str', '') or ''
    f_exp = _fit_font(exp_val, VALUE_BASE_MM,
                      LABEL_W_PX - _mm(4), bold=True, min_mm=2.5)
    p.setFont(f_exp)
    p.drawText(QRect(0, y, LABEL_W_PX, _mm(5.5)),
               Qt.AlignHCenter | Qt.AlignVCenter, exp_val)
    y += _mm(6)

    # ================= ФУТЕР =================
    marked = data.get('marked_by') or ''
    if marked:
        footer = f'Маркировал: {marked}'
        f_footer = _fit_font(footer, FOOTER_MM,
                             LABEL_W_PX - _mm(4), bold=True, min_mm=2.0)
        footer = _elide(footer, f_footer, LABEL_W_PX - _mm(4))
        p.setFont(f_footer)
        p.drawText(QRect(0, y, LABEL_W_PX, _mm(4)),
                   Qt.AlignHCenter | Qt.AlignVCenter, footer)

    p.end()
    return pm