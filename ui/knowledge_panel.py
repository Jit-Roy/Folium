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

        # Referenced By Section
        self.ref_header = QLabel("REFERENCED BY (0)")
        self.ref_header.setStyleSheet("font-size: 11px; font-weight: bold; color: #888888; letter-spacing: 1px; margin-top: 20px;")
        layout.addWidget(self.ref_header)

        # Using QScrollArea instead of QListWidget to fix overlapping issues
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        
        self.ref_container = QWidget()
        self.ref_container.setStyleSheet("background: transparent;")
        self.ref_layout = QVBoxLayout(self.ref_container)
        self.ref_layout.setContentsMargins(0, 0, 0, 0)
        self.ref_layout.setSpacing(0)
        self.ref_layout.addStretch()
        
        self.scroll_area.setWidget(self.ref_container)
        layout.addWidget(self.scroll_area)

    def load_references(self, topic):
        """Load references for the given topic from the database"""
        from core.database import get_session
        from core.models import NoteReference
        
        # Clear existing
        while self.ref_layout.count() > 1: # keep the stretch at the end
            item = self.ref_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        if not topic:
            self.ref_header.setText("REFERENCED BY (0)")
            return

        session = get_session()
        refs = session.query(NoteReference).filter(NoteReference.referenced_topic_id == topic.id).all()
        
        self.ref_header.setText(f"REFERENCED BY ({len(refs)})")
        
        for ref in refs:
            note = ref.note
            source_topic_name = note.topic.name if note.topic else "Unknown Note"
            
            item_widget = QWidget()
            item_widget.setMinimumHeight(40)
            item_widget.setStyleSheet("border-bottom: 1px solid #1E1E1E;")
            
            item_layout = QHBoxLayout(item_widget)
            item_layout.setContentsMargins(5, 5, 5, 5)
            
            dot = QLabel("●")
            dot.setStyleSheet("color: #A3BE8C; font-size: 14px; border: none;") # Muted green
            
            title = QLabel(source_topic_name)
            title.setStyleSheet("color: #E0E0E0; border: none;")
            
            meta = QLabel("Notes · 1 mention")
            meta.setStyleSheet("color: #666666; font-size: 11px; border: none;")
            
            arrow = QLabel(">")
            arrow.setStyleSheet("color: #444444; border: none;")
            
            item_layout.addWidget(dot)
            item_layout.addWidget(title)
            item_layout.addStretch()
            item_layout.addWidget(meta)
            item_layout.addWidget(arrow)
            
            # Insert before the stretch
            self.ref_layout.insertWidget(self.ref_layout.count() - 1, item_widget)
            
        session.close()
