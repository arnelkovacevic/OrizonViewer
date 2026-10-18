"""Popup «dettagli articolo» costruito dal profilo. Dimensioni e font FISSI, calcolati una sola volta."""
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QFontMetrics, QTextLayout, QTextOption
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget

from . import theme
from .barcode_utils import BarcodeError, barcode_source_pixmap
from .details import ABOVE_PX, HL_PX, TYPE_SHORT, DetailSpec, is_valid
from .modal_overlay import BaseModal, app_scale

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


def fixed_label(text, name, px, color=None, align=Qt.AlignCenter):
    """QLabel con font in pixel fisso (lo stylesheet locale vince su quello globale) e altezza non espandibile."""
    lbl = QLabel(text, objectName=name, alignment=align)
    lbl.ensurePolished()
    f = lbl.font()
    f.setPixelSize(px)
    lbl.setFont(f)
    css = f"font-size: {px}px;"
    if color:
        css += f" color: {color};"
    lbl.setStyleSheet(css)
    lbl.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
    return lbl


class DetailContent(QWidget):
    """Contenuto del popup: testo sopra | testo evidenziato | codice a barre | codice.
    Usato dal dialogo e (in scala ridotta) dall'anteprima del wizard."""

    def __init__(self, scale, text_w, box_w, box_h, spec: DetailSpec, code, above, highlight, dpr=1.0, parent=None):
        super().__init__(parent)
        self.setObjectName("TabPage")
        self.invalid = False
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(max(3, round(8 * scale)))
        code, above, highlight = (code or "").strip(), (above or "").strip(), (highlight or "").strip()

        if spec.above_col and above:
            px = max(9, round(ABOVE_PX[spec.above_size] * scale))
            lbl = fixed_label("", "DetailDesc", px)
            shown, truncated = elide_to_lines(above, lbl.font(), text_w, DESC_MAX_LINES)
            lbl.setText(shown)
            lbl.setFixedHeight(QFontMetrics(lbl.font()).lineSpacing() * (shown.count("\n") + 1))
            lbl.setToolTip(above if truncated else "")
            lay.addWidget(lbl)

        if spec.hl_col and highlight:
            px = max(12, round(HL_PX[spec.hl_size] * scale))
            color = theme.tokens()["hl_" + spec.hl_color]
            lbl = fixed_label("", "DetailLayout", px, color)
            fm = QFontMetrics(lbl.font())
            lbl.setText(fm.elidedText(highlight, Qt.ElideRight, text_w))
            lbl.setFixedHeight(fm.lineSpacing())
            lay.addWidget(lbl)

        if spec.enabled and spec.code_col and code:
            self._add_code(lay, scale, text_w, box_w, box_h, spec, code, dpr)

    def _add_code(self, lay, scale, text_w, box_w, box_h, spec, code, dpr):
        pm = None
        if is_valid(spec.barcode_type, code):
            try:
                src = barcode_source_pixmap(code, spec.barcode_type)
                # scala UNA volta, sempre con KeepAspectRatio
                pm = src.scaled(QSize(int(box_w * dpr), int(box_h * dpr)), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                pm.setDevicePixelRatio(dpr)
            except BarcodeError:
                pm = None
        if pm is not None:
            bar = QLabel(alignment=Qt.AlignCenter)
            bar.setPixmap(pm)
            bar.setFixedSize(round(pm.width() / dpr), round(pm.height() / dpr))
            lay.addWidget(bar, 0, Qt.AlignHCenter)
            lbl = fixed_label(code, "DetailCode", max(8, round(12 * scale)))
            lbl.setFixedHeight(QFontMetrics(lbl.font()).lineSpacing())
            lay.addWidget(lbl)
        else:
            self.invalid = True
            big = fixed_label("", "DetailInvalidCode", max(12, round(34 * scale)))
            fm = QFontMetrics(big.font())
            big.setText(fm.elidedText(code.upper(), Qt.ElideRight, text_w))
            big.setFixedHeight(fm.lineSpacing())
            lay.addWidget(big)
            msg = fixed_label(f"Codice non valido per {TYPE_SHORT.get(spec.barcode_type, spec.barcode_type)}",
                              "DetailInvalidMsg", max(9, round(15 * scale)))
            msg.setFixedHeight(QFontMetrics(msg.font()).lineSpacing())
            lay.addWidget(msg)


class DetailDialog(BaseModal):
    """Popup articolo: contenuto da profilo + stretch + Chiudi."""

    def __init__(self, parent, spec: DetailSpec, code: str, above: str, highlight: str):
        super().__init__(parent, 0.50, 0.55, min_size=(520, 390))
        s = self.s
        m = round(16 * s)
        self.body.setContentsMargins(m, m, m, m)
        self.body.setSpacing(round(8 * s))
        text_w = max(self._target_w, self._min_w) - 2 * self.pad - 2 * m - 6
        bar_w = int(max(self._target_w, self._min_w) * 0.46)
        qr_h = int(max(self._target_h, self._min_h) * 0.34)
        box_h = qr_h if spec.barcode_type == "qr" else bar_w
        self.content = DetailContent(s, text_w, bar_w, box_h, spec, code, above, highlight, self.devicePixelRatioF())
        self.body.addWidget(self.content, 0, Qt.AlignHCenter)
        self.body.addStretch(1)
        btn = self.add_close_button()
        btn.setMinimumSize(round(220 * s), max(44, round(50 * s)))
        self.finalize()


class NoDetailsDialog(BaseModal):
    """Info: i dettagli non sono attivi nel profilo corrente."""

    def __init__(self, parent):
        super().__init__(parent, width_px=round(520 * app_scale()))
        s = self.s
        self.open_settings = False
        self.body.setSpacing(round(18 * s))
        title = QLabel("Dettagli non attivi", objectName="DialogTitle", alignment=Qt.AlignCenter)
        text = QLabel("Dettagli non attivi. Attivali in Impostazioni → File → Modifica configurazione.",
                      objectName="WizardInfo", alignment=Qt.AlignCenter)
        text.setWordWrap(True)
        self.body.addWidget(title)
        self.body.addWidget(text)
        row = QHBoxLayout()
        row.setSpacing(round(12 * s))
        close = QPushButton("Chiudi", objectName="SecondaryButton")
        close.clicked.connect(self.reject)
        go = QPushButton("Apri impostazioni", objectName="AccentButton")
        go.clicked.connect(self._go)
        for b in (close, go):
            b.setMinimumHeight(max(44, round(50 * s)))
            row.addWidget(b)
        self.body.addLayout(row)
        self.finalize()

    def _go(self):
        self.open_settings = True
        self.accept()
