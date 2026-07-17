from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QHBoxLayout, 
    QListWidget, QListWidgetItem
)
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtCore import Qt, Signal, QSize

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

        # Header Title
        self.header_layout = QHBoxLayout()
        self.title_label = QLabel("SELECT TOPIC")
        self.title_label.setStyleSheet("font-size: 11px; font-weight: bold; color: #888888; letter-spacing: 1px; text-transform: uppercase;")
        self.header_layout.addWidget(self.title_label)
        self.header_layout.addStretch()
        
        self.options_btn = QLabel("...")
        self.options_btn.setStyleSheet("color: #888888; font-weight: bold;")
        # No more button in image, actually the image has `...` next to "ATTENTION" text. 
        self.header_layout.addWidget(self.options_btn)
        
        layout.addLayout(self.header_layout)

        # Cards List
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget { background: transparent; border: none; outline: none; }
            QListWidget::item { 
                background-color: #1A1A1A; 
                border: 1px solid #2D2D2D; 
                border-radius: 8px; 
                margin-bottom: 8px;
            }
            QListWidget::item:hover {
                background-color: #242424;
            }
            QListWidget::item:selected {
                background-color: #2D2036;
                border-left: 3px solid #B48EAD;
                border-top: 1px solid #4D305A;
                border-right: 1px solid #4D305A;
                border-bottom: 1px solid #4D305A;
            }
        """)
        self.list_widget.itemSelectionChanged.connect(self.on_selection)
        layout.addWidget(self.list_widget)

    def load_topic_sections(self, topic):
        self.list_widget.clear()
        if not topic:
            self.title_label.setText("SELECT TOPIC")
            return
            
        self.title_label.setText(topic.name)
        
        # Hardcoding the structure as per requirements
        sections = [
            ("NOTES", "My detailed notes", "5", "file-text"),
            ("QUESTIONS", "Important questions", "25", "help-circle"),
            ("RESOURCES", "Books, papers, videos, etc.", "7", "link"),
            ("IMAGES", "Diagrams & screenshots", "12", "image"),
            ("BOOKMARKS", "Useful web links", "6", "bookmark"),
            ("FLASHCARDS", "For quick revision", "18", "layers"),
            ("SUB TOPICS", "Multi Head Attention, KV Cache...", str(len(topic.children)), "git-branch"),
            ("REFERENCED BY", "Transformers, LLMs...", "6", "link")
        ]
        
        for name, desc, count, icon in sections:
            item_widget = QWidget()
            item_widget.setMinimumHeight(60)
            item_layout = QVBoxLayout(item_widget)
            item_layout.setContentsMargins(15, 10, 15, 10)
            
            top_layout = QHBoxLayout()
            
            # Icon
            icon_label = QLabel()
            icon_pixmap = QIcon(f"assets/icons/{icon}.svg").pixmap(QSize(16, 16))
            icon_label.setPixmap(icon_pixmap)
            
            title = QLabel(name)
            title.setStyleSheet("color: #E0E0E0; font-weight: bold; font-size: 12px; border: none;")
            
            count_label = QLabel(count)
            count_label.setStyleSheet("color: #888888; font-size: 12px; border: none;")
            
            top_layout.addWidget(icon_label)
            top_layout.addWidget(title)
            top_layout.addStretch()
            top_layout.addWidget(count_label)
            
            desc_label = QLabel(desc)
            desc_label.setStyleSheet("color: #666666; font-size: 11px; border: none; padding-left: 22px;")
            
            item_layout.addLayout(top_layout)
            item_layout.addWidget(desc_label)
            
            list_item = QListWidgetItem(self.list_widget)
            list_item.setSizeHint(item_widget.sizeHint())
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
        if items:
            section_name = items[0].data(Qt.UserRole)
            self.section_selected.emit(section_name)
