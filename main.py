import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QSplitter, QVBoxLayout, QHBoxLayout, QWidget
)
from PySide6.QtCore import Qt

from ui.theme import MAIN_QSS
from ui.activity_bar import ActivityBar
from ui.side_panel import SidePanel
from ui.panels.notes_panel import NotesPanel
from ui.panels.tags_panel import TagsPanel
from ui.editor_tabs import EditorTabs
from ui.knowledge_panel import KnowledgePanel
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
        self.tags_panel    = TagsPanel()

        self.side_panel = SidePanel({
            "notes": self.notes_panel,
            "tags":  self.tags_panel,
        })
        main_splitter.addWidget(self.side_panel)

        # ── Right area: inner splitter ───────────────────────────
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # --- INNER SPLITTER (Editor & Knowledge Panel) ---
        inner_splitter = QSplitter(Qt.Horizontal)
        inner_splitter.setStyleSheet("QSplitter::handle { background: #2a2a2a; }")

        self.editor_tabs    = EditorTabs()
        self.knowledge_panel = KnowledgePanel()

        inner_splitter.addWidget(self.editor_tabs)
        inner_splitter.addWidget(self.knowledge_panel)

        inner_splitter.setSizes([750, 250])
        inner_splitter.setStretchFactor(0, 3)
        inner_splitter.setStretchFactor(1, 1)
        inner_splitter.setCollapsible(0, False)
        inner_splitter.setCollapsible(1, False)

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

        # Notes panel → select topic → open tab
        self.notes_panel.topic_selected.connect(self.on_topic_selected)
        self.notes_panel.topic_deleted.connect(self.on_topic_deleted)

        # Editor Tabs → tab changed → update UI
        self.editor_tabs.active_topic_changed.connect(self._on_active_tab_changed)

        # Editor tabs breadcrumb → navigate to ancestor topic
        self.editor_tabs.topic_navigated.connect(self.on_topic_selected)

        # Trash panel restore → refresh notes panel
        # (Trash panel removed)

        # Daily notes → open in editor
        # (Daily notes panel removed)

        # ── Load data ─────────────────────────────────────────────────────
        self.notes_panel.load_topics_from_db()

    # ── Slots ──────────────────────────────────────────────────────────────

    def on_topic_deleted(self, deleted_ids):
        for tid in deleted_ids:
            self.editor_tabs.close_topic_without_saving(tid)

        # Clear selection visually if the active topic was deleted
        if self.current_topic and self.current_topic.id in deleted_ids:
            self._on_active_tab_changed(None)

    def _on_panel_requested(self, key: str):
        self.side_panel.show_panel(key)

    def on_topic_selected(self, topic_id: int):
        session = get_session()
        topic = session.get(Topic, topic_id)

        if topic:
            def get_path_parts(t):
                parts = [(t.name, t.id)]
                current = t
                while current.parents:
                    current = current.parents[0]
                    parts.insert(0, (current.name, current.id))
                return parts

            class _T:
                def __init__(self, t, path_parts):
                    self.id = t.id
                    self.name = t.name
                    self.path_parts = path_parts
                    self.path_str = " > ".join(n for n, _ in path_parts)
                    self.children_count = len(t.children)

            t_obj = _T(topic, get_path_parts(topic))
            self.editor_tabs.open_topic(t_obj, section="NOTES")

        session.close()

    def _on_active_tab_changed(self, topic):
        self.current_topic = topic
        if topic:
            # Sync selection in NotesPanel
            if hasattr(topic, 'id'):
                self.notes_panel.select_topic(topic.id)
            
            # Load panels
            self.knowledge_panel.load_references(topic)
        else:
            self.notes_panel.clear_selection()

    def on_section_selected(self, section_name: str):
        if self.current_topic:
            self.editor_tabs.change_section_for_current(section_name)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    init_db()
    app.setStyleSheet(MAIN_QSS)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
