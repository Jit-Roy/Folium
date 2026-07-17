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
            
        # Get visual position in the viewport
        rect = self.editor.cursorRect(self.target_cursor)
        
        image_format = char_format.toImageFormat()
        width = image_format.width()
        height = image_format.height()
        
        if width <= 0 or height <= 0:
            # Fallback if properties not manually set
            self.hide()
            return
            
        # The cursorRect might be just a line, but its topLeft is usually correct
        # Wait, if we use cursorRect of the image character, width/height is usually available.
        # QTextEdit cursorRect for an image usually returns the width/height of the block line.
        # We'll build the overlay rect based on the image size and bottom-left/bottom-right of the rect
        
        # Actually, cursorRect for a character gives its bounding rect!
        x = rect.x()
        y = rect.y()
        self.setGeometry(x, y, int(width), int(height))
        self.show()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw Border
        pen = QPen(QColor("#88C0D0"))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(0, 0, self.width() - 1, self.height() - 1)
        
        # Draw Corner Handles
        painter.setBrush(QColor("#88C0D0"))
        painter.setPen(Qt.NoPen)
        s = self.handle_size
        w, h = self.width(), self.height()
        
        handles = [
            QRect(0, 0, s, s), QRect(w-s, 0, s, s),
            QRect(0, h-s, s, s), QRect(w-s, h-s, s, s)
        ]
        
        for handle in handles:
            painter.drawRect(handle)

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
            
            # Maintain Aspect Ratio roughly, or just scale width/height
            if "right" in self.drag_handle:
                new_rect.setWidth(max(50, self.start_geometry.width() + delta.x()))
            elif "left" in self.drag_handle:
                new_rect.setLeft(min(self.start_geometry.right() - 50, self.start_geometry.left() + delta.x()))
                
            if "bottom" in self.drag_handle:
                new_rect.setHeight(max(50, self.start_geometry.height() + delta.y()))
            elif "top" in self.drag_handle:
                new_rect.setTop(min(self.start_geometry.bottom() - 50, self.start_geometry.top() + delta.y()))
                
            self.setGeometry(new_rect)
            
            # Update Document Image instantly
            char_format = self.target_cursor.charFormat()
            image_format = char_format.toImageFormat()
            image_format.setWidth(new_rect.width())
            image_format.setHeight(new_rect.height())
            
            pos = self.target_cursor.position()
            self.target_cursor.setPosition(pos)
            self.target_cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor)
            self.target_cursor.setCharFormat(image_format)
            
    def mouseReleaseEvent(self, event):
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
        cursor = self.cursorForPosition(event.position().toPoint())
        cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor)
        char_format = cursor.charFormat()
        
        if char_format.isImageFormat():
            # Calculate explicitly stored size if possible to init properly
            img_fmt = char_format.toImageFormat()
            if img_fmt.width() <= 0:
                # Set a default size so we can grab it
                img_fmt.setWidth(300)
                img_fmt.setHeight(300)
                cursor.setCharFormat(img_fmt)
                
            self.active_overlay = ImageResizerOverlay(self, cursor)
            
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
        
        # Check char to the right
        cursor_right = QTextCursor(cursor)
        cursor_right.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor)
        if cursor_right.selectedText() in ["☐", "☑"]:
            char = "☑" if cursor_right.selectedText() == "☐" else "☐"
            cursor_right.insertText(char)
            return
            
        # Check char to the left
        cursor_left = QTextCursor(cursor)
        cursor_left.movePosition(QTextCursor.Left, QTextCursor.KeepAnchor)
        if cursor_left.selectedText() in ["☐", "☑"]:
            char = "☑" if cursor_left.selectedText() == "☐" else "☐"
            cursor_left.insertText(char)
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
