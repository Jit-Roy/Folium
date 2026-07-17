MAIN_QSS = """
QMainWindow {
    background-color: #121212;
    color: #E0E0E0;
}
QWidget {
    background-color: #121212;
    color: #E0E0E0;
    font-family: "Inter", "Segoe UI", sans-serif;
    font-size: 14px;
}
QSplitter::handle {
    background-color: #2D2D2D;
    width: 1px;
}
QTreeView {
    background-color: #121212;
    border: none;
    outline: none;
    padding: 10px;
}
QTreeView::item {
    padding: 5px;
    border-radius: 4px;
}
QTreeView::item:hover {
    background-color: #1E1E1E;
}
QTreeView::item:selected {
    background-color: #2D2D2D;
    color: #FFFFFF;
}
QTextEdit, QPlainTextEdit {
    background-color: #121212;
    color: #E0E0E0;
    border: none;
    padding: 40px;
    font-size: 16px;
    line-height: 1.6;
}
QLineEdit {
    background-color: #1E1E1E;
    border: 1px solid #2D2D2D;
    border-radius: 6px;
    padding: 6px 10px;
    color: #FFFFFF;
}
QPushButton {
    background-color: #1E1E1E;
    color: #E0E0E0;
    border: 1px solid #2D2D2D;
    border-radius: 6px;
    padding: 6px 12px;
}
QPushButton:hover {
    background-color: #2D2D2D;
}
QLabel {
    color: #AAAAAA;
}
QScrollBar:vertical {
    background: #121212;
    width: 8px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #333333;
    min-height: 20px;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    background: #555555;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""
