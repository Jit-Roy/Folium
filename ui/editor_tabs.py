from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget, QLabel
)
from PySide6.QtCore import Qt, Signal
from ui.editor import NoteEditor

class EditorTabs(QWidget):
    """
    Manages multiple NoteEditor instances in a VS Code-style tabbed interface.
    Supports drag and drop from the notes tree.
    """
    active_topic_changed = Signal(object) # Emits the topic object (or None)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.editors = {} # Maps topic_id to NoteEditor instance
        self.topic_map = {} # Maps topic_id to Topic object
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setDocumentMode(True)
        self.tab_widget.setMovable(True)
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background: #121212;
            }
            QTabBar::tab {
                background: #181818;
                color: #888888;
                padding: 8px 12px;
                border: none;
                border-right: 1px solid #2a2a2a;
                font-size: 13px;
                min-width: 100px;
                max-width: 200px;
            }
            QTabBar::tab:hover {
                background: #1f1f1f;
                color: #cccccc;
            }
            QTabBar::tab:selected {
                background: #121212;
                color: #ffffff;
                border-bottom: 2px solid #B48EAD;
            }
            QTabBar::close-button {
                image: url(assets/icons/x.svg); /* Close icon placeholder */
                subcontrol-position: right;
                subcontrol-origin: padding;
            }
            QTabBar::close-button:hover {
                background: rgba(255,255,255,0.1);
                border-radius: 2px;
            }
            /* Fill the rest of the tab bar area */
            QTabWidget::tab-bar {
                alignment: left;
            }
        """)

        # Add a placeholder when empty
        self.empty_label = QLabel("Drag a note here or click one in the Explorer")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet("color: #555555; font-size: 16px; font-style: italic;")
        
        self.stacked = QVBoxLayout()
        self.stacked.addWidget(self.empty_label)
        self.stacked.addWidget(self.tab_widget)
        self.tab_widget.hide()
        
        layout.addLayout(self.stacked)

        self.tab_widget.tabCloseRequested.connect(self._on_tab_close)
        self.tab_widget.currentChanged.connect(self._on_tab_changed)

        # Enable Drag and Drop
        self.setAcceptDrops(True)

    # ── Public API ─────────────────────────────────────────────────────────

    def open_topic(self, topic, section="NOTES"):
        """Opens a topic in a new tab or switches to it if already open."""
        if not topic:
            return

        topic_id = getattr(topic, 'id', topic)
        
        if topic_id in self.editors:
            # Switch to existing tab
            editor = self.editors[topic_id]
            idx = self.tab_widget.indexOf(editor)
            if idx >= 0:
                self.tab_widget.setCurrentIndex(idx)
            # Switch section if needed
            editor.load_topic(topic, section)
        else:
            # Create new tab
            editor = NoteEditor()
            editor.load_topic(topic, section)
            
            # Add to map
            self.editors[topic_id] = editor
            self.topic_map[topic_id] = topic
            
            idx = self.tab_widget.addTab(editor, getattr(topic, 'name', 'Note'))
            self.tab_widget.setTabToolTip(idx, getattr(topic, 'name', 'Note'))
            self.tab_widget.setCurrentIndex(idx)
            
        self._update_visibility()

    def get_current_editor(self):
        """Returns the currently active NoteEditor."""
        idx = self.tab_widget.currentIndex()
        if idx >= 0:
            return self.tab_widget.widget(idx)
        return None

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

    def _on_tab_close(self, index):
        editor = self.tab_widget.widget(index)
        if editor:
            # Force save before closing
            editor.save_note()
            topic_id = editor.current_topic_id
            if topic_id in self.editors:
                del self.editors[topic_id]
            if topic_id in self.topic_map:
                del self.topic_map[topic_id]
                
        self.tab_widget.removeTab(index)

    def close_topic_without_saving(self, topic_id):
        """Forcefully close a tab without triggering a save. Used when a topic is deleted."""
        if topic_id in self.editors:
            editor = self.editors[topic_id]
            idx = self.tab_widget.indexOf(editor)
            
            # Remove references first so that when removeTab fires currentChanged, it doesn't find it
            del self.editors[topic_id]
            if topic_id in self.topic_map:
                del self.topic_map[topic_id]
                
            if idx >= 0:
                self.tab_widget.removeTab(idx)
        self._update_visibility()
        
    def _on_tab_changed(self, index):
        from PySide6.QtCore import QTimer
        def emit_change():
            topic = self.get_current_topic()
            self.active_topic_changed.emit(topic)
        QTimer.singleShot(0, emit_change)

    def _update_visibility(self):
        has_tabs = self.tab_widget.count() > 0
        self.tab_widget.setVisible(has_tabs)
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
