from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QFrame,
    QTreeView, QAbstractItemView, QMenu, QStyleFactory
)
from PySide6.QtGui import QStandardItemModel, QStandardItem, QIcon, QAction
from PySide6.QtCore import Qt, Signal, QSize, QPoint
from ui.delegates.topic_delegate import TopicDelegate


class NotesPanel(QWidget):
    """
    VS Code-style Explorer panel for the Notes section.
    Shows the topic tree with: workspace header, action buttons row, and tree view.
    """
    topic_selected = Signal(int)
    topic_deleted = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.pending_parent_id = None
        self._new_type = "file"
        self._collapsed = False
        self._renaming = False
        self._rename_topic_id = None
        self.init_ui()

    def init_ui(self):
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("background-color: #181818;")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Section header — action icons only, no title text ─────────────
        self.header = QWidget()
        self.header.setFixedHeight(40)
        self.header.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #1f1f1f, stop:1 #181818);
            border-bottom: 1px solid #2a2a2a;
        """)
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(10, 0, 8, 0)
        header_layout.setSpacing(10)

        # Search Bar
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search Name...")
        self.search_box.setFixedHeight(26)
        self.search_box.setStyleSheet("""
            QLineEdit {
                background-color: #1A1A1A;
                border: 1px solid #2D2D2D;
                border-radius: 4px;
                padding: 4px 10px;
                color: #FFFFFF;
                font-size: 11px;
            }
        """)
        search_pixmap = QIcon("assets/icons/search.svg").pixmap(QSize(16, 16))
        self.search_box.addAction(QIcon(search_pixmap), QLineEdit.LeadingPosition)
        self.search_box.textChanged.connect(self._on_search_text_changed)
        header_layout.addWidget(self.search_box)

        # Action buttons: New File, New Folder, Collapse All
        _ACTION_BTN_STYLE = """
            QPushButton {
                border: none;
                background: transparent;
                border-radius: 5px;
                padding: 2px;
            }
            QPushButton:hover {
                background: rgba(255,255,255,0.12);
            }
            QPushButton:pressed {
                background: rgba(255,255,255,0.06);
            }
        """
        action_specs = [
            ("edit.svg",   "New Topic",      self.new_file),
            ("panel-collapse.svg",   "Collapse All",  self.collapse_all),
        ]
        
        button_layout = QHBoxLayout()
        button_layout.setSpacing(0)
        button_layout.setContentsMargins(0, 0, 0, 0)
        
        for icon_file, tip, slot in action_specs:
            btn = QPushButton()
            btn.setIcon(QIcon(f"assets/icons/{icon_file}"))
            btn.setIconSize(QSize(16, 16))
            btn.setFixedSize(26, 26)
            btn.setToolTip(tip)
            btn.setStyleSheet(_ACTION_BTN_STYLE)
            btn.clicked.connect(slot)
            button_layout.addWidget(btn)

        header_layout.addLayout(button_layout)
        layout.addWidget(self.header)

        # ── Separator ──────────────────────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background: #2a2a2a; border:none; max-height:1px;")
        layout.addWidget(sep)

        # ── Tree view ──────────────────────────────────────────────────────
        self.topic_model = QStandardItemModel()
        self.topic_model.setColumnCount(1)

        self.topic_view = QTreeView()
        self.topic_view.setModel(self.topic_model)
        self.topic_view.setHeaderHidden(True)
        self.topic_view.setIndentation(18)
        self.topic_view.setAnimated(True)
        self.topic_view.setIconSize(QSize(16, 16))
        self.topic_view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.topic_view.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed)
        self.topic_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.topic_view.customContextMenuRequested.connect(self._show_context_menu)
        self.topic_view.setStyle(QStyleFactory.create("Fusion"))
        
        # Enable mouse tracking for hover repaints in delegate
        self.topic_view.setMouseTracking(True)
        self.topic_view.viewport().setMouseTracking(True)
        
        self.topic_delegate = TopicDelegate(self.topic_view)
        self.topic_delegate.signals.add_clicked.connect(self.add_subtopic)
        self.topic_delegate.signals.delete_clicked.connect(self.delete_topic)
        self.topic_delegate.signals.move_up_clicked.connect(self.move_up)
        self.topic_delegate.signals.move_down_clicked.connect(self.move_down)
        self.topic_view.setItemDelegate(self.topic_delegate)
        
        # Enable Drag and Drop
        self.topic_view.setDragEnabled(True)
        self.topic_view.setAcceptDrops(True)
        self.topic_view.setDropIndicatorShown(True)
        self.topic_view.setDragDropMode(QAbstractItemView.InternalMove)
        
        self.topic_model.rowsInserted.connect(self._on_rows_moved)
        self.topic_model.itemChanged.connect(self._on_item_changed)
        self.topic_delegate.closeEditor.connect(self._on_editor_closed)
        
        self.topic_view.setStyleSheet("""
            QTreeView {
                background: transparent;
                border: none;
                outline: none;
                color: #d4d4d4;
                font-size: 13px;
                padding: 4px 0px 4px 10px;
            }
            QTreeView::item {
                padding: 4px 6px 4px 2px;
                min-height: 24px;
                border-radius: 4px;
            }
            QTreeView::item:hover {
                background: rgba(255,255,255,0.08);
                color: #ffffff;
            }
            QTreeView::item:selected {
                background: #2d2036;
                color: #e0c8f0;
            }
            QTreeView::item:selected:hover {
                background: #38264a;
            }
            QTreeView::branch {
                background: transparent;
                border-image: none;
            }
            QTreeView::branch:hover {
                background: rgba(255,255,255,0.08);
            }
            QTreeView::branch:selected {
                background: #2d2036;
            }
            QTreeView::branch:selected:hover {
                background: #38264a;
            }
            QTreeView::branch:has-siblings:!adjoins-item { border-image: none; image: none; }
            QTreeView::branch:has-siblings:adjoins-item { border-image: none; image: none; }
            QTreeView::branch:!has-children:!has-siblings:adjoins-item { border-image: none; image: none; }
            
            QTreeView::branch:has-children:!has-siblings:closed,
            QTreeView::branch:closed:has-children:has-siblings {
                border-image: none;
                image: url(assets/icons/chevron-right.svg);
            }
            QTreeView::branch:open:has-children:!has-siblings,
            QTreeView::branch:open:has-children:has-siblings {
                border-image: none;
                image: url(assets/icons/chevron-down.svg);
            }
            QTreeView::branch:!has-children {
                image: none;
            }
        """)
        self.topic_view.selectionModel().selectionChanged.connect(self._on_selection)
        
        # Override mousePressEvent to clear selection when clicking empty space
        original_mouse_press = self.topic_view.mousePressEvent
        def custom_mouse_press(event):
            index = self.topic_view.indexAt(event.pos())
            if not index.isValid():
                self.topic_view.clearSelection()
            original_mouse_press(event)
        self.topic_view.mousePressEvent = custom_mouse_press
        
        layout.addWidget(self.topic_view)


    # ── Public API ─────────────────────────────────────────────────────────

    def load_topics_from_db(self):
        try:
            self.topic_model.rowsInserted.disconnect(self._on_rows_moved)
        except RuntimeError:
            pass # Signal was not connected yet
            
        # Save expanded state
        expanded_ids = set()
        if self.topic_model.rowCount() > 0:
            def save_expanded(parent_idx):
                for row in range(self.topic_model.rowCount(parent_idx)):
                    idx = self.topic_model.index(row, 0, parent_idx)
                    if self.topic_view.isExpanded(idx):
                        topic_id = idx.data(Qt.UserRole)
                        if topic_id:
                            expanded_ids.add(topic_id)
                        save_expanded(idx)
            from PySide6.QtCore import QModelIndex
            save_expanded(QModelIndex())
        else:
            expanded_ids = None # Indicates first load
            
        self.topic_model.clear()

        from core.database import get_session
        from core.models import Topic

        session = get_session()
        all_topics = session.query(Topic).filter_by(is_deleted=False).order_by(Topic.order_index).all()
        root_topics = [t for t in all_topics if not t.parents]
        visited = set()

        def add_node(parent_item, topic):
            if topic.id in visited:
                return
            visited.add(topic.id)

            item = QStandardItem(topic.name)
            item.setData(topic.id, Qt.UserRole)
            item.setEditable(True)

            parent_item.appendRow(item)

            for child in topic.children:
                if not child.is_deleted:
                    add_node(item, child)

            visited.discard(topic.id)

        for root in root_topics:
            add_node(self.topic_model.invisibleRootItem(), root)

        session.close()
        
        # Restore expanded state
        if expanded_ids is None:
            self.topic_view.expandAll()
        else:
            def restore_expanded(parent_idx):
                for row in range(self.topic_model.rowCount(parent_idx)):
                    idx = self.topic_model.index(row, 0, parent_idx)
                    topic_id = idx.data(Qt.UserRole)
                    if topic_id in expanded_ids:
                        self.topic_view.expand(idx)
                    restore_expanded(idx)
            from PySide6.QtCore import QModelIndex
            restore_expanded(QModelIndex())

        # Reconnect signal after populating model
        self.topic_model.rowsInserted.connect(self._on_rows_moved)

    def select_topic(self, topic_id, block_signals=False):
        match = self.topic_model.match(
            self.topic_model.index(0, 0), Qt.UserRole, topic_id, 1,
            Qt.MatchExactly | Qt.MatchRecursive
        )
        if match:
            if block_signals:
                self.topic_view.selectionModel().blockSignals(True)
                
            from PySide6.QtCore import QItemSelectionModel
            self.topic_view.selectionModel().select(
                match[0], 
                QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows
            )
            self.topic_view.setCurrentIndex(match[0])
            
            if block_signals:
                self.topic_view.selectionModel().blockSignals(False)

    def clear_selection(self, block_signals=False):
        if block_signals:
            self.topic_view.selectionModel().blockSignals(True)
        
        self.topic_view.selectionModel().clearSelection()
        
        from PySide6.QtCore import QModelIndex
        self.topic_view.setCurrentIndex(QModelIndex())
        
        if block_signals:
            self.topic_view.selectionModel().blockSignals(False)

    # ── Slot: action button handlers ───────────────────────────────────────

    def new_file(self):
        item = QStandardItem("")
        item.setData("temp_new", Qt.UserRole)
        item.setData(None, Qt.UserRole + 1) # Parent ID
        item.setEditable(True)
        
        root = self.topic_model.invisibleRootItem()
        root.appendRow(item)
        
        idx = item.index()
        self.topic_view.setCurrentIndex(idx)
        self.topic_view.edit(idx)

    def refresh(self):
        self.load_topics_from_db()

    def collapse_all(self):
        self.topic_view.collapseAll()

    def commit_new(self):
        text = self.new_input.text().strip()
        if text:
            if self._renaming and self._rename_topic_id is not None:
                # Rename mode
                self.rename_topic(self._rename_topic_id, text)
            else:
                # Create mode
                from core.database import get_session
                from core.models import Topic
                from sqlalchemy.exc import IntegrityError
                from PySide6.QtWidgets import QMessageBox

                session = get_session()
                new_topic = Topic(name=text, is_deleted=False)

                if self.pending_parent_id:
                    parent = session.get(Topic, self.pending_parent_id)
                    if parent:
                        new_topic.parents.append(parent)

                session.add(new_topic)
                try:
                    session.commit()
                    new_id = new_topic.id
                    self.load_topics_from_db()
                    self.select_topic(new_id)
                except IntegrityError:
                    session.rollback()
                    QMessageBox.warning(self, "Duplicate Name", f"A note or folder named '{text}' already exists.")
                finally:
                    session.close()

        self._hide_input()

    def delete_topic(self, topic_id):
        """Permanently delete topic and its children from the database (called by inline checkmark)."""
        from core.database import get_session
        from core.models import Topic

        session = get_session()
        topic = session.get(Topic, topic_id)
        deleted_ids = []
        if topic:
            def delete_recursive(t):
                deleted_ids.append(t.id)
                for child in t.children:
                    delete_recursive(child)
                session.delete(t)
            
            delete_recursive(topic)
            session.commit()
        session.close()
        self.load_topics_from_db()
        if deleted_ids:
            self.topic_deleted.emit(deleted_ids)

    def rename_topic(self, topic_id, new_name):
        if not new_name.strip():
            return
        from core.database import get_session
        from core.models import Topic
        from sqlalchemy.exc import IntegrityError
        from PySide6.QtWidgets import QMessageBox

        session = get_session()
        topic = session.get(Topic, topic_id)
        if topic:
            topic.name = new_name.strip()
            try:
                session.commit()
                self.load_topics_from_db()
            except IntegrityError:
                session.rollback()
                QMessageBox.warning(self, "Duplicate Name", f"A note or folder named '{new_name.strip()}' already exists.")
        session.close()

    def add_subtopic(self, parent_id):
        # Find the parent item
        match = self.topic_model.match(
            self.topic_model.index(0, 0), Qt.UserRole, parent_id, 1,
            Qt.MatchExactly | Qt.MatchRecursive
        )
        if not match:
            return
            
        parent_item = self.topic_model.itemFromIndex(match[0])
        
        item = QStandardItem("")
        item.setData("temp_new", Qt.UserRole)
        item.setData(parent_id, Qt.UserRole + 1) # Parent ID
        item.setEditable(True)
        
        parent_item.appendRow(item)
        self.topic_view.expand(match[0])
        
        idx = item.index()
        self.topic_view.setCurrentIndex(idx)
        self.topic_view.edit(idx)

    # ── Private helpers ────────────────────────────────────────────────────

    def _on_search_text_changed(self, text):
        text = text.lower()
        def filter_recursive(parent_item):
            match_found = False
            for row in range(parent_item.rowCount()):
                child = parent_item.child(row)
                if not child:
                    continue
                child_match = filter_recursive(child)
                name = child.text().lower()
                if text in name or child_match:
                    self.topic_view.setRowHidden(row, parent_item.index(), False)
                    match_found = True
                    if child_match and text:
                        self.topic_view.expand(child.index())
                else:
                    self.topic_view.setRowHidden(row, parent_item.index(), True)
            return match_found
        
        filter_recursive(self.topic_model.invisibleRootItem())

    def _on_selection(self, selected, deselected):
        indexes = selected.indexes()
        if indexes:
            item = self.topic_model.itemFromIndex(indexes[0])
            if item:
                topic_id = item.data(Qt.UserRole)
                if topic_id and topic_id != "temp_new":
                    self.topic_selected.emit(topic_id)

    def _show_context_menu(self, pos: QPoint):
        index = self.topic_view.indexAt(pos)
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: #252526;
                border: 1px solid #454545;
                border-radius: 6px;
                padding: 4px 0;
                color: #FFFFFF;
                font-size: 13px;
            }
            QMenu::item {
                padding: 5px 24px 5px 12px;
            }
            QMenu::item:selected {
                background: #37373d;
                color: #ffffff;
            }
            QMenu::separator {
                background: #454545;
                height: 1px;
                margin: 3px 0;
            }
        """)

        if index.isValid():
            item = self.topic_model.itemFromIndex(index)
            topic_id = item.data(Qt.UserRole) if item else None

            new_child_action = QAction("New Note Here", self)
            new_child_action.triggered.connect(lambda: self.add_subtopic(topic_id))
            menu.addAction(new_child_action)

            menu.addSeparator()

            rename_action = QAction("Rename", self)
            rename_action.triggered.connect(lambda: self.topic_view.edit(index))
            menu.addAction(rename_action)

            menu.addSeparator()

            delete_action = QAction("Delete", self)
            delete_action.triggered.connect(lambda: self.delete_topic(topic_id))
            menu.addAction(delete_action)
        else:
            # Clicked on empty area
            new_action = QAction("New Topic", self)
            new_action.triggered.connect(self.new_file)
            menu.addAction(new_action)

        menu.exec(self.topic_view.viewport().mapToGlobal(pos))

    def _on_item_changed(self, item):
        topic_id = item.data(Qt.UserRole)
        new_name = item.text().strip()
        
        if topic_id == "temp_new":
            if not new_name:
                return # Handled by _on_editor_closed
            
            parent_id = item.data(Qt.UserRole + 1)
            
            from core.database import get_session
            from core.models import Topic
            from sqlalchemy.exc import IntegrityError
            from PySide6.QtWidgets import QMessageBox

            session = get_session()
            
            # Determine order index (last sibling)
            if parent_id:
                siblings = session.query(Topic).filter(Topic.parents.any(id=parent_id), Topic.is_deleted == False).count()
            else:
                siblings = session.query(Topic).filter(~Topic.parents.any(), Topic.is_deleted == False).count()
                
            new_topic = Topic(name=new_name, is_deleted=False, order_index=siblings)

            if parent_id:
                parent = session.get(Topic, parent_id)
                if parent:
                    new_topic.parents.append(parent)

            session.add(new_topic)
            try:
                session.commit()
                item.setData(new_topic.id, Qt.UserRole)
                # Ensure the tree reflects exactly by doing a full reload (deferred to prevent crash)
                from PySide6.QtCore import QTimer
                def reload_and_select(tid=new_topic.id):
                    self.load_topics_from_db()
                    self.select_topic(tid)
                QTimer.singleShot(0, reload_and_select)
            except IntegrityError:
                session.rollback()
                QMessageBox.warning(self, "Duplicate Name", f"A note or folder named '{new_name}' already exists.")
                # Remove the invalid temporary node
                if item.parent():
                    item.parent().removeRow(item.row())
                else:
                    self.topic_model.removeRow(item.row())
            finally:
                session.close()
            return
            
        if not topic_id or not new_name:
            return
        
        from core.database import get_session
        from core.models import Topic
        from sqlalchemy.exc import IntegrityError
        from PySide6.QtWidgets import QMessageBox

        session = get_session()
        topic = session.get(Topic, topic_id)
        if topic and topic.name != new_name:
            topic.name = new_name
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                QMessageBox.warning(self, "Duplicate Name", f"A note or folder named '{new_name}' already exists.")
                # revert visually
                item.setText(topic.name)
        session.close()

    def _on_editor_closed(self, editor, hint):
        # Find if there are any blank temp_new items and remove them
        def clean_temp_recursive(parent_item):
            for row in range(parent_item.rowCount() - 1, -1, -1):
                child = parent_item.child(row)
                if child.data(Qt.UserRole) == "temp_new" and not child.text().strip():
                    parent_item.removeRow(row)
                else:
                    clean_temp_recursive(child)
        clean_temp_recursive(self.topic_model.invisibleRootItem())

    def move_up(self, topic_id):
        self._swap_order(topic_id, -1)

    def move_down(self, topic_id):
        self._swap_order(topic_id, 1)

    def _swap_order(self, topic_id, direction):
        from core.database import get_session
        from core.models import Topic

        session = get_session()
        topic = session.get(Topic, topic_id)
        if not topic:
            session.close()
            return

        # Get siblings
        if topic.parents:
            siblings = session.query(Topic).filter(Topic.parents.any(id=topic.parents[0].id), Topic.is_deleted == False).order_by(Topic.order_index).all()
        else:
            siblings = session.query(Topic).filter(~Topic.parents.any(), Topic.is_deleted == False).order_by(Topic.order_index).all()

        try:
            idx = siblings.index(topic)
        except ValueError:
            session.close()
            return

        swap_idx = idx + direction
        if 0 <= swap_idx < len(siblings):
            # Swap order_index
            other = siblings[swap_idx]
            topic.order_index, other.order_index = other.order_index, topic.order_index
            session.commit()
            
        session.close()
        self.load_topics_from_db()
        self.select_topic(topic_id)

    def _on_rows_moved(self, parent, first, last):
        """Called when a row is dropped via drag-and-drop."""
        # Because QStandardItemModel handles the visual move, we just need to read the new order 
        # of the children under the given parent and update the DB.
        from core.database import get_session
        from core.models import Topic
        
        session = get_session()
        parent_item = self.topic_model.itemFromIndex(parent) if parent.isValid() else self.topic_model.invisibleRootItem()
        
        # Determine parent topic ID in DB
        parent_topic_id = parent_item.data(Qt.UserRole) if parent.isValid() else None
        
        # Iterate through all children visually under this parent and update order_index and parent relationships
        for row in range(parent_item.rowCount()):
            child_item = parent_item.child(row)
            if child_item is None:
                continue
            topic_id = child_item.data(Qt.UserRole)
            if not topic_id or topic_id == "temp_new":
                continue
                
            topic = session.get(Topic, topic_id)
            if topic:
                topic.order_index = row
                # Handle parent reassignment if it was dragged to a new parent
                topic.parents = []
                if parent_topic_id:
                    parent_topic = session.get(Topic, parent_topic_id)
                    if parent_topic:
                        topic.parents.append(parent_topic)
        
        session.commit()
        session.close()


