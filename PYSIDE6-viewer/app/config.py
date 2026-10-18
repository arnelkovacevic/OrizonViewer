"""Costanti, credenziali (solo hash SHA-256), percorsi risorse e scala UI."""
import hashlib
import hmac
import os
import sys

APP_NAME = "Orizon Viewer"
ORG_NAME = "Orizon-AIX"
APP_VERSION = "1.1.0"
COPYRIGHT_YEAR = "2026"

# Solo hash SHA-256: nessuna credenziale in chiaro nel codice.
USERNAME_HASH = "426a3d9667ccff155ef850dcba1a06d58a9c7d5811019d42d45c25d4d1bd10a1"
PASSWORD_HASH = "ee09198e46224875cf39928511ef2b855895c43ee86d1de894ee82bc7c990afa"
PIN_HASH = "ee09198e46224875cf39928511ef2b855895c43ee86d1de894ee82bc7c990afa"

LOGO_FILE = os.path.join("assets", "Orizon-com.jpg")
ICON_DIR = os.path.join("assets", "icons")
FONT_FAMILIES = ["Helvetica Neue", "Helvetica", "Segoe UI", "SF Pro Text", "Arial", "sans-serif"]

PREVIEW_ROWS = 200  # righe lette per l'anteprima del wizard e l'analisi dei codici

SEARCH_DEBOUNCE_MS = 150


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def verify(plain: str, hashed: str) -> bool:
    return hmac.compare_digest(sha256_hex(plain), hashed)


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
