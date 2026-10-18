"""Kiosk: fullscreen con dimensione esplicita, Esc e chiusura protetta da PIN."""
import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from app import config
from app.file_profiles import ProfileStore
from app.pin_dialog import PinDialog
from gui_helpers import pump


@pytest.fixture()
def kiosk(qapp, tmp_path, monkeypatch):
    import app.main_window as mw
    monkeypatch.setattr(config, "ORG_NAME", "Orizon-AIX-PYTEST")
    monkeypatch.setattr(mw, "ProfileStore", lambda: ProfileStore(str(tmp_path / "p.json")))
    w = mw.MainWindow(1.0)
    w.settings._s.clear()
    w.settings.set_remember_last_file(False)
    w.enter_fullscreen()
    w.start_session()
    pump(300)
    yield w
    w._allow_close = True
    w.close()


def test_fullscreen_takes_screen_size(kiosk):
    assert kiosk.isFullScreen()
    assert kiosk.geometry().size() == kiosk.screen().geometry().size()
    # niente dimensioni minime/fisse piu' grandi di 1024x600
    hint = kiosk.minimumSizeHint()
    assert hint.width() <= 1024 and hint.height() <= 600
    assert kiosk.minimumSize().width() <= 1024 and kiosk.minimumSize().height() <= 600
    assert kiosk.maximumWidth() > 10000 and kiosk.maximumHeight() > 10000


def test_esc_and_close_do_not_exit(kiosk, monkeypatch):
    QTest.keyClick(kiosk, Qt.Key_Escape)
    pump(100)
    assert kiosk.isFullScreen() and kiosk.isVisible()
    asked = []
    monkeypatch.setattr(PinDialog, "ask", staticmethod(lambda parent, prompt="": (asked.append(prompt), False)[1]))
    kiosk.close()                                   # X / Alt+F4
    pump(150)
    assert asked == ["PIN per uscire"] and kiosk.isVisible()
