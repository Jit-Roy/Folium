from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame, QHBoxLayout, QGridLayout
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QColor, QPen, QFont

_T_PRI = "#ffffff"
_T_SEC = "#a0a0a0"
_T_DIM = "#808080"

class CircularProgress(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(120, 120)
        self.value = 0

    def set_value(self, value):
        self.value = value
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(10, 10, self.width() - 20, self.height() - 20)

        # Draw background ring
        pen = QPen(QColor(255, 255, 255, 10))
        pen.setWidth(8)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawArc(rect, 0, 360 * 16)

        # Draw progress ring
        # Zstudy accent color is often a soft purple #B48EAD or #81A1C1
        pen = QPen(QColor("#B48EAD"))
        pen.setWidth(8)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        
        span_angle = int((self.value / 100.0) * 360 * 16)
        # 90 degrees offset to start from top, drawing counter-clockwise so negative angle
        painter.drawArc(rect, 90 * 16, -span_angle)

        # Draw text
        painter.setPen(QColor(_T_PRI))
        font = QFont("Inter", 16, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, f"{self.value}%")
        painter.end()


class HabitsSidebar(QWidget):
    def __init__(self, habit_service, parent=None):
        super().__init__(parent)
        self.habit_service = habit_service
        self.setObjectName("contextSidebar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("""
            QWidget#contextSidebar { background: #181818; }
            .QWidget { background: transparent; }
        """)

        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignmentFlag.AlignTop)
        lay.setContentsMargins(20, 24, 20, 24)
        lay.setSpacing(8)

        lbl = QLabel("Habits")
        lbl.setStyleSheet("color: #ffffff; font-size: 13pt; font-weight: bold; letter-spacing: 0.5px; background: transparent;")
        lay.addWidget(lbl)

        desc = QLabel("Daily Trackers")
        desc.setStyleSheet(f"color: {_T_SEC}; font-size: 10pt; background: transparent;")
        lay.addWidget(desc)

        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setFixedHeight(1)
        div.setStyleSheet("background: rgba(255,255,255,0.05); border: none; margin-top: 12px; margin-bottom: 12px;")
        lay.addWidget(div)
        
        # ── Total Completion Rate ──
        rate_lbl = QLabel("WEEKLY COMPLETION")
        rate_lbl.setStyleSheet(f"color: {_T_DIM}; font-size: 8pt; font-weight: bold; letter-spacing: 1px; background: transparent;")
        lay.addWidget(rate_lbl)

        self.progress = CircularProgress()
        # Center the progress ring
        prog_lay = QHBoxLayout()
        prog_lay.addWidget(self.progress)
        prog_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        prog_wrap = QWidget()
        prog_wrap.setLayout(prog_lay)
        lay.addWidget(prog_wrap)
        
        lay.addSpacing(20)

        # ── Stats Grid ──
        grid = QGridLayout()
        grid.setSpacing(15)

        streak_title = QLabel("LONGEST STREAK")
        streak_title.setStyleSheet(f"color: {_T_DIM}; font-size: 7.5pt; font-weight: bold; letter-spacing: 0.5px; background: transparent;")
        grid.addWidget(streak_title, 0, 0)

        self.streak_val = QLabel("0 Days")
        self.streak_val.setStyleSheet(f"color: {_T_PRI}; font-size: 11pt; font-weight: bold; background: transparent;")
        grid.addWidget(self.streak_val, 1, 0)
        
        self.streak_name = QLabel("None")
        self.streak_name.setStyleSheet(f"color: {_T_DIM}; font-size: 8pt; background: transparent;")
        grid.addWidget(self.streak_name, 2, 0)

        perfect_title = QLabel("PERFECT DAYS")
        perfect_title.setStyleSheet(f"color: {_T_DIM}; font-size: 7.5pt; font-weight: bold; letter-spacing: 0.5px; background: transparent;")
        grid.addWidget(perfect_title, 0, 1)

        self.perfect_val = QLabel("0")
        self.perfect_val.setStyleSheet(f"color: {_T_PRI}; font-size: 11pt; font-weight: bold; background: transparent;")
        grid.addWidget(self.perfect_val, 1, 1)

        perfect_desc = QLabel("This Month")
        perfect_desc.setStyleSheet(f"color: {_T_DIM}; font-size: 8pt; background: transparent;")
        grid.addWidget(perfect_desc, 2, 1)

        lay.addLayout(grid)
        lay.addStretch()
        
        self.refresh_stats()

    def refresh_stats(self, week_start=None, week_end=None):
        from datetime import date, timedelta
        if week_start is None:
            # Default to current week
            today = date.today()
            week_start = today - timedelta(days=today.weekday())
            week_end = week_start + timedelta(days=6)
            
        stats = self.habit_service.habits.get_stats(week_start, week_end)
        self.progress.set_value(stats["completion_rate"])
        
        streak = stats["longest_streak"]
        self.streak_val.setText(f"{streak} Day{'s' if streak != 1 else ''}")
        self.streak_name.setText(stats["longest_streak_name"][:15] + ("..." if len(stats["longest_streak_name"]) > 15 else ""))
        
        self.perfect_val.setText(str(stats["perfect_days"]))
