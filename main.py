import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QSplitter, QVBoxLayout, QWidget
from PySide6.QtCore import Qt

from ui.theme import MAIN_QSS
from ui.topic_explorer import TopicExplorer
from ui.section_menu import SectionMenu
from ui.editor import NoteEditor
from ui.knowledge_panel import KnowledgePanel
from ui.top_bar import TopBar
from core.database import init_db, get_session
from core.models import Topic

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Study Notebook")
        self.resize(1600, 900)
        self.current_topic = None
        self.init_ui()

    def init_ui(self):
        # Create Main Splitter (Left Explorer vs Everything Else)
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.setCentralWidget(self.main_splitter)
        
        # Panel 1: Topic Explorer
        self.explorer_panel = TopicExplorer()
        self.main_splitter.addWidget(self.explorer_panel)
        
        # Right Side Container (TopBar + Inner Splitter)
        self.right_container = QWidget()
        self.right_layout = QVBoxLayout(self.right_container)
        self.right_layout.setContentsMargins(0, 0, 0, 0)
        self.right_layout.setSpacing(0)
        
        # Top Bar
        self.top_bar = TopBar()
        self.right_layout.addWidget(self.top_bar)
        
        # Inner Splitter (Section Menu, Editor, Knowledge Panel)
        self.inner_splitter = QSplitter(Qt.Horizontal)
        
        # Panels 2, 3, 4
        self.section_menu = SectionMenu()
        self.editor_panel = NoteEditor()
        self.knowledge_panel = KnowledgePanel()
        
        self.inner_splitter.addWidget(self.section_menu)
        self.inner_splitter.addWidget(self.editor_panel)
        self.inner_splitter.addWidget(self.knowledge_panel)
        
        # Set stretch factors for inner splitter
        self.inner_splitter.setStretchFactor(0, 1) # Section menu (narrow)
        self.inner_splitter.setStretchFactor(1, 4) # Editor (wide)
        self.inner_splitter.setStretchFactor(2, 2) # Knowledge (medium)
        self.inner_splitter.setCollapsible(0, False)
        self.inner_splitter.setCollapsible(1, False)
        self.inner_splitter.setCollapsible(2, False)
        
        self.right_layout.addWidget(self.inner_splitter)
        self.main_splitter.addWidget(self.right_container)
        
        # Main Splitter config
        self.main_splitter.setStretchFactor(0, 1)
        self.main_splitter.setStretchFactor(1, 7)
        self.main_splitter.setCollapsible(0, False)
        self.main_splitter.setCollapsible(1, False)

        # Wire signals
        self.explorer_panel.topic_selected.connect(self.on_topic_selected)
        self.section_menu.section_selected.connect(self.on_section_selected)
        
        # Load data AFTER signals are wired so that auto-selection triggers the editor load
        self.explorer_panel.load_topics_from_db()

    def on_topic_selected(self, topic_id):
        session = get_session()
        topic = session.get(Topic, topic_id)
        
        if topic:
            class SimpleTopic:
                def __init__(self, t_id, t_name):
                    self.id = t_id
                    self.name = t_name
            
            self.current_topic = SimpleTopic(topic.id, topic.name)
            
            # Generate breadcrumb string
            path = []
            curr = topic
            # simple single path for breadcrumbs
            while curr:
                path.append(curr.name)
                curr = curr.parents[0] if curr.parents else None
            path.reverse()
            breadcrumb = " > ".join(path)
            self.top_bar.set_breadcrumb(breadcrumb)
            
            # Load panels
            self.section_menu.load_topic_sections(topic)
            self.editor_panel.load_topic(self.current_topic, section="NOTES") # default section
            self.knowledge_panel.load_references(topic)
            
        session.close()

    def on_section_selected(self, section_name):
        if self.current_topic:
            # We don't need to re-query the topic from DB since editor just needs id and name
            self.editor_panel.load_topic(self.current_topic, section=section_name)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    init_db()
    app.setStyleSheet(MAIN_QSS)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
