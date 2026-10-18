"""Passo 1 — Foglio."""
from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QVBoxLayout, QWidget

from .common import Stepper


def _fmt(n: int) -> str:
    return f"{n:,}".replace(",", ".")


class StepSheet(QWidget):
    sheetChosen = Signal(str)
    headerRowChanged = Signal(int)

    def __init__(self, scale, parent=None):
        super().__init__(parent)
        self.setObjectName("TabPage")
        self.s = scale
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(round(10 * scale))
        self.info = QLabel("", objectName="WizardInfo")
        self.info.setWordWrap(True)
        lay.addWidget(self.info)
        self.list = QListWidget(objectName="SheetList")
        self.list.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.list.currentItemChanged.connect(self._on_item)
        lay.addWidget(self.list, 1)

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

    def set_file(self, file_name: str, sheets: list, selected: str = None):
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
        item = self.list.currentItem()
        return item.data(Qt.UserRole) if item else None

    def _on_item(self, cur, _prev):
        if cur is not None:
            self.sheetChosen.emit(cur.data(Qt.UserRole))
