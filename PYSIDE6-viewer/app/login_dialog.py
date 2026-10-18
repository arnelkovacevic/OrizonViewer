"""Schermata di accesso a tutto schermo, prima della finestra principale."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout

from . import config
from .pin_dialog import PinDialog, app_scale
from .toast import show_toast


class LoginDialog(QDialog):
    def __init__(self):
        super().__init__(None, Qt.Window | Qt.FramelessWindowHint)
        self.setObjectName("LoginDialog")
        s = app_scale()

        root = QVBoxLayout(self)
        root.addStretch(1)
        mid = QHBoxLayout()
        mid.addStretch(1)
        card = QFrame(objectName="Card")
        card.setFixedWidth(round(520 * s))
        mid.addWidget(card)
        mid.addStretch(1)
        root.addLayout(mid)
        root.addStretch(1)

        lay = QVBoxLayout(card)
        m = round(36 * s)
        lay.setContentsMargins(m, m, m, m)
        lay.setSpacing(round(16 * s))

        pm = QPixmap(config.resource_path(config.LOGO_FILE))
        if not pm.isNull():
            dpr = self.devicePixelRatioF()
            pm = pm.scaledToHeight(round(70 * s * dpr), Qt.SmoothTransformation)
            pm.setDevicePixelRatio(dpr)
            logo = QLabel()
            logo.setPixmap(pm)
            logo.setAlignment(Qt.AlignCenter)
            lay.addWidget(logo)

        title = QLabel("ORIZON - Viewer", objectName="LoginTitle")
        title.setAlignment(Qt.AlignCenter)
        lay.addWidget(title)
        sub = QLabel("Accesso", objectName="Muted")
        sub.setAlignment(Qt.AlignCenter)
        lay.addWidget(sub)

        self.user = QLineEdit()
        self.user.setPlaceholderText("Nome utente")
        self.pwd = QLineEdit()
        self.pwd.setPlaceholderText("Password")
        self.pwd.setEchoMode(QLineEdit.Password)
        lay.addWidget(self.user)
        lay.addWidget(self.pwd)
        self.user.returnPressed.connect(self.pwd.setFocus)
        self.pwd.returnPressed.connect(self._attempt)

        login = QPushButton("Accedi", objectName="PrimaryButton")
        login.setAutoDefault(False)
        login.setMinimumHeight(round(56 * s))
        login.clicked.connect(self._attempt)
        lay.addWidget(login)

        quit_btn = QPushButton("Esci", objectName="DangerButton")
        quit_btn.setAutoDefault(False)
        quit_btn.setMinimumHeight(round(48 * s))
        quit_btn.clicked.connect(self._quit)
        lay.addWidget(quit_btn)

    def _attempt(self):
        ok_user = config.verify(self.user.text().strip(), config.USERNAME_HASH)
        ok_pwd = config.verify(self.pwd.text(), config.PASSWORD_HASH)
        if ok_user and ok_pwd:
            self.accept()
            return
        self.pwd.clear()
        self.pwd.setFocus()
        show_toast(self, "Credenziali errate")

    def _quit(self):
        if PinDialog.ask(self, "PIN per uscire"):
            super().reject()

    # Esc / Alt+F4 non chiudono la schermata di accesso
    def reject(self):
        pass

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            e.ignore()
            return
        super().keyPressEvent(e)

    def showEvent(self, e):
        super().showEvent(e)
        self.user.setFocus()
