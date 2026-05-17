from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QScrollArea, QGridLayout,
    QGraphicsDropShadowEffect
)
from PySide6.QtCore import (
    Qt, Signal, QRectF, QRect, QTimer, QPoint,
    QPropertyAnimation, QEasingCurve, Property
)
from PySide6.QtGui import QFont, QColor, QPainter, QPen, QPainterPath

from core.icons import get_pixmap, get_icon


class AppTile(QWidget):
    clicked = Signal()

    def __init__(self, name, icon_name, parent=None):
        super().__init__(parent)
        self.name = name
        self.icon_name = icon_name
        self._px = get_pixmap(icon_name, 30)
        self.setFixedSize(88, 78)
        self.setCursor(Qt.PointingHandCursor)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        if self.underMouse():
            p.setBrush(QColor(255, 255, 255, 12)); p.setPen(Qt.NoPen)
            p.drawRoundedRect(self.rect().adjusted(3, 3, -3, -3), 6, 6)
        p.drawPixmap((self.width()-30)//2, 10, self._px)
        p.setFont(QFont("Segoe UI", 8))
        p.setPen(QColor(255, 255, 255, 190))
        p.drawText(QRect(4, 44, self.width()-8, 28), Qt.AlignHCenter | Qt.AlignTop | Qt.TextWordWrap, self.name)
        p.end()

    def enterEvent(self, e): self.update()
    def leaveEvent(self, e): self.update()
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton: self.clicked.emit()


class AppListItem(QWidget):
    clicked = Signal()

    def __init__(self, name, icon_name, parent=None):
        super().__init__(parent)
        self.name = name
        self._px = get_pixmap(icon_name, 20)
        self.setFixedHeight(36)
        self.setCursor(Qt.PointingHandCursor)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        if self.underMouse():
            p.setBrush(QColor(255, 255, 255, 10)); p.setPen(Qt.NoPen)
            p.drawRoundedRect(self.rect().adjusted(4, 1, -4, -1), 5, 5)
        p.drawPixmap(16, (self.height()-20)//2, self._px)
        p.setFont(QFont("Segoe UI", 10))
        p.setPen(QColor(255, 255, 255, 210))
        p.drawText(QRect(44, 0, self.width()-52, self.height()), Qt.AlignVCenter, self.name)
        p.end()

    def enterEvent(self, e): self.update()
    def leaveEvent(self, e): self.update()
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton: self.clicked.emit()


class SearchResultItem(QWidget):
    """Résultat de recherche avec highlight."""
    clicked = Signal()

    def __init__(self, name, icon_name, category="App", parent=None):
        super().__init__(parent)
        self.name = name
        self.category = category
        self._px = get_pixmap(icon_name, 24)
        self.setFixedHeight(44)
        self.setCursor(Qt.PointingHandCursor)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)

        if self.underMouse():
            p.setBrush(QColor(255, 255, 255, 10)); p.setPen(Qt.NoPen)
            p.drawRoundedRect(self.rect().adjusted(4, 2, -4, -2), 6, 6)

        p.drawPixmap(16, (self.height()-24)//2, self._px)

        p.setFont(QFont("Segoe UI", 10))
        p.setPen(QColor(255, 255, 255, 220))
        p.drawText(QRect(50, 2, self.width()-60, 22), Qt.AlignVCenter, self.name)

        p.setFont(QFont("Segoe UI", 8))
        p.setPen(QColor(255, 255, 255, 70))
        p.drawText(QRect(50, 22, self.width()-60, 18), Qt.AlignVCenter, self.category)
        p.end()

    def enterEvent(self, e): self.update()
    def leaveEvent(self, e): self.update()
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton: self.clicked.emit()


class StartMenu(QWidget):
    app_clicked = Signal(str)

    MENU_W = 640
    MENU_H = 580
    SLIDE_PX = 40

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(self.MENU_W, self.MENU_H)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.SubWindow)

        self._is_open = False
        self._showing_all = False
        self._searching = False
        self._apps_data = []
        self._opacity_val = 0.0

        self._pos_anim = QPropertyAnimation(self, b"pos")
        self._opa_anim = QPropertyAnimation(self, b"menu_opacity")

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(40); shadow.setOffset(0, 6)
        shadow.setColor(QColor(0, 0, 0, 90))
        self.setGraphicsEffect(shadow)

        self._build_ui()
        self.hide()

    def get_menu_opacity(self): return self._opacity_val
    def set_menu_opacity(self, v):
        self._opacity_val = max(0.0, min(1.0, v)); self.setWindowOpacity(self._opacity_val)
    menu_opacity = Property(float, get_menu_opacity, set_menu_opacity)

    def is_open(self): return self._is_open

    def slide_show(self, x, y):
        self._is_open = True
        self.move(x, y + self.SLIDE_PX); self.setWindowOpacity(0.0)
        self.show(); self.raise_()

        # Reset search
        self.search.clear()
        self._on_search_changed("")
        if self._showing_all:
            self._show_pinned()

        self._pos_anim.stop()
        self._pos_anim.setDuration(280); self._pos_anim.setEasingCurve(QEasingCurve.OutQuart)
        self._pos_anim.setStartValue(QPoint(x, y + self.SLIDE_PX))
        self._pos_anim.setEndValue(QPoint(x, y)); self._pos_anim.start()

        self._opa_anim.stop()
        self._opa_anim.setDuration(200); self._opa_anim.setEasingCurve(QEasingCurve.OutQuad)
        self._opa_anim.setStartValue(0.0); self._opa_anim.setEndValue(1.0); self._opa_anim.start()

        # Focus search bar
        QTimer.singleShot(300, self.search.setFocus)

    def slide_hide(self):
        if not self._is_open: return
        self._is_open = False; cp = self.pos()
        self._pos_anim.stop()
        self._pos_anim.setDuration(180); self._pos_anim.setEasingCurve(QEasingCurve.InQuad)
        self._pos_anim.setStartValue(cp)
        self._pos_anim.setEndValue(QPoint(cp.x(), cp.y() + self.SLIDE_PX)); self._pos_anim.start()
        self._opa_anim.stop()
        self._opa_anim.setDuration(150); self._opa_anim.setEasingCurve(QEasingCurve.InQuad)
        self._opa_anim.setStartValue(self._opacity_val); self._opa_anim.setEndValue(0.0); self._opa_anim.start()
        QTimer.singleShot(200, self._finish_hide)

    def _finish_hide(self):
        if not self._is_open:
            self.hide()
            if self._showing_all: self._show_pinned()

    def _build_ui(self):
        self._lo = QVBoxLayout(self)
        self._lo.setContentsMargins(24, 24, 24, 16)
        self._lo.setSpacing(0)

        # Search
        self.search = QLineEdit()
        self.search.setPlaceholderText("   Search for apps, settings, and documents")
        self.search.setFixedHeight(36)
        self.search.setFont(QFont("Segoe UI", 10))
        self.search.setStyleSheet("""
            QLineEdit{background:rgba(255,255,255,7);border:1px solid rgba(255,255,255,10);
            border-bottom:2px solid rgba(0,103,192,200);border-radius:6px;color:white;padding:0 14px;}
            QLineEdit:focus{background:rgba(255,255,255,10);border-bottom:2px solid rgba(0,103,192,255);}
        """)
        self.search.textChanged.connect(self._on_search_changed)
        self._lo.addWidget(self.search)
        self._lo.addSpacing(16)

        # Header
        self._header_lo = QHBoxLayout()
        self._header_label = QLabel("Pinned")
        self._header_label.setFont(QFont("Segoe UI Semibold", 13))
        self._header_label.setStyleSheet("color:white;")
        self._header_lo.addWidget(self._header_label)
        self._header_lo.addStretch()
        self._toggle_btn = QPushButton("All apps  →")
        self._toggle_btn.setFont(QFont("Segoe UI", 9))
        self._toggle_btn.setCursor(Qt.PointingHandCursor)
        self._toggle_btn.setStyleSheet("""
            QPushButton{background:rgba(255,255,255,7);border:none;border-radius:4px;
            color:rgba(255,255,255,200);padding:4px 14px;}
            QPushButton:hover{background:rgba(255,255,255,12);}
        """)
        self._toggle_btn.clicked.connect(self._toggle_view)
        self._header_lo.addWidget(self._toggle_btn)
        self._lo.addLayout(self._header_lo)
        self._lo.addSpacing(8)

        # Content scroll
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet("""
            QScrollArea{background:transparent;border:none;}
            QScrollBar:vertical{width:3px;background:transparent;}
            QScrollBar::handle:vertical{background:rgba(255,255,255,20);border-radius:1px;min-height:30px;}
            QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0;}
        """)

        # Pinned grid
        self._pinned_w = QWidget(); self._pinned_w.setStyleSheet("background:transparent;")
        self._pinned_grid = QGridLayout(self._pinned_w)
        self._pinned_grid.setSpacing(4); self._pinned_grid.setContentsMargins(0, 0, 0, 0)

        # All apps list
        self._all_w = QWidget(); self._all_w.setStyleSheet("background:transparent;")
        self._all_lo = QVBoxLayout(self._all_w)
        self._all_lo.setContentsMargins(0, 0, 0, 0); self._all_lo.setSpacing(1)

        # Search results
        self._search_w = QWidget(); self._search_w.setStyleSheet("background:transparent;")
        self._search_lo = QVBoxLayout(self._search_w)
        self._search_lo.setContentsMargins(0, 0, 0, 0); self._search_lo.setSpacing(2)

        self._scroll.setWidget(self._pinned_w)
        self._lo.addWidget(self._scroll, 1)

        # Bottom section (Recommended, etc.)
        self._bottom_section = QWidget()
        bl = QVBoxLayout(self._bottom_section)
        bl.setContentsMargins(0, 0, 0, 0); bl.setSpacing(0)

        bl.addSpacing(8)
        sep = QWidget(); sep.setFixedHeight(1); sep.setStyleSheet("background:rgba(255,255,255,8);")
        bl.addWidget(sep); bl.addSpacing(6)

        rl = QLabel("Recommended"); rl.setFont(QFont("Segoe UI Semibold", 13))
        rl.setStyleSheet("color:white;"); bl.addWidget(rl); bl.addSpacing(4)

        self._rec1 = self._make_rec("readme.txt", "Recently opened")
        self._rec2 = self._make_rec("notes.md", "Yesterday")
        bl.addWidget(self._rec1); bl.addWidget(self._rec2)

        self._lo.addWidget(self._bottom_section)
        self._lo.addStretch()

        # Bottom bar
        self._lo.addSpacing(4)
        sep2 = QWidget(); sep2.setFixedHeight(1); sep2.setStyleSheet("background:rgba(255,255,255,8);")
        self._lo.addWidget(sep2); self._lo.addSpacing(6)

        bottom = QHBoxLayout()
        ub = QPushButton(); ub.setIcon(get_icon("user", 18, QColor(255, 255, 255, 200)))
        ub.setText("  User"); ub.setFont(QFont("Segoe UI", 10)); ub.setCursor(Qt.PointingHandCursor)
        ub.setStyleSheet("""QPushButton{background:transparent;border:none;border-radius:6px;
            color:white;padding:8px 14px;}QPushButton:hover{background:rgba(255,255,255,8);}""")
        bottom.addWidget(ub); bottom.addStretch()
        pb = QPushButton(); pb.setIcon(get_icon("power", 18, QColor(255, 255, 255, 200)))
        pb.setFixedSize(36, 36); pb.setCursor(Qt.PointingHandCursor)
        pb.setStyleSheet("""QPushButton{background:transparent;border:none;border-radius:6px;}
            QPushButton:hover{background:rgba(255,255,255,8);}""")
        pb.clicked.connect(self._power)
        bottom.addWidget(pb)
        self._lo.addLayout(bottom)

    def _make_rec(self, name, desc):
        w = QWidget(); w.setFixedHeight(36); w.setCursor(Qt.PointingHandCursor)
        lo = QHBoxLayout(w); lo.setContentsMargins(12, 0, 12, 0); lo.setSpacing(8)
        il = QLabel(); il.setPixmap(get_pixmap("file", 16)); il.setFixedWidth(20); lo.addWidget(il)
        nl = QLabel(name); nl.setFont(QFont("Segoe UI", 9)); nl.setStyleSheet("color:rgba(255,255,255,200);")
        lo.addWidget(nl); lo.addStretch()
        dl = QLabel(desc); dl.setFont(QFont("Segoe UI", 8)); dl.setStyleSheet("color:rgba(255,255,255,60);")
        lo.addWidget(dl)
        return w

    # ═══════════════════════════════════════════════════
    #  RECHERCHE FONCTIONNELLE
    # ═══════════════════════════════════════════════════

    def _on_search_changed(self, text):
        query = text.strip().lower()

        if not query:
            # Revenir à la vue normale
            self._searching = False
            self._header_label.show()
            self._toggle_btn.show()
            self._bottom_section.show()

            if self._showing_all:
                self._scroll.takeWidget()
                self._scroll.setWidget(self._all_w)
            else:
                self._scroll.takeWidget()
                self._scroll.setWidget(self._pinned_w)
            return

        # Mode recherche
        self._searching = True
        self._header_label.setText("Results")
        self._header_label.show()
        self._toggle_btn.hide()
        self._bottom_section.hide()

        # Vider les résultats précédents
        while self._search_lo.count():
            it = self._search_lo.takeAt(0)
            if it.widget(): it.widget().deleteLater()

        # Chercher dans les apps
        results = []
        for info in self._apps_data:
            name = info["name"]
            if query in name.lower():
                score = 0
                if name.lower().startswith(query):
                    score = 2
                elif query in name.lower():
                    score = 1
                results.append((score, info, "App"))

        # Chercher dans les settings keywords
        settings_keywords = {
            "display": ("settings", "Display settings"),
            "brightness": ("settings", "Brightness"),
            "volume": ("settings", "Sound volume"),
            "sound": ("settings", "Sound settings"),
            "wifi": ("settings", "Wi-Fi settings"),
            "network": ("settings", "Network settings"),
            "bluetooth": ("settings", "Bluetooth"),
            "wallpaper": ("settings", "Background wallpaper"),
            "background": ("settings", "Background"),
            "theme": ("settings", "Theme & colors"),
            "color": ("settings", "Colors"),
            "notification": ("settings", "Notifications"),
            "privacy": ("settings", "Privacy & security"),
            "update": ("settings", "Windows Update"),
            "about": ("settings", "About this PC"),
            "account": ("settings", "Accounts"),
            "password": ("settings", "Password settings"),
            "taskbar": ("settings", "Taskbar settings"),
            "mouse": ("settings", "Mouse settings"),
            "keyboard": ("settings", "Keyboard settings"),
            "language": ("settings", "Language settings"),
            "time": ("settings", "Time & date"),
            "date": ("settings", "Date & time"),
            "power": ("settings", "Power settings"),
            "battery": ("settings", "Battery settings"),
            "storage": ("settings", "Storage"),
        }

        for keyword, (app_id, label) in settings_keywords.items():
            if query in keyword:
                results.append((1, {"id": app_id, "name": label, "icon_name": "settings"}, "Setting"))

        # Trier par score
        results.sort(key=lambda x: -x[0])

        # Limiter à 10 résultats
        for score, info, category in results[:10]:
            item = SearchResultItem(info["name"], info.get("icon_name", "file"), category)
            item.clicked.connect(lambda aid=info["id"]: self._launch(aid))
            self._search_lo.addWidget(item)

        if not results:
            no_result = QLabel("  No results found")
            no_result.setFont(QFont("Segoe UI", 10))
            no_result.setStyleSheet("color:rgba(255,255,255,60); padding: 20px;")
            no_result.setFixedHeight(60)
            self._search_lo.addWidget(no_result)

        self._search_lo.addStretch()

        self._scroll.takeWidget()
        self._scroll.setWidget(self._search_w)

    # ═══════════════════════════════════════════════════
    #  VIEWS
    # ═══════════════════════════════════════════════════

    def _toggle_view(self):
        if self._searching: return
        if self._showing_all:
            self._show_pinned()
        else:
            self._show_all()

    def _show_pinned(self):
        self._showing_all = False
        self._header_label.setText("Pinned")
        self._toggle_btn.setText("All apps  →")
        self._bottom_section.show()
        self._scroll.takeWidget()
        self._scroll.setWidget(self._pinned_w)

    def _show_all(self):
        self._showing_all = True
        self._header_label.setText("All apps")
        self._toggle_btn.setText("←  Back")
        self._bottom_section.hide()

        while self._all_lo.count():
            it = self._all_lo.takeAt(0)
            if it.widget(): it.widget().deleteLater()

        for info in sorted(self._apps_data, key=lambda x: x["name"].lower()):
            item = AppListItem(info["name"], info.get("icon_name", "file"))
            item.clicked.connect(lambda aid=info["id"]: self._launch(aid))
            self._all_lo.addWidget(item)
        self._all_lo.addStretch()

        self._scroll.takeWidget()
        self._scroll.setWidget(self._all_w)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 12, 12)
        p.setClipPath(path)
        p.fillRect(self.rect(), QColor(36, 36, 36, 252))
        p.setClipping(False)
        p.setPen(QPen(QColor(255, 255, 255, 10), 1)); p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(QRectF(self.rect()).adjusted(.5, .5, -.5, -.5), 12, 12)
        p.end()

    def set_apps(self, apps):
        self._apps_data = apps
        while self._pinned_grid.count():
            it = self._pinned_grid.takeAt(0)
            if it.widget(): it.widget().deleteLater()
        row, col = 0, 0
        for info in apps:
            tile = AppTile(info["name"], info.get("icon_name", "file"))
            tile.clicked.connect(lambda aid=info["id"]: self._launch(aid))
            self._pinned_grid.addWidget(tile, row, col)
            col += 1
            if col >= 6: col = 0; row += 1

    def _launch(self, aid):
        self.app_clicked.emit(aid)
        self.slide_hide()

    def _power(self):
        from PySide6.QtWidgets import QApplication
        QApplication.quit()