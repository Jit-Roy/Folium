from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem, QLabel
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor

class OutlineItemWidget(QWidget):
    def __init__(self, badge: str, text: str, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        self.setMinimumHeight(34)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(12)
        
        self.badge_label = QLabel(f"[{badge}]")
        self.badge_label.setFixedWidth(55)
        self.badge_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.badge_label.setStyleSheet("color: #B48EAD; font-weight: bold; font-size: 12px;")
        
        self.text_label = QLabel(text)
        self.text_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.text_label.setStyleSheet("color: #FFFFFF; font-size: 14px;")
        
        layout.addWidget(self.badge_label)
        layout.addWidget(self.text_label, stretch=1)

class OutlinePanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.active_editor = None
        self._init_ui()
        
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        self.title = QLabel("Table of Contents")
        self.title.setStyleSheet("color: #FFFFFF; font-size: 16px; font-weight: bold;")
        layout.addWidget(self.title)
        
        self.list_widget = QListWidget()
        self.list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list_widget.setStyleSheet("""
            QListWidget {
                background: transparent;
                border: none;
                outline: none;
            }
            QListWidget::item { 
                color: #FFFFFF;
                border-radius: 4px;
            }
            QListWidget::item:hover { background: #1a1a1a; color: #FFFFFF; }
            QListWidget::item:selected { background: rgba(180,142,173,0.15); color: #B48EAD; font-weight: bold; }
        """)
        self.list_widget.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self.list_widget, stretch=1)
        
        self.empty_label = QLabel("No headings found.")
        self.empty_label.setStyleSheet("color: #666; font-size: 12px; font-style: italic;")
        self.empty_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.empty_label)
        
        self.list_widget.hide()
        self.title.hide()
        
    def set_active_editor(self, editor):
        if self.active_editor and hasattr(self.active_editor, 'editor'):
            try:
                self.active_editor.editor.textChanged.disconnect(self.refresh_outline)
            except Exception:
                pass
                
        self.active_editor = editor
        
        if self.active_editor and hasattr(self.active_editor, 'editor'):
            self.active_editor.editor.textChanged.connect(self.refresh_outline)
            
        self.refresh_outline()
        
    def refresh_outline(self):
        self.list_widget.clear()
        
        if not self.active_editor or not hasattr(self.active_editor, 'editor'):
            self.empty_label.show()
            self.list_widget.hide()
            return
            
        doc = self.active_editor.editor.document()
        block = doc.begin()
        
        headings_found = False
        seen_tables = set()
        previous_badge = None
        
        while block.isValid():
            text = block.text().strip()
            
            # Check for Table
            cursor = QTextCursor(block)
            table = cursor.currentTable()
            
            badge = None
            display_text = text
            current_type = None
            
            if table:
                current_type = "Table"
                if table not in seen_tables:
                    seen_tables.add(table)
                    badge = "Table"
                    display_text = "Table"
            else:
                # Check for List
                if block.textList():
                    current_type = "List"
                    if previous_badge != "List":
                        badge = "List"
                        display_text = display_text if display_text else "List Item"
                else:
                    # Scan fragments for images, links and font sizes
                    has_image = False
                    has_link = False
                    max_size = 0
                    it = block.begin()
                    while not it.atEnd():
                        fragment = it.fragment()
                        if fragment.isValid():
                            fmt = fragment.charFormat()
                            if fmt.isImageFormat():
                                has_image = True
                            if fmt.isAnchor() and fmt.anchorHref():
                                has_link = True
                            size = fmt.fontPointSize()
                            if size > max_size:
                                max_size = size
                        it += 1
                        
                    if has_image:
                        current_type = "Img"
                        badge = "Img"
                        display_text = "Image"
                    elif has_link:
                        current_type = "Link"
                        badge = "Link"
                    elif max_size >= 24:
                        current_type = "H1"
                        badge = "H1"
                    elif max_size >= 20:
                        current_type = "H2"
                        badge = "H2"
                    elif max_size >= 16:
                        current_type = "H3"
                        badge = "H3"
                    elif text:
                        current_type = "Para"
                        if previous_badge != "Para":
                            badge = "Para"
                            
            if current_type is not None:
                previous_badge = current_type
                        
            if badge and display_text:
                headings_found = True
                
                # Truncate text for UI cleanliness
                if len(display_text) > 40:
                    display_text = display_text[:40] + "..."
                    
                item = QListWidgetItem(self.list_widget)
                widget = OutlineItemWidget(badge, display_text)
                
                item.setSizeHint(widget.sizeHint())
                item.setData(Qt.UserRole, block.position())
                
                self.list_widget.setItemWidget(item, widget)
                
            block = block.next()
            
        if headings_found:
            self.empty_label.hide()
            self.title.show()
            self.list_widget.show()
        else:
            self.empty_label.show()
            self.title.hide()
            self.list_widget.hide()
            
    def _on_item_clicked(self, item):
        if not self.active_editor:
            return
            
        pos = item.data(Qt.UserRole)
        if pos is not None:
            cursor = QTextCursor(self.active_editor.editor.document())
            cursor.setPosition(pos)
            self.active_editor.editor.setTextCursor(cursor)
            self.active_editor.editor.ensureCursorVisible()
            self.active_editor.editor.setFocus()
