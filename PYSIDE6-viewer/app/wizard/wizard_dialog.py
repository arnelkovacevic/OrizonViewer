"""Wizard «Configurazione file»: 1 Foglio → 2 Colonne → 3 Dettagli. Dimensione fissa (calcolata una volta)."""
import os
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QStackedWidget, QVBoxLayout

from .. import xlsx_reader
from ..details import DetailSpec
from ..file_profiles import Profile
from ..modal_overlay import BaseModal
from ..toast import show_toast
from .common import StepIndicator
from .step_columns import StepColumns
from .step_details import StepDetails
from .step_sheet import StepSheet

MM16_COLUMNS = ["Codice Prodotto", "Descrizione Libera", "Note Interne", "LAYOUT"]
STEP_LABELS = ["Foglio", "Colonne", "Dettagli"]


def default_columns(names: list) -> list:
    """mm16.xlsx: le 4 colonne storiche nell'ordine storico; altrimenti tutte."""
    if all(c in names for c in MM16_COLUMNS):
        return list(MM16_COLUMNS)
    return list(names)


def default_details(names: list) -> DetailSpec:
    if all(c in names for c in MM16_COLUMNS):
        return DetailSpec(enabled=True, code_col="Codice Prodotto", barcode_type="code128",
                          above_col="Descrizione Libera", above_size="medio",
                          hl_col="LAYOUT", hl_size="grande", hl_color="verde")
    return DetailSpec()


def order_with_selection(names: list, selected: list) -> list:
    """Ordine di visualizzazione: le colonne scelte occupano le loro posizioni originali,
    ma nell'ordine del profilo; le altre restano dove sono."""
    chosen = [c for c in selected if c in names]
    slots = [i for i, n in enumerate(names) if n in chosen]
    out = list(names)
    for slot, col in zip(slots, chosen):
        out[slot] = col
    return out


class WizardDialog(BaseModal):
    def __init__(self, parent, path: str, sheets: list, prefill: Optional[Profile] = None):
        super().__init__(parent, 0.88, 0.94, min_size=(880, 540))
        s = self.s
        self.path, self.sheets, self.prefill = path, sheets, prefill
        self.profile: Optional[Profile] = None
        self.preview: Optional[xlsx_reader.Preview] = None
        self._cols_key = None
        self._details_key = None
        self.step = 0

        m = round(14 * s)
        self.body.setContentsMargins(m, m, m, m)
        self.body.setSpacing(round(8 * s))

        head = QHBoxLayout()
        head.addWidget(QLabel("Configurazione file", objectName="DialogTitle"))
        head.addStretch(1)
        self.indicator = StepIndicator(STEP_LABELS, s)
        head.addWidget(self.indicator)
        self.body.addLayout(head)

        # dimensione dell'anteprima: frazione dello spazio utile
        inner_w = max(self._target_w, self._min_w) - 2 * self.pad - 2 * m - 6
        inner_h = max(self._target_h, self._min_h) - 2 * self.pad - 2 * m - 6
        self.stack = QStackedWidget()
        self.step_sheet = StepSheet(s)
        self.step_cols = StepColumns(s)
        self.step_details = StepDetails(s, int(inner_w * 0.34), int(inner_h * 0.62))
        for w in (self.step_sheet, self.step_cols, self.step_details):
            self.stack.addWidget(w)
        self.body.addWidget(self.stack, 1)

        nav = QHBoxLayout()
        nav.setSpacing(round(10 * s))
        self.btn_cancel = QPushButton("Annulla", objectName="SecondaryButton")
        self.btn_back = QPushButton("Indietro", objectName="SecondaryButton")
        self.btn_next = QPushButton("Avanti", objectName="AccentButton")
        for b in (self.btn_cancel, self.btn_back, self.btn_next):
            b.setMinimumSize(round(150 * s), max(44, round(48 * s)))
            b.setAutoDefault(False)
        nav.addWidget(self.btn_cancel)
        nav.addStretch(1)
        nav.addWidget(self.btn_back)
        nav.addWidget(self.btn_next)
        self.body.addLayout(nav)

        self.btn_cancel.clicked.connect(self.reject)
        self.btn_back.clicked.connect(lambda: self.goto(self.step - 1))
        self.btn_next.clicked.connect(self._next)
        self.step_sheet.sheetChosen.connect(lambda _n: self._update_nav())
        self.step_sheet.headerRowChanged.connect(self._on_header_row)
        self.step_cols.headerRowChanged.connect(self._on_header_row)
        self.step_cols.selectionChanged.connect(self._update_nav)
        self.step_details.changed.connect(self._update_nav)

        self.header_row = prefill.header_row if prefill else 1
        self._sync_steppers()
        self.step_sheet.set_file(os.path.basename(path), sheets, prefill.sheet if prefill else None)
        self.finalize()
        self.goto(1 if len(sheets) == 1 else 0)  # un solo foglio: si passa subito alle colonne

    # ------------------------------------------------------------ stato
    @property
    def sheet(self) -> Optional[str]:
        return self.step_sheet.current_sheet()

    def _sync_steppers(self):
        for st in (self.step_sheet.stepper, self.step_cols.stepper):
            st.set_value(self.header_row, emit=False)

    def _on_header_row(self, value: int):
        self.header_row = value
        self._sync_steppers()
        if self.step == 1:  # le colonne dipendono dalla riga di intestazione
            self._ensure_columns()

    # ------------------------------------------------------------ navigazione
    def goto(self, step: int):
        step = max(0, min(2, step))
        if step >= 1 and not self._ensure_columns():
            step = 0
        if step == 2:
            self._ensure_details()
        self.step = step
        self.stack.setCurrentIndex(step)
        self.indicator.set_step(step)
        self._update_nav()

    def _next(self):
        if self.step < 2:
            self.goto(self.step + 1)
        else:
            self._confirm()

    def _update_nav(self):
        self.btn_back.setVisible(self.step > 0)
        self.btn_next.setText("Conferma" if self.step == 2 else "Avanti")
        if self.step == 0:
            ok = self.sheet is not None
        elif self.step == 1:
            ok = len(self.step_cols.selected_in_order()) >= 1
        else:
            ok = self.step_details.is_complete()
        self.btn_next.setEnabled(ok)

    # ------------------------------------------------------------ passi
    def _ensure_columns(self) -> bool:
        sheet = self.sheet
        if sheet is None:
            return False
        key = (sheet, self.header_row)
        if key == self._cols_key:
            return True
        try:
            self.preview = xlsx_reader.read_preview(self.path, sheet, self.header_row)
        except xlsx_reader.XlsxError as e:
            show_toast(self, f"Impossibile leggere il foglio: {str(e)[:120]}")
            return False
        names = self.preview.names
        if not names:
            show_toast(self, "Nessuna colonna trovata: controlla la riga di intestazione")
        use_prefill = (self.prefill is not None and self.prefill.sheet == sheet
                       and self.prefill.header_row == self.header_row)
        wanted = [c for c in self.prefill.columns if c in names] if use_prefill else []
        selected = wanted or default_columns(names)
        order = order_with_selection(names, selected)
        samples = [self.preview.samples[names.index(n)] for n in order]
        self.step_cols.set_columns(order, samples, set(selected))
        self._cols_key = key
        self._details_key = None
        return True

    def _ensure_details(self):
        if self._details_key == self._cols_key:
            return
        names = self.preview.names
        self.step_details.set_columns(names, self.preview.rows)
        sheet, header = self._cols_key
        if self.prefill and self.prefill.sheet == sheet and self.prefill.header_row == header:
            spec = self.prefill.details.drop_missing(names)
        else:
            spec = default_details(names)
        self.step_details.set_spec(spec)
        self._details_key = self._cols_key

    def _confirm(self):
        sheet, header = self._cols_key
        widths = {}
        if self.prefill and self.prefill.sheet == sheet:
            widths = dict(self.prefill.widths)
        self.profile = Profile(
            path=self.path, sheet=sheet, header_row=header,
            all_columns=list(self.preview.names),
            columns=self.step_cols.selected_in_order(),
            details=self.step_details.get_spec(), widths=widths,
        )
        self.accept()
