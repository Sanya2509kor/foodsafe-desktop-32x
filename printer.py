# printer.py
import time
import win32print
from PIL import Image


LABEL_W_MM = 58
LABEL_H_MM = 60
LABEL_W_DOTS = 464   # 58 мм * 8 точек/мм (203 dpi)
LABEL_H_DOTS = 480
GAP_MM = 3
DENSITY = 8
SPEED = 3


def list_printers():
    return [
        p[2] for p in win32print.EnumPrinters(
            win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
        )
    ]


def get_default_printer():
    return win32print.GetDefaultPrinter()


def print_image_tspl(printer_name, image_path,
                     width_mm=LABEL_W_MM, height_mm=LABEL_H_MM,
                     density=DENSITY, speed=SPEED):
    """
    Печатает PNG напрямую в принтер через TSPL-команды (RAW).
    AiYin IP802, Xprinter, TSC — все используют TSPL/TSPL2.
    """
    img = Image.open(image_path).convert('L')

    # Приводим к точному размеру
    w_dots = int(round(width_mm * 8))
    h_dots = int(round(height_mm * 8))
    if img.size != (w_dots, h_dots):
        img = img.resize((w_dots, h_dots), Image.LANCZOS)

    # 1-битный чёрно-белый
    img = img.point(lambda p: 0 if p < 128 else 255, '1')
    w, h = img.size  # 464, 480

    # --- TSPL-задание ---
    cmds = []
    cmds.append(f"SIZE {width_mm} mm,{height_mm} mm\r\n")
    cmds.append(f"GAP {GAP_MM} mm,0 mm\r\n")
    cmds.append("DIRECTION 1\r\n")
    cmds.append("REFERENCE 0,0\r\n")
    cmds.append(f"DENSITY {density}\r\n")
    cmds.append(f"SPEED {speed}\r\n")
    cmds.append("CLS\r\n")

    # BITMAP width — в БАЙТАХ, а не в точках
    width_bytes = (w + 7) // 8

    # Бинарные данные: 0 = чёрный (mode=0 у AiYin инверсный)
    pixels = img.load()
    bitmap = bytearray()
    for y in range(h):
        row = bytearray(b'\xff' * width_bytes)  # по умолчанию все белые = 1
        for x in range(w):
            if pixels[x, y] == 0:  # чёрный → ставим 0
                row[x // 8] &= ~(1 << (7 - (x % 8)))
        bitmap += row

    # Собираем все команды в один байтовый поток
    head = ''.join(cmds).encode('ascii')
    # BITMAP с заголовком + сырые данные
    bitmap_header = f"BITMAP 0,0,{width_bytes},{h},0,".encode('ascii')
    tail = b"\r\nPRINT 1,1\r\n"

    payload = head + bitmap_header + bytes(bitmap) + tail

    # RAW-задание
    hprinter = win32print.OpenPrinter(printer_name)
    try:
        job = win32print.StartDocPrinter(hprinter, 1, ('Label', None, 'RAW'))
        try:
            win32print.StartPagePrinter(hprinter)
            win32print.WritePrinter(hprinter, payload)
            win32print.EndPagePrinter(hprinter)
        finally:
            win32print.EndDocPrinter(hprinter)
    finally:
        win32print.ClosePrinter(hprinter)
        

def print_batch_tspl(printer_name, image_paths,
                     width_mm=LABEL_W_MM, height_mm=LABEL_H_MM,
                     density=DENSITY, speed=SPEED,
                     delay_ms=300):
    """
    Печатает пачку PNG по одной этикетке за раз с паузой.
    delay_ms — пауза между этикетками в миллисекундах.
    """
    if not image_paths:
        return

    delay_sec = delay_ms / 1000.0

    for i, image_path in enumerate(image_paths):
        print_image_tspl(
            printer_name, image_path,
            width_mm=width_mm, height_mm=height_mm,
            density=density, speed=speed,
        )
        if i < len(image_paths) - 1:
            time.sleep(delay_sec)