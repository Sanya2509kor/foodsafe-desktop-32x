# sync.py
from datetime import datetime
from api_client import ApiClient, ApiError
import local_db


def sync_all(api: ApiClient, status_cb=None, with_cart: bool = False):
    """
    Полная синхронизация: заведения + по каждому заведению категории,
    маркировки, сотрудники.
    Корзина синхронизируется только при with_cart=True.

    status_cb(text) — вызывается для отображения статуса.
    """
    def report(msg):
        if status_cb:
            status_cb(msg)

    report('Получаем список заведений...')
    me = api.me()
    establishments = me['establishments']
    local_db.save_establishments(establishments)

    for est in establishments:
        est_id = est['id']

        report(f'Категории: {est["name"]}...')
        try:
            cats = api.categories(est_id)['categories']
            local_db.save_categories(est_id, cats)
        except ApiError as e:
            report(f'  ⚠ категории: {e}')

        report(f'Сотрудники: {est["name"]}...')
        try:
            emps = api.employees(est_id)['employees']
            local_db.save_employees(est_id, emps)
        except ApiError as e:
            report(f'  ⚠ сотрудники: {e}')

        report(f'Маркировки: {est["name"]}...')
        try:
            lbls = api.labels(est_id)['labels']
            local_db.save_labels(est_id, lbls)
        except ApiError as e:
            report(f'  ⚠ маркировки: {e}')

        if with_cart:
            report(f'Корзина: {est["name"]}...')
            try:
                cart = api.cart(est_id)
                local_db.save_cart(est_id, cart.get('items', []))
            except ApiError as e:
                report(f'  ⚠ корзина: {e}')

    now = datetime.now().strftime('%d.%m.%Y %H:%M')
    local_db.set_meta('last_sync', now)
    report(f'✅ Синхронизация завершена: {now}')
    return True


def sync_cart_for_establishment(api: ApiClient, establishment_id: int):
    """
    Синхронизирует корзину только одного заведения.
    Перезаписывает локальную корзину серверной.
    Возвращает количество items с сервера.
    """
    cart = api.cart(establishment_id)
    items = cart.get('items', [])
    local_db.save_cart(establishment_id, items)
    return len(items)