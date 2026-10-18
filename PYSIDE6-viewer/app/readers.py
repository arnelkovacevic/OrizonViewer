"""Livello unico di lettura per tutti i formati supportati.

  .xlsx .xlsm        -> openpyxl (streaming)
  .xls               -> xlrd
  .xlsb              -> pyxlsb
  .ods               -> odfpy
  .csv .tsv .txt     -> lettore di testo (codifica e separatore rilevati automaticamente)

Interfaccia: list_sheets, read_preview, read_data (DataFrame di stringhe, vuoti = ""), piu'
preview() che restituisce la struttura usata dal wizard. Nessun altro modulo legge i file direttamente.
"""
import codecs
import csv
import itertools
import os
from dataclasses import dataclass, field

import pandas as pd

from . import config
from .xlsx_reader import SheetInfo, iter_raw_rows, resolve_names, sheet_infos, to_text

TEXT_SHEET = "(testo)"
MSG_DAMAGED = "File danneggiato o non supportato"
MSG_LOCKED = "File aperto in un altro programma, chiudilo e riprova"

EXCEL_EXT = (".xlsx", ".xlsm", ".xls", ".xlsb")
ODS_EXT = (".ods",)
TEXT_EXT = (".csv", ".tsv", ".txt")
ALL_EXT = EXCEL_EXT + ODS_EXT + TEXT_EXT

FILE_FILTER = ";;".join([
    "Tutti i file supportati (*.xlsx *.xlsm *.xls *.xlsb *.ods *.csv *.tsv *.txt)",
    "Excel (*.xlsx *.xlsm *.xls *.xlsb)",
    "LibreOffice (*.ods)",
    "Testo (*.csv *.tsv *.txt)",
])

# (etichetta mostrata, codec Python)
ENCODINGS = [("UTF-8", "utf-8-sig"), ("Windows-1252", "cp1252"), ("ISO-8859-1", "latin-1")]
# (carattere, etichetta mostrata)
DELIMITERS = [(";", "; (punto e virgola)"), (",", ", (virgola)"), ("\t", "Tab"), ("|", "| (barra verticale)")]

_PANDAS_ENGINE = {".xls": "xlrd", ".xlsb": "pyxlsb", ".ods": "odf"}
_ZIP_MAGIC = (b"PK\x03\x04", b"PK\x05\x06")
_OLE_MAGIC = bytes.fromhex("D0CF11E0A1B11AE1")

csv.field_size_limit(10_000_000)


class ReaderError(Exception):
    """Errore di lettura con messaggio gia' pronto per l'utente (italiano)."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


@dataclass
class Preview:
    names: list = field(default_factory=list)    # nomi colonna univoci
    rows: list = field(default_factory=list)     # righe (liste di str) dopo l'intestazione
    samples: list = field(default_factory=list)  # primo valore non vuoto per colonna


# ------------------------------------------------------------------ formato / errori
def ext_of(path: str) -> str:
    return os.path.splitext(path)[1].lower()


def kind(path: str) -> str:
    """'excel' | 'ods' | 'text' (estensione case-insensitive)."""
    ext = ext_of(path)
    if ext in EXCEL_EXT:
        return "excel"
    if ext in ODS_EXT:
        return "ods"
    if ext in TEXT_EXT:
        return "text"
    raise ReaderError(f"Formato non supportato: «{ext or os.path.basename(path)}»")


def format_label(path: str) -> str:
    ext = ext_of(path)
    k = kind(path)
    return {"excel": f"Excel ({ext})", "ods": "LibreOffice (.ods)", "text": f"Testo ({ext})"}[k]


def delimiter_label(delimiter: str) -> str:
    return {";": ";", ",": ",", "\t": "Tab", "|": "|"}.get(delimiter, delimiter)


def _translate(e: Exception) -> ReaderError:
    if isinstance(e, ReaderError):
        return e
    if isinstance(e, FileNotFoundError):
        return ReaderError("File non trovato")
    if isinstance(e, PermissionError) or (isinstance(e, OSError) and getattr(e, "winerror", None) == 32):
        return ReaderError(MSG_LOCKED)
    if isinstance(e, ImportError):
        return ReaderError(f"Componente mancante per leggere questo formato ({e.name}). "
                           "Esegui: pip install -r requirements.txt")
    return ReaderError(MSG_DAMAGED)


def _guard(fn):
    def wrapper(*a, **k):
        try:
            return fn(*a, **k)
        except Exception as e:  # noqa: BLE001 - tutto viene tradotto in un messaggio chiaro
            raise _translate(e) from e
    wrapper.__name__ = fn.__name__
    wrapper.__doc__ = fn.__doc__
    return wrapper


def _check_magic(path: str):
    """Il contenuto deve corrispondere all'estensione (zip per xlsx/xlsm/xlsb/ods, OLE per xls)."""
    ext = ext_of(path)
    with open(path, "rb") as f:
        head = f.read(8)
    if ext in (".xlsx", ".xlsm", ".xlsb", ".ods"):
        ok = head[:4] in _ZIP_MAGIC
    elif ext == ".xls":
        ok = head == _OLE_MAGIC
    else:
        ok = True
    if not ok:
        raise ReaderError(MSG_DAMAGED)


# ------------------------------------------------------------------ testo (csv/tsv/txt)
def _codec(label: str) -> str:
    return dict(ENCODINGS).get(label, "latin-1")


def detect_encoding(path: str) -> str:
    """UTF-8 (anche con BOM), poi Windows-1252, poi ISO-8859-1."""
    size = os.path.getsize(path)
    with open(path, "rb") as f:
        data = f.read(20 * 1024 * 1024)
    if b"\x00" in data[:8192]:
        raise ReaderError(MSG_DAMAGED)  # binario / UTF-16: non e' testo delimitato
    for label, codec in ENCODINGS:
        try:
            codecs.getincrementaldecoder(codec)().decode(data, final=len(data) >= size)
            return label
        except UnicodeDecodeError:
            continue
    return "ISO-8859-1"


def _sample_lines(path: str, encoding_label: str, n: int = 50) -> list:
    with open(path, "r", encoding=_codec(encoding_label), errors="replace", newline="") as f:
        return list(itertools.islice(f, n))


def detect_delimiter(path: str, encoding_label: str) -> str:
    if ext_of(path) == ".tsv":
        return "\t"
    lines = _sample_lines(path, encoding_label)
    sample = "".join(lines)
    candidates = [d for d, _l in DELIMITERS]
    try:
        d = csv.Sniffer().sniff(sample, delimiters="".join(candidates)).delimiter
        if d in candidates and lines and d in lines[0]:
            return d
    except csv.Error:
        pass
    # alternativa: il candidato con numero di occorrenze costante e maggiore di 0 in tutte le righe
    best, best_count = None, 0
    for d in candidates:
        counts = {ln.count(d) for ln in lines if ln.strip()}
        if len(counts) == 1 and (c := counts.pop()) > best_count:
            best, best_count = d, c
    return best or ";"


def detect_text_options(path: str) -> dict:
    enc = detect_encoding(path)
    return {"delimiter": detect_delimiter(path, enc), "encoding": enc}


def _text_opts(path: str, opts) -> dict:
    return dict(opts) if opts else detect_text_options(path)


def _text_rows(path: str, opts: dict):
    with open(path, "r", encoding=_codec(opts["encoding"]), errors="replace", newline="") as f:
        yield from csv.reader(f, delimiter=opts["delimiter"], quotechar='"')


# ------------------------------------------------------------------ righe grezze per formato
def _raw_rows(path: str, sheet: str, opts, max_row=None):
    k, ext = kind(path), ext_of(path)
    if k == "text":
        rows = _text_rows(path, _text_opts(path, opts))
        yield from (itertools.islice(rows, max_row) if max_row else rows)
    elif ext in (".xlsx", ".xlsm"):
        yield from iter_raw_rows(path, sheet, max_row)
    else:
        df = pd.read_excel(path, sheet_name=sheet, header=None, dtype=object, keep_default_na=False,
                           na_filter=False, engine=_PANDAS_ENGINE[ext], nrows=max_row)
        yield from df.values.tolist()


def _layout(header, sample_rows) -> tuple:
    """(nomi colonna, numero colonne): ultima colonna con intestazione o dati nelle righe campione."""
    last = -1
    for i, h in enumerate(header):
        if to_text(h):
            last = i
    for r in sample_rows:
        for i in range(len(r) - 1, last, -1):
            if to_text(r[i]):
                last = i
                break
    count = last + 1
    return resolve_names(header, count), count


def _norm_rows(rows, count: int) -> list:
    out = []
    for r in rows:
        vals = [to_text(v) for v in r[:count]]
        vals += [""] * (count - len(vals))
        if any(vals):
            out.append(vals)
    return out


# ------------------------------------------------------------------ interfaccia pubblica
@_guard
def list_sheets(path: str, opts=None) -> list:
    """Fogli del file (con righe/colonne se disponibili rapidamente). Per i file di testo: un solo foglio."""
    k, ext = kind(path), ext_of(path)
    if os.path.getsize(path) == 0:
        raise ReaderError(MSG_DAMAGED)
    if k == "text":
        _text_opts(path, opts)  # valida che sia testo leggibile
        return [SheetInfo(TEXT_SHEET)]
    _check_magic(path)
    if ext in (".xlsx", ".xlsm"):
        return sheet_infos(path)
    with pd.ExcelFile(path, engine=_PANDAS_ENGINE[ext]) as xf:
        return [SheetInfo(n) for n in xf.sheet_names]


@_guard
def read_preview(path: str, sheet: str, header_row: int = 1, n: int = 50, opts=None) -> pd.DataFrame:
    """Prime `n` righe di dati come DataFrame di stringhe (colonne = nomi univoci)."""
    header_row = max(1, header_row)
    if kind(path) != "text":
        _check_magic(path)
    rows = list(itertools.islice(_raw_rows(path, sheet, opts, max_row=header_row + n), header_row + n))
    if len(rows) < header_row:
        return pd.DataFrame(dtype=str)
    header, data = rows[header_row - 1], rows[header_row:]
    names, count = _layout(header, data)
    return pd.DataFrame(_norm_rows(data, count), columns=names, dtype=str)


def preview(path: str, sheet: str, header_row: int = 1, opts=None, n: int = config.PREVIEW_ROWS) -> Preview:
    """Anteprima per il wizard (nomi, righe, primo valore non vuoto per colonna)."""
    df = read_preview(path, sheet, header_row, n, opts)
    rows = df.values.tolist()
    samples = [next((r[c] for r in rows if r[c]), "") for c in range(df.shape[1])]
    return Preview(list(df.columns), rows, samples)


def header_names(path: str, sheet: str, header_row: int, opts=None) -> list:
    return preview(path, sheet, header_row, opts).names


@_guard
def read_data(path: str, sheet: str, header_row: int, columns: list, opts=None) -> pd.DataFrame:
    """Tutte le righe, solo le `columns` richieste (ordine mantenuto)."""
    header_row = max(1, header_row)
    if kind(path) != "text":
        _check_magic(path)
    it = iter(_raw_rows(path, sheet, opts))
    head = list(itertools.islice(it, header_row))
    if len(head) < header_row:
        return pd.DataFrame(columns=list(columns), dtype=str)
    header = head[-1]
    sample = list(itertools.islice(it, config.PREVIEW_ROWS))  # stessa regola dell'anteprima
    names, count = _layout(header, sample)
    index = {}
    for i, name in enumerate(names):
        index.setdefault(name, i)
    missing = [c for c in columns if c not in index]
    if missing:
        raise ReaderError("Colonne non trovate nel file: " + ", ".join(missing))
    idx = [index[c] for c in columns]
    out = []
    for r in itertools.chain(sample, it):
        vals = [to_text(r[i]) if i < len(r) else "" for i in idx]
        if any(vals):
            out.append(vals)
    return pd.DataFrame(out, columns=list(columns), dtype=str)
