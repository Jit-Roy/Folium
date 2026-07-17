from PySide6.QtWidgets import QTextEdit, QWidget
from PySide6.QtGui import QTextCursor, QTextFormat, QDesktopServices, QPainter, QColor, QPen
from PySide6.QtCore import Qt, QUrl, QRect, QPoint, Signal, QTimer
import os
import logging
logging.basicConfig(filename='debug.log', level=logging.DEBUG, format='%(asctime)s - %(message)s')

class ImageResizerOverlay(QWidget):
    def __init__(self, editor, cursor):
        super().__init__(editor.viewport())
        self.editor = editor
        self.target_cursor = cursor
        
        # Make transparent and draw on top
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setMouseTracking(True)
        
        self.handle_size = 8
        self.padding = 4
        self.dragging = False
        self.drag_handle = None
        self.start_pos = QPoint()
        self.start_geometry = None
        self.setMouseTracking(True)
        
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
        
        logging.debug(f"[update_geometry] cursor pos: {self.target_cursor.position()}")
        logging.debug(f"[update_geometry] cursorRect: {rect.x()}, {rect.y()}, {rect.width()}, {rect.height()}")
        logging.debug(f"[update_geometry] img_fmt w/h: {width}x{height}")
        
        # Prevent ghost bounds from oversized images
        max_w = self.editor.viewport().width() - x - 5
        if width > max_w:
            logging.debug(f"[update_geometry] CLAMPING width from {width} to {max_w}")
            height = int(height * (max_w / width))
            width = max_w
            
            image_format.setWidth(width)
            image_format.setHeight(height)
            
            # Use a COPY of the cursor to prevent mutating the original position!
            c = QTextCursor(self.target_cursor)
            pos = c.position()
            c.setPosition(pos)
            c.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor)
            c.setCharFormat(image_format)
            
        p = self.padding
        logging.debug(f"[update_geometry] final overlay rect: x={x-p}, y={y-p}, w={width+2*p}, h={height+2*p}")
        self.setGeometry(x - p, y - p, int(width) + 2*p, int(height) + 2*p)
        self.show()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)
        
        p = self.padding
        w = self.rect().width() - 2*p
        h = self.rect().height() - 2*p
        
        # The rect of the image itself
        img_rect = QRect(p, p, w, h)
        
        # Draw the blue border exactly around the image
        painter.setPen(QPen(QColor("#B48EAD"), 2, Qt.SolidLine))
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(img_rect)
        
        # Draw the handles
        h_size = self.handle_size
        half = h_size // 2
        
        # Handle style: violet fill, no border
        painter.setBrush(QColor("#B48EAD"))
        painter.setPen(Qt.NoPen)
        
        def draw_handle(x, y):
            painter.drawRect(x - half, y - half, h_size, h_size)
            
        # Corners
        draw_handle(p, p) # Top-Left
        draw_handle(p + w, p) # Top-Right
        draw_handle(p, p + h) # Bottom-Left
        draw_handle(p + w, p + h) # Bottom-Right
        
        # Edges
        mid_w = p + w // 2
        mid_h = p + h // 2
        draw_handle(mid_w, p) # Top
        draw_handle(mid_w, p + h) # Bottom
        draw_handle(p, mid_h) # Left
        draw_handle(p + w, mid_h) # Right

    def _get_handle_at(self, pos):
        s = self.handle_size + 4 # slightly larger hitbox
        half = s // 2
        p = self.padding
        w = self.width() - 2*p
        h = self.height() - 2*p
        
        mid_w = p + w // 2
        mid_h = p + h // 2
        
        def r(x, y):
            return QRect(x - half, y - half, s, s)
            
        handles = {
            "top_left": r(p, p), "top_right": r(p+w, p),
            "bottom_left": r(p, p+h), "bottom_right": r(p+w, p+h),
            "top": r(mid_w, p), "bottom": r(mid_w, p+h),
            "left": r(p, mid_h), "right": r(p+w, mid_h)
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
                self.grabMouse()
            else:
                self.hide()
                self.deleteLater()
                event.ignore()
        else:
            event.ignore()

    def mouseMoveEvent(self, event):
        if not self.dragging:
            handle = self._get_handle_at(event.position().toPoint())
            if handle in ("top_left", "bottom_right"):
                self.setCursor(Qt.SizeFDiagCursor)
            elif handle in ("top_right", "bottom_left"):
                self.setCursor(Qt.SizeBDiagCursor)
            elif handle in ("left", "right"):
                self.setCursor(Qt.SizeHorCursor)
            elif handle in ("top", "bottom"):
                self.setCursor(Qt.SizeVerCursor)
            else:
                self.setCursor(Qt.ArrowCursor)
            return
            
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
                
            old_rect = self.geometry()
            logging.debug(f"[mouseMoveEvent] dragging {self.drag_handle}, new_rect: {new_rect}")
            self.setGeometry(new_rect)
            if self.parent():
                self.parent().repaint(old_rect)
            
    def mouseReleaseEvent(self, event):
        if self.dragging:
            new_rect = self.geometry()
            logging.debug(f"[mouseReleaseEvent] final applied size: {new_rect.width()}x{new_rect.height()}")
            char_format = self.target_cursor.charFormat()
            image_format = char_format.toImageFormat()
            
            p = self.padding
            image_format.setWidth(new_rect.width() - 2*p)
            image_format.setHeight(new_rect.height() - 2*p)
            
            # Use a COPY of the cursor to prevent mutating the original position!
            c = QTextCursor(self.target_cursor)
            pos = c.position()
            c.setPosition(pos)
            c.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor)
            c.setCharFormat(image_format)
            
        self.dragging = False
        self.drag_handle = None
        
        if hasattr(self, 'releaseMouse'):
            self.releaseMouse()
            
        # Give document layout engine time to finish calculating before snapping
        QTimer.singleShot(10, self.update_geometry)

from ui.widgets.floating_widgets import FloatingInput

class RichTextEditor(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.active_overlay = None
        
    def scrollContentsBy(self, dx, dy):
        super().scrollContentsBy(dx, dy)
        if self.active_overlay:
            if not getattr(self.active_overlay, 'dragging', False):
                self.active_overlay.update_geometry()
            
    def _get_image_cursor_at(self, pos):
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
            
            # Constrain click detection to viewport to prevent ghost clicks
            max_w = self.viewport().width() - rect.x() - 5
            if w > max_w:
                w = max_w
                
            p = 4
            img_rect = QRect(rect.x() - p, rect.y() - p, int(w) + 2*p, int(h) + 2*p)
            if img_rect.contains(pos):
                return c
        return None

    def mousePressEvent(self, event):
        # Hide overlay on click anywhere
        if self.active_overlay:
            self.active_overlay.hide()
            self.active_overlay.deleteLater()
            self.active_overlay = None
            
        super().mousePressEvent(event)
        
        # Check for single click on Image
        pos = event.position().toPoint()
        img_cursor = self._get_image_cursor_at(pos)
        
        if img_cursor:
            logging.debug(f"[mousePressEvent] HIT! Spawning overlay for image")
            img_fmt = img_cursor.charFormat().toImageFormat()
            if img_fmt.width() <= 0:
                img_fmt.setWidth(300)
                img_fmt.setHeight(300)
                img_cursor.setCharFormat(img_fmt)
            self.active_overlay = ImageResizerOverlay(self, img_cursor)
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
        
        pos = event.position().toPoint()
        
        # Change cursor on hover for images
        if self._get_image_cursor_at(pos):
            self.viewport().setCursor(Qt.SizeAllCursor)
            return
            
        # Change cursor on hover for links and checkboxes
        href = self.anchorAt(pos)
        if href:
            self.viewport().setCursor(Qt.PointingHandCursor)
            return
            
        cursor = self.cursorForPosition(pos)
        
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
