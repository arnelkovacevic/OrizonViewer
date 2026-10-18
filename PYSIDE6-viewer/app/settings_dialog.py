"""Dialogo Impostazioni con le schede «Generale», «File» e «Info»."""
from PySide6.QtWidgets import QTabWidget

from .modal_overlay import BaseModal
from .settings_tabs.file_tab import FileTab
from .settings_tabs.general_tab import GeneralTab
from .settings_tabs.info_tab import InfoTab

TAB_GENERAL, TAB_FILE, TAB_INFO = 0, 1, 2


class SettingsDialog(BaseModal):
    """`requested` vale "edit" se l'utente ha chiesto di modificare la configurazione
    (la finestra principale chiede il PIN e apre il wizard dopo la chiusura)."""

    def __init__(self, parent, settings, tab: int = TAB_GENERAL, file_info: dict = None, confirm_clear=None):
        super().__init__(parent, 0.58, 0.8)
        self.requested = None
        self._confirm_clear = confirm_clear
        self.tabs = QTabWidget()
        self.tabs.addTab(GeneralTab(settings, self.s), "Generale")
        self.file_tab = FileTab(self.s, file_info or {}, self._edit, self._clear)
        self.tabs.addTab(self.file_tab, "File")
        self.tabs.addTab(InfoTab(self.s), "Info")
        self.tabs.setCurrentIndex(tab)
        self.body.addWidget(self.tabs, 1)
        self.add_close_button()
        self.finalize()

    def _edit(self):
        self.requested = "edit"
        self.accept()

    def _clear(self):
        if self._confirm_clear is not None:
            self._confirm_clear()
