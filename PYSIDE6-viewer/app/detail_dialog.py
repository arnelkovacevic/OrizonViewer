"""Dialogo modale: dettaglio articolo. Dimensioni e font FISSI, calcolati una sola volta all'apertura."""
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QFontMetrics, QTextLayout, QTextOption
from PySide6.QtWidgets import QLabel, QSizePolicy

from .barcode_utils import BarcodeError, barcode_source_pixmap
from .modal_overlay import BaseModal

DESC_MAX_LINES = 3


def wrap_lines(text: str, font, width: int) -> list:
    """Righe in cui il testo va a capo alla larghezza data (anche dentro parole lunghe)."""
    lay = QTextLayout(text, font)
    opt = QTextOption()
    opt.setWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
    lay.setTextOption(opt)
    lines = []
    lay.beginLayout()
    while True:
        ln = lay.createLine()
        if not ln.isValid():
            break
        ln.setLineWidth(max(1, width))
        lines.append(text[ln.textStart():ln.textStart() + ln.textLength()].strip())
    lay.endLayout()
    return lines or [""]


def elide_to_lines(text: str, font, width: int, max_lines: int):
    """(testo su max_lines righe, troncato?) con «…» alla fine dell'ultima riga."""
    lines = wrap_lines(text, font, width)
    if len(lines) <= max_lines:
        return "\n".join(lines), False
    rest = " ".join(lines[max_lines - 1:])
    last = QFontMetrics(font).elidedText(rest, Qt.ElideRight, width)
    return "\n".join(lines[:max_lines - 1] + [last]), True


def _fixed_label(text, name, px, align=Qt.AlignCenter):
    lbl = QLabel(text, objectName=name, alignment=align)
    lbl.ensurePolished()
    f = lbl.font()
    f.setPixelSize(px)
    lbl.setFont(f)
    lbl.setStyleSheet(f"font-size: {px}px;")  # vince sulla regola globale QWidget{font-size}
    lbl.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
    return lbl


class DetailDialog(BaseModal):
    """Descrizione | LAYOUT | barcode | codice | (spazio) | Chiudi."""

    def __init__(self, parent, code: str, description: str, layout: str):
        super().__init__(parent, 0.50, 0.55, min_size=(520, 390))
        s = self.s
        code, description, layout = code.strip(), description.strip(), layout.strip()

        m = round(16 * s)
        self.body.setContentsMargins(m, m, m, m)
        self.body.setSpacing(round(8 * s))
        # larghezza utile del testo (dialogo - ombra - margini - bordo)
        text_w = max(self._target_w, self._min_w) - 2 * self.pad - 2 * m - 6

        # Descrizione: bold, max 3 righe, troncata con «…» una sola volta
        desc = _fixed_label("", "DetailDesc", max(12, round(20 * s)))
        shown, truncated = elide_to_lines(description, desc.font(), text_w, DESC_MAX_LINES)
        desc.setText(shown)
        desc.setFixedHeight(QFontMetrics(desc.font()).lineSpacing() * (shown.count("\n") + 1))
        desc.setToolTip(description if truncated else "")
        self.body.addWidget(desc)

        # LAYOUT: verde, il testo piu' grande del popup
        lay = _fixed_label("", "DetailLayout", max(20, round(48 * s)))
        fm = QFontMetrics(lay.font())
        lay.setText(fm.elidedText(layout, Qt.ElideRight, text_w))
        lay.setFixedHeight(fm.lineSpacing())
        self.body.addWidget(lay)

        # Barcode: scalato una volta (KeepAspectRatio), QLabel a dimensione fissa
        try:
            src = barcode_source_pixmap(code)
        except BarcodeError:
            src = None
            self.toast_when_shown("Impossibile generare il codice a barre")
        if src is not None:
            dpr = self.devicePixelRatioF()
            bar_w = int(self._target_w * 0.46)
            pm = src.scaled(QSize(int(bar_w * dpr), int(bar_w * dpr)), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            pm.setDevicePixelRatio(dpr)
            bar = QLabel(alignment=Qt.AlignCenter)
            bar.setPixmap(pm)
            bar.setFixedSize(round(pm.width() / dpr), round(pm.height() / dpr))
            self.body.addWidget(bar, 0, Qt.AlignHCenter)
            code_lbl = _fixed_label(code, "DetailCode", max(10, round(12 * s)))
            code_lbl.setFixedHeight(QFontMetrics(code_lbl.font()).lineSpacing())
            self.body.addWidget(code_lbl)

        self.body.addStretch(1)
        btn = self.add_close_button()
        btn.setMinimumSize(round(220 * s), max(44, round(50 * s)))
        self.finalize()
