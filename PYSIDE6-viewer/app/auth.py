"""Account locale (un amministratore per computer): password, PIN e codice di recupero.

Tutto resta offline in account.json (cartella dati dell'app). Nessun segreto in chiaro: solo hash
PBKDF2-HMAC-SHA256 (200.000 iterazioni) con salt casuale per ciascun segreto. Il contatore dei tentativi
falliti e il blocco temporaneo sono salvati nello stesso file, quindi sopravvivono al riavvio.
"""
import datetime
import hashlib
import hmac
import json
import logging
import os
import re
import secrets
import socket
import sys
import time
from dataclasses import dataclass
from typing import Optional

log = logging.getLogger("orizon.auth")

ITERATIONS = 200_000
SALT_BYTES = 16
MAX_ATTEMPTS = 5
LOCK_SECONDS = 30
DATA_SUBDIR = os.path.join("Orizon-AIX", "OrizonViewer")  # usato anche da Ripristina_account.bat

# senza caratteri facilmente confondibili: 0/O, 1/I/L
CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 12

_USERNAME_RE = re.compile(r"^[A-Za-z0-9._-]{3,20}$")


# ------------------------------------------------------------------ validazione (messaggi per l'utente)
def validate_username(value: str) -> Optional[str]:
    if not _USERNAME_RE.match(value or ""):
        return "Da 3 a 20 caratteri: lettere, numeri, . _ -"
    return None


def validate_password(value: str) -> Optional[str]:
    if len(value or "") < 6:
        return "Almeno 6 caratteri"
    return None


def validate_pin(value: str) -> Optional[str]:
    v = value or ""
    if not (v.isascii() and v.isdigit() and 4 <= len(v) <= 6):
        return "Da 4 a 6 cifre"
    return None


def normalize_code(code: str) -> str:
    """Il codice di recupero ignora trattini, spazi e maiuscole/minuscole."""
    return "".join(c for c in (code or "").upper() if c.isalnum())


def generate_code() -> str:
    raw = "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))
    return "-".join(raw[i:i + 4] for i in range(0, CODE_LENGTH, 4))


# ------------------------------------------------------------------ hash
def _hash(secret: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", secret.encode("utf-8"), salt, ITERATIONS)


def _make(secret: str) -> tuple:
    salt = secrets.token_bytes(SALT_BYTES)
    return _hash(secret, salt).hex(), salt.hex()


def _check(secret: str, hash_hex: str, salt_hex: str) -> bool:
    try:
        return hmac.compare_digest(_hash(secret, bytes.fromhex(salt_hex)), bytes.fromhex(hash_hex))
    except (ValueError, TypeError):
        return False


# ------------------------------------------------------------------ percorso
def data_dir() -> str:
    """Cartella dati dell'app (account.json, profiles.json, orizon.log). Calcolata senza Qt, cosi' esiste
    anche prima della QApplication; coincide con la AppDataLocation di Qt (organizzazione/applicazione).
    Windows: %APPDATA%\\Orizon-AIX\\OrizonViewer (lo stesso percorso usa Ripristina_account.bat)."""
    home = os.path.expanduser("~")
    if os.name == "nt":
        base = os.environ.get("APPDATA") or os.path.join(home, "AppData", "Roaming")
    elif sys.platform == "darwin":
        base = os.path.join(home, "Library", "Application Support")
    else:
        base = os.environ.get("XDG_DATA_HOME") or os.path.join(home, ".local", "share")
    return os.path.join(base, DATA_SUBDIR)


def account_path() -> str:
    return os.path.join(data_dir(), "account.json")


# ------------------------------------------------------------------ risultati
@dataclass(frozen=True)
class Check:
    status: str          # "ok" | "bad" | "locked"
    remaining: int = 0   # secondi di blocco rimanenti (solo per "locked")

    @property
    def ok(self) -> bool:
        return self.status == "ok"

    @property
    def locked(self) -> bool:
        return self.status == "locked"


_REQUIRED = ("device_name", "username", "password_hash", "password_salt", "pin_hash", "pin_salt",
             "recovery_hash", "recovery_salt", "created_at", "failed_attempts", "locked_until")


class AccountStore:
    def __init__(self, path: Optional[str] = None, clock=time.time):
        self.path = path or account_path()
        self._clock = clock
        self._data: Optional[dict] = None
        self.load()

    # ---------------------------------------------------------- file
    def load(self):
        self._data = None
        try:
            with open(self.path, encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict) or any(k not in data for k in _REQUIRED):
                raise ValueError("campi mancanti")
            data["failed_attempts"] = int(data["failed_attempts"])
            data["locked_until"] = float(data["locked_until"])
            self._data = data
        except FileNotFoundError:
            self._data = None
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as e:
            # nessun segreto nel log: solo il tipo di problema
            log.warning("account.json non valido o illeggibile (%s): si riparte dalla registrazione",
                        type(e).__name__)
            self._data = None

    def _save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=1)
        try:
            os.chmod(tmp, 0o600)
        except OSError:
            pass
        os.replace(tmp, self.path)

    def exists(self) -> bool:
        return self._data is not None

    # ---------------------------------------------------------- informazioni
    @property
    def device_name(self) -> str:
        return self._data["device_name"] if self._data else socket.gethostname()

    @property
    def username(self) -> str:
        return self._data["username"] if self._data else ""

    @property
    def created_at(self) -> Optional[datetime.datetime]:
        try:
            return datetime.datetime.fromisoformat(self._data["created_at"])
        except (TypeError, ValueError, KeyError):
            return None

    # ---------------------------------------------------------- blocco
    def lock_remaining(self) -> int:
        """Secondi di blocco rimanenti (0 se non bloccato)."""
        if not self._data:
            return 0
        left = self._data["locked_until"] - self._clock()
        if left <= 0:
            return 0
        return int(min(left, LOCK_SECONDS) + 0.999)  # orologio spostato indietro: mai oltre 30 s

    def failed_attempts(self) -> int:
        return self._data["failed_attempts"] if self._data else 0

    def _fail(self) -> Check:
        d = self._data
        d["failed_attempts"] += 1
        if d["failed_attempts"] >= MAX_ATTEMPTS:
            d["failed_attempts"] = 0
            d["locked_until"] = self._clock() + LOCK_SECONDS
            self._save()
            return Check("locked", LOCK_SECONDS)
        self._save()
        return Check("bad")

    def _succeed(self):
        d = self._data
        if d["failed_attempts"] or d["locked_until"]:
            d["failed_attempts"], d["locked_until"] = 0, 0.0
            self._save()

    def _guarded(self, ok_fn) -> Check:
        """Controlla un segreto con il contatore comune (login, PIN, password, codice di recupero)."""
        if not self._data:
            return Check("bad")
        left = self.lock_remaining()
        if left:
            return Check("locked", left)
        if ok_fn():
            self._succeed()
            return Check("ok")
        return self._fail()

    # ---------------------------------------------------------- creazione
    def create(self, username: str, password: str, pin: str, device_name: Optional[str] = None) -> str:
        """Crea l'account e restituisce il codice di recupero (da mostrare UNA volta)."""
        for err in (validate_username(username), validate_password(password), validate_pin(pin)):
            if err:
                raise ValueError(err)
        code = generate_code()
        ph, ps = _make(password)
        nh, ns = _make(pin)
        rh, rs = _make(normalize_code(code))
        self._data = {
            "device_name": device_name or socket.gethostname(), "username": username,
            "password_hash": ph, "password_salt": ps, "pin_hash": nh, "pin_salt": ns,
            "recovery_hash": rh, "recovery_salt": rs,
            "created_at": datetime.datetime.now().replace(microsecond=0).isoformat(),
            "failed_attempts": 0, "locked_until": 0.0,
        }
        self._save()
        return code

    # ---------------------------------------------------------- verifiche
    def check_login(self, username: str, password: str) -> Check:
        d = self._data
        return self._guarded(lambda: bool(d) and hmac.compare_digest(
            (username or "").strip().encode(), d["username"].encode())
            & _check(password or "", d["password_hash"], d["password_salt"]))

    def check_password(self, password: str) -> Check:
        d = self._data
        return self._guarded(lambda: _check(password or "", d["password_hash"], d["password_salt"]))

    def check_pin(self, pin: str) -> Check:
        d = self._data
        return self._guarded(lambda: _check(pin or "", d["pin_hash"], d["pin_salt"]))

    def check_recovery(self, code: str) -> Check:
        d = self._data
        return self._guarded(lambda: _check(normalize_code(code), d["recovery_hash"], d["recovery_salt"]))

    # ---------------------------------------------------------- modifiche
    def change_password(self, current: str, new: str) -> Check:
        res = self.check_password(current)
        if res.ok:
            err = validate_password(new)
            if err:
                raise ValueError(err)
            self._data["password_hash"], self._data["password_salt"] = _make(new)
            self._save()
        return res

    def change_pin(self, current_password: str, new_pin: str) -> Check:
        res = self.check_password(current_password)
        if res.ok:
            err = validate_pin(new_pin)
            if err:
                raise ValueError(err)
            self._data["pin_hash"], self._data["pin_salt"] = _make(new_pin)
            self._save()
        return res

    def new_recovery_code(self, current_password: str) -> tuple:
        """(Check, nuovo codice o None). Il vecchio codice smette di valere."""
        res = self.check_password(current_password)
        if not res.ok:
            return res, None
        return res, self._rotate_code()

    def _rotate_code(self) -> str:
        code = generate_code()
        self._data["recovery_hash"], self._data["recovery_salt"] = _make(normalize_code(code))
        self._save()
        return code

    def recover(self, code: str, new_password: str, new_pin: str) -> tuple:
        """Oppure reimposta password e PIN con il codice. (Check, NUOVO codice o None)."""
        res = self.check_recovery(code)
        if not res.ok:
            return res, None
        for err in (validate_password(new_password), validate_pin(new_pin)):
            if err:
                raise ValueError(err)
        self._data["password_hash"], self._data["password_salt"] = _make(new_password)
        self._data["pin_hash"], self._data["pin_salt"] = _make(new_pin)
        return res, self._rotate_code()


# ------------------------------------------------------------------ istanza condivisa
_store: Optional[AccountStore] = None


def get_store() -> AccountStore:
    global _store
    if _store is None:
        _store = AccountStore()
    return _store


def set_store(store: Optional[AccountStore]):
    global _store
    _store = store
