"""Notifiche toast non modali, al posto dei QMessageBox."""
from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt, QTimer
from PySide6.QtWidgets import QDialog, QGraphicsOpacityEffect, QLabel, QWidget


class Toast(QLabel):
    def __init__(self, parent: QWidget, text: str, kind: str):
        super().__init__(text, parent)
        self.setObjectName("Toast")
        self.setProperty("kind", kind)
        self.setWordWrap(True)
        self.setAlignment(Qt.AlignCenter)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._fx = QGraphicsOpacityEffect(self)
        self._fx.setOpacity(0.0)
        self.setGraphicsEffect(self._fx)
        self._anim = None

    def _fade(self, start, end, on_done=None):
        self._anim = QPropertyAnimation(self._fx, b"opacity", self)
        self._anim.setDuration(180)
        self._anim.setStartValue(start)
        self._anim.setEndValue(end)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        if on_done:
            self._anim.finished.connect(on_done)
        self._anim.start()

    def present(self, duration_ms: int):
        parent = self.parentWidget()
        max_w = int(parent.width() * 0.9)
        self.setWordWrap(False)
        self.adjustSize()
        if self.width() > max_w:  # testo lungo: va a capo
            self.setWordWrap(True)
            self.setFixedWidth(max_w)
            self.setFixedHeight(self.heightForWidth(max_w))
        x = (parent.width() - self.width()) // 2
        if isinstance(parent, QDialog):  # nei dialoghi in alto, per non coprire i pulsanti
            y = int(parent.height() * 0.04)
        else:
            y = parent.height() - self.height() - int(parent.height() * 0.08)
        self.move(max(0, x), max(0, y))
        self.show()
        self.raise_()
        self._fade(0.0, 1.0)
        QTimer.singleShot(duration_ms, lambda: self._fade(1.0, 0.0, self.deleteLater))


def show_toast(widget: QWidget, text: str, kind: str = "error", duration_ms: int = 2600):
    """Mostra un toast in basso al centro della finestra che contiene `widget`.
    kind: 'error' | 'success' | 'info'."""
    host = widget.window()
    old = getattr(host, "_current_toast", None)
    if old is not None:
        try:
            old.hide()
            old.deleteLater()
        except RuntimeError:
            pass
    toast = Toast(host, text, kind)
    host._current_toast = toast
    toast.present(duration_ms)
    return toast
