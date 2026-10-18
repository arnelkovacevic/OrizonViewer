"""Utilita' per pilotare i dialoghi modali (exec) in test offscreen."""
import time

from PySide6.QtCore import QRect, QTimer
from PySide6.QtWidgets import QApplication


class FakeScreen:
    def __init__(self, w, h):
        self._r = QRect(0, 0, w, h)

    def geometry(self):
        return self._r


def pump(ms=100):
    app = QApplication.instance()
    end = time.time() + ms / 1000
    while time.time() < end:
        app.processEvents()
        time.sleep(0.005)


def find_dialog(cls):
    for w in QApplication.instance().topLevelWidgets():
        if isinstance(w, cls) and w.isVisible():
            return w
    return None


def run_modal(cls, action, trigger, delay=150):
    """Esegue `trigger()` (che apre un modale cls con exec) e, a modale aperto, chiama `action(dialog)`.
    L'azione deve chiudere il dialogo (accept/reject). Ritorna il valore dell'azione."""
    box = {}

    def _tick():
        dlg = find_dialog(cls)
        if dlg is None:
            QTimer.singleShot(50, _tick)
            return
        pump(80)
        box["result"] = action(dlg)

    QTimer.singleShot(delay, _tick)
    trigger()
    return box.get("result")


def wait_loaded(window, timeout=30):
    end = time.time() + timeout
    while window._loader is not None and time.time() < end:
        pump(40)
    pump(150)
