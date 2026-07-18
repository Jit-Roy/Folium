import sys
from PySide6.QtWidgets import QApplication, QScrollArea, QTabBar, QWidget, QVBoxLayout
from PySide6.QtCore import Qt

app = QApplication(sys.argv)
win = QWidget()
win.resize(600, 200)
layout = QVBoxLayout(win)

scroll = QScrollArea()
scroll.setFixedHeight(50)
scroll.setWidgetResizable(True)
scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

bar = QTabBar()
bar.setUsesScrollButtons(False)
bar.setExpanding(False)
for i in range(3):
    bar.addTab(f"Tab {i}")

scroll.setWidget(bar)
layout.addWidget(scroll)

def check_max():
    print("Maximum:", scroll.horizontalScrollBar().maximum())
    print("TabBar width:", bar.width())
    print("Viewport width:", scroll.viewport().width())
    print("TabBar sizeHint:", bar.sizeHint())
    print("TabBar minSizeHint:", bar.minimumSizeHint())

from PySide6.QtCore import QTimer
QTimer.singleShot(1000, check_max)

win.show()
sys.exit(app.exec())
