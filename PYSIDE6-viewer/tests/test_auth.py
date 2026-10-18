import json
import logging
import os

import pytest

from app import auth
from app.auth import AccountStore, LOCK_SECONDS, MAX_ATTEMPTS

PWD, PIN = "segreta-123", "4821"


class Clock:
    def __init__(self, t=1_000_000.0):
        self.t = t

    def __call__(self):
        return self.t


@pytest.fixture()
def clock():
    return Clock()


@pytest.fixture()
def store(tmp_path, clock):
    s = AccountStore(str(tmp_path / "account.json"), clock=clock)
    s.code = s.create("admin", PWD, PIN, "PC-OFFICINA")
    return s


def test_no_account_file_means_registration(tmp_path):
    s = AccountStore(str(tmp_path / "account.json"))
    assert not s.exists()


def test_create_and_login(store, tmp_path):
    assert store.exists() and store.device_name == "PC-OFFICINA" and store.username == "admin"
    assert store.created_at is not None
    assert store.check_login("admin", PWD).ok
    assert store.check_login("  admin ", PWD).ok          # spazi attorno al nome utente
    assert store.check_login("admin", "sbagliata").status == "bad"
    assert store.check_login("altro", PWD).status == "bad"
    assert store.check_pin(PIN).ok and store.check_pin("0000").status == "bad"
    # persistenza: un nuovo oggetto legge lo stesso file
    again = AccountStore(store.path)
    assert again.exists() and again.check_login("admin", PWD).ok and again.check_pin(PIN).ok


def test_validation_rules():
    assert auth.validate_username("ab") and auth.validate_username("a" * 21) and auth.validate_username("bad name")
    assert auth.validate_username("admin") is None and auth.validate_username("a.b_c-9") is None
    assert auth.validate_password("12345") and auth.validate_password("123456") is None
    assert auth.validate_pin("123") and auth.validate_pin("1234567") and auth.validate_pin("12a4")
    assert auth.validate_pin("1234") is None and auth.validate_pin("123456") is None
    with pytest.raises(ValueError):
        AccountStore.create(AccountStore(os.devnull + "x"), "ab", "123456", "1234")


def test_recovery_code_format():
    for _ in range(50):
        code = auth.generate_code()
        parts = code.split("-")
        assert len(parts) == 3 and all(len(p) == 4 for p in parts)
        assert not set("".join(parts)) & set("0O1IL")
    assert auth.normalize_code(" abcd-efgh-2345 ") == "ABCDEFGH2345"


def test_lock_after_five_wrong_and_unlock_after_expiry(store, clock):
    for i in range(MAX_ATTEMPTS - 1):
        assert store.check_login("admin", "x").status == "bad", i
    last = store.check_login("admin", "x")
    assert last.locked and last.remaining == LOCK_SECONDS
    assert store.lock_remaining() == LOCK_SECONDS
    # durante il blocco anche la password GIUSTA e il PIN giusto vengono respinti
    assert store.check_login("admin", PWD).locked and store.check_pin(PIN).locked
    clock.t += 10
    assert 0 < store.lock_remaining() <= 20
    clock.t += 21
    assert store.lock_remaining() == 0
    assert store.check_login("admin", PWD).ok            # sbloccato


def test_lock_survives_restart(store, clock):
    for _ in range(MAX_ATTEMPTS):
        store.check_pin("0000")
    again = AccountStore(store.path, clock=clock)
    assert again.lock_remaining() > 0 and again.check_pin(PIN).locked
    clock.t += LOCK_SECONDS + 1
    assert AccountStore(store.path, clock=clock).check_pin(PIN).ok


def test_failed_attempts_persist_and_reset_on_success(store, clock):
    store.check_pin("0000")
    store.check_pin("0001")
    assert AccountStore(store.path, clock=clock).failed_attempts() == 2
    assert store.check_pin(PIN).ok and store.failed_attempts() == 0
    assert AccountStore(store.path, clock=clock).failed_attempts() == 0


def test_clock_moved_backwards_never_locks_longer_than_30s(store, clock):
    for _ in range(MAX_ATTEMPTS):
        store.check_pin("0000")
    clock.t -= 3600
    assert store.lock_remaining() <= LOCK_SECONDS


def test_pin_and_recovery_and_login_share_the_counter(store):
    store.check_login("admin", "x")
    store.check_pin("0000")
    store.check_recovery("AAAA-BBBB-CCCC")
    store.check_pin("1111")
    assert store.check_recovery("ZZZZ-ZZZZ-ZZZZ").locked


def test_recovery_with_dashes_without_and_lowercase(store):
    old = store.code
    variants = [old, old.replace("-", ""), old.lower(), old.replace("-", " ").lower()]
    for v in variants:
        s = AccountStore(store.path)
        res, new = s.recover(v, "nuova-pass-9", "9876")
        assert res.ok and new and new != old
        # ripristino il codice originale per provare la variante successiva
        s2 = AccountStore(store.path)
        s2._data["recovery_hash"], s2._data["recovery_salt"] = auth._make(auth.normalize_code(old))
        s2._save()


def test_recovery_changes_credentials_and_invalidates_old_code(store):
    old = store.code
    res, new = store.recover(old, "nuova-pass-9", "9876")
    assert res.ok
    assert store.check_login("admin", "nuova-pass-9").ok and store.check_pin("9876").ok
    assert store.check_login("admin", PWD).status == "bad" and store.check_pin(PIN).status == "bad"
    assert store.check_recovery(old).status == "bad"       # il vecchio codice non vale piu'
    assert store.check_recovery(new).ok
    res, none = store.recover("AAAA-BBBB-CCCC", "x" * 8, "1234")
    assert res.status == "bad" and none is None and store.check_login("admin", "nuova-pass-9").ok


def test_wrong_recovery_code_counts_towards_lock(store):
    for i in range(MAX_ATTEMPTS - 1):
        assert store.recover("AAAA-BBBB-CCCC", "abcdef", "1234")[0].status == "bad"
    assert store.recover("AAAA-BBBB-CCCC", "abcdef", "1234")[0].locked
    assert store.recover(store.code, "abcdef", "1234")[0].locked    # anche il codice giusto, durante il blocco


def test_change_password_pin_and_new_code(store):
    assert store.change_password("sbagliata", "nuova-pass").status == "bad"
    assert store.check_login("admin", PWD).ok
    assert store.change_password(PWD, "nuova-pass").ok
    assert store.check_login("admin", "nuova-pass").ok and store.check_login("admin", PWD).status == "bad"
    assert store.change_pin("nuova-pass", "55555").ok and store.check_pin("55555").ok
    assert store.change_pin("sbagliata", "1111").status == "bad" and store.check_pin("55555").ok
    old = store.code
    res, code = store.new_recovery_code("nuova-pass")
    assert res.ok and code != old and store.check_recovery(old).status == "bad" and store.check_recovery(code).ok
    assert store.new_recovery_code("sbagliata") [1] is None


def test_file_has_no_plaintext_secrets(store):
    store.change_pin(PWD, "246810")
    new_code = store.new_recovery_code(PWD)[1]
    raw = open(store.path, encoding="utf-8").read()
    for secret in (PWD, PIN, "246810", store.code, new_code, new_code.replace("-", ""), auth.normalize_code(new_code)):
        assert secret not in raw
    data = json.loads(raw)
    assert set(data) == {"device_name", "username", "password_hash", "password_salt", "pin_hash", "pin_salt",
                         "recovery_hash", "recovery_salt", "created_at", "failed_attempts", "locked_until"}
    assert len(bytes.fromhex(data["password_salt"])) == 16 and len(bytes.fromhex(data["password_hash"])) == 32
    assert data["password_salt"] != data["pin_salt"] != data["recovery_salt"]   # salt distinti


def test_hash_parameters(monkeypatch):
    calls = []
    real = auth.hashlib.pbkdf2_hmac
    monkeypatch.setattr(auth.hashlib, "pbkdf2_hmac", lambda *a, **k: (calls.append(a), real(*a, **k))[1])
    auth._make("segreto")
    assert calls[0][0] == "sha256" and calls[0][3] == 200_000


@pytest.mark.parametrize("content", ["{non e json", "", "[]", '{"username": "x"}', "\x00\x01\x02"])
def test_corrupt_account_file_behaves_like_missing(tmp_path, caplog, content):
    path = tmp_path / "account.json"
    path.write_text(content, encoding="utf-8", errors="ignore")
    with caplog.at_level(logging.WARNING, logger="orizon.auth"):
        s = AccountStore(str(path))
    assert not s.exists()
    assert any("account.json" in r.message for r in caplog.records)
    assert s.check_login("a", "b").status == "bad"
    code = s.create("admin", PWD, PIN, "PC")                # si puo' registrare di nuovo
    assert s.exists() and code and AccountStore(str(path)).check_pin(PIN).ok


def test_log_never_contains_secrets(tmp_path, caplog):
    path = tmp_path / "account.json"
    path.write_text("{rotto", encoding="utf-8")
    with caplog.at_level(logging.DEBUG, logger="orizon.auth"):
        s = AccountStore(str(path))
        code = s.create("admin", PWD, PIN, "PC")
        s.check_login("admin", "sbagliata-xyz")
    text = " ".join(r.getMessage() for r in caplog.records)
    for secret in (PWD, PIN, code, "sbagliata-xyz"):
        assert secret not in text


def test_windows_data_dir_matches_bat(monkeypatch):
    monkeypatch.setattr(auth.os, "name", "nt")
    monkeypatch.setenv("APPDATA", r"C:\Users\x\AppData\Roaming")
    assert auth.data_dir().endswith(os.path.join("Orizon-AIX", "OrizonViewer"))
    bat = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Ripristina_account.bat"),
               encoding="utf-8").read()
    assert r"%APPDATA%\Orizon-AIX\OrizonViewer\account.json" in bat
    assert "tasklist" in bat and "/I not" in bat and "SI" in bat and "del /F /Q" in bat
    assert "account.json" in bat and "profiles.json" not in bat       # elimina solo l'account


def test_no_hardcoded_credentials_left():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    hits = []
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in (".venv", "__pycache__", "tests", ".pytest_cache", "build", "dist")]
        for f in files:
            if f.endswith((".py", ".qss", ".spec", ".bat")):
                text = open(os.path.join(dirpath, f), encoding="utf-8", errors="ignore").read()
                if "nadir" in text or "1616" in text or "USERNAME_HASH" in text or "PIN_HASH" in text:
                    hits.append(f)
    assert not hits, hits
