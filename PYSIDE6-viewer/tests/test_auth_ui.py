"""Schermate di accesso: registrazione, login con blocco, recupero, PIN e azioni di Sicurezza."""
import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QDialog

from app import auth
from app.auth import AccountStore
from app.auth_widgets import AccountFormDialog, RecoveryCodeDialog
from app.login_dialog import LoginDialog
from app.pin_dialog import PinDialog
from gui_helpers import pump, run_modal

PWD, PIN = "segreta-123", "4821"


class Clock:
    t = 2_000_000.0

    def __call__(self):
        return self.t


@pytest.fixture()
def clock():
    return Clock()


@pytest.fixture()
def shown_codes(monkeypatch):
    codes = []
    monkeypatch.setattr(RecoveryCodeDialog, "show_code", staticmethod(lambda parent, code, dev="": codes.append(code)))
    return codes


@pytest.fixture()
def empty_store(qapp, tmp_path, clock):
    s = AccountStore(str(tmp_path / "account.json"), clock=clock)
    auth.set_store(s)
    yield s
    auth.set_store(None)


@pytest.fixture()
def store(empty_store):
    empty_store.create("admin", PWD, PIN, "PC-TEST")
    return empty_store


def test_first_run_shows_setup_and_validates(empty_store, shown_codes):
    d = LoginDialog(empty_store)
    d.show()
    page = d.pages["setup"]
    assert d.current() == "setup" and page.device.isReadOnly() and page.device.text()
    assert page.user.text() == "admin" and not page.create_btn.isEnabled()
    page.pwd.edit.setText("123")
    assert page.g_pwd.error.text() == "Almeno 6 caratteri"
    page.pwd.edit.setText("segreta-123")
    page.pwd2.edit.setText("diversa")
    assert page.g_pwd2.error.text() == "Le password non coincidono" and not page.create_btn.isEnabled()
    page.pwd2.edit.setText("segreta-123")
    page.pin.edit.setText("12")
    assert page.g_pin.error.text() == "Da 4 a 6 cifre"
    page.pin.edit.setText("48211234")                      # max 6 cifre: il campo non accetta oltre
    assert len(page.pin.text()) <= 6
    page.pin.edit.setText("4821")
    page.pin2.edit.setText("4822")
    assert page.g_pin2.error.text() == "I PIN non coincidono" and not page.create_btn.isEnabled()
    page.pin2.edit.setText("4821")
    page.user.setText("a b")
    assert "3 a 20" in page.g_user.error.text() and not page.create_btn.isEnabled()
    page.user.setText("capo.officina")
    assert page.create_btn.isEnabled()
    page.create_btn.click()
    assert d.result() == QDialog.Accepted and len(shown_codes) == 1
    assert empty_store.exists() and empty_store.check_login("capo.officina", PWD).ok and empty_store.check_pin("4821").ok
    # il PIN scelto sostituisce qualsiasi PIN fisso
    assert not AccountStore(empty_store.path).check_pin("1" + "616").ok


def test_login_ok_wrong_and_lockout(store, clock):
    d = LoginDialog(store)
    d.show()
    page = d.pages["login"]
    assert d.current() == "login" and "PC-TEST" in page.device_label.text()
    page.user.setText("admin")
    page.pwd.edit.setText("sbagliata")
    page._attempt()
    assert d._current_toast.text() == "Credenziali errate" and page.pwd.text() == "" and d.result() != QDialog.Accepted
    for _ in range(4):
        page.pwd.edit.setText("sbagliata")
        page._attempt()
    assert "Riprova tra 30 s" in page.lock_label.text()
    assert not page.login_btn.isEnabled() and not page.user.isEnabled()
    clock.t += 12
    page.refresh_lock()
    assert "Riprova tra 18 s" in page.lock_label.text()
    clock.t += 20
    page.refresh_lock()
    assert page.lock_label.text() == "" and page.login_btn.isEnabled()
    page.user.setText("admin")
    page.pwd.edit.setText(PWD)
    page._attempt()
    assert d.result() == QDialog.Accepted


def test_lock_countdown_shown_after_restart(store, clock):
    for _ in range(5):
        store.check_login("admin", "x")
    d2 = LoginDialog(AccountStore(store.path, clock=clock))
    d2.show()
    assert "Riprova tra" in d2.pages["login"].lock_label.text() and not d2.pages["login"].login_btn.isEnabled()


def test_forgot_password_flow(store, shown_codes):
    old_code = _first_code(store)
    d = LoginDialog(store)
    d.show()
    login = d.pages["login"]
    login.forgot.click()
    page = d.pages["recovery"]
    assert d.current() == "recovery" and not page.reset_btn.isEnabled()
    assert "Ripristina_account.bat" in " ".join(l.text() for l in page.findChildren(type(page.lock_label)))
    page.code.setText("aaaa-bbbb-cccc")
    page.pwd.edit.setText("nuova-pass-9")
    page.pwd2.edit.setText("nuova-pass-9")
    page.pin.edit.setText("9876")
    page.pin2.edit.setText("9876")
    assert page.reset_btn.isEnabled()
    page._submit()                                                 # codice sbagliato
    assert d._current_toast.text() == "Codice di recupero errato" and d.current() == "recovery"
    page.code.setText(old_code.lower().replace("-", ""))           # minuscolo e senza trattini
    page._submit()
    assert d.current() == "login" and len(shown_codes) == 1 and shown_codes[0] != old_code
    assert store.check_login("admin", "nuova-pass-9").ok and store.check_pin("9876").ok
    assert store.check_recovery(old_code).status == "bad" and store.check_recovery(shown_codes[0]).ok


def _first_code(store):
    code = store.new_recovery_code(PWD)[1]
    return code


def test_wrong_recovery_codes_lock(store, clock, shown_codes):
    d = LoginDialog(store)
    d.show()
    d.go("recovery")
    page = d.pages["recovery"]
    for _ in range(5):
        page.code.setText("AAAA-BBBB-CCCC")
        page.pwd.edit.setText("nuova-pass-9"); page.pwd2.edit.setText("nuova-pass-9")
        page.pin.edit.setText("9876"); page.pin2.edit.setText("9876")
        if page.reset_btn.isEnabled():
            page._submit()
    assert "Riprova tra" in page.lock_label.text() and not page.reset_btn.isEnabled()


def test_pin_dialog_uses_account_pin_and_locks(store, qapp):
    d = PinDialog(None, "PIN per importare")
    d.show()
    d.edit.setText("1616")                                          # il vecchio PIN fisso non vale piu'
    d._confirm()
    assert d.result() != QDialog.Accepted and d._current_toast.text() == "PIN errato" and d.edit.text() == ""
    d.edit.setText(PIN)
    d._confirm()
    assert d.result() == QDialog.Accepted
    d2 = PinDialog(None)
    d2.show()
    for _ in range(5):
        d2.edit.setText("0000")
        d2._confirm()
    assert d2._current_toast.text().startswith("Troppi tentativi. Riprova tra")
    d2.edit.setText(PIN)
    d2._confirm()
    assert d2.result() != QDialog.Accepted                          # bloccato anche col PIN giusto


def test_recovery_code_dialog_needs_checkbox_and_ignores_escape(qapp, tmp_path, monkeypatch):
    d = RecoveryCodeDialog(None, "ABCD-EFGH-JKMN", "PC-TEST")
    d.show()
    assert not d.ok_btn.isEnabled() and d.code_label.text() == "ABCD-EFGH-JKMN"
    QTest.keyClick(d, Qt.Key_Escape)
    assert d.isVisible()
    out = tmp_path / "codice.txt"
    from PySide6.QtWidgets import QFileDialog
    monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: (str(out), "")))
    d.save_btn.click()
    assert "ABCD-EFGH-JKMN" in out.read_text(encoding="utf-8") and "PC-TEST" in out.read_text(encoding="utf-8")
    d.check.setChecked(True)
    assert d.ok_btn.isEnabled()
    d.ok_btn.click()
    assert d.result() == QDialog.Accepted


def test_security_actions_from_settings(store, qapp, tmp_path, monkeypatch, shown_codes):
    import app.main_window as mw
    from app.file_profiles import ProfileStore
    from app import config
    monkeypatch.setattr(config, "ORG_NAME", "Orizon-AIX-PYTEST")
    monkeypatch.setattr(mw, "ProfileStore", lambda: ProfileStore(str(tmp_path / "p.json")))
    w = mw.MainWindow(1.0)
    w.show()
    host = QDialog()                                               # al posto del dialogo Impostazioni
    host.show()

    def fill(values, click_ok=True):
        def act(dlg):
            for k, v in values.items():
                dlg.inputs[k].edit.setText(v)
            if click_ok:
                dlg.ok_btn.click()
            else:
                dlg.reject()
            return dlg
        return act

    # password: attuale errata -> resta aperto con errore, poi riesce
    wrong = run_modal(AccountFormDialog, lambda dlg: (
        dlg.inputs["current"].edit.setText("sbagliata"), dlg.inputs["new"].edit.setText("altra-pass-1"),
        dlg.inputs["confirm"].edit.setText("altra-pass-1"), dlg.ok_btn.click(),
        pump(100), dlg.reject(), dlg._current_toast.text())[-1], lambda: w.account_action("password", host))
    assert wrong == "Password attuale errata" and store.check_login("admin", PWD).ok
    run_modal(AccountFormDialog, fill({"current": PWD, "new": "altra-pass-1", "confirm": "altra-pass-1"}),
              lambda: w.account_action("password", host))
    assert store.check_login("admin", "altra-pass-1").ok and host._current_toast.text() == "Password aggiornata"
    # PIN
    run_modal(AccountFormDialog, fill({"password": "altra-pass-1", "new": "135790", "confirm": "135790"}),
              lambda: w.account_action("pin", host))
    assert store.check_pin("135790").ok and host._current_toast.text() == "PIN aggiornato"
    # nuovo codice
    old_hash = store._data["recovery_hash"]
    run_modal(AccountFormDialog, fill({"password": "altra-pass-1"}), lambda: w.account_action("recovery", host))
    assert len(shown_codes) == 1 and store._data["recovery_hash"] != old_hash
    assert host._current_toast.text() == "Nuovo codice di recupero generato"
    w._allow_close = True
    w.close()
    host.close()


def test_security_tab_shows_account_info(store, qapp):
    from app.settings_tabs.security_tab import SecurityTab
    from PySide6.QtWidgets import QLabel
    tab = SecurityTab(1.0, lambda k: None)
    texts = [l.text() for l in tab.findChildren(QLabel)]
    assert "PC-TEST" in texts and "admin" in texts
    assert any("/" in t and ":" in t for t in texts)               # data di creazione
    assert set(tab.buttons) == {"password", "pin", "recovery"}
