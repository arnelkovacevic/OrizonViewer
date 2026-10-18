"""Interruttore on/off animato (non un semplice checkbox)."""
from PySide6.QtCore import Property, QEasingCurve, QPropertyAnimation, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QAbstractButton

from . import theme


class ToggleSwitch(QAbstractButton):
    def __init__(self, scale: float = 1.0, checked: bool = False, parent=None):
        super().__init__(parent)
        self._w, self._h = round(60 * scale), round(32 * scale)
        self.setCheckable(True)
        self.setChecked(checked)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.NoFocus)
        self.setFixedSize(self._w, self._h)
        self._pos = 1.0 if checked else 0.0
        self._anim = QPropertyAnimation(self, b"offset", self)
        self._anim.setDuration(160)
        self._anim.setEasingCurve(QEasingCurve.InOutCubic)
        self.toggled.connect(self._animate)

    def sizeHint(self):
        return QSize(self._w, self._h)

    def _animate(self, on: bool):
        self._anim.stop()
        self._anim.setStartValue(self._pos)
        self._anim.setEndValue(1.0 if on else 0.0)
        self._anim.start()

    def _get_offset(self) -> float:
        return self._pos

    def _set_offset(self, v: float):
        self._pos = v
        self.update()

    offset = Property(float, _get_offset, _set_offset)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        off, on = theme.qcolor("toggle_off"), theme.qcolor("accent")
        t = self._pos
        track = QColor(
            round(off.red() + (on.red() - off.red()) * t),
            round(off.green() + (on.green() - off.green()) * t),
            round(off.blue() + (on.blue() - off.blue()) * t),
        )
        if not self.isEnabled():
            track.setAlpha(110)
        p.setPen(Qt.NoPen)
        p.setBrush(track)
        p.drawRoundedRect(QRectF(0, 0, self._w, self._h), self._h / 2, self._h / 2)
        m = self._h * 0.12
        d = self._h - 2 * m
        x = m + (self._w - 2 * m - d) * t
        p.setBrush(QColor("#FFFFFF"))
        p.drawEllipse(QRectF(x, m, d, d))
