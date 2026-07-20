import sys
import os

# ── Silence QtWebEngine / Chromium log spam and Enable GPU Accel ──────────────
# Must be set before QApplication is created.
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = (
    "--disable-logging "
    "--log-level=3 "
    "--enable-gpu-rasterization "
    "--enable-zero-copy "
    "--ignore-gpu-blocklist"
)
os.environ["QT_LOGGING_RULES"] = (
    "qt.webenginecontext.info=false;"
    "qt.webengine.chromium=false;"
    "*.debug=false;"
    "js=false"
)
# ─────────────────────────────────────────────────────────────────────────────

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
        self.inner_splitter = QSplitter(Qt.Horizontal)
        self.inner_splitter.setStyleSheet(
            "QSplitter::handle { background: #2a2a2a; width: 3px; }"
        )

        self.editor_tabs = EditorTabs()
        self.editor_tabs.setMinimumWidth(750)  # Keep the canvas wide enough for all H1/H2 formatting buttons!
        self.knowledge_panel = KnowledgePanel()

        self.inner_splitter.addWidget(self.editor_tabs)
        self.inner_splitter.addWidget(self.knowledge_panel)

        # Give the Reference Viewer maximum expandable width on startup
        self.inner_splitter.setSizes([750, 100000])
        self.inner_splitter.setStretchFactor(0, 1)
        self.inner_splitter.setStretchFactor(1, 3)
        self.inner_splitter.setCollapsible(0, False)
        self.inner_splitter.setCollapsible(1, False)
        self.inner_splitter.splitterMoved.connect(self._on_splitter_moved)

        right_layout.addWidget(self.inner_splitter)

        main_splitter.addWidget(right_container)
        main_splitter.setStretchFactor(0, 0)
        main_splitter.setStretchFactor(1, 1)
        main_splitter.setCollapsible(0, False)
        main_splitter.setCollapsible(1, False)

        # ── Wire signals ──────────────────────────────────────────────────
        # Activity bar ↔ side panel switching
        self.activity_bar.panel_requested.connect(self._on_panel_requested)
        self.activity_bar.toggle_panel.connect(self._toggle_side_panel)

        # Panel-right button in any open editor → toggle reference panel
        self.editor_tabs.toggle_reference_viewer.connect(self._toggle_reference_panel)

        # Notes panel → select topic → open tab
        self.notes_panel.topic_selected.connect(self.on_topic_selected)
        self.notes_panel.topic_deleted.connect(self.on_topic_deleted)

        # Editor Tabs → tab changed → update UI
        self.editor_tabs.active_topic_changed.connect(self._on_active_tab_changed)

        # Editor tabs breadcrumb → navigate to ancestor topic
        self.editor_tabs.topic_navigated.connect(self.on_topic_selected)

        # Reference viewer close button → collapse the panel
        self.knowledge_panel.close_requested.connect(self._hide_reference_panel)

        # Reference viewer maximize button → hide the canvas
        self.knowledge_panel.maximize_requested.connect(self._on_reference_viewer_maximize_requested)

        # ── Load data ──────────────────────────────────────────────────
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

    def _toggle_side_panel(self):
        self.side_panel.toggle_visibility()
        # When folder architecture is collapsed, expand Reference Viewer to maximum
        if not self.side_panel._is_visible and self.knowledge_panel.isVisible():
            self.inner_splitter.setSizes([750, 100000])

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
                self.knowledge_panel.set_current_topic(topic.id)
            
            # Load panels
            self.knowledge_panel.load_references(topic)
            self.knowledge_panel.set_active_editor(self.editor_tabs.get_current_editor())
        else:
            self.notes_panel.clear_selection()
            self.knowledge_panel.set_current_topic(None)
            self.knowledge_panel.set_active_editor(None)

    def on_section_selected(self, section_name: str):
        if self.current_topic:
            self.editor_tabs.change_section_for_current(section_name)

    def _hide_reference_panel(self):
        """Collapse the right panel."""
        self.knowledge_panel.hide()
        self._sync_panel_btn(False)

    def _on_reference_viewer_maximize_requested(self, is_maximized: bool):
        """Maximize the reference viewer by hiding the editor canvas."""
        if is_maximized:
            self.editor_tabs.hide()
        else:
            self.editor_tabs.show()
            self.inner_splitter.setSizes([750, 100000])

    def _toggle_reference_panel(self):
        """Toggle the reference viewer panel open/closed."""
        if not self.knowledge_panel.isVisible():  # Currently collapsed → open it
            self.knowledge_panel.show()
            
            # Reopen to the maximum expandable width as requested
            self.inner_splitter.setSizes([750, 100000])
                
            self._sync_panel_btn(True)
        else:
            self._hide_reference_panel()

    def _on_splitter_moved(self, pos, index):
        """Keep the panel button in sync when user drags the splitter."""
        self._sync_panel_btn(self.knowledge_panel.isVisible())

    def _sync_panel_btn(self, is_open: bool):
        """Sync the panel-right button checked state in the active editor."""
        editor = self.editor_tabs.get_current_editor()
        if editor and hasattr(editor, 'panel_right_btn'):
            editor.panel_right_btn.setChecked(is_open)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    init_db()
    app.setStyleSheet(MAIN_QSS)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
