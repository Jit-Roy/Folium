from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QFrame, QHBoxLayout, QPushButton, QCalendarWidget
)
from PySide6.QtCore import Qt, Signal, QDate, QRectF
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QTextCharFormat
from ui.panels.habits_sidebar import CircularProgress

_T_PRI = "#ffffff"
_T_SEC = "#a0a0a0"
_T_DIM = "#808080"


class PlannerSidebar(QWidget):
    # Emits a date to the PlannerPanel so it can jump to that week
    date_selected = Signal(QDate)
    
    # Emits a request to navigate weeks (offset)
    navigate_weeks = Signal(int) # -1 for last week, 1 for next week, 0 for this week

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("plannerSidebar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("""
            QWidget#plannerSidebar { background: #181818; }
            .QWidget { background: transparent; }
        """)

        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignmentFlag.AlignTop)
        lay.setContentsMargins(20, 24, 20, 24)
        lay.setSpacing(8)

        # ── Header ──
        lbl = QLabel("Planner")
        lbl.setStyleSheet(f"color: {_T_PRI}; font-size: 13pt; font-weight: bold; letter-spacing: 0.5px; background: transparent;")
        lay.addWidget(lbl)

        desc = QLabel("Weekly Goals")
        desc.setStyleSheet(f"color: {_T_SEC}; font-size: 10pt; background: transparent;")
        lay.addWidget(desc)

        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setFixedHeight(1)
        div.setStyleSheet("background: rgba(255,255,255,0.05); border: none; margin-top: 12px; margin-bottom: 12px;")
        lay.addWidget(div)

        # ── Mini Calendar ──
        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(False)
        self.calendar.setNavigationBarVisible(True)
        self.calendar.setStyleSheet("""
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
                background-color: transparent;
                selection-background-color: #B48EAD;
                selection-color: #2D2036;
            }
            QCalendarWidget QAbstractItemView:disabled {
                color: #555555;
            }
        """)
        
        fmt = QTextCharFormat()
        fmt.setForeground(QColor("#B48EAD"))
        self.calendar.setWeekdayTextFormat(Qt.DayOfWeek.Saturday, fmt)
        self.calendar.setWeekdayTextFormat(Qt.DayOfWeek.Sunday, fmt)

        self.calendar.clicked.connect(self._on_calendar_clicked)
        lay.addWidget(self.calendar)
        
        div2 = QFrame()
        div2.setFrameShape(QFrame.Shape.HLine)
        div2.setFixedHeight(1)
        div2.setStyleSheet("background: rgba(255,255,255,0.05); border: none; margin-top: 12px; margin-bottom: 12px;")
        lay.addWidget(div2)

        # ── Quick Navigation ──
        nav_lbl = QLabel("QUICK FILTERS")
        nav_lbl.setStyleSheet(f"color: {_T_DIM}; font-size: 8pt; font-weight: bold; letter-spacing: 1px; background: transparent;")
        lay.addWidget(nav_lbl)

        btn_style = """
            QPushButton {
                background: rgba(255,255,255,0.05);
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 8px 12px;
                text-align: left;
            }
            QPushButton:hover { background: rgba(255,255,255,0.1); }
        """

        self.btn_last_week = QPushButton("Last Week")
        self.btn_last_week.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_last_week.setStyleSheet(btn_style)
        self.btn_last_week.clicked.connect(lambda: self.navigate_weeks.emit(-1))
        lay.addWidget(self.btn_last_week)

        self.btn_this_week = QPushButton("This Week")
        self.btn_this_week.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_this_week.setStyleSheet(btn_style)
        self.btn_this_week.clicked.connect(lambda: self.navigate_weeks.emit(0))
        lay.addWidget(self.btn_this_week)

        self.btn_next_week = QPushButton("Next Week")
        self.btn_next_week.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_next_week.setStyleSheet(btn_style)
        self.btn_next_week.clicked.connect(lambda: self.navigate_weeks.emit(1))
        lay.addWidget(self.btn_next_week)

        div3 = QFrame()
        div3.setFrameShape(QFrame.Shape.HLine)
        div3.setFixedHeight(1)
        div3.setStyleSheet("background: rgba(255,255,255,0.05); border: none; margin-top: 12px; margin-bottom: 12px;")
        lay.addWidget(div3)

        # ── Weekly Completion ──
        comp_lbl = QLabel("WEEKLY COMPLETION")
        comp_lbl.setStyleSheet(f"color: {_T_DIM}; font-size: 8pt; font-weight: bold; letter-spacing: 1px; background: transparent;")
        lay.addWidget(comp_lbl)

        self.progress = CircularProgress()
        prog_lay = QHBoxLayout()
        prog_lay.addWidget(self.progress)
        prog_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        prog_wrap = QWidget()
        prog_wrap.setLayout(prog_lay)
        lay.addWidget(prog_wrap)
        
        self.stats_lbl = QLabel("0 / 0 goals completed")
        self.stats_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.stats_lbl.setStyleSheet(f"color: {_T_SEC}; font-size: 9pt; background: transparent;")
        lay.addWidget(self.stats_lbl)

        lay.addStretch()

    def _on_calendar_clicked(self, date: QDate):
        self.date_selected.emit(date)

    def update_stats(self, completed: int, total: int):
        if total == 0:
            percentage = 0
        else:
            percentage = int((completed / total) * 100)
            
        self.progress.set_value(percentage)
        self.stats_lbl.setText(f"{completed} / {total} goals completed")

    def sync_calendar(self, start_date: QDate):
        """Called by PlannerPanel to sync the calendar selection to the currently viewed week."""
        self.calendar.blockSignals(True)
        self.calendar.setSelectedDate(start_date)
        self.calendar.blockSignals(False)
