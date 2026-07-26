from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel, QPushButton, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QShortcut, QKeySequence

class FindReplaceWidget(QFrame):
    find_requested = Signal(str, bool)  # text, forward
    replace_requested = Signal(str, str)  # find_text, replace_text
    replace_all_requested = Signal(str, str) # find_text, replace_text
    closed = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('findReplaceWidget')
        self.setStyleSheet("""
            QFrame#findReplaceWidget {
                background: #252526;
                border: 1px solid #3c3c3c;
                border-radius: 4px;
            }
        """)
        self.setFixedWidth(350)
        self.init_ui()
        
        QShortcut(QKeySequence("Esc"), self, self.close_widget)
        
    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(4)
        main_layout.setSizeConstraint(QHBoxLayout.SetFixedSize)
        
        # --- Left Layout (Toggle) ---
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 0, 0)
        self.toggle_btn = QPushButton()
        self.toggle_btn.setIcon(QIcon("assets/icons/chevron-down.svg"))
        self.toggle_btn.setFixedSize(22, 22)
        self.toggle_btn.setToolTip("Toggle Replace")
        self.toggle_btn.setCursor(Qt.PointingHandCursor)
        self.toggle_btn.setStyleSheet("""
            QPushButton { border: none; background-color: transparent; border-radius: 3px; padding: 2px; }
            QPushButton:hover { background-color: #4d4d4d; }
        """)
        self.toggle_btn.clicked.connect(self._toggle_replace_mode)
        left_layout.addWidget(self.toggle_btn)
        left_layout.addStretch()
        main_layout.addLayout(left_layout)
        
        # --- Right Layout (Inputs) ---
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(4)
        
        # --- Top Row (Find) ---
        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(4)
        
        self.find_input = QLineEdit()
        self.find_input.setPlaceholderText("Find")
        self.find_input.setFixedHeight(24)
        self.find_input.setFixedWidth(180)
        self.find_input.setStyleSheet("""
            QLineEdit {
                background: #3c3c3c;
                border: 1px solid #3c3c3c;
                border-radius: 2px;
                padding: 0 4px;
                color: #cccccc;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 1px solid #007fd4;
            }
        """)
        self.find_input.textChanged.connect(self._on_find_text_changed)
        self.find_input.returnPressed.connect(self._on_find_next)
        top_layout.addWidget(self.find_input)
        
        self.count_label = QLabel("No results")
        self.count_label.setStyleSheet("color: #888; font-size: 11px; background-color: transparent;")
        self.count_label.setFixedWidth(55)
        top_layout.addWidget(self.count_label)
        
        def make_icon_btn(icon_name, tooltip=""):
            btn = QPushButton()
            btn.setIcon(QIcon(f"assets/icons/{icon_name}.svg"))
            btn.setFixedSize(22, 22)
            btn.setToolTip(tooltip)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton { 
                    border: none; 
                    background-color: transparent; 
                    border-radius: 3px; 
                    padding: 2px;
                }
                QPushButton:hover { 
                    background-color: #4d4d4d; 
                }
            """)
            return btn
            
        self.prev_btn = make_icon_btn("arrow-up", "Previous Match (Shift+Enter)")
        self.prev_btn.clicked.connect(self._on_find_prev)
        top_layout.addWidget(self.prev_btn)
        
        self.next_btn = make_icon_btn("arrow-down", "Next Match (Enter)")
        self.next_btn.clicked.connect(self._on_find_next)
        top_layout.addWidget(self.next_btn)
        
        self.close_btn = make_icon_btn("x", "Close (Esc)")
        self.close_btn.clicked.connect(self.close_widget)
        top_layout.addWidget(self.close_btn)
        
        right_layout.addLayout(top_layout)
        
        # --- Bottom Row (Replace) ---
        self.bottom_widget = QWidget()
        self.bottom_widget.setStyleSheet("background-color: transparent;")
        bottom_layout = QHBoxLayout(self.bottom_widget)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(4)
        
        self.replace_input = QLineEdit()
        self.replace_input.setPlaceholderText("Replace")
        self.replace_input.setFixedHeight(24)
        self.replace_input.setFixedWidth(180)
        self.replace_input.setStyleSheet(self.find_input.styleSheet())
        self.replace_input.returnPressed.connect(self._on_replace)
        bottom_layout.addWidget(self.replace_input)
        
        self.replace_btn = make_icon_btn("replace", "Replace (Enter)")
        self.replace_btn.clicked.connect(self._on_replace)
        bottom_layout.addWidget(self.replace_btn)
        
        self.replace_all_btn = make_icon_btn("replace-all", "Replace All")
        self.replace_all_btn.clicked.connect(self._on_replace_all)
        bottom_layout.addWidget(self.replace_all_btn)
        
        bottom_layout.addStretch()
        right_layout.addWidget(self.bottom_widget)
        
        main_layout.addLayout(right_layout)
        
        self._replace_mode = True
        
    def _toggle_replace_mode(self):
        self._replace_mode = not self._replace_mode
        self.bottom_widget.setVisible(self._replace_mode)
        if self._replace_mode:
            self.toggle_btn.setIcon(QIcon("assets/icons/chevron-down.svg"))
        else:
            self.toggle_btn.setIcon(QIcon("assets/icons/chevron-right.svg"))
        
    def set_match_count(self, current, total):
        if total == 0:
            self.count_label.setText("No results")
        else:
            self.count_label.setText(f"{current} of {total}")
            
    def _on_find_text_changed(self, text):
        self.find_requested.emit(text, True)
        
    def _on_find_next(self):
        self.find_requested.emit(self.find_input.text(), True)
        
    def _on_find_prev(self):
        self.find_requested.emit(self.find_input.text(), False)
        
    def _on_replace(self):
        self.replace_requested.emit(self.find_input.text(), self.replace_input.text())
        
    def _on_replace_all(self):
        self.replace_all_requested.emit(self.find_input.text(), self.replace_input.text())
        
    def close_widget(self):
        self.hide()
        self.closed.emit()
        
    def focus_find(self):
        self.find_input.setFocus()
        self.find_input.selectAll()
