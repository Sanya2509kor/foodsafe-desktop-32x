# ui/print_poller.py
from PyQt5.QtCore import QRunnable, QObject, pyqtSignal, pyqtSlot

from api_client import ApiClient, ApiError


class PollSignals(QObject):
    """Сигналы для передачи результата в GUI-поток."""
    finished = pyqtSignal(list)     # список заданий
    error = pyqtSignal(str)         # сообщение об ошибке


class PollRunnable(QRunnable):
    """
    Фоновая задача: получить pending-задания с сервера.
    Результат передаётся через сигналы в GUI-поток.
    """
    def __init__(self, api: ApiClient, establishment_id: int):
        super().__init__()
        self.api = api
        self.establishment_id = establishment_id
        self.signals = PollSignals()
        self.setAutoDelete(True)

    @pyqtSlot()
    def run(self):
        try:
            data = self.api.print_pending_fast(self.establishment_id)
            jobs = data.get('jobs', [])
            self.signals.finished.emit(jobs)
        except ApiError as e:
            self.signals.error.emit(str(e))
        except Exception as e:
            self.signals.error.emit(f'Unexpected: {e}')