from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLineEdit, QGridLayout, QLabel, QPushButton
)
from PySide6.QtCore import Qt, Signal, QEvent

class FloatingInput(QWidget):
    submitted = Signal(str)
    
    def __init__(self, parent=None, placeholder="", numeric_only=False):
        super().__init__(parent)
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        self.setStyleSheet("""
            QWidget {
                background-color: #2D2036;
                border: 1px solid #4D305A;
                border-radius: 6px;
            }
            QLineEdit {
                background: transparent;
                color: #FFFFFF;
                border: none;
                padding: 8px;
                font-size: 13px;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        
        self.input = QLineEdit()
        self.input.setPlaceholderText(placeholder)
        self.input.returnPressed.connect(self.on_submit)
        
        if numeric_only:
            from PySide6.QtGui import QIntValidator
            self.input.setValidator(QIntValidator(10, 4000, self))
            
        layout.addWidget(self.input)
        self.setFixedWidth(250)
        
    def show_at(self, pos):
        self.move(pos)
        self.input.clear()
        self.show()
        self.input.setFocus()
        
    def on_submit(self):
        text = self.input.text()
        self.hide()
        if text.strip():
            self.submitted.emit(text)

class FloatingTableGrid(QWidget):
    submitted = Signal(int, int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        self.setStyleSheet("""
            QWidget { background-color: #2D2036; border: 1px solid #4D305A; border-radius: 6px; }
            QLabel { color: #FFFFFF; font-size: 11px; padding: 4px; border: none; }
            QPushButton { background: #1E1E1E; border: 1px solid #444444; }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        
        self.label = QLabel("Insert Table")
        layout.addWidget(self.label)
        
        grid_layout = QGridLayout()
        grid_layout.setSpacing(2)
        
        self.cells = []
        for r in range(6):
            row = []
            for c in range(6):
                btn = QPushButton()
                btn.setFixedSize(20, 20)
                btn.installEventFilter(self) 
                btn.clicked.connect(lambda checked=False, row=r, col=c: self.on_select(row, col))
                grid_layout.addWidget(btn, r, c)
                row.append(btn)
            self.cells.append(row)
            
        layout.addLayout(grid_layout)
        
    def show_at(self, pos):
        self.move(pos)
        self.show()
        
    def on_select(self, r, c):
        self.hide()
        self.submitted.emit(r + 1, c + 1)
        
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Enter:
            # Find the row and col of the hovered button
            for r in range(6):
                for c in range(6):
                    if self.cells[r][c] == obj:
                        self.highlight_grid(r, c)
                        return super().eventFilter(obj, event)
        return super().eventFilter(obj, event)
        
    def highlight_grid(self, max_r, max_c):
        self.label.setText(f"Insert Table ({max_r+1}x{max_c+1})")
        for r in range(6):
            for c in range(6):
                if r <= max_r and c <= max_c:
                    self.cells[r][c].setStyleSheet("background: #B48EAD; border: 1px solid #EBCB8B;")
                else:
                    self.cells[r][c].setStyleSheet("background: #1E1E1E; border: 1px solid #444444;")
