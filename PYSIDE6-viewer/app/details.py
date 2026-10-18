"""Impostazioni del popup «dettagli articolo» (senza Qt) + validazione dei codici a barre."""
from dataclasses import asdict, dataclass
from typing import Optional

# (id, etichetta nel wizard, nome breve per i messaggi)
BARCODE_TYPES = [
    ("code128", "Code128 (consigliato)", "Code128"),
    ("code39", "Code39", "Code39"),
    ("ean13", "EAN-13", "EAN-13"),
    ("ean8", "EAN-8", "EAN-8"),
    ("upca", "UPC-A", "UPC-A"),
    ("itf", "ITF", "ITF"),
    ("qr", "QR Code", "QR Code"),
]
TYPE_SHORT = {t[0]: t[2] for t in BARCODE_TYPES}

# (id, etichetta, pixel base a scala 1.0)
ABOVE_SIZES = [("piccolo", "Piccolo", 16), ("medio", "Medio", 20), ("grande", "Grande", 26)]
HL_SIZES = [("medio", "Medio", 36), ("grande", "Grande", 48), ("molto_grande", "Molto grande", 64)]
HL_COLORS = [("verde", "Verde"), ("blu", "Blu"), ("arancione", "Arancione"), ("neutro", "Bianco / Nero")]
ABOVE_PX = {k: px for k, _l, px in ABOVE_SIZES}
HL_PX = {k: px for k, _l, px in HL_SIZES}

_CODE39_CHARS = set("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ -.$/+%")


@dataclass
class DetailSpec:
    enabled: bool = False
    code_col: Optional[str] = None
    barcode_type: str = "code128"
    above_col: Optional[str] = None
    above_size: str = "medio"
    hl_col: Optional[str] = None
    hl_size: str = "grande"
    hl_color: str = "verde"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "DetailSpec":
        known = {k: v for k, v in (d or {}).items() if k in cls.__dataclass_fields__}
        spec = cls(**known)
        if spec.barcode_type not in TYPE_SHORT:
            spec.barcode_type = "code128"
        if spec.above_size not in ABOVE_PX:
            spec.above_size = "medio"
        if spec.hl_size not in HL_PX:
            spec.hl_size = "grande"
        if spec.hl_color not in dict(HL_COLORS):
            spec.hl_color = "verde"
        return spec

    def used_columns(self) -> list:
        """Colonne del foglio necessarie al popup."""
        return [c for c in (self.code_col, self.above_col, self.hl_col) if c]

    def drop_missing(self, names) -> "DetailSpec":
        """Copia in cui le colonne non piu' presenti nel foglio sono azzerate."""
        d = self.to_dict()
        for k in ("code_col", "above_col", "hl_col"):
            if d[k] not in names:
                d[k] = None
        if d["code_col"] is None:
            d["enabled"] = False
        return DetailSpec.from_dict(d)


def _ean_checksum_ok(digits: str) -> bool:
    nums = [int(c) for c in digits]
    total = sum(n * (3 if i % 2 == len(nums) % 2 else 1) for i, n in enumerate(nums[:-1]))
    return (10 - total % 10) % 10 == nums[-1]


def _numeric_ok(text: str, n: int) -> bool:
    """n cifre con checksum corretto, oppure n-1 cifre (checksum calcolato dal generatore)."""
    if not text.isascii() or not text.isdigit():
        return False
    if len(text) == n - 1:
        return True
    return len(text) == n and _ean_checksum_ok(text)


def is_valid(barcode_type: str, text: str) -> bool:
    text = (text or "").strip()
    if not text:
        return False
    if barcode_type == "code128":
        return all(32 <= ord(c) < 127 for c in text)
    if barcode_type == "code39":
        return all(c in _CODE39_CHARS for c in text.upper())
    if barcode_type == "ean13":
        return _numeric_ok(text, 13)
    if barcode_type == "ean8":
        return _numeric_ok(text, 8)
    if barcode_type == "upca":
        return _numeric_ok(text, 12)
    if barcode_type == "itf":
        return text.isascii() and text.isdigit()
    if barcode_type == "qr":
        return True
    return False


def suggest_type(values) -> str:
    """EAN-13 se tutti i valori hanno 12/13 cifre, altrimenti Code128."""
    vals = [str(v).strip() for v in values if str(v).strip()][:200]
    if vals and all(v.isascii() and v.isdigit() and len(v) in (12, 13) for v in vals):
        return "ean13"
    return "code128"


def count_invalid(barcode_type: str, values):
    """(non validi, totali) sui primi ~200 valori non vuoti."""
    vals = [str(v).strip() for v in values if str(v).strip()][:200]
    return sum(1 for v in vals if not is_valid(barcode_type, v)), len(vals)
