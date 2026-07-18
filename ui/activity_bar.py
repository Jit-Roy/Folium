from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon


# (icon_file, panel_key, tooltip)
_PANELS = [
    ("act-notes.svg",  "notes", "Explorer"),
    ("act-daily.svg",  "daily", "Daily Notes"),
    ("act-tags.svg",   "tags",  "Tags"),
    ("act-trash.svg",  "trash", "Trash"),
]

# Active button: prominent left border + subtle purple fill
_ACTIVE_STYLE = """
    QPushButton {
        border: none;
        background: rgba(180, 142, 173, 0.14);
        border-left: 2px solid #B48EAD;
        border-radius: 0px;
        padding: 0px;
        opacity: 1;
    }
"""

# Inactive button: dimmed icon, hover brightens
_INACTIVE_STYLE = """
    QPushButton {
        border: none;
        background: transparent;
        border-left: 2px solid transparent;
        border-radius: 0px;
        padding: 0px;
        opacity: 0.55;
    }
    QPushButton:hover {
        background: rgba(255,255,255,0.08);
        opacity: 0.85;
    }
"""

_SETTINGS_STYLE = """
    QPushButton {
        border: none;
        background: transparent;
        border-radius: 0px;
        padding: 0px;
    }
    QPushButton:hover {
        background: rgba(255,255,255,0.08);
    }
"""


class ActivityBar(QWidget):
    """
    Slim 48-px icon bar on the far left — Obsidian / VS Code style.
    Emits `panel_requested(key)` when an icon is clicked.
    Clicking the already-active icon toggles the side panel visibility.
    """
    panel_requested = Signal(str)   # "notes" | "daily" | "tags" | "trash"
    toggle_panel    = Signal()      # emitted when active icon clicked again

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(48)
        self._active: str | None = None
        self.buttons: dict[str, QPushButton] = {}
        self._init_ui()

    def _init_ui(self):
        self.setStyleSheet(
            "background-color: #181818;"
            "border-right: 1px solid #2a2a2a;"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 12, 0, 8)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignTop)

        # ── Section icon buttons ───────────────────────────────────────────
        for icon_file, key, tip in _PANELS:
            btn = QPushButton()
            btn.setIcon(QIcon(f"assets/icons/{icon_file}"))
            btn.setIconSize(QSize(24, 24))
            btn.setFixedSize(48, 48)
            btn.setToolTip(tip)
            btn.setCheckable(True)
            btn.setStyleSheet(_INACTIVE_STYLE)
            btn.clicked.connect(lambda _, k=key: self._on_click(k))
            layout.addWidget(btn)
            self.buttons[key] = btn

        layout.addStretch()

        # ── Settings button anchored at bottom ─────────────────────────────
        self.settings_btn = QPushButton()
        self.settings_btn.setIcon(QIcon("assets/icons/act-settings.svg"))
        self.settings_btn.setIconSize(QSize(22, 22))
        self.settings_btn.setFixedSize(48, 48)
        self.settings_btn.setToolTip("Settings")
        self.settings_btn.setStyleSheet(_SETTINGS_STYLE)
        layout.addWidget(self.settings_btn)

        # Default: activate Notes (no signal)
        self.set_active("notes", emit=False)

    def set_active(self, key: str, emit: bool = True):
        """Programmatically activate a panel button."""
        for k, btn in self.buttons.items():
            is_active = k == key
            btn.setChecked(is_active)
            btn.setStyleSheet(_ACTIVE_STYLE if is_active else _INACTIVE_STYLE)
        self._active = key
        if emit:
            self.panel_requested.emit(key)

    def _on_click(self, key: str):
        if self._active == key:
            self.toggle_panel.emit()
        else:
            self.set_active(key)
