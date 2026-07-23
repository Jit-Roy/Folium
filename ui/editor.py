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
from ui.section_menu import SectionMenu

class NoteEditor(QWidget):
    toggle_reference_viewer = Signal()  # emitted when panel-right button is clicked
    tags_updated = Signal() # emitted when a tag is added
    
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

    def set_read_only(self, readonly: bool):
        self.editor.setReadOnly(readonly)
        for btn in self.format_btns.values():
            btn.setVisible(not readonly)
        self.add_tag_btn.setVisible(not readonly)
        if hasattr(self, 'title_label'):
            # You might want to let them know it's locked by appending to title? No, just keep it simple.
            pass

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Formatting Toolbar
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(90, 15, 8, 15)
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
        
        self.panel_right_btn = QPushButton()
        self.panel_right_btn.setIcon(QIcon("assets/icons/panel-right.svg"))
        self.panel_right_btn.setFixedSize(28, 28)
        self.panel_right_btn.setToolTip("Toggle Reference Viewer")
        self.panel_right_btn.setCheckable(True)
        self.panel_right_btn.setChecked(True)  # panel starts open
        self.panel_right_btn.setStyleSheet("""
            QPushButton { border: none; background: transparent; color: #888888; }
            QPushButton:hover { background: #242424; border-radius: 4px; }
            QPushButton:checked { background: #2D2036; border-radius: 4px; color: #B48EAD; }
        """)
        self.panel_right_btn.clicked.connect(self.toggle_reference_viewer.emit)
        toolbar.addWidget(self.panel_right_btn)
        
        layout.addLayout(toolbar)

        # Lower Area (Horizontal Splitter)
        lower_layout = QHBoxLayout()
        lower_layout.setContentsMargins(0, 0, 0, 0)
        lower_layout.setSpacing(0)
        
        self.section_menu = SectionMenu()
        self.section_menu.section_selected.connect(self._on_section_selected)
        lower_layout.addWidget(self.section_menu)

        # Content Area
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(40, 20, 40, 0)
        
        self.title_label = QLabel("Select a topic")
        self.title_label.setStyleSheet("font-size: 28px; font-weight: bold; color: #FFFFFF; border: none; padding-bottom: 10px;")
        content_layout.addWidget(self.title_label)
        
        # Tags area
        self.tags_layout = QHBoxLayout()
        
        self.add_tag_btn = QPushButton("Add tag")
        self.add_tag_btn.setStyleSheet("border: none; background: transparent; color: #888888; font-size: 11px;")
        
        from ui.widgets.floating_widgets import FloatingInput
        self.tag_input = FloatingInput(placeholder="Enter tag name...")
        self.tag_input.submitted.connect(self.on_tag_submitted)
        self.add_tag_btn.clicked.connect(self.show_tag_input)
        
        self.tags_layout.addWidget(self.add_tag_btn)
        self.tags_layout.addStretch()
        content_layout.addLayout(self.tags_layout)
        
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
        lower_layout.addLayout(content_layout)
        layout.addLayout(lower_layout)
        
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

    def show_tag_input(self):
        if not self.current_topic_id:
            return
        rect = self.add_tag_btn.geometry()
        pos = self.add_tag_btn.parentWidget().mapToGlobal(rect.bottomLeft())
        self.tag_input.show_at(pos)

    def on_tag_submitted(self, text):
        if not self.current_topic_id:
            return
            
        tag_name = text.strip().lower()
        if tag_name.startswith("#"):
            tag_name = tag_name[1:]
            
        from core.database import get_session
        from core.models import Topic, Tag
        
        session = get_session()
        topic = session.query(Topic).get(self.current_topic_id)
        if topic:
            tag = session.query(Tag).filter_by(name=tag_name).first()
            if not tag:
                tag = Tag(name=tag_name)
                session.add(tag)
            
            if tag not in topic.tags:
                topic.tags.append(tag)
                session.commit()
                self._add_tag_bubble(tag.name)
                self.tags_updated.emit()
                
        session.close()

    def _add_tag_bubble(self, tag_name):
        from PySide6.QtWidgets import QFrame
        from PySide6.QtCore import Qt, QSize
        from PySide6.QtGui import QIcon
        
        container = QFrame()
        container.setObjectName("tagBubble")
        container.setStyleSheet("""
            QFrame#tagBubble {
                background-color: #2D2036; 
                border-radius: 12px;
                border: 1px solid #4D305A;
            }
        """)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(10, 4, 8, 4)
        layout.setSpacing(6)
        
        lbl = QLabel(f"#{tag_name}")
        lbl.setStyleSheet("color: #B48EAD; font-size: 11px; border: none; background: transparent; padding: 0px;")
        
        close_btn = QPushButton()
        close_btn.setIcon(QIcon("assets/icons/x.svg"))
        close_btn.setIconSize(QSize(12, 12))
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setFixedSize(16, 16)
        close_btn.setStyleSheet("""
            QPushButton {
                border: none; 
                background: transparent;
                border-radius: 8px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.1);
            }
        """)
        close_btn.clicked.connect(lambda: self.remove_tag(tag_name, container))
        
        layout.addWidget(lbl)
        layout.addWidget(close_btn)
        
        idx = self.tags_layout.count() - 2
        if idx < 0:
            idx = 0
        self.tags_layout.insertWidget(idx, container)

    def remove_tag(self, tag_name, widget):
        if not self.current_topic_id:
            return
            
        from core.database import get_session
        from core.models import Topic, Tag
        
        session = get_session()
        topic = session.query(Topic).get(self.current_topic_id)
        if topic:
            tag = session.query(Tag).filter_by(name=tag_name).first()
            if tag and tag in topic.tags:
                topic.tags.remove(tag)
                session.commit()
                widget.deleteLater()
                self.tags_updated.emit()
                
        session.close()

    def _on_section_selected(self, section_name):
        if self.current_section == section_name:
            return
            
        # Save current note before switching
        if self.save_timer.isActive():
            self.save_timer.stop()
            self.save_note()
            
        class _T:
            def __init__(self, tid, name):
                self.id = tid
                self.name = name
                self.children = []
                self.children_count = 0
                
        # Load the new section
        t = _T(self.current_topic_id, self.title_label.text()) if self.current_topic_id else None
        self.load_topic(t, section_name)

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
            if font.family() != "Courier New":
                font.setFamily("Courier New")
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
            block_format = cursor.blockFormat()
            
            if not is_active:
                header_char_format.setFontPointSize(11)
                header_char_format.setFontWeight(QFont.Normal)
                block_format.setHeadingLevel(0)
            else:
                if format_type == "h1":
                    header_char_format.setFontPointSize(24)
                    header_char_format.setFontWeight(QFont.Normal)
                    block_format.setHeadingLevel(1)
                elif format_type == "h2":
                    header_char_format.setFontPointSize(20)
                    header_char_format.setFontWeight(QFont.Normal)
                    block_format.setHeadingLevel(2)
                elif format_type == "h3":
                    header_char_format.setFontPointSize(16)
                    header_char_format.setFontWeight(QFont.Normal)
                    block_format.setHeadingLevel(3)
                
            pos = cursor.position()
            cursor.select(QTextCursor.BlockUnderCursor)
            cursor.mergeCharFormat(header_char_format)
            cursor.setBlockFormat(block_format)
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
            cf = cursor.charFormat()
            font = cf.font()
            font.setFamily("Segoe UI Symbol")
            cf.setFont(font)
            cursor.setCharFormat(cf)
            cursor.insertText("☐ ")
            # Reset back
            font.setFamily("Segoe UI")
            cf.setFont(font)
            cursor.setCharFormat(cf)
            
        elif format_type == "image":
            file_name, _ = QFileDialog.getOpenFileName(self, "Insert Image", "", "Images (*.png *.jpg *.jpeg *.gif *.svg)")
            if file_name:
                import os
                import uuid
                import shutil
                
                # Create uploads directory
                uploads_dir = os.path.join("assets", "uploads")
                os.makedirs(uploads_dir, exist_ok=True)
                
                # Generate a unique secure filename and copy it over
                ext = os.path.splitext(file_name)[1]
                unique_filename = f"{uuid.uuid4().hex}{ext}"
                dest_path = os.path.join(uploads_dir, unique_filename)
                shutil.copy2(file_name, dest_path)
                
                abs_dest = os.path.abspath(dest_path).replace(chr(92), '/')
                url = f"file:///{abs_dest}"
                
                from PySide6.QtGui import QImage
                img = QImage(abs_dest)
                w = img.width()
                h = img.height()
                
                max_w = self.editor.viewport().width() - 40
                if w > max_w:
                    h = int(h * (max_w / w))
                    w = max_w
                
                img_format = QTextImageFormat()
                img_format.setName(url)
                img_format.setWidth(w)
                img_format.setHeight(h)
                
                cursor.insertImage(img_format)
                cursor.insertText("\n")
                self.editor.setTextCursor(cursor)
                
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
            self._clear_tags()
            self.editor.clear()
            self.editor.setEnabled(False)
            self.section_menu.load_topic_sections(None)
            return
            
        self.section_menu.load_topic_sections(topic, section)
        self.title_label.setText(topic.name if hasattr(topic, 'name') else "Topic")
        
        self._clear_tags()
        if hasattr(topic, 'id'):
            from core.database import get_session
            from core.models import Topic
            session = get_session()
            db_topic = session.query(Topic).get(topic.id)
            if db_topic:
                for t in db_topic.tags:
                    self._add_tag_bubble(t.name)
            session.close()
        
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
            # Strip legacy max-width to prevent ghost sizing bugs
            content = content.replace('style="max-width: 100%;"', '')
            self.editor.setHtml(content)
        else:
            self.editor.setPlainText(content if content else "")
            
        self.editor.setEnabled(True)
        self.editor.blockSignals(False)
        
        self.on_text_changed()
        self.status_label.setText("Loaded")

    def export_markdown(self):
        from PySide6.QtWidgets import QFileDialog
        if not self.current_topic_id:
            return
            
        # Clean title for filename
        clean_title = "".join(c for c in self.title_label.text() if c.isalnum() or c in " -_").strip()
        default_name = f"{clean_title}.md"
        
        file_name, _ = QFileDialog.getSaveFileName(self, "Export to Markdown", default_name, "Markdown Files (*.md)")
        if file_name:
            html_content = self.editor.toHtml()
            try:
                import markdownify
                import re
                
                # Pre-process Qt's inline CSS spans into standard HTML tags for markdownify
                html_content = re.sub(r'(<span[^>]*?font-weight:\s*[6-9]\d{2}[^>]*?>)(.*?)(</span>)', r'\1<strong>\2</strong>\3', html_content)
                html_content = re.sub(r'(<span[^>]*?font-weight:\s*bold[^>]*?>)(.*?)(</span>)', r'\1<strong>\2</strong>\3', html_content)
                html_content = re.sub(r'(<span[^>]*?font-style:\s*italic[^>]*?>)(.*?)(</span>)', r'\1<em>\2</em>\3', html_content)
                
                # Convert old fake headings (font-size spans) into actual heading tags
                html_content = re.sub(r'<p[^>]*>(<span[^>]*?font-size:\s*24pt[^>]*?>)(.*?)(</span>)</p>', r'<h1>\2</h1>', html_content)
                html_content = re.sub(r'<p[^>]*>(<span[^>]*?font-size:\s*20pt[^>]*?>)(.*?)(</span>)</p>', r'<h2>\2</h2>', html_content)
                html_content = re.sub(r'<p[^>]*>(<span[^>]*?font-size:\s*16pt[^>]*?>)(.*?)(</span>)</p>', r'<h3>\2</h3>', html_content)
                
                md_content = markdownify.markdownify(html_content, heading_style="ATX", default_title=True)
            except ImportError:
                from PySide6.QtGui import QTextDocument
                import re
                
                md_content = self.editor.document().toMarkdown(QTextDocument.MarkdownDialectGitHub)
                
                # Qt's toMarkdown often leaves spaces inside bold/italic tags, breaking them.
                md_content = re.sub(r'\*\*(.*?)\s+\*\*', r'**\1** ', md_content)
                md_content = re.sub(r'(?<!\*)\*(?!\*)(.*?)\s+\*', r'*\1* ', md_content)
                md_content = re.sub(r'_(.*?)\s+_', r'_\1_ ', md_content)

            with open(file_name, "w", encoding="utf-8") as f:
                f.write(md_content)
            self.status_label.setText("Exported successfully")

    def export_html(self):
        from PySide6.QtWidgets import QFileDialog
        if not self.current_topic_id:
            return
            
        clean_title = "".join(c for c in self.title_label.text() if c.isalnum() or c in " -_").strip()
        default_name = f"{clean_title}.html"
        
        file_name, _ = QFileDialog.getSaveFileName(self, "Export to HTML", default_name, "HTML Files (*.html)")
        if file_name:
            html_content = self.editor.toHtml()
            with open(file_name, "w", encoding="utf-8") as f:
                f.write(html_content)
            self.status_label.setText("Exported HTML successfully")

    def _clear_tags(self):
        # Remove all widgets from tags_layout except the add button and stretch
        while self.tags_layout.count() > 2:
            item = self.tags_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
