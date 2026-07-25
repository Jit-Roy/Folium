from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QStackedWidget,
    QLineEdit, QTextEdit, QCheckBox, QDateEdit, QPushButton, QFrame, QScrollArea, QFormLayout, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QDate
from core.models import PlannerTask, TaskStatus
from ui.panels.recent_tasks_panel import TasksService
from datetime import date

_T_PRI = "#ffffff"
_T_SEC = "#a0a0a0"
_T_DIM = "#808080"

class TasksSidebar(QWidget):
    # Emitted when a task is created or updated successfully
    data_changed = Signal()

    def __init__(self, service: TasksService, parent=None):
        super().__init__(parent)
        self.service = service
        self.current_task_id = None
        self.setObjectName("tasksSidebar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("""
            QWidget#tasksSidebar { background: #181818; }
            .QWidget { background: transparent; }
            QStackedWidget { background: transparent; }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        main_layout.setContentsMargins(20, 24, 20, 24)
        main_layout.setSpacing(8)

        # Header
        lbl = QLabel("Task Details")
        lbl.setStyleSheet(f"color: {_T_PRI}; font-size: 13pt; font-weight: bold; letter-spacing: 0.5px; background: transparent;")
        main_layout.addWidget(lbl)

        desc = QLabel("Metadata and Properties")
        desc.setStyleSheet(f"color: {_T_SEC}; font-size: 10pt; background: transparent;")
        main_layout.addWidget(desc)

        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setFixedHeight(1)
        div.setStyleSheet("background: rgba(255,255,255,0.05); border: none; margin-top: 12px; margin-bottom: 12px;")
        main_layout.addWidget(div)

        # Stacked Widget for states
        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack)

        # State 0: Empty
        self.empty_widget = QWidget()
        empty_layout = QVBoxLayout(self.empty_widget)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label = QLabel("Select a task to view its metadata\nor click + to create a new one.")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet(f"color: {_T_DIM}; font-size: 10pt; text-align: center; background: transparent;")
        empty_layout.addWidget(self.empty_label)
        self.stack.addWidget(self.empty_widget)

        # State 1: Form
        self.form_widget = QWidget()
        form_layout = QVBoxLayout(self.form_widget)
        form_layout.setContentsMargins(0, 0, 0, 0)
        
        # We use a scroll area just in case the screen is small
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        inner_form = QVBoxLayout(scroll_content)
        inner_form.setContentsMargins(0, 0, 0, 0)
        inner_form.setSpacing(15)

        # Title
        title_lbl = QLabel("Title")
        title_lbl.setStyleSheet(f"color: {_T_SEC}; font-size: 9pt; font-weight: bold; background: transparent;")
        inner_form.addWidget(title_lbl)
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Task Title")
        inner_form.addWidget(self.title_input)

        # Description
        desc_lbl = QLabel("Description")
        desc_lbl.setStyleSheet(f"color: {_T_SEC}; font-size: 9pt; font-weight: bold; background: transparent;")
        inner_form.addWidget(desc_lbl)
        self.desc_input = QTextEdit()
        self.desc_input.setPlaceholderText("Notes or description...")
        self.desc_input.setMaximumHeight(100)
        self.desc_input.setStyleSheet("""
            QTextEdit {
                background-color: #1E1E1E;
                border: 1px solid #2D2D2D;
                border-radius: 6px;
                padding: 6px 10px;
                color: #FFFFFF;
                font-size: 13px;
            }
        """)
        inner_form.addWidget(self.desc_input)

        # Due Date Toggle
        self.due_date_cb = QCheckBox("Has Due Date")
        self.due_date_cb.setStyleSheet(f"color: {_T_PRI}; font-size: 10pt; background: transparent;")
        inner_form.addWidget(self.due_date_cb)

        # Due Date Edit
        self.due_date_edit = QDateEdit(QDate.currentDate())
        self.due_date_edit.setCalendarPopup(True)
        self.due_date_edit.setEnabled(False)
        inner_form.addWidget(self.due_date_edit)
        self.due_date_cb.toggled.connect(self.due_date_edit.setEnabled)

        # Style the calendar popup
        calendar = self.due_date_edit.calendarWidget()
        calendar.setStyleSheet("""
            QCalendarWidget QToolButton {
                color: #FFFFFF;
                background-color: transparent;
                border: none;
                margin: 5px;
            }
            QCalendarWidget QToolButton::menu-indicator {
                image: none;
            }
            QCalendarWidget QToolButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
                border-radius: 4px;
            }
            QCalendarWidget QMenu {
                background-color: #1E1E1E;
                color: #FFFFFF;
                border: 1px solid #2D2D2D;
            }
            QCalendarWidget QAbstractItemView:enabled {
                color: #FFFFFF;
                background-color: #121212;
                selection-background-color: #B48EAD;
                selection-color: #2D2036;
            }
            QCalendarWidget QAbstractItemView:disabled {
                color: #555555;
            }
        """)
        
        # Change weekend color from red to our hero purple
        from PySide6.QtGui import QTextCharFormat, QColor
        fmt = QTextCharFormat()
        fmt.setForeground(QColor("#B48EAD"))
        calendar.setWeekdayTextFormat(Qt.DayOfWeek.Saturday, fmt)
        calendar.setWeekdayTextFormat(Qt.DayOfWeek.Sunday, fmt)

        inner_form.addStretch()

        scroll.setWidget(scroll_content)
        form_layout.addWidget(scroll)

        # Action Buttons
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save")
        self.save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_btn.setStyleSheet("""
            QPushButton {
                background: #B48EAD;
                color: #2D2036;
                border: none;
                border-radius: 6px;
                padding: 8px 12px;
                font-weight: bold;
            }
            QPushButton:hover { background: #c5a0be; }
        """)
        self.save_btn.clicked.connect(self._save_task)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,0.1);
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 8px 12px;
            }
            QPushButton:hover { background: rgba(255,255,255,0.15); }
        """)
        self.cancel_btn.clicked.connect(self.show_empty)

        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.save_btn)
        form_layout.addLayout(btn_layout)

        self.stack.addWidget(self.form_widget)
        self.show_empty()

    def show_empty(self):
        self.current_task_id = None
        self.stack.setCurrentWidget(self.empty_widget)

    def prepare_new_task(self):
        self.current_task_id = None
        self.title_input.clear()
        self.desc_input.clear()
        self.due_date_cb.setChecked(False)
        self.due_date_edit.setDate(QDate.currentDate())
        self.save_btn.setText("Create Task")
        self.stack.setCurrentWidget(self.form_widget)
        self.title_input.setFocus()

    def load_task(self, task_id: int):
        task = self.service.get_task(task_id)
        if not task:
            self.show_empty()
            return

        self.current_task_id = task.id
        self.title_input.setText(task.title or "")
        self.desc_input.setPlainText(task.description or "")
        if task.due_date:
            self.due_date_cb.setChecked(True)
            self.due_date_edit.setDate(QDate(task.due_date.year, task.due_date.month, task.due_date.day))
        else:
            self.due_date_cb.setChecked(False)
            self.due_date_edit.setDate(QDate.currentDate())

        self.save_btn.setText("Update Task")
        self.stack.setCurrentWidget(self.form_widget)

    def _save_task(self):
        title = self.title_input.text().strip() or "Untitled task"
        desc = self.desc_input.toPlainText().strip()
        
        due = None
        if self.due_date_cb.isChecked():
            due = self.due_date_edit.date().toPython()

        if self.current_task_id is None:
            # Create
            task = PlannerTask(
                title=title,
                description=desc,
                due_date=due,
                status=TaskStatus.TODO,
                tracked_seconds=0
            )
            self.service.create_task(task)
        else:
            # Update
            task = self.service.get_task(self.current_task_id)
            if task:
                task.title = title
                task.description = desc
                task.due_date = due
                self.service.update_task(self.current_task_id, task)

        self.data_changed.emit()
        self.show_empty()
