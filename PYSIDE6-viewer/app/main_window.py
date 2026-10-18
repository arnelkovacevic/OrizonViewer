"""Finestra principale in modalità kiosk."""
import os

from PySide6.QtCore import QDateTime, QEvent, QSize, QTimer, Qt, Signal
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QFileDialog, QFrame, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QProgressBar, QPushButton, QStackedLayout, QTableView, QVBoxLayout, QWidget,
)

from . import config, theme
from .detail_dialog import DetailDialog
from .pin_dialog import PinDialog
from .settings import Settings
from .settings_dialog import TAB_GENERAL, TAB_INFO, SettingsDialog
from .table_model import ArticleModel, ExcelLoader, HighlightDelegate
from .toast import show_toast


class ArticleTable(QTableView):
    """QTableView che segnala l'attivazione di una riga con doppio clic o Invio."""

    rowActivated = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.doubleClicked.connect(lambda idx: self.rowActivated.emit(idx.row()))

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_Return, Qt.Key_Enter) and self.currentIndex().isValid():
            self.rowActivated.emit(self.currentIndex().row())
            return
        super().keyPressEvent(e)


def fmt_int(n: int) -> str:
    return f"{n:,}".replace(",", ".")


class MainWindow(QWidget):
    def __init__(self, scale: float):
        super().__init__(None, Qt.Window | Qt.FramelessWindowHint)
        self.s = scale
        self.settings = Settings()
        self._allow_close = False
        self._pin_open = False
        self._loader = None
        self._saved_widths = self.settings.column_widths()
        self.setWindowTitle(config.APP_NAME)

        self.model = ArticleModel(self)
        self._build_ui()

        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(config.SEARCH_DEBOUNCE_MS)
        self._debounce.timeout.connect(self.apply_filters)

        self._width_timer = QTimer(self)
        self._width_timer.setSingleShot(True)
        self._width_timer.setInterval(400)
        self._width_timer.timeout.connect(self._save_widths)

    # ------------------------------------------------------------ UI
    def _px(self, v):
        return round(v * self.s)

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.content = QWidget()  # tutto il contenuto: bersaglio della sfocatura quando c'e' un modale
        self.blur_target = self.content
        outer.addWidget(self.content)
        root = QVBoxLayout(self.content)
        m = self._px(20)
        root.setContentsMargins(m, self._px(12), m, self._px(14))
        root.setSpacing(self._px(12))

        # intestazione: orologio | ricerca + Nuova Ricerca | icone | logo
        head = QHBoxLayout()
        head.setSpacing(self._px(10))

        clock = QVBoxLayout()
        clock.setSpacing(0)
        self.clock_time = QLabel("--:--:--", objectName="ClockTime")
        self.clock_date = QLabel("--/--/----", objectName="ClockDate")
        clock.addWidget(self.clock_time)
        clock.addWidget(self.clock_date)
        head.addLayout(clock)

        self.search = QLineEdit(objectName="MainSearch")
        self.search.setPlaceholderText("Cerca...  (usa % o spazio per più parole)")
        self.search.setClearButtonEnabled(True)
        self.search.returnPressed.connect(self._enter_in_search)
        self.search.textChanged.connect(self._debounce_filters)
        head.addWidget(self.search, 1)
        self.new_btn = QPushButton("Nuova Ricerca", objectName="AccentButton")
        self.new_btn.setCursor(Qt.PointingHandCursor)
        self.new_btn.setMinimumSize(self._px(180), max(self._px(48), 44))
        self.new_btn.clicked.connect(self.reset_search)
        head.addWidget(self.new_btn)

        self.settings_btn = self._icon_button("settings.svg", "Impostazioni", self.open_settings)
        self.import_btn = self._icon_button("import.svg", "Importa file", self.import_excel)
        self.exit_btn = self._icon_button("power.svg", "Esci", self.request_exit, danger=True)
        for b in (self.settings_btn, self.import_btn, self.exit_btn):
            head.addWidget(b)

        self.logo = QLabel(cursor=Qt.PointingHandCursor)
        pm = QPixmap(config.resource_path(config.LOGO_FILE))
        if not pm.isNull():
            dpr = self.devicePixelRatioF()
            pm = pm.scaledToHeight(self._px(40) * round(dpr), Qt.SmoothTransformation)
            pm.setDevicePixelRatio(dpr)
            self.logo.setPixmap(pm)
        self.logo.mousePressEvent = lambda e: self.open_settings(TAB_INFO)
        head.addWidget(self.logo)
        root.addLayout(head)

        root.addSpacing(self._px(2))
        divider = QFrame(objectName="Divider")
        divider.setFixedHeight(max(2, self._px(2)))
        root.addWidget(divider)
        root.addSpacing(self._px(8))

        self._clock_timer = QTimer(self)
        self._clock_timer.setInterval(1000)
        self._clock_timer.timeout.connect(self._tick_clock)
        self._clock_timer.start()
        self._tick_clock()

        # tabella
        self.table = ArticleTable()
        self.table.setModel(self.model)
        self.table.setItemDelegate(HighlightDelegate(self.table))
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setWordWrap(False)
        self.table.setTextElideMode(Qt.ElideRight)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(self._px(40))
        self.table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        font = self.table.font()
        font.setPixelSize(self._px(18))
        self.table.setFont(font)
        self.table.rowActivated.connect(self.show_detail)

        hdr = self.table.horizontalHeader()
        hdr.setSortIndicatorShown(True)
        hdr.setSectionsClickable(True)
        hdr.setMinimumSectionSize(self._px(60))
        hdr.setStretchLastSection(False)
        defaults = {0: 230, 2: 260, 3: 130}
        for c in range(self.model.columnCount()):
            if c == config.STRETCH_VIEW_COLUMN:
                hdr.setSectionResizeMode(c, QHeaderView.Stretch)
            else:
                hdr.setSectionResizeMode(c, QHeaderView.Interactive)
                name = self.model.headerData(c, Qt.Horizontal)
                w = self._saved_widths.get(name, defaults.get(c, 150))
                hdr.resizeSection(c, self._px(w))
        hdr.sectionResized.connect(self._on_section_resized)
        self.table.setSortingEnabled(True)
        hdr.setSortIndicator(-1, Qt.AscendingOrder)  # nessun ordinamento iniziale

        # card della tabella: pagina 0 = tabella, pagina 1 = stato vuoto
        self.card = QFrame(objectName="TableCard")
        self.stack = QStackedLayout(self.card)
        pad = self._px(10)
        self.stack.setContentsMargins(pad, pad, pad, pad)
        self.stack.addWidget(self.table)
        self.stack.addWidget(self._build_empty_state())
        root.addWidget(self.card, 1)

        # contatore + stato caricamento
        info = QHBoxLayout()
        self.counter = QLabel("0 / 0 articoli", objectName="Counter")
        info.addWidget(self.counter)
        info.addStretch(1)
        self.loading_label = QLabel("Caricamento...", objectName="Counter")
        self.loading_label.hide()
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(False)
        self.progress.setFixedWidth(self._px(180))
        self.progress.hide()
        info.addWidget(self.loading_label)
        info.addWidget(self.progress)
        root.addLayout(info)

        self.version_label = QLabel(f"v.{config.APP_VERSION}", objectName="Version")
        info.addSpacing(self._px(16))
        info.addWidget(self.version_label, 0, Qt.AlignRight | Qt.AlignVCenter)

    def _build_empty_state(self):
        page = QWidget(objectName="EmptyState")
        lay = QVBoxLayout(page)
        lay.setSpacing(self._px(10))
        lay.addStretch(1)
        self.empty_icon = QLabel(alignment=Qt.AlignCenter)
        lay.addWidget(self.empty_icon)
        title = QLabel("Nessun file caricato", objectName="EmptyTitle", alignment=Qt.AlignCenter)
        sub = QLabel("Importa un file Excel per visualizzare la tabella", objectName="EmptySub",
                     alignment=Qt.AlignCenter)
        sub.setWordWrap(True)
        lay.addWidget(title)
        lay.addWidget(sub)
        lay.addSpacing(self._px(10))
        btn = QPushButton("Importa file", objectName="AccentButton")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setMinimumSize(self._px(220), max(self._px(52), 44))
        btn.clicked.connect(self.import_excel)
        self.empty_btn = btn
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(btn)
        row.addStretch(1)
        lay.addLayout(row)
        lay.addStretch(1)
        self._update_empty_icon()
        theme.notifier.changed.connect(lambda _n: self._update_empty_icon())
        return page

    def _update_empty_icon(self):
        size = self._px(84)
        path = config.resource_path(os.path.join(config.ICON_DIR, "file.svg"))
        self.empty_icon.setPixmap(theme.svg_pixmap(path, theme.tokens()["muted"], size, self.devicePixelRatioF()))

    def _refresh_state(self):
        """Stato vuoto (nessun file) o tabella; ricerca attiva solo con dati."""
        has = self.model.total() > 0
        self.search.setEnabled(has)
        self.new_btn.setEnabled(has)
        self.stack.setCurrentIndex(0 if (has or self._loader is not None) else 1)
        if not has:
            self.counter.setText("0 articoli")

    def _icon_button(self, icon_file, tooltip, slot, danger=False):
        btn = QPushButton(objectName="IconButton")
        btn.setProperty("danger", danger)
        btn.setToolTip(tooltip)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFocusPolicy(Qt.NoFocus)
        size = max(self._px(40), 44)  # minimo ~44 px per il tocco
        btn.setFixedSize(size, size)
        btn.setIcon(QIcon(config.resource_path(os.path.join(config.ICON_DIR, icon_file))))
        btn.setIconSize(QSize(round(size * 0.55), round(size * 0.55)))
        btn.clicked.connect(lambda _=False: slot())
        return btn

    def _tick_clock(self):
        now = QDateTime.currentDateTime()
        self.clock_time.setText(now.toString("HH:mm:ss"))
        self.clock_date.setText(now.toString("dd/MM/yyyy"))

    def open_settings(self, tab=TAB_GENERAL):
        SettingsDialog(self, self.settings, tab if isinstance(tab, int) else TAB_GENERAL).exec()

    # ------------------------------------------------------------ kiosk
    def show_kiosk(self):
        self.showFullScreen()
        self.raise_()
        self.activateWindow()
        QTimer.singleShot(0, self.autoload)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            e.ignore()  # Esc non esce dal fullscreen
            return
        super().keyPressEvent(e)

    def changeEvent(self, e):
        super().changeEvent(e)
        if e.type() == QEvent.WindowStateChange and not self.isFullScreen() and not self._allow_close:
            QTimer.singleShot(0, self.showFullScreen)  # ripristina il fullscreen

    def closeEvent(self, e):
        if self._allow_close:
            self._save_widths()
            e.accept()
            return
        e.ignore()  # X / Alt+F4 / Cmd+Q: serve il PIN
        QTimer.singleShot(0, self.request_exit)

    def request_exit(self):
        if self._pin_open:
            return
        self._pin_open = True
        try:
            ok = PinDialog.ask(self, "PIN per uscire")
        finally:
            self._pin_open = False
        if ok:
            self._allow_close = True
            self.close()
            QApplication.instance().quit()

    # ------------------------------------------------------------ Excel
    def autoload(self):
        """Apre solo l'ultimo file dell'utente (se l'opzione e' attiva); altrimenti stato vuoto."""
        self._refresh_state()
        if not self.settings.remember_last_file():
            return
        path = self.settings.last_file()
        if not path:
            return
        if not os.path.isfile(path):
            show_toast(self, f"File non trovato: {os.path.basename(path)}", "error", 4000)
            return
        self.load_file(path)

    def import_excel(self):
        if self._loader is not None:
            return
        if not PinDialog.ask(self, "PIN per importare"):
            return
        start = os.path.dirname(self.settings.last_file()) or os.path.expanduser("~")
        path, _ = QFileDialog.getOpenFileName(
            self, "Seleziona un file Excel", start, "File Excel (*.xlsx)"
        )
        if path:
            self.load_file(path)

    def load_file(self, path: str):
        if self._loader is not None:
            return
        self._loader = ExcelLoader(path, self)
        self._set_loading(True)
        self._loader.loaded.connect(self._on_loaded)
        self._loader.failed.connect(self._on_failed)
        self._loader.finished.connect(self._on_loader_finished)
        self._loader.start()

    def _set_loading(self, on: bool):
        self.loading_label.setVisible(on)
        self.progress.setVisible(on)
        self.import_btn.setEnabled(not on)
        self.empty_btn.setEnabled(not on)
        self._refresh_state()

    def _on_loaded(self, dataset, path):
        self.model.set_dataset(dataset)
        self.settings.set_last_file(path)
        self.apply_filters()
        self._refresh_state()
        show_toast(self, f"Caricati {fmt_int(len(dataset))} articoli", "success", 1800)

    def _on_failed(self, message):
        show_toast(self, f"Errore durante l'importazione: {message[:160]}", "error", 5000)

    def _on_loader_finished(self):
        self._loader.deleteLater()
        self._loader = None
        self._set_loading(False)

    # ------------------------------------------------------------ ricerca
    def _debounce_filters(self):
        self._debounce.start()

    def apply_filters(self):
        from .search import parse_query
        query = self.search.text()
        rows = self.model.dataset().search(query)
        parts = parse_query(query)
        self.model.set_rows(rows, {c: parts for c in range(self.model.columnCount())})
        self.table.scrollToTop()
        if self.model.total() == 0:
            self.counter.setText("0 articoli")
        else:
            self.counter.setText(f"{fmt_int(len(rows))} / {fmt_int(self.model.total())} articoli")

    def reset_search(self):
        self._debounce.stop()
        self.search.blockSignals(True)
        self.search.clear()
        self.search.blockSignals(False)
        self.apply_filters()
        self.search.setFocus()

    def _enter_in_search(self):
        """Invio nel campo principale: con un solo risultato (es. lettore barcode) apre il dettaglio."""
        self._debounce.stop()
        self.apply_filters()
        if self.model.rowCount() == 1:
            self.show_detail(0)
        elif self.model.rowCount() > 1:
            self.table.setFocus()
            self.table.selectRow(0)

    # ------------------------------------------------------------ dettaglio
    def show_detail(self, view_row: int):
        if view_row < 0 or view_row >= self.model.rowCount():
            return
        v = self.model.row_values(view_row)
        DetailDialog(self, v[config.ALL_COLUMNS.index("Codice Prodotto")],
                     v[config.ALL_COLUMNS.index("Descrizione Libera")],
                     v[config.ALL_COLUMNS.index("LAYOUT")]).exec()

    # ------------------------------------------------------------ larghezze colonne
    def _on_section_resized(self, idx, old, new):
        if idx != config.STRETCH_VIEW_COLUMN:
            name = self.model.headerData(idx, Qt.Horizontal)
            self._saved_widths[name] = new / self.s
            self._width_timer.start()

    def _save_widths(self):
        self.settings.set_column_widths(self._saved_widths)
