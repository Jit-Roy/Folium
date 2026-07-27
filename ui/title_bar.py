from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QLineEdit, QPushButton, QApplication
)
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt

class CustomTitleBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setFixedHeight(35)
        self.setObjectName("customTitleBar")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("""
            QWidget#customTitleBar {
                background-color: #1e1e1e;
            }
            QLabel {
                color: #cccccc;
            }
            QPushButton {
                border: none;
                background: transparent;
                color: #cccccc;
                font-family: 'Segoe MDL2 Assets';
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #2d2d2d;
            }
            QPushButton#closeBtn:hover {
                background-color: #e81123;
                color: white;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 0, 0, 0)
        layout.setSpacing(10)

        # App Icon
        icon_lbl = QLabel()
        icon_lbl.setStyleSheet("background: transparent;")
        icon_lbl.setPixmap(QIcon("assets/icons/app-icon.ico").pixmap(18, 18))
        layout.addWidget(icon_lbl)
        
        layout.addStretch(1)



        layout.addStretch(1)

        # Window Controls using Windows 10/11 Segoe MDL2 Assets
        min_btn = QPushButton("\uE921") 
        min_btn.setFixedSize(46, 35)
        min_btn.clicked.connect(self.parent.showMinimized)
        self.min_btn = min_btn
        
        max_btn = QPushButton("\uE922")
        max_btn.setFixedSize(46, 35)
        max_btn.clicked.connect(self.toggle_max_restore)
        self.max_btn = max_btn
        
        close_btn = QPushButton("\uE8BB")
        close_btn.setObjectName("closeBtn")
        close_btn.setFixedSize(46, 35)
        close_btn.clicked.connect(self.parent.close)
        self.close_btn = close_btn

        layout.addWidget(min_btn)
        layout.addWidget(max_btn)
        layout.addWidget(close_btn)
        layout.setContentsMargins(15, 0, 0, 0) 

    def toggle_max_restore(self):
        if getattr(self.parent, '_is_pseudo_maximized', False):
            if hasattr(self.parent, '_normal_geometry'):
                self.parent.setGeometry(self.parent._normal_geometry)
            self.parent._is_pseudo_maximized = False
            self.update_max_icon(False)
        else:
            self.parent._normal_geometry = self.parent.geometry()
            screen = QApplication.screenAt(self.parent.geometry().center())
            if screen:
                self.parent.setGeometry(screen.availableGeometry())
            self.parent._is_pseudo_maximized = True
            self.update_max_icon(True)

    def update_max_icon(self, is_maximized):
        if is_maximized:
            self.max_btn.setText("\uE923") # Restore Icon
        else:
            self.max_btn.setText("\uE922") # Maximize Icon

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and hasattr(self, '_drag_pos'):
            # Only allow dragging if not maximized
            if not getattr(self.parent, '_is_pseudo_maximized', False):
                diff = event.globalPosition().toPoint() - self._drag_pos
                self.parent.move(self.parent.pos() + diff)
                self._drag_pos = event.globalPosition().toPoint()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.toggle_max_restore()
