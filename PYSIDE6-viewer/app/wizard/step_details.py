"""Passo 3 — Dettagli articolo: impostazioni del popup + anteprima dal vivo."""
from typing import Optional

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox, QFrame, QHBoxLayout, QLabel, QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
)

from ..detail_dialog import DetailContent
from ..details import (
    ABOVE_SIZES, BARCODE_TYPES, HL_COLORS, HL_SIZES, TYPE_SHORT, DetailSpec, count_invalid, suggest_type,
)
from ..toggle_switch import ToggleSwitch
from .common import make_group

NONE_LABEL = "Nessuno"


def _combo():
    c = QComboBox()
    c.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    c.setMinimumContentsLength(8)
    c.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
    return c


def _field(caption, widget, scale):
    box = QVBoxLayout()
    box.setSpacing(round(2 * scale))
    box.addWidget(QLabel(caption, objectName="FormCaption"))
    box.addWidget(widget)
    return box


class DetailPreview(QFrame):
    """Popup in miniatura, ricostruito a ogni modifica."""

    def __init__(self, scale, width, height, parent=None):
        super().__init__(parent)
        self.setObjectName("PreviewCard")
        self.s, self._w, self._h = scale, width, height
        self.setFixedSize(width, height)
        self._lay = QVBoxLayout(self)
        m = round(10 * scale)
        self._lay.setContentsMargins(m, m, m, m)
        self._content = None

    def show_spec(self, spec: DetailSpec, values: dict):
        if self._content is not None:
            self._lay.removeWidget(self._content)
            self._content.setParent(None)
            self._content.deleteLater()
            self._content = None
        while self._lay.count():
            self._lay.takeAt(0)
        if not spec.enabled:
            w = QLabel("Dettagli disattivati", objectName="Muted", alignment=Qt.AlignCenter)
        else:
            k = 0.55 * self.s
            inner_w = self._w - 2 * round(10 * self.s) - 4
            box_h = int(self._h * 0.34)
            w = DetailContent(k, inner_w, int(inner_w * 0.62), box_h, spec,
                              values.get(spec.code_col, ""), values.get(spec.above_col, ""),
                              values.get(spec.hl_col, ""), self.devicePixelRatioF())
        self._content = w
        self._lay.addStretch(1)
        self._lay.addWidget(w, 0, Qt.AlignHCenter)
        self._lay.addStretch(1)


class StepDetails(QWidget):
    changed = Signal()

    def __init__(self, scale, preview_w, preview_h, parent=None):
        super().__init__(parent)
        self.setObjectName("TabPage")
        self.s = scale
        self._names = []
        self._rows = []
        self._loading = False
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(round(14 * scale))

        # ---- form (a sinistra, con scorrimento di sicurezza)
        scroll = QScrollArea(objectName="WizardScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        holder = QWidget(objectName="TabPage")
        form = QVBoxLayout(holder)
        form.setContentsMargins(0, 0, round(6 * scale), 0)
        form.setSpacing(round(8 * scale))
        scroll.setWidget(holder)
        root.addWidget(scroll, 3)

        row = QHBoxLayout()
        row.setSpacing(round(12 * scale))
        self.toggle = ToggleSwitch(scale, False)
        row.addWidget(self.toggle)
        row.addWidget(QLabel("Mostra dettagli con codice a barre", objectName="SettingTitle"), 1)
        form.addLayout(row)

        # codice
        g1, l1 = make_group(scale, "Codice a barre")
        r1 = QHBoxLayout()
        r1.setSpacing(round(10 * scale))
        self.code_col = _combo()
        self.btype = _combo()
        for tid, label, _short in BARCODE_TYPES:
            self.btype.addItem(label, tid)
        r1.addLayout(_field("Colonna codice", self.code_col, scale), 1)
        r1.addLayout(_field("Tipo codice a barre", self.btype, scale), 1)
        l1.addLayout(r1)
        self.warn = QLabel("", objectName="WizardWarn")
        self.warn.setWordWrap(True)
        l1.addWidget(self.warn)
        self.g1 = g1
        form.addWidget(g1)

        # testo sopra
        g2, l2 = make_group(scale, "Testo sopra il codice")
        r2 = QHBoxLayout()
        r2.setSpacing(round(10 * scale))
        self.above_col = _combo()
        self.above_size = _combo()
        for sid, label, _px in ABOVE_SIZES:
            self.above_size.addItem(label, sid)
        r2.addLayout(_field("Colonna", self.above_col, scale), 2)
        r2.addLayout(_field("Dimensione", self.above_size, scale), 1)
        l2.addLayout(r2)
        self.g2 = g2
        form.addWidget(g2)

        # testo evidenziato
        g3, l3 = make_group(scale, "Testo evidenziato")
        r3 = QHBoxLayout()
        r3.setSpacing(round(10 * scale))
        self.hl_col = _combo()
        self.hl_size = _combo()
        self.hl_color = _combo()
        for sid, label, _px in HL_SIZES:
            self.hl_size.addItem(label, sid)
        for cid, label in HL_COLORS:
            self.hl_color.addItem(label, cid)
        r3.addLayout(_field("Colonna", self.hl_col, scale), 2)
        r3.addLayout(_field("Dimensione", self.hl_size, scale), 2)
        r3.addLayout(_field("Colore", self.hl_color, scale), 2)
        l3.addLayout(r3)
        self.g3 = g3
        form.addWidget(g3)
        form.addStretch(1)

        # ---- anteprima (a destra)
        right = QVBoxLayout()
        right.setSpacing(round(4 * scale))
        right.addWidget(QLabel("Anteprima", objectName="PreviewTitle"))
        self.preview = DetailPreview(scale, preview_w, preview_h)
        right.addWidget(self.preview)
        right.addStretch(1)
        root.addLayout(right, 2)

        self.toggle.toggled.connect(self._on_toggle)
        self.code_col.activated.connect(self._on_code_col_user)
        for c in (self.btype, self.above_col, self.above_size, self.hl_col, self.hl_size, self.hl_color):
            c.currentIndexChanged.connect(self._on_any)
        self._set_enabled_ui(False)

    # ------------------------------------------------------------ dati
    def set_columns(self, names: list, rows: list):
        self._names, self._rows = list(names), rows
        self._loading = True
        self.code_col.clear()
        for n in names:
            self.code_col.addItem(n, n)
        for combo in (self.above_col, self.hl_col):
            combo.clear()
            combo.addItem(NONE_LABEL, None)
            for n in names:
                combo.addItem(n, n)
        self._loading = False

    def set_spec(self, spec: DetailSpec):
        self._loading = True
        self.toggle.setChecked(spec.enabled)
        self._select(self.code_col, spec.code_col, 0)
        self._select(self.btype, spec.barcode_type, 0)
        self._select(self.above_col, spec.above_col, 0)
        self._select(self.above_size, spec.above_size, 1)
        self._select(self.hl_col, spec.hl_col, 0)
        self._select(self.hl_size, spec.hl_size, 1)
        self._select(self.hl_color, spec.hl_color, 0)
        self._loading = False
        self._set_enabled_ui(spec.enabled)
        self._refresh()

    @staticmethod
    def _select(combo: QComboBox, data, fallback: int):
        i = combo.findData(data)
        combo.setCurrentIndex(i if i >= 0 else min(fallback, combo.count() - 1))

    def get_spec(self) -> DetailSpec:
        code = self.code_col.currentData()
        return DetailSpec(
            enabled=self.toggle.isChecked() and code is not None,
            code_col=code,
            barcode_type=self.btype.currentData() or "code128",
            above_col=self.above_col.currentData(),
            above_size=self.above_size.currentData() or "medio",
            hl_col=self.hl_col.currentData(),
            hl_size=self.hl_size.currentData() or "grande",
            hl_color=self.hl_color.currentData() or "verde",
        )

    def is_complete(self) -> bool:
        return (not self.toggle.isChecked()) or self.code_col.currentData() is not None

    # ------------------------------------------------------------ logica
    def _column_values(self, name: Optional[str]) -> list:
        if name not in self._names:
            return []
        i = self._names.index(name)
        return [r[i] for r in self._rows if i < len(r)]

    def _set_enabled_ui(self, on: bool):
        for g in (self.g1, self.g2, self.g3):
            g.setEnabled(on)

    def _on_toggle(self, on: bool):
        self._set_enabled_ui(on)
        if on and not self._loading:
            self._suggest_for_current_column()
        self._refresh()

    def _on_code_col_user(self, _i):
        self._suggest_for_current_column()
        self._refresh()

    def _suggest_for_current_column(self):
        """Dopo la scelta della colonna analizza ~200 valori e propone il tipo di codice."""
        sug = suggest_type(self._column_values(self.code_col.currentData()))
        self._loading = True
        self._select(self.btype, sug, 0)
        self._loading = False

    def _on_any(self, _i=None):
        if not self._loading:
            self._refresh()

    def _refresh(self):
        spec = self.get_spec()
        self.warn.setText("")
        if self.toggle.isChecked() and spec.code_col:
            bad, total = count_invalid(spec.barcode_type, self._column_values(spec.code_col))
            if bad:
                self.warn.setText(f"{bad} valori su {total} non sono validi per {TYPE_SHORT[spec.barcode_type]}")
        values = {}
        first = next((r for r in self._rows if any(r)), None)
        if first is not None:
            values = {n: (first[i] if i < len(first) else "") for i, n in enumerate(self._names)}
        self.preview.show_spec(spec, values)
        self.changed.emit()
