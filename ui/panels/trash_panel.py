from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QListWidget, QListWidgetItem, QPushButton, QMessageBox
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon


class TrashPanel(QWidget):
    """
    Trash panel — shows soft-deleted topics with Restore and Delete Forever options.
    """
    topic_restored = Signal()  # emitted when a topic is restored (so Notes panel can refresh)

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

        title = QLabel("TRASH")
        title.setStyleSheet(
            "font-size:11px; font-weight:700; color:#cccccc; letter-spacing:1px; padding-left:4px;"
        )
        h_layout.addWidget(title)
        h_layout.addStretch()

        # Empty Trash button
        empty_btn = QPushButton("Empty")
        empty_btn.setFixedSize(52, 20)
        empty_btn.setStyleSheet("""
            QPushButton {
                border: 1px solid #555;
                background: transparent;
                color: #888;
                font-size: 10px;
                border-radius: 3px;
            }
            QPushButton:hover { background: rgba(255,80,80,0.12); color: #ff6b6b; border-color: #ff6b6b; }
        """)
        empty_btn.setToolTip("Permanently delete all trashed items")
        empty_btn.clicked.connect(self.empty_trash)
        h_layout.addWidget(empty_btn)

        layout.addWidget(header)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background:#2a2a2a; border:none; max-height:1px;")
        layout.addWidget(sep)

        # ── List ───────────────────────────────────────────────────────────
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget {
                background: transparent;
                border: none;
                outline: none;
                color: #888888;
                font-size: 13px;
                padding: 4px 0;
            }
            QListWidget::item { padding: 4px 8px; margin: 1px 4px; border-radius:3px; }
            QListWidget::item:hover { background: rgba(255,255,255,0.06); }
            QListWidget::item:selected { background: #37373d; }
        """)
        layout.addWidget(self.list_widget)

        self.load_trash()

    def load_trash(self):
        self.list_widget.clear()
        from core.database import get_session
        from core.models import Topic

        session = get_session()
        deleted = session.query(Topic).filter_by(is_deleted=True).all()
        session.close()

        if not deleted:
            placeholder = QListWidgetItem("  Trash is empty")
            placeholder.setFlags(Qt.NoItemFlags)
            placeholder.setForeground(Qt.darkGray)
            self.list_widget.addItem(placeholder)
            return

        for topic in deleted:
            # Container widget per item
            container = QWidget()
            container.setStyleSheet("background: transparent;")
            row = QHBoxLayout(container)
            row.setContentsMargins(8, 2, 4, 2)
            row.setSpacing(6)

            icon_lbl = QLabel()
            icon_lbl.setPixmap(QIcon("assets/icons/note-file.svg").pixmap(QSize(14, 14)))
            row.addWidget(icon_lbl)

            name_lbl = QLabel(topic.name)
            name_lbl.setStyleSheet("color:#888888; font-size:13px;")
            row.addWidget(name_lbl)
            row.addStretch()

            restore_btn = QPushButton("Restore")
            restore_btn.setFixedSize(52, 20)
            restore_btn.setStyleSheet("""
                QPushButton { border:1px solid #555; background:transparent; color:#888; font-size:10px; border-radius:3px; }
                QPushButton:hover { background:rgba(80,180,80,0.15); color:#7dbb7d; border-color:#7dbb7d; }
            """)
            restore_btn.clicked.connect(lambda _, tid=topic.id: self.restore_topic(tid))
            row.addWidget(restore_btn)

            del_btn = QPushButton("✕")
            del_btn.setFixedSize(20, 20)
            del_btn.setStyleSheet("""
                QPushButton { border:none; background:transparent; color:#666; font-size:12px; border-radius:3px; }
                QPushButton:hover { background:rgba(255,80,80,0.15); color:#ff6b6b; }
            """)
            del_btn.setToolTip("Delete forever")
            del_btn.clicked.connect(lambda _, tid=topic.id: self.delete_forever(tid))
            row.addWidget(del_btn)

            list_item = QListWidgetItem(self.list_widget)
            list_item.setSizeHint(container.sizeHint())
            list_item.setData(Qt.UserRole, topic.id)
            self.list_widget.addItem(list_item)
            self.list_widget.setItemWidget(list_item, container)

    def restore_topic(self, topic_id: int):
        from core.database import get_session
        from core.models import Topic

        session = get_session()
        topic = session.get(Topic, topic_id)
        if topic:
            topic.is_deleted = False
            session.commit()
        session.close()
        self.load_trash()
        self.topic_restored.emit()

    def delete_forever(self, topic_id: int):
        from core.database import get_session
        from core.models import Topic

        session = get_session()
        topic = session.get(Topic, topic_id)
        if topic:
            session.delete(topic)
            session.commit()
        session.close()
        self.load_trash()

    def empty_trash(self):
        reply = QMessageBox.question(
            self, "Empty Trash",
            "Permanently delete all items in Trash? This cannot be undone.",
            QMessageBox.Yes | QMessageBox.Cancel,
        )
        if reply != QMessageBox.Yes:
            return

        from core.database import get_session
        from core.models import Topic

        session = get_session()
        deleted = session.query(Topic).filter_by(is_deleted=True).all()
        for t in deleted:
            session.delete(t)
        session.commit()
        session.close()
        self.load_trash()
