# api_client.py
import requests
import time


class ApiError(Exception):
    pass


class ApiClient:
    def __init__(self, base_url, api_key):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session = requests.Session()

    def _get(self, path, **params):
        params['key'] = self.api_key
        url = f'{self.base_url}{path}'

        last_error = None
        for attempt in range(3):  # 3 попытки
            try:
                r = self.session.get(url, params=params, timeout=20)
                break
            except requests.RequestException as e:
                last_error = e
                if attempt < 2:
                    time.sleep(0.5 + attempt * 0.5)  # 0.5, 1.0 сек
                    continue
                raise ApiError(f'Нет связи с сервером: {e}')

        if r.status_code == 401:
            raise ApiError('Неверный или отозванный ключ')
        if r.status_code == 403:
            raise ApiError('Нет доступа')
        if not r.ok:
            raise ApiError(f'Ошибка сервера: {r.status_code}')

        data = r.json()
        if not data.get('success'):
            raise ApiError(data.get('error', 'Неизвестная ошибка'))
        return data

    # ---------- API ----------

    def me(self):
        return self._get('/api/me/')

    def labels(self, establishment_id, category=None):
        params = {}
        if category is not None:
            params['category'] = category
        return self._get(f'/api/establishments/{establishment_id}/labels/', **params)

    def categories(self, establishment_id):
        return self._get(f'/api/establishments/{establishment_id}/categories/')

    def employees(self, establishment_id):
        return self._get(f'/api/establishments/{establishment_id}/employees/')

    def cart(self, establishment_id):
        return self._get(f'/api/establishments/{establishment_id}/cart/')
    
    def ping(self):
        """Быстрая проверка, что сервер доступен и ключ валиден."""
        return self.me()
    
    def label_create(self, establishment_id, name, storage_duration,
                    duration_unit='hours', storage_temperature=None,
                    category_id=None, employee_id=None):
        """Создаёт новую маркировку на сервере."""
        url = f'{self.base_url}/api/establishments/{establishment_id}/labels/create/'
        data = {
            'key': self.api_key,
            'name': name,
            'storage_duration': storage_duration,
            'duration_unit': duration_unit,
        }
        if storage_temperature is not None:
            data['storage_temperature'] = storage_temperature
        if category_id is not None:
            data['category_id'] = category_id
        if employee_id is not None:
            data['employee_id'] = employee_id

        # Retry — как в _get
        last_error = None
        r = None
        for attempt in range(3):
            try:
                r = self.session.post(url, data=data, timeout=20)
                break
            except requests.RequestException as e:
                last_error = e
                if attempt < 2:
                    time.sleep(0.5 + attempt * 0.5)  # 0.5, 1.0 сек
                    continue
                raise ApiError(f'Нет связи с сервером: {e}')

        if r.status_code == 401:
            raise ApiError('Неверный или отозванный ключ')
        if r.status_code == 403:
            raise ApiError('Нет доступа')
        if not r.ok:
            raise ApiError(f'Ошибка сервера: {r.status_code}')

        result = r.json()
        if not result.get('success'):
            raise ApiError(result.get('error', 'Неизвестная ошибка'))
        return result
    
    
    
    # ---------- Сотрудники ----------

    def employee_create(self, establishment_id, name, position=''):
        url = f'{self.base_url}/api/establishments/{establishment_id}/employees/create/'
        data = {'key': self.api_key, 'name': name, 'position': position}
        return self._post(url, data)

    def employee_update(self, establishment_id, employee_id, name, position=''):
        url = f'{self.base_url}/api/establishments/{establishment_id}/employees/{employee_id}/update/'
        data = {'key': self.api_key, 'name': name, 'position': position}
        return self._post(url, data)

    def employee_delete(self, establishment_id, employee_id):
        url = f'{self.base_url}/api/establishments/{establishment_id}/employees/{employee_id}/delete/'
        return self._post(url, {'key': self.api_key})

    def employee_toggle(self, establishment_id, employee_id):
        url = f'{self.base_url}/api/establishments/{establishment_id}/employees/{employee_id}/toggle/'
        return self._post(url, {'key': self.api_key})

    # ---------- Категории ----------

    def category_create(self, establishment_id, name, color='#6c757d', order=0):
        url = f'{self.base_url}/api/establishments/{establishment_id}/categories/create/'
        data = {'key': self.api_key, 'name': name, 'color': color, 'order': order}
        return self._post(url, data)

    def category_update(self, establishment_id, category_id, name, color, order):
        url = f'{self.base_url}/api/establishments/{establishment_id}/categories/{category_id}/update/'
        data = {'key': self.api_key, 'name': name, 'color': color, 'order': order}
        return self._post(url, data)

    def category_delete(self, establishment_id, category_id):
        url = f'{self.base_url}/api/establishments/{establishment_id}/categories/{category_id}/delete/'
        return self._post(url, {'key': self.api_key})

    def category_toggle(self, establishment_id, category_id):
        url = f'{self.base_url}/api/establishments/{establishment_id}/categories/{category_id}/toggle/'
        return self._post(url, {'key': self.api_key})
    
    
    def _post(self, url, data):
        for attempt in range(3):
            try:
                r = self.session.post(url, data=data, timeout=20)
                break
            except requests.RequestException as e:
                if attempt < 2:
                    time.sleep(0.5 + attempt * 0.5)
                    continue
                raise ApiError(f'Нет связи с сервером: {e}')

        if r.status_code == 401:
            raise ApiError('Неверный или отозванный ключ')
        if r.status_code == 403:
            raise ApiError('Нет доступа')
        if not r.ok:
            raise ApiError(f'Ошибка сервера: {r.status_code}')

        result = r.json()
        if not result.get('success'):
            raise ApiError(result.get('error', 'Неизвестная ошибка'))
        return result