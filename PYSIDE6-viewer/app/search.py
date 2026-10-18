"""Logica di ricerca pura (senza Qt): testo normalizzato pre-calcolato + filtro per sottostringhe."""
import unicodedata

from . import config


def fold(text: str) -> str:
    """Minuscolo senza accenti. Mantiene la lunghezza (utile per l'evidenziazione)."""
    t = text.lower()
    if t.isascii():
        return t
    return "".join(c for c in unicodedata.normalize("NFD", t) if not unicodedata.combining(c))


def normalize(text: str) -> str:
    """fold + spazi multipli ridotti a uno."""
    return " ".join(fold(text).split())


def parse_query(query: str) -> list:
    """Divide la query per '%' e per spazi; parti normalizzate, senza duplicati."""
    parts = []
    for p in normalize(query.replace("%", " ")).split():
        if p not in parts:
            parts.append(p)
    return parts


def filter_indices(haystack: list, parts: list, subset=None) -> list:
    """Indici delle righe che contengono TUTTE le parti (in qualsiasi ordine)."""
    if subset is None:
        subset = range(len(haystack))
    if not parts:
        return list(subset)
    if len(parts) == 1:
        p = parts[0]
        return [i for i in subset if p in haystack[i]]
    return [i for i in subset if all(p in haystack[i] for p in parts)]


class Dataset:
    """Righe dell'Excel (tutte le 8 colonne come testo) + liste di ricerca pre-calcolate."""

    def __init__(self, rows: list):
        self.rows = rows  # list[tuple[str, ...]] con len == len(ALL_COLUMNS)
        # una volta sola: tutto il testo della riga unito, normalizzato
        self.haystack = [normalize(" ".join(r)) for r in rows]
        self._sort_keys = {}

    def __len__(self):
        return len(self.rows)

    def sort_keys(self, col: int) -> list:
        if col not in self._sort_keys:
            self._sort_keys[col] = [fold(r[col]) for r in self.rows]
        return self._sort_keys[col]

    def search(self, query: str = "") -> list:
        """Indici delle righe che contengono tutte le parti della query (qualsiasi ordine)."""
        parts = parse_query(query)
        if not parts:
            return list(range(len(self.rows)))
        return filter_indices(self.haystack, parts)

    @classmethod
    def from_dataframe(cls, df) -> "Dataset":
        n = len(config.ALL_COLUMNS)
        cols = []
        for i, name in enumerate(config.ALL_COLUMNS):
            if name in df.columns:
                cols.append(df[name])
            elif i < df.shape[1]:
                cols.append(df.iloc[:, i])
            else:
                cols.append(None)
        lists = []
        for c in cols:
            if c is None:
                lists.append([""] * len(df))
            else:
                lists.append([("" if v is None else str(v)).strip() for v in c.fillna("").tolist()])
        rows = [tuple(lists[j][i] for j in range(n)) for i in range(len(df))]
        return cls(rows)
