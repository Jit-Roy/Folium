MAIN_QSS = """
QMainWindow {
    background-color: #121212;
    color: #E0E0E0;
}
* {
    outline: none;
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
    background-color: transparent;
    border: none;
    outline: none;
    padding: 4px 0;
}
QTreeView::item {
    padding: 4px;
}
QTreeView::item:hover {
    background-color: rgba(255,255,255,0.07);
}
QTreeView::item:selected {
    background-color: #37373d;
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
    width: 6px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #333333;
    min-height: 20px;
    border-radius: 3px;
}
QScrollBar::handle:vertical:hover {
    background: #555555;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QScrollBar:horizontal {
    background: #121212;
    height: 6px;
    margin: 0;
}
QScrollBar::handle:horizontal {
    background: #333333;
    min-width: 20px;
    border-radius: 3px;
}
QScrollBar::handle:horizontal:hover {
    background: #555555;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}
QToolTip {
    background: #252526;
    color: #cccccc;
    border: 1px solid #454545;
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 12px;
}
"""
