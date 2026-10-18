"""Widget condivisi del wizard: indicatore dei passi, selettore numerico touch, gruppo."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget


class StepIndicator(QWidget):
    """1 Foglio › 2 Colonne › 3 Dettagli"""

    def __init__(self, labels, scale, parent=None):
        super().__init__(parent)
        self.setObjectName("TabPage")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(round(8 * scale))
        self._pills = []
        for i, text in enumerate(labels):
            if i:
                lay.addWidget(QLabel("›", objectName="StepArrow"))
            pill = QLabel(f"{i + 1}  {text}", objectName="StepPill")
            pill.setProperty("state", "todo")
            lay.addWidget(pill)
            self._pills.append(pill)

    def set_step(self, current: int):
        for i, pill in enumerate(self._pills):
            pill.setProperty("state", "active" if i == current else "done" if i < current else "todo")
            pill.style().unpolish(pill)
            pill.style().polish(pill)


class Stepper(QWidget):
    """− valore + (pulsanti grandi per il touch)."""

    changed = Signal(int)

    def __init__(self, scale, value=1, minimum=1, maximum=999, parent=None):
        super().__init__(parent)
        self.setObjectName("TabPage")
        self._min, self._max, self._value = minimum, maximum, value
        size = max(44, round(46 * scale))
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(round(8 * scale))
        self.minus = QPushButton("−", objectName="StepperButton")
        self.plus = QPushButton("+", objectName="StepperButton")
        self.label = QLabel(str(value), objectName="StepperValue", alignment=Qt.AlignCenter)
        self.label.setMinimumWidth(round(44 * scale))
        for b in (self.minus, self.plus):
            b.setFixedSize(size, size)
            b.setFocusPolicy(Qt.NoFocus)
            b.setAutoRepeat(True)
            b.setAutoRepeatDelay(400)
        lay.addWidget(self.minus)
        lay.addWidget(self.label)
        lay.addWidget(self.plus)
        self.minus.clicked.connect(lambda: self.set_value(self._value - 1))
        self.plus.clicked.connect(lambda: self.set_value(self._value + 1))

    def value(self) -> int:
        return self._value

    def set_value(self, v: int, emit=True):
        v = max(self._min, min(self._max, int(v)))
        if v == self._value:
            return
        self._value = v
        self.label.setText(str(v))
        if emit:
            self.changed.emit(v)


def make_group(scale, title=None):
    """Riquadro con titolo opzionale. Ritorna (frame, layout)."""
    frame = QFrame(objectName="GroupBox")
    lay = QVBoxLayout(frame)
    m = round(10 * scale)
    lay.setContentsMargins(m, round(8 * scale), m, m)
    lay.setSpacing(round(4 * scale))
    if title:
        lay.addWidget(QLabel(title, objectName="GroupTitle"))
    return frame, lay
