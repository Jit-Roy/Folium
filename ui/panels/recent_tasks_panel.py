from __future__ import annotations
from core.database import get_session
from core.models import PlannerTask, TaskStatus
from datetime import date

class TasksService:
    def create_task(self, task: PlannerTask):
        with get_session() as session:
            session.add(task)
            session.commit()
            session.refresh(task)
            return task.id
            
    def update_task(self, task_id: int, updated_task: PlannerTask):
        with get_session() as session:
            db_task = session.query(PlannerTask).get(task_id)
            if db_task:
                db_task.title = updated_task.title
                db_task.description = updated_task.description
                db_task.due_date = updated_task.due_date
                db_task.status = updated_task.status
                db_task.tracked_seconds = updated_task.tracked_seconds
                session.commit()
                
    def delete_task(self, task_id: int):
        with get_session() as session:
            task = session.query(PlannerTask).get(task_id)
            if task:
                session.delete(task)
                session.commit()
                
    def get_task(self, task_id: int):
        with get_session() as session:
            return session.query(PlannerTask).get(task_id)
            
    def get_all_tasks(self):
        with get_session() as session:
            return session.query(PlannerTask).all()
            
    def mark_completed(self, task_id: int):
        with get_session() as session:
            task = session.query(PlannerTask).get(task_id)
            if task:
                task.status = TaskStatus.COMPLETED
                session.commit()
                
    def mark_skipped(self, task_id: int):
        with get_session() as session:
            task = session.query(PlannerTask).get(task_id)
            if task:
                task.status = TaskStatus.SKIPPED
                session.commit()
                
    def carry_forward(self):
        with get_session() as session:
            overdue = session.query(PlannerTask).filter(
                PlannerTask.status.in_([TaskStatus.TODO, TaskStatus.IN_PROGRESS]),
                PlannerTask.due_date != None,
                PlannerTask.due_date < date.today()
            ).all()
            for task in overdue:
                task.due_date = date.today()
            session.commit()


from datetime import date, datetime

from PySide6.QtGui import QFont, QIcon, QPixmap, QPainter, QColor, QPen
from PySide6.QtCore import QDate, QEvent, QTimer, QSize, Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
    QScrollArea,
    QStackedWidget,
)
from PySide6.QtSvg import QSvgRenderer




class CircleCheck(QCheckBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(20, 20)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("QCheckBox { background: transparent; border: none; }")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        r = self.rect()
        # draw circular border
        pen = QPen(QColor('#3a3a3c'))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(r.adjusted(1, 1, -1, -1))

        # draw tick when checked
        if self.isChecked():
            pen = QPen(QColor('#ffffff'))
            pen.setWidth(2)
            painter.setPen(pen)
            w = r.width()
            h = r.height()
            p1 = (int(w * 0.28), int(h * 0.55))
            p2 = (int(w * 0.45), int(h * 0.72))
            p3 = (int(w * 0.75), int(h * 0.32))
            painter.drawLine(p1[0], p1[1], p2[0], p2[1])
            painter.drawLine(p2[0], p2[1], p3[0], p3[1])

        painter.end()


from core.models import PlannerTask, TaskStatus



_TRACKER_BTN_IDLE = """
    QPushButton {
        background: rgba(255,255,255,0.06);
        border: none;
        border-radius: 14px;
        color: #636366;
        font-size: 9px;
        padding: 0px;
    }
    QPushButton:hover {
        background: rgba(255,255,255,0.12);
        color: #e8e8ed;
    }
    QPushButton:pressed {
        background: rgba(255,255,255,0.04);
    }
"""

_TRACKER_BTN_LIVE = """
    QPushButton {
        background: rgba(255,255,255,0.10);
        border: none;
        border-radius: 14px;
        color: #ffffff;
        font-size: 9px;
        padding: 0px;
    }
    QPushButton:hover {
        background: rgba(255,255,255,0.16);
        color: #ffffff;
    }
    QPushButton:pressed {
        background: rgba(255,255,255,0.05);
    }
"""

_ADD_TODAY_BTN = """
    QPushButton {
        background: rgba(255,255,255,0.06);
        border: 1px solid rgba(255,255,255,0.14);
        border-radius: 8px;
        color: #c8c8cc;
        font-size: 8pt;
        padding: 2px 8px;
        letter-spacing: 0.2px;
    }
    QPushButton:hover {
        background: rgba(255,255,255,0.13);
        border: 1px solid rgba(255,255,255,0.26);
        color: #ffffff;
    }
    QPushButton:pressed {
        background: rgba(255,255,255,0.04);
    }
"""


class PlannerTaskItemWidget(QWidget):
    """Monochrome task row widget."""

    def __init__(self, task: PlannerTask, parent=None, is_overdue: bool = False):
        super().__init__(parent)
        self.task = task
        self.parent_page = parent
        self.is_tracking = False
        self.is_overdue = is_overdue
        self.session_start_time: datetime | None = None

        self.tracker_timer = QTimer(self)
        self.tracker_timer.setInterval(1000)
        self.tracker_timer.timeout.connect(self._update_tracked_time_label)

        is_completed = task.status == TaskStatus.COMPLETED
        self.is_completed = is_completed

        # ── Outer centering shell ──────────────────────────────────────────
        container_layout = QHBoxLayout(self)
        container_layout.setContentsMargins(0, 4, 0, 4)

        self.inner_widget = QWidget()
        self.inner_widget.setObjectName("taskCard")
        self.inner_widget.setFixedWidth(820)
        self.inner_widget.setMinimumHeight(64)

        if is_completed:
            border_normal = "rgba(255,255,255,0.04)"
            border_hover  = "rgba(255,255,255,0.07)"
            bg_normal     = "#161618"
            bg_hover      = "#1c1c1e"
        elif is_overdue:
            border_normal = "rgba(255,255,255,0.09)"
            border_hover  = "rgba(255,255,255,0.17)"
            bg_normal     = "#1e1c1c"
            bg_hover      = "#252223"
        else:
            border_normal = "rgba(255,255,255,0.08)"
            border_hover  = "rgba(255,255,255,0.16)"
            bg_normal     = "#1c1c1e"
            bg_hover      = "#242427"

        self.normal_style = f"""
            QWidget#taskCard {{
                background: {bg_normal};
                border-radius: 10px;
                border: 1px solid {border_normal};
            }}
        """
        self.hover_style = f"""
            QWidget#taskCard {{
                background: {bg_hover};
                border-radius: 10px;
                border: 1px solid {border_hover};
            }}
        """

        self.inner_widget.setStyleSheet(self.normal_style)
        self.inner_widget.setAttribute(Qt.WidgetAttribute.WA_Hover)
        self.inner_widget.installEventFilter(self)

        # ── Card layout ────────────────────────────────────────────────────
        layout = QHBoxLayout(self.inner_widget)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        # Left accent strip — slightly warm grey for overdue, no status colour elsewhere
        accent = QWidget()
        accent.setFixedWidth(3)
        if is_completed:
            accent_color = "#2a2a2c"
        elif is_overdue:
            accent_color = "#4a3c3a"   # warm-tinged grey for visual distinction
        else:
            accent_color = "#3a3a3c"
        accent.setStyleSheet(f"QWidget {{ background: {accent_color}; border-radius: 2px; }}")
        layout.addWidget(accent, alignment=Qt.AlignmentFlag.AlignVCenter)

        # ── Circular checkbox ──────────────────────────────────────────────
        self.checkbox = CircleCheck()
        self.checkbox.setChecked(is_completed)
        self.checkbox.clicked.connect(self._toggle_completion)
        layout.addWidget(self.checkbox, alignment=Qt.AlignmentFlag.AlignVCenter)

        # ── Title + progress badge ─────────────────────────────────────────
        text_layout = QVBoxLayout()
        text_layout.setSpacing(3)
        text_layout.setContentsMargins(6, 0, 0, 0)

        title = QLabel(task.title)
        if is_completed:
            title.setStyleSheet(
                "color: #484848; text-decoration: line-through; "
                "font-size: 11pt; background: transparent; letter-spacing: 0.1px;"
            )
        elif is_overdue:
            title.setStyleSheet(
                "color: #c8c8cc; font-size: 11pt; font-weight: 500; "
                "background: transparent; letter-spacing: 0.1px;"
            )
        else:
            title.setStyleSheet(
                "color: #e8e8ed; font-size: 11pt; font-weight: 500; "
                "background: transparent; letter-spacing: 0.1px;"
            )
        text_layout.addWidget(title)

        # Badge is always created but only shown while tracker is actively running.
        self.progress_badge = QLabel("● Tracking")
        self.progress_badge.setStyleSheet(
            "color: #8e8e93; font-size: 7.5pt; background: transparent; letter-spacing: 0.5px;"
        )
        self.progress_badge.setVisible(False)
        text_layout.addWidget(self.progress_badge)

        layout.addLayout(text_layout, stretch=1)

        # ── Right-side controls ────────────────────────────────────────────
        right_layout = QHBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)
        right_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.tracker_time_label = QLabel(self._format_duration(task.tracked_seconds))
        self.tracker_time_label.setAlignment(
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight
        )
        self.tracker_time_label.setStyleSheet(
            "color: #636366; font-size: 8.5pt; background: transparent; "
            "min-width: 52px; letter-spacing: 0.2px;"
        )

        self.tracker_btn = QPushButton()
        self.tracker_btn.setIcon(QIcon("assets/icons/play.svg"))
        self.tracker_btn.setIconSize(QSize(12, 12))
        self.tracker_btn.setFixedSize(28, 28)
        self.tracker_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.tracker_btn.setFont(QFont("Segoe UI Symbol", 10))
        self.tracker_btn.setStyleSheet(_TRACKER_BTN_IDLE)
        self.tracker_btn.clicked.connect(self._toggle_tracker)
        self._set_tracker_button()
        if self.is_completed or self.is_overdue:
            self.tracker_btn.setEnabled(False)
            self.tracker_btn.setCursor(Qt.CursorShape.ArrowCursor)

        right_layout.addWidget(self.tracker_time_label)
        right_layout.addWidget(self.tracker_btn)

        # Date chip — monochrome; overdue/today use brighter grey instead of red
        if task.due_date:
            today_flag   = task.due_date == date.today()
            overdue_flag = task.due_date < date.today()

            if today_flag or overdue_flag:
                chip_color  = "#e8e8ed"
                chip_bg     = "rgba(255,255,255,0.08)"
                chip_border = "rgba(255,255,255,0.20)"
                icon        = "⚑"
                d_str       = "Today" if today_flag else (
                    f"{task.due_date.day} {task.due_date.strftime('%b')}"
                )
            else:
                chip_color  = "#636366"
                chip_bg     = "rgba(255,255,255,0.04)"
                chip_border = "rgba(255,255,255,0.08)"
                icon        = "◷"
                d_str       = f"{task.due_date.day} {task.due_date.strftime('%b')}"

            sep = QWidget()
            sep.setFixedSize(1, 18)
            sep.setStyleSheet("background: rgba(255,255,255,0.08);")
            right_layout.addWidget(sep, alignment=Qt.AlignmentFlag.AlignVCenter)

            self.date_label = QLabel(f"{icon}  {d_str}")
            self.date_label.setStyleSheet(f"""
                color: {chip_color};
                background: {chip_bg};
                border: 1px solid {chip_border};
                font-size: 8.5pt;
                padding: 2px 9px 2px 7px;
                border-radius: 8px;
                letter-spacing: 0.2px;
            """)
            right_layout.addWidget(self.date_label, alignment=Qt.AlignmentFlag.AlignVCenter)
        else:
            self.date_label = QLabel()

        # ── "Add to Today" button — only rendered for overdue task cards ──
        if is_overdue:
            sep2 = QWidget()
            sep2.setFixedSize(1, 18)
            sep2.setStyleSheet("background: rgba(255,255,255,0.08);")
            right_layout.addWidget(sep2, alignment=Qt.AlignmentFlag.AlignVCenter)

            self.add_today_btn = QPushButton("↺  Add to today")
            self.add_today_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.add_today_btn.setStyleSheet(_ADD_TODAY_BTN)
            self.add_today_btn.setFixedHeight(24)
            self.add_today_btn.clicked.connect(self._add_to_today)
            right_layout.addWidget(self.add_today_btn, alignment=Qt.AlignmentFlag.AlignVCenter)

        self.flag_label = QLabel()
        self.flag_label.hide()

        layout.addLayout(right_layout)

        container_layout.addStretch(1)
        container_layout.addWidget(self.inner_widget)
        container_layout.addStretch(1)

    # ─────────────────────────────────────────────────────────────────────
    #  Event filter
    # ─────────────────────────────────────────────────────────────────────

    def eventFilter(self, obj, event):
        if obj is self.inner_widget:
            t = event.type()
            if t == QEvent.Type.Enter:
                self.inner_widget.setStyleSheet(self.hover_style)
            elif t == QEvent.Type.Leave:
                self.inner_widget.setStyleSheet(self.normal_style)
            elif t == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                if self.parent_page and hasattr(self.parent_page, "task_selected"):
                    self.parent_page._selected_task_id = self.task.id
                    self.parent_page.task_selected.emit(self.task.id)
        return super().eventFilter(obj, event)

    # ─────────────────────────────────────────────────────────────────────
    #  Helpers
    # ─────────────────────────────────────────────────────────────────────

    @staticmethod
    def _format_duration(seconds: int) -> str:
        if seconds <= 0:
            return "0s"
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        if h:
            return f"{h}h {m}m"
        if m:
            return f"{m}m {s}s"
        return f"{s}s"

    def _update_tracked_time_label(self) -> None:
        total = self.task.tracked_seconds
        if self.is_tracking and self.session_start_time:
            total += int((datetime.now() - self.session_start_time).total_seconds())

        if self.is_tracking:
            self.tracker_time_label.setStyleSheet(
                "color: #ffffff; font-size: 8.5pt; background: transparent; "
                "min-width: 52px; letter-spacing: 0.2px;"
            )
            self.tracker_time_label.setText(f"● {self._format_duration(total)}")
        else:
            self.tracker_time_label.setStyleSheet(
                "color: #636366; font-size: 8.5pt; background: transparent; "
                "min-width: 52px; letter-spacing: 0.2px;"
            )
            self.tracker_time_label.setText(self._format_duration(total))

    def _set_tracker_button(self) -> None:
        if self.is_tracking:
            self.tracker_btn.setText("")
            self.tracker_btn.setIcon(QIcon("assets/icons/pause.svg"))
            self.tracker_btn.setIconSize(QSize(12, 12))
            self.tracker_btn.setToolTip("Pause tracker")
            self.tracker_btn.setStyleSheet(_TRACKER_BTN_LIVE)
        else:
            self.tracker_btn.setText("")
            self.tracker_btn.setIcon(QIcon("assets/icons/play.svg"))
            self.tracker_btn.setIconSize(QSize(12, 12))
            self.tracker_btn.setToolTip("Start tracker")
            self.tracker_btn.setStyleSheet(_TRACKER_BTN_IDLE)

    # ─────────────────────────────────────────────────────────────────────
    #  Tracker logic
    # ─────────────────────────────────────────────────────────────────────

    def _toggle_completion(self, checked: bool) -> None:
        if not self.parent_page:
            return
        if self.is_tracking:
            self.pause_tracker()
        if checked:
            self.parent_page.service.mark_completed(self.task.id)
        else:
            self.task.status = TaskStatus.TODO
            self.parent_page.service.update_task(self.task.id, self.task)
        self.parent_page.refresh()

    def _toggle_tracker(self) -> None:
        # Do not start or toggle tracker for completed or overdue tasks
        if self.task.status == TaskStatus.COMPLETED or self.is_overdue:
            return
        if self.is_tracking:
            self.pause_tracker()
        elif self.parent_page:
            self.parent_page.start_task_tracker(self)
        else:
            self.start_tracker()

    def _add_to_today(self) -> None:
        """Reschedule this overdue task to today and move it back to the active list."""
        if not self.parent_page:
            return
        self.task.due_date = date.today()
        self.parent_page.service.update_task(self.task.id, self.task)
        self.parent_page.refresh()

    def start_tracker(self) -> None:
        # Don't start tracker for completed or overdue tasks
        if self.task.status == TaskStatus.COMPLETED or self.is_overdue:
            return
        if self.is_tracking:
            return
        if self.task.status == TaskStatus.TODO:
            self.task.status = TaskStatus.IN_PROGRESS
            if self.parent_page:
                self.parent_page.service.update_task(self.task.id, self.task)

        self.is_tracking = True
        self.session_start_time = datetime.now()
        self.progress_badge.setVisible(True)
        self._set_tracker_button()
        self._update_tracked_time_label()
        self.tracker_timer.start()

    def pause_tracker(self) -> None:
        if not self.is_tracking:
            return
        elapsed = 0
        if self.session_start_time:
            elapsed = int((datetime.now() - self.session_start_time).total_seconds())

        self.is_tracking = False
        self.session_start_time = None
        self.tracker_timer.stop()
        self.task.tracked_seconds += elapsed

        if self.parent_page:
            self.parent_page.service.update_task(self.task.id, self.task)
            if self.task.id in self.parent_page.active_tracker_widgets:
                del self.parent_page.active_tracker_widgets[self.task.id]
            if self.task.id in self.parent_page.active_tracker_start_times:
                del self.parent_page.active_tracker_start_times[self.task.id]

        self.progress_badge.setVisible(False)
        self._set_tracker_button()
        self._update_tracked_time_label()

    def resume_tracker(self, start_time: datetime) -> None:
        self.is_tracking = True
        self.session_start_time = start_time
        self.progress_badge.setVisible(True)
        self._set_tracker_button()
        self._update_tracked_time_label()
        self.tracker_timer.start()



# ─────────────────────────────────────────────────────────────────────────────
#  Shared list-widget stylesheet (used by all three section widgets)
# ─────────────────────────────────────────────────────────────────────────────

_LIST_WIDGET_STYLE = """
    QListWidget {
        background: transparent;
        border: none;
        outline: 0;
    }
    QListWidget::item {
        background: transparent;
        border: none;
    }
    QListWidget::item:selected {
        background: transparent;
    }
    QListWidget::item:hover {
        background: transparent;
    }
"""


class OverdueTasksSection(QWidget):
    """Collapsible section that surfaces tasks whose deadline has passed."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.collapsed = False
        self.parent_page = parent

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(0)

        # ── Divider above the section ──────────────────────────────────────
        top_divider = QWidget()
        top_divider.setFixedHeight(1)
        top_divider.setStyleSheet("background: rgba(255,255,255,0.07);")
        layout.addWidget(top_divider)

        # ── Header row ────────────────────────────────────────────────────
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(15, 10, 15, 10)

        self.collapse_btn = QPushButton()
        self.collapse_btn.setFixedSize(20, 20)
        self.collapse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.collapse_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #c8c8cc;
                font-size: 12px;
                padding: 0px;
            }
            QPushButton:hover { color: #ffffff; }
        """)
        self.collapse_btn.setText("▼")
        self.collapse_btn.clicked.connect(self._toggle_collapse)

        header_layout.addStretch()
        header_layout.addWidget(self.collapse_btn)

        self.header_label = QLabel("Overdue")
        self.header_label.setStyleSheet(
            "font-weight: bold; font-size: 11pt; color: #c8c8cc; margin-left: 6px;"
        )
        header_layout.addWidget(self.header_label)

        self.count_label = QLabel("(0)")
        self.count_label.setStyleSheet(
            "color: rgba(255,255,255,0.4); font-size: 10pt; margin-left: 5px;"
        )
        header_layout.addWidget(self.count_label)

        header_layout.addStretch()
        layout.addLayout(header_layout)

        # ── Task list ──────────────────────────────────────────────────────
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(_LIST_WIDGET_STYLE)
        layout.addWidget(self.list_widget, 1)

    # ── Collapse / expand ──────────────────────────────────────────────────

    def _toggle_collapse(self, force: bool | None = None):
        if force is not None:
            self.collapsed = force
        else:
            self.collapsed = not self.collapsed
        if self.collapsed:
            self.collapse_btn.setText("▶")
            self.list_widget.hide()
        else:
            self.collapse_btn.setText("▼")
            self.list_widget.show()

    # ── Populate ───────────────────────────────────────────────────────────

    def populate(self, overdue_tasks: list[PlannerTask]) -> None:
        self.list_widget.clear()
        self.count_label.setText(f"({len(overdue_tasks)})")
        for task in overdue_tasks:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, task.id)
            widget = PlannerTaskItemWidget(task, parent=self.parent_page, is_overdue=True)
            item.setSizeHint(widget.sizeHint())
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, widget)


class CompletedTasksSection(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.collapsed = False
        self.parent_page = parent

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(0)

        # ── Divider above the section ──────────────────────────────────────
        top_divider = QWidget()
        top_divider.setFixedHeight(1)
        top_divider.setStyleSheet("background: rgba(255,255,255,0.07);")
        layout.addWidget(top_divider)

        # ── Header row ────────────────────────────────────────────────────
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(15, 10, 15, 10)

        self.collapse_btn = QPushButton()
        self.collapse_btn.setFixedSize(20, 20)
        self.collapse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.collapse_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: white;
                font-size: 12px;
                padding: 0px;
            }
            QPushButton:hover { color: #ffffff; }
        """)
        self.collapse_btn.setText("▼")
        self.collapse_btn.clicked.connect(self._toggle_collapse)

        header_layout.addStretch()
        header_layout.addWidget(self.collapse_btn)

        self.header_label = QLabel("Completed Tasks")
        self.header_label.setStyleSheet(
            "font-weight: bold; font-size: 11pt; color: rgba(255,255,255,0.9); margin-left: 6px;"
        )
        header_layout.addWidget(self.header_label)

        self.count_label = QLabel("(0)")
        self.count_label.setStyleSheet(
            "color: rgba(255,255,255,0.6); font-size: 10pt; margin-left: 5px;"
        )
        header_layout.addWidget(self.count_label)

        header_layout.addStretch()
        layout.addLayout(header_layout)

        # ── Task list ──────────────────────────────────────────────────────
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(_LIST_WIDGET_STYLE)
        layout.addWidget(self.list_widget, 1)

        # ── Archive button ─────────────────────────────────────────────────
        self.archive_btn = QPushButton("✓ Move completed tasks to archive")
        self.archive_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        # shrink to content so hover background only covers the text area
        self.archive_btn.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self.archive_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #c8c8cc;
                padding: 8px 12px;
                margin: 10px 15px 15px 15px;
                border-radius: 8px;
            }
            QPushButton:hover {
                color: #e8e8ed;
                background: rgba(255,255,255,0.03);
            }
            QPushButton:pressed {
                background: rgba(255,255,255,0.06);
            }
        """)
        self.archive_btn.clicked.connect(self._archive_completed)
        layout.addWidget(self.archive_btn, 0, Qt.AlignmentFlag.AlignHCenter)

    def _toggle_collapse(self, force: bool | None = None):
        if force is not None:
            self.collapsed = force
        else:
            self.collapsed = not self.collapsed
        if self.collapsed:
            self.collapse_btn.setText("▶")
            self.list_widget.hide()
            self.archive_btn.hide()
        else:
            self.collapse_btn.setText("▼")
            self.list_widget.show()
            self.archive_btn.show()

    def _archive_completed(self):
        if self.parent_page:
            self.parent_page.archive_completed_tasks()

    def populate(self, completed_tasks: list[PlannerTask]) -> None:
        self.list_widget.clear()
        self.count_label.setText(f"({len(completed_tasks)})")
        for task in completed_tasks:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, task.id)
            widget = PlannerTaskItemWidget(task, parent=self.parent_page)
            item.setSizeHint(widget.sizeHint())
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, widget)


class TasksPage(QWidget):
    create_task_requested = Signal()
    task_selected = Signal(int)

    def __init__(self, service: TasksService) -> None:
        super().__init__()
        self.service = service
        self._selected_task_id: int | None = None
        # support multiple concurrent trackers: map task_id -> widget and start time
        self.active_tracker_widgets: dict[int, PlannerTaskItemWidget] = {}
        self.active_tracker_start_times: dict[int, datetime] = {}
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Toolbar
        # Toolbar substitute
        toolbar = QWidget()
        toolbar.setFixedHeight(50)
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(20, 0, 20, 0)
        toolbar_layout.setSpacing(10)
        
        toolbar_layout.addStretch()
        
        self.add_button = QPushButton()
        self.add_button.setIcon(QIcon("assets/icons/plus.svg"))
        self.add_button.setIconSize(QSize(16, 16))
        self.add_button.setToolTip("Add Task")
        self.add_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_button.setFixedSize(44, 44)
        self.add_button.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 22px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.08);
                border: none;
            }
            QPushButton:pressed {
                background: rgba(255, 255, 255, 0.15);
                border: none;
            }
        """)
        toolbar_layout.addWidget(self.add_button)
        toolbar_layout.addStretch()
        
        layout.addWidget(toolbar)
        

        # Scroll area for task content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
        """)

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # ── Active task list & Empty State ────────────────────────────────
        self.active_stack = QStackedWidget()
        
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(_LIST_WIDGET_STYLE)
        
        # Empty state
        self.empty_state = QWidget()
        empty_layout = QVBoxLayout(self.empty_state)
        empty_layout.setAlignment(Qt.AlignCenter)
        empty_label = QLabel("You're all caught up for today! 🎉\nEnjoy your day or add a new task.")
        empty_label.setAlignment(Qt.AlignCenter)
        empty_label.setStyleSheet("color: #636366; font-size: 14px; line-height: 1.4;")
        empty_layout.addWidget(empty_label)
        
        self.active_stack.addWidget(self.list_widget)
        self.active_stack.addWidget(self.empty_state)
        
        content_layout.addWidget(self.active_stack, 1)

        # ── Overdue tasks section (hidden until there are overdue tasks) ───
        self.overdue_section = OverdueTasksSection(parent=self)
        self.overdue_section.hide()
        content_layout.addWidget(self.overdue_section)

        # ── Completed tasks section ────────────────────────────────────────
        self.completed_section = CompletedTasksSection(parent=self)
        self.completed_section.hide()
        content_layout.addWidget(self.completed_section)

        content_layout.addStretch()

        scroll.setWidget(content_widget)
        layout.addWidget(scroll, 1)

        # Connections
        self.add_button.clicked.connect(self.add_task)

    # ─────────────────────────────────────────────────────────────────────
    #  State persistence
    # ─────────────────────────────────────────────────────────────────────

    def save_state(self, settings):
        settings.beginGroup("tasks_page")
        settings.setValue("overdue_collapsed", self.overdue_section.collapsed)
        settings.setValue("completed_collapsed", self.completed_section.collapsed)
        settings.endGroup()

    def restore_state(self, settings):
        settings.beginGroup("tasks_page")
        overdue_collapsed = settings.value("overdue_collapsed", False, type=bool)
        completed_collapsed = settings.value("completed_collapsed", False, type=bool)
        settings.endGroup()
        # Apply to sections (only takes effect once they are visible)
        if overdue_collapsed:
            self.overdue_section._toggle_collapse(force=True)
        if completed_collapsed:
            self.completed_section._toggle_collapse(force=True)

    # ─────────────────────────────────────────────────────────────────────
    #  Tracker management
    # ─────────────────────────────────────────────────────────────────────

    def start_task_tracker(self, widget: PlannerTaskItemWidget) -> None:
        task_id = widget.task.id
        if task_id in self.active_tracker_widgets:
            return

        widget.start_tracker()
        self.active_tracker_widgets[task_id] = widget
        self.active_tracker_start_times[task_id] = widget.session_start_time

    def clear_active_tracker(self) -> None:
        self.active_tracker_widgets.clear()
        self.active_tracker_start_times.clear()

    # ─────────────────────────────────────────────────────────────────────
    #  Refresh
    # ─────────────────────────────────────────────────────────────────────

    def refresh(self) -> None:
        tasks = self.service.get_all_tasks()
        today = date.today()

        # ── Categorise tasks into three buckets ───────────────────────────
        # overdue: not completed, has a past due date
        # active:  not completed, no due date OR due date is today or future
        # completed: status == COMPLETED (regardless of date)
        active_tasks = [
            t for t in tasks
            if t.status != TaskStatus.COMPLETED
            and (t.due_date is None or t.due_date >= today)
        ]
        overdue_tasks = [
            t for t in tasks
            if t.status != TaskStatus.COMPLETED
            and t.due_date is not None
            and t.due_date < today
        ]
        completed_tasks = [t for t in tasks if t.status == TaskStatus.COMPLETED]

        # Preserve running tracker state across the refresh
        active_task_ids = set(self.active_tracker_widgets.keys())

        # ── Populate active tasks ──────────────────────────────────────────
        self.list_widget.clear()
        for task in active_tasks:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, task.id)
            widget = PlannerTaskItemWidget(task, parent=self)
            if task.id in active_task_ids and self.active_tracker_start_times.get(task.id) is not None:
                widget.resume_tracker(self.active_tracker_start_times[task.id])
            item.setSizeHint(widget.sizeHint())
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, widget)
            
        if active_tasks:
            self.active_stack.setCurrentWidget(self.list_widget)
        else:
            self.active_stack.setCurrentWidget(self.empty_state)
        if active_tasks and self.list_widget.currentRow() < 0:
            self.list_widget.setCurrentRow(0)

        # ── Populate / hide overdue section ───────────────────────────────
        if overdue_tasks:
            self.overdue_section.show()
            self.overdue_section.populate(overdue_tasks)
        else:
            self.overdue_section.hide()

        # ── Populate / hide completed section ─────────────────────────────
        if completed_tasks:
            self.completed_section.show()
            self.completed_section.populate(completed_tasks)
        else:
            self.completed_section.hide()

    # ─────────────────────────────────────────────────────────────────────
    #  Task CRUD helpers
    # ─────────────────────────────────────────────────────────────────────

    def _selected_task_id_value(self) -> int | None:
        item = self.list_widget.currentItem()
        if item is None:
            return self._selected_task_id
        value = item.data(Qt.ItemDataRole.UserRole)
        return int(value) if value is not None else None

    def _on_item_clicked(self, item):
        task_id = item.data(Qt.ItemDataRole.UserRole)
        if task_id is not None:
            self._selected_task_id = int(task_id)
            self.task_selected.emit(int(task_id))
            
    def add_task(self) -> None:
        self.create_task_requested.emit()

    def delete_task(self) -> None:
        task_id = self._selected_task_id_value()
        if task_id is None:
            return
        self.service.delete_task(task_id)
        self._selected_task_id = None
        self.refresh()

    def select_task(self, task_id: int) -> None:
        for row in range(self.list_widget.count()):
            item = self.list_widget.item(row)
            if int(item.data(Qt.ItemDataRole.UserRole)) == task_id:
                self.list_widget.setCurrentRow(row)
                break

    def mark_selected_completed(self) -> None:
        task_id = self._selected_task_id_value()
        if task_id is None:
            return
        self.service.mark_completed(task_id)
        self.refresh()
        self.select_task(task_id)

    def mark_selected_skipped(self) -> None:
        task_id = self._selected_task_id_value()
        if task_id is None:
            return
        self.service.mark_skipped(task_id)
        self.refresh()
        self.select_task(task_id)

    def carry_forward(self) -> None:
        self.service.carry_forward()
        self.refresh()

    def archive_completed_tasks(self) -> None:
        tasks = self.service.get_all_tasks()
        completed_tasks = [t for t in tasks if t.status == TaskStatus.COMPLETED]
        for task in completed_tasks:
            self.service.delete_task(task.id)
        self.refresh()