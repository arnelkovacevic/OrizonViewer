"""Lettura di file .xlsx (openpyxl, read_only): fogli, anteprima, caricamento delle sole colonne necessarie."""
import datetime
from dataclasses import dataclass, field
from typing import Optional

from openpyxl import load_workbook

from . import config
from .search import Dataset


class XlsxError(Exception):
    pass


@dataclass
class SheetInfo:
    name: str
    rows: Optional[int] = None
    cols: Optional[int] = None


@dataclass
class Preview:
    names: list = field(default_factory=list)    # nomi colonna univoci
    rows: list = field(default_factory=list)     # righe (liste di str) dopo l'intestazione
    samples: list = field(default_factory=list)  # primo valore non vuoto per colonna


def to_text(v) -> str:
    """Valore cella -> testo. Numeri interi senza «.0»; date ISO."""
    if v is None:
        return ""
    if isinstance(v, bool):
        return str(v)
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        return str(int(v)) if v.is_integer() and abs(v) < 1e15 else repr(v)
    if isinstance(v, datetime.datetime):
        return v.date().isoformat() if v.time() == datetime.time(0) else v.isoformat(sep=" ")
    if isinstance(v, (datetime.date, datetime.time)):
        return v.isoformat()
    return str(v).strip()


def resolve_names(raw_header, count: int) -> list:
    """Nomi colonna: vuoti -> «Colonna N», duplicati -> «Nome (2)»."""
    names, seen = [], set()
    for i in range(count):
        base = to_text(raw_header[i]) if i < len(raw_header) else ""
        name = base or f"Colonna {i + 1}"
        if name in seen:
            n = 2
            while f"{base or f'Colonna {i + 1}'} ({n})" in seen:
                n += 1
            name = f"{base or f'Colonna {i + 1}'} ({n})"
        seen.add(name)
        names.append(name)
    return names


def _open(path: str):
    try:
        return load_workbook(path, read_only=True, data_only=True)
    except Exception as e:
        raise XlsxError(str(e)) from e


def list_sheets(path: str) -> list:
    """Nomi dei fogli (+ righe/colonne se disponibili rapidamente)."""
    wb = _open(path)
    try:
        out = []
        for name in wb.sheetnames:
            ws = wb[name]
            rows = cols = None
            try:
                rows, cols = ws.max_row, ws.max_column
            except Exception:
                pass
            out.append(SheetInfo(name, rows or None, cols or None))
        return out
    finally:
        wb.close()


def read_preview(path: str, sheet: str, header_row: int = 1, nrows: int = config.PREVIEW_ROWS) -> Preview:
    wb = _open(path)
    try:
        if sheet not in wb.sheetnames:
            raise XlsxError(f"foglio «{sheet}» non trovato")
        ws = wb[sheet]
        it = ws.iter_rows(min_row=max(1, header_row), max_row=max(1, header_row) + nrows, values_only=True)
        header = next(it, None)
        if header is None:
            return Preview()
        rows = [[to_text(v) for v in r] for r in it]
    finally:
        wb.close()
    last = -1  # ultima colonna con intestazione o dati
    for i, h in enumerate(header):
        if to_text(h):
            last = max(last, i)
    for r in rows:
        for i in range(len(r) - 1, last, -1):
            if r[i]:
                last = i
                break
    count = last + 1
    names = resolve_names(header, count)
    rows = [(r + [""] * count)[:count] for r in rows]
    rows = [r for r in rows if any(r)]
    samples = []
    for c in range(count):
        samples.append(next((r[c] for r in rows if r[c]), ""))
    return Preview(names, rows, samples)


def header_names(path: str, sheet: str, header_row: int) -> list:
    return read_preview(path, sheet, header_row).names


def load_dataset(path: str, sheet: str, header_row: int, wanted: list) -> Dataset:
    """Carica TUTTE le righe, ma solo le colonne `wanted` (ordine mantenuto, senza duplicati)."""
    wb = _open(path)
    try:
        ws = wb[sheet]
        it = ws.iter_rows(min_row=max(1, header_row), values_only=True)
        header = next(it, None)
        if header is None:
            return Dataset([], list(wanted))
        names = resolve_names(header, len(header))
        # colonne con dati oltre l'intestazione: stessa logica dell'anteprima (nomi posizionali)
        index = {}
        for i, n in enumerate(names):
            index.setdefault(n, i)
        missing = [w for w in wanted if w not in index]
        if missing:
            raise XlsxError("colonne non trovate: " + ", ".join(missing))
        idx = [index[w] for w in wanted]
        rows = []
        for r in it:
            vals = tuple(to_text(r[i]) if i < len(r) else "" for i in idx)
            if any(vals):
                rows.append(vals)
    finally:
        wb.close()
    return Dataset(rows, list(wanted))
