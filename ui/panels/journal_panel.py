from __future__ import annotations

from datetime import date, timedelta

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import (
    QColor, QFont, QPainter, QPen, QPixmap, QIcon, QTextCharFormat,
    QTextBlockFormat, QTextCursor,
)
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.models import JournalEntry
from core.database import get_session


# ── Palette — mirrors app-wide strict B&W/grey scheme ─────────────────────────
_BG = "transparent"
_SIDEBAR_BG   = _BG
_CARD_HOV     = "rgba(255,255,255,0.025)"
_CARD_SEL     = "#2D2036"
_BORDER = "rgba(255,255,255,0.06)"
_BORDER_MID   = "rgba(255,255,255,0.10)"
_BORDER_SEL   = "#B48EAD"
_DIVIDER      = "rgba(255,255,255,0.05)"
_T_PRI = "#ffffff"
_T_SEC = "#a0a0a0"
_T_TER = "#808080"
_T_DIM        = "#2a2a2c"
_SURFACE_IN   = "#1c1c1c"
_MONO         = "Courier New"

_SIDEBAR_W    = 236
_AUTOSAVE_MS  = 850      # debounce window before writing to service


# ── Thin rules ─────────────────────────────────────────────────────────────────

def _hdiv(color: str = _DIVIDER) -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setFixedHeight(1)
    f.setStyleSheet(f"background: {color}; border: none;")
    return f


def _vdiv(color: str = _DIVIDER) -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.VLine)
    f.setFixedWidth(1)
    f.setStyleSheet(f"background: {color}; border: none;")
    return f


# ── Delete icon ────────────────────────────────────────────────────────────────

def _trash_icon(color: str = _T_TER) -> QIcon:
    pix = QPixmap(16, 16)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor(color), 1.3)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    # lid
    p.drawLine(4, 5, 12, 5)
    p.drawLine(6, 5, 6, 3)
    p.drawLine(10, 5, 10, 3)
    p.drawLine(6, 3, 10, 3)
    # body
    p.drawLine(5, 6, 5, 13)
    p.drawLine(11, 6, 11, 13)
    p.drawLine(5, 13, 11, 13)
    # inner lines
    p.drawLine(8, 7, 8, 12)
    p.end()
    return QIcon(pix)


# ── Sidebar entry item ─────────────────────────────────────────────────────────

class _WritingPane(QWidget):
    """
    Right panel: date nav bar → editor → footer.

    Emits content_changed on every keystroke so the parent can debounce saves.
    """

    content_changed = Signal(str)
    delete_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setStyleSheet(f"background: {_BG};")
        self._build()

    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # ── Navigation bar ─────────────────────────────────────────────────
        nav = QWidget()
        nav.setFixedHeight(56)
        nav.setStyleSheet(f"background: {_BG};")
        nl = QHBoxLayout(nav)
        nl.setContentsMargins(56, 0, 56, 0)
        nl.setSpacing(0)

        self.prev_btn = self._arrow("‹")
        nl.addWidget(self.prev_btn)
        nl.addSpacing(16)

        self.date_lbl = QLabel()
        self.date_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.date_lbl.setStyleSheet(
            f"color: {_T_PRI}; font-size: 11pt; font-weight: 600;"
            f"letter-spacing: -0.2px; background: transparent;"
        )
        nl.addWidget(self.date_lbl, 1)

        self.today_btn = QPushButton("Today")
        self.today_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.today_btn.setStyleSheet(
            f"QPushButton {{ color: {_T_TER}; background: transparent; border: none;"
            f"font-size: 8pt; letter-spacing: 0.2px; }}"
            f"QPushButton:hover {{ color: {_T_SEC}; }}"
        )
        nl.addWidget(self.today_btn)
        nl.addSpacing(16)

        self.next_btn = self._arrow("›")
        nl.addWidget(self.next_btn)

        lay.addWidget(nav)
        lay.addWidget(_hdiv())

        # ── Editor area ────────────────────────────────────────────────────
        editor_wrap = QWidget()
        editor_wrap.setStyleSheet(f"background: {_BG};")
        ew = QVBoxLayout(editor_wrap)
        ew.setContentsMargins(56, 28, 56, 16)
        ew.setSpacing(0)

        # Relative date label (TODAY / YESTERDAY / N DAYS AGO)
        self.sub_lbl = QLabel()
        self.sub_lbl.setStyleSheet(
            f"color: {_T_TER}; font-size: 7pt; font-weight: 700;"
            f"letter-spacing: 1.6px; background: transparent;"
        )
        ew.addWidget(self.sub_lbl)
        ew.addSpacing(22)

        # Main editor
        self.editor = QTextEdit()
        self.editor.setPlaceholderText(
            "What's on your mind?\n\n"
            "Capture today's thoughts, wins, reflections, gratitude…"
        )

        # Premium readable font for the editor
        editor_font = QFont("Georgia", 12)
        editor_font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
        self.editor.setFont(editor_font)

        # Generous line height via block format
        fmt = QTextBlockFormat()
        fmt.setLineHeight(180, QTextBlockFormat.LineHeightTypes.ProportionalHeight.value)
        cursor = self.editor.textCursor()
        cursor.select(QTextCursor.SelectionType.Document)
        cursor.setBlockFormat(fmt)
        self.editor.setTextCursor(cursor)

        self.editor.setStyleSheet(
            f"QTextEdit {{"
            f"  background: transparent;"
            f"  color: {_T_PRI};"
            f"  border: none;"
            f"  letter-spacing: 0.25px;"
            f"  selection-background-color: rgba(255,255,255,0.10);"
            f"  selection-color: {_T_PRI};"
            f"}}"
        )
        self.editor.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.editor.textChanged.connect(self._on_change)
        ew.addWidget(self.editor, 1)

        lay.addWidget(editor_wrap, 1)
        lay.addWidget(_hdiv())

        # ── Footer ─────────────────────────────────────────────────────────
        footer = QWidget()
        footer.setFixedHeight(36)
        footer.setStyleSheet(f"background: {_BG};")
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(56, 0, 56, 0)
        fl.setSpacing(0)

        self.word_lbl = QLabel("0 words")
        self.word_lbl.setStyleSheet(
            f"color: {_T_TER}; font-size: 7.5pt; font-family: '{_MONO}';"
            "letter-spacing: 0.3px; background: transparent;"
        )
        fl.addWidget(self.word_lbl)

        fl.addStretch()

        # Delete link — only visible when a saved entry is loaded
        self.del_btn = QPushButton("Delete entry")
        self.del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.del_btn.setVisible(False)
        self.del_btn.setStyleSheet(
            f"QPushButton {{ color: {_T_TER}; background: transparent; border: none;"
            f"font-size: 7.5pt; font-family: '{_MONO}'; letter-spacing: 0.3px; }}"
            f"QPushButton:hover {{ color: #7a3535; }}"
        )
        self.del_btn.clicked.connect(self.delete_requested.emit)
        fl.addWidget(self.del_btn)
        fl.addSpacing(18)

        self.status_lbl = QLabel()
        self.status_lbl.setStyleSheet(
            f"color: {_T_TER}; font-size: 7.5pt; font-family: '{_MONO}';"
            "letter-spacing: 0.3px; background: transparent;"
        )
        fl.addWidget(self.status_lbl)

        lay.addWidget(footer)

    @staticmethod
    def _arrow(glyph: str) -> QPushButton:
        btn = QPushButton(glyph)
        btn.setFixedSize(28, 28)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(
            f"QPushButton {{ color: {_T_TER}; background: transparent; border: none;"
            f"font-size: 18pt; padding: 0; }}"
            f"QPushButton:hover {{ color: {_T_PRI}; }}"
            f"QPushButton:disabled {{ color: {_T_DIM}; }}"
        )
        return btn

    # ── Internal ───────────────────────────────────────────────────────────

    def _on_change(self) -> None:
        text  = self.editor.toPlainText()
        words = len(text.split()) if text.strip() else 0
        self.word_lbl.setText(f"{words} word{'s' if words != 1 else ''}")
        self._set_status("Unsaved", dim=False)
        self.content_changed.emit(text)

    def _set_status(self, text: str, dim: bool = True) -> None:
        color = _T_TER if dim else _T_SEC
        self.status_lbl.setText(text)
        self.status_lbl.setStyleSheet(
            f"color: {color}; font-size: 7.5pt; font-family: '{_MONO}';"
            "letter-spacing: 0.3px; background: transparent;"
        )

    # ── Public API ─────────────────────────────────────────────────────────

    def set_date(self, d: date) -> None:
        self.date_lbl.setText(d.strftime("%A, %d %B %Y"))
        today = date.today()
        delta = (today - d).days
        if d == today:
            self.sub_lbl.setText("TODAY")
            self.today_btn.setStyleSheet(
                f"QPushButton {{ color: #FFFFFF; background: transparent; border: none;"
                f"font-size: 8pt; letter-spacing: 0.2px; }}"
            )
        else:
            self.today_btn.setStyleSheet(
                f"QPushButton {{ color: {_T_TER}; background: transparent; border: none;"
                f"font-size: 8pt; letter-spacing: 0.2px; }}"
                f"QPushButton:hover {{ color: {_T_SEC}; }}"
            )
            if delta == 1:
                self.sub_lbl.setText("YESTERDAY")
            elif 2 <= delta <= 6:
                self.sub_lbl.setText(f"{delta} DAYS AGO")
            elif d < today:
                self.sub_lbl.setText(d.strftime("%B %Y").upper())
            else:
                self.sub_lbl.setText("")

    def set_content(self, text: str, has_saved_entry: bool = False) -> None:
        """Load text without triggering the auto-save signal."""
        self.editor.blockSignals(True)
        self.editor.setPlainText(text)
        self.editor.blockSignals(False)

        words = len(text.split()) if text.strip() else 0
        self.word_lbl.setText(f"{words} word{'s' if words != 1 else ''}")
        self.del_btn.setVisible(has_saved_entry)
        self._set_status("Saved" if has_saved_entry else "", dim=True)

    def mark_saved(self, has_entry: bool = True) -> None:
        self._set_status("Saved", dim=True)
        self.del_btn.setVisible(has_entry)

    def mark_empty(self) -> None:
        self._set_status("", dim=True)
        self.del_btn.setVisible(False)

    def get_content(self) -> str:
        return self.editor.toPlainText()

    def focus_editor(self) -> None:
        self.editor.setFocus()
        cursor = self.editor.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.editor.setTextCursor(cursor)


# ── JournalPanel ──────────────────────────────────────────────────────────────────


class JournalService:
    def list_diary_entries(self):
        with get_session() as session:
            entries = session.query(JournalEntry).all()
            for e in entries:
                if type(e.entry_date) == str:
                    from datetime import datetime
                    e.entry_date = datetime.strptime(e.entry_date, '%Y-%m-%d').date()
            return entries
            
    def get_diary_entry(self, entry_date):
        with get_session() as session:
            e = session.query(JournalEntry).filter_by(entry_date=str(entry_date)).first()
            if e and type(e.entry_date) == str:
                from datetime import datetime
                e.entry_date = datetime.strptime(e.entry_date, '%Y-%m-%d').date()
            return e
            
    def create_diary_entry(self, entry):
        with get_session() as session:
            if type(entry.entry_date) != str:
                entry.entry_date = str(entry.entry_date)
            session.add(entry)
            session.commit()
            return entry.id
            
    def update_diary_entry(self, entry):
        with get_session() as session:
            db_entry = session.query(JournalEntry).get(entry.id)
            if db_entry:
                db_entry.content = entry.content
                session.commit()
                
    def delete_diary_entry(self, entry_id):
        with get_session() as session:
            db_entry = session.query(JournalEntry).get(entry_id)
            if db_entry:
                session.delete(db_entry)
                session.commit()


class JournalPanel(QWidget):
    date_changed = Signal(date)
    data_changed = Signal()
    """
    Daily journal / diary page.

    ┌─ ToolBar ──────────────────────────────────────────────────────────────┐
    ├─ Sidebar ────────────┬─ Writing Pane ──────────────────────────────────┤
    │  JOURNAL             │  ‹  Wednesday, 07 June 2026            Today  › │
    │  ─────────           │  ─────────────────────────────────────────────  │
    │  JUNE 2026           │  TODAY                                          │
    │  ┌──────────────┐    │                                                 │
    │  │ 07  TODAY    │    │  What's on your mind?                           │
    │  │ JUN Snippet… │    │                                                 │
    │  └──────────────┘    │  [  large Georgia text editor              ]    │
    │  ┌──────────────┐    │  [                                         ]    │
    │  │ 06  Saturday │    │                                                 │
    │  │ JUN Yesterday│    │  ─────────────────────────────────────────────  │
    │  └──────────────┘    │  42 words          Delete entry        Saved    │
    └──────────────────────┴─────────────────────────────────────────────────┘

    Auto-saves with an 850 ms debounce after each keystroke.
    Requires the following additions to ProductivityService / models:

        JournalEntry(id, entry_date, content)

        service.get_diary_entry(d: date) -> JournalEntry | None
        service.list_diary_entries()     -> list[JournalEntry]
        service.create_diary_entry(e)    -> JournalEntry
        service.update_diary_entry(e)    -> JournalEntry
        service.delete_diary_entry(id)   -> None
    """

    def __init__(self) -> None:
        super().__init__()
        self.service = JournalService()
        self.setStyleSheet(f"background: {_BG};")

        self._current_date: date = date.today()

        # Debounced auto-save
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(_AUTOSAVE_MS)
        self._save_timer.timeout.connect(self._do_save)

        self._build_ui()
        self._nav_to(date.today())

    # ── UI skeleton ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Body
        body = QWidget()
        body.setStyleSheet(f"background: {_BG};")
        bl = QHBoxLayout(body)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(0)

        self._pane = _WritingPane()
        self._pane.prev_btn.clicked.connect(self._prev_day)
        self._pane.next_btn.clicked.connect(self._next_day)
        self._pane.today_btn.clicked.connect(lambda: self._nav_to(date.today()))
        self._pane.content_changed.connect(self._on_content_changed)
        self._pane.delete_requested.connect(self._delete_entry)
        bl.addWidget(self._pane, 1)

        root.addWidget(body, 1)

    # ── Day navigation ────────────────────────────────────────────────────

    def _prev_day(self) -> None:
        self._nav_to(self._current_date - timedelta(days=1))

    def _next_day(self) -> None:
        target = self._current_date + timedelta(days=1)
        if target <= date.today():
            self._nav_to(target)

    def load_date(self, d: date) -> None:
        self._nav_to(d)

    def _nav_to(self, d: date) -> None:
        # Flush any pending save before leaving the current date
        if self._save_timer.isActive():
            self._save_timer.stop()
            self._do_save()

        self._current_date = d

        # Load entry (or blank if none saved yet)
        entry = self.service.get_diary_entry(d)
        self._pane.set_date(d)
        self._pane.set_content(
            entry.content if entry else "",
            has_saved_entry=(entry is not None),
        )

        # Disable next arrow on today
        self._pane.next_btn.setEnabled(d < date.today())
        self.date_changed.emit(d)


    def _on_content_changed(self, _: str) -> None:
        """Restart the debounce timer on every keystroke."""
        self._save_timer.start()

    def _do_save(self) -> None:
        content = self._pane.get_content()
        if not content.strip():
            return   # never persist empty entries

        entry = self.service.get_diary_entry(self._current_date)
        if entry:
            entry.content = content
            self.service.update_diary_entry(entry)
        else:
            self.service.create_diary_entry(
                JournalEntry(id=None, entry_date=self._current_date, content=content)
            )

        self._pane.mark_saved(has_entry=True)
        self.data_changed.emit()

    # ── Delete ────────────────────────────────────────────────────────────

    def _delete_entry(self) -> None:
        self.delete_date_entry(self._current_date)

    def delete_date_entry(self, d: date) -> None:
        entry = self.service.get_diary_entry(d)
        if entry and entry.id is not None:
            self.service.delete_diary_entry(entry.id)
            if self._current_date == d:
                self._pane.set_content("", has_saved_entry=False)
                self._pane.mark_empty()
            self.data_changed.emit()
    
    # ── Toolbar shortcut ──────────────────────────────────────────────────

    def _open_today(self) -> None:
        self._nav_to(date.today())
        self._pane.focus_editor()

    # ── External refresh (called by app shell on tab switch) ───────────────

    def refresh(self) -> None:
        pass