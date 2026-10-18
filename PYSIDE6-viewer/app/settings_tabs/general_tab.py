"""Scheda «Generale»: tema e apertura dell'ultimo file."""
from PySide6.QtWidgets import QApplication, QButtonGroup, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from .. import theme
from ..toggle_switch import ToggleSwitch


class GeneralTab(QWidget):
    def __init__(self, settings, scale: float, parent=None):
        super().__init__(parent)
        self.setObjectName("TabPage")
        self._settings = settings
        s = scale
        lay = QVBoxLayout(self)
        m = round(22 * s)
        lay.setContentsMargins(m, m, m, m)
        lay.setSpacing(round(18 * s))

        # --- Tema: interruttore segmentato Scura / Chiara
        row = QHBoxLayout()
        row.addWidget(QLabel("Tema", objectName="SettingTitle"))
        row.addStretch(1)
        seg = QFrame(objectName="Segmented")
        seg_lay = QHBoxLayout(seg)
        p = round(4 * s)
        seg_lay.setContentsMargins(p, p, p, p)
        seg_lay.setSpacing(p)
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._buttons = {}
        for name, label in (("dark", "Scura"), ("light", "Chiara")):
            b = QPushButton(label, objectName="SegButton")
            b.setCheckable(True)
            b.setMinimumHeight(round(40 * s))
            b.setCursor(b.cursor())
            self._group.addButton(b)
            seg_lay.addWidget(b)
            self._buttons[name] = b
            b.clicked.connect(lambda _=False, n=name: self._set_theme(n))
        self._buttons[theme.current()].setChecked(True)
        row.addWidget(seg)
        lay.addLayout(row)

        line = QFrame(objectName="RowDivider")
        line.setFixedHeight(max(1, round(s)))
        lay.addWidget(line)

        # --- Ricorda ultimo file aperto
        row2 = QHBoxLayout()
        txt = QVBoxLayout()
        txt.setSpacing(round(4 * s))
        txt.addWidget(QLabel("Ricorda ultimo file aperto", objectName="SettingTitle"))
        desc = QLabel("All'avvio apre automaticamente l'ultimo file importato", objectName="SettingDesc")
        desc.setWordWrap(True)
        txt.addWidget(desc)
        row2.addLayout(txt, 1)
        self.toggle = ToggleSwitch(s, settings.remember_last_file())
        self.toggle.toggled.connect(settings.set_remember_last_file)
        row2.addWidget(self.toggle)
        lay.addLayout(row2)
        lay.addStretch(1)

    def _set_theme(self, name: str):
        if name == theme.current():
            return
        self._settings.set_theme(name)
        theme.apply_theme(QApplication.instance(), name)
