from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QFrame, QTextEdit
)
from PySide6.QtCore import Qt, Signal, QSize, QDate
from PySide6.QtGui import QIcon


class DailyNotesPanel(QWidget):
    """
    Daily Notes panel — shows date-sorted quick notes, one per day.
    Notes are stored using the existing Note model with is_daily=True.
    """
    daily_note_selected = Signal(str)  # emits the date string "YYYY-MM-DD"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Header ─────────────────────────────────────────────────────────
        header = QWidget()
        header.setFixedHeight(36)
        header.setStyleSheet("background: #181818;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 0, 6, 0)
        header_layout.setSpacing(4)

        chevron = QLabel("›")
        chevron.setStyleSheet("color:#888; font-size:14px;")
        header_layout.addWidget(chevron)

        title = QLabel("DAILY NOTES")
        title.setStyleSheet(
            "font-size:11px; font-weight:700; color:#cccccc;"
            "letter-spacing:1px; padding-left:4px;"
        )
        header_layout.addWidget(title)
        header_layout.addStretch()

        today_btn = QPushButton()
        today_btn.setIcon(QIcon("assets/icons/act-daily.svg"))
        today_btn.setIconSize(QSize(15, 15))
        today_btn.setFixedSize(24, 24)
        today_btn.setToolTip("Open Today's Note")
        today_btn.setStyleSheet("""
            QPushButton { border:none; background:transparent; border-radius:4px; }
            QPushButton:hover { background:rgba(255,255,255,0.1); }
        """)
        today_btn.clicked.connect(self.open_today)
        header_layout.addWidget(today_btn)

        layout.addWidget(header)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background:#2a2a2a; border:none; max-height:1px;")
        layout.addWidget(sep)

        # ── Notes list ─────────────────────────────────────────────────────
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget {
                background: transparent;
                border: none;
                outline: none;
                color: #cccccc;
                font-size: 13px;
                padding: 4px 0;
            }
            QListWidget::item {
                padding: 6px 14px;
                border-radius: 3px;
                margin: 1px 4px;
            }
            QListWidget::item:hover { background: rgba(255,255,255,0.07); }
            QListWidget::item:selected { background: #37373d; color:#ffffff; }
        """)
        self.list_widget.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self.list_widget)

        self.load_daily_notes()

    def load_daily_notes(self):
        self.list_widget.clear()
        from core.database import get_session
        from core.models import Note

        session = get_session()
        notes = (
            session.query(Note)
            .filter_by(is_daily=True)
            .order_by(Note.daily_date.desc())
            .all()
        )

        # Group by date label
        today = QDate.currentDate().toString("yyyy-MM-dd")
        yesterday = QDate.currentDate().addDays(-1).toString("yyyy-MM-dd")

        prev_date = None
        for note in notes:
            date_str = note.daily_date or ""

            # Date section divider
            if date_str != prev_date:
                prev_date = date_str
                if date_str == today:
                    label = "Today"
                elif date_str == yesterday:
                    label = "Yesterday"
                else:
                    try:
                        qdate = QDate.fromString(date_str, "yyyy-MM-dd")
                        label = qdate.toString("MMMM d, yyyy")
                    except Exception:
                        label = date_str

                sep_item = QListWidgetItem(f"  {label}")
                sep_item.setFlags(Qt.NoItemFlags)
                sep_item.setForeground(Qt.gray)
                font = sep_item.font()
                font.setPointSize(9)
                font.setBold(True)
                sep_item.setFont(font)
                self.list_widget.addItem(sep_item)

            # Actual note item
            snippet = (note.content or "").replace("\n", " ").strip()
            display = snippet[:50] + "…" if len(snippet) > 50 else snippet or "(empty)"
            item = QListWidgetItem()
            item.setIcon(QIcon("assets/icons/daily-note-file.svg"))
            item.setText(f"  {display}")
            item.setData(Qt.UserRole, date_str)
            self.list_widget.addItem(item)

        session.close()

        # If no notes yet, show placeholder
        if self.list_widget.count() == 0:
            placeholder = QListWidgetItem("No daily notes yet.\nClick ▶ to create today's note.")
            placeholder.setFlags(Qt.NoItemFlags)
            placeholder.setForeground(Qt.gray)
            self.list_widget.addItem(placeholder)

    def open_today(self):
        today = QDate.currentDate().toString("yyyy-MM-dd")
        self._ensure_daily_note(today)
        self.daily_note_selected.emit(today)
        self.load_daily_notes()

    def _on_item_clicked(self, item: QListWidgetItem):
        date_str = item.data(Qt.UserRole)
        if date_str:
            self._ensure_daily_note(date_str)
            self.daily_note_selected.emit(date_str)

    def _ensure_daily_note(self, date_str: str):
        """Create a daily note for the given date if one doesn't exist."""
        from core.database import get_session
        from core.models import Note

        session = get_session()
        existing = session.query(Note).filter_by(is_daily=True, daily_date=date_str).first()
        if not existing:
            note = Note(
                title=date_str,
                content="",
                section_type="Daily",
                is_daily=True,
                daily_date=date_str,
            )
            session.add(note)
            session.commit()
        session.close()
