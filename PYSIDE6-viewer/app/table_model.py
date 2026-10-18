"""Modello tabella (QAbstractTableModel), delegate con evidenziazione e thread di caricamento Excel."""
from PySide6.QtCore import QAbstractTableModel, QModelIndex, QRect, Qt, QThread, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication, QStyle, QStyledItemDelegate, QStyleOptionViewItem

from . import theme, xlsx_reader
from .search import Dataset, fold


class ArticleModel(QAbstractTableModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._ds = Dataset([], [])
        self._display = []  # indici (in Dataset.columns) delle colonne mostrate, nell'ordine scelto
        self._rows = []  # indici di Dataset visibili, nell'ordine mostrato
        self._sort_col = -1
        self._sort_order = Qt.AscendingOrder
        self._terms = {}  # colonna vista -> parti da evidenziare

    # ---- dati
    def set_dataset(self, ds: Dataset, display_names: list = None):
        self.beginResetModel()
        self._ds = ds
        names = display_names if display_names is not None else ds.columns
        self._display = [ds.col_index(n) for n in names]
        self._sort_col = -1
        self._rows = list(range(len(ds)))
        self._apply_sort()
        self.endResetModel()

    def dataset(self) -> Dataset:
        return self._ds

    def set_rows(self, indices: list, terms: dict = None):
        self.beginResetModel()
        self._rows = list(indices)
        self._terms = terms or {}
        self._apply_sort()
        self.endResetModel()

    def source_row(self, view_row: int) -> int:
        return self._rows[view_row]

    def row_values(self, view_row: int) -> tuple:
        return self._ds.rows[self._rows[view_row]]

    def terms_for(self, col: int) -> list:
        return self._terms.get(col, [])

    def total(self) -> int:
        return len(self._ds)

    # ---- ordinamento
    def _apply_sort(self):
        if self._sort_col < 0 or self._sort_col >= len(self._display):
            self._rows.sort()
            return
        keys = self._ds.sort_keys(self._display[self._sort_col])
        self._rows.sort(key=keys.__getitem__, reverse=self._sort_order == Qt.DescendingOrder)

    def sort(self, column, order=Qt.AscendingOrder):
        self.layoutAboutToBeChanged.emit()
        self._sort_col, self._sort_order = column, order
        self._apply_sort()
        self.layoutChanged.emit()

    # ---- interfaccia Qt
    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._display)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        if role == Qt.DisplayRole:
            return self._ds.rows[self._rows[index.row()]][self._display[index.column()]]
        if role == Qt.TextAlignmentRole:
            return int(Qt.AlignCenter)
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self._ds.columns[self._display[section]]
        return None


class HighlightDelegate(QStyledItemDelegate):
    """Disegna la cella normalmente; se ci sono termini di ricerca evidenzia le corrispondenze."""

    def paint(self, painter, option, index):
        model = index.model()
        terms = model.terms_for(index.column())
        if not terms:
            return super().paint(painter, option, index)

        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        text = opt.text
        opt.text = ""
        style = opt.widget.style() if opt.widget else QApplication.style()
        style.drawControl(QStyle.CE_ItemViewItem, opt, painter, opt.widget)

        rect = style.subElementRect(QStyle.SE_ItemViewItemText, opt, opt.widget).adjusted(4, 0, -4, 0)
        fm = opt.fontMetrics
        shown = fm.elidedText(text, Qt.ElideRight, rect.width())
        folded = fold(shown)
        spans = []
        if len(folded) == len(shown):
            for t in terms:
                start = folded.find(t)
                while start >= 0:
                    spans.append((start, start + len(t)))
                    start = folded.find(t, start + len(t))
        spans = _merge(spans)

        painter.save()
        painter.setFont(opt.font)
        total_w = fm.horizontalAdvance(shown)
        x0 = rect.x() + max(0, (rect.width() - total_w) // 2)  # testo centrato
        for a, b in spans:
            xa = x0 + fm.horizontalAdvance(shown[:a])
            wa = fm.horizontalAdvance(shown[a:b])
            painter.fillRect(QRect(xa, rect.y() + 2, wa, rect.height() - 4), theme.qcolor("hl_bg"))
        pos, x = 0, x0
        base = QColor("#FFFFFF") if opt.state & QStyle.State_Selected else theme.qcolor("text")
        for a, b in spans + [(len(shown), len(shown))]:
            for seg, color in ((shown[pos:a], base), (shown[a:b], theme.qcolor("hl_fg"))):
                if seg:
                    painter.setPen(color)
                    w = fm.horizontalAdvance(seg)
                    painter.drawText(QRect(x, rect.y(), w + 2, rect.height()), Qt.AlignVCenter | Qt.AlignLeft, seg)
                    x += w
            pos = b
        painter.restore()


def _merge(spans):
    spans.sort()
    out = []
    for a, b in spans:
        if out and a <= out[-1][1]:
            out[-1] = (out[-1][0], max(out[-1][1], b))
        else:
            out.append((a, b))
    return out


class ExcelLoader(QThread):
    """Legge l'Excel fuori dal thread UI: solo le colonne necessarie, tutto come testo."""

    loaded = Signal(object, object)  # Dataset, Profile
    failed = Signal(str)

    def __init__(self, profile, parent=None):
        super().__init__(parent)
        self.profile = profile

    def run(self):
        try:
            p = self.profile
            ds = xlsx_reader.load_dataset(p.path, p.sheet, p.header_row, p.needed_columns())
            self.loaded.emit(ds, p)
        except Exception as e:
            self.failed.emit(str(e))
