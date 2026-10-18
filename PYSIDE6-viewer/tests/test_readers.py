"""Lettura di tutti i formati: stessi dati ovunque, vuoti, accenti, zeri iniziali e lettere nei codici."""
import hashlib
import os
import shutil

import pandas as pd
import pytest

from app import readers
from app.file_profiles import Profile, ProfileStore, resolve, signature
from app.readers import MSG_DAMAGED, MSG_LOCKED, ReaderError

COLUMNS = ["Codice", "Descrizione", "Um", "Note"]
ROWS = [
    ["90702010185217i", "Raccordo à 90° ø12", "NR", ""],
    ["0012345", "Vite è inox", "PZ", "nota"],
    ["A-1", "Spazio doppio", "", "x; y"],
]
EXPECTED = pd.DataFrame(ROWS, columns=COLUMNS, dtype=str)
SHEET = "Dati"


def _xlsx(path):
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = SHEET
    ws.append(COLUMNS)
    for r in ROWS:
        ws.append([v if v != "" else None for v in r])
    wb.save(path)


def _xls(path):
    xlwt = pytest.importorskip("xlwt", reason="xlwt non installato: impossibile generare un .xls di prova")
    wb = xlwt.Workbook()
    ws = wb.add_sheet(SHEET)
    for c, h in enumerate(COLUMNS):
        ws.write(0, c, h)
    for r, row in enumerate(ROWS, start=1):
        for c, v in enumerate(row):
            if v != "":
                ws.write(r, c, v)
    wb.save(path)


def _ods(path):
    pytest.importorskip("odf")
    pd.DataFrame(ROWS, columns=COLUMNS).to_excel(path, sheet_name=SHEET, index=False, engine="odf")


def _text(path, sep, encoding):
    def q(v):
        return f'"{v}"' if sep in v or '"' in v else v
    lines = [sep.join(COLUMNS)] + [sep.join(q(v) for v in r) for r in ROWS]
    with open(path, "wb") as f:
        f.write(("\n".join(lines) + "\n").encode(encoding))


CASES = {
    "xlsx": (".xlsx", _xlsx, SHEET),
    "xls": (".xls", _xls, SHEET),
    "ods": (".ods", _ods, SHEET),
    "csv_semicolon_cp1252": (".csv", lambda p: _text(p, ";", "cp1252"), readers.TEXT_SHEET),
    "csv_comma_utf8bom": (".csv", lambda p: _text(p, ",", "utf-8-sig"), readers.TEXT_SHEET),
    "tsv_utf8": (".tsv", lambda p: _text(p, "\t", "utf-8"), readers.TEXT_SHEET),
    "txt_pipe_latin1": (".txt", lambda p: _text(p, "|", "latin-1"), readers.TEXT_SHEET),
}


@pytest.fixture(params=list(CASES))
def sample(request, tmp_path):
    ext, maker, sheet = CASES[request.param]
    path = str(tmp_path / f"dati{ext}")
    maker(path)
    return request.param, path, sheet


def test_same_columns_and_values_everywhere(sample):
    name, path, sheet = sample
    assert [s.name for s in readers.list_sheets(path)] == [sheet]
    df = readers.read_preview(path, sheet, 1)
    assert list(df.columns) == COLUMNS, name
    pd.testing.assert_frame_equal(df.reset_index(drop=True), EXPECTED, check_dtype=False)
    assert df.iloc[0, 0] == "90702010185217i"      # lettera finale intatta
    assert df.iloc[1, 0] == "0012345"              # zeri iniziali intatti
    assert df.iloc[0, 1] == "Raccordo à 90° ø12"   # accenti, grado, ø
    assert df.iloc[0, 3] == "" and df.iloc[2, 2] == ""   # vuoti = ""


def test_read_data_selected_columns(sample):
    _name, path, sheet = sample
    df = readers.read_data(path, sheet, 1, ["Note", "Codice"])
    assert list(df.columns) == ["Note", "Codice"] and len(df) == 3
    assert df["Codice"].tolist() == ["90702010185217i", "0012345", "A-1"]
    assert df["Note"].tolist() == ["", "nota", "x; y"]
    with pytest.raises(ReaderError):
        readers.read_data(path, sheet, 1, ["Inesistente"])


def test_preview_structure(sample):
    _n, path, sheet = sample
    pv = readers.preview(path, sheet, 1)
    assert pv.names == COLUMNS and len(pv.rows) == 3
    assert pv.samples == ["90702010185217i", "Raccordo à 90° ø12", "NR", "nota"]


def test_text_detection(tmp_path):
    expect = {
        "a.csv": (";", "Windows-1252", lambda p: _text(p, ";", "cp1252")),
        "b.csv": (",", "UTF-8", lambda p: _text(p, ",", "utf-8-sig")),
        "c.tsv": ("\t", "UTF-8", lambda p: _text(p, "\t", "utf-8")),
        "d.txt": ("|", "ISO-8859-1", lambda p: _text(p, "|", "latin-1")),
    }
    for fname, (delim, enc, maker) in expect.items():
        path = str(tmp_path / fname)
        maker(path)
        got = readers.detect_text_options(path)
        # cp1252 e latin-1 sono indistinguibili per questi caratteri: accetto la prima che decodifica
        assert got["delimiter"] == delim, fname
        assert got["encoding"] in (enc, "Windows-1252"), fname
    utf8 = str(tmp_path / "u.csv")
    _text(utf8, ";", "utf-8")
    assert readers.detect_encoding(utf8) == "UTF-8"


def test_text_explicit_options_override_detection(tmp_path):
    path = str(tmp_path / "x.csv")
    _text(path, ";", "cp1252")
    wrong = readers.read_preview(path, readers.TEXT_SHEET, 1, opts={"delimiter": ",", "encoding": "UTF-8"})
    assert list(wrong.columns) != COLUMNS            # separatore sbagliato -> colonne non divise
    right = readers.read_preview(path, readers.TEXT_SHEET, 1, opts={"delimiter": ";", "encoding": "Windows-1252"})
    assert list(right.columns) == COLUMNS and right.iloc[0, 1] == "Raccordo à 90° ø12"


def test_header_row_in_text(tmp_path):
    path = str(tmp_path / "h.csv")
    with open(path, "w", encoding="utf-8") as f:
        f.write("Titolo del report;;\n" + ";".join(COLUMNS) + "\n" + ";".join(ROWS[0]) + "\n")
    df = readers.read_preview(path, readers.TEXT_SHEET, header_row=2)
    assert list(df.columns) == COLUMNS and df.iloc[0, 0] == "90702010185217i"


def test_extension_case_insensitive(tmp_path):
    src = str(tmp_path / "a.xlsx")
    _xlsx(src)
    up = str(tmp_path / "B.XLSX")
    shutil.copy(src, up)
    csv_up = str(tmp_path / "C.Csv")
    _text(csv_up, ";", "utf-8")
    assert readers.kind(up) == "excel" and readers.kind(csv_up) == "text"
    assert readers.list_sheets(up)[0].name == SHEET
    assert list(readers.read_preview(csv_up, readers.TEXT_SHEET, 1).columns) == COLUMNS


def test_clear_errors(tmp_path, monkeypatch):
    fake = tmp_path / "finto.xlsx"
    fake.write_text("non sono un file excel")
    with pytest.raises(ReaderError) as e:
        readers.list_sheets(str(fake))
    assert e.value.message == MSG_DAMAGED
    empty = tmp_path / "vuoto.xlsx"
    empty.write_bytes(b"")
    with pytest.raises(ReaderError) as e:
        readers.list_sheets(str(empty))
    assert e.value.message == MSG_DAMAGED
    binary = tmp_path / "bin.csv"
    binary.write_bytes(bytes(range(256)) * 20)
    with pytest.raises(ReaderError) as e:
        readers.list_sheets(str(binary))
    assert e.value.message == MSG_DAMAGED
    with pytest.raises(ReaderError):
        readers.kind(str(tmp_path / "x.pdf"))
    # file aperto in un altro programma (Windows: PermissionError)
    good = str(tmp_path / "ok.xlsx")
    _xlsx(good)

    def locked(path):
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr(readers, "_check_magic", locked)
    with pytest.raises(ReaderError) as e:
        readers.list_sheets(good)
    assert e.value.message == MSG_LOCKED


def test_xlsb_support_is_wired():
    pytest.importorskip("pyxlsb")
    assert readers.kind("dati.XLSB") == "excel" and readers._PANDAS_ENGINE[".xlsb"] == "pyxlsb"
    # un .xlsb non e' generabile senza Excel: qui si verifica solo che un file finto dia l'errore pulito
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "finto.xlsb")
        with open(p, "wb") as f:
            f.write(b"PK\x03\x04 non valido")
        with pytest.raises(ReaderError) as e:
            readers.list_sheets(p)
        assert e.value.message == MSG_DAMAGED


def test_profile_signature_backward_compatible_and_text(tmp_path):
    names = ["a", "b"]
    old = hashlib.sha256(("Foglio1" + "\x1e" + "\x1f".join(names)).encode()).hexdigest()[:20]
    assert signature("Foglio1", names) == old                       # profili .xlsx salvati prima: invariati
    assert signature("Foglio1", names, "ods") != old
    t1 = signature(readers.TEXT_SHEET, names, "text", {"delimiter": ";", "encoding": "UTF-8"})
    t2 = signature(readers.TEXT_SHEET, names, "text", {"delimiter": ",", "encoding": "UTF-8"})
    t3 = signature(readers.TEXT_SHEET, names, "text", {"delimiter": ";", "encoding": "Windows-1252"})
    assert len({t1, t2, t3}) == 3

    path = str(tmp_path / "t.csv")
    _text(path, ";", "cp1252")
    opts = readers.detect_text_options(path)
    pv = readers.preview(path, readers.TEXT_SHEET, 1, opts)
    store = ProfileStore(str(tmp_path / "p.json"))
    store.upsert(Profile(path, readers.TEXT_SHEET, 1, pv.names, ["Codice", "Note"], fmt="text", text_opts=opts))
    again = ProfileStore(str(tmp_path / "p.json")).all()[0]
    assert again.fmt == "text" and again.text_opts == opts
    assert resolve(path, ProfileStore(str(tmp_path / "p.json"))).kind == "applied"
    # un .xlsx con le stesse colonne non deve ereditare il profilo del testo
    x = str(tmp_path / "t.xlsx")
    _xlsx(x)
    assert resolve(x, ProfileStore(str(tmp_path / "p.json"))).kind == "none"


def test_old_profile_json_without_format_still_loads(tmp_path, fixture_xlsx):
    import json
    from app.details import DetailSpec
    pv = readers.preview(fixture_xlsx, "Dati", 2)
    old_id = signature("Dati", pv.names)
    data = {"version": 1, "profiles": [{
        "id": old_id, "path": fixture_xlsx, "sheet": "Dati", "header_row": 2, "all_columns": pv.names,
        "columns": ["Codice", "EAN"], "details": DetailSpec().to_dict(), "widths": {}, "last_used": 1.0}]}
    pfile = tmp_path / "old.json"
    pfile.write_text(json.dumps(data))
    store = ProfileStore(str(pfile))
    p = store.all()[0]
    assert p.fmt == "excel" and p.text_opts is None and p.id == old_id
    assert resolve(fixture_xlsx, store).kind == "applied"
