from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QListWidget, QListWidgetItem, QSplitter, QStackedWidget
)
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QIcon

class TagRowWidget(QWidget):
    def __init__(self, tag_name, count, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        
        lbl = QLabel(f"#{tag_name}")
        lbl.setStyleSheet("color: #FFFFFF; font-size: 13px; background: transparent;")
        
        badge = QLabel(str(count))
        badge.setAlignment(Qt.AlignCenter)
        badge.setStyleSheet("""
            background-color: #2a2a2a;
            color: #FFFFFF;
            border-radius: 10px;
            font-size: 10px;
            font-weight: bold;
        """)
        badge.setFixedSize(20, 20)
        
        layout.addWidget(lbl)
        layout.addStretch()
        layout.addWidget(badge)

class AccordionHeader(QFrame):
    toggled = Signal(bool)
    
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.is_expanded = False
        self.setFixedHeight(48)
        self.setStyleSheet("""
            QFrame { background: transparent; border-top: 1px solid #2a2a2a; border-bottom: none; border-left: none; border-right: none; }
            QFrame:hover { background: #2a2d2e; }
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 0, 8, 0)
        layout.setSpacing(6)
        
        self.icon_lbl = QLabel("▸")
        self.icon_lbl.setStyleSheet("color: #FFFFFF; font-weight: bold; font-family: monospace; font-size: 14px; background: transparent; border: none;")
        self.icon_lbl.setFixedWidth(18)
        
        self.title_lbl = QLabel(title)
        self.title_lbl.setStyleSheet("color: #FFFFFF; font-size: 16px; font-weight: bold; background: transparent; border: none;")
        
        layout.addWidget(self.icon_lbl)
        layout.addWidget(self.title_lbl)
        layout.addStretch()
        
        self.setCursor(Qt.PointingHandCursor)
        
    def mousePressEvent(self, event):
        self.set_expanded(not self.is_expanded)

    def set_expanded(self, expanded: bool):
        if self.is_expanded != expanded:
            self.is_expanded = expanded
            self.icon_lbl.setText("▾" if self.is_expanded else "▸")
            self.toggled.emit(self.is_expanded)

class TagsPanel(QWidget):
    """
    Tags panel showing all workspace tags and their associated topics.
    Split view: Top half shows tags, bottom half shows filtered topics.
    """
    topic_selected = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._saved_splitter_sizes = [400, 200]
        self.init_ui()
        self.load_tags()

    def init_ui(self):
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("background-color: #181818;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Header ─────────────────────────────────────────────────────────
        header = QWidget()
        header.setFixedHeight(40)
        header.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1f1f1f, stop:1 #181818); border-bottom: 1px solid #2a2a2a;")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(10, 0, 8, 0)
        h_layout.setSpacing(10)

        title = QLabel("TAGS")
        title.setStyleSheet("font-size:11px; font-weight:700; color:#FFFFFF;")
        h_layout.addWidget(title)
        h_layout.addStretch()
        
        layout.addWidget(header)

        # ── Splitter ───────────────────────────────────────────────────────
        self.splitter = QSplitter(Qt.Vertical)
        self.splitter.setStyleSheet("QSplitter::handle { background: transparent; height: 1px; }")
        
        # Top: Tags Stack (List or Empty State)
        self.top_stack = QStackedWidget()
        
        self.tags_empty_state = QWidget()
        tags_empty_layout = QVBoxLayout(self.tags_empty_state)
        tags_empty_text = QLabel("No tags found.\n\nCreate a tag in the editor to see it here.")
        tags_empty_text.setWordWrap(True)
        tags_empty_text.setStyleSheet("color: #FFFFFF; font-size: 12px; padding: 20px;")
        tags_empty_text.setAlignment(Qt.AlignCenter)
        tags_empty_layout.addStretch()
        tags_empty_layout.addWidget(tags_empty_text)
        tags_empty_layout.addStretch()
        
        self.tags_list = QListWidget()
        self.tags_list.setStyleSheet("""
            QListWidget { background: transparent; border: none; outline: none; }
            QListWidget::item { border-radius: 4px; margin: 2px 8px; }
            QListWidget::item:hover { background-color: #222222; }
            QListWidget::item:selected { background-color: #1f1a24; border-left: 2px solid #b48ead; }
        """)
        self.tags_list.itemSelectionChanged.connect(self.on_tag_selected)
        
        self.top_stack.addWidget(self.tags_empty_state)
        self.top_stack.addWidget(self.tags_list)
        
        # Bottom: Topics Accordion
        self.bottom_container = QWidget()
        bottom_layout = QVBoxLayout(self.bottom_container)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(0)
        
        self.bottom_header = AccordionHeader("FILTERED TOPICS")
        bottom_layout.addWidget(self.bottom_header)
        
        self.bottom_stack = QStackedWidget()
        self.bottom_header.toggled.connect(self.toggle_accordion)
        
        self.empty_state = QWidget()
        empty_layout = QVBoxLayout(self.empty_state)
        empty_layout.setContentsMargins(0, 0, 0, 0)
        empty_text = QLabel("Select a tag above to see its topics.")
        empty_text.setWordWrap(True)
        empty_text.setStyleSheet("color: #FFFFFF; font-size: 12px; padding: 10px 20px;")
        empty_text.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        empty_layout.addWidget(empty_text)
        empty_layout.addStretch()
        
        # Bottom: Topics List
        self.topics_list = QListWidget()
        self.topics_list.setStyleSheet("""
            QListWidget { background: transparent; border: none; outline: none; padding: 0 8px; }
            QListWidget::item { color: #FFFFFF; padding: 8px; border-radius: 4px; margin-bottom: 2px; }
            QListWidget::item:hover { background-color: #2a2a2a; }
            QListWidget::item:selected { background-color: #242424; color: #ffffff; }
        """)
        self.topics_list.itemClicked.connect(self.on_topic_clicked)
        
        self.bottom_stack.addWidget(self.empty_state)
        self.bottom_stack.addWidget(self.topics_list)
        bottom_layout.addWidget(self.bottom_stack)
        
        self.splitter.addWidget(self.top_stack)
        self.splitter.addWidget(self.bottom_container)
        self.splitter.setSizes([400, 200])
        
        layout.addWidget(self.splitter)
        
        # Initialize collapsed state
        self.toggle_accordion(self.bottom_header.is_expanded)

    def toggle_accordion(self, expanded):
        self.bottom_stack.setVisible(expanded)
        if expanded:
            self.bottom_container.setMaximumHeight(16777215)
            self.splitter.setSizes(self._saved_splitter_sizes)
        else:
            current_sizes = self.splitter.sizes()
            if current_sizes[1] > 50:
                self._saved_splitter_sizes = current_sizes
            self.bottom_container.setMaximumHeight(48)

    def load_tags(self):
        from core.database import get_session
        from core.models import Tag
        
        self.tags_list.clear()
        self.topics_list.clear()
        
        session = get_session()
        tags = session.query(Tag).order_by(Tag.name).all()
        
        has_tags = False
        for tag in tags:
            count = len(tag.topics)
            if count > 0:
                has_tags = True
                item = QListWidgetItem()
                item.setData(Qt.UserRole, tag.id)
                widget = TagRowWidget(tag.name, count)
                item.setSizeHint(widget.sizeHint())
                self.tags_list.addItem(item)
                self.tags_list.setItemWidget(item, widget)
                
        if has_tags:
            self.top_stack.setCurrentIndex(1)
        else:
            self.top_stack.setCurrentIndex(0)
            
        session.close()

    def on_tag_selected(self):
        self.topics_list.clear()
        items = self.tags_list.selectedItems()
        if not items:
            self.bottom_stack.setCurrentIndex(0)
            return
            
        self.bottom_stack.setCurrentIndex(1)
        if not self.bottom_header.is_expanded:
            self.bottom_header.set_expanded(True)
            
        tag_id = items[0].data(Qt.UserRole)
        
        from core.database import get_session
        from core.models import Tag
        
        session = get_session()
        tag = session.query(Tag).get(tag_id)
        if tag:
            for topic in tag.topics:
                item = QListWidgetItem(topic.name)
                item.setData(Qt.UserRole, topic.id)
                item.setIcon(QIcon("assets/icons/file-text.svg"))
                self.topics_list.addItem(item)
                
        session.close()
        
    def on_topic_clicked(self, item):
        topic_id = item.data(Qt.UserRole)
        self.topic_selected.emit(topic_id)
