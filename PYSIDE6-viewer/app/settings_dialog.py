"""Dialogo Impostazioni con le schede «Generale» e «Info»."""
from PySide6.QtWidgets import QTabWidget

from .modal_overlay import BaseModal
from .settings_tabs.general_tab import GeneralTab
from .settings_tabs.info_tab import InfoTab

TAB_GENERAL, TAB_INFO = 0, 1


class SettingsDialog(BaseModal):
    def __init__(self, parent, settings, tab: int = TAB_GENERAL):
        super().__init__(parent, 0.58, 0.8)
        self.tabs = QTabWidget()
        self.tabs.addTab(GeneralTab(settings, self.s), "Generale")
        self.tabs.addTab(InfoTab(self.s), "Info")
        self.tabs.setCurrentIndex(tab)
        self.body.addWidget(self.tabs, 1)
        self.add_close_button()
        self.finalize()
