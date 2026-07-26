"""
Note Version History Dialog
Presents a chronological list of auto-saved note snapshots
with a diff viewer and one-click restore functionality.
"""
from __future__ import annotations

import difflib
import re
from datetime import datetime

from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QTextEdit, QSplitter,
    QPushButton, QFrame, QWidget, QScrollArea, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QFont, QColor, QTextCharFormat, QTextCursor


# ── Helpers ────────────────────────────────────────────────────────────────

def _strip_html(html: str) -> str:
    text = re.sub(r'<[^>]+>', ' ', html or '')
    text = text.replace('&nbsp;', ' ').replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
    return re.sub(r'\s+', ' ', text).strip()


def _word_count(html: str) -> int:
    plain = _strip_html(html)
    return len([w for w in plain.split() if w.strip()])


def _format_timestamp(dt: datetime) -> str:
    if dt is None:
        return '—'
    now = datetime.utcnow()
    delta = now - dt
    if delta.days == 0:
        if delta.seconds < 60:
            return 'Just now'
        if delta.seconds < 3600:
            return f'{delta.seconds // 60} min ago'
        return f'{delta.seconds // 3600} hr ago'
    if delta.days == 1:
        return f'Yesterday {dt.strftime("%H:%M")}'
    return dt.strftime('%b %d, %Y  %H:%M')


# ── History View ─────────────────────────────────────────────────────────

class NoteHistoryView(QWidget):
    """
    Widget to browse, diff, and restore note history snapshots.
    Emits restore_requested(html_content) when the user chooses to restore.
    """
    restore_requested = Signal(str)
    close_requested = Signal()

    def __init__(self, note_id: int, current_content: str, parent=None):
        super().__init__(parent)
        self._note_id = note_id
        self._current_content = current_content
        self._versions: list = []   # list of NoteVersion ORM objects
        self._selected_version = None

        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("""
            QWidget {
                background: #1a1a1a;
            }
        """)
        self._init_ui()
        self._load_versions()

    # ── UI ─────────────────────────────────────────────────────────────────

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)



        # ── Main splitter: version list | diff view ──
        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet('QSplitter::handle { background: #2a2a2a; width: 2px; }')
        root.addWidget(splitter)

        # Left: version list
        left_widget = QWidget()
        left_widget.setStyleSheet('background: #181818;')
        left_widget.setFixedWidth(240)
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        list_header = QLabel('  VERSIONS')
        list_header.setFixedHeight(34)
        list_header.setStyleSheet('color: #666; font-size: 10px; font-weight: bold; letter-spacing: 1px; background: #141414; border-bottom: 1px solid #2a2a2a;')
        list_header.setAlignment(Qt.AlignVCenter)

        self._version_list = QListWidget()
        self._version_list.setStyleSheet("""
            QListWidget {
                background: #181818;
                border: none;
            }
            QListWidget::item {
                border-bottom: 1px solid #2a2a2a;
                padding: 10px 12px;
                color: #aaa;
                font-size: 12px;
            }
            QListWidget::item:selected {
                background: #2D2036;
                color: #e0e0e0;
                border-left: 3px solid #B48EAD;
            }
            QListWidget::item:hover {
                background: #222;
            }
        """)
        self._version_list.currentRowChanged.connect(self._on_version_selected)

        left_layout.addWidget(list_header)
        left_layout.addWidget(self._version_list)
        splitter.addWidget(left_widget)

        # Right: diff viewer + restore button
        right_widget = QWidget()
        right_widget.setStyleSheet('background: #1a1a1a;')
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # Diff header
        diff_header = QWidget()
        diff_header.setFixedHeight(40)
        diff_header.setStyleSheet('background: #141414; border-bottom: 1px solid #2a2a2a;')
        dh_layout = QHBoxLayout(diff_header)
        dh_layout.setContentsMargins(16, 0, 12, 0)

        self._diff_title = QLabel('Select a version to compare')
        self._diff_title.setStyleSheet('color: #888; font-size: 12px;')

        self._restore_btn = QPushButton('⟳  Restore this version')
        self._restore_btn.setFixedHeight(28)
        self._restore_btn.setEnabled(False)
        self._restore_btn.setStyleSheet("""
            QPushButton {
                background: #2D2036;
                color: #B48EAD;
                border: 1px solid #4D305A;
                border-radius: 5px;
                font-size: 12px;
                padding: 0 14px;
            }
            QPushButton:hover:enabled {
                background: #3d2a4a;
                border-color: #B48EAD;
            }
            QPushButton:disabled { color: #555; border-color: #333; background: #1e1e1e; }
        """)
        self._restore_btn.clicked.connect(self._on_restore)

        dh_layout.addWidget(self._diff_title)
        dh_layout.addStretch()
        dh_layout.addWidget(self._restore_btn)

        # Legend
        legend = QWidget()
        legend.setStyleSheet('background: #141414; border-bottom: 1px solid #2a2a2a;')
        legend.setFixedHeight(28)
        leg_layout = QHBoxLayout(legend)
        leg_layout.setContentsMargins(16, 0, 16, 0)
        leg_layout.setSpacing(20)
        for color, label in [('#3a5a3a', '+ Added'), ('#5a3a3a', '− Removed'), ('#3a3a3a', '  Unchanged')]:
            lbl = QLabel(f'<span style="background:{color}; padding:1px 6px; border-radius:3px;">&nbsp;</span>  {label}')
            lbl.setTextFormat(Qt.RichText)
            lbl.setStyleSheet('color: #888; font-size: 11px;')
            leg_layout.addWidget(lbl)
        leg_layout.addStretch()

        # Diff text area
        self._diff_view = QTextEdit()
        self._diff_view.setReadOnly(True)
        self._diff_view.setFont(QFont('Consolas', 10))
        self._diff_view.setStyleSheet("""
            QTextEdit {
                background: #1a1a1a;
                color: #c0c0c0;
                border: none;
                padding: 12px;
                line-height: 1.6;
            }
        """)
        self._diff_view.setLineWrapMode(QTextEdit.WidgetWidth)

        right_layout.addWidget(diff_header)
        right_layout.addWidget(legend)
        right_layout.addWidget(self._diff_view)

        splitter.addWidget(right_widget)
        splitter.setSizes([240, 720])
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)

    # ── Data ───────────────────────────────────────────────────────────────

    def _load_versions(self):
        from core.database import get_session
        from core.models import NoteVersion

        session = get_session()
        try:
            self._versions = (
                session.query(NoteVersion)
                .filter_by(note_id=self._note_id)
                .order_by(NoteVersion.saved_at.desc())
                .all()
            )
            # Detach from session by loading attributes
            self._versions = [
                {'id': v.id, 'content': v.content, 'word_count': v.word_count, 'saved_at': v.saved_at}
                for v in self._versions
            ]
        finally:
            session.close()

        self._version_list.clear()
        if not self._versions:
            item = QListWidgetItem('No history yet.\nSave the note to create\nyour first snapshot.')
            item.setFlags(Qt.NoItemFlags)
            self._version_list.addItem(item)
            return

        for i, v in enumerate(self._versions):
            ts = _format_timestamp(v['saved_at'])
            wc = v['word_count']
            label = f'{ts}\n{wc} words'
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, i)
            self._version_list.addItem(item)

        # Auto-select the most recent version
        self._version_list.setCurrentRow(0)

    def _on_version_selected(self, row: int):
        if row < 0 or row >= len(self._versions):
            self._diff_view.clear()
            self._restore_btn.setEnabled(False)
            return

        v = self._versions[row]
        self._selected_version = v
        ts = v['saved_at'].strftime('%B %d, %Y at %H:%M:%S') if v['saved_at'] else '—'
        self._diff_title.setText(f'Comparing to version from  {ts}')
        self._restore_btn.setEnabled(True)
        self._show_diff(v['content'])

    def _show_diff(self, old_html: str):
        current_plain = _strip_html(self._current_content).splitlines(keepends=True)
        old_plain = _strip_html(old_html).splitlines(keepends=True)

        diff = list(difflib.ndiff(old_plain, current_plain))

        doc = self._diff_view
        doc.clear()
        cursor = doc.textCursor()
        cursor.movePosition(QTextCursor.Start)

        base_fmt = QTextCharFormat()
        base_fmt.setFontFamily('Consolas')
        base_fmt.setFontPointSize(10)

        add_fmt = QTextCharFormat(base_fmt)
        add_fmt.setBackground(QColor('#1a3a1a'))
        add_fmt.setForeground(QColor('#6db86d'))

        rem_fmt = QTextCharFormat(base_fmt)
        rem_fmt.setBackground(QColor('#3a1a1a'))
        rem_fmt.setForeground(QColor('#b86d6d'))

        neu_fmt = QTextCharFormat(base_fmt)
        neu_fmt.setForeground(QColor('#888888'))

        for line in diff:
            tag = line[:2]
            text = line[2:]

            if tag == '+ ':
                fmt = add_fmt
                prefix = '+ '
            elif tag == '- ':
                fmt = rem_fmt
                prefix = '− '
            elif tag == '  ':
                fmt = neu_fmt
                prefix = '  '
            else:
                continue   # skip '? ' hint lines

            cursor.insertText(prefix + text, fmt)

        self._diff_view.setTextCursor(cursor)
        doc.verticalScrollBar().setValue(0)

    def _on_restore(self):
        if self._selected_version:
            self.restore_requested.emit(self._selected_version['content'])
            self.close_requested.emit()
