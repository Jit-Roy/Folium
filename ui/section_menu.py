from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QHBoxLayout, 
    QListWidget, QListWidgetItem
)
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt, Signal, QSize

class SectionMenu(QWidget):
    section_selected = Signal(str) # Emits the section name (e.g. "Notes")
    # Breadcrumb navigated signal is removed from here since breadcrumb is relocated

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(50)  # Thin icon-only bar
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 16, 0, 10)
        layout.setSpacing(0)

        # Cards List
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget { background: transparent; border: none; outline: none; }
            QListWidget::item { 
                background-color: transparent; 
                border-left: 3px solid transparent; 
            }
            QListWidget::item:hover {
                background-color: #242424;
            }
            QListWidget::item:selected {
                background-color: rgba(180, 142, 173, 0.1);
                border-left: 3px solid #B48EAD;
            }
        """)
        self.list_widget.setSpacing(5)
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list_widget.itemSelectionChanged.connect(self.on_selection)
        layout.addWidget(self.list_widget)

    def load_topic_sections(self, topic, current_section="NOTES"):
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        if not topic:
            self.list_widget.blockSignals(False)
            return
            
        # Hardcoding the structure as per requirements
        children_count = getattr(topic, 'children_count', len(getattr(topic, 'children', [])))
        sections = [
            ("NOTES", "5", "file-text"),
            ("QUESTIONS", "25", "help-circle"),
            ("RESOURCES", "7", "link"),
            ("IMAGES", "12", "image"),
            ("FLASHCARDS", "18", "layers"),
            ("SUB TOPICS", str(children_count), "git-branch")
        ]
        
        target_row = 0
        for i, (name, count, icon) in enumerate(sections):
            item_widget = QWidget()
            item_widget.setFixedSize(50, 50)
            item_layout = QVBoxLayout(item_widget)
            item_layout.setContentsMargins(0, 0, 0, 0)
            item_layout.setAlignment(Qt.AlignCenter)
            
            # Icon
            icon_label = QLabel()
            icon_pixmap = QIcon(f"assets/icons/{icon}.svg").pixmap(QSize(20, 20))
            icon_label.setPixmap(icon_pixmap)
            item_layout.addWidget(icon_label)
            
            list_item = QListWidgetItem(self.list_widget)
            list_item.setSizeHint(QSize(50, 50))
            list_item.setToolTip(f"{name} ({count})")
            
            self.list_widget.addItem(list_item)
            self.list_widget.setItemWidget(list_item, item_widget)
            
            # Store the section name
            list_item.setData(Qt.UserRole, name)
            if name == current_section:
                target_row = i
            
        # Select the target item
        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(target_row)
        self.list_widget.blockSignals(False)

    def on_selection(self):
        items = self.list_widget.selectedItems()
        if items:
            section_name = items[0].data(Qt.UserRole)
            self.section_selected.emit(section_name)
