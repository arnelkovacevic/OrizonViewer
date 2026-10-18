"""Accesso a tutto schermo: registrazione iniziale, login e recupero, tutto nella stessa finestra
(una sola finestra fullscreen, nessuna transizione tra finestre)."""
import logging
import socket

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QStackedWidget, QVBoxLayout, QWidget,
)

from . import auth, config
from .auth_widgets import FieldGroup, PasswordField, RecoveryCodeDialog, lock_message
from .confirm_dialog import ConfirmDialog
from .modal_overlay import app_scale
from .pin_dialog import PinDialog
from .toast import show_toast

log = logging.getLogger("orizon.auth")


class _Page(QWidget):
    """Pagina centrata con una carta di larghezza fissa; `self.lay` e' il layout della carta."""

    def __init__(self, container, card_width: int):
        super().__init__()
        self.setObjectName("TabPage")
        self.container = container
        self.store = container.store
        self.s = app_scale()
        s = self.s
        root = QVBoxLayout(self)
        root.addStretch(1)
        mid = QHBoxLayout()
        mid.addStretch(1)
        card = QFrame(objectName="Card")
        screen_w = container.screen().geometry().width() if container.screen() else 1280
        card.setFixedWidth(min(round(card_width * s), int(screen_w * 0.94)))
        mid.addWidget(card)
        mid.addStretch(1)
        root.addLayout(mid)
        root.addStretch(1)
        self.lay = QVBoxLayout(card)
        m = round(26 * s)
        self.lay.setContentsMargins(m, round(20 * s), m, round(20 * s))
        self.lay.setSpacing(round(6 * s))

    def add_header(self, subtitle: str, logo_h: int = 56):
        s = self.s
        pm = QPixmap(config.resource_path(config.LOGO_FILE))
        if not pm.isNull():
            dpr = self.devicePixelRatioF()
            pm = pm.scaledToHeight(round(logo_h * s * dpr), Qt.SmoothTransformation)
            pm.setDevicePixelRatio(dpr)
            logo = QLabel(alignment=Qt.AlignCenter)
            logo.setPixmap(pm)
            self.lay.addWidget(logo)
        self.lay.addWidget(QLabel("ORIZON - Viewer", objectName="LoginTitle", alignment=Qt.AlignCenter))
        self.lay.addWidget(QLabel(subtitle, objectName="Muted", alignment=Qt.AlignCenter))

    def button(self, text, name="PrimaryButton", height=52):
        b = QPushButton(text, objectName=name)
        b.setAutoDefault(False)
        b.setMinimumHeight(max(44, round(height * self.s)))
        return b

    def on_show(self):
        pass


# ============================================================ registrazione
class SetupPage(_Page):
    def __init__(self, container):
        super().__init__(container, 780)
        self.add_header("Configurazione iniziale")

        self.device = QLineEdit(socket.gethostname())
        self.device.setReadOnly(True)
        self.device.setFocusPolicy(Qt.NoFocus)
        self.user = QLineEdit("admin")
        self.pwd, self.pwd2 = PasswordField("Password"), PasswordField("Conferma password")
        self.pin, self.pin2 = PasswordField("PIN (4-6 cifre)", digits=True), PasswordField("Conferma PIN", digits=True)
        self.g_dev = FieldGroup("Nome dispositivo", self.device)
        self.g_user = FieldGroup("Nome utente", self.user)
        self.g_pwd = FieldGroup("Password", self.pwd)
        self.g_pwd2 = FieldGroup("Conferma password", self.pwd2)
        self.g_pin = FieldGroup("PIN (serve per importare, modificare e uscire)", self.pin)
        self.g_pin2 = FieldGroup("Conferma PIN", self.pin2)
        grid = QGridLayout()
        grid.setHorizontalSpacing(round(14 * self.s))
        grid.setVerticalSpacing(0)
        for i, g in enumerate((self.g_dev, self.g_user, self.g_pwd, self.g_pwd2, self.g_pin, self.g_pin2)):
            grid.addWidget(g, i // 2, i % 2)
        self.lay.addLayout(grid)

        row = QHBoxLayout()
        row.setSpacing(round(12 * self.s))
        self.quit_btn = self.button("Esci", "DangerButton", 50)
        self.quit_btn.clicked.connect(self._quit)
        self.create_btn = self.button("Crea account", "AccentButton", 52)
        self.create_btn.clicked.connect(self._create)
        row.addWidget(self.quit_btn, 1)
        row.addWidget(self.create_btn, 2)
        self.lay.addLayout(row)

        for w in (self.user, self.pwd, self.pwd2, self.pin, self.pin2):
            w.textChanged.connect(self._validate)
        self.pin2.returnPressed.connect(self._create)
        self._validate()

    def _errors(self) -> dict:
        e = {}
        e["user"] = auth.validate_username(self.user.text())
        e["pwd"] = auth.validate_password(self.pwd.text())
        e["pwd2"] = None if self.pwd2.text() == self.pwd.text() else "Le password non coincidono"
        e["pin"] = auth.validate_pin(self.pin.text())
        e["pin2"] = None if self.pin2.text() == self.pin.text() else "I PIN non coincidono"
        return e

    def _validate(self):
        e = self._errors()
        shown = {"user": bool(self.user.text()), "pwd": bool(self.pwd.text()), "pwd2": bool(self.pwd2.text()),
                 "pin": bool(self.pin.text()), "pin2": bool(self.pin2.text())}
        for key, group in (("user", self.g_user), ("pwd", self.g_pwd), ("pwd2", self.g_pwd2),
                           ("pin", self.g_pin), ("pin2", self.g_pin2)):
            group.set_error(e[key] if shown[key] else "")
        complete = all(shown.values()) and not any(e.values())
        self.create_btn.setEnabled(complete)

    def _create(self):
        if not self.create_btn.isEnabled():
            return
        try:
            code = self.store.create(self.user.text(), self.pwd.text(), self.pin.text(), self.device.text())
        except Exception as e:  # noqa: BLE001
            log.error("creazione account fallita: %s", type(e).__name__)
            show_toast(self, "Impossibile creare l'account")
            return
        RecoveryCodeDialog.show_code(self.container, code, self.store.device_name)
        self.container.finish()

    def _quit(self):
        if ConfirmDialog.ask(self.container, "Uscire?", "L'account non è stato ancora creato. Vuoi uscire "
                             "dall'applicazione?", "Esci", danger=True):
            self.container.quit_app()

    def on_show(self):
        self.user.setFocus()


# ============================================================ login
class LoginPage(_Page):
    def __init__(self, container):
        super().__init__(container, 520)
        self.add_header("Accesso")
        self.lay.addWidget(QLabel("", objectName="Muted", alignment=Qt.AlignCenter))
        self.device_label = self.lay.itemAt(self.lay.count() - 1).widget()
        self.lay.addSpacing(round(6 * self.s))

        self.user = QLineEdit()
        self.user.setPlaceholderText("Nome utente")
        self.pwd = PasswordField("Password")
        self.lay.addWidget(self.user)
        self.lay.addSpacing(round(6 * self.s))
        self.lay.addWidget(self.pwd)
        self.lock_label = QLabel("", objectName="LockNotice", alignment=Qt.AlignCenter)
        self.lock_label.setFixedHeight(self.lock_label.fontMetrics().lineSpacing() + round(6 * self.s))
        self.lay.addWidget(self.lock_label)
        self.user.returnPressed.connect(self.pwd.setFocus)
        self.pwd.returnPressed.connect(self._attempt)

        self.login_btn = self.button("Accedi", "PrimaryButton", 56)
        self.login_btn.clicked.connect(self._attempt)
        self.lay.addWidget(self.login_btn)
        self.forgot = QPushButton("Password dimenticata?", objectName="LinkButton")
        self.forgot.setCursor(Qt.PointingHandCursor)
        self.forgot.setFocusPolicy(Qt.NoFocus)
        self.forgot.clicked.connect(lambda: self.container.go("recovery"))
        self.lay.addWidget(self.forgot, 0, Qt.AlignHCenter)
        quit_btn = self.button("Esci", "DangerButton", 48)
        quit_btn.clicked.connect(self._quit)
        self.lay.addWidget(quit_btn)

        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self.refresh_lock)

    def refresh_lock(self):
        left = self.store.lock_remaining()
        locked = left > 0
        self.lock_label.setText(lock_message(left) if locked else "")
        for w in (self.user, self.pwd, self.login_btn):
            w.setEnabled(not locked)
        if locked and not self._timer.isActive():
            self._timer.start()
        if not locked:
            self._timer.stop()

    def _attempt(self):
        if self.store.lock_remaining():
            self.refresh_lock()
            return
        res = self.store.check_login(self.user.text(), self.pwd.text())
        if res.ok:
            self.container.finish()
            return
        self.pwd.clear()
        if res.locked:
            self.refresh_lock()
            show_toast(self, lock_message(res.remaining))
        else:
            self.pwd.setFocus()
            show_toast(self, "Credenziali errate")

    def _quit(self):
        if PinDialog.ask(self.container, "PIN per uscire"):
            self.container.quit_app()

    def on_show(self):
        self.device_label.setText(f"Dispositivo: {self.store.device_name}")
        self.pwd.clear()
        self.refresh_lock()
        self.user.setFocus()


# ============================================================ recupero
class RecoveryPage(_Page):
    def __init__(self, container):
        super().__init__(container, 780)
        self.add_header("Recupero accesso")
        self.code = QLineEdit()
        self.code.setPlaceholderText("XXXX-XXXX-XXXX")
        self.pwd, self.pwd2 = PasswordField("Nuova password"), PasswordField("Conferma nuova password")
        self.pin, self.pin2 = PasswordField("Nuovo PIN (4-6 cifre)", digits=True), PasswordField("Conferma nuovo PIN", digits=True)
        self.g_code = FieldGroup("Codice di recupero", self.code)
        self.g_pwd = FieldGroup("Nuova password", self.pwd)
        self.g_pwd2 = FieldGroup("Conferma password", self.pwd2)
        self.g_pin = FieldGroup("Nuovo PIN", self.pin)
        self.g_pin2 = FieldGroup("Conferma PIN", self.pin2)
        self.lock_label = QLabel("", objectName="LockNotice", alignment=Qt.AlignCenter)
        self.lock_label.setFixedHeight(self.lock_label.fontMetrics().lineSpacing() + round(4 * self.s))
        grid = QGridLayout()
        grid.setHorizontalSpacing(round(14 * self.s))
        grid.setVerticalSpacing(0)
        grid.addWidget(self.g_code, 0, 0, 1, 2)
        for i, g in enumerate((self.g_pwd, self.g_pwd2, self.g_pin, self.g_pin2)):
            grid.addWidget(g, 1 + i // 2, i % 2)
        self.lay.addLayout(grid)
        self.lay.addWidget(self.lock_label)

        row = QHBoxLayout()
        row.setSpacing(round(12 * self.s))
        back = self.button("Annulla", "SecondaryButton", 50)
        back.clicked.connect(lambda: self.container.go("login"))
        self.reset_btn = self.button("Reimposta accesso", "AccentButton", 52)
        self.reset_btn.clicked.connect(self._submit)
        row.addWidget(back, 1)
        row.addWidget(self.reset_btn, 2)
        self.lay.addLayout(row)
        note = QLabel("Codice smarrito? L'amministratore del computer può reimpostare l'account da Windows con "
                      "'Ripristina_account.bat' nella cartella del programma.", objectName="Footnote",
                      alignment=Qt.AlignCenter)
        note.setWordWrap(True)
        self.lay.addWidget(note)

        self.code.textChanged.connect(lambda t: self._upper(t))
        for w in (self.code, self.pwd, self.pwd2, self.pin, self.pin2):
            w.textChanged.connect(self._validate)
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self.refresh_lock)
        self._validate()

    def _upper(self, text):
        if text != text.upper():
            pos = self.code.cursorPosition()
            self.code.setText(text.upper())
            self.code.setCursorPosition(pos)

    def _validate(self):
        norm = auth.normalize_code(self.code.text())
        e_pwd, e_pin = auth.validate_password(self.pwd.text()), auth.validate_pin(self.pin.text())
        e_pwd2 = None if self.pwd2.text() == self.pwd.text() else "Le password non coincidono"
        e_pin2 = None if self.pin2.text() == self.pin.text() else "I PIN non coincidono"
        self.g_pwd.set_error(e_pwd if self.pwd.text() else "")
        self.g_pwd2.set_error(e_pwd2 if self.pwd2.text() else "")
        self.g_pin.set_error(e_pin if self.pin.text() else "")
        self.g_pin2.set_error(e_pin2 if self.pin2.text() else "")
        ok = (len(norm) == auth.CODE_LENGTH and self.pwd.text() and self.pwd2.text() and self.pin.text()
              and self.pin2.text() and not (e_pwd or e_pwd2 or e_pin or e_pin2))
        self.reset_btn.setEnabled(bool(ok) and self.store.lock_remaining() == 0)

    def refresh_lock(self):
        left = self.store.lock_remaining()
        self.lock_label.setText(lock_message(left) if left else "")
        if left and not self._timer.isActive():
            self._timer.start()
        if not left:
            self._timer.stop()
        self._validate()

    def _submit(self):
        if not self.reset_btn.isEnabled():
            return
        res, new_code = self.store.recover(self.code.text(), self.pwd.text(), self.pin.text())
        if res.ok:
            RecoveryCodeDialog.show_code(self.container, new_code, self.store.device_name)
            self.container.go("login")
            show_toast(self.container, "Accesso ripristinato: ora puoi accedere", "success", 3500)
            return
        self.code.clear()
        if res.locked:
            self.refresh_lock()
            show_toast(self, lock_message(res.remaining))
        else:
            show_toast(self, "Codice di recupero errato")

    def on_show(self):
        for w in (self.code, self.pwd, self.pwd2, self.pin, self.pin2):
            w.clear()
        self.refresh_lock()
        self.code.setFocus()


# ============================================================ contenitore
class LoginDialog(QDialog):
    """Finestra fullscreen unica: registrazione (primo avvio), login, recupero."""

    def __init__(self, store=None):
        super().__init__(None, Qt.Window | Qt.FramelessWindowHint)
        self.setObjectName("LoginDialog")
        self.store = store or auth.get_store()
        self._quit = False
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.stack = QStackedWidget()
        lay.addWidget(self.stack)
        self.pages = {"setup": SetupPage(self), "login": LoginPage(self), "recovery": RecoveryPage(self)}
        for p in self.pages.values():
            self.stack.addWidget(p)
        self.go("login" if self.store.exists() else "setup")

    def go(self, name: str):
        page = self.pages[name]
        self.stack.setCurrentWidget(page)
        page.on_show()

    def current(self) -> str:
        return next(k for k, p in self.pages.items() if p is self.stack.currentWidget())

    def finish(self):
        self.accept()

    def quit_app(self):
        self._quit = True
        QDialog.reject(self)

    @property
    def quit_requested(self) -> bool:
        return self._quit

    def show_fullscreen(self):
        """Fullscreen con dimensione esplicita (vedi MainWindow.enter_fullscreen)."""
        self.setGeometry(self.screen().geometry())
        self.showFullScreen()
        self.raise_()
        self.activateWindow()

    # Esc / Alt+F4 non chiudono la schermata di accesso
    def reject(self):
        pass

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            e.ignore()
            return
        super().keyPressEvent(e)
