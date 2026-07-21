from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QStackedWidget,
    QPushButton, QSizePolicy, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon

from ui.panels.reference_viewer_panel import ReferenceViewerPanel
from ui.panels.outline_panel import OutlinePanel
from ui.panels.tasks_panel import TasksPanel


class KnowledgePanel(QWidget):
    """
    The collapsible right panel.
    Contains a tab-like header to switch between sub-panels:
      - REFERENCE  (full embedded browser)
      - OUTLINE    (future: heading navigator)
    """
    # Emitted when the panel wants to hide itself (close button)
    close_requested = Signal()
    # Emitted when the panel wants to maximize itself (hide the editor)
    maximize_requested = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(450)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Tab header ────────────────────────────────────────────────────────
        tab_bar = QFrame()
        tab_bar.setFixedHeight(38)
        tab_bar.setStyleSheet(
            "background: #181818;"
            "border-bottom: 1px solid #2a2a2a;"
        )
        tab_layout = QHBoxLayout(tab_bar)
        tab_layout.setContentsMargins(8, 0, 8, 0)
        tab_layout.setSpacing(0)

        self._tab_buttons: dict[str, QPushButton] = {}
        tab_defs = [
            ("REFERENCE", "monitor"),
            ("OUTLINE",   "list"),
            ("TASKS",     "check-square"),
        ]
        for name, icon in tab_defs:
            btn = QPushButton(name)
            btn.setCheckable(True)
            btn.setFixedHeight(38)
            btn.setStyleSheet(self._tab_style(False))
            btn.clicked.connect(lambda _, n=name: self._select_tab(n))
            tab_layout.addWidget(btn)
            self._tab_buttons[name] = btn

        tab_layout.addStretch()

        # Maximize button
        self.is_maximized = False
        self.maximize_btn = QPushButton()
        self.maximize_btn.setIcon(QIcon("assets/icons/maximize.svg"))
        self.maximize_btn.setFixedSize(26, 26)
        self.maximize_btn.setToolTip("Maximize panel")
        self.maximize_btn.setStyleSheet(
            "QPushButton { border: none; background: transparent; }"
            "QPushButton:hover { background: rgba(255,255,255,0.08); border-radius: 4px; }"
        )
        self.maximize_btn.clicked.connect(self._on_maximize_clicked)
        tab_layout.addWidget(self.maximize_btn)

        # Close button
        close_btn = QPushButton()
        close_btn.setIcon(QIcon("assets/icons/x.svg"))
        close_btn.setFixedSize(26, 26)
        close_btn.setToolTip("Hide panel")
        close_btn.setStyleSheet(
            "QPushButton { border: none; background: transparent; }"
            "QPushButton:hover { background: rgba(255,255,255,0.08); border-radius: 4px; }"
        )
        close_btn.clicked.connect(self.close_requested.emit)
        tab_layout.addWidget(close_btn)

        layout.addWidget(tab_bar)

        # ── Stacked content ────────────────────────────────────────────────────
        self.stack = QStackedWidget()
        layout.addWidget(self.stack, stretch=1)

        # Page 0 – Reference Viewer
        self.reference_panel = ReferenceViewerPanel()
        self.reference_panel.close_requested.connect(self.close_requested.emit)
        self.stack.addWidget(self.reference_panel)

        # Page 1 – Outline
        self.outline_panel = OutlinePanel()
        self.stack.addWidget(self.outline_panel)
        
        # Page 2 – Tasks
        self.tasks_panel = TasksPanel()
        self.stack.addWidget(self.tasks_panel)

        # Default tab
        self._select_tab("REFERENCE")

    def _on_maximize_clicked(self):
        self.is_maximized = not self.is_maximized
        if self.is_maximized:
            self.maximize_btn.setIcon(QIcon("assets/icons/minimize.svg"))
            self.maximize_btn.setToolTip("Restore panel")
        else:
            self.maximize_btn.setIcon(QIcon("assets/icons/maximize.svg"))
            self.maximize_btn.setToolTip("Maximize panel")
        self.maximize_requested.emit(self.is_maximized)

    # ── Tab logic ──────────────────────────────────────────────────────────────
    def _select_tab(self, name: str):
        tab_order = ["REFERENCE", "OUTLINE", "TASKS"]
        idx = tab_order.index(name) if name in tab_order else 0
        self.stack.setCurrentIndex(idx)
        for k, btn in self._tab_buttons.items():
            btn.setChecked(k == name)
            btn.setStyleSheet(self._tab_style(k == name))

    @staticmethod
    def _tab_style(active: bool) -> str:
        if active:
            return """
                QPushButton {
                    border: none;
                    background: transparent;
                    color: #B48EAD;
                    border-bottom: 2px solid #B48EAD;
                    border-radius: 0px;
                    font-size: 10px;
                    font-weight: bold;
                    letter-spacing: 1px;
                    padding: 0 14px;
                }
            """
        return """
            QPushButton {
                border: none;
                background: transparent;
                color: #555555;
                border-bottom: 2px solid transparent;
                font-size: 10px;
                font-weight: bold;
                letter-spacing: 1px;
                padding: 0 14px;
            }
            QPushButton:hover { color: #888888; }
        """

    # ── Public API ─────────────────────────────────────────────────────────────
    def save_state(self, settings):
        settings.beginGroup("knowledge_panel")
        
        # Save active tab name
        active_tab = "REFERENCE"
        for name, btn in self._tab_buttons.items():
            if btn.isChecked():
                active_tab = name
                break
        settings.setValue("active_tab", active_tab)
        
        # Save visibility of the panel
        settings.setValue("is_visible", self.isVisible())
        
        settings.endGroup()
        
        # Delegate to children
        self.reference_panel.save_state(settings)
        
    def restore_state(self, settings):
        settings.beginGroup("knowledge_panel")
        
        active_tab = settings.value("active_tab", "REFERENCE")
        self._select_tab(active_tab)
        
        # is_visible determines whether we start expanded or collapsed
        is_visible = settings.value("is_visible", True, type=bool)
        if not is_visible:
            self.hide()
        
        settings.endGroup()
        
        # Delegate to children
        self.reference_panel.restore_state(settings)

    def load_references(self, topic):
        pass
        
    def set_active_editor(self, editor):
        self.outline_panel.set_active_editor(editor)
        
    def set_current_topic(self, topic_id: int):
        self.tasks_panel.set_current_topic(topic_id)
