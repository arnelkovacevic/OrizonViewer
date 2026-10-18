"""Impostazioni persistenti (QSettings): ultimo file, larghezze colonne, tema."""
import json

from PySide6.QtCore import QSettings

from . import config

_KEY_LAST_FILE = "last_file"
_KEY_WIDTHS = "column_widths"
_KEY_THEME = "theme"
_KEY_REMEMBER = "remember_last_file"


class Settings:
    def __init__(self):
        self._s = QSettings(config.ORG_NAME, "OrizonViewer")

    def last_file(self) -> str:
        return str(self._s.value(_KEY_LAST_FILE, "") or "")

    def set_last_file(self, path: str):
        self._s.setValue(_KEY_LAST_FILE, path)

    def column_widths(self) -> dict:
        """Larghezze indipendenti dalla scala (px a scala 1.0), per nome colonna."""
        try:
            data = json.loads(str(self._s.value(_KEY_WIDTHS, "{}") or "{}"))
            return {k: float(v) for k, v in data.items()}
        except (ValueError, TypeError, AttributeError):
            return {}

    def set_column_widths(self, widths: dict):
        self._s.setValue(_KEY_WIDTHS, json.dumps(widths))
        self._s.sync()

    def theme(self) -> str:
        v = str(self._s.value(_KEY_THEME, "dark") or "dark")
        return v if v in ("dark", "light") else "dark"

    def set_theme(self, name: str):
        self._s.setValue(_KEY_THEME, name)
        self._s.sync()

    def remember_last_file(self) -> bool:
        """Default: attivo."""
        return str(self._s.value(_KEY_REMEMBER, True)).lower() in ("true", "1")

    def set_remember_last_file(self, on: bool):
        self._s.setValue(_KEY_REMEMBER, bool(on))
        self._s.sync()
