"""Scheda «Sicurezza»: dati dell'account e azioni (password, PIN, codice di recupero)."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from .. import auth


class SecurityTab(QWidget):
    def __init__(self, scale: float, on_action, parent=None):
        """on_action(kind): kind in 'password' | 'pin' | 'recovery'."""
        super().__init__(parent)
        self.setObjectName("TabPage")
        s = scale
        store = auth.get_store()
        lay = QVBoxLayout(self)
        m = round(22 * s)
        lay.setContentsMargins(m, m, m, m)
        lay.setSpacing(round(12 * s))

        created = store.created_at
        rows = [("Nome dispositivo", store.device_name),
                ("Nome utente", store.username),
                ("Account creato il", created.strftime("%d/%m/%Y %H:%M") if created else "-")]
        grid = QGridLayout()
        grid.setHorizontalSpacing(round(18 * s))
        grid.setVerticalSpacing(round(8 * s))
        for i, (k, v) in enumerate(rows):
            grid.addWidget(QLabel(k, objectName="InfoKey"), i, 0, Qt.AlignTop)
            grid.addWidget(QLabel(v, objectName="InfoValue"), i, 1)
        grid.setColumnStretch(1, 1)
        lay.addLayout(grid)
        lay.addStretch(1)

        self.buttons = {}
        for kind, text in (("password", "Cambia password"), ("pin", "Cambia PIN"),
                           ("recovery", "Genera nuovo codice di recupero")):
            b = QPushButton(text, objectName="SecondaryButton" if kind != "recovery" else "AccentButton")
            b.setMinimumHeight(max(44, round(48 * s)))
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, k=kind: on_action(k))
            lay.addWidget(b)
            self.buttons[kind] = b
