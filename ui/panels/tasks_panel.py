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
            QCheckBox { color: #cccccc; font-size: 14px; }
            QCheckBox::indicator { width: 16px; height: 16px; border-radius: 4px; border: 1px solid #444; background: #242424; }
            QCheckBox::indicator:checked { 
                background: #242424; 
                border: 1px solid #B48EAD; 
                image: url('assets/icons/check-white.svg'); 
            }
        """)
        self.checkbox.toggled.connect(self._on_toggled)
        layout.addWidget(self.checkbox, stretch=1)
        
        delete_btn = QPushButton()
        delete_btn.setIcon(QIcon("assets/icons/trash.svg"))
        delete_btn.setFixedSize(24, 24)
        delete_btn.setToolTip("Delete task")
        delete_btn.setStyleSheet(
            "QPushButton { border: none; background: transparent; }"
            "QPushButton:hover { background: rgba(255,255,255,0.1); border-radius: 4px; }"
        )
        delete_btn.clicked.connect(self._on_delete)
        layout.addWidget(delete_btn)
        
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
        
        title = QLabel("To-Do List")
        title.setStyleSheet("color: #FFFFFF; font-size: 16px; font-weight: bold;")
        layout.addWidget(title)
        
        # Add task input
        input_layout = QHBoxLayout()
        self.task_input = QLineEdit()
        self.task_input.setPlaceholderText("Add a new task...")
        self.task_input.setStyleSheet("""
            QLineEdit {
                background: #1e1e1e;
                border: 1px solid #333333;
                border-radius: 5px;
                padding: 6px 10px;
                color: #cccccc;
                font-size: 13px;
            }
            QLineEdit:focus { border: 1px solid #B48EAD; }
        """)
        self.task_input.returnPressed.connect(self._add_task)
        input_layout.addWidget(self.task_input, stretch=1)
        
        add_btn = QPushButton()
        add_btn.setIcon(QIcon("assets/icons/plus.svg"))
        add_btn.setFixedSize(30, 30)
        add_btn.setStyleSheet("""
            QPushButton { background: #2D2036; border: 1px solid #4D305A; border-radius: 4px; }
            QPushButton:hover { background: #3E2B4B; }
        """)
        add_btn.clicked.connect(self._add_task)
        input_layout.addWidget(add_btn)
        layout.addLayout(input_layout)
        
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
        """)
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
            self.task_input.setEnabled(False)
            return
            
        self.empty_label.hide()
        self.list_widget.show()
        self.task_input.setEnabled(True)
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
        
    def _add_task(self):
        content = self.task_input.text().strip()
        if not content or not self.current_topic_id:
            return
            
        session = get_session()
        new_task = Task(topic_id=self.current_topic_id, content=content)
        session.add(new_task)
        session.commit()
        
        self._add_task_to_list(new_task.id, new_task.content, False)
        self.task_input.clear()
        session.close()
        
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
