"""Logica di ricerca pura (senza Qt): testo normalizzato pre-calcolato + filtro per sottostringhe."""
import unicodedata


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
    """Righe (solo le colonne necessarie, come testo) + testo di ricerca pre-calcolato."""

    def __init__(self, rows: list, columns: list = None):
        self.rows = rows  # list[tuple[str, ...]]
        width = len(rows[0]) if rows else (len(columns) if columns else 0)
        self.columns = list(columns) if columns else [f"Colonna {i + 1}" for i in range(width)]
        # una volta sola: tutto il testo della riga unito, normalizzato
        self.haystack = [normalize(" ".join(r)) for r in rows]
        self._sort_keys = {}

    def __len__(self):
        return len(self.rows)

    def col_index(self, name: str) -> int:
        return self.columns.index(name)

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
