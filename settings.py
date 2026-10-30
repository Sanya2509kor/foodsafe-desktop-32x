# settings.py
import json
from paths import config_file


DEFAULTS = {
    'api_url': 'https://markirovki24.ru',
    'api_key': '',
    'printer_name': '',
    'label_width_mm': 58,
    'label_height_mm': 60,
    'auto_sync_on_start': False,
    'auto_sync_minutes': 0,
    'selected_employee': {},
    'categories_visible': True,
    'theme': 'light',
    # НОВОЕ:
    'print_delay_ms': 300,   # пауза между этикетками, миллисекунды
    'ui_scale': 'normal',   # 'normal' | 'large' | 'xlarge'
    'remote_print_enabled': True,
}

def load_config():
    f = config_file()
    if f.exists():
        try:
            data = json.loads(f.read_text(encoding='utf-8'))
            return {**DEFAULTS, **data}
        except Exception:
            pass
    return dict(DEFAULTS)


def save_config(cfg):
    config_file().write_text(
        json.dumps(cfg, ensure_ascii=False, indent=2),
        encoding='utf-8'
    )
    
def get_selected_employee(establishment_id):
    cfg = load_config()
    return cfg.get('selected_employee', {}).get(str(establishment_id))


def set_selected_employee(establishment_id, employee_id):
    cfg = load_config()
    sel = cfg.get('selected_employee', {})
    if employee_id is None:
        sel.pop(str(establishment_id), None)
    else:
        sel[str(establishment_id)] = employee_id
    cfg['selected_employee'] = sel
    save_config(cfg)