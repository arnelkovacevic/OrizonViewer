"""Widget comuni per account/accesso: campo password con «Mostra», gruppo campo+errore,
codice di recupero e form modale per le azioni in Impostazioni → Sicurezza."""
import datetime
import os

from PySide6.QtCore import QRegularExpression, Qt
from PySide6.QtGui import QFontMetrics, QRegularExpressionValidator
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton, QSizePolicy, QVBoxLayout,
    QWidget,
)

from . import auth
from .modal_overlay import BaseModal, app_scale
from .toast import show_toast


class PasswordField(QWidget):
    """QLineEdit mascherato + pulsante Mostra/Nascondi. `digits=True` per i PIN (solo cifre, max 6)."""

    def __init__(self, placeholder="", digits=False, parent=None):
        super().__init__(parent)
        self.setObjectName("TabPage")
        s = app_scale()
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(round(8 * s))
        self.edit = QLineEdit()
        self.edit.setEchoMode(QLineEdit.Password)
        self.edit.setPlaceholderText(placeholder)
        if digits:
            self.edit.setMaxLength(6)
            self.edit.setValidator(QRegularExpressionValidator(QRegularExpression(r"\d{0,6}")))
        lay.addWidget(self.edit, 1)
        self.toggle = QPushButton("Mostra", objectName="SecondaryButton")
        self.toggle.setCheckable(True)
        self.toggle.setFocusPolicy(Qt.NoFocus)
        self.toggle.setCursor(Qt.PointingHandCursor)
        self.toggle.setFixedWidth(round(144 * s))  # abbastanza per «Nascondi»
        self.toggle.setMinimumHeight(max(44, round(46 * s)))
        self.toggle.toggled.connect(self._toggled)
        lay.addWidget(self.toggle)
        self.textChanged = self.edit.textChanged
        self.returnPressed = self.edit.returnPressed

    def _toggled(self, on: bool):
        self.edit.setEchoMode(QLineEdit.Normal if on else QLineEdit.Password)
        self.toggle.setText("Nascondi" if on else "Mostra")

    def text(self) -> str:
        return self.edit.text()

    def clear(self):
        self.edit.clear()

    def setFocus(self):
        self.edit.setFocus()

    def setEnabled(self, on: bool):
        super().setEnabled(on)


class FieldGroup(QWidget):
    """Didascalia + campo + riga d'errore (rossa) sotto il campo."""

    def __init__(self, caption: str, field: QWidget, parent=None):
        super().__init__(parent)
        self.setObjectName("TabPage")
        s = app_scale()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(round(2 * s))
        lay.addWidget(QLabel(caption, objectName="FormCaption"))
        lay.addWidget(field)
        self.error = QLabel("", objectName="FieldError")
        self.error.setFixedHeight(self.error.fontMetrics().lineSpacing() + 2)
        lay.addWidget(self.error)
        self.field = field

    def set_error(self, text: str):
        self.error.setText(text or "")


def lock_message(seconds: int) -> str:
    return f"Troppi tentativi. Riprova tra {seconds} s"


# ------------------------------------------------------------------ codice di recupero
class RecoveryCodeDialog(BaseModal):
    """Mostra il codice UNA volta. Si chiude solo dopo la conferma esplicita."""

    def __init__(self, parent, code: str, device_name: str = ""):
        super().__init__(parent, width_px=round(640 * app_scale()))
        s = self.s
        self._code, self._device = code, device_name
        self._confirmed = False
        self.body.setSpacing(round(14 * s))
        self.body.addWidget(QLabel("Codice di recupero", objectName="DialogTitle", alignment=Qt.AlignCenter))
        self.code_label = QLabel(code, objectName="RecoveryCode", alignment=Qt.AlignCenter)
        px = max(20, round(40 * s))
        self.code_label.setStyleSheet(f"font-size: {px}px;")
        self.code_label.ensurePolished()
        f = self.code_label.font()
        f.setPixelSize(px)
        self.code_label.setFixedHeight(QFontMetrics(f).lineSpacing() + round(52 * s))  # + padding/bordo QSS
        self.code_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.body.addWidget(self.code_label)
        info = QLabel("Scrivi questo codice e conservalo in un luogo sicuro. Serve per reimpostare password e PIN. "
                      "Non verrà più mostrato.", objectName="WizardInfo", alignment=Qt.AlignCenter)
        info.setWordWrap(True)
        info.ensurePolished()
        text_w = round(640 * s) - 2 * round(30 * s) - 8
        info.setMinimumHeight(info.fontMetrics().boundingRect(0, 0, text_w, 10000, Qt.TextWordWrap, info.text()).height()
                              + round(8 * s))   # un QLabel con a-capo sottostima l'altezza: la fissiamo noi
        self.body.addWidget(info)

        self.save_btn = QPushButton("Salva su file…", objectName="SecondaryButton")
        self.save_btn.setMinimumHeight(max(44, round(48 * s)))
        self.save_btn.clicked.connect(self._save)
        self.body.addWidget(self.save_btn)

        self.check = QCheckBox("Ho salvato il codice di recupero")
        self.body.addWidget(self.check)
        self.ok_btn = QPushButton("Ho conservato il codice", objectName="AccentButton")
        self.ok_btn.setMinimumHeight(max(44, round(52 * s)))
        self.ok_btn.setEnabled(False)
        self.check.toggled.connect(self.ok_btn.setEnabled)
        self.ok_btn.clicked.connect(self._confirm)
        self.body.addWidget(self.ok_btn)
        self.finalize()

    def _save(self):
        stamp = datetime.date.today().strftime("%Y%m%d")
        default = os.path.join(os.path.expanduser("~"), f"Orizon_codice_di_recupero_{stamp}.txt")
        path, _ = QFileDialog.getSaveFileName(self, "Salva il codice di recupero", default, "Testo (*.txt)")
        if not path:
            return
        text = ("Orizon Viewer - Codice di recupero\n"
                f"Dispositivo: {self._device}\n"
                f"Generato il: {datetime.datetime.now():%d/%m/%Y %H:%M}\n\n"
                f"{self._code}\n\n"
                "Conserva questo file in un luogo sicuro: serve per reimpostare password e PIN.\n")
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
            show_toast(self, "Codice salvato su file", "success")
        except OSError:
            show_toast(self, "Impossibile salvare il file")

    def _confirm(self):
        self._confirmed = True
        self.accept()

    def reject(self):  # Esc non chiude: il codice non verrebbe piu' mostrato
        if self._confirmed:
            super().reject()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            e.ignore()
            return
        super().keyPressEvent(e)

    @staticmethod
    def show_code(parent, code: str, device_name: str = ""):
        RecoveryCodeDialog(parent, code, device_name).exec()


# ------------------------------------------------------------------ form per Impostazioni → Sicurezza
class AccountFormDialog(BaseModal):
    """Form modale generico. fields: [(chiave, didascalia, 'password'|'pin')].
    `submit(values) -> (esito Check | None, messaggio_errore | None)`: se il messaggio e' None l'azione e' riuscita."""

    def __init__(self, parent, title: str, fields: list, submit, validate=None, ok_label="Conferma", hint: str = ""):
        super().__init__(parent, width_px=round(520 * app_scale()))
        s = self.s
        self._submit, self._validate = submit, validate
        self.result_value = None
        self.body.setSpacing(round(8 * s))
        self.body.addWidget(QLabel(title, objectName="DialogTitle", alignment=Qt.AlignCenter))
        if hint:
            h = QLabel(hint, objectName="WizardHint", alignment=Qt.AlignCenter)
            h.setWordWrap(True)
            self.body.addWidget(h)
        self.groups, self.inputs = {}, {}
        for key, caption, kind in fields:
            pf = PasswordField(digits=(kind == "pin"))
            pf.textChanged.connect(self._refresh)
            pf.returnPressed.connect(self._go)
            g = FieldGroup(caption, pf)
            self.groups[key], self.inputs[key] = g, pf
            self.body.addWidget(g)
        row = QHBoxLayout()
        row.setSpacing(round(10 * s))
        cancel = QPushButton("Annulla", objectName="SecondaryButton")
        cancel.clicked.connect(self.reject)
        self.ok_btn = QPushButton(ok_label, objectName="AccentButton")
        self.ok_btn.clicked.connect(self._go)
        for b in (cancel, self.ok_btn):
            b.setMinimumHeight(max(44, round(50 * s)))
            row.addWidget(b)
        self.body.addLayout(row)
        self.ok_btn.setEnabled(False)
        self.finalize()

    def values(self) -> dict:
        return {k: w.text() for k, w in self.inputs.items()}

    def _refresh(self):
        vals = self.values()
        errors = self._validate(vals) if self._validate else {}
        for key, g in self.groups.items():
            g.set_error(errors.get(key, "") if vals[key] else "")
        self.ok_btn.setEnabled(all(vals.values()) and not any(errors.values()))

    def _go(self):
        if not self.ok_btn.isEnabled():
            return
        res, err = self._submit(self.values())
        if err is None:
            self.accept()
            return
        show_toast(self, err)
        first = next(iter(self.inputs))
        if res is not None and res.locked:
            return
        self.inputs[first].clear()
        self.inputs[first].setFocus()

    def showEvent(self, e):
        super().showEvent(e)
        next(iter(self.inputs.values())).setFocus()
