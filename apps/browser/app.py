"""
WinPy11 Edge Browser
Fonctionne avec ou sans PySide6-WebEngine.
"""
import os
import sys
import time
import webbrowser

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLineEdit, QStackedWidget, QLabel, QMenu, QSizePolicy
)
from PySide6.QtCore import (
    Qt, Signal, QUrl, QRect, QRectF, QSize, QTimer, QPointF
)
from PySide6.QtGui import (
    QFont, QColor, QPainter, QPen, QPainterPath, QIcon
)

from core.icons import get_pixmap, get_icon

# Vérifier si WebEngine est disponible
_HAS_WEBENGINE = False
try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
    from PySide6.QtWebEngineCore import (
        QWebEnginePage, QWebEngineProfile, QWebEngineSettings
    )
    _HAS_WEBENGINE = True
except ImportError:
    pass

ACCENT = QColor(0, 103, 192)
BG_TAB_BAR = QColor(25, 25, 25)
BG_TAB_ACTIVE = QColor(38, 38, 38)
BG_TOOLBAR = QColor(38, 38, 38)
BG_BODY = QColor(30, 30, 30)
TEXT_COLOR = QColor(255, 255, 255, 210)
TEXT_DIM = QColor(255, 255, 255, 100)
BORDER_COL = QColor(255, 255, 255, 8)

HOME_PAGE = """<!DOCTYPE html>
<html><head><style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#1e1e1e;color:#fff;font-family:'Segoe UI',sans-serif;
display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;overflow:hidden}
.logo{font-size:38px;font-weight:600;margin-bottom:28px;
background:linear-gradient(135deg,#0078d4,#00b4d8);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.search-box{width:560px;max-width:90vw;position:relative}
.search-box input{width:100%;height:44px;background:rgba(255,255,255,.06);
border:1px solid rgba(255,255,255,.08);border-radius:22px;color:#fff;font-size:14px;
padding:0 48px 0 20px;outline:none;transition:.2s}
.search-box input:focus{background:rgba(255,255,255,.1);border-color:rgba(0,120,212,.6);
box-shadow:0 0 0 2px rgba(0,120,212,.15)}
.search-box input::placeholder{color:rgba(255,255,255,.25)}
.search-icon{position:absolute;right:16px;top:50%;transform:translateY(-50%);color:rgba(255,255,255,.25)}
.shortcuts{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-top:36px;width:560px;max-width:90vw}
.sc{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.06);
border-radius:10px;padding:14px;text-align:center;cursor:pointer;transition:.15s;text-decoration:none;color:#fff}
.sc:hover{background:rgba(255,255,255,.08);transform:translateY(-1px)}
.sc .i{font-size:22px;margin-bottom:6px}.sc .l{font-size:11px;color:rgba(255,255,255,.5)}
</style></head><body>
<div class="logo">WinPy11 Edge</div>
<div class="search-box">
<input type="text" placeholder="Search the web..." id="s"
onkeydown="if(event.key==='Enter')window.location.href='https://www.google.com/search?q='+this.value">
<span class="search-icon">⌕</span></div>
<div class="shortcuts">
<a class="sc" href="https://www.google.com"><div class="i">🔍</div><div class="l">Google</div></a>
<a class="sc" href="https://www.youtube.com"><div class="i">▶️</div><div class="l">YouTube</div></a>
<a class="sc" href="https://github.com"><div class="i">💻</div><div class="l">GitHub</div></a>
<a class="sc" href="https://en.wikipedia.org"><div class="i">📚</div><div class="l">Wikipedia</div></a>
</div></body></html>"""


# ═══════════════════════════════════════════════════════
#  BROWSER PAGE — intercepte ouverture nouvel onglet
# ═══════════════════════════════════════════════════════

if _HAS_WEBENGINE:
    class BrowserPage(QWebEnginePage):
        open_in_new_tab = Signal(QUrl)

        def __init__(self, profile, parent=None):
            super().__init__(profile, parent)

        def createWindow(self, window_type):
            temp = BrowserPage(self.profile(), self)
            temp.urlChanged.connect(lambda url: self._on_new(url, temp))
            return temp

        def _on_new(self, url, temp):
            if url.isValid() and url.toString() not in ("", "about:blank"):
                self.open_in_new_tab.emit(url)
            QTimer.singleShot(100, temp.deleteLater)

    class BrowserTab:
        def __init__(self, profile):
            self.view = QWebEngineView()
            self.page = BrowserPage(profile, self.view)
            self.view.setPage(self.page)
            self.title = "New Tab"
            self.url = ""
            self.loading = False
            s = self.page.settings()
            s.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
            s.setAttribute(QWebEngineSettings.LocalStorageEnabled, True)
            s.setAttribute(QWebEngineSettings.ScrollAnimatorEnabled, True)


# ═══════════════════════════════════════════════════════
#  TAB BUTTON
# ═══════════════════════════════════════════════════════

class TabButton(QWidget):
    clicked = Signal()
    close_clicked = Signal()
    middle_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.title = "New Tab"
        self.active = False
        self.loading = False
        self._hover = False
        self._hover_close = False
        self._favicon = None
        self.setFixedHeight(34)
        self.setMinimumWidth(60)
        self.setMaximumWidth(240)
        self.setCursor(Qt.PointingHandCursor)
        self.setMouseTracking(True)

    def set_title(self, t):
        self.title = t[:28] + "..." if len(t) > 28 else t
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        w, h = self.width(), self.height()

        if self.active:
            path = QPainterPath()
            path.moveTo(0, h); path.lineTo(0, 6); path.quadTo(0, 0, 6, 0)
            path.lineTo(w-6, 0); path.quadTo(w, 0, w, 6); path.lineTo(w, h)
            p.setPen(Qt.NoPen); p.setBrush(BG_TAB_ACTIVE); p.drawPath(path)
        elif self._hover:
            p.setBrush(QColor(255, 255, 255, 8)); p.setPen(Qt.NoPen)
            p.drawRoundedRect(QRectF(2, 2, w-4, h-4), 6, 6)

        ix = 10
        if self.loading:
            p.setPen(QPen(ACCENT, 2)); p.setBrush(Qt.NoBrush)
            angle = int(time.time() * 720) % 360
            p.drawArc(QRect(ix, 9, 14, 14), angle * 16, 270 * 16)
        elif self._favicon and not self._favicon.isNull():
            p.drawPixmap(ix, 9, self._favicon.scaled(14, 14, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            p.drawPixmap(ix, 9, get_pixmap("globe", 14, TEXT_DIM))

        p.setFont(QFont("Segoe UI", 9))
        p.setPen(TEXT_COLOR if self.active else TEXT_DIM)
        tx = ix + 20
        tw = w - tx - 28
        if tw > 10:
            fm = p.fontMetrics()
            p.drawText(QRect(tx, 0, tw, h), Qt.AlignVCenter, fm.elidedText(self.title, Qt.ElideRight, tw))

        cr = QRect(w-26, 7, 20, 20)
        if self._hover_close:
            p.setBrush(QColor(255, 255, 255, 15)); p.setPen(Qt.NoPen)
            p.drawRoundedRect(cr, 4, 4)

        if self._hover or self.active:
            ccx, ccy = cr.center().x(), cr.center().y()
            p.setPen(QPen(QColor(255, 255, 255, 140), 1.2))
            p.drawLine(ccx-4, ccy-4, ccx+4, ccy+4)
            p.drawLine(ccx+4, ccy-4, ccx-4, ccy+4)
        p.end()

    def enterEvent(self, e): self._hover = True; self.update()
    def leaveEvent(self, e): self._hover = False; self._hover_close = False; self.update()

    def mouseMoveEvent(self, event):
        old = self._hover_close
        self._hover_close = QRect(self.width()-26, 7, 20, 20).contains(event.position().toPoint())
        if old != self._hover_close: self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if QRect(self.width()-26, 7, 20, 20).contains(event.position().toPoint()):
                self.close_clicked.emit()
            else:
                self.clicked.emit()
        elif event.button() == Qt.MiddleButton:
            self.middle_clicked.emit()

    def sizeHint(self): return QSize(200, 34)


# ═══════════════════════════════════════════════════════
#  TAB BAR
# ═══════════════════════════════════════════════════════

class TabBar(QWidget):
    tab_clicked = Signal(int)
    tab_close = Signal(int)
    tab_middle_close = Signal(int)
    new_tab = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(36)
        self.tabs = []
        self._lo = QHBoxLayout(self)
        self._lo.setContentsMargins(4, 2, 4, 0)
        self._lo.setSpacing(1)

        self._new_btn = QPushButton()
        self._new_btn.setFixedSize(28, 28)
        self._new_btn.setCursor(Qt.PointingHandCursor)
        self._new_btn.setIcon(get_icon("plus", 14, QColor(255, 255, 255, 150)))
        self._new_btn.setStyleSheet("""QPushButton{background:transparent;border:none;border-radius:6px;}
            QPushButton:hover{background:rgba(255,255,255,10);}""")
        self._new_btn.clicked.connect(self.new_tab.emit)
        self._lo.addStretch()
        self._lo.addWidget(self._new_btn)

        self._load_timer = None

    def add_tab(self, title="New Tab"):
        btn = TabButton(); btn.set_title(title)
        self._lo.insertWidget(len(self.tabs), btn)
        self.tabs.append(btn)
        self._reconnect()
        return len(self.tabs) - 1

    def remove_tab(self, idx):
        if 0 <= idx < len(self.tabs):
            b = self.tabs.pop(idx)
            self._lo.removeWidget(b); b.deleteLater()
            self._reconnect()

    def set_active(self, idx):
        for i, t in enumerate(self.tabs): t.active = (i == idx); t.update()

    def set_title(self, idx, t):
        if 0 <= idx < len(self.tabs): self.tabs[idx].set_title(t)

    def set_loading(self, idx, v):
        if 0 <= idx < len(self.tabs):
            self.tabs[idx].loading = v; self.tabs[idx].update()
            if v:
                if not self._load_timer:
                    self._load_timer = QTimer(self)
                    self._load_timer.timeout.connect(self._upd_loading)
                    self._load_timer.start(50)
            elif not any(t.loading for t in self.tabs):
                if self._load_timer:
                    self._load_timer.stop(); self._load_timer = None

    def _upd_loading(self):
        for t in self.tabs:
            if t.loading: t.update()

    def set_favicon(self, idx, px):
        if 0 <= idx < len(self.tabs): self.tabs[idx]._favicon = px; self.tabs[idx].update()

    def _reconnect(self):
        for i, b in enumerate(self.tabs):
            try: b.clicked.disconnect()
            except (TypeError, RuntimeError): pass
            try: b.close_clicked.disconnect()
            except (TypeError, RuntimeError): pass
            try: b.middle_clicked.disconnect()
            except (TypeError, RuntimeError): pass
            b.clicked.connect(lambda _=False, idx=i: self.tab_clicked.emit(idx))
            b.close_clicked.connect(lambda _=False, idx=i: self.tab_close.emit(idx))
            b.middle_clicked.connect(lambda _=False, idx=i: self.tab_middle_close.emit(idx))

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), BG_TAB_BAR)
        p.setPen(BORDER_COL); p.drawLine(0, self.height()-1, self.width(), self.height()-1)
        p.end()


# ═══════════════════════════════════════════════════════
#  NAVIGATION BAR
# ═══════════════════════════════════════════════════════

class NavigationBar(QWidget):
    navigate = Signal(str)
    back = Signal()
    forward = Signal()
    reload_page = Signal()
    go_home = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(42)
        lo = QHBoxLayout(self)
        lo.setContentsMargins(8, 4, 8, 4)
        lo.setSpacing(4)

        css = """QPushButton{background:transparent;border:none;border-radius:6px;padding:4px;}
            QPushButton:hover{background:rgba(255,255,255,10);}
            QPushButton:disabled{opacity:0.3;}"""

        self.back_btn = QPushButton()
        self.back_btn.setIcon(get_icon("arrow_left", 16, QColor(255,255,255,180)))
        self.back_btn.setFixedSize(32, 32); self.back_btn.setStyleSheet(css)
        self.back_btn.clicked.connect(self.back.emit)
        lo.addWidget(self.back_btn)

        self.fwd_btn = QPushButton()
        self.fwd_btn.setIcon(get_icon("arrow_right", 16, QColor(255,255,255,180)))
        self.fwd_btn.setFixedSize(32, 32); self.fwd_btn.setStyleSheet(css)
        self.fwd_btn.clicked.connect(self.forward.emit)
        lo.addWidget(self.fwd_btn)

        self.reload_btn = QPushButton()
        self.reload_btn.setIcon(get_icon("refresh", 14, QColor(255,255,255,180)))
        self.reload_btn.setFixedSize(32, 32); self.reload_btn.setStyleSheet(css)
        self.reload_btn.clicked.connect(self.reload_page.emit)
        lo.addWidget(self.reload_btn)

        self.home_btn = QPushButton()
        self.home_btn.setIcon(get_icon("home", 16, QColor(255,255,255,180)))
        self.home_btn.setFixedSize(32, 32); self.home_btn.setStyleSheet(css)
        self.home_btn.clicked.connect(self.go_home.emit)
        lo.addWidget(self.home_btn)

        lo.addSpacing(4)

        self.url_bar = QLineEdit()
        self.url_bar.setFont(QFont("Segoe UI", 10))
        self.url_bar.setFixedHeight(32)
        self.url_bar.setPlaceholderText("Search or enter URL")
        self.url_bar.setStyleSheet("""
            QLineEdit{background:rgba(255,255,255,6);border:1px solid rgba(255,255,255,8);
            border-radius:16px;color:white;padding:0 16px;selection-background-color:rgba(0,103,192,120);}
            QLineEdit:focus{background:rgba(255,255,255,10);border:1px solid rgba(0,103,192,160);}
        """)
        self.url_bar.returnPressed.connect(lambda: self.navigate.emit(self.url_bar.text().strip()))
        lo.addWidget(self.url_bar, 1)

        lo.addSpacing(4)
        self.menu_btn = QPushButton()
        self.menu_btn.setIcon(get_icon("navigation", 16, QColor(255,255,255,180)))
        self.menu_btn.setFixedSize(32, 32); self.menu_btn.setStyleSheet(css)
        lo.addWidget(self.menu_btn)

    def set_url(self, u): self.url_bar.setText(u)

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), BG_TOOLBAR)
        p.setPen(BORDER_COL); p.drawLine(0, self.height()-1, self.width(), self.height()-1)
        p.end()


# ═══════════════════════════════════════════════════════
#  FALLBACK WIDGET (quand pas de WebEngine)
# ═══════════════════════════════════════════════════════

class FallbackWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background:#1e1e1e;")

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        w, h = self.width(), self.height()

        p.fillRect(self.rect(), QColor(30, 30, 30))

        px = get_pixmap("globe", 64, QColor(255, 255, 255, 35))
        p.drawPixmap((w-64)//2, h//2 - 80, px)

        p.setFont(QFont("Segoe UI Semibold", 18))
        p.setPen(QColor(255, 255, 255, 170))
        p.drawText(QRect(0, h//2 - 10, w, 30), Qt.AlignCenter, "Browser unavailable")

        p.setFont(QFont("Segoe UI", 11))
        p.setPen(QColor(255, 255, 255, 80))
        p.drawText(QRect(0, h//2 + 25, w, 25), Qt.AlignCenter, "PySide6-WebEngine is not installed")

        p.setFont(QFont("Segoe UI", 10))
        p.setPen(QColor(96, 175, 255))
        p.drawText(QRect(0, h//2 + 55, w, 22), Qt.AlignCenter, "pip install PySide6-WebEngine")

        p.end()


# ═══════════════════════════════════════════════════════
#  APP PRINCIPALE
# ═══════════════════════════════════════════════════════

class App(QWidget):
    def __init__(self, file_system=None, parent=None):
        super().__init__(parent)
        self.fs = file_system

        lo = QVBoxLayout(self)
        lo.setContentsMargins(0, 0, 0, 0)
        lo.setSpacing(0)

        if not _HAS_WEBENGINE:
            lo.addWidget(FallbackWidget())
            return

        self.tabs_data = []
        self.current_idx = -1

        self._profile = QWebEngineProfile.defaultProfile()
        self._profile.setHttpUserAgent(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        self.tab_bar = TabBar()
        self.tab_bar.tab_clicked.connect(self._switch_tab)
        self.tab_bar.tab_close.connect(self._close_tab)
        self.tab_bar.tab_middle_close.connect(self._close_tab)
        self.tab_bar.new_tab.connect(lambda: self._new_tab())
        lo.addWidget(self.tab_bar)

        self.nav_bar = NavigationBar()
        self.nav_bar.navigate.connect(self._navigate)
        self.nav_bar.back.connect(self._go_back)
        self.nav_bar.forward.connect(self._go_forward)
        self.nav_bar.reload_page.connect(self._reload)
        self.nav_bar.go_home.connect(self._go_home)
        lo.addWidget(self.nav_bar)

        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background:#1e1e1e;")
        lo.addWidget(self.stack, 1)

        self._new_tab()

    def _create_tab(self):
        tab = BrowserTab(self._profile)
        tab.view.titleChanged.connect(lambda t, tb=tab: self._on_title(tb, t))
        tab.view.urlChanged.connect(lambda u, tb=tab: self._on_url(tb, u))
        tab.view.loadStarted.connect(lambda tb=tab: self._on_start(tb))
        tab.view.loadFinished.connect(lambda ok, tb=tab: self._on_end(tb))
        tab.view.iconChanged.connect(lambda ico, tb=tab: self._on_ico(tb, ico))
        tab.page.open_in_new_tab.connect(self._open_new)
        tab.view.page().setBackgroundColor(QColor(30, 30, 30))
        self.tabs_data.append(tab)
        self.stack.addWidget(tab.view)
        return len(self.tabs_data) - 1

    def _new_tab(self, url=None):
        idx = self._create_tab()
        self.tab_bar.add_tab("New Tab")
        self._switch_tab(idx)
        if url:
            u = QUrl(url) if isinstance(url, str) else url
            self.tabs_data[idx].view.setUrl(u)
        else:
            self.tabs_data[idx].view.setHtml(HOME_PAGE, QUrl("about:home"))

    def _open_new(self, url):
        if url.isValid():
            self._new_tab(url)

    def _switch_tab(self, idx):
        if 0 <= idx < len(self.tabs_data):
            self.current_idx = idx
            self.stack.setCurrentWidget(self.tabs_data[idx].view)
            self.tab_bar.set_active(idx)
            u = self.tabs_data[idx].url
            self.nav_bar.set_url("" if u in ("", "about:home") else u)
            self._upd_nav()

    def _close_tab(self, idx):
        if len(self.tabs_data) <= 1:
            self._go_home(); return
        if 0 <= idx < len(self.tabs_data):
            tab = self.tabs_data.pop(idx)
            self.stack.removeWidget(tab.view); tab.view.deleteLater()
            self.tab_bar.remove_tab(idx)
            if self.current_idx >= len(self.tabs_data):
                self.current_idx = len(self.tabs_data) - 1
            elif self.current_idx > idx:
                self.current_idx -= 1
            self._switch_tab(max(0, self.current_idx))

    def _navigate(self, text):
        if self.current_idx < 0 or not text: return
        t = text.strip()
        if "." in t and " " not in t:
            if not t.startswith(("http://", "https://")): t = "https://" + t
        elif not t.startswith(("http://", "https://", "file://")):
            t = f"https://www.google.com/search?q={t}"
        self.tabs_data[self.current_idx].view.setUrl(QUrl(t))

    def navigate_to(self, url):
        """API publique pour naviguer vers une URL (utilisé par les raccourcis web)."""
        if not _HAS_WEBENGINE:
            webbrowser.open(url)
            return
        if self.current_idx >= 0:
            self.tabs_data[self.current_idx].view.setUrl(QUrl(url))
        else:
            self._new_tab(url)

    def _go_back(self):
        if self.current_idx >= 0: self.tabs_data[self.current_idx].view.back()
    def _go_forward(self):
        if self.current_idx >= 0: self.tabs_data[self.current_idx].view.forward()
    def _reload(self):
        if self.current_idx >= 0: self.tabs_data[self.current_idx].view.reload()
    def _go_home(self):
        if self.current_idx >= 0:
            self.tabs_data[self.current_idx].view.setHtml(HOME_PAGE, QUrl("about:home"))
            self.nav_bar.set_url("")

    def _on_title(self, tab, title):
        i = self._idx(tab)
        if i >= 0: tab.title = title or "New Tab"; self.tab_bar.set_title(i, tab.title)
    def _on_url(self, tab, url):
        i = self._idx(tab)
        if i >= 0:
            tab.url = url.toString()
            if i == self.current_idx:
                self.nav_bar.set_url("" if tab.url == "about:home" else tab.url)
                self._upd_nav()
    def _on_start(self, tab):
        i = self._idx(tab)
        if i >= 0: tab.loading = True; self.tab_bar.set_loading(i, True)
    def _on_end(self, tab):
        i = self._idx(tab)
        if i >= 0: tab.loading = False; self.tab_bar.set_loading(i, False); self._upd_nav()
    def _on_ico(self, tab, icon):
        i = self._idx(tab)
        if i >= 0:
            px = icon.pixmap(16, 16)
            if not px.isNull(): self.tab_bar.set_favicon(i, px)

    def _idx(self, tab):
        try: return self.tabs_data.index(tab)
        except ValueError: return -1

    def _upd_nav(self):
        if self.current_idx >= 0:
            v = self.tabs_data[self.current_idx].view
            self.nav_bar.back_btn.setEnabled(v.history().canGoBack())
            self.nav_bar.fwd_btn.setEnabled(v.history().canGoForward())

    def paintEvent(self, event):
        p = QPainter(self); p.fillRect(self.rect(), BG_BODY); p.end()