"""Costanti, percorsi risorse e scala UI. Nessuna credenziale: l'account e' in app/auth.py."""
import os
import sys

APP_NAME = "Orizon Viewer"
ORG_NAME = "Orizon-AIX"
APP_VERSION = "1.2.0"
COPYRIGHT_YEAR = "2026"

LOGO_FILE = os.path.join("assets", "Orizon-com.jpg")
ICON_FILE = os.path.join("assets", "orizon.ico")
ICON_DIR = os.path.join("assets", "icons")
_UI_FONTS = ["Helvetica Neue", "Helvetica", "Segoe UI", "SF Pro Text", "Arial", "DejaVu Sans"]
_MONO_FONTS = ["Menlo", "Consolas", "Courier New", "DejaVu Sans Mono"]


def _installed(candidates, fallback):
    """Solo famiglie realmente installate: una famiglia mancante rallenta l'avvio e stampa un avviso Qt."""
    from PySide6.QtGui import QFontDatabase
    found = [f for f in candidates if QFontDatabase.hasFamily(f)]
    return found or [fallback]


def ui_fonts() -> list:
    return _installed(_UI_FONTS, "Arial")


def mono_fonts() -> list:
    return _installed(_MONO_FONTS, "Courier New")

PREVIEW_ROWS = 200  # righe lette per l'anteprima del wizard e l'analisi dei codici

SEARCH_DEBOUNCE_MS = 150
FULLSCREEN_SETTLE_MS = 150       # attesa prima di ultimo file / wizard
FULLSCREEN_SETTLE_MS_MAC = 300


def app_dir() -> str:
    """Cartella PYSIDE6-viewer (o _MEIPASS dentro l'exe)."""
    base = getattr(sys, "_MEIPASS", None)
    return base or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def resource_path(relative_path: str) -> str:
    return os.path.join(app_dir(), relative_path)


# ---------------------------------------------------------------- scala UI
def compute_scale(screen) -> float:
    """Fattore di scala dalla geometria logica dello schermo (1024x600 ... 4K)."""
    g = screen.geometry()
    f = min(g.width() / 1280.0, g.height() / 720.0)
    return max(0.8, min(f, 2.5))
