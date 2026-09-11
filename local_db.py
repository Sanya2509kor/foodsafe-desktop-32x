import sqlite3
from contextlib import contextmanager

from paths import db_file


@contextmanager
def conn():
    c = sqlite3.connect(db_file())
    c.row_factory = sqlite3.Row
    try:
        yield c
        c.commit()
    finally:
        c.close()


def init_db():
    with conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        CREATE TABLE IF NOT EXISTS establishments (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            role TEXT,
            timezone TEXT,
            invite_code TEXT
        );
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY,
            establishment_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            color TEXT,
            order_num INTEGER,
            is_active INTEGER
        );
        CREATE TABLE IF NOT EXISTS labels (
            id INTEGER PRIMARY KEY,
            establishment_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            category_id INTEGER,
            category_name TEXT,
            category_color TEXT,
            storage_temperature TEXT,
            storage_duration INTEGER,
            duration_unit TEXT,
            storage_period_text TEXT,
            marked_by TEXT,
            employee_id INTEGER,
            employee_name TEXT,
            created_at TEXT,
            last_printed_at TEXT,
            manual_print_time TEXT
        );
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY,
            establishment_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            position TEXT,
            is_active INTEGER
        );
        CREATE TABLE IF NOT EXISTS cart_items (
            id INTEGER PRIMARY KEY,
            establishment_id INTEGER NOT NULL,
            label_id INTEGER,
            name TEXT,
            category_name TEXT,
            category_color TEXT,
            storage_temperature TEXT,
            storage_duration INTEGER,
            duration_unit TEXT,
            storage_period_text TEXT,
            marked_by TEXT,
            quantity INTEGER
        );
        CREATE TABLE IF NOT EXISTS print_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            label_id INTEGER,
            label_name TEXT,
            printed_at TEXT,
            printer_name TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_labels_est ON labels(establishment_id);
        CREATE INDEX IF NOT EXISTS idx_labels_cat ON labels(category_id);
        CREATE INDEX IF NOT EXISTS idx_cat_est ON categories(establishment_id);
        CREATE INDEX IF NOT EXISTS idx_emp_est ON employees(establishment_id);
        CREATE INDEX IF NOT EXISTS idx_cart_est ON cart_items(establishment_id);
        """)


# ---------- meta ----------

def set_meta(key, value):
    with conn() as c:
        c.execute(
            "INSERT INTO meta(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, str(value))
        )


def get_meta(key, default=None):
    with conn() as c:
        row = c.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        return row['value'] if row else default


def last_sync():
    return get_meta('last_sync')


# ---------- establishments ----------

def save_establishments(items):
    with conn() as c:
        c.execute("DELETE FROM establishments")
        c.executemany(
            "INSERT INTO establishments(id, name, role, timezone, invite_code) "
            "VALUES(?, ?, ?, ?, ?)",
            [(e['id'], e['name'], e.get('role'), e.get('timezone'),
              e.get('invite_code')) for e in items]
        )


def get_establishments():
    with conn() as c:
        rows = c.execute("SELECT * FROM establishments ORDER BY name").fetchall()
        return [dict(r) for r in rows]


# ---------- categories ----------

def save_categories(establishment_id, items):
    with conn() as c:
        c.execute("DELETE FROM categories WHERE establishment_id = ?",
                  (establishment_id,))
        c.executemany(
            "INSERT INTO categories(id, establishment_id, name, color, order_num, is_active) "
            "VALUES(?, ?, ?, ?, ?, ?)",
            [(x['id'], establishment_id, x['name'], x.get('color'),
              x.get('order', 0), 1 if x.get('is_active') else 0) for x in items]
        )


def get_categories(establishment_id):
    with conn() as c:
        rows = c.execute(
            "SELECT * FROM categories WHERE establishment_id = ? "
            "ORDER BY order_num, name",
            (establishment_id,)
        ).fetchall()
        return [dict(r) for r in rows]


# ---------- labels ----------

def save_labels(establishment_id, items):
    with conn() as c:
        c.execute("DELETE FROM labels WHERE establishment_id = ?",
                  (establishment_id,))
        rows = []
        for x in items:
            cat = x.get('category') or {}
            emp = x.get('employee') or {}
            rows.append((
                x['id'], establishment_id, x['name'],
                cat.get('id'), cat.get('name'), cat.get('color'),
                x.get('storage_temperature'),
                x.get('storage_duration'),
                x.get('duration_unit'),
                x.get('storage_period_text'),
                x.get('marked_by'),
                emp.get('id'), emp.get('name'),
                x.get('created_at'),
                x.get('last_printed_at'),
                x.get('manual_print_time'),
            ))
        c.executemany(
            "INSERT INTO labels(id, establishment_id, name, category_id, "
            "category_name, category_color, storage_temperature, "
            "storage_duration, duration_unit, storage_period_text, marked_by, "
            "employee_id, employee_name, created_at, last_printed_at, "
            "manual_print_time) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            rows
        )


def get_labels(establishment_id):
    with conn() as c:
        rows = c.execute(
            "SELECT * FROM labels WHERE establishment_id = ? "
            "ORDER BY datetime(created_at) DESC, id DESC",
            (establishment_id,)
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d['category'] = (
                {'id': d['category_id'], 'name': d['category_name'],
                 'color': d['category_color']}
                if d['category_id'] else None
            )
            d['employee'] = (
                {'id': d['employee_id'], 'name': d['employee_name']}
                if d['employee_id'] else None
            )
            result.append(d)
        return result


# ---------- employees ----------

def save_employees(establishment_id, items):
    with conn() as c:
        c.execute("DELETE FROM employees WHERE establishment_id = ?",
                  (establishment_id,))
        c.executemany(
            "INSERT INTO employees(id, establishment_id, name, position, is_active) "
            "VALUES(?, ?, ?, ?, ?)",
            [(x['id'], establishment_id, x['name'], x.get('position'),
              1 if x.get('is_active') else 0) for x in items]
        )


def get_employees(establishment_id):
    with conn() as c:
        rows = c.execute(
            "SELECT * FROM employees WHERE establishment_id = ? ORDER BY name",
            (establishment_id,)
        ).fetchall()
        return [dict(r) for r in rows]


# ---------- cart ----------

def save_cart(establishment_id, items):
    with conn() as c:
        c.execute("DELETE FROM cart_items WHERE establishment_id = ?",
                  (establishment_id,))
        rows = []
        for x in items:
            cat = x.get('category') or {}
            rows.append((
                x['id'], establishment_id, x.get('label_id'),
                x['name'], cat.get('name'), cat.get('color'),
                x.get('storage_temperature'), x.get('storage_duration'),
                x.get('duration_unit'), x.get('storage_period_text'),
                x.get('marked_by'), x.get('quantity', 1),
            ))
        c.executemany(
            "INSERT INTO cart_items(id, establishment_id, label_id, name, "
            "category_name, category_color, storage_temperature, "
            "storage_duration, duration_unit, storage_period_text, marked_by, "
            "quantity) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            rows
        )


def get_cart(establishment_id):
    with conn() as c:
        rows = c.execute(
            "SELECT * FROM cart_items WHERE establishment_id = ?",
            (establishment_id,)
        ).fetchall()
        return [dict(r) for r in rows]
    
    
def log_print(label_id, label_name, printer_name):
    from datetime import datetime
    with conn() as c:
        c.execute(
            "INSERT INTO print_log(label_id, label_name, printed_at, printer_name) "
            "VALUES(?, ?, ?, ?)",
            (label_id, label_name, datetime.now().isoformat(timespec='seconds'), printer_name)
        )


def get_print_log(limit=100):
    with conn() as c:
        rows = c.execute(
            "SELECT * FROM print_log ORDER BY id DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
    
def get_employee(employee_id):
    with conn() as c:
        row = c.execute(
            "SELECT * FROM employees WHERE id = ?", (employee_id,)
        ).fetchone()
        return dict(row) if row else None
    
    
def insert_label(establishment_id, label_dict):
    """Вставляет одну маркировку (например, только что созданную на сервере)."""
    cat = label_dict.get('category') or {}
    emp = label_dict.get('employee') or {}
    with conn() as c:
        c.execute(
            "INSERT OR REPLACE INTO labels(id, establishment_id, name, "
            "category_id, category_name, category_color, storage_temperature, "
            "storage_duration, duration_unit, storage_period_text, marked_by, "
            "employee_id, employee_name, created_at, last_printed_at, "
            "manual_print_time) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                label_dict['id'], establishment_id, label_dict['name'],
                cat.get('id'), cat.get('name'), cat.get('color'),
                label_dict.get('storage_temperature'),
                label_dict.get('storage_duration'),
                label_dict.get('duration_unit'),
                label_dict.get('storage_period_text'),
                label_dict.get('marked_by'),
                emp.get('id'), emp.get('name'),
                label_dict.get('created_at'),
                label_dict.get('last_printed_at'),
                label_dict.get('manual_print_time'),
            )
        )
        
        
# ---------- cart: локальные операции ----------

def cart_add(establishment_id, label):
    """
    Добавляет маркировку в локальную корзину.
    Если такая уже есть — увеличивает quantity на 1.
    label — dict с полями из labels (name, storage_temperature, ...).
    """
    with conn() as c:
        # Проверяем, есть ли уже такая позиция
        row = c.execute(
            "SELECT id, quantity FROM cart_items "
            "WHERE establishment_id = ? AND label_id = ?",
            (establishment_id, label['id'])
        ).fetchone()

        if row:
            c.execute(
                "UPDATE cart_items SET quantity = quantity + 1 WHERE id = ?",
                (row['id'],)
            )
        else:
            cat = label.get('category') or {}
            c.execute(
                "INSERT INTO cart_items(establishment_id, label_id, name, "
                "category_name, category_color, storage_temperature, "
                "storage_duration, duration_unit, storage_period_text, "
                "marked_by, quantity) "
                "VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)",
                (
                    establishment_id,
                    label['id'],
                    label['name'],
                    cat.get('name'),
                    cat.get('color'),
                    label.get('storage_temperature'),
                    label.get('storage_duration'),
                    label.get('duration_unit'),
                    label.get('storage_period_text'),
                    label.get('marked_by'),
                )
            )


def cart_count(establishment_id):
    """Сколько всего штук в корзине для заведения."""
    with conn() as c:
        row = c.execute(
            "SELECT COALESCE(SUM(quantity), 0) AS total "
            "FROM cart_items WHERE establishment_id = ?",
            (establishment_id,)
        ).fetchone()
        return int(row['total'])


def cart_update_quantity(item_id, quantity):
    """Меняет количество. Если quantity <= 0 — удаляет."""
    with conn() as c:
        if quantity <= 0:
            c.execute("DELETE FROM cart_items WHERE id = ?", (item_id,))
        else:
            c.execute(
                "UPDATE cart_items SET quantity = ? WHERE id = ?",
                (quantity, item_id)
            )


def cart_remove(item_id):
    with conn() as c:
        c.execute("DELETE FROM cart_items WHERE id = ?", (item_id,))


def cart_clear(establishment_id):
    with conn() as c:
        c.execute("DELETE FROM cart_items WHERE establishment_id = ?",
                  (establishment_id,))