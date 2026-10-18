"""Modali comuni: overlay scuro + sfocatura dello sfondo, carta con ombra e bordo accento."""
from PySide6.QtCore import QEvent, QObject, QTimer, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QApplication, QDialog, QFrame, QGraphicsBlurEffect, QGraphicsDropShadowEffect, QHBoxLayout,
    QPushButton, QVBoxLayout, QWidget,
)

from .toast import show_toast

BLUR_RADIUS = 8


def app_scale() -> float:
    return float(QApplication.instance().property("ui_scale") or 1.0)


def center_on(dialog, parent):
    """Centra `dialog` sulla finestra padre (o sullo schermo)."""
    ref = parent.window().frameGeometry() if parent is not None else dialog.screen().geometry()
    dialog.move(ref.center() - dialog.rect().center())


class ModalOverlay(QWidget):
    """Velo semitrasparente su tutta la finestra ospite (colore dal tema, vedi styles.qss)."""

    def __init__(self, host: QWidget):
        super().__init__(host)
        self.setObjectName("ModalOverlay")
        self.setAttribute(Qt.WA_StyledBackground, True)
        host.installEventFilter(self)
        self.setGeometry(host.rect())

    def eventFilter(self, obj: QObject, e: QEvent):
        if e.type() == QEvent.Resize:
            self.setGeometry(self.parentWidget().rect())
        return False

    # -- gestione condivisa: un solo overlay per finestra, anche con modali annidati
    @staticmethod
    def acquire(host: QWidget):
        depth = getattr(host, "_modal_depth", 0)
        if depth == 0:
            overlay = ModalOverlay(host)
            host._modal_overlay = overlay
            target = getattr(host, "blur_target", None)
            if target is not None:
                blur = QGraphicsBlurEffect(target)
                blur.setBlurRadius(BLUR_RADIUS)
                blur.setBlurHints(QGraphicsBlurEffect.QualityHint)
                target.setGraphicsEffect(blur)
            overlay.show()
            overlay.raise_()
        host._modal_depth = depth + 1

    @staticmethod
    def release(host: QWidget):
        depth = getattr(host, "_modal_depth", 0) - 1
        host._modal_depth = max(0, depth)
        if depth <= 0:
            overlay = getattr(host, "_modal_overlay", None)
            if overlay is not None:
                overlay.hide()
                overlay.deleteLater()
                host._modal_overlay = None
            target = getattr(host, "blur_target", None)
            if target is not None:
                target.setGraphicsEffect(None)


class BaseModal(QDialog):
    """Base di tutti i dialoghi modali. Fornisce `self.body` (layout della carta),
    overlay + blur dello sfondo, ombra, centratura e un toast differito."""

    def __init__(self, parent, w_frac=None, h_frac=None, width_px=None, min_size=(0, 0)):
        super().__init__(parent, Qt.Dialog | Qt.FramelessWindowHint)
        self.setObjectName("Modal")
        self.setModal(True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.s = app_scale()
        self._host = parent.window() if parent is not None else None
        self._overlay_on = False
        self._pending_toast = None

        pad = self.pad = round(28 * self.s)  # spazio per l'ombra
        outer = QVBoxLayout(self)
        outer.setContentsMargins(pad, pad, pad, pad)
        self.card = QFrame(objectName="ModalCard")
        shadow = QGraphicsDropShadowEffect(self.card)
        shadow.setBlurRadius(round(46 * self.s))
        shadow.setOffset(0, round(10 * self.s))
        shadow.setColor(QColor(0, 0, 0, 170))
        self.card.setGraphicsEffect(shadow)
        outer.addWidget(self.card)

        self.body = QVBoxLayout(self.card)
        m = round(30 * self.s)
        self.body.setContentsMargins(m, m, m, m)
        self.body.setSpacing(round(16 * self.s))

        # dimensione bersaglio, fissata UNA volta in finalize() (nessun ridimensionamento dinamico)
        screen = parent.screen() if parent is not None else self.screen()
        geo = screen.geometry()
        self._max_w, self._max_h = int(geo.width() * 0.96), int(geo.height() * 0.96)
        if width_px:
            self._target_w, self._target_h = width_px + 2 * pad, 0
        else:
            self._target_w = int(geo.width() * w_frac)
            self._target_h = int(geo.height() * h_frac)
        self._min_w, self._min_h = min_size

    def finalize(self):
        """Da chiamare a fine __init__ del dialogo: calcola e blocca la dimensione (una sola volta).
        Mai piu' piccola del minimo richiesto dal contenuto, cosi' nulla viene tagliato."""
        for w in self.findChildren(QWidget):
            w.ensurePolished()
        self.layout().activate()
        need = self.layout().minimumSize()
        w = min(max(self._target_w, self._min_w, need.width()), self._max_w)
        h = min(max(self._target_h, self._min_h, need.height()), self._max_h)
        self.setFixedSize(w, h)

    def add_close_button(self, text="Chiudi"):
        btn = QPushButton(text, objectName="AccentButton")
        btn.setMinimumSize(round(240 * self.s), round(60 * self.s))
        btn.clicked.connect(self.accept)
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(btn)
        row.addStretch(1)
        self.body.addLayout(row)
        btn.setDefault(True)
        return btn

    def toast_when_shown(self, text: str):
        self._pending_toast = text

    def showEvent(self, e):
        super().showEvent(e)
        if self._host is not None and not self._overlay_on:
            self._overlay_on = True
            ModalOverlay.acquire(self._host)
        center_on(self, self.parentWidget())
        self.raise_()
        self.activateWindow()
        if self._pending_toast:
            text, self._pending_toast = self._pending_toast, None
            QTimer.singleShot(60, lambda: show_toast(self, text))

    def hideEvent(self, e):
        super().hideEvent(e)
        if self._overlay_on:
            self._overlay_on = False
            ModalOverlay.release(self._host)
