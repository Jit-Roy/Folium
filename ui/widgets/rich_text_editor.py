from PySide6.QtWidgets import QTextEdit, QWidget
from PySide6.QtGui import QTextCursor, QTextFormat, QDesktopServices, QPainter, QColor, QPen
from PySide6.QtCore import Qt, QUrl, QRect, QPoint, Signal

class ImageResizerOverlay(QWidget):
    def __init__(self, editor, cursor):
        super().__init__(editor.viewport())
        self.editor = editor
        self.target_cursor = cursor
        
        # Make transparent and draw on top
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setMouseTracking(True)
        
        self.handle_size = 8
        self.dragging = False
        self.drag_handle = None
        self.start_pos = None
        self.start_geometry = None
        
        self.update_geometry()
        
    def update_geometry(self):
        # Calculate exactly where the image is
        char_format = self.target_cursor.charFormat()
        if not char_format.isImageFormat():
            self.hide()
            return
            
        # Get visual position in the viewport from the start of the image
        start_cursor = QTextCursor(self.target_cursor)
        start_cursor.setPosition(self.target_cursor.selectionStart())
        rect = self.editor.cursorRect(start_cursor)
        
        image_format = char_format.toImageFormat()
        width = image_format.width()
        height = image_format.height()
        
        if width <= 0 or height <= 0:
            width = 300
            height = 300
            
        x = rect.x()
        y = rect.y()
        self.setGeometry(x, y, int(width), int(height))
        self.show()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setPen(QPen(QColor("#88C0D0"), 2, Qt.SolidLine))
        
        # Draw border
        rect = self.rect().adjusted(1, 1, -2, -2)
        painter.drawRect(rect)
        
        # Draw handles
        painter.setBrush(QColor("#88C0D0"))
        h_size = self.handle_size
        
        # Top-Left
        painter.drawRect(0, 0, h_size, h_size)
        # Top-Right
        painter.drawRect(self.rect().width() - h_size, 0, h_size, h_size)
        # Bottom-Left
        painter.drawRect(0, self.rect().height() - h_size, h_size, h_size)
        # Bottom-Right
        painter.drawRect(self.rect().width() - h_size, self.rect().height() - h_size, h_size, h_size)

    def _get_handle_at(self, pos):
        s = self.handle_size
        w, h = self.width(), self.height()
        handles = {
            "top_left": QRect(0, 0, s, s), "top_right": QRect(w-s, 0, s, s),
            "bottom_left": QRect(0, h-s, s, s), "bottom_right": QRect(w-s, h-s, s, s)
        }
        for name, rect in handles.items():
            if rect.contains(pos):
                return name
        return None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            handle = self._get_handle_at(event.position().toPoint())
            if handle:
                self.dragging = True
                self.drag_handle = handle
                self.start_pos = event.globalPosition().toPoint()
                self.start_geometry = self.geometry()
            else:
                # Pass click to editor if not clicking a handle
                event.ignore()
                self.hide()
        else:
            event.ignore()

    def mouseMoveEvent(self, event):
        handle = self._get_handle_at(event.position().toPoint())
        
        if handle in ["top_left", "bottom_right"]:
            self.setCursor(Qt.SizeFDiagCursor)
        elif handle in ["top_right", "bottom_left"]:
            self.setCursor(Qt.SizeBDiagCursor)
        else:
            self.setCursor(Qt.ArrowCursor)
            
        if self.dragging and self.start_pos:
            delta = event.globalPosition().toPoint() - self.start_pos
            new_rect = QRect(self.start_geometry)
            
            if "right" in self.drag_handle:
                new_w = max(50, self.start_geometry.width() + delta.x())
                new_w = min(new_w, self.editor.viewport().width() - self.start_geometry.x() - 5)
                new_rect.setWidth(new_w)
            elif "left" in self.drag_handle:
                new_left = min(self.start_geometry.right() - 50, self.start_geometry.left() + delta.x())
                new_left = max(5, new_left) # Prevent dragging past left edge
                new_rect.setLeft(new_left)
                
            if "bottom" in self.drag_handle:
                new_rect.setHeight(max(50, self.start_geometry.height() + delta.y()))
            elif "top" in self.drag_handle:
                new_rect.setTop(min(self.start_geometry.bottom() - 50, self.start_geometry.top() + delta.y()))
                
            self.setGeometry(new_rect)
            
    def mouseReleaseEvent(self, event):
        if self.dragging:
            # Apply final size to Document Image
            new_rect = self.geometry()
            char_format = self.target_cursor.charFormat()
            image_format = char_format.toImageFormat()
            image_format.setWidth(new_rect.width())
            image_format.setHeight(new_rect.height())
            
            pos = self.target_cursor.position()
            self.target_cursor.setPosition(pos)
            self.target_cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor)
            self.target_cursor.setCharFormat(image_format)
            
        self.dragging = False
        self.drag_handle = None
        self.update_geometry() # snap perfectly to updated image

from ui.widgets.floating_widgets import FloatingInput

class RichTextEditor(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.active_overlay = None
        
    def scrollContentsBy(self, dx, dy):
        super().scrollContentsBy(dx, dy)
        if self.active_overlay:
            self.active_overlay.hide()
            self.active_overlay = None
            
    def mousePressEvent(self, event):
        # Hide overlay on click anywhere
        if self.active_overlay:
            self.active_overlay.hide()
            self.active_overlay = None
            
        super().mousePressEvent(event)
        
        # Check for single click on Image
        pos = event.position().toPoint()
        cursor = self.cursorForPosition(pos)
        
        candidates = []
        c_right = QTextCursor(cursor)
        c_right.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor)
        if c_right.charFormat().isImageFormat():
            candidates.append(c_right)
            
        c_left = QTextCursor(cursor)
        c_left.movePosition(QTextCursor.Left, QTextCursor.KeepAnchor)
        if c_left.charFormat().isImageFormat():
            candidates.append(c_left)
            
        for c in candidates:
            start_cursor = QTextCursor(c)
            start_cursor.setPosition(c.selectionStart())
            rect = self.cursorRect(start_cursor)
            
            img_fmt = c.charFormat().toImageFormat()
            w = img_fmt.width() if img_fmt.width() > 0 else 300
            h = img_fmt.height() if img_fmt.height() > 0 else 300
            
            img_rect = QRect(rect.x(), rect.y(), int(w), int(h))
            if img_rect.contains(pos):
                if img_fmt.width() <= 0:
                    img_fmt.setWidth(300)
                    img_fmt.setHeight(300)
                    c.setCharFormat(img_fmt)
                self.active_overlay = ImageResizerOverlay(self, c)
                return
            
    def mouseDoubleClickEvent(self, event):
        pass # Remove old double click logic
        
    def mouseReleaseEvent(self, event):
        # Open links on click
        href = self.anchorAt(event.position().toPoint())
        if href:
            import webbrowser
            webbrowser.open(href)
            return
            
        super().mouseReleaseEvent(event)
        
        # Removed Ctrl+Scroll image logic since we have handles now
        
        # Interactive Checkboxes
        cursor = self.textCursor()
        
        def toggle_checkbox(target_cursor):
            char = "☑" if target_cursor.selectedText() == "☐" else "☐"
            cf = target_cursor.charFormat()
            font = cf.font()
            font.setFamily("Segoe UI Symbol")
            cf.setFont(font)
            target_cursor.insertText(char)
            # Re-select the inserted char to set the format correctly
            target_cursor.movePosition(QTextCursor.Left, QTextCursor.KeepAnchor)
            target_cursor.setCharFormat(cf)
            target_cursor.clearSelection()
            
        # Check char to the right
        cursor_right = QTextCursor(cursor)
        cursor_right.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor)
        if cursor_right.selectedText() in ["☐", "☑"]:
            toggle_checkbox(cursor_right)
            return
            
        # Check char to the left
        cursor_left = QTextCursor(cursor)
        cursor_left.movePosition(QTextCursor.Left, QTextCursor.KeepAnchor)
        if cursor_left.selectedText() in ["☐", "☑"]:
            toggle_checkbox(cursor_left)
            return
            
    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        
        # Change cursor on hover for links and checkboxes
        href = self.anchorAt(event.position().toPoint())
        if href:
            self.viewport().setCursor(Qt.PointingHandCursor)
            return
            
        cursor = self.cursorForPosition(event.position().toPoint())
        
        # Check char to the right
        cursor_right = QTextCursor(cursor)
        cursor_right.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor)
        
        # Check char to the left
        cursor_left = QTextCursor(cursor)
        cursor_left.movePosition(QTextCursor.Left, QTextCursor.KeepAnchor)
        
        if cursor_right.selectedText() in ["☐", "☑"] or cursor_left.selectedText() in ["☐", "☑"]:
            self.viewport().setCursor(Qt.PointingHandCursor)
        else:
            self.viewport().setCursor(Qt.IBeamCursor)
