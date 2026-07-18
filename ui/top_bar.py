from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QLineEdit, QPushButton
)
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt

class TopBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(60)
        self.setStyleSheet("background-color: #121212; border-bottom: 1px solid #1E1E1E;")
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(15)

        # Navigation
        self.nav_left = QPushButton()
        self.nav_left.setIcon(QIcon("assets/icons/chevron-left.svg"))
        self.nav_right = QPushButton()
        self.nav_right.setIcon(QIcon("assets/icons/chevron-right.svg"))
        for btn in (self.nav_left, self.nav_right):
            btn.setFixedSize(30, 30)
            btn.setStyleSheet("border: none; background: transparent; font-size: 16px; color: #666666;")
        
        layout.addWidget(self.nav_left)
        layout.addWidget(self.nav_right)

        # Breadcrumbs
        self.breadcrumb_label = QLabel("")
        self.breadcrumb_label.setStyleSheet("color: #E0E0E0; font-size: 13px; border: none;")
        layout.addWidget(self.breadcrumb_label)
        
        layout.addStretch()

        # Search Bar
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search anything...")
        self.search_box.setFixedSize(300, 32)
        # We can add search icon via QAction or just style, but for simplicity just padding
        self.search_box.setStyleSheet("""
            QLineEdit {
                background-color: #1A1A1A;
                border: 1px solid #2D2D2D;
                border-radius: 6px;
                padding: 5px 15px;
                color: #FFFFFF;
            }
        """)
        self.search_box.addAction(QIcon("assets/icons/search.svg"), QLineEdit.LeadingPosition)
        layout.addWidget(self.search_box)
        
        layout.addStretch()



    def set_breadcrumb(self, text):
        # We can format it nicely
        self.breadcrumb_label.setText(text)
