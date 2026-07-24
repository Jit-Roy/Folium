from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, 
    QListWidget, QListWidgetItem, QCheckBox, QLabel
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from core.database import get_session
from core.models import Task

class TaskItemWidget(QWidget):
    def __init__(self, task_id: int, content: str, is_completed: bool, parent_panel=None):
        super().__init__()
        self.task_id = task_id
        self.parent_panel = parent_panel
        self.setStyleSheet("background: transparent;")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        self.checkbox = QCheckBox(content)
        self.checkbox.setChecked(is_completed)
        self.checkbox.setStyleSheet("""
            QCheckBox { color: #FFFFFF; font-size: 14px; }
            QCheckBox::indicator { width: 16px; height: 16px; border-radius: 4px; border: 1px solid #444; background: #242424; }
            QCheckBox::indicator:checked { 
                background: #242424; 
                border: 1px solid #B48EAD; 
                image: url('assets/icons/check-white.svg'); 
            }
        """)
        self.checkbox.toggled.connect(self._on_toggled)
        layout.addWidget(self.checkbox, stretch=1)
        
        self.delete_btn = QPushButton()
        self.delete_btn.setIcon(QIcon("assets/icons/trash.svg"))
        self.delete_btn.setFixedSize(24, 24)
        self.delete_btn.setToolTip("Delete task")
        
        btn_style = (
            "QPushButton { border: none; background: transparent; }"
            "QPushButton:hover { background: rgba(255,255,255,0.1); border-radius: 4px; }"
        )
        self.delete_btn.setStyleSheet(btn_style)
        self.delete_btn.clicked.connect(self._show_confirm)
        layout.addWidget(self.delete_btn)
        
        self.confirm_btn = QPushButton()
        self.confirm_btn.setIcon(QIcon("assets/icons/check.svg"))
        self.confirm_btn.setFixedSize(24, 24)
        self.confirm_btn.setStyleSheet(btn_style)
        self.confirm_btn.setToolTip("Confirm delete")
        self.confirm_btn.hide()
        self.confirm_btn.clicked.connect(self._on_delete)
        layout.addWidget(self.confirm_btn)
        
        self.cancel_btn = QPushButton()
        self.cancel_btn.setIcon(QIcon("assets/icons/x.svg"))
        self.cancel_btn.setFixedSize(24, 24)
        self.cancel_btn.setStyleSheet(btn_style)
        self.cancel_btn.setToolTip("Cancel delete")
        self.cancel_btn.hide()
        self.cancel_btn.clicked.connect(self._hide_confirm)
        layout.addWidget(self.cancel_btn)
        
    def _show_confirm(self):
        self.delete_btn.hide()
        self.confirm_btn.show()
        self.cancel_btn.show()
        
    def _hide_confirm(self):
        self.confirm_btn.hide()
        self.cancel_btn.hide()
        self.delete_btn.show()
        
    def _on_toggled(self, checked):
        if self.parent_panel:
            self.parent_panel.toggle_task(self.task_id, checked)
            
    def _on_delete(self):
        if self.parent_panel:
            self.parent_panel.delete_task(self.task_id)


class TasksPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_topic_id = None
        self._init_ui()
        
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(5, 0, 5, 0)
        title = QLabel("To-Do List")
        title.setStyleSheet("color: #FFFFFF; font-size: 16px; font-weight: bold;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        add_btn = QPushButton()
        add_btn.setIcon(QIcon("assets/icons/plus.svg"))
        add_btn.setFixedSize(26, 26)
        add_btn.setToolTip("Add new task")
        add_btn.setStyleSheet(
            "QPushButton { border: none; background: transparent; border-radius: 4px; }"
            "QPushButton:hover { background: rgba(255,255,255,0.1); }"
        )
        add_btn.clicked.connect(self._add_task_inline)
        header_layout.addWidget(add_btn)
        layout.addLayout(header_layout)
        
        # Tasks list
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget {
                background: transparent;
                border: none;
                outline: none;
            }
            QListWidget::item { border-bottom: 1px solid #222; }
            QListWidget::item:hover { background: #1a1a1a; }
            QListWidget QLineEdit { background: #1A1A1A; color: #FFFFFF; border: 1px solid #B48EAD; border-radius: 4px; padding: 2px; }
        """)
        self.list_widget.itemDelegate().closeEditor.connect(self._on_editor_closed)
        layout.addWidget(self.list_widget, stretch=1)
        
        self.empty_label = QLabel("No active topic selected.")
        self.empty_label.setStyleSheet("color: #666; font-size: 12px; font-style: italic;")
        self.empty_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.empty_label)
        self.list_widget.hide()
        
    def set_current_topic(self, topic_id: int):
        self.current_topic_id = topic_id
        if not topic_id:
            self.empty_label.show()
            self.list_widget.hide()
            return
            
        self.empty_label.hide()
        self.list_widget.show()
        self.load_tasks()
        
    def load_tasks(self):
        self.list_widget.clear()
        if not self.current_topic_id:
            return
            
        session = get_session()
        tasks = session.query(Task).filter_by(topic_id=self.current_topic_id).all()
        
        for task in tasks:
            self._add_task_to_list(task.id, task.content, task.is_completed)
            
        session.close()
        
    def _add_task_inline(self):
        if not self.current_topic_id:
            return
            
        item = QListWidgetItem()
        item.setData(Qt.UserRole, "temp_new")
        item.setFlags(item.flags() | Qt.ItemIsEditable)
        self.list_widget.addItem(item)
        self.list_widget.setCurrentItem(item)
        self.list_widget.editItem(item)
        
    def _on_editor_closed(self, editor, hint):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.data(Qt.UserRole) == "temp_new":
                content = item.text().strip()
                self.list_widget.takeItem(i)
                if content:
                    session = get_session()
                    new_task = Task(topic_id=self.current_topic_id, content=content)
                    session.add(new_task)
                    session.commit()
                    self._add_task_to_list(new_task.id, new_task.content, False)
                    session.close()
                break
        
    def _add_task_to_list(self, task_id: int, content: str, is_completed: bool):
        item = QListWidgetItem(self.list_widget)
        widget = TaskItemWidget(task_id, content, is_completed, self)
        
        item.setSizeHint(widget.sizeHint())
        self.list_widget.setItemWidget(item, widget)
        
    def toggle_task(self, task_id: int, is_completed: bool):
        session = get_session()
        task = session.query(Task).get(task_id)
        if task:
            task.is_completed = is_completed
            session.commit()
        session.close()
        
    def delete_task(self, task_id: int):
        session = get_session()
        task = session.query(Task).get(task_id)
        if task:
            session.delete(task)
            session.commit()
        session.close()
        self.load_tasks()
