"""Generazione del codice a barre Code128 come QPixmap (sorgente ad alta risoluzione)."""
import io

import barcode
from barcode.writer import ImageWriter
from PIL import Image, ImageOps
from PySide6.QtGui import QImage, QPixmap

PADDING_PX = 10  # bordo bianco aggiuntivo oltre alla quiet zone (10 moduli)


class BarcodeError(Exception):
    pass


# 0.254 mm a 300 dpi = esattamente 3 px per modulo; il testo si scrive a parte (write_text=False)
_OPTIONS = {
    "dpi": 300,
    "module_width": 0.254,
    "module_height": 8.0,
    "quiet_zone": 2.6,
    "write_text": False,
}


def render_barcode_image(data: str) -> Image.Image:
    data = (data or "").strip()
    if not data:
        raise BarcodeError("codice vuoto")
    try:
        obj = barcode.get_barcode_class("code128")(data, writer=ImageWriter())
        buf = io.BytesIO()
        obj.write(buf, options=_OPTIONS)
        buf.seek(0)
        img = Image.open(buf).convert("RGB")
        return ImageOps.expand(img, border=PADDING_PX, fill="white")
    except Exception as e:  # caratteri non supportati, ecc.
        raise BarcodeError(str(e)) from e


def barcode_source_pixmap(data: str) -> QPixmap:
    """Pixmap originale (grande, sfondo bianco). Va ridimensionato SOLO con KeepAspectRatio."""
    img = render_barcode_image(data)
    w, h = img.size
    qimg = QImage(img.tobytes(), w, h, w * 3, QImage.Format_RGB888).copy()
    return QPixmap.fromImage(qimg)
