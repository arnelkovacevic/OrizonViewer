"""Dialogo di conferma (al posto di QMessageBox)."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton

from .modal_overlay import BaseModal, app_scale


class ConfirmDialog(BaseModal):
    def __init__(self, parent, title: str, text: str, ok_label: str = "Conferma", danger: bool = False):
        super().__init__(parent, width_px=round(520 * app_scale()))
        s = self.s
        self.body.setSpacing(round(18 * s))
        self.body.addWidget(QLabel(title, objectName="DialogTitle", alignment=Qt.AlignCenter))
        msg = QLabel(text, objectName="WizardInfo", alignment=Qt.AlignCenter)
        msg.setWordWrap(True)
        self.body.addWidget(msg)
        row = QHBoxLayout()
        row.setSpacing(round(12 * s))
        cancel = QPushButton("Annulla", objectName="SecondaryButton")
        cancel.clicked.connect(self.reject)
        ok = QPushButton(ok_label, objectName="DangerButton" if danger else "AccentButton")
        ok.clicked.connect(self.accept)
        for b in (cancel, ok):
            b.setMinimumHeight(max(44, round(50 * s)))
            row.addWidget(b)
        self.body.addLayout(row)
        self.finalize()

    @staticmethod
    def ask(parent, title, text, ok_label="Conferma", danger=False) -> bool:
        return ConfirmDialog(parent, title, text, ok_label, danger).exec() == QDialog.Accepted
