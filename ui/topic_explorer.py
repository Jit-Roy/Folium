from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTreeView, QLineEdit, 
    QLabel, QFrame, QHBoxLayout, QPushButton, QHeaderView, QMessageBox
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QStandardItemModel, QStandardItem, QIcon

class TopicExplorer(QWidget):
    topic_selected = Signal(int) # Emits the topic ID when selected

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(250)
        self.setMaximumWidth(350)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 20, 10, 10)
        layout.setSpacing(10)

        # Header with branding
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(10, 0, 10, 10)
        
        menu_btn = QPushButton()
        menu_btn.setIcon(QIcon("assets/icons/menu.svg"))
        menu_btn.setFixedSize(24, 24)
        menu_btn.setStyleSheet("border: none; background: transparent;")
        
        book_icon = QLabel()
        book_icon.setPixmap(QIcon("assets/icons/book.svg").pixmap(QSize(16, 16)))
        
        title_label = QLabel("Study Notebook")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #FFFFFF;")
        
        header_layout.addWidget(menu_btn)
        header_layout.addSpacing(5)
        header_layout.addWidget(book_icon)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Fixed items (Daily Notes, Tags, Bookmarks)
        self.fixed_model = QStandardItemModel()
        
        fixed_items_data = [
            ("Daily Notes", "file.svg"),
            ("All Notes", "file.svg"),
            ("Bookmarks", "bookmark.svg"),
            ("Tags", "tag.svg"),
            ("Trash", "trash.svg")
        ]
        
        for name, icon_file in fixed_items_data:
            item = QStandardItem(name)
            item.setIcon(QIcon(f"assets/icons/{icon_file}"))
            self.fixed_model.invisibleRootItem().appendRow(item)
            
        self.fixed_view = QTreeView()
        self.fixed_view.setModel(self.fixed_model)
        self.fixed_view.setHeaderHidden(True)
        self.fixed_view.setMaximumHeight(150)
        self.fixed_view.setStyleSheet("""
            QTreeView { background: transparent; border: none; outline: none; }
            QTreeView::item { padding: 4px; color: #FFFFFF; }
            QTreeView::item:hover { background: #242424; border-radius: 4px; }
            QTreeView::item:selected { background: #2D2036; color: #B48EAD; border-radius: 4px; }
        """)
        layout.addWidget(self.fixed_view)

        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("background-color: #2D2D2D;")
        layout.addWidget(line)

        # Topics Label
        topics_header = QHBoxLayout()
        topics_header.setContentsMargins(10, 10, 10, 0)
        topics_label = QLabel("TOPICS")
        topics_label.setStyleSheet("font-size: 11px; font-weight: bold; color: #FFFFFF; letter-spacing: 1px;")
        
        btn_style = """
            QPushButton { border: none; background: transparent; border-radius: 4px; }
            QPushButton:hover { background: rgba(255, 255, 255, 0.1); }
        """
        
        self.add_btn = QPushButton()
        self.add_btn.setIcon(QIcon("assets/icons/plus.svg"))
        self.add_btn.setFixedSize(24, 24)
        self.add_btn.setStyleSheet(btn_style)
        self.add_btn.clicked.connect(self.add_topic_prompt)
        
        topics_header.addWidget(topics_label)
        topics_header.addStretch()
        topics_header.addWidget(self.add_btn)
        layout.addLayout(topics_header)

        # Inline Input for New Topic (Hidden by default)
        self.new_topic_input = QLineEdit()
        self.new_topic_input.setPlaceholderText("Enter topic name...")
        self.new_topic_input.setStyleSheet("""
            QLineEdit {
                background-color: #1A1A1A;
                border: 1px solid #B48EAD;
                border-radius: 4px;
                padding: 4px 8px;
                color: #FFFFFF;
                margin: 0px 10px;
            }
        """)
        self.new_topic_input.hide()
        self.new_topic_input.returnPressed.connect(self.commit_new_topic)
        # If user clicks away without pressing enter, we can hide it or keep it.
        # Let's just keep it simple, they have to press enter or clear it to hide.
        layout.addWidget(self.new_topic_input)

        # Topic Tree
        self.topic_model = QStandardItemModel()
        self.topic_model.setColumnCount(2)
        
        self.topic_view = QTreeView()
        self.topic_view.setModel(self.topic_model)
        self.topic_view.setHeaderHidden(True)
        self.topic_view.setIndentation(12) # Reduced indentation to save horizontal space
        self.topic_view.header().setStretchLastSection(False)
        self.topic_view.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.topic_view.header().setSectionResizeMode(1, QHeaderView.Fixed)
        self.topic_view.setColumnWidth(1, 50)
        self.topic_view.setSelectionBehavior(QTreeView.SelectRows)
        self.topic_view.setStyleSheet("""
            QTreeView { background: transparent; border: none; outline: none; show-decoration-selected: 1; }
            QTreeView::item { padding: 4px; color: #FFFFFF; margin: 0px; border: none; border-radius: 0px; }
            QTreeView::item:selected { background: #2D2036; color: #B48EAD; }
            
            QTreeView::branch { background: #121212; border-image: none; image: none; }
            QTreeView::branch:selected { background: #2D2036; }
            
            QTreeView::branch:has-children:hover { background: #2A2A2A; }
            QTreeView::branch:has-children:selected:hover { background: #42354B; }
            
            QTreeView::branch:has-children:closed {
                image: url(assets/icons/chevron-right.svg);
            }
            QTreeView::branch:has-children:open {
                image: url(assets/icons/chevron-down.svg);
            }
            QTreeView QLineEdit { background: #1A1A1A; color: #FFFFFF; border: 1px solid #B48EAD; border-radius: 4px; padding: 2px; }
        """)
        self.topic_view.selectionModel().selectionChanged.connect(self.on_selection_changed)
        self.topic_model.itemChanged.connect(self.on_item_changed)
        layout.addWidget(self.topic_view)

        # Bottom Toggle Bar
        bottom_bar = QHBoxLayout()
        bottom_bar.setContentsMargins(10, 10, 10, 10)
        
        settings_btn = QPushButton()
        settings_btn.setIcon(QIcon("assets/icons/settings.svg"))
        settings_btn.setFixedSize(24, 24)
        settings_btn.setStyleSheet("border: none; background: transparent;")
        
        sun_icon = QLabel()
        sun_icon.setPixmap(QIcon("assets/icons/sun.svg").pixmap(QSize(16, 16)))
        
        toggle_icon = QLabel()
        toggle_icon.setPixmap(QIcon("assets/icons/toggle.svg").pixmap(QSize(32, 16)))
        
        moon_icon = QLabel()
        moon_icon.setPixmap(QIcon("assets/icons/moon.svg").pixmap(QSize(16, 16)))
        
        bottom_bar.addWidget(settings_btn)
        bottom_bar.addStretch()
        bottom_bar.addWidget(sun_icon)
        bottom_bar.addSpacing(5)
        bottom_bar.addWidget(toggle_icon)
        bottom_bar.addSpacing(5)
        bottom_bar.addWidget(moon_icon)
        
        
        layout.addLayout(bottom_bar)
        
        # We don't load topics here anymore, the MainWindow will call it after wiring signals.

    def add_topic_prompt(self):
        # Show the inline input and focus it
        self.pending_parent_id = None
        self.new_topic_input.setText("")
        self.new_topic_input.show()
        self.new_topic_input.setFocus()

    def commit_new_topic(self):
        text = self.new_topic_input.text().strip()
        if text:
            from core.database import get_session
            from core.models import Topic
            session = get_session()
            new_topic = Topic(name=text)
            
            if hasattr(self, 'pending_parent_id') and self.pending_parent_id:
                parent_topic = session.get(Topic, self.pending_parent_id)
                if parent_topic:
                    new_topic.parents.append(parent_topic)
                    
            session.add(new_topic)
            session.commit()
            new_topic_id = new_topic.id
            session.close()
            self.load_topics_from_db()
            self.select_topic(new_topic_id)
            
        self.new_topic_input.hide()
        self.pending_parent_id = None

    def add_subtopic(self, parent_id):
        self.pending_parent_id = parent_id
        self.new_topic_input.setText("")
        self.new_topic_input.show()
        self.new_topic_input.setFocus()
        
    def delete_topic(self, topic_id):
        from core.database import get_session
        from core.models import Topic
        session = get_session()
        topic = session.get(Topic, topic_id)
        if topic:
            deleted = set()
            def delete_recursive(t):
                if t.id in deleted: return
                deleted.add(t.id)
                children = list(t.children)
                for child in children:
                    delete_recursive(child)
                session.delete(t)
            delete_recursive(topic)
            session.commit()
        session.close()
        self.load_topics_from_db()

    def select_topic(self, topic_id):
        match = self.topic_model.match(
            self.topic_model.index(0, 0),
            Qt.UserRole,
            topic_id,
            1,
            Qt.MatchExactly | Qt.MatchRecursive
        )
        if match:
            self.topic_view.setCurrentIndex(match[0])

    def on_selection_changed(self, selected, deselected):
        indexes = selected.indexes()
        if indexes:
            item = self.topic_model.itemFromIndex(indexes[0])
            topic_id = item.data(Qt.UserRole)
            if topic_id: # Only emit if it's a real topic (not fixed items)
                self.topic_selected.emit(topic_id)

    def on_item_changed(self, item):
        topic_id = item.data(Qt.UserRole)
        if topic_id:
            from core.database import get_session
            from core.models import Topic
            session = get_session()
            topic = session.get(Topic, topic_id)
            if topic and topic.name != item.text():
                topic.name = item.text()
                session.commit()
            session.close()

    def load_topics_from_db(self):
        self.topic_model.clear()
        self.topic_model.setColumnCount(2)
        
        # Re-apply header settings because clear() destroys column configuration
        self.topic_view.header().setStretchLastSection(False)
        self.topic_view.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.topic_view.header().setSectionResizeMode(1, QHeaderView.Fixed)
        self.topic_view.setColumnWidth(1, 55) # Ensure buttons have enough space
        
        from core.database import get_session
        from core.models import Topic
        
        session = get_session()
        # Find root topics (topics with no parents)
        all_topics = session.query(Topic).all()
        root_topics = [t for t in all_topics if not t.parents]
        
        visited = set()
        
        def add_node(parent_item, topic):
            if topic.id in visited:
                return # avoid infinite recursion in graph
            visited.add(topic.id)
            
            item = QStandardItem(topic.name)
            item.setData(topic.id, Qt.UserRole)
            item.setToolTip(topic.name) # Add hover tooltip
            
            # Set icon based on children
            if topic.children:
                item.setIcon(QIcon("assets/icons/folder.svg"))
            else:
                item.setIcon(QIcon("assets/icons/file.svg"))
                
            btn_item = QStandardItem()
            parent_item.appendRow([item, btn_item])
            
            btn_widget = QWidget()
            btn_widget.setStyleSheet("background: transparent;")
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(0, 0, 0, 0)
            btn_layout.setSpacing(2)
            
            inline_btn_style = """
                QPushButton { border: none; background: transparent; padding: 2px; border-radius: 4px; }
                QPushButton:hover { background: rgba(255, 255, 255, 0.1); }
            """
            
            add_btn = QPushButton()
            add_btn.setIcon(QIcon("assets/icons/plus.svg"))
            add_btn.setFixedSize(20, 20)
            add_btn.setStyleSheet(inline_btn_style)
            add_btn.clicked.connect(lambda _, t_id=topic.id: self.add_subtopic(t_id))
            
            del_btn = QPushButton()
            del_btn.setIcon(QIcon("assets/icons/trash.svg"))
            del_btn.setFixedSize(20, 20)
            del_btn.setStyleSheet(inline_btn_style)
            
            confirm_btn = QPushButton()
            confirm_btn.setIcon(QIcon("assets/icons/check.svg"))
            confirm_btn.setFixedSize(20, 20)
            confirm_btn.setStyleSheet(inline_btn_style)
            confirm_btn.hide()
            
            cancel_btn = QPushButton()
            cancel_btn.setIcon(QIcon("assets/icons/x.svg"))
            cancel_btn.setFixedSize(20, 20)
            cancel_btn.setStyleSheet(inline_btn_style)
            cancel_btn.hide()
            
            def show_confirm(a=add_btn, d=del_btn, c=confirm_btn, x=cancel_btn):
                a.hide()
                d.hide()
                c.show()
                x.show()
                
            def hide_confirm(a=add_btn, d=del_btn, c=confirm_btn, x=cancel_btn):
                c.hide()
                x.hide()
                a.show()
                d.show()
                
            del_btn.clicked.connect(lambda _: show_confirm())
            cancel_btn.clicked.connect(lambda _: hide_confirm())
            confirm_btn.clicked.connect(lambda _, t_id=topic.id: self.delete_topic(t_id))
            
            btn_layout.addStretch()
            btn_layout.addWidget(add_btn)
            btn_layout.addWidget(del_btn)
            btn_layout.addWidget(confirm_btn)
            btn_layout.addWidget(cancel_btn)
            
            self.topic_view.setIndexWidget(btn_item.index(), btn_widget)
            
            for child in topic.children:
                add_node(item, child)
                
            visited.remove(topic.id) # allow topic in multiple branches if graph allows
            
        for root in root_topics:
            add_node(self.topic_model.invisibleRootItem(), root)
            
        session.close()
        self.topic_view.expandAll()
        
        # Auto-select the first topic if it exists
        if self.topic_model.rowCount() > 0:
            index = self.topic_model.index(0, 0)
            self.topic_view.setCurrentIndex(index)
