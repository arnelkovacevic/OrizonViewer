"""Profili salvati (JSON): una configurazione per struttura di foglio, riconosciuta da una firma."""
import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from typing import Optional

from PySide6.QtCore import QStandardPaths

from . import xlsx_reader
from .details import DetailSpec


def signature(sheet: str, names: list) -> str:
    """Firma = hash di nome del foglio + elenco dei nomi colonna."""
    raw = sheet + "\x1e" + "\x1f".join(names)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


def _norm(path: str) -> str:
    return os.path.normcase(os.path.abspath(path))


@dataclass
class Profile:
    path: str
    sheet: str
    header_row: int
    all_columns: list                       # nomi di tutte le colonne del foglio (per la firma)
    columns: list                           # colonne mostrate, nell'ordine scelto
    details: DetailSpec = field(default_factory=DetailSpec)
    widths: dict = field(default_factory=dict)  # nome colonna -> larghezza a scala 1.0
    last_used: float = 0.0

    @property
    def id(self) -> str:
        return signature(self.sheet, self.all_columns)

    @property
    def name(self) -> str:
        return f"{os.path.basename(self.path)} / {self.sheet}"

    def needed_columns(self) -> list:
        """Colonne da leggere: mostrate + quelle del popup, senza duplicati."""
        out = []
        for c in list(self.columns) + self.details.used_columns():
            if c not in out:
                out.append(c)
        return out

    def to_dict(self) -> dict:
        return {
            "id": self.id, "path": self.path, "sheet": self.sheet, "header_row": self.header_row,
            "all_columns": self.all_columns, "columns": self.columns,
            "details": self.details.to_dict(), "widths": self.widths, "last_used": self.last_used,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Profile":
        return cls(
            path=d["path"], sheet=d["sheet"], header_row=int(d.get("header_row", 1)),
            all_columns=list(d.get("all_columns", [])), columns=list(d.get("columns", [])),
            details=DetailSpec.from_dict(d.get("details", {})), widths=dict(d.get("widths", {})),
            last_used=float(d.get("last_used", 0.0)),
        )


class ProfileStore:
    def __init__(self, file_path: Optional[str] = None):
        if file_path is None:
            base = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
            file_path = os.path.join(base, "profiles.json")
        self.file_path = file_path
        self._profiles = {}
        self._load()

    def _load(self):
        try:
            with open(self.file_path, encoding="utf-8") as f:
                data = json.load(f)
            for d in data.get("profiles", []):
                p = Profile.from_dict(d)
                self._profiles[p.id] = p
        except (OSError, ValueError, KeyError, TypeError):
            self._profiles = {}

    def _save(self):
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        tmp = self.file_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"version": 1, "profiles": [p.to_dict() for p in self._profiles.values()]},
                      f, ensure_ascii=False, indent=1)
        os.replace(tmp, self.file_path)

    def all(self) -> list:
        return sorted(self._profiles.values(), key=lambda p: p.last_used, reverse=True)

    def count(self) -> int:
        return len(self._profiles)

    def upsert(self, profile: Profile):
        profile.last_used = time.time()
        # stessa struttura/percorso: sostituisce; se la struttura e' cambiata resta anche quella vecchia
        self._profiles[profile.id] = profile
        self._save()

    def clear(self):
        self._profiles = {}
        self._save()


@dataclass
class Match:
    kind: str                       # "applied" | "changed" | "none"
    profile: Optional[Profile] = None


def resolve(path: str, store: ProfileStore) -> Match:
    """Cerca un profilo applicabile al file.
    applied: stessa firma (foglio + nomi colonna) e tutte le colonne esistono ancora;
    changed: esiste un profilo per questo file ma la struttura non coincide piu';
    none: file mai configurato."""
    try:
        sheets = {s.name for s in xlsx_reader.list_sheets(path)}
    except xlsx_reader.XlsxError:
        raise
    cache = {}
    same_path = []
    for p in store.all():  # piu' recenti prima
        is_same = _norm(p.path) == _norm(path)
        if is_same:
            same_path.append(p)
        if p.sheet not in sheets:
            continue
        key = (p.sheet, p.header_row)
        if key not in cache:
            cache[key] = xlsx_reader.header_names(path, p.sheet, p.header_row)
        names = cache[key]
        if signature(p.sheet, names) == p.id and all(c in names for c in p.columns):
            if not is_same:  # stessa struttura in un file diverso: il profilo segue il nuovo percorso
                p.path = path
            return Match("applied", p)
    if same_path:
        return Match("changed", same_path[0])
    return Match("none")
