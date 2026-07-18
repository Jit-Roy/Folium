from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QHBoxLayout, 
    QTabWidget, QScrollArea
)
from PySide6.QtCore import Qt

class KnowledgePanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(250)
        self.setMaximumWidth(350)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # Tabs for GRAPH and OUTLINE
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: none; }
            QTabBar::tab {
                background: transparent;
                color: #888888;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 11px;
                letter-spacing: 1px;
            }
            QTabBar::tab:selected {
                color: #B48EAD; /* Muted purple for active tab */
                border-bottom: 2px solid #B48EAD;
            }
        """)

        # Graph Tab
        self.graph_tab = QWidget()
        graph_layout = QVBoxLayout(self.graph_tab)
        graph_placeholder = QLabel("Graph Visualization\n(To be implemented with D3.js or QGraphicsScene)")
        graph_placeholder.setAlignment(Qt.AlignCenter)
        graph_placeholder.setWordWrap(True)
        graph_placeholder.setStyleSheet("color: #666666; border: 1px dashed #2D2D2D; border-radius: 8px; padding: 10px;")
        graph_layout.addWidget(graph_placeholder)
        self.tabs.addTab(self.graph_tab, "GRAPH")

        # Outline Tab
        self.outline_tab = QWidget()
        outline_layout = QVBoxLayout(self.outline_tab)
        outline_layout.addWidget(QLabel("Outline content here..."))
        self.tabs.addTab(self.outline_tab, "OUTLINE")

        layout.addWidget(self.tabs)

    def load_references(self, topic):
        """Load references for the given topic from the database"""
        pass
