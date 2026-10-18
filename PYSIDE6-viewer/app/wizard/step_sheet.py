"""Passo 1 — Foglio (Excel/ODS) oppure «Opzioni file di testo» (csv/tsv/txt)."""
from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QFrame, QHBoxLayout, QHeaderView, QLabel, QListWidget, QListWidgetItem,
    QSizePolicy, QStackedWidget, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from .. import readers
from .common import Stepper


def _fmt(n: int) -> str:
    return f"{n:,}".replace(",", ".")


class StepSheet(QWidget):
    sheetChosen = Signal(str)
    headerRowChanged = Signal(int)
    textOptionsChanged = Signal()

    def __init__(self, scale, parent=None):
        super().__init__(parent)
        self.setObjectName("TabPage")
        self.s = scale
        self._text_mode = False
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(round(10 * scale))
        self.info = QLabel("", objectName="WizardInfo")
        self.info.setWordWrap(True)
        lay.addWidget(self.info)

        self.pages = QStackedWidget()
        # --- pagina 0: elenco fogli
        self.list = QListWidget(objectName="SheetList")
        self.list.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.list.currentItemChanged.connect(self._on_item)
        self.pages.addWidget(self.list)
        # --- pagina 1: opzioni file di testo
        text = QWidget(objectName="TabPage")
        tl = QVBoxLayout(text)
        tl.setContentsMargins(0, 0, 0, 0)
        tl.setSpacing(round(8 * scale))
        tl.addWidget(QLabel("Opzioni file di testo", objectName="GroupTitle"))
        row = QHBoxLayout()
        row.setSpacing(round(12 * scale))
        self.delim = QComboBox()
        for d, label in readers.DELIMITERS:
            self.delim.addItem(label, d)
        self.enc = QComboBox()
        for label, _codec in readers.ENCODINGS:
            self.enc.addItem(label, label)
        for caption, combo in (("Separatore", self.delim), ("Codifica", self.enc)):
            box = QVBoxLayout()
            box.setSpacing(round(2 * scale))
            box.addWidget(QLabel(caption, objectName="FormCaption"))
            combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            box.addWidget(combo)
            row.addLayout(box, 1)
        tl.addLayout(row)
        self.preview_caption = QLabel("Anteprima delle prime righe", objectName="FormCaption")
        tl.addWidget(self.preview_caption)
        self.table = QTableWidget(objectName="TextPreview")
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.NoSelection)
        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(max(24, round(28 * scale)))
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setDefaultSectionSize(round(150 * scale))
        self.table.setAlternatingRowColors(True)
        tl.addWidget(self.table, 1)
        self.pages.addWidget(text)
        self.delim.currentIndexChanged.connect(lambda _i: self._text_changed())
        self.enc.currentIndexChanged.connect(lambda _i: self._text_changed())
        lay.addWidget(self.pages, 1)

        row = QHBoxLayout()
        row.setSpacing(round(12 * scale))
        row.addWidget(QLabel("Riga intestazione", objectName="SettingTitle"))
        self.stepper = Stepper(scale, 1)
        self.stepper.changed.connect(self.headerRowChanged)
        row.addWidget(self.stepper)
        hint = QLabel("La riga che contiene i nomi delle colonne (di solito la 1)", objectName="WizardHint")
        hint.setWordWrap(True)
        row.addWidget(hint, 1)
        lay.addLayout(row)

    # ------------------------------------------------------------ Excel / ODS
    def set_file(self, file_name: str, sheets: list, selected: str = None):
        self._text_mode = False
        self.pages.setCurrentIndex(0)
        n = len(sheets)
        self.info.setText(f"File caricato: {file_name}. Contiene {n} {'foglio' if n == 1 else 'fogli'}.")
        self.list.blockSignals(True)
        self.list.clear()
        for sh in sheets:
            text = sh.name
            if sh.rows and sh.cols:
                text += (f"     {_fmt(sh.rows)} {'riga' if sh.rows == 1 else 'righe'} × "
                         f"{sh.cols} {'colonna' if sh.cols == 1 else 'colonne'}")
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, sh.name)
            item.setSizeHint(QSize(0, max(52, round(56 * self.s))))
            self.list.addItem(item)
        self.list.blockSignals(False)
        names = [sh.name for sh in sheets]
        target = selected if selected in names else (names[0] if names else None)
        if target is not None:
            self.list.setCurrentRow(names.index(target))

    def current_sheet(self):
        if self._text_mode:
            return readers.TEXT_SHEET
        item = self.list.currentItem()
        return item.data(Qt.UserRole) if item else None

    def _on_item(self, cur, _prev):
        if cur is not None:
            self.sheetChosen.emit(cur.data(Qt.UserRole))

    # ------------------------------------------------------------ testo
    def set_text_file(self, file_name: str, opts: dict):
        self._text_mode = True
        self.pages.setCurrentIndex(1)
        self.info.setText(f"File di testo caricato: {file_name}. Controlla separatore e codifica: "
                          "le colonne devono apparire ben divise.")
        self.set_text_options(opts)

    def set_text_options(self, opts: dict):
        for combo, key in ((self.delim, "delimiter"), (self.enc, "encoding")):
            combo.blockSignals(True)
            i = combo.findData(opts.get(key))
            combo.setCurrentIndex(max(0, i))
            combo.blockSignals(False)

    def text_options(self) -> dict:
        return {"delimiter": self.delim.currentData(), "encoding": self.enc.currentData()}

    def _text_changed(self):
        self.textOptionsChanged.emit()

    def show_preview_table(self, names: list, rows: list, error: str = ""):
        """Prime ~10 righe: si aggiorna a ogni modifica di separatore/codifica/riga intestazione."""
        self.table.clear()
        self.table.setColumnCount(len(names))
        self.table.setRowCount(len(rows))
        self.table.setHorizontalHeaderLabels(names)
        for r, row in enumerate(rows):
            for c, value in enumerate(row):
                self.table.setItem(r, c, QTableWidgetItem(value))
        self.preview_caption.setText(error or f"Anteprima delle prime righe · {len(names)} colonne rilevate")
