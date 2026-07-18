from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QListWidget, QListWidgetItem
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon


class TagsPanel(QWidget):
    """
    Tags panel — placeholder for future tag browsing.
    Currently shows a friendly empty state with instructions.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Header ─────────────────────────────────────────────────────────
        header = QWidget()
        header.setFixedHeight(36)
        header.setStyleSheet("background: #181818;")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(12, 0, 6, 0)
        h_layout.setSpacing(4)

        chevron = QLabel("›")
        chevron.setStyleSheet("color:#888; font-size:14px;")
        h_layout.addWidget(chevron)

        title = QLabel("TAGS")
        title.setStyleSheet(
            "font-size:11px; font-weight:700; color:#cccccc; letter-spacing:1px; padding-left:4px;"
        )
        h_layout.addWidget(title)
        h_layout.addStretch()
        layout.addWidget(header)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background:#2a2a2a; border:none; max-height:1px;")
        layout.addWidget(sep)

        # ── Empty state ────────────────────────────────────────────────────
        layout.addStretch()

        icon_label = QLabel()
        icon_label.setPixmap(QIcon("assets/icons/act-tags.svg").pixmap(QSize(40, 40)))
        icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_label)

        msg = QLabel("No tags yet")
        msg.setAlignment(Qt.AlignCenter)
        msg.setStyleSheet("color:#888888; font-size:13px; padding-top:8px;")
        layout.addWidget(msg)

        hint = QLabel("Add #tags inside your notes\nto organize them here.")
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet("color:#555555; font-size:11px; padding-top:4px;")
        layout.addWidget(hint)

        layout.addStretch()
