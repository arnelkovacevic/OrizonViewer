"""Passo 2 — Colonne: selezione e ordine (frecce ▲▼, adatte al touch)."""
from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox, QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
)
from PySide6.QtGui import QFontMetrics

from .common import Stepper


class ColumnRow(QFrame):
    moveRequested = Signal(object, int)   # (riga, -1 su / +1 giu')
    toggled = Signal()
    dragMoved = Signal(object, int)       # (riga, y globale del cursore)

    def __init__(self, name: str, sample: str, scale: float, parent=None):
        super().__init__(parent)
        self.setObjectName("ColumnRow")
        self.name = name
        lay = QHBoxLayout(self)
        m = round(8 * scale)
        lay.setContentsMargins(m, round(4 * scale), m, round(4 * scale))
        lay.setSpacing(round(10 * scale))
        self.grip = QLabel("⋮⋮", objectName="ColSample")
        self.grip.setToolTip("Trascina per cambiare l'ordine")
        lay.addWidget(self.grip)
        self.check = QCheckBox()
        self.check.toggled.connect(lambda _c: self.toggled.emit())
        lay.addWidget(self.check)
        title = QLabel(name, objectName="ColName")
        title.setMinimumWidth(round(120 * scale))
        lay.addWidget(title, 2)
        self.sample = QLabel("", objectName="ColSample")
        self.sample.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.sample.setToolTip(sample)
        self._sample_full = sample
        lay.addWidget(self.sample, 3)
        size = max(44, round(44 * scale))
        self.up = QPushButton("▲", objectName="MoveButton")
        self.down = QPushButton("▼", objectName="MoveButton")
        for b, d in ((self.up, -1), (self.down, 1)):
            b.setFixedSize(size, size)
            b.setFocusPolicy(Qt.NoFocus)
            b.clicked.connect(lambda _=False, delta=d: self.moveRequested.emit(self, delta))
            lay.addWidget(b)
        self.setMinimumHeight(size + round(10 * scale))

    # --- trascinamento (alternativo alle frecce)
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._press_y = e.globalPosition().toPoint().y()
            self._dragging = False
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if e.buttons() & Qt.LeftButton and hasattr(self, "_press_y"):
            y = e.globalPosition().toPoint().y()
            if self._dragging or abs(y - self._press_y) > 8:
                if not self._dragging:
                    self._dragging = True
                    self.setCursor(Qt.ClosedHandCursor)
                self.dragMoved.emit(self, y)
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        self._dragging = False
        self.unsetCursor()
        super().mouseReleaseEvent(e)

    def resizeEvent(self, e):  # solo elisione del testo di esempio; non cambia la dimensione
        super().resizeEvent(e)
        fm = QFontMetrics(self.sample.font())
        text = f"es. {self._sample_full}" if self._sample_full else "(vuoto)"
        self.sample.setText(fm.elidedText(text, Qt.ElideRight, max(20, self.sample.width())))


class StepColumns(QWidget):
    selectionChanged = Signal()
    headerRowChanged = Signal(int)

    def __init__(self, scale, parent=None):
        super().__init__(parent)
        self.setObjectName("TabPage")
        self.s = scale
        self._rows = []
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(round(8 * scale))

        top = QHBoxLayout()
        self.info = QLabel("", objectName="WizardInfo")
        top.addWidget(self.info, 1)
        top.addWidget(QLabel("Riga intestazione", objectName="WizardHint"))
        self.stepper = Stepper(scale, 1)
        self.stepper.changed.connect(self.headerRowChanged)
        top.addWidget(self.stepper)
        lay.addLayout(top)

        bar = QHBoxLayout()
        bar.setSpacing(round(10 * scale))
        self.btn_all = QPushButton("Seleziona tutto", objectName="SecondaryButton")
        self.btn_none = QPushButton("Deseleziona tutto", objectName="SecondaryButton")
        for b in (self.btn_all, self.btn_none):
            b.setMinimumHeight(max(44, round(44 * scale)))
            bar.addWidget(b)
        self.count = QLabel("", objectName="WizardHint")
        bar.addWidget(self.count, 1, Qt.AlignRight)
        lay.addLayout(bar)
        self.btn_all.clicked.connect(lambda: self.set_all(True))
        self.btn_none.clicked.connect(lambda: self.set_all(False))

        self.scroll = QScrollArea(objectName="WizardScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.holder = QWidget(objectName="TabPage")
        self.rows_layout = QVBoxLayout(self.holder)
        self.rows_layout.setContentsMargins(0, 0, round(6 * scale), 0)
        self.rows_layout.setSpacing(round(6 * scale))
        self.rows_layout.addStretch(1)
        self.scroll.setWidget(self.holder)
        lay.addWidget(self.scroll, 1)

    # ------------------------------------------------------------ dati
    def set_columns(self, names: list, samples: list, selected: set):
        for r in self._rows:
            r.setParent(None)
            r.deleteLater()
        self._rows = []
        for name, sample in zip(names, samples):
            row = ColumnRow(name, sample, self.s)
            row.check.setChecked(name in selected)
            row.moveRequested.connect(self._move)
            row.dragMoved.connect(self._drag)
            row.toggled.connect(self._changed)
            self._rows.append(row)
            self.rows_layout.insertWidget(self.rows_layout.count() - 1, row)
        n = len(names)
        self.info.setText(f"Il foglio contiene {n} {'colonna' if n == 1 else 'colonne'}.")
        self._refresh_arrows()
        self._changed()

    def selected_in_order(self) -> list:
        return [r.name for r in self._rows if r.check.isChecked()]

    def all_in_order(self) -> list:
        return [r.name for r in self._rows]

    def set_all(self, on: bool):
        for r in self._rows:
            r.check.blockSignals(True)
            r.check.setChecked(on)
            r.check.blockSignals(False)
        self._changed()

    # ------------------------------------------------------------ ordine
    def _move(self, row, delta: int):
        i = self._rows.index(row)
        j = i + delta
        if not 0 <= j < len(self._rows):
            return
        self._rows[i], self._rows[j] = self._rows[j], self._rows[i]
        self.rows_layout.removeWidget(row)
        self.rows_layout.insertWidget(j, row)
        self._refresh_arrows()
        self.selectionChanged.emit()
        self.scroll.ensureWidgetVisible(row)

    def _drag(self, row, global_y: int):
        y = self.holder.mapFromGlobal(QPoint(0, global_y)).y()
        i = self._rows.index(row)
        target = sum(1 for r in self._rows if r is not row and r.geometry().center().y() < y)
        if target != i:
            self._move(row, target - i)

    def _refresh_arrows(self):
        last = len(self._rows) - 1
        for i, r in enumerate(self._rows):
            r.up.setEnabled(i > 0)
            r.down.setEnabled(i < last)

    def _changed(self):
        n = len(self.selected_in_order())
        self.count.setText(f"{n} selezionate" if n != 1 else "1 selezionata")
        self.selectionChanged.emit()
