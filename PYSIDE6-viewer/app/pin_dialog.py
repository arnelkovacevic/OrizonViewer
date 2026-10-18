"""Dialogo PIN modale con tastierino touch."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton

from . import config
from .modal_overlay import BaseModal, app_scale, center_on  # noqa: F401  (ri-esportati)
from .toast import show_toast


class PinDialog(BaseModal):
    def __init__(self, parent=None, prompt="Inserire il PIN"):
        super().__init__(parent, width_px=round(420 * app_scale()))
        s = self.s

        self.body.setSpacing(round(14 * s))
        title = QLabel(prompt, objectName="DialogTitle")
        title.setAlignment(Qt.AlignCenter)
        self.body.addWidget(title)

        self.edit = QLineEdit()
        self.edit.setEchoMode(QLineEdit.Password)
        self.edit.setAlignment(Qt.AlignCenter)
        self.edit.setPlaceholderText("PIN")
        self.edit.returnPressed.connect(self._confirm)
        self.body.addWidget(self.edit)

        grid = QGridLayout()
        grid.setSpacing(round(10 * s))
        keys = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "C", "0", "⌫"]
        for i, k in enumerate(keys):
            b = QPushButton(k, objectName="KeyButton")
            b.setFocusPolicy(Qt.NoFocus)
            b.setMinimumHeight(round(56 * s))
            b.clicked.connect(lambda _=False, key=k: self._key(key))
            grid.addWidget(b, i // 3, i % 3)
        self.body.addLayout(grid)

        row = QHBoxLayout()
        row.setSpacing(round(10 * s))
        cancel = QPushButton("Annulla", objectName="SecondaryButton")
        cancel.setAutoDefault(False)
        cancel.clicked.connect(self.reject)
        ok = QPushButton("Conferma", objectName="PrimaryButton")
        ok.setAutoDefault(False)
        ok.clicked.connect(self._confirm)
        for b in (cancel, ok):
            b.setMinimumHeight(round(52 * s))
            row.addWidget(b)
        self.body.addLayout(row)
        self.finalize()

    def _key(self, key):
        if key == "C":
            self.edit.clear()
        elif key == "⌫":
            self.edit.backspace()
        else:
            self.edit.insert(key)

    def _confirm(self):
        if config.verify(self.edit.text(), config.PIN_HASH):
            self.accept()
        else:
            self.edit.clear()
            show_toast(self, "PIN errato")

    def showEvent(self, e):
        super().showEvent(e)
        self.edit.setFocus()

    @staticmethod
    def ask(parent, prompt="Inserire il PIN") -> bool:
        return PinDialog(parent, prompt).exec() == QDialog.Accepted
