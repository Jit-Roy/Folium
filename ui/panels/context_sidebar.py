from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame
from PySide6.QtCore import Qt

class ContextSidebar(QWidget):
    """
    A simple, contextual sidebar for full-canvas dashboard pages 
    (Habits, Planner, Courses, Journal). 
    Replaces the default 'Notes' tree when these pages are active.
    """
    def __init__(self, title: str, subtitle: str = "Dashboard", parent=None):
        super().__init__(parent)
        self.setObjectName("contextSidebar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("""
            QWidget#contextSidebar { background: #181818; }
            .QWidget { background: transparent; }
        """)

        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignmentFlag.AlignTop)
        lay.setContentsMargins(20, 24, 20, 24)
        lay.setSpacing(8)

        lbl = QLabel(title)
        lbl.setStyleSheet("color: #ffffff; font-size: 13pt; font-weight: bold; letter-spacing: 0.5px; background: transparent;")
        lay.addWidget(lbl)

        desc = QLabel(subtitle)
        desc.setStyleSheet("color: #8e8e93; font-size: 10pt; background: transparent;")
        lay.addWidget(desc)

        # Thin divider
        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setFixedHeight(1)
        div.setStyleSheet("background: rgba(255,255,255,0.05); border: none; margin-top: 12px;")
        lay.addWidget(div)
