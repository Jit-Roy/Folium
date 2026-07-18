from PySide6.QtWidgets import QWidget, QVBoxLayout, QStackedWidget
from PySide6.QtCore import Qt


_PANEL_ORDER = ["notes", "daily", "tags", "trash"]


class SidePanel(QWidget):
    """
    Collapsible side panel that wraps a QStackedWidget.
    Each 'page' corresponds to a panel key: notes | daily | tags | trash.
    """

    def __init__(self, panels: dict, parent=None):
        """
        panels: dict mapping key -> QWidget
            e.g. {"notes": NotesPanel(), "daily": DailyNotesPanel(), ...}
        """
        super().__init__(parent)
        self.setMinimumWidth(200)
        self.setMaximumWidth(380)
        self._is_visible = True

        self.setObjectName("sidePanel")
        self.setStyleSheet("#sidePanel { background-color: #1e1e1e; border-right: 1px solid #2a2a2a; }")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.stack = QStackedWidget()
        for key in _PANEL_ORDER:
            widget = panels.get(key, QWidget())
            self.stack.addWidget(widget)

        layout.addWidget(self.stack)

        # Store references for public access
        self.panels = panels
        self._current_key = "notes"

    # ── Public API ─────────────────────────────────────────────────────────

    def show_panel(self, key: str):
        """Switch visible panel to the given key and ensure the widget is shown."""
        if key in _PANEL_ORDER:
            self.stack.setCurrentIndex(_PANEL_ORDER.index(key))
            self._current_key = key
        self.setVisible(True)
        self._is_visible = True

    def toggle_visibility(self):
        """Toggle the entire side panel on/off."""
        self._is_visible = not self._is_visible
        self.setVisible(self._is_visible)

    def current_key(self) -> str:
        return self._current_key

    def panel(self, key: str):
        """Return the panel widget for the given key."""
        return self.panels.get(key)
