from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget, QLabel, QTabBar, QScrollBar, QHBoxLayout
)
from PySide6.QtCore import Qt, Signal, QPoint, QTimer, QSize
from PySide6.QtGui import QWheelEvent
from ui.editor import NoteEditor
from ui.widgets.breadcrumb import BreadcrumbWidget


class HoverScrollBar(QScrollBar):
    """A thin horizontal scrollbar that fades in on hover and out when mouse leaves."""
    def __init__(self, parent=None):
        super().__init__(Qt.Horizontal, parent)
        self._fade_timer = QTimer(self)
        self._fade_timer.setSingleShot(True)
        self._fade_timer.timeout.connect(self.hide)
        self.setFixedHeight(4)
        self.setStyleSheet("""
            QScrollBar:horizontal {
                background: transparent;
                border: none;
                height: 4px;
                margin: 0;
            }
            QScrollBar::handle:horizontal {
                background: rgba(180, 142, 173, 0.7);
                border-radius: 2px;
                min-width: 30px;
            }
            QScrollBar::handle:horizontal:hover {
                background: rgba(180, 142, 173, 1.0);
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0; border: none; background: none;
            }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: none;
            }
        """)
        self.hide()

    def show_briefly(self):
        self.show()
        self._fade_timer.stop()
        self._fade_timer.start(1500)

    def show_persistent(self):
        self.show()
        self._fade_timer.stop()


class EditorTabs(QWidget):
    """
    Manages multiple NoteEditor instances in a VS Code-style tabbed interface.
    Supports drag and drop from the notes tree.
    """
    active_topic_changed = Signal(object) # Emits the topic object (or None)
    topic_navigated = Signal(int) # Emits topic_id when breadcrumb is clicked
    toggle_reference_viewer = Signal()  # Relayed from whichever NoteEditor is active
    tags_updated = Signal() # Relayed from whichever NoteEditor is active

    def __init__(self, parent=None):
        super().__init__(parent)
        self.editors = {} # Maps topic_id to NoteEditor instance
        self.topic_map = {} # Maps topic_id to Topic object
        self.init_ui()

    def init_ui(self):
        from PySide6.QtWidgets import QStackedWidget, QScrollArea
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Breadcrumb at the very top
        self.breadcrumb = BreadcrumbWidget()
        self.breadcrumb.segment_clicked.connect(self.topic_navigated.emit)
        
        # We need a small container to give it some padding, or just set margins on a container
        breadcrumb_container = QWidget()
        bc_layout = QVBoxLayout(breadcrumb_container)
        bc_layout.setContentsMargins(15, 10, 15, 10)
        bc_layout.addWidget(self.breadcrumb)
        layout.addWidget(breadcrumb_container)

        self.stacked_editors = QStackedWidget()
        self.stacked_editors.setStyleSheet("background: #121212;")

        # Standalone Tab Bar
        self._tab_bar = QTabBar()
        self._tab_bar.setDocumentMode(True)
        self._tab_bar.setTabsClosable(True)
        self._tab_bar.setMovable(True)
        self._tab_bar.setUsesScrollButtons(False)
        self._tab_bar.setExpanding(False)
        
        self._tab_bar.setStyleSheet("""
            QTabBar::tab {
                background: #181818;
                color: #888888;
                padding: 8px 12px;
                border: none;
                border-right: 1px solid #2a2a2a;
                font-size: 13px;
                min-width: 100px;
                max-width: 200px;
                height: 19px; /* Adjust total height to fit nicely */
            }
            QTabBar::tab:hover {
                background: #1f1f1f;
                color: #cccccc;
            }
            QTabBar::tab:selected {
                background: #2D2036;
                color: #B48EAD;
            }
            QTabBar::close-button {
                image: url(assets/icons/x.svg);
                subcontrol-position: right;
                subcontrol-origin: padding;
            }
            QTabBar::close-button:hover {
                background: rgba(255,255,255,0.1);
                border-radius: 2px;
            }
        """)

        # Scroll Area to provide perfect pixel scrolling for the tab bar
        self._scroll_area = QScrollArea()
        self._scroll_area.setFixedHeight(35)
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setFrameShape(QScrollArea.NoFrame)
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll_area.setWidget(self._tab_bar)
        self._scroll_area.setStyleSheet("background: #121212;")

        # ── Dedicated hover scroll strip ───────────────────────────────────
        self._scroll_bar = HoverScrollBar()

        # Wire up our hover scrollbar to perfectly reflect the native scroll area
        native_h_bar = self._scroll_area.horizontalScrollBar()
        native_h_bar.rangeChanged.connect(self._scroll_bar.setRange)
        native_h_bar.valueChanged.connect(self._scroll_bar.setValue)
        
        # Sync pageStep so the scroll handle resizes dynamically
        native_h_bar.rangeChanged.connect(self._sync_scroll_metrics)
        
        self._scroll_bar.sliderMoved.connect(native_h_bar.setValue)
        self._scroll_bar.sliderReleased.connect(self._check_fade_after_drag)

        self._scroll_strip = QWidget()
        self._scroll_strip.setFixedHeight(4)
        self._scroll_strip.setStyleSheet("background: #121212;")
        _ss_layout = QHBoxLayout(self._scroll_strip)
        _ss_layout.setContentsMargins(0, 0, 0, 0)
        _ss_layout.setSpacing(0)
        _ss_layout.addWidget(self._scroll_bar)
        self._scroll_strip.hide()

        # Main Container
        self._tab_container = QWidget()
        _tc_layout = QVBoxLayout(self._tab_container)
        _tc_layout.setContentsMargins(0, 0, 0, 0)
        _tc_layout.setSpacing(0)
        _tc_layout.addWidget(self._scroll_area)
        _tc_layout.addWidget(self._scroll_strip)
        _tc_layout.addWidget(self.stacked_editors)

        # Placeholder
        self.empty_label = QLabel("Drag a note here or click one in the Explorer")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet("color: #555555; font-size: 16px; font-style: italic;")

        layout.addWidget(self.empty_label)
        layout.addWidget(self._tab_container)
        self._tab_container.hide()

        self._tab_bar.tabCloseRequested.connect(self._on_tab_close)
        self._tab_bar.currentChanged.connect(self._on_tab_changed)
        self._tab_bar.tabMoved.connect(self._on_tab_moved)

        # Install event filters to translate wheel scrolls into smooth horizontal scrolls
        self._scroll_area.installEventFilter(self)
        self._tab_bar.installEventFilter(self)

        # Enable Drag and Drop
        self.setAcceptDrops(True)

    def _sync_scroll_metrics(self):
        """Syncs the page step of the native scrollbar to the custom hover scrollbar to dynamically size the handle."""
        native = self._scroll_area.horizontalScrollBar()
        self._scroll_bar.setPageStep(native.pageStep())
        
        # If tabs were removed or window resized such that no scroll is needed, hide immediately
        if not self._is_scroll_needed():
            self._scroll_strip.hide()

    def _check_fade_after_drag(self):
        """Called when the scrollbar handle is released. Fades out if the mouse is no longer hovering."""
        if not (self._tab_bar.underMouse() or self._scroll_area.underMouse() or self._scroll_strip.underMouse()):
            self._scroll_bar._fade_timer.start(800)

    def _is_scroll_needed(self):
        """Manually calculate if tabs exceed the viewport width."""
        total_tab_width = sum(self._tab_bar.tabRect(i).width() for i in range(self._tab_bar.count()))
        return total_tab_width > self._scroll_area.viewport().width()

    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent
        if event.type() == QEvent.Wheel and obj in (self._scroll_area, self._tab_bar):
            # Intercept wheel scroll and smoothly translate it to the horizontal scrollbar
            h_bar = self._scroll_area.horizontalScrollBar()
            dy = event.angleDelta().y()
            dx = event.angleDelta().x()
            
            # Figure out the scroll delta (prefer horizontal swipe, fallback to vertical wheel)
            if abs(dx) > abs(dy):
                delta = dx
            else:
                delta = -dy  # inverted so scrolling mouse wheel down goes right

            h_bar.setValue(h_bar.value() - delta)
            
            # Keep scrollbar visible when scrolling
            if self._is_scroll_needed():
                self._scroll_strip.show()
                self._scroll_bar.show_persistent()
            return True

        if obj in (self._tab_bar, self._scroll_area):
            if event.type() == QEvent.Enter:
                if self._is_scroll_needed():
                    self._scroll_strip.show()
                    self._scroll_bar.show_persistent()
            elif event.type() == QEvent.Leave:
                if not self._scroll_bar.isSliderDown():
                    self._scroll_bar._fade_timer.start(800)
                
        return super().eventFilter(obj, event)

    # ── Public API ─────────────────────────────────────────────────────────

    def get_current_editor(self):
        """Returns the currently active NoteEditor widget."""
        return self.stack.currentWidget()

    def open_topic(self, topic, section="NOTES"):
        """Opens a topic in a new tab or switches to it if already open."""
        if not topic:
            return

        topic_id = getattr(topic, 'id', topic)
        
        if topic_id in self.editors:
            # Switch to existing tab
            editor = self.editors[topic_id]
            idx = self.stacked_editors.indexOf(editor)
            if idx >= 0:
                self._tab_bar.setCurrentIndex(idx)
            # Switch section if needed
            editor.load_topic(topic, section)
        else:
            # Create new tab
            editor = NoteEditor()
            editor.load_topic(topic, section)
            
            # Add to map
            self.editors[topic_id] = editor
            self.topic_map[topic_id] = topic
            
            # Relay the panel-right toggle signal from this editor
            editor.toggle_reference_viewer.connect(self.toggle_reference_viewer.emit)
            editor.tags_updated.connect(self.tags_updated.emit)
            
            self.stacked_editors.addWidget(editor)
            idx = self._tab_bar.addTab(getattr(topic, 'name', 'Note'))
            self._tab_bar.setTabToolTip(idx, getattr(topic, 'name', 'Note'))
            self._tab_bar.setCurrentIndex(idx)
            
        self._update_visibility()

    def get_current_editor(self):
        """Returns the currently active NoteEditor."""
        return self.stacked_editors.currentWidget()

    def get_current_topic(self):
        """Returns the currently active topic object."""
        editor = self.get_current_editor()
        if editor and editor.current_topic_id:
            return self.topic_map.get(editor.current_topic_id)
        return None

    def change_section_for_current(self, section):
        editor = self.get_current_editor()
        if editor:
            topic = self.topic_map.get(editor.current_topic_id)
            if topic:
                editor.load_topic(topic, section)

    # ── Internal Callbacks ──────────────────────────────────────────────────

    def _on_tab_moved(self, from_idx, to_idx):
        """Syncs the QStackedWidget when a tab is dragged and dropped to reorder."""
        widget = self.stacked_editors.widget(from_idx)
        self.stacked_editors.removeWidget(widget)
        self.stacked_editors.insertWidget(to_idx, widget)

    def _on_tab_close(self, index):
        editor = self.stacked_editors.widget(index)
        if editor:
            # Force save before closing
            editor.save_note()
            topic_id = editor.current_topic_id
            if topic_id in self.editors:
                del self.editors[topic_id]
            if topic_id in self.topic_map:
                del self.topic_map[topic_id]
                
            self.stacked_editors.removeWidget(editor)
            
        self._tab_bar.removeTab(index)
        self._update_visibility()

    def close_topic_without_saving(self, topic_id):
        """Forcefully close a tab without triggering a save. Used when a topic is deleted."""
        if topic_id in self.editors:
            editor = self.editors[topic_id]
            idx = self.stacked_editors.indexOf(editor)
            
            # Remove references first so that when removeTab fires currentChanged, it doesn't find it
            del self.editors[topic_id]
            if topic_id in self.topic_map:
                del self.topic_map[topic_id]
                
            if idx >= 0:
                self.stacked_editors.removeWidget(editor)
                self._tab_bar.removeTab(idx)
        self._update_visibility()
        
    def _on_tab_changed(self, index):
        if index >= 0:
            self.stacked_editors.setCurrentIndex(index)
            
        from PySide6.QtCore import QTimer
        def emit_change():
            topic = self.get_current_topic()
            self.active_topic_changed.emit(topic)
            
            # Update breadcrumb
            if topic:
                path_parts = getattr(topic, 'path_parts', [(topic.name, getattr(topic, 'id', 0))])
                self.breadcrumb.set_path(path_parts)
            else:
                self.breadcrumb.set_path([])
                
        QTimer.singleShot(0, emit_change)

    def _update_visibility(self):
        has_tabs = self._tab_bar.count() > 0
        self._tab_container.setVisible(has_tabs)
        self.empty_label.setVisible(not has_tabs)

    # ── Drag and Drop ──────────────────────────────────────────────────────

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/x-qabstractitemmodeldatalist"):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasFormat("application/x-qabstractitemmodeldatalist"):
            byte_array = event.mimeData().data("application/x-qabstractitemmodeldatalist")
            
            # Parse QStandardItemModel MIME data manually to extract Qt.UserRole
            from PySide6.QtCore import QDataStream, QIODevice
            stream = QDataStream(byte_array, QIODevice.ReadOnly)
            
            # The format is: (int row, int col, QMap<int, QVariant> roles) repeated
            while not stream.atEnd():
                row = stream.readInt32()
                col = stream.readInt32()
                roles = stream.readQVariant() # This might fail if we don't handle map correctly
                
                # A safer way to retrieve the topic_id is to fetch it directly from DB if needed,
                # but let's try reading the map directly or just use PySide's built-in decoding if possible.
                
                # Actually, in PySide6 QDataStream reading a QMap might be tricky.
                # Let's use a simpler way: emit a signal or just read the current index from NotesPanel.
                # But we don't have access to NotesPanel here easily.
                # Let's assume the string format might contain it, or we just parse the roles manually.
                pass
            
            # Safest workaround for extracting data from internal drag-and-drop:
            # Since the app runs in one process, we can find the NotesPanel instance directly through parent hierarchy,
            # or better: when an item is dragged, NotesPanel could store the dragged topic_id in a globally accessible place.
            # But wait, QDataStream can easily read the roles map in PyQt/PySide:
            stream.device().seek(0)
            while not stream.atEnd():
                r = stream.readInt32()
                c = stream.readInt32()
                roles = stream.readQVariant() # dict mapping int to value
                if isinstance(roles, dict):
                    topic_id = roles.get(Qt.UserRole)
                    if topic_id and topic_id != "temp_new":
                        from core.database import get_session
                        from core.models import Topic
                        session = get_session()
                        topic = session.get(Topic, topic_id)
                        if topic:
                            # We must detach the topic or recreate a lightweight wrapper since session closes
                            class _T:
                                def __init__(self, t):
                                    self.id = t.id
                                    self.name = t.name
                            self.open_topic(_T(topic))
                        session.close()
            
            event.acceptProposedAction()
        else:
            event.ignore()
