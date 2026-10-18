import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.search import Dataset, parse_query  # noqa: E402

ROW = "VITE TCE 16x50 BANCO OSCILLANTE"


def make_dataset():
    def row(code, desc, layout="A1", note="0"):
        return (code, "3A", "NR", desc, note, layout, "", "")

    return Dataset([
        row("90702010185217i", ROW, "A19A"),
        row("90204010751307U", "CUSCINETTO 51307", "A22A"),
        row("111", "Perno  con  testa  (più) lungo", "B3"),
        row("222", "VITE ZINCATA", "C4"),
        row("333", "BANCO DA LAVORO", "A19A"),
    ])


def test_parse_query():
    assert parse_query("BANCO%VITE") == ["banco", "vite"]
    assert parse_query("  %tce% ") == ["tce"]
    assert parse_query("banco   vite") == ["banco", "vite"]
    assert parse_query("") == []
    assert parse_query("%") == []


def test_examples_match_row():
    ds = make_dataset()
    for q in ["BANCO%VITE", "vite%banco", "banco vite", "16x50%osc", "%tce%"]:
        assert 0 in ds.search(q), q


def test_and_semantics():
    ds = make_dataset()
    assert ds.search("banco%vite") == [0]
    assert ds.search("vite") == [0, 3]
    assert ds.search("vite%inesistente") == []
    assert ds.search() == [0, 1, 2, 3, 4]


def test_accents_and_spaces_normalized():
    ds = make_dataset()
    assert ds.search("piu lungo") == [2]
    assert ds.search("PERNO CON TESTA") == [2]


def test_code_with_trailing_letter():
    ds = make_dataset()
    assert ds.search("90702010185217I") == [0]
    assert ds.search("185217i") == [0]


def test_dynamic_columns():
    from app.search import Dataset
    ds = Dataset([("X1", "banco da lavoro", "A1"), ("X2", "vite zincata", "B2")], ["Codice", "Testo", "Posizione"])
    assert ds.columns == ["Codice", "Testo", "Posizione"]
    assert ds.col_index("Posizione") == 2
    assert ds.search("lavoro%banco") == [0]
    assert ds.search("b2") == [1]            # la ricerca copre tutte le colonne memorizzate
    assert ds.sort_keys(1) == ["banco da lavoro", "vite zincata"]
