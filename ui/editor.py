from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, 
    QTextEdit, QLabel, QPushButton, QFrame, QFileDialog, QLineEdit, QGridLayout
)
from PySide6.QtGui import (
    QIcon, QTextCursor, QTextCharFormat, QFont, 
    QTextBlockFormat, QTextListFormat, QTextImageFormat, QColor, QTextFormat
)
from PySide6.QtCore import QTimer, Qt, Signal
from functools import partial
import os

from ui.widgets.floating_widgets import FloatingInput, FloatingTableGrid
from ui.widgets.rich_text_editor import RichTextEditor

class NoteEditor(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_topic_id = None
        self.current_section = "NOTES"
        self.init_ui()
        
        self.save_timer = QTimer(self)
        self.save_timer.setSingleShot(True)
        self.save_timer.timeout.connect(self.save_note)
        
        self.editor.textChanged.connect(self.on_text_changed)
        self.editor.cursorPositionChanged.connect(self.update_toolbar_state)
        
        # Inline Widgets
        self.link_input = FloatingInput(self, "Paste URL here...")
        self.link_input.submitted.connect(self.insert_link)
        
        self.math_input = FloatingInput(self, "Type Math/Equation...")
        self.math_input.submitted.connect(self.insert_math)
        
        self.table_grid = FloatingTableGrid(self)
        self.table_grid.submitted.connect(self.insert_custom_table)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Formatting Toolbar
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(30, 15, 30, 15)
        toolbar.setSpacing(15)
        
        self.format_btns = {}
        format_icons = ["h1", "h2", "h3", "list", "check-square", "bold", "italic", "underline", "code", "table", "image", "link", "sigma", "fx"]
        tooltips = {
            "h1": "Heading 1", "h2": "Heading 2", "h3": "Heading 3", "list": "Bullet List",
            "check-square": "Checkbox", "bold": "Bold", "italic": "Italic", "underline": "Underline",
            "code": "Code", "table": "Insert Table", "image": "Insert Image", "link": "Insert Link",
            "sigma": "Math", "fx": "Equation"
        }
        
        for icon in format_icons:
            btn = QPushButton()
            btn.setIcon(QIcon(f"assets/icons/{icon}.svg"))
            btn.setFixedSize(28, 28)
            btn.setToolTip(tooltips.get(icon, icon))
            btn.setCheckable(True)
            btn.setStyleSheet("""
                QPushButton { border: none; background: transparent; color: #888888; font-weight: bold; }
                QPushButton:hover { background: #242424; border-radius: 4px; }
                QPushButton:checked { background: #2D2036; border-radius: 4px; }
            """)
            btn.clicked.connect(partial(self.apply_format, icon))
            toolbar.addWidget(btn)
            self.format_btns[icon] = btn
            
        toolbar.addStretch()
        more_btn = QPushButton()
        more_btn.setIcon(QIcon("assets/icons/more-horizontal.svg"))
        more_btn.setStyleSheet("border: none; background: transparent; color: #888888;")
        toolbar.addWidget(more_btn)
        
        layout.addLayout(toolbar)
        
        # Separator line
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #1E1E1E;")
        layout.addWidget(line)

        # Content Area
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(40, 20, 40, 0)
        
        self.title_label = QLabel("Select a topic")
        self.title_label.setStyleSheet("font-size: 28px; font-weight: bold; color: #FFFFFF; border: none; padding-bottom: 10px;")
        content_layout.addWidget(self.title_label)
        
        # Tags area
        tags_layout = QHBoxLayout()
        self.tag_bubble = QLabel("#tag")
        self.tag_bubble.setStyleSheet("""
            background-color: #2D2036; 
            color: #B48EAD; 
            padding: 4px 10px; 
            border-radius: 12px;
            font-size: 11px;
            border: 1px solid #4D305A;
        """)
        self.tag_bubble.hide()
        
        add_tag_btn = QPushButton("Add tag")
        add_tag_btn.setStyleSheet("border: none; background: transparent; color: #888888; font-size: 11px;")
        
        tags_layout.addWidget(self.tag_bubble)
        tags_layout.addWidget(add_tag_btn)
        tags_layout.addStretch()
        content_layout.addLayout(tags_layout)
        
        # Main Editor
        self.editor = RichTextEditor()
        self.editor.setPlaceholderText("Start writing here...")
        self.editor.setEnabled(False)
        self.editor.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.editor.setStyleSheet("""
            QTextEdit {
                background: transparent;
                color: #E0E0E0;
                border: none;
                padding-top: 20px;
            }
        """)
        
        # Set default font
        font = QFont("Segoe UI", 11)
        self.editor.setFont(font)
        
        content_layout.addWidget(self.editor)
        layout.addLayout(content_layout)
        
        # Status Bar
        status_layout = QHBoxLayout()
        status_layout.setContentsMargins(40, 10, 40, 10)
        
        self.status_label = QLabel("Saved")
        self.status_label.setStyleSheet("color: #666666; font-size: 11px; border: none;")
        
        self.words_label = QLabel("0 words")
        self.words_label.setStyleSheet("color: #666666; font-size: 11px; border: none;")
        
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        status_layout.addWidget(self.words_label)
        
        layout.addLayout(status_layout)

    def update_toolbar_state(self):
        cursor = self.editor.textCursor()
        if not cursor:
            return
            
        char_format = cursor.charFormat()
        
        self.format_btns["bold"].setChecked(char_format.fontWeight() == QFont.Bold)
        self.format_btns["italic"].setChecked(char_format.fontItalic())
        self.format_btns["underline"].setChecked(char_format.fontUnderline())
        self.format_btns["code"].setChecked(char_format.font().family() == "Consolas")
        
        pt_size = char_format.fontPointSize()
        self.format_btns["h1"].setChecked(pt_size == 24)
        self.format_btns["h2"].setChecked(pt_size == 20)
        self.format_btns["h3"].setChecked(pt_size == 16)
        
        # Prevent toggling of non-toggleable buttons
        for icon in ["list", "check-square", "table", "image", "link", "sigma", "fx"]:
            self.format_btns[icon].setChecked(False)

    def apply_format(self, format_type):
        cursor = self.editor.textCursor()
        if not cursor:
            return
            
        char_format = cursor.charFormat()
        
        if format_type == "bold":
            char_format.setFontWeight(QFont.Bold if char_format.fontWeight() != QFont.Bold else QFont.Normal)
            cursor.mergeCharFormat(char_format)
            
        elif format_type == "italic":
            char_format.setFontItalic(not char_format.fontItalic())
            cursor.mergeCharFormat(char_format)
            
        elif format_type == "underline":
            char_format.setFontUnderline(not char_format.fontUnderline())
            cursor.mergeCharFormat(char_format)
            
        elif format_type == "code":
            font = char_format.font()
            if font.family() != "Consolas":
                font.setFamily("Consolas")
                char_format.setFont(font)
                char_format.setBackground(QColor("#242424"))
                char_format.setForeground(QColor("#B48EAD"))
            else:
                font.setFamily("Segoe UI")
                char_format.setFont(font)
                char_format.clearProperty(QTextFormat.BackgroundBrush)
                char_format.clearProperty(QTextFormat.ForegroundBrush)
            cursor.mergeCharFormat(char_format)
            
        elif format_type in ["h1", "h2", "h3"]:
            # Make mutually exclusive
            for h in ["h1", "h2", "h3"]:
                if h != format_type:
                    self.format_btns[h].setChecked(False)
                    
            is_active = self.format_btns[format_type].isChecked()
            header_char_format = QTextCharFormat()
            
            if not is_active:
                header_char_format.setFontPointSize(11)
                header_char_format.setFontWeight(QFont.Normal)
            else:
                if format_type == "h1":
                    header_char_format.setFontPointSize(24)
                    header_char_format.setFontWeight(QFont.Bold)
                elif format_type == "h2":
                    header_char_format.setFontPointSize(20)
                    header_char_format.setFontWeight(QFont.Bold)
                elif format_type == "h3":
                    header_char_format.setFontPointSize(16)
                    header_char_format.setFontWeight(QFont.Bold)
                
            pos = cursor.position()
            cursor.select(QTextCursor.BlockUnderCursor)
            cursor.mergeCharFormat(header_char_format)
            cursor.setPosition(pos)
            
            self.editor.setTextCursor(cursor)
            self.editor.setCurrentCharFormat(header_char_format)
            self.editor.setFocus()
            return
            
        elif format_type == "list":
            list_format = QTextListFormat()
            list_format.setStyle(QTextListFormat.ListDisc)
            cursor.createList(list_format)
            
        elif format_type == "check-square":
            cursor.insertText("☐ ")
            
        elif format_type == "image":
            file_name, _ = QFileDialog.getOpenFileName(self, "Insert Image", "", "Images (*.png *.jpg *.jpeg *.gif *.svg)")
            if file_name:
                url = f"file:///{file_name.replace(chr(92), '/')}"
                self.editor.insertHtml(f'<img src="{url}" style="max-width: 100%;"><br>')
                
        elif format_type == "table":
            rect = self.format_btns["table"].geometry()
            pos = self.format_btns["table"].parentWidget().mapToGlobal(rect.bottomLeft())
            self.table_grid.show_at(pos)
            return
            
        elif format_type == "link":
            rect = self.format_btns["link"].geometry()
            pos = self.format_btns["link"].parentWidget().mapToGlobal(rect.bottomLeft())
            self.link_input.show_at(pos)
            return
            
        elif format_type in ["sigma", "fx"]:
            rect = self.format_btns[format_type].geometry()
            pos = self.format_btns[format_type].parentWidget().mapToGlobal(rect.bottomLeft())
            self.math_input.show_at(pos)
            return
            
        self.editor.setTextCursor(cursor)
        self.editor.setFocus()

    def insert_link(self, url):
        cursor = self.editor.textCursor()
        sel_text = cursor.selectedText()
        if not sel_text:
            sel_text = url
        self.editor.insertHtml(f'<a href="{url}" style="color: #88C0D0;">{sel_text}</a>')
        self.editor.setFocus()
        
    def insert_math(self, text):
        cursor = self.editor.textCursor()
        # Style it like an equation
        html = f'<span style="font-family: Consolas; color: #EBCB8B; background-color: #2D2036; padding: 2px 4px; border-radius: 4px;">{text}</span>&nbsp;'
        self.editor.insertHtml(html)
        self.editor.setFocus()
        
    def insert_custom_table(self, rows, cols):
        html = "<table border='1' cellpadding='8' cellspacing='0' style='border-collapse: collapse; border-color: #4D305A; background-color: #1E1E1E; width: 100%;'>"
        for r in range(rows):
            html += "<tr>"
            for c in range(cols):
                html += "<td>&nbsp;</td>"
            html += "</tr>"
        html += "</table><br>"
        self.editor.insertHtml(html)
        self.editor.setFocus()

    def on_text_changed(self):
        text = self.editor.toPlainText()
        words = len([w for w in text.split() if w.strip()])
        chars = len(text)
        self.words_label.setText(f"{words} words  |  {chars} characters")
        
        self.status_label.setText("Saving...")
        self.save_timer.start(1000)

    def save_note(self):
        if not self.current_topic_id:
            return
            
        from core.database import get_session
        from core.models import Note
        
        session = get_session()
        note = session.query(Note).filter_by(
            topic_id=self.current_topic_id, 
            section_type=self.current_section
        ).first()
        
        if not note:
            note = Note(topic_id=self.current_topic_id, section_type=self.current_section)
            session.add(note)
            
        note.content = self.editor.toHtml()
        session.commit()
        session.close()
        
        self.status_label.setText("Saved")

    def load_topic(self, topic, section="NOTES"):
        self.current_topic_id = topic.id if topic else None
        self.current_section = section
        
        if not topic:
            self.title_label.setText("Select a topic")
            self.tag_bubble.hide()
            self.editor.clear()
            self.editor.setEnabled(False)
            return
            
        self.title_label.setText(topic.name)
        self.tag_bubble.setText(f"#{topic.name.lower().replace(' ', '')}")
        self.tag_bubble.show()
        
        from core.database import get_session
        from core.models import Note
        
        session = get_session()
        note = session.query(Note).filter_by(
            topic_id=topic.id, 
            section_type=section
        ).first()
        content = note.content if note else ""
        session.close()
        
        self.editor.blockSignals(True)
        if content and ("<html" in content.lower() or "<body" in content.lower()):
            self.editor.setHtml(content)
        else:
            self.editor.setPlainText(content)
            
        self.editor.setEnabled(True)
        self.editor.blockSignals(False)
        
        self.on_text_changed()
        self.status_label.setText("Loaded")
