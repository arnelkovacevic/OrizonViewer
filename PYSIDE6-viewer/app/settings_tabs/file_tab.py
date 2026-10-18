"""Scheda «File»: configurazione del file corrente."""
import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import QGridLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from .. import readers
from ..details import TYPE_SHORT


class FileTab(QWidget):
    def __init__(self, scale: float, info: dict, on_edit, on_clear, parent=None):
        """info: {'path','sheet','columns','details','type'} oppure {} se nessun file."""
        super().__init__(parent)
        self.setObjectName("TabPage")
        s = scale
        lay = QVBoxLayout(self)
        m = round(22 * s)
        lay.setContentsMargins(m, m, m, m)
        lay.setSpacing(round(14 * s))

        grid = QGridLayout()
        grid.setHorizontalSpacing(round(18 * s))
        grid.setVerticalSpacing(round(10 * s))
        if info:
            details_on = info.get("details")
            rows = [
                ("File", os.path.basename(info["path"]), info["path"]),
                ("Formato", readers.format_label(info["path"]), ""),
                ("Foglio", info["sheet"], ""),
                ("Colonne visualizzate", str(info["columns"]), ""),
                ("Dettagli", "Attivi" if details_on else "Non attivi", ""),
            ]
            if info.get("fmt") == "text":
                rows = [r for r in rows if r[0] != "Foglio"]
                opts = info.get("text_opts") or {}
                rows.insert(2, ("Separatore", readers.delimiter_label(opts.get("delimiter", ";")), ""))
                rows.insert(3, ("Codifica", opts.get("encoding", ""), ""))
            if details_on:
                rows.append(("Codice a barre", TYPE_SHORT.get(info.get("type"), "-"), ""))
        else:
            rows = [("File", "Nessun file caricato", "")]
        for i, (k, v, tip) in enumerate(rows):
            key = QLabel(k, objectName="InfoKey")
            val = QLabel(v, objectName="InfoValue")
            val.setToolTip(tip)
            val.setWordWrap(True)
            grid.addWidget(key, i, 0, Qt.AlignTop)
            grid.addWidget(val, i, 1)
        grid.setColumnStretch(1, 1)
        lay.addLayout(grid)
        lay.addStretch(1)

        self.edit_btn = QPushButton("Modifica configurazione", objectName="AccentButton")
        self.clear_btn = QPushButton("Elimina configurazioni salvate", objectName="DangerButton")
        for b in (self.edit_btn, self.clear_btn):
            b.setMinimumHeight(max(44, round(50 * s)))
            b.setCursor(Qt.PointingHandCursor)
            lay.addWidget(b)
        self.edit_btn.setEnabled(bool(info))
        self.edit_btn.clicked.connect(on_edit)
        self.clear_btn.clicked.connect(on_clear)
