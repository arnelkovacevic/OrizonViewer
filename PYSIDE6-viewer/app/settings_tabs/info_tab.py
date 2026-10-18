"""Scheda «Info»: versione, sviluppatore e contatti."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from .. import config

TEXT = (
    "────── Orizon Viewer ─────\n"
    "Versione: {version}\n"
    "Piattaforma: Windows\n"
    "Linguaggio: Python\n\n"
    "Sviluppatore:\n"
    "Arnel Kovacevic\n"
    "Orizon-AIX\n\n"
    "Copyright © {year} Orizon-AIX\n"
    "──────────────────────────────────────\n\n"
    "Sito Web: orizon-aix.com\n"
    "Email: info@orizon-aix.com\n"
    "Telefono: +39 380 7525438"
)


class InfoTab(QWidget):
    def __init__(self, scale: float, parent=None):
        super().__init__(parent)
        self.setObjectName("TabPage")
        lay = QVBoxLayout(self)
        lay.setSpacing(round(12 * scale))
        pm = QPixmap(config.resource_path(config.LOGO_FILE))
        if not pm.isNull():
            dpr = self.devicePixelRatioF()
            pm = pm.scaledToHeight(round(60 * scale * dpr), Qt.SmoothTransformation)
            pm.setDevicePixelRatio(dpr)
            logo = QLabel()
            logo.setPixmap(pm)
            logo.setAlignment(Qt.AlignCenter)
            lay.addWidget(logo)
        text = QLabel(TEXT.format(version=config.APP_VERSION, year=config.COPYRIGHT_YEAR), objectName="InfoText")
        text.setAlignment(Qt.AlignCenter)
        lay.addStretch(1)
        lay.addWidget(text)
        lay.addStretch(1)
