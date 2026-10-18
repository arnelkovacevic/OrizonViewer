"""Dialogo per gli errori imprevisti (al posto di QMessageBox)."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QPushButton

from .modal_overlay import BaseModal, app_scale


class ErrorDialog(BaseModal):
    def __init__(self, parent, log_path: str):
        super().__init__(parent, width_px=round(640 * app_scale()))
        s = self.s
        self.body.setSpacing(round(14 * s))
        self.body.addWidget(QLabel("Si è verificato un errore imprevisto", objectName="DialogTitle",
                                   alignment=Qt.AlignCenter))
        text_w = round(640 * s) - 2 * round(30 * s) - 8
        info = QLabel("I dettagli tecnici sono stati salvati nel file di log:", objectName="WizardInfo",
                      alignment=Qt.AlignCenter)
        info.setWordWrap(True)
        info.ensurePolished()
        info.setMinimumHeight(info.fontMetrics().boundingRect(0, 0, text_w, 10000, Qt.TextWordWrap,
                                                              info.text()).height() + round(6 * s))
        self.body.addWidget(info)
        self.path_label = QLabel(log_path, objectName="LogPath", alignment=Qt.AlignCenter)
        self.path_label.setWordWrap(True)
        self.path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.path_label.ensurePolished()
        self.path_label.setMinimumHeight(self.path_label.fontMetrics().boundingRect(
            0, 0, text_w - round(24 * s), 10000, Qt.TextWordWrap, log_path).height() + round(26 * s))
        self.body.addWidget(self.path_label)
        btn = QPushButton("Chiudi", objectName="AccentButton")
        btn.setMinimumHeight(max(44, round(50 * s)))
        btn.clicked.connect(self.accept)
        btn.setDefault(True)
        self.body.addWidget(btn)
        self.finalize()
