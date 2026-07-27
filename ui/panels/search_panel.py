"""
Global Full-Text Search Panel
Searches all note content across every topic with live results,
section filtering, and matched snippet highlighting.
"""
from __future__ import annotations

import re
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel,
    QScrollArea, QComboBox, QPushButton, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QTimer, QSize
from PySide6.QtGui import QIcon, QColor


# ── Helpers ────────────────────────────────────────────────────────────────

def _strip_html(html: str) -> str:
    """Remove HTML tags and decode common entities."""
    text = re.sub(r'<[^>]+>', ' ', html or '')
    text = text.replace('&nbsp;', ' ').replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
    return re.sub(r'\s+', ' ', text).strip()


def _snippet(plain: str, query: str, context: int = 120) -> str:
    """Return a short excerpt around the first occurrence of query."""
    lower = plain.lower()
    idx = lower.find(query.lower())
    if idx == -1:
        return plain[:context * 2]
    start = max(0, idx - context // 2)
    end = min(len(plain), idx + len(query) + context // 2)
    excerpt = plain[start:end]
    if start > 0:
        excerpt = '…' + excerpt
    if end < len(plain):
        excerpt = excerpt + '…'
    return excerpt


def _highlight(text: str, query: str) -> str:
    """Wrap every case-insensitive match of query in an HTML <b> tag."""
    if not query:
        return text
    escaped_q = re.escape(query)
    return re.sub(f'({escaped_q})', r'<b style="color:#B48EAD">\1</b>', text, flags=re.IGNORECASE)


# ── Result Card ────────────────────────────────────────────────────────────

class _ResultCard(QFrame):
    clicked = Signal(int, str)   # (topic_id, section_type)

    _SECTION_COLORS = {
        'NOTES':      '#4C8BB5',
        'QUESTIONS':  '#B5844C',
        'RESOURCES':  '#4CB57A',
        'SUB TOPICS': '#4CB5B5'
    }

    def __init__(self, topic_id: int, topic_name: str, section: str, snippet: str, query: str, parent=None):
        super().__init__(parent)
        self._topic_id = topic_id
        self._section = section
        self.setCursor(Qt.PointingHandCursor)
        self.setObjectName('resultCard')
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("""
            QFrame#resultCard {
                background: #1e1e1e;
                border-radius: 6px;
                border: 1px solid #2a2a2a;
            }
            QFrame#resultCard:hover {
                background: #252525;
                border-color: #3a3a3a;
            }
        """)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(5)

        # Header row: topic name + section badge
        header = QHBoxLayout()
        header.setSpacing(8)

        name_lbl = QLabel(topic_name)
        name_lbl.setStyleSheet('color: #e0e0e0; font-size: 13px; font-weight: bold; border: none;')
        name_lbl.setWordWrap(False)
        name_lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        section_color = self._SECTION_COLORS.get(section, '#555')
        badge = QLabel(section.title())
        badge.setStyleSheet(
            f'color: {section_color}; font-size: 10px; font-weight: bold;'
            f' border: 1px solid {section_color}; border-radius: 3px; padding: 1px 5px;'
        )

        header.addWidget(name_lbl)
        header.addStretch()
        header.addWidget(badge)
        layout.addLayout(header)

        # Snippet
        highlighted = _highlight(_snippet(snippet, query), query)
        snippet_lbl = QLabel(highlighted)
        snippet_lbl.setTextFormat(Qt.RichText)
        snippet_lbl.setWordWrap(True)
        snippet_lbl.setStyleSheet('color: #888; font-size: 11px; border: none; line-height: 1.4;')
        layout.addWidget(snippet_lbl)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self._topic_id, self._section)
        super().mousePressEvent(event)


# ── Search Overlay ─────────────────────────────────────────────────────────

class SearchOverlay(QFrame):
    """
    Floating VS Code-style search overlay.
    Emits topic_selected(topic_id, section_type) when a result is clicked.
    """
    topic_selected = Signal(int, str)

    _SECTIONS = ['All Sections', 'NOTES', 'QUESTIONS', 'RESOURCES', 'SUB TOPICS']

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('searchOverlay')
        self.setStyleSheet("""
            QFrame#searchOverlay {
                background: #1e1e1e;
                border: 1px solid #3a3a3a;
                border-radius: 8px;
            }
        """)
        
        from PySide6.QtGui import QShortcut, QKeySequence
        QShortcut(QKeySequence("Esc"), self, self.hide)

        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(300)
        self._debounce.timeout.connect(self._run_search)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.setSizeConstraint(QVBoxLayout.SetFixedSize)

        # ── Input Row ──
        input_container = QWidget()
        input_container.setStyleSheet('background: #252526; border-top-left-radius: 8px; border-top-right-radius: 8px;')
        ic_layout = QHBoxLayout(input_container)
        ic_layout.setContentsMargins(10, 10, 10, 10)
        ic_layout.setSpacing(6)

        self._query_edit = QLineEdit()
        self._query_edit.setPlaceholderText('Find in notes...')
        self._query_edit.setFixedHeight(26)
        self._query_edit.setStyleSheet("""
            QLineEdit {
                background: #3c3c3c;
                border: 1px solid #3c3c3c;
                border-radius: 4px;
                padding: 0 8px;
                color: #cccccc;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #007fd4;
            }
        """)
        self._query_edit.textChanged.connect(self._on_text_changed)

        # Section filter
        self._section_combo = QComboBox()
        for s in self._SECTIONS:
            self._section_combo.addItem(s)
        self._section_combo.setFixedHeight(26)
        self._section_combo.setFixedWidth(100)
        self._section_combo.setStyleSheet("""
            QComboBox {
                background: #3c3c3c;
                border: 1px solid #3c3c3c;
                border-radius: 4px;
                padding: 0 8px;
                color: #cccccc;
                font-size: 11px;
            }
            QComboBox::drop-down { border: none; width: 16px; }
            QComboBox QAbstractItemView {
                background: #252526;
                border: 1px solid #3c3c3c;
                color: #cccccc;
                selection-background-color: #04395e;
            }
        """)
        self._section_combo.currentIndexChanged.connect(lambda _: self._run_search())

        close_btn = QPushButton('✕')
        close_btn.setFixedSize(26, 26)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton { border: none; background: transparent; color: #cccccc; font-size: 13px; border-radius: 4px; }
            QPushButton:hover { background: #4d4d4d; color: white; }
        """)
        close_btn.clicked.connect(self.hide)

        ic_layout.addWidget(self._query_edit, stretch=1)
        ic_layout.addWidget(self._section_combo)
        ic_layout.addWidget(close_btn)
        
        layout.addWidget(input_container)

        # ── Result count label ──
        self._count_lbl = QLabel('')
        self._count_lbl.setStyleSheet('color: #888; font-size: 10px; padding: 0 12px 6px 12px; background: #252526; border-bottom-left-radius: 8px; border-bottom-right-radius: 8px;')
        self._count_lbl.hide()
        layout.addWidget(self._count_lbl)

        # ── Results scroll area ──
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QScrollArea.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet('background: #1e1e1e; border-bottom-left-radius: 8px; border-bottom-right-radius: 8px;')
        self._scroll.setMaximumHeight(350)
        self._scroll.hide()

        self._results_container = QWidget()
        self._results_container.setStyleSheet('background: transparent;')
        self._results_layout = QVBoxLayout(self._results_container)
        self._results_layout.setContentsMargins(8, 8, 8, 8)
        self._results_layout.setSpacing(6)
        self._results_layout.addStretch()

        self._scroll.setWidget(self._results_container)
        layout.addWidget(self._scroll)

    # ── Slots ──────────────────────────────────────────────────────────────

    def _on_text_changed(self, text: str):
        self._debounce.stop()
        if len(text.strip()) >= 2:
            self._debounce.start()
        else:
            self._clear_results()
            self._count_lbl.setText('')

    def _run_search(self):
        query = self._query_edit.text().strip()
        if len(query) < 2:
            self._clear_results()
            return

        section_filter = self._section_combo.currentText()

        from core.database import get_session
        from core.models import Note, Topic
        from sqlalchemy import or_

        session = get_session()
        try:
            q = session.query(Note, Topic).join(
                Topic, Note.topic_id == Topic.id
            ).filter(
                Topic.is_deleted == False,
                Note.topic_id != None,
            )
            if section_filter != 'All Sections':
                q = q.filter(Note.section_type == section_filter)

            rows = q.all()
        finally:
            session.close()

        # Filter in Python (LIKE is unreliable on HTML content; strip first)
        results = []
        ql = query.lower()
        for note, topic in rows:
            plain = _strip_html(note.content)
            if ql in plain.lower():
                results.append((topic.id, topic.name, note.section_type, plain))

        self._clear_results()
        self._count_lbl.setText(f'{len(results)} result{"s" if len(results) != 1 else ""} for "{query}"' if results else f'No results for "{query}"')
        self._count_lbl.show()
        
        if results:
            self._scroll.show()
            # Remove border radius from input container and count label when scroll is active
            self._count_lbl.setStyleSheet('color: #888; font-size: 10px; padding: 0 12px 6px 12px; background: #252526; border-radius: 0;')
        else:
            self._scroll.hide()
            self._count_lbl.setStyleSheet('color: #888; font-size: 10px; padding: 0 12px 6px 12px; background: #252526; border-bottom-left-radius: 8px; border-bottom-right-radius: 8px;')

        for topic_id, topic_name, section, plain in results[:100]:
            card = _ResultCard(topic_id, topic_name, section, plain, query)
            card.clicked.connect(self.topic_selected.emit)
            self._results_layout.insertWidget(self._results_layout.count() - 1, card)

    def _clear_results(self):
        while self._results_layout.count() > 1:
            item = self._results_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._scroll.hide()
        self._count_lbl.hide()

    def focus_search(self):
        """Called when the panel becomes visible to auto-focus the input."""
        self._query_edit.setFocus()
        self._query_edit.selectAll()
