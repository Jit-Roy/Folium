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
from PySide6.QtCore import Qt, QSettings, QTimer, QByteArray, QObject, QEvent
from PySide6.QtGui import QIcon, QColor

import logging
import time

logging.basicConfig(
    filename='resize_debug.log', 
    level=logging.DEBUG, 
    format='%(asctime)s.%(msecs)03d | %(levelname)s | %(message)s', 
    datefmt='%H:%M:%S'
)

class WhiteFlashDetector(QObject):
    def __init__(self):
        super().__init__()
        self.last_resize_time = 0
        self.resize_count = 0
        
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Resize:
            if isinstance(obj, QWidget):
                now = time.time()
                elapsed = (now - self.last_resize_time) * 1000
                self.last_resize_time = now
                self.resize_count += 1
                
                # Check for lag
                if elapsed > 30 and self.resize_count > 5:
                    extra = ""
                    if hasattr(obj, 'text'):
                        extra = f" | Text: '{obj.text()[:50]}'"
                    elif hasattr(obj, 'objectName') and obj.objectName():
                        extra = f" | ObjName: '{obj.objectName()}'"
                    logging.warning(f"LAG DETECTED! {obj.__class__.__name__} resize took {elapsed:.1f}ms!{extra} (This causes DWM ghosting)")
                
                # Check for white backgrounds
                try:
                    bg_role = obj.backgroundRole()
                    color = obj.palette().color(bg_role)
                    # Exclude typical generic widgets that are transparent in practice but return their palette color
                    if color.name().lower() == '#ffffff' or color.name().lower() == '#f0f0f0':
                        if 'QTextEdit' in obj.__class__.__name__ or 'MainWindow' in obj.__class__.__name__ or 'QSplitter' in obj.__class__.__name__ or 'EditorTabs' in obj.__class__.__name__ or 'NoteEditor' in obj.__class__.__name__:
                            logging.error(f"WHITE/LIGHT BACKGROUND DETECTED ON: {obj.__class__.__name__} (Role: {bg_role.name.decode('utf-8') if hasattr(bg_role, 'name') else bg_role})")
                except Exception as e:
                    pass
        return False

from ui.theme import MAIN_QSS
from ui.activity_bar import ActivityBar
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
        self.setWindowTitle(" ")
        
        # Attach our global white flash detector
        self.flash_detector = WhiteFlashDetector()
        QApplication.instance().installEventFilter(self.flash_detector)
        logging.info("--- APP STARTED. WHITE FLASH DETECTOR ACTIVE ---")
        
        # Force Qt BackingStore to clear to our dark palette instead of white during resize lag
        self.setAutoFillBackground(True)
        self.setAttribute(Qt.WA_StyledBackground, True)
        
        import sys
        from PySide6.QtGui import QIcon
        from pathlib import Path
        basedir = Path(__file__).resolve().parent
        abs_icon = str(basedir / "assets" / "icons" / "app-icon.ico")
        self.setWindowIcon(QIcon(abs_icon))
        
        self.resize(1600, 900)
        self.current_topic = None
        self._init_ui()

    def showEvent(self, event):
        super().showEvent(event)
        self._apply_dwm_titlebar()

    def nativeEvent(self, eventType, message):
        # Intercept WM_ERASEBKGND (0x0014) to prevent Windows from painting
        # the background white before Qt's paint event fires.
        # This is the root cause of the white flash during resize.
        if eventType in (b'windows_generic_MSG', b'windows_dispatcher_MSG'):
            try:
                import ctypes
                import ctypes.wintypes

                # MSG struct on 64-bit Windows:
                # HWND   hwnd     (8 bytes)
                # UINT   message  (4 bytes) <- we need this
                # WPARAM wParam   (8 bytes) <- HDC when message==WM_ERASEBKGND
                class MSG(ctypes.Structure):
                    _fields_ = [
                        ('hwnd',    ctypes.c_void_p),
                        ('message', ctypes.c_uint),
                        ('wParam',  ctypes.c_size_t),
                        ('lParam',  ctypes.c_ssize_t),
                        ('time',    ctypes.c_uint),
                        ('pt_x',   ctypes.c_long),
                        ('pt_y',   ctypes.c_long),
                    ]

                msg = ctypes.cast(int(message), ctypes.POINTER(MSG)).contents
                if msg.message == 0x0014:  # WM_ERASEBKGND
                    hdc = ctypes.c_void_p(msg.wParam)
                    hwnd = ctypes.c_void_p(int(self.winId()))
                    # Fill client area with our dark background color
                    rc = ctypes.create_string_buffer(16)  # RECT struct (4 x c_long)
                    ctypes.windll.user32.GetClientRect(hwnd, rc)
                    brush = ctypes.windll.gdi32.CreateSolidBrush(0x00181818)  # #181818
                    ctypes.windll.user32.FillRect(hdc, rc, brush)
                    ctypes.windll.gdi32.DeleteObject(brush)
                    return True, 1  # Tell Windows we handled it
            except Exception:
                pass
        return super().nativeEvent(eventType, message)

    def _apply_dwm_titlebar(self):
        import sys
        if sys.platform != "win32":
            return
            
        try:
            import ctypes
            from ctypes import wintypes
            from ctypes import c_int
            
            hwnd = int(self.winId())
            
            # --- 1. Enable immersive dark mode so DWM ghost is dark not white ---
            color = 0x00181818
            DWMWA_CAPTION_COLOR = 35
            DWMWA_TEXT_COLOR = 36
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(c_int(1)), ctypes.sizeof(c_int))
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, DWMWA_CAPTION_COLOR, ctypes.byref(c_int(color)), ctypes.sizeof(c_int))
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, DWMWA_TEXT_COLOR, ctypes.byref(c_int(0x00FFFFFF)), ctypes.sizeof(c_int))
                
            # --- 2. Replace the Win32 Class Background Brush ---
            # By default, Windows clears newly-exposed regions during resize using a white
            # COLOR_WINDOW brush. We replace it with #121212 so that any area exposed
            # between frames appears dark instead of white.
            ctypes.windll.gdi32.CreateSolidBrush.restype = ctypes.c_void_p
            dark_brush = ctypes.windll.gdi32.CreateSolidBrush(0x00181818)  # 0x00bbggrr
            GCLP_HBRBACKGROUND = -10
            if ctypes.sizeof(ctypes.c_void_p) == 8:
                SetClassLongPtr = ctypes.windll.user32.SetClassLongPtrW
                SetClassLongPtr.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
                SetClassLongPtr.restype = ctypes.c_void_p
                SetClassLongPtr(hwnd, GCLP_HBRBACKGROUND, dark_brush)
            else:
                SetClassLong = ctypes.windll.user32.SetClassLongW
                SetClassLong.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_long]
                SetClassLong.restype = ctypes.c_long
                SetClassLong(hwnd, GCLP_HBRBACKGROUND, dark_brush)

            # 3. Hide the title bar icon natively
            try:
                from ui.win32_utils import hide_titlebar_icon
                hide_titlebar_icon(hwnd)
            except Exception as e:
                print(f"Failed to hide titlebar icon: {e}")

        except Exception as e:
            print(f"DWM titlebar setup failed: {e}")

    def _init_ui(self):
        # ── Outermost vertical layout for main content ─
        main_container = QWidget()
        v_layout = QVBoxLayout(main_container)
        v_layout.setContentsMargins(0, 0, 0, 0)
        v_layout.setSpacing(0)
        self.setCentralWidget(main_container)
        
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
    import ctypes
    import sys
    myappid = 'Zstudy.app.1.0'
    try:
        if not getattr(sys, 'frozen', False):
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass

    app = QApplication(sys.argv)
    app.setOrganizationName("Zstudy")
    app.setApplicationName("StudyNotebook")
    init_db()
    
    # Set dark palette to prevent white flashes before QSS is applied
    app.setStyle("Fusion")
    from PySide6.QtGui import QPalette, QColor
    from PySide6.QtCore import Qt
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor("#121212"))
    palette.setColor(QPalette.WindowText, Qt.white)
    palette.setColor(QPalette.Base, QColor("#121212"))
    palette.setColor(QPalette.AlternateBase, QColor("#121212"))
    palette.setColor(QPalette.ToolTipBase, Qt.white)
    palette.setColor(QPalette.ToolTipText, Qt.white)
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, QColor("#121212"))
    palette.setColor(QPalette.ButtonText, Qt.white)
    palette.setColor(QPalette.BrightText, Qt.red)
    palette.setColor(QPalette.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(palette)
    
    app.setStyleSheet(MAIN_QSS)
    window = MainWindow()
    
    from pathlib import Path
    basedir = Path(__file__).resolve().parent
    abs_icon = str(basedir / "assets" / "icons" / "app-icon.ico")
    
    if not getattr(sys, 'frozen', False):
        try:
            from ui.win32_utils import setup_windows_identity
            setup_windows_identity(window, myappid, abs_icon)
        except Exception as e:
            print(f"Failed to setup windows identity: {e}")

    # Note: window.show() is called at the end of window.restore_state()
    # to prevent visual UI flashing on startup
    sys.exit(app.exec())
