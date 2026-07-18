import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QSplitter, QVBoxLayout, QHBoxLayout, QWidget
)
from PySide6.QtCore import Qt

from ui.theme import MAIN_QSS
from ui.activity_bar import ActivityBar
from ui.side_panel import SidePanel
from ui.panels.notes_panel import NotesPanel
from ui.panels.daily_notes_panel import DailyNotesPanel
from ui.panels.tags_panel import TagsPanel
from ui.panels.trash_panel import TrashPanel
from ui.section_menu import SectionMenu
from ui.editor import NoteEditor
from ui.knowledge_panel import KnowledgePanel
from ui.top_bar import TopBar
from core.database import init_db, get_session
from core.models import Topic


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Study Notebook")
        self.resize(1600, 900)
        self.current_topic = None
        self._init_ui()

    def _init_ui(self):
        # ── Outermost horizontal layout: ActivityBar | SidePanel | RightArea ─
        root = QWidget()
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        self.setCentralWidget(root)

        # ── Activity Bar ──────────────────────────────────────────────────
        self.activity_bar = ActivityBar()
        root_layout.addWidget(self.activity_bar)

        # ── Main Splitter (SidePanel | RightArea) ─────────────────────────
        main_splitter = QSplitter(Qt.Horizontal)
        root_layout.addWidget(main_splitter, stretch=1)

        # ── Side Panel (stacked pages) ────────────────────────────────────
        self.notes_panel   = NotesPanel()
        self.daily_panel   = DailyNotesPanel()
        self.tags_panel    = TagsPanel()
        self.trash_panel   = TrashPanel()

        self.side_panel = SidePanel({
            "notes": self.notes_panel,
            "daily": self.daily_panel,
            "tags":  self.tags_panel,
            "trash": self.trash_panel,
        })
        main_splitter.addWidget(self.side_panel)

        # ── Right area: TopBar + inner splitter ───────────────────────────
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self.top_bar = TopBar()
        right_layout.addWidget(self.top_bar)

        inner_splitter = QSplitter(Qt.Horizontal)
        self.section_menu   = SectionMenu()
        self.editor_panel   = NoteEditor()
        self.knowledge_panel = KnowledgePanel()

        inner_splitter.addWidget(self.section_menu)
        inner_splitter.addWidget(self.editor_panel)
        inner_splitter.addWidget(self.knowledge_panel)
        inner_splitter.setStretchFactor(0, 1)
        inner_splitter.setStretchFactor(1, 4)
        inner_splitter.setStretchFactor(2, 2)
        inner_splitter.setCollapsible(0, False)
        inner_splitter.setCollapsible(1, False)
        inner_splitter.setCollapsible(2, False)

        right_layout.addWidget(inner_splitter)
        main_splitter.addWidget(right_container)
        main_splitter.setStretchFactor(0, 0)
        main_splitter.setStretchFactor(1, 1)
        main_splitter.setCollapsible(0, False)
        main_splitter.setCollapsible(1, False)

        # ── Wire signals ──────────────────────────────────────────────────
        # Activity bar ↔ side panel switching
        self.activity_bar.panel_requested.connect(self._on_panel_requested)
        self.activity_bar.toggle_panel.connect(self.side_panel.toggle_visibility)

        # Notes panel → select topic → load editor
        self.notes_panel.topic_selected.connect(self.on_topic_selected)

        # Section menu → switch section in editor
        self.section_menu.section_selected.connect(self.on_section_selected)

        # Trash panel restore → refresh notes panel
        self.trash_panel.topic_restored.connect(self.notes_panel.load_topics_from_db)

        # Daily notes → open in editor
        self.daily_panel.daily_note_selected.connect(self._on_daily_note_selected)

        # ── Load data ─────────────────────────────────────────────────────
        self.notes_panel.load_topics_from_db()

    # ── Slots ──────────────────────────────────────────────────────────────

    def _on_panel_requested(self, key: str):
        self.side_panel.show_panel(key)

    def on_topic_selected(self, topic_id: int):
        session = get_session()
        topic = session.get(Topic, topic_id)

        if topic:
            class _T:
                def __init__(self, t):
                    self.id = t.id
                    self.name = t.name

            self.current_topic = _T(topic)

            # Breadcrumb
            path, curr = [], topic
            while curr:
                path.append(curr.name)
                curr = curr.parents[0] if curr.parents else None
            path.reverse()
            self.top_bar.set_breadcrumb(" > ".join(path))

            # Load panels
            self.section_menu.load_topic_sections(topic)
            self.editor_panel.load_topic(self.current_topic, section="NOTES")
            self.knowledge_panel.load_references(topic)

        session.close()

    def on_section_selected(self, section_name: str):
        if self.current_topic:
            self.editor_panel.load_topic(self.current_topic, section=section_name)

    def _on_daily_note_selected(self, date_str: str):
        """Load a daily note into the editor."""
        from core.models import Note
        session = get_session()
        note = session.query(Note).filter_by(is_daily=True, daily_date=date_str).first()

        if note:
            class _DailyTopic:
                """Lightweight stand-in so the editor can load a daily note."""
                def __init__(self, n):
                    self.id = n.id
                    self.name = n.daily_date or "Daily Note"

            self.top_bar.set_breadcrumb(f"Daily Notes > {date_str}")
            # Re-use editor to load daily note by its id via a wrapper
            self.editor_panel.load_topic(_DailyTopic(note), section="NOTES")

        session.close()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    init_db()
    app.setStyleSheet(MAIN_QSS)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
