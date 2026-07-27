from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QStackedWidget,
    QWidget, QLabel, QPushButton, QComboBox, QCheckBox, QFrame,
    QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QIcon, QFont
import os
from ui.title_bar import CustomTitleBar

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.resize(700, 500)
        self.setModal(True)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        
        # We need a border around the dialog so it doesn't bleed into the dark background
        self.setStyleSheet("""
            QDialog {
                background-color: #141414;
                color: #FFFFFF;
                border: 1px solid #333333;
            }
            QListWidget {
                background-color: #1A1A1A;
                border: none;
                border-right: 1px solid #2A2A2A;
                padding: 10px 0px;
                outline: none;
            }
            QListWidget::item {
                padding: 10px 20px;
                color: #A0A0A0;
                font-size: 13px;
                border-radius: 4px;
                margin: 0px 8px;
            }
            QListWidget::item:hover {
                background-color: #2D2D2D;
                color: #FFFFFF;
            }
            QListWidget::item:selected {
                background-color: #332244;
                color: #B48EAD;
                font-weight: bold;
            }
            QLabel {
                color: #E0E0E0;
            }
            QLabel#header {
                font-size: 20px;
                font-weight: bold;
                color: #FFFFFF;
                margin-bottom: 20px;
            }
            QLabel#desc {
                color: #888888;
                font-size: 12px;
            }
            QComboBox {
                background-color: #1E1E1E;
                border: 1px solid #333333;
                border-radius: 4px;
                padding: 5px 10px;
                color: #FFFFFF;
                min-width: 150px;
            }
            QComboBox:hover {
                border-color: #555555;
            }
            QComboBox::drop-down {
                border: none;
            }
            QPushButton {
                background-color: #2D2D2D;
                color: #FFFFFF;
                border: 1px solid #404040;
                border-radius: 4px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #3D3D3D;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.title_bar = CustomTitleBar(self)
        self.title_bar.min_btn.hide()
        self.title_bar.max_btn.hide()
        main_layout.addWidget(self.title_bar)

        content_hbox = QHBoxLayout()
        content_hbox.setContentsMargins(0, 0, 0, 0)
        content_hbox.setSpacing(0)

        # ── Sidebar ──
        self.sidebar = QListWidget()
        self.sidebar.setFixedWidth(180)
        self.sidebar.addItem("Appearance")
        self.sidebar.addItem("Editor")
        self.sidebar.addItem("Data & Storage")
        self.sidebar.addItem("About")
        self.sidebar.currentRowChanged.connect(self._change_page)
        
        content_hbox.addWidget(self.sidebar)

        # ── Content Area ──
        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(30, 30, 30, 30)

        self.stack = QStackedWidget()
        self.stack.addWidget(self._create_appearance_page())
        self.stack.addWidget(self._create_editor_page())
        self.stack.addWidget(self._create_data_page())
        self.stack.addWidget(self._create_about_page())
        
        content_layout.addWidget(self.stack)
        
        content_hbox.addWidget(content_container)
        
        main_layout.addLayout(content_hbox)

        self.sidebar.setCurrentRow(0)
        self._load_settings()

    def _change_page(self, index):
        self.stack.setCurrentIndex(index)

    def _create_appearance_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignTop)

        title = QLabel("Appearance")
        title.setObjectName("header")
        layout.addWidget(title)

        # Theme
        theme_layout = QHBoxLayout()
        theme_label = QLabel("App Theme")
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark (Default)"])
        theme_layout.addWidget(theme_label)
        theme_layout.addStretch()
        theme_layout.addWidget(self.theme_combo)
        layout.addLayout(theme_layout)


        
        # Accent Color
        accent_layout = QHBoxLayout()
        accent_label = QLabel("Accent Color")
        self.accent_combo = QComboBox()
        self.accent_combo.addItems(["Purple (#B48EAD)"])
        accent_layout.addWidget(accent_label)
        accent_layout.addStretch()
        accent_layout.addWidget(self.accent_combo)
        
        layout.addSpacing(20)
        layout.addLayout(accent_layout)
        


        return page

    def _create_editor_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignTop)

        title = QLabel("Editor & Behavior")
        title.setObjectName("header")
        layout.addWidget(title)

        # Auto-save
        autosave_layout = QHBoxLayout()
        autosave_label = QLabel("Auto-Save Interval")
        self.autosave_combo = QComboBox()
        self.autosave_combo.addItems(["1 second", "5 seconds", "10 seconds", "Manual"])
        autosave_layout.addWidget(autosave_label)
        autosave_layout.addStretch()
        autosave_layout.addWidget(self.autosave_combo)
        layout.addLayout(autosave_layout)

        layout.addSpacing(15)

        return page

    def _create_data_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignTop)

        title = QLabel("Data & Storage")
        title.setObjectName("header")
        layout.addWidget(title)

        db_path = os.path.abspath("learning_notebook.db")
        
        path_label = QLabel("Database Location:")
        layout.addWidget(path_label)
        
        path_value = QLabel(db_path)
        path_value.setStyleSheet("color: #FFC933; font-family: Consolas;")
        layout.addWidget(path_value)
        
        layout.addStretch()

        return page

    def _create_about_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignTop)

        title = QLabel("About Zstudy")
        title.setObjectName("header")
        layout.addWidget(title)

        version = QLabel("Version 1.0.0")
        layout.addWidget(version)
        
        desc = QLabel("A sleek, modern productivity suite and note-taking environment.\nBuilt with Python, PySide6, and SQLAlchemy.")
        desc.setStyleSheet("line-height: 1.5; color: #CCCCCC;")
        layout.addWidget(desc)

        return page

    def _load_settings(self):
        settings = QSettings("Zstudy", "ZstudyApp")
        
        self.theme_combo.setCurrentText(settings.value("theme", "Dark (Default)"))
        self.accent_combo.setCurrentText(settings.value("accent_color", "Purple (#B48EAD)"))
        
        self.autosave_combo.setCurrentText(settings.value("autosave", "1 second"))

    def _save_settings(self):
        settings = QSettings("Zstudy", "ZstudyApp")
        
        settings.setValue("theme", self.theme_combo.currentText())
        settings.setValue("accent_color", self.accent_combo.currentText())
        
        settings.setValue("autosave", self.autosave_combo.currentText())
        
        # Apply accent color globally by replacing the old hex code in the source files
        import re
        import os
        old_color = settings.value("applied_accent_color", "#B48EAD").upper()
        new_color_str = self.accent_combo.currentText()
        if "Yellow" in new_color_str: new_color = "#FFC933"
        elif "Blue" in new_color_str: new_color = "#88C0D0"
        else: new_color = "#B48EAD"
        
        if new_color != old_color:
            ui_dir = os.path.abspath("ui")
            for root, dirs, files in os.walk(ui_dir):
                for file in files:
                    if file.endswith(".py") and file != "settings_dialog.py":
                        filepath = os.path.join(root, file)
                        with open(filepath, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        # case insensitive replace
                        content_new = re.sub(old_color, new_color, content, flags=re.IGNORECASE)
                        
                        if content != content_new:
                            with open(filepath, 'w', encoding='utf-8') as f:
                                f.write(content_new)
            settings.setValue("applied_accent_color", new_color)
            QMessageBox.information(self, "Restart Required", "Accent color applied! Please restart the app for all changes to take effect.")

    def closeEvent(self, event):
        self._save_settings()
        super().closeEvent(event)
