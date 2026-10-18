"""Gestione degli errori imprevisti (sys.excepthook / threading.excepthook) di main.py."""
import sys
import threading

import pytest
from PySide6.QtCore import QObject, Signal

from gui_helpers import pump


@pytest.fixture()
def crash(qapp, tmp_path, monkeypatch):
    saved = (sys.excepthook, threading.excepthook)
    import main
    monkeypatch.setattr(main.auth, "data_dir", lambda: str(tmp_path / "dati"))
    main._handling_error = False
    shown = []

    from app.error_dialog import ErrorDialog
    monkeypatch.setattr(ErrorDialog, "exec", lambda self: (shown.append(
        {"path": self.path_label.text(), "size": (self.width(), self.height())}), 0)[1])
    main.install_excepthooks()
    yield main, shown, tmp_path / "dati" / "orizon.log"
    sys.excepthook, threading.excepthook = saved


def _raise():
    try:
        raise RuntimeError("boom di prova")
    except RuntimeError:
        return sys.exc_info()


def test_unexpected_error_is_logged_with_traceback_and_dialog_shown(crash):
    main, shown, log = crash
    assert sys.excepthook is main.handle_exception and threading.excepthook is main.handle_thread_exception
    sys.excepthook(*_raise())
    text = log.read_text(encoding="utf-8")
    assert "RuntimeError: boom di prova" in text and "Traceback (most recent call last)" in text
    assert "test_crash.py" in text
    assert len(shown) == 1 and shown[0]["path"] == str(log)


def test_error_before_qapplication_only_writes_log(crash, monkeypatch):
    main, shown, log = crash
    from PySide6.QtWidgets import QApplication
    monkeypatch.setattr(QApplication, "instance", staticmethod(lambda: None))
    sys.excepthook(*_raise())
    assert "boom di prova" in log.read_text(encoding="utf-8")
    assert shown == []                                    # nessun dialogo, nessuna eccezione


def test_error_in_other_thread_shows_dialog_in_gui_thread(crash):
    main, shown, log = crash
    t = threading.Thread(target=lambda: (_ for _ in ()).throw(ValueError("errore nel thread")))
    t.start()
    t.join()
    pump(150)
    assert "ValueError: errore nel thread" in log.read_text(encoding="utf-8")
    assert len(shown) == 1


def test_exception_inside_qt_slot_reaches_the_hook(crash):
    main, shown, log = crash

    class Emitter(QObject):
        ping = Signal()

    class Receiver(QObject):
        def slot(self):
            raise KeyError("errore nello slot")

    e, r = Emitter(), Receiver()
    e.ping.connect(r.slot)
    e.ping.emit()
    pump(50)
    assert "KeyError" in log.read_text(encoding="utf-8") and len(shown) == 1


def test_keyboard_interrupt_is_not_swallowed(crash, monkeypatch):
    main, shown, log = crash
    called = []
    monkeypatch.setattr(sys, "__excepthook__", lambda *a: called.append(a[0]))
    sys.excepthook(KeyboardInterrupt, KeyboardInterrupt(), None)
    assert called == [KeyboardInterrupt] and shown == [] and not log.exists()


def test_no_dialog_loop_when_already_handling(crash):
    main, shown, log = crash
    main._handling_error = True
    sys.excepthook(*_raise())
    main._handling_error = False
    assert shown == [] and "boom" in log.read_text(encoding="utf-8")


def test_log_directory_is_created(crash):
    main, shown, log = crash
    assert not log.parent.exists()
    sys.excepthook(*_raise())
    assert log.exists()


def test_error_dialog_layout_and_texts(qapp):
    from app.error_dialog import ErrorDialog
    from PySide6.QtWidgets import QLabel, QPushButton
    long_path = "C:\\Users\\Mario Rossi\\AppData\\Roaming\\Orizon-AIX\\OrizonViewer\\orizon.log"
    d = ErrorDialog(None, long_path)
    d.show()
    size = d.size()
    pump(500)
    assert d.size() == size                                # dimensione fissa
    texts = [l.text() for l in d.findChildren(QLabel)]
    assert "Si è verificato un errore imprevisto" in texts and long_path in texts
    assert [b.text() for b in d.findChildren(QPushButton)] == ["Chiudi"]
    d.findChildren(QPushButton)[0].click()
    assert d.result() == 1
