from datetime import date
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QPainter, QFontMetrics, QIcon
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QFrame, QPushButton, QSizePolicy
from core.models import JournalEntry

_BG = "#181818"
_SIDEBAR_BG = _BG
_CARD_HOV = "rgba(255,255,255,0.025)"
_CARD_SEL = "#2D2036"
_BORDER_SEL = "#B48EAD"
_DIVIDER = "rgba(255,255,255,0.05)"
_T_PRI = "#ffffff"
_T_SEC = "#ffffff"
_T_DIM = "#ffffff"
_T_TER = "#ffffff"
_MONO = "Consolas"
_SIDEBAR_W = 236

class ElidedLabel(QLabel):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setMinimumWidth(1)
        self._text = text

    def setText(self, text: str) -> None:
        self._text = text
        self._update_elided()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_elided()

    def _update_elided(self):
        metrics = self.fontMetrics()
        elided = metrics.elidedText(self._text, Qt.TextElideMode.ElideRight, self.width())
        super().setText(elided)

def _hdiv(color: str = _DIVIDER) -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setFixedHeight(1)
    f.setStyleSheet(f"background: {color}; border: none;")
    return f

class _EntryItem(QFrame):
    """
    One diary date row in the sidebar.

    ┌──────────────────────────────────────────┐
    │  07   │  Monday (or TODAY)               │
    │  JUN  │  First line of entry or  —       │
    └──────────────────────────────────────────┘
    """

    date_clicked = Signal(date)
    delete_clicked = Signal(date)

    _IDLE = "QWidget#EI { background: transparent; }"
    _HOV  = "QWidget#EI { background: " + _CARD_HOV + "; }"
    _SEL  = (
        "QWidget#EI {"
        f"  background: {_CARD_SEL};"
        "}"
    )

    def __init__(
        self,
        entry_date: date,
        snippet: str,
        selected: bool = False,
        is_today: bool = False,
        has_entry: bool = False,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("EI")
        self.entry_date = entry_date
        self.selected   = selected
        self.is_today   = is_today
        self.has_entry  = has_entry
        self._hov       = False

        self.setAttribute(Qt.WidgetAttribute.WA_Hover)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(72)
        self._build(snippet)
        self._restyle()

    def _build(self, snippet: str) -> None:
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 0, 14, 0)
        lay.setSpacing(10)

        # ── Date column ────────────────────────────────────────────────────
        date_box = QWidget()
        date_box.setFixedWidth(34)
        date_box.setStyleSheet("background: transparent;")
        db = QVBoxLayout(date_box)
        db.setContentsMargins(0, 0, 0, 0)
        db.setSpacing(1)

        pri_color = _T_PRI if self.is_today else _T_SEC
        day_num = QLabel(f"{self.entry_date.day:02d}")
        day_num.setAlignment(Qt.AlignmentFlag.AlignCenter)
        day_num.setStyleSheet(
            f"color: {pri_color};"
            f"font-size: 11pt; font-weight: {'700' if self.is_today else '500'};"
            f"font-family: '{_MONO}'; background: transparent; letter-spacing: -0.5px;"
        )
        db.addWidget(day_num)

        mon = QLabel(self.entry_date.strftime("%b").upper())
        mon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mon.setStyleSheet(
            f"color: {_T_DIM}; font-size: 5.8pt; letter-spacing: 0.7px;"
            "background: transparent;"
        )
        db.addWidget(mon)
        lay.addWidget(date_box)

        # Thin vertical hairline
        vsep = QWidget()
        vsep.setFixedSize(1, 22)
        vsep.setStyleSheet(f"background: {_DIVIDER};")
        lay.addWidget(vsep, alignment=Qt.AlignmentFlag.AlignVCenter)

        # ── Info column ────────────────────────────────────────────────────
        info = QWidget()
        info.setStyleSheet("background: transparent;")
        il = QVBoxLayout(info)
        il.setContentsMargins(0, 0, 0, 0)
        il.setSpacing(6)

        weekday_text = "TODAY" if self.is_today else self.entry_date.strftime("%A")
        wday = QLabel(weekday_text)
        wday.setStyleSheet(
            f"color: {pri_color};"
            f"font-size: {'8.5' if self.is_today else '9'}pt;"
            f"font-weight: {'700' if self.is_today else '400'};"
            f"letter-spacing: {'1.0' if self.is_today else '0'}px;"
            "background: transparent;"
        )
        il.addWidget(wday)

        snip_raw = (snippet or "").strip().split("\n")[0] or "—"
        snip = ElidedLabel(snip_raw)
        snip.setStyleSheet(
            "color: #8e8e93; font-size: 9pt; background: transparent;"
        )
        il.addWidget(snip)
        lay.addWidget(info, 1)

        # Delete button
        self.del_btn = QPushButton()
        self.del_btn.setIcon(QIcon("assets/icons/trash.svg"))
        self.del_btn.setFixedSize(24, 24)
        self.del_btn.setIconSize(QSize(14, 14))
        self.del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.del_btn.setStyleSheet(
            "QPushButton { background: transparent; border: none; }"
            "QPushButton:hover { background: rgba(255, 60, 60, 0.15); border-radius: 4px; }"
        )
        self.del_btn.hide()
        self.del_btn.clicked.connect(self._on_delete)
        lay.addWidget(self.del_btn, alignment=Qt.AlignmentFlag.AlignVCenter)
        lay.addSpacing(4)

    def _restyle(self) -> None:
        if self.selected:
            self.setStyleSheet(self._SEL)
        elif self._hov:
            self.setStyleSheet(self._HOV)
        else:
            self.setStyleSheet(self._IDLE)

    def set_selected(self, val: bool) -> None:
        self.selected = val
        self._restyle()

    def _on_delete(self):
        self.delete_clicked.emit(self.entry_date)

    def enterEvent(self, _) -> None:
        self._hov = True
        if self.has_entry:
            self.del_btn.show()
        self._restyle()

    def leaveEvent(self, _) -> None:
        self._hov = False
        self.del_btn.hide()
        self._restyle()

    def mousePressEvent(self, _) -> None:
        self.date_clicked.emit(self.entry_date)


# ── Sidebar ────────────────────────────────────────────────────────────────────

class JournalSidebar(QWidget):
    """
    Left panel: all diary entries, newest-first, grouped by calendar month.
    Always shows today at the top even when no entry exists yet.
    """

    date_selected = Signal(date)
    delete_requested = Signal(date)

    def __init__(self, service, parent=None) -> None:
        super().__init__(parent)
        self.service = service
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"background: {_SIDEBAR_BG};")
        self._items: list[_EntryItem] = []
        self._current_date = date.today()
        self._build()
        self.refresh(self._current_date)

    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # Header wrapper
        hdr = QWidget()
        hdr_lay = QVBoxLayout(hdr)
        hdr_lay.setAlignment(Qt.AlignmentFlag.AlignTop)
        hdr_lay.setContentsMargins(20, 24, 20, 12)
        hdr_lay.setSpacing(8)

        lbl = QLabel("Diary")
        lbl.setStyleSheet("color: #ffffff; font-size: 13pt; font-weight: bold; letter-spacing: 0.5px;")
        hdr_lay.addWidget(lbl)

        desc = QLabel("Daily Journals")
        desc.setStyleSheet("color: #8e8e93; font-size: 10pt;")
        hdr_lay.addWidget(desc)

        lay.addWidget(hdr)
        
        # Thin divider
        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setFixedHeight(1)
        div.setStyleSheet("background: rgba(255,255,255,0.05); border: none; margin-left: 20px; margin-right: 20px; margin-bottom: 12px;")
        lay.addWidget(div)

        # Scrollable list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            f"QScrollArea {{ background: {_SIDEBAR_BG}; border: none; }}"
            "QScrollBar:vertical { width: 3px; background: transparent; margin: 0; }"
            "QScrollBar::handle:vertical {"
            "  background: rgba(255,255,255,0.07); border-radius: 1px; min-height: 20px;"
            "}"
            "QScrollBar::add-line, QScrollBar::sub-line { height: 0; }"
            "QScrollBar::add-page, QScrollBar::sub-page { height: 0; }"
        )

        self._body = QWidget()
        self._body.setStyleSheet(f"background: {_SIDEBAR_BG};")
        self._body_lay = QVBoxLayout(self._body)
        self._body_lay.setContentsMargins(0, 6, 0, 14)
        self._body_lay.setSpacing(0)
        self._body_lay.addStretch(1)

        scroll.setWidget(self._body)
        lay.addWidget(scroll, 1)

    # ── Month separator label ──────────────────────────────────────────────

    @staticmethod
    def _month_label(d: date) -> QLabel:
        lbl = QLabel(d.strftime("%B %Y").upper())
        lbl.setStyleSheet(
            f"color: {_T_DIM}; font-size: 6.5pt; font-weight: 700;"
            f"letter-spacing: 1.3px; background: transparent;"
            f"padding: 14px 14px 4px 14px;"
        )
        return lbl

    # ── Populate ───────────────────────────────────────────────────────────

    def refresh(self, selected_date: date | None = None) -> None:
        entries = self.service.list_diary_entries()
        self._populate(entries, selected_date)

    def _populate(self, entries: list[JournalEntry], selected_date: date | None = None) -> None:
        # Wipe existing widgets
        while self._body_lay.count():
            item = self._body_lay.takeAt(0)
            if w := item.widget():
                w.deleteLater()
        self._items = []

        today = date.today()

        # Build a date → entry mapping; always include today
        date_map: dict[date, JournalEntry | None] = {e.entry_date: e for e in entries}
        if today not in date_map:
            date_map[today] = None   # synthetic placeholder — no content yet

        sorted_dates = sorted(date_map.keys(), reverse=True)

        current_month: tuple[int, int] | None = None
        for d in sorted_dates:
            month_key = (d.year, d.month)
            if month_key != current_month:
                current_month = month_key
                self._body_lay.addWidget(self._month_label(d))

            entry   = date_map[d]
            has_entry = entry is not None
            snippet = entry.content if entry else ""
            is_sel  = (d == selected_date)
            is_today= (d == today)

            item_w = _EntryItem(d, snippet=snippet, selected=is_sel, is_today=is_today, has_entry=has_entry)
            item_w.date_clicked.connect(self.date_selected.emit)
            item_w.delete_clicked.connect(self.delete_requested.emit)
            self._body_lay.addWidget(item_w)
            self._items.append(item_w)

        self._body_lay.addStretch(1)

    def set_selection(self, d: date) -> None:
        self._current_date = d
        for item in self._items:
            item.set_selected(item.entry_date == d)


# ── Writing pane ───────────────────────────────────────────────────────────────
