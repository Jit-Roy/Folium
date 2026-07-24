from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
    QPushButton, QFrame, QSizePolicy, QLabel, QStackedWidget,
    QFileDialog
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineProfile, QWebEngineSettings
from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QIcon, QColor
import os


class ReferenceViewerPanel(QWidget):
    """
    A dockable right-side panel that embeds a full web browser.
    Supports YouTube videos, PDFs (via Google Docs viewer), and any website.
    """

    # Emitted when the user explicitly closes the panel
    close_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(450)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── URL / search bar ──────────────────────────────────────────────────
        nav_frame = QFrame()
        nav_frame.setFixedHeight(40)
        nav_frame.setStyleSheet("background: #1e1e1e; border-bottom: 1px solid #2a2a2a;")
        nav_layout = QHBoxLayout(nav_frame)
        nav_layout.setContentsMargins(8, 4, 8, 4)
        nav_layout.setSpacing(4)

        # Back
        self.back_btn = QPushButton()
        self.back_btn.setIcon(QIcon("assets/icons/chevron-left.svg"))
        self.back_btn.setFixedSize(26, 26)
        self.back_btn.setToolTip("Back")
        self.back_btn.setStyleSheet(
            "QPushButton { border: none; background: transparent; }"
            "QPushButton:hover { background: rgba(255,255,255,0.08); border-radius: 4px; }"
            "QPushButton:disabled { opacity: 0.3; }"
        )
        self.back_btn.clicked.connect(self._go_back)
        nav_layout.addWidget(self.back_btn)

        # URL bar
        self.url_bar = QLineEdit()
        self.url_bar.setPlaceholderText("Paste URL, YouTube link, or search term…")
        self.url_bar.setStyleSheet("""
            QLineEdit {
                background: #282828;
                border: 1px solid #333333;
                border-radius: 5px;
                padding: 2px 8px;
                color: #FFFFFF;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 1px solid #B48EAD;
            }
        """)
        self.url_bar.returnPressed.connect(self._navigate)
        nav_layout.addWidget(self.url_bar)

        # Open file button
        open_file_btn = QPushButton()
        open_file_btn.setIcon(QIcon("assets/icons/folder.svg"))
        open_file_btn.setFixedSize(26, 26)
        open_file_btn.setToolTip("Browse for local file (PDFs, HTML, etc)")
        open_file_btn.setStyleSheet(
            "QPushButton { border: none; background: transparent; }"
            "QPushButton:hover { background: rgba(255,255,255,0.08); border-radius: 4px; }"
        )
        open_file_btn.clicked.connect(self._open_local_file)
        nav_layout.addWidget(open_file_btn)

        # Go button
        go_btn = QPushButton()
        go_btn.setIcon(QIcon("assets/icons/chevron-right.svg"))
        go_btn.setFixedSize(26, 26)
        go_btn.setToolTip("Go")
        go_btn.setStyleSheet(
            "QPushButton { border: none; background: transparent; }"
            "QPushButton:hover { background: rgba(180,142,173,0.2); border-radius: 4px; }"
        )
        go_btn.clicked.connect(self._navigate)
        nav_layout.addWidget(go_btn)

        layout.addWidget(nav_frame)

        # ── Quick-launch shortcuts ─────────────────────────────────────────────
        shortcuts_frame = QFrame()
        shortcuts_frame.setFixedHeight(36)
        shortcuts_frame.setStyleSheet("background: #1a1a1a; border-bottom: 1px solid #2a2a2a;")
        shortcuts_layout = QHBoxLayout(shortcuts_frame)
        shortcuts_layout.setContentsMargins(8, 4, 8, 4)
        shortcuts_layout.setSpacing(6)

        shortcut_data = [
            ("YouTube", "https://www.youtube.com"),
            ("Wikipedia", "https://en.wikipedia.org"),
            ("Google", "https://www.google.com"),
        ]
        
        shortcut_style = """
            QPushButton {
                border: 1px solid #333333;
                background: #242424;
                color: #FFFFFF;
                border-radius: 4px;
                padding: 0px 8px;
                font-size: 10px;
            }
            QPushButton:hover {
                border: 1px solid #B48EAD;
                color: #B48EAD;
                background: rgba(180,142,173,0.1);
            }
        """
        
        # Home button
        home_btn = QPushButton("Home")
        home_btn.setFixedHeight(24)
        home_btn.setCursor(Qt.PointingHandCursor)
        home_btn.setStyleSheet(shortcut_style)
        home_btn.clicked.connect(self._load_welcome_page)
        shortcuts_layout.addWidget(home_btn)

        for label, url in shortcut_data:
            btn = QPushButton(label)
            btn.setFixedHeight(24)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(shortcut_style)
            btn.clicked.connect(lambda _, u=url: self._load_url(u))
            shortcuts_layout.addWidget(btn)

        shortcuts_layout.addStretch()
        layout.addWidget(shortcuts_frame)

        # ── Web View ──────────────────────────────────────────────────────────
        self.web_view = QWebEngineView()
        self.web_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.web_view.urlChanged.connect(self._on_url_changed)
        self.web_view.setStyleSheet("background: #121212;")

        # Allow web pages (e.g. YouTube) to go fullscreen
        self.web_view.page().fullScreenRequested.connect(
            lambda request: request.accept()
        )
        self.web_view.page().setBackgroundColor(QColor("#121212"))

        # ── Fix for modern SPAs and Persistence ───────────────────────────────
        profile = self.web_view.page().profile()
        
        # Enable persistent storage (cookies, local storage for YouTube, etc.)
        import os
        from PySide6.QtCore import QStandardPaths
        cache_path = os.path.join(QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation), "Zstudy", "WebCache")
        os.makedirs(cache_path, exist_ok=True)
        profile.setPersistentStoragePath(cache_path)
        profile.setPersistentCookiesPolicy(QWebEngineProfile.AllowPersistentCookies)
        
        profile.setHttpUserAgent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        settings = self.web_view.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.Accelerated2dCanvasEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.ScrollAnimatorEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.PdfViewerEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, True)

        layout.addWidget(self.web_view, stretch=1)

    def save_state(self, settings):
        settings.beginGroup("reference_viewer")
        current_url = self.web_view.url().toString()
        if current_url.startswith("http://localhost/"):
            current_url = self.url_bar.text()
        elif not current_url or current_url.startswith("data:"):
            current_url = ""
        settings.setValue("url", current_url)
        settings.endGroup()

    def restore_state(self, settings):
        settings.beginGroup("reference_viewer")
        url = settings.value("url", "")
        settings.endGroup()
        
        if url:
            self._load_url(url)
        else:
            self._load_welcome_page()

    def _load_welcome_page(self):
        html = """
        <!DOCTYPE html>
        <html>
        <head>
        <style>
            body {
                background: #121212;
                color: #666666;
                font-family: 'Segoe UI', sans-serif;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                height: 100vh;
                margin: 0;
                text-align: center;
            }
            .icon { font-size: 48px; margin-bottom: 16px; }
            h2 { color: #FFFFFF; font-weight: 400; margin-bottom: 8px; }
            p { font-size: 13px; line-height: 1.6; max-width: 280px; }
            .hint {
                margin-top: 20px;
                font-size: 11px;
                color: #444444;
                border: 1px solid #2a2a2a;
                padding: 8px 14px;
                border-radius: 6px;
            }
        </style>
        </head>
        <body>
            <div class="icon">
                <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                    <rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect>
                    <line x1="8" y1="21" x2="16" y2="21"></line>
                    <line x1="12" y1="17" x2="12" y2="21"></line>
                </svg>
            </div>
            <h2>Reference Viewer</h2>
            <p>Paste a URL above to load YouTube videos, PDFs, Wikipedia articles, and more.</p>
            <div class="hint">
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: middle; margin-right: 4px; margin-bottom: 2px;">
                    <path d="M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A6 6 0 0 0 6 8c0 1 .2 2.2 1.5 3.5.7.9 1.2 1.5 1.5 2.5"/>
                    <path d="M9 18h6"/>
                    <path d="M10 22h4"/>
                </svg>
                Study tip: keep your notes on the left, references on the right
            </div>
        </body>
        </html>
        """
        self.web_view.setHtml(html)

    def _navigate(self):
        raw = self.url_bar.text().strip()
        if not raw:
            return
        self._load_url(raw)

    def _load_url(self, raw: str):
        """Smart URL loader: handles YouTube, plain URLs, and search terms."""
        import re, urllib.parse
        yt_match = re.search(
            r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([A-Za-z0-9_\-]{11})", raw
        )
        if yt_match:
            vid_id = yt_match.group(1)
            
            # Parse query params to keep playlists or timestamps
            parsed = urllib.parse.urlparse(raw)
            qs = urllib.parse.parse_qs(parsed.query)
            
            display_url = f"https://www.youtube.com/watch?v={vid_id}"
            embed_src = f"https://www.youtube.com/embed/{vid_id}?autoplay=0&rel=0"
            
            if 'list' in qs:
                embed_src += f"&list={qs['list'][0]}"
                display_url += f"&list={qs['list'][0]}"
            if 't' in qs:
                embed_src += f"&start={qs['t'][0].replace('s', '')}"
                display_url += f"&t={qs['t'][0]}"
            
            # YouTube embeds throw Error 152 if framed by a youtube.com base URL.
            # Use localhost as a safe, permitted origin.
            html = f"""
            <!DOCTYPE html>
            <html style="margin:0;padding:0;width:100%;height:100%;overflow:hidden;">
              <body style="margin:0;padding:0;width:100%;height:100%;background:#121212;">
                <iframe style="width:100%;height:100%;border:none;" 
                        src="{embed_src}" 
                        allowfullscreen>
                </iframe>
              </body>
            </html>
            """
            self.web_view.setHtml(html, QUrl("http://localhost/"))
            self.url_bar.setText(display_url)
            return
            
        if raw.startswith("http://") or raw.startswith("https://") or raw.startswith("file://"):
            url = raw
        elif os.path.exists(raw):
            # It's a local file path
            from pathlib import Path
            url = Path(raw).as_uri()
        elif "." in raw and " " not in raw:
            url = f"https://{raw}"
        else:
            # Treat as a search query
            import urllib.parse
            url = f"https://www.google.com/search?q={urllib.parse.quote(raw)}"

        self.web_view.load(QUrl(url))
        self.url_bar.setText(url)

    def _on_url_changed(self, qurl: QUrl):
        """Sync URL bar when the page navigates — ignore internal welcome page URLs."""
        url_str = qurl.toString()
        # Skip our fake base URL for YouTube
        if url_str.startswith("http://localhost/"):
            return
            
        # Skip internal data: URLs (welcome page) and blank pages
        if url_str.startswith("data:") or url_str in ("about:blank", ""):
            self.url_bar.clear()
            return
            
        # Automatically convert any YouTube navigations into our clean full-screen embed
        import re
        if re.search(r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([A-Za-z0-9_\-]{11})", url_str):
            from PySide6.QtCore import QTimer
            QTimer.singleShot(0, lambda: self._load_url(url_str))
            return
            
        self.url_bar.setText(url_str)

    def _go_back(self):
        if self.web_view.history().canGoBack():
            self.web_view.back()

    def _open_local_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Local File",
            "",
            "Supported Files (*.pdf *.html *.htm *.txt *.jpg *.png);;PDF Files (*.pdf);;All Files (*)"
        )
        if file_path:
            self.url_bar.setText(file_path)
            self._navigate()
