"""Generazione di codici a barre (Code128, Code39, EAN-13, EAN-8, UPC-A, ITF, QR) come QPixmap."""
import io

import barcode
from barcode.writer import ImageWriter
from PIL import Image, ImageOps
from PySide6.QtGui import QImage, QPixmap

from .details import is_valid

PADDING_PX = 10  # bordo bianco aggiuntivo oltre alla quiet zone


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


def _render_qr(data: str) -> Image.Image:
    import qrcode
    qr = qrcode.QRCode(box_size=8, border=2, error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(data)
    qr.make(fit=True)
    return qr.make_image(fill_color="black", back_color="white").convert("RGB")


def render_barcode_image(data: str, barcode_type: str = "code128") -> Image.Image:
    data = (data or "").strip()
    if not data:
        raise BarcodeError("codice vuoto")
    if not is_valid(barcode_type, data):
        raise BarcodeError(f"valore non valido per {barcode_type}")
    try:
        if barcode_type == "qr":
            img = _render_qr(data)
        else:
            if barcode_type == "code39":
                obj = barcode.get_barcode_class("code39")(data.upper(), writer=ImageWriter(), add_checksum=False)
            else:
                obj = barcode.get_barcode_class(barcode_type)(data, writer=ImageWriter())
            buf = io.BytesIO()
            obj.write(buf, options=_OPTIONS)
            buf.seek(0)
            img = Image.open(buf).convert("RGB")
        return ImageOps.expand(img, border=PADDING_PX, fill="white")
    except BarcodeError:
        raise
    except Exception as e:  # caratteri non supportati, ecc.
        raise BarcodeError(str(e)) from e


def barcode_source_pixmap(data: str, barcode_type: str = "code128") -> QPixmap:
    """Pixmap originale (grande, sfondo bianco). Va ridimensionato SOLO con KeepAspectRatio."""
    img = render_barcode_image(data, barcode_type)
    w, h = img.size
    qimg = QImage(img.tobytes(), w, h, w * 3, QImage.Format_RGB888).copy()
    return QPixmap.fromImage(qimg)
