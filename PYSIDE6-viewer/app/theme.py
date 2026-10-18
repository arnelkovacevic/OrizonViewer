"""Temi (scura / chiara): token colore in un unico posto; lo stylesheet è generato da styles.qss."""
import os
import re

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from . import config

ACCENT = "#0A8799"

_COMMON = {
    "accent": ACCENT,
    "accent_hover": "#0F9FB4",
    "accent_press": "#076170",
    "accent_edge": "#064F5B",
    "primary": "#1E3D58",
    "primary_hover": "#2A5378",
    "primary_press": "#17304A",
    "primary_border": "#2C4F6E",
    "icon_hover": "#2E5C85",
    "icon_hover_border": "#5FA3D6",
    "header_bg": "#1E3D58",
    "header_hover": "#2A5378",
    "sel": "#2F6FA5",
    "hl_bg": "#F2B544",
    "hl_fg": "#10161C",
}

THEMES = {
    "dark": {
        **_COMMON,
        "bg": "#0F1822",
        "text": "#E8EEF4",
        "text_strong": "#FFFFFF",
        "muted": "#8FA3B5",
        "muted2": "#A9BCCD",
        "faint": "#6E8091",
        "surface": "#162433",
        "surface_alt": "#1A2A3A",
        "border": "#2C4358",
        "border_hover": "#3B5D7C",
        "table_bg": "#131F2B",
        "table_alt": "#1A2A3A",
        "grid": "#34506A",
        "card_bg": "#162433",
        "modal_bg": "#22394F",
        "overlay": "rgba(0, 0, 0, 140)",
        "divider": "rgba(10, 135, 153, 170)",
        "scroll_track": "#0F1822",
        "scroll_handle": "#3B5D7C",
        "scroll_handle_hover": "#4C7FA8",
        "dis_bg": "#243341",
        "dis_text": "#6E8091",
        "sec_bg": "#2B3A49",
        "sec_hover": "#384B5E",
        "key_bg": "#2B4259",
        "key_hover": "#365472",
        "key_text": "#FFFFFF",
        "tab_bg": "#1A2A3A",
        "tab_hover": "#24394D",
        "toggle_off": "#44586B",
        "tooltip_bg": "#162433",
        "layout_green": "#3DDC84",
        "hl_verde": "#3DDC84",
        "hl_blu": "#5AB0FF",
        "hl_arancione": "#FFA640",
        "hl_neutro": "#FFFFFF",
        "warn": "#FFB454",
        "danger_text": "#FF7B7F",
        "shadow": "#000000",
    },
    "light": {
        **_COMMON,
        "bg": "#EAF0F5",
        "text": "#14212D",
        "text_strong": "#0B1620",
        "muted": "#566B7D",
        "muted2": "#40576B",
        "faint": "#76899A",
        "surface": "#FFFFFF",
        "surface_alt": "#E3EBF2",
        "border": "#BFCDD9",
        "border_hover": "#8FA7BA",
        "table_bg": "#FFFFFF",
        "table_alt": "#EAF1F7",
        "grid": "#C3D0DC",
        "card_bg": "#F7FAFC",
        "modal_bg": "#FFFCF6",
        "overlay": "rgba(0, 0, 0, 140)",
        "divider": "rgba(10, 135, 153, 150)",
        "scroll_track": "#EAF0F5",
        "scroll_handle": "#A9BCCD",
        "scroll_handle_hover": "#8FA7BA",
        "dis_bg": "#D5DEE6",
        "dis_text": "#8697A6",
        "sec_bg": "#D5DEE6",
        "sec_hover": "#C5D2DD",
        "key_bg": "#DCE6EE",
        "key_hover": "#CBD9E5",
        "key_text": "#14212D",
        "tab_bg": "#DCE6EE",
        "tab_hover": "#CBD9E5",
        "toggle_off": "#A9B9C7",
        "tooltip_bg": "#FFFFFF",
        "layout_green": "#12853F",
        "hl_verde": "#12853F",
        "hl_blu": "#1769C9",
        "hl_arancione": "#C75F00",
        "hl_neutro": "#0B1620",
        "warn": "#B35A00",
        "danger_text": "#C1272D",
        "shadow": "#000000",
    },
}

_current = "dark"


class _Notifier(QObject):
    changed = Signal(str)


notifier = _Notifier()


def current() -> str:
    return _current


def tokens() -> dict:
    return THEMES[_current]


_PX = re.compile(r"\{(\d+(?:\.\d+)?)\}")
_TOKEN = re.compile(r"\$([a-z0-9_]+)")


def build_stylesheet(name: str, scale: float) -> str:
    """styles.qss: $token -> colore del tema, {N} -> N*scala px."""
    t = THEMES[name]
    with open(config.resource_path(os.path.join("app", "styles.qss")), encoding="utf-8") as f:
        qss = f.read()
    qss = _TOKEN.sub(lambda m: t[m.group(1)], qss)
    quote = lambda fams: ", ".join(f'"{f}"' for f in fams)
    qss = qss.replace('UIFONTS', quote(config.ui_fonts())).replace('MONOFONTS', quote(config.mono_fonts()))
    for key, fname in (('CHECKICON', 'check.svg'), ('CHEVRONICON', 'chevron.svg')):
        qss = qss.replace(key, config.resource_path(os.path.join(config.ICON_DIR, fname)).replace('\\', '/'))
    return _PX.sub(lambda m: str(max(1, round(float(m.group(1)) * scale))), qss)


def apply_theme(app, name: str):
    """Applica il tema subito a tutta l'applicazione."""
    global _current
    _current = name if name in THEMES else "dark"
    scale = float(app.property("ui_scale") or 1.0)
    app.setStyleSheet(build_stylesheet(_current, scale))
    notifier.changed.emit(_current)


def svg_pixmap(path: str, color: str, size: int, dpr: float = 1.0) -> QPixmap:
    """Disegna un'icona SVG (tratti #FFFFFF) nel colore richiesto."""
    with open(path, encoding="utf-8") as f:
        svg = f.read().replace("#FFFFFF", color)
    renderer = QSvgRenderer(svg.encode("utf-8"))
    px = max(1, int(size * dpr))
    img = QImage(px, px, QImage.Format_ARGB32_Premultiplied)
    img.fill(Qt.transparent)
    p = QPainter(img)
    renderer.render(p)
    p.end()
    pm = QPixmap.fromImage(img)
    pm.setDevicePixelRatio(dpr)
    return pm


def qcolor(token: str) -> QColor:
    return QColor(tokens()[token])
