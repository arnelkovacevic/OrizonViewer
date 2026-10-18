"""Engine openpyxl (.xlsx/.xlsm) in modalita' read_only + conversione celle -> testo.
Non va usato direttamente: l'interfaccia comune e' app/readers.py."""
import datetime
from dataclasses import dataclass
from typing import Optional

from openpyxl import load_workbook


@dataclass
class SheetInfo:
    name: str
    rows: Optional[int] = None
    cols: Optional[int] = None


def to_text(v) -> str:
    """Valore cella -> testo. Numeri interi senza «.0»; date ISO; vuoti/NaN -> ''."""
    if v is None:
        return ""
    if isinstance(v, bool):
        return str(v)
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        if v != v:  # NaN
            return ""
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
        label = base or f"Colonna {i + 1}"
        name = label
        if name in seen:
            n = 2
            while f"{label} ({n})" in seen:
                n += 1
            name = f"{label} ({n})"
        seen.add(name)
        names.append(name)
    return names


def sheet_infos(path: str) -> list:
    wb = load_workbook(path, read_only=True, data_only=True)
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


def iter_raw_rows(path: str, sheet: str, max_row: Optional[int] = None):
    """Righe grezze (tuple di valori) dalla riga 1, in streaming."""
    wb = load_workbook(path, read_only=True, data_only=True)
    try:
        if sheet not in wb.sheetnames:
            raise KeyError(sheet)
        yield from wb[sheet].iter_rows(min_row=1, max_row=max_row, values_only=True)
    finally:
        wb.close()
