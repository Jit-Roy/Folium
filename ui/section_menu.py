from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QHBoxLayout, 
    QListWidget, QListWidgetItem, QSizePolicy
)
from PySide6.QtGui import QIcon, QPixmap, QFontMetrics
from PySide6.QtCore import Qt, Signal, QSize

class WrappingLabel(QLabel):
    def __init__(self, text=""):
        super().__init__(text)
        self.setWordWrap(True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        
    def _update_height(self):
        if not self.text() or self.width() <= 0:
            return
        metrics = QFontMetrics(self.font())
        rect = metrics.boundingRect(0, 0, self.width(), 1000, 
                                   Qt.TextWordWrap | Qt.AlignLeft, self.text())
        # Add a tiny buffer so text doesn't clip vertically
        self.setFixedHeight(rect.height() + 2)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_height()
        
    def setText(self, text):
        super().setText(text)
        self._update_height()

class SectionMenu(QWidget):
    section_selected = Signal(str) # Emits the section name (e.g. "Notes")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(250)
        self.setMaximumWidth(300)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)

        # Header Title Area
        self.header_container = QWidget()
        self.header_container.setFixedHeight(55) # Locks the height so buttons below never jump
        
        self.header_layout = QVBoxLayout(self.header_container)
        self.header_layout.setContentsMargins(0, 0, 0, 0)
        self.header_layout.setAlignment(Qt.AlignTop)
        
        self.title_label = WrappingLabel("SELECT TOPIC")
        self.title_label.setStyleSheet("font-size: 11px; font-weight: bold; color: #888888; letter-spacing: 0.5px;")
        self.header_layout.addWidget(self.title_label)
        
        layout.addWidget(self.header_container)
        layout.addSpacing(15)

        # Cards List
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget { background: transparent; border: none; outline: none; }
            QListWidget::item { 
                background-color: #1A1A1A; 
                border: 1px solid #2D2D2D; 
                border-radius: 8px; 
            }
            QListWidget::item:hover {
                background-color: #242424;
            }
            QListWidget::item:selected {
                background-color: #2D2036;
                border: none;
            }
        """)
        self.list_widget.setSpacing(8)
        self.list_widget.itemSelectionChanged.connect(self.on_selection)
        layout.addWidget(self.list_widget)

    def load_topic_sections(self, topic):
        self.list_widget.clear()
        if not topic:
            self.title_label.setText("SELECT TOPIC")
            self.title_label.setToolTip("")
            return
            
        path = getattr(topic, 'path_str', topic.name)
        self.title_label.setText(path)
        self.title_label.setToolTip(path)
        
        # Hardcoding the structure as per requirements
        children_count = getattr(topic, 'children_count', len(getattr(topic, 'children', [])))
        sections = [
            ("NOTES", "5", "file-text"),
            ("QUESTIONS", "25", "help-circle"),
            ("RESOURCES", "7", "link"),
            ("IMAGES", "12", "image"),
            ("BOOKMARKS", "6", "bookmark"),
            ("FLASHCARDS", "18", "layers"),
            ("SUB TOPICS", str(children_count), "git-branch"),
            ("REFERENCED BY", "6", "link")
        ]
        
        for name, count, icon in sections:
            item_widget = QWidget()
            item_widget.setMinimumHeight(46) # Increased height
            item_layout = QHBoxLayout(item_widget)
            item_layout.setContentsMargins(15, 0, 15, 0) # 0 top/bottom margins for perfect vertical centering
            item_layout.setSpacing(10) # Good spacing between icon and title
            
            # Icon
            icon_label = QLabel()
            icon_pixmap = QIcon(f"assets/icons/{icon}.svg").pixmap(QSize(16, 16))
            icon_label.setPixmap(icon_pixmap)
            
            title = QLabel(name)
            title.setObjectName("title")
            
            count_label = QLabel(count)
            count_label.setObjectName("count")
            
            item_layout.addWidget(icon_label)
            item_layout.addWidget(title)
            item_layout.addStretch()
            item_layout.addWidget(count_label)
            
            # Default unselected style
            item_widget.setStyleSheet("""
                QWidget { background: transparent; }
                QLabel#title { color: #E0E0E0; font-weight: bold; font-size: 12px; border: none; }
                QLabel#count { color: #888888; font-size: 12px; border: none; }
            """)
            
            list_item = QListWidgetItem(self.list_widget)
            list_item.setSizeHint(QSize(item_widget.sizeHint().width(), 46)) # Explicitly force the 46px height
            self.list_widget.addItem(list_item)
            self.list_widget.setItemWidget(list_item, item_widget)
            
            # Store the section name
            list_item.setData(Qt.UserRole, name)
            
        # Select the first item ("NOTES") by default
        if self.list_widget.count() > 0:
            # Block signals briefly so it doesn't double-fire if we handle it in main.py, 
            # or just let it fire to keep it simple. Let's let it fire.
            self.list_widget.setCurrentRow(0)

    def on_selection(self):
        items = self.list_widget.selectedItems()
        
        # Update styles for all items based on selection state
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            widget = self.list_widget.itemWidget(item)
            if widget:
                if item.isSelected():
                    widget.setStyleSheet("""
                        QWidget { background: transparent; }
                        QLabel#title { color: #B48EAD; font-weight: bold; font-size: 12px; border: none; }
                        QLabel#count { color: #B48EAD; font-size: 12px; border: none; }
                    """)
                else:
                    widget.setStyleSheet("""
                        QWidget { background: transparent; }
                        QLabel#title { color: #E0E0E0; font-weight: bold; font-size: 12px; border: none; }
                        QLabel#count { color: #888888; font-size: 12px; border: none; }
                    """)
                    
        if items:
            section_name = items[0].data(Qt.UserRole)
            self.section_selected.emit(section_name)
