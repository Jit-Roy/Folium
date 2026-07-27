import sys
import os
import faulthandler
faulthandler.enable()

# ── Silence QtWebEngine / Chromium log spam and Enable GPU Accel ──────────────
# Must be set before QApplication is created.
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = (
    "--disable-logging "
    "--log-level=3 "
    "--enable-gpu-rasterization "
    "--enable-zero-copy "
    "--ignore-gpu-blocklist "
    "--blink-settings=darkModeEnabled=true,darkModeImagePolicy=2"
)
os.environ["QT_LOGGING_RULES"] = (
    "qt.webenginecontext.info=false;"
    "qt.webengine.chromium=false;"
    "*.debug=false;"
    "js=false"
)
# ─────────────────────────────────────────────────────────────────────────────

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QSplitter, QVBoxLayout, QHBoxLayout, QWidget,
    QStackedWidget
)
from PySide6.QtCore import Qt, QSettings, QTimer, QByteArray
from PySide6.QtGui import QIcon

from ui.theme import MAIN_QSS
from ui.activity_bar import ActivityBar
from ui.title_bar import CustomTitleBar
from ui.side_panel import SidePanel
from ui.panels.context_sidebar import ContextSidebar
from ui.panels.habits_sidebar import HabitsSidebar
from ui.panels.planner_sidebar import PlannerSidebar
from ui.panels.recent_tasks_panel import TasksPage, TasksService
from ui.panels.tasks_sidebar import TasksSidebar
from ui.panels.notes_panel import NotesPanel
from ui.panels.journal_panel import JournalPanel
from ui.panels.journal_sidebar import JournalSidebar
from ui.panels.habits_panel import HabitPage as HabitsPanel
from ui.panels.planner_panel import PlannerPage as PlannerPanel
from ui.editor_tabs import EditorTabs
from ui.knowledge_panel import KnowledgePanel
from ui.panels.search_panel import SearchOverlay
from core.database import init_db, get_session
from core.models import Topic


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint)
        self.setWindowTitle(" ")
        self.setWindowIcon(QIcon("assets/icons/app-icon.ico"))
        self.resize(1600, 900)
        self._is_pseudo_maximized = False
        self.current_topic = None
        self._init_ui()
        
        # Install global event filter to capture mouse movements over child widgets for edge resizing
        from PySide6.QtWidgets import QApplication
        QApplication.instance().installEventFilter(self)

    def _init_ui(self):
        # ── Outermost vertical layout for title bar + main content ─
        main_container = QWidget()
        v_layout = QVBoxLayout(main_container)
        v_layout.setContentsMargins(0, 0, 0, 0)
        v_layout.setSpacing(0)
        self.setCentralWidget(main_container)
        
        self.title_bar = CustomTitleBar(self)
        v_layout.addWidget(self.title_bar)
        
        # ── Inner horizontal layout: ActivityBar | SidePanel | RightArea ─
        root = QWidget()
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        v_layout.addWidget(root)

        # ── Activity Bar ──────────────────────────────────────────────────
        self.activity_bar = ActivityBar()
        root_layout.addWidget(self.activity_bar)

        # ── Main Splitter (SidePanel | RightArea) ─────────────────────────
        self.main_splitter = QSplitter(Qt.Horizontal)
        root_layout.addWidget(self.main_splitter, stretch=1)

        # ── Central Panels (instantiated early for sidebars) ──
        self.journal_panel = JournalPanel()
        self.habits_panel  = HabitsPanel()
        self.planner_panel = PlannerPanel()
        self.recent_tasks_service = TasksService()
        self.recent_tasks_panel = TasksPage(self.recent_tasks_service)

        self.notes_panel   = NotesPanel()
        
        self.side_panel = SidePanel({
            "notes": self.notes_panel,
            "habits": HabitsSidebar(self.habits_panel.service),
            "planner": PlannerSidebar(),
            "journal": JournalSidebar(self.journal_panel.service),
            "recent_tasks": TasksSidebar(self.recent_tasks_service),
        })
        self.main_splitter.addWidget(self.side_panel)

        self.habits_panel.data_changed.connect(
            self.side_panel.panels["habits"].refresh_stats
        )

        planner_sb = self.side_panel.panels["planner"]
        planner_sb.date_selected.connect(self.planner_panel.jump_to_date)
        planner_sb.navigate_weeks.connect(self.planner_panel._jump)
        self.planner_panel.week_changed.connect(planner_sb.sync_calendar)
        self.planner_panel.stats_updated.connect(planner_sb.update_stats)

        # ── Right area: inner splitter ───────────────────────────
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # --- CENTRAL STACK ---
        self.central_stack = QStackedWidget()
        right_layout.addWidget(self.central_stack)

        # --- INNER SPLITTER (Editor & Knowledge Panel) ---
        self.inner_splitter = QSplitter(Qt.Horizontal)
        self.inner_splitter.setStyleSheet(
            "QSplitter::handle { background: #2a2a2a; width: 3px; }"
        )

        self.editor_tabs = EditorTabs()
        self.editor_tabs.setMinimumWidth(750)
        self.editor_tabs.tags_updated.connect(self.notes_panel.load_tags)
        self.knowledge_panel = KnowledgePanel()

        self.inner_splitter.addWidget(self.editor_tabs)
        self.inner_splitter.addWidget(self.knowledge_panel)

        self.inner_splitter.setSizes([750, 100000])
        self.inner_splitter.setStretchFactor(0, 1)
        self.inner_splitter.setStretchFactor(1, 3)
        self.inner_splitter.setCollapsible(0, False)
        self.inner_splitter.setCollapsible(1, False)
        self.inner_splitter.splitterMoved.connect(self._on_splitter_moved)

        # --- ADD TO CENTRAL STACK ---
        self.central_stack.addWidget(self.inner_splitter)
        
        self.central_stack.addWidget(self.journal_panel)
        self.central_stack.addWidget(self.habits_panel)
        self.central_stack.addWidget(self.planner_panel)
        self.central_stack.addWidget(self.recent_tasks_panel)
        
        self.central_widgets_map = {
            "notes": self.inner_splitter,
            "journal": self.journal_panel,
            "habits": self.habits_panel,
            "planner": self.planner_panel,
            "recent_tasks": self.recent_tasks_panel,
        }


        # Signal connections for Journal refactor
        self.side_panel.panels["journal"].date_selected.connect(self.journal_panel.load_date)
        self.side_panel.panels["journal"].date_selected.connect(self.side_panel.panels["journal"].set_selection)
        self.side_panel.panels["journal"].delete_requested.connect(self.journal_panel.delete_date_entry)
        self.journal_panel.date_changed.connect(self.side_panel.panels["journal"].set_selection)
        self.journal_panel.data_changed.connect(self.side_panel.panels["journal"].refresh)
        
        # Signal connections for Tasks Sidebar
        tasks_sidebar = self.side_panel.panels["recent_tasks"]
        self.recent_tasks_panel.task_selected.connect(tasks_sidebar.load_task)
        self.recent_tasks_panel.create_task_requested.connect(tasks_sidebar.prepare_new_task)
        tasks_sidebar.data_changed.connect(self.recent_tasks_panel.refresh)
        
        self.main_splitter.addWidget(right_container)

        self.main_splitter.setStretchFactor(0, 0)
        self.main_splitter.setStretchFactor(1, 1)
        self.main_splitter.setCollapsible(0, False)
        self.main_splitter.setCollapsible(1, False)

        # ── Wire signals ──────────────────────────────────────────────────
        # Activity bar ↔ side panel switching
        self.activity_bar.panel_requested.connect(self._on_panel_requested)
        self.activity_bar.toggle_panel.connect(self._toggle_side_panel)
        self.activity_bar.settings_requested.connect(self._open_settings)

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

        # ── Global Search overlay (Ctrl+Shift+F) ───────────────────────────
        from PySide6.QtGui import QShortcut, QKeySequence
        self.search_overlay = SearchOverlay(self)
        self.search_overlay.topic_selected.connect(self._on_search_result_selected)
        self.search_overlay.hide()

        shortcut = QShortcut(QKeySequence("Ctrl+Shift+F"), self)
        shortcut.activated.connect(self._toggle_search_overlay)

        # ── Load data ──────────────────────────────────────────────────
        self.notes_panel.load_topics_from_db()
        self.notes_panel.load_tags()

        # Restore application state after the event loop starts to prevent UI flicker and access violations
        QTimer.singleShot(100, self.restore_state)

    def save_state(self):
        settings = QSettings()
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())
        settings.setValue("is_pseudo_maximized", getattr(self, "_is_pseudo_maximized", False))
        if hasattr(self, "_normal_geometry"):
            settings.setValue("normal_geometry", self._normal_geometry)
            
        settings.setValue("main_splitter_v2", self.main_splitter.saveState())
        settings.setValue("inner_splitter_v2", self.inner_splitter.saveState())
        
        # Save Activity bar
        settings.setValue("active_panel", self.activity_bar._active)
        
        # Delegate saving to components
        self.notes_panel.save_state(settings)
        self.editor_tabs.save_state(settings)
        self.knowledge_panel.save_state(settings)
        self.recent_tasks_panel.save_state(settings)
        
        # Save side panel visibility
        settings.setValue("side_panel_visible", self.side_panel._is_visible)
        
        # Save planner week offset
        settings.setValue("planner_week_offset", self.planner_panel.week_offset)

    def restore_state(self):
        settings = QSettings()
        
        if settings.value("normal_geometry"):
            self._normal_geometry = settings.value("normal_geometry")
            
        if settings.value("geometry"):
            self.restoreGeometry(settings.value("geometry"))
        if settings.value("windowState"):
            self.restoreState(settings.value("windowState"))
            
        if settings.value("main_splitter_v2"):
            self.main_splitter.restoreState(settings.value("main_splitter_v2"))
        if settings.value("inner_splitter_v2"):
            self.inner_splitter.restoreState(settings.value("inner_splitter_v2"))
            
        active_panel = settings.value("active_panel", "notes")
        self.activity_bar.set_active(active_panel)
        
        # Delegate restoring to components
        self.notes_panel.restore_state(settings)
        self.editor_tabs.restore_state(settings)
        self.knowledge_panel.restore_state(settings)
        self.recent_tasks_panel.restore_state(settings)
        
        # Restore side panel visibility
        side_visible = settings.value("side_panel_visible", True, type=bool)
        if not side_visible:
            self.side_panel.setVisible(False)
            self.side_panel._is_visible = False
            
        # Restore planner week offset
        try:
            week_offset = settings.value("planner_week_offset", 0)
            self.planner_panel.week_offset = int(week_offset) if week_offset is not None else 0
        except (ValueError, TypeError):
            self.planner_panel.week_offset = 0
        
        # Sync the panel-right button on the active editor
        self._sync_panel_btn(self.knowledge_panel.isVisible())
        
        # If knowledge panel was maximized, hide the editor tabs to restore that state
        if self.knowledge_panel.is_maximized:
            self.editor_tabs.hide()
            
        # Restore maximized state explicitly
        is_max = settings.value("is_pseudo_maximized", False, type=bool)
        if is_max:
            self._is_pseudo_maximized = True
            self.title_bar.update_max_icon(True)
            
            from PySide6.QtWidgets import QApplication
            screen = QApplication.screenAt(self.geometry().center())
            if screen:
                self.setGeometry(screen.availableGeometry())
        else:
            self._is_pseudo_maximized = False
            self.title_bar.update_max_icon(False)

        # Show the window now that the UI state has been completely restored
        # This prevents the user from seeing the initial unstyled or partial loading state
        self.show()

    def closeEvent(self, event):
        self.save_state()
        super().closeEvent(event)

    # ── Slots ──────────────────────────────────────────────────────────────

    def on_topic_deleted(self, deleted_ids):
        for tid in deleted_ids:
            self.editor_tabs.close_topic_without_saving(tid)

        # Clear selection visually if the active topic was deleted
        if self.current_topic and self.current_topic.id in deleted_ids:
            self._on_active_tab_changed(None)

    def _on_panel_requested(self, key: str):
        # Route the sidebar to the corresponding context page
        self.side_panel.show_panel(key)
        
        # Make sure sidebar is visible when navigating
        if not self.side_panel.isVisible():
            self.side_panel.setVisible(True)
            self.side_panel._is_visible = True

        if key in self.central_widgets_map:
            # Show the productivity tool
            widget = self.central_widgets_map[key]
            self.central_stack.setCurrentWidget(widget)
            if hasattr(widget, "refresh"):
                widget.refresh()
        else:
            # Show the editor/knowledge split view for Notes/Tags
            self.central_stack.setCurrentWidget(self.inner_splitter)

    def _toggle_side_panel(self):
        self.side_panel.toggle_visibility()
        # When folder architecture is collapsed, expand Reference Viewer to maximum
        if not self.side_panel._is_visible and self.knowledge_panel.isVisible():
            self.inner_splitter.setSizes([750, 100000])

    def _toggle_search_overlay(self):
        """Toggle the VS Code-style floating global search overlay (Ctrl+Shift+F)."""
        if self.search_overlay.isVisible():
            self.search_overlay.hide()
        else:
            self._position_search_overlay()
            self.search_overlay.show()
            self.search_overlay.raise_()
            self.search_overlay.focus_search()

    def _position_search_overlay(self):
        """Position the overlay in the top-right area of the editor, VS Code style."""
        # Get the geometry of the right area (inner_splitter)
        ref = self.inner_splitter
        tl = ref.mapTo(self, ref.rect().topLeft())
        overlay_w = min(420, ref.width() - 40)
        x = tl.x() + ref.width() - overlay_w - 30
        y = tl.y() + 15
        self.search_overlay.setFixedWidth(overlay_w)
        self.search_overlay.move(x, y)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'search_overlay') and self.search_overlay.isVisible():
            self._position_search_overlay()

    def _on_search_result_selected(self, topic_id: int, section_type: str):
        """Called when user clicks a search result — opens the matched note section."""
        self.search_overlay.hide()
        # Switch the main view to notes/editor
        self.central_stack.setCurrentWidget(self.inner_splitter)
        # Open the topic in the editor at the correct section
        session = get_session()
        topic = session.get(Topic, topic_id)
        if topic:
            class _T:
                def __init__(self, t, section):
                    self.id = t.id
                    self.name = t.name
                    self.path_parts = [(t.name, t.id)]
                    self.children = []
                    self.children_count = 0
                    self._section = section
            t = _T(topic, section_type)
            session.close()
            self.editor_tabs.open_topic(t, section_type)
        else:
            session.close()

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

    def _toggle_reference_panel(self, url: str):
        if not self.knowledge_panel.isVisible():
            self.knowledge_panel.show()
            self.knowledge_panel.is_maximized = False
            self.knowledge_panel.setMaximumWidth(400)
            self.knowledge_panel.reference_panel.load_url(url)
            self.knowledge_panel.switch_tab("REFERENCE")
        else:
            if self.knowledge_panel.active_tab == "REFERENCE" and self.knowledge_panel.reference_panel.web_view.url().toString() == url:
                self.knowledge_panel.hide()
            else:
                self.knowledge_panel.switch_tab("REFERENCE")
                self.knowledge_panel.reference_panel.load_url(url)

    def _open_settings(self):
        from ui.panels.settings_dialog import SettingsDialog
        dialog = SettingsDialog(self)
        dialog.exec()

    def _hide_reference_panel(self):
        """Collapse the right panel."""
        self.knowledge_panel.hide()
        self._sync_panel_btn(False)

    def _on_active_tab_changed(self, topic):
        self.current_topic = topic
        if topic:
            # Sync selection in NotesPanel
            if hasattr(topic, 'id'):
                self.notes_panel.select_topic(topic.id)
                self.knowledge_panel.set_current_topic(topic.id)
            
            # Load panels
            self.knowledge_panel.set_active_editor(self.editor_tabs.get_current_editor())
        else:
            self.notes_panel.clear_selection()
            self.knowledge_panel.set_current_topic(None)
            self.knowledge_panel.set_active_editor(None)

    RESIZE_MARGIN = 6

    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent, Qt
        if event.type() in (QEvent.MouseMove, QEvent.MouseButtonPress):
            if not self.isVisible() or self.isMaximized() or getattr(self, '_is_pseudo_maximized', False):
                return super().eventFilter(obj, event)

            try:
                global_pos = event.globalPosition().toPoint()
            except AttributeError:
                return super().eventFilter(obj, event)
                
            pos = self.mapFromGlobal(global_pos)
            w, h = self.width(), self.height()
            
            m = 6
            left = pos.x() < m and pos.x() >= 0
            right = pos.x() > w - m and pos.x() <= w
            top = pos.y() < m and pos.y() >= 0
            bottom = pos.y() > h - m and pos.y() <= h
            
            if top and pos.x() > w - 150:
                top = False
                right = False

            is_edge = left or right or top or bottom

            if event.type() == QEvent.MouseMove:
                if is_edge:
                    cursor = Qt.ArrowCursor
                    if (top and left) or (bottom and right): cursor = Qt.SizeFDiagCursor
                    elif (top and right) or (bottom and left): cursor = Qt.SizeBDiagCursor
                    elif left or right: cursor = Qt.SizeHorCursor
                    elif top or bottom: cursor = Qt.SizeVerCursor
                    
                    if not getattr(self, '_cursor_overridden', False):
                        from PySide6.QtWidgets import QApplication
                        QApplication.setOverrideCursor(cursor)
                        self._cursor_overridden = True
                    else:
                        from PySide6.QtWidgets import QApplication
                        QApplication.changeOverrideCursor(cursor)
                    return True
                else:
                    if getattr(self, '_cursor_overridden', False):
                        from PySide6.QtWidgets import QApplication
                        QApplication.restoreOverrideCursor()
                        self._cursor_overridden = False

            elif event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
                if getattr(self, '_cursor_overridden', False):
                    from PySide6.QtWidgets import QApplication
                    QApplication.restoreOverrideCursor()
                    self._cursor_overridden = False
                    
                if is_edge and self.windowHandle():
                    edges = Qt.Edge(0)
                    if top: edges |= Qt.Edge.TopEdge
                    if bottom: edges |= Qt.Edge.BottomEdge
                    if left: edges |= Qt.Edge.LeftEdge
                    if right: edges |= Qt.Edge.RightEdge
                    self.windowHandle().startSystemResize(edges)
                    return True

        return super().eventFilter(obj, event)

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
    app.setOrganizationName("Zstudy")
    app.setApplicationName("StudyNotebook")
    init_db()
    app.setStyleSheet(MAIN_QSS)
    window = MainWindow()
    # Note: window.show() is called at the end of window.restore_state()
    # to prevent visual UI flashing on startup
    sys.exit(app.exec())
