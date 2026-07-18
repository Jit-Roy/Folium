from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QHBoxLayout, 
    QListWidget, QListWidgetItem, QSizePolicy
)
from PySide6.QtGui import QIcon, QPixmap, QFontMetrics, QCursor
from PySide6.QtCore import Qt, Signal, QSize

class _BreadcrumbSegment(QLabel):
    """A single clickable breadcrumb segment."""
    clicked = Signal(int)

    def __init__(self, name: str, topic_id: int, is_active: bool):
        super().__init__(name)
        self._topic_id = topic_id
        self._is_active = is_active
        self._apply_style(False)
        if not is_active:
            self.setCursor(QCursor(Qt.PointingHandCursor))

    def _apply_style(self, hovered: bool):
        if self._is_active:
            self.setStyleSheet(
                "font-size: 12px; font-weight: bold; color: #E8E8E8;"
                " background: transparent; border: none;"
            )
        else:
            color = "#AAAAAA" if hovered else "#666666"
            self.setStyleSheet(
                f"font-size: 11px; font-weight: normal; color: {color};"
                " background: transparent; border: none;"
                " text-decoration: underline;"
            )

    def enterEvent(self, event):
        if not self._is_active:
            self._apply_style(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        if not self._is_active:
            self._apply_style(False)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and not self._is_active:
            self.clicked.emit(self._topic_id)
        super().mousePressEvent(event)


class FlowLayout(QHBoxLayout):
    """
    A layout that arranges widgets in a flow, wrapping to the next line
    when the available width is exceeded. Implemented as a custom QWidget
    subclass that manages its children manually.
    """
    pass  # See FlowContainer below


class FlowContainer(QWidget):
    """A widget that lays out children horizontally, wrapping to new rows."""

    def __init__(self, h_spacing=4, v_spacing=4, parent=None):
        super().__init__(parent)
        self._h_spacing = h_spacing
        self._v_spacing = v_spacing
        self._items = []  # list of QWidget
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

    def add_widget(self, widget):
        widget.setParent(self)
        self._items.append(widget)
        widget.show()
        # Immediately position to avoid flicker at (0,0)
        self._do_layout(self.contentsRect())
        self.updateGeometry()

    def clear(self):
        for w in self._items:
            w.setParent(None)
            w.deleteLater()
        self._items = []
        self.updateGeometry()

    def _do_layout(self, rect):
        x, y = rect.x(), rect.y()
        row_height = 0
        for widget in self._items:
            hint = widget.sizeHint()
            w, h = hint.width(), hint.height()
            if x + w > rect.right() + 1 and x > rect.x():
                x = rect.x()
                y += row_height + self._v_spacing
                row_height = 0
            widget.setGeometry(x, y, w, h)
            x += w + self._h_spacing
            row_height = max(row_height, h)
        return y + row_height - rect.y()

    def heightForWidth(self, width):
        return self._do_layout_width(width)

    def _do_layout_width(self, width):
        x, y, row_height = 0, 0, 0
        for widget in self._items:
            hint = widget.sizeHint()
            w, h = hint.width(), hint.height()
            if x + w > width and x > 0:
                x = 0
                y += row_height + self._v_spacing
                row_height = 0
            x += w + self._h_spacing
            row_height = max(row_height, h)
        return y + row_height

    def sizeHint(self):
        h = self._do_layout_width(self.width() or 200)
        return QSize(self.width(), h)

    def hasHeightForWidth(self):
        return True

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._do_layout(self.contentsRect())
        # Force parent to re-evaluate height
        if self.parent():
            self.parent().updateGeometry()

    def showEvent(self, event):
        super().showEvent(event)
        self._do_layout(self.contentsRect())


class BreadcrumbWidget(QWidget):
    """Renders a full breadcrumb path with styled chevrons that wrap to new lines."""
    segment_clicked = Signal(int)

    def __init__(self):
        super().__init__()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._flow = FlowContainer(h_spacing=3, v_spacing=3)
        outer.addWidget(self._flow)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

    def set_path(self, path_parts):
        """path_parts: list of (name, topic_id) tuples."""
        self._flow.clear()

        if not path_parts:
            placeholder = QLabel("SELECT TOPIC")
            placeholder.setStyleSheet(
                "font-size: 11px; font-weight: bold; color: #555555;"
                " background: transparent; border: none;"
            )
            self._flow.add_widget(placeholder)
            return

        for i, (name, topic_id) in enumerate(path_parts):
            is_active = (i == len(path_parts) - 1)
            seg = _BreadcrumbSegment(name, topic_id, is_active)
            seg.clicked.connect(self.segment_clicked.emit)
            self._flow.add_widget(seg)

            if not is_active:
                chevron = QLabel("›")
                chevron.setStyleSheet(
                    "font-size: 13px; color: #444444;"
                    " background: transparent; border: none;"
                )
                self._flow.add_widget(chevron)

        # Force a deferred layout re-pass to ensure correct positions after all widgets added
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, lambda: self._flow._do_layout(self._flow.contentsRect()))


class SectionMenu(QWidget):
    section_selected = Signal(str) # Emits the section name (e.g. "Notes")
    topic_navigated = Signal(int)  # Emits topic_id when a breadcrumb segment is clicked

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(250)
        self.setMaximumWidth(300)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 16, 10, 10)
        layout.setSpacing(15)

        # Breadcrumb header
        self.breadcrumb = BreadcrumbWidget()
        self.breadcrumb.segment_clicked.connect(self.topic_navigated.emit)
        layout.addWidget(self.breadcrumb)
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
            self.breadcrumb.set_path([])
            return
            
        path_parts = getattr(topic, 'path_parts', [(topic.name, getattr(topic, 'id', 0))])
        self.breadcrumb.set_path(path_parts)
        
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
