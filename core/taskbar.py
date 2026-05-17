from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QCalendarWidget, QVBoxLayout,
    QLabel, QGraphicsDropShadowEffect, QGridLayout
)
from PySide6.QtCore import (
    Qt, Signal, QTimer, QDateTime, QRect, QRectF, QPoint,
    QPropertyAnimation, QEasingCurve, Property, QLocale
)
from PySide6.QtGui import (
    QFont, QColor, QPainter, QPen, QRadialGradient, QPainterPath
)

from core.icons import get_pixmap
from core.start_menu import StartMenu

ACCENT = QColor(0, 103, 192)
TASKBAR_BG = QColor(29, 29, 29)


# ═══════════════════════════════════════════════════════
#  CHEVRON PANEL — petites icônes cachées
# ═══════════════════════════════════════════════════════

class ChevronPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(180, 48)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.SubWindow)
        self._is_open = False
        self._opacity_val = 0.0
        self._pos_anim = QPropertyAnimation(self, b"pos")
        self._pos_anim.setDuration(200)
        self._pos_anim.setEasingCurve(QEasingCurve.OutQuart)
        self._opa_anim = QPropertyAnimation(self, b"panel_opacity")
        self._opa_anim.setDuration(150)
        self._opa_anim.setEasingCurve(QEasingCurve.OutQuad)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setOffset(0, -2)
        shadow.setColor(QColor(0, 0, 0, 60))
        self.setGraphicsEffect(shadow)
        self._icons = [
            ("volume", "Volume"), ("wifi", "Network"),
            ("battery", "Battery"), ("shield", "Security"),
            ("settings", "Settings"),
        ]
        self._hover_idx = -1
        self.setMouseTracking(True)
        self.hide()

    def get_panel_opacity(self): return self._opacity_val
    def set_panel_opacity(self, v):
        self._opacity_val = max(0.0, min(1.0, v))
        self.setWindowOpacity(self._opacity_val)
    panel_opacity = Property(float, get_panel_opacity, set_panel_opacity)
    def is_open(self): return self._is_open

    def slide_show(self, x, y):
        self._is_open = True
        self.move(x, y + 15)
        self.setWindowOpacity(0.0)
        self.show()
        self.raise_()
        self._pos_anim.stop()
        self._pos_anim.setDuration(200)
        self._pos_anim.setEasingCurve(QEasingCurve.OutQuart)
        self._pos_anim.setStartValue(QPoint(x, y + 15))
        self._pos_anim.setEndValue(QPoint(x, y))
        self._pos_anim.start()
        self._opa_anim.stop()
        self._opa_anim.setStartValue(0.0)
        self._opa_anim.setEndValue(1.0)
        self._opa_anim.start()

    def slide_hide(self):
        if not self._is_open:
            return
        self._is_open = False
        cp = self.pos()
        self._pos_anim.stop()
        self._pos_anim.setDuration(150)
        self._pos_anim.setEasingCurve(QEasingCurve.InQuad)
        self._pos_anim.setStartValue(cp)
        self._pos_anim.setEndValue(QPoint(cp.x(), cp.y() + 15))
        self._pos_anim.start()
        self._opa_anim.stop()
        self._opa_anim.setStartValue(self._opacity_val)
        self._opa_anim.setEndValue(0.0)
        self._opa_anim.start()
        QTimer.singleShot(170, self._finish)

    def _finish(self):
        if not self._is_open:
            self.hide()

    def _icon_rect(self, idx):
        size = 28
        spacing = 4
        x = 8 + idx * (size + spacing)
        y = (self.height() - size) // 2
        return QRect(x, y, size, size)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 8, 8)
        p.setClipPath(path)
        p.fillRect(self.rect(), QColor(40, 40, 40, 250))
        p.setClipping(False)
        p.setPen(QPen(QColor(255, 255, 255, 10), 1))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(QRectF(self.rect()).adjusted(.5, .5, -.5, -.5), 8, 8)
        for i, (icon_name, _) in enumerate(self._icons):
            r = self._icon_rect(i)
            if i == self._hover_idx:
                p.setBrush(QColor(255, 255, 255, 15))
                p.setPen(Qt.NoPen)
                p.drawRoundedRect(QRectF(r), 5, 5)
            px = get_pixmap(icon_name, 16, QColor(255, 255, 255, 180))
            p.drawPixmap(r.x() + 6, r.y() + 6, px)
        p.end()

    def mouseMoveEvent(self, event):
        old = self._hover_idx
        self._hover_idx = -1
        for i in range(len(self._icons)):
            if self._icon_rect(i).contains(event.pos()):
                self._hover_idx = i
                break
        if old != self._hover_idx:
            self.setCursor(Qt.PointingHandCursor if self._hover_idx >= 0 else Qt.ArrowCursor)
            self.update()

    def leaveEvent(self, e):
        self._hover_idx = -1
        self.update()


# ═══════════════════════════════════════════════════════
#  QUICK SETTINGS PANEL — Wi-Fi, Bluetooth, Volume, etc.
# ═══════════════════════════════════════════════════════

class QuickTile(QWidget):
    clicked = Signal()

    def __init__(self, icon_name, label, active=True, parent=None):
        super().__init__(parent)
        self.icon_name = icon_name
        self.label = label
        self.active = active
        self._hover = False
        self.setFixedSize(96, 64)
        self.setCursor(Qt.PointingHandCursor)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        r = QRectF(2, 2, self.width() - 4, self.height() - 4)
        if self.active:
            bg = QColor(ACCENT.red(), ACCENT.green(), ACCENT.blue(), 45 if self._hover else 30)
            border = QColor(ACCENT.red(), ACCENT.green(), ACCENT.blue(), 70)
        elif self._hover:
            bg = QColor(255, 255, 255, 12)
            border = QColor(255, 255, 255, 6)
        else:
            bg = QColor(255, 255, 255, 5)
            border = QColor(255, 255, 255, 4)
        p.setBrush(bg)
        p.setPen(QPen(border, 1))
        p.drawRoundedRect(r, 8, 8)
        px = get_pixmap(self.icon_name, 16, QColor(255, 255, 255, 200 if self.active else 100))
        p.drawPixmap((self.width() - 16) // 2, 14, px)
        p.setFont(QFont("Segoe UI", 8))
        p.setPen(QColor(255, 255, 255, 180 if self.active else 80))
        p.drawText(QRect(0, 36, self.width(), 20), Qt.AlignCenter, self.label)
        p.end()

    def enterEvent(self, e):
        self._hover = True
        self.update()

    def leaveEvent(self, e):
        self._hover = False
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.active = not self.active
            self.update()
            self.clicked.emit()


class QuickSlider(QWidget):
    def __init__(self, icon_name, value=70, parent=None):
        super().__init__(parent)
        self.setFixedHeight(32)
        self._value = value
        self._hover = False
        self._dragging = False
        self.setMouseTracking(True)
        self.setCursor(Qt.PointingHandCursor)
        self._px = get_pixmap(icon_name, 14, QColor(255, 255, 255, 140))

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        p.drawPixmap(6, (h - 14) // 2, self._px)
        tx = 28
        tw = w - tx - 10
        ty = h // 2
        th = 4 if not self._hover else 5
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255, 18))
        p.drawRoundedRect(QRectF(tx, ty - th / 2, tw, th), th / 2, th / 2)
        pw = tw * self._value / 100
        p.setBrush(ACCENT)
        p.drawRoundedRect(QRectF(tx, ty - th / 2, pw, th), th / 2, th / 2)
        if self._hover or self._dragging:
            p.setBrush(QColor(255, 255, 255))
            p.drawEllipse(QRectF(tx + pw - 5, ty - 5, 10, 10))
        p.end()

    def _val(self, x):
        tx = 28
        tw = self.width() - tx - 10
        return max(0, min(100, int((x - tx) / max(tw, 1) * 100)))

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._dragging = True
            self._value = self._val(e.position().x())
            self.update()

    def mouseMoveEvent(self, e):
        self._hover = True
        if self._dragging:
            self._value = self._val(e.position().x())
        self.update()

    def mouseReleaseEvent(self, e):
        self._dragging = False

    def enterEvent(self, e):
        self._hover = True
        self.update()

    def leaveEvent(self, e):
        self._hover = False
        self.update()


class QuickPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(320, 300)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.SubWindow)
        self._is_open = False
        self._opacity_val = 0.0
        self._pos_anim = QPropertyAnimation(self, b"pos")
        self._pos_anim.setDuration(250)
        self._pos_anim.setEasingCurve(QEasingCurve.OutQuart)
        self._opa_anim = QPropertyAnimation(self, b"panel_opacity")
        self._opa_anim.setDuration(200)
        self._opa_anim.setEasingCurve(QEasingCurve.OutQuad)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(30)
        shadow.setOffset(0, -4)
        shadow.setColor(QColor(0, 0, 0, 80))
        self.setGraphicsEffect(shadow)
        self._build()
        self.hide()

    def get_panel_opacity(self): return self._opacity_val
    def set_panel_opacity(self, v):
        self._opacity_val = max(0.0, min(1.0, v))
        self.setWindowOpacity(self._opacity_val)
    panel_opacity = Property(float, get_panel_opacity, set_panel_opacity)
    def is_open(self): return self._is_open

    def _build(self):
        lo = QVBoxLayout(self)
        lo.setContentsMargins(14, 14, 14, 14)
        lo.setSpacing(10)
        grid = QGridLayout()
        grid.setSpacing(5)
        grid.addWidget(QuickTile("wifi", "Wi-Fi", True), 0, 0)
        grid.addWidget(QuickTile("settings", "Bluetooth", False), 0, 1)
        grid.addWidget(QuickTile("globe", "Airplane", False), 0, 2)
        grid.addWidget(QuickTile("battery", "Saver", False), 1, 0)
        grid.addWidget(QuickTile("star", "Night", False), 1, 1)
        grid.addWidget(QuickTile("lock", "VPN", False), 1, 2)
        lo.addLayout(grid)
        sep = QWidget()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background:rgba(255,255,255,6);")
        lo.addWidget(sep)
        bl = QLabel("Brightness")
        bl.setFont(QFont("Segoe UI", 8))
        bl.setStyleSheet("color:rgba(255,255,255,80);")
        lo.addWidget(bl)
        lo.addWidget(QuickSlider("star", 80))
        vl = QLabel("Volume")
        vl.setFont(QFont("Segoe UI", 8))
        vl.setStyleSheet("color:rgba(255,255,255,80);")
        lo.addWidget(vl)
        lo.addWidget(QuickSlider("volume", 65))
        lo.addStretch()

    def slide_show(self, x, y):
        self._is_open = True
        self.move(x, y + 30)
        self.setWindowOpacity(0.0)
        self.show()
        self.raise_()
        self._pos_anim.stop()
        self._pos_anim.setDuration(250)
        self._pos_anim.setEasingCurve(QEasingCurve.OutQuart)
        self._pos_anim.setStartValue(QPoint(x, y + 30))
        self._pos_anim.setEndValue(QPoint(x, y))
        self._pos_anim.start()
        self._opa_anim.stop()
        self._opa_anim.setStartValue(0.0)
        self._opa_anim.setEndValue(1.0)
        self._opa_anim.start()

    def slide_hide(self):
        if not self._is_open:
            return
        self._is_open = False
        cp = self.pos()
        self._pos_anim.stop()
        self._pos_anim.setDuration(180)
        self._pos_anim.setEasingCurve(QEasingCurve.InQuad)
        self._pos_anim.setStartValue(cp)
        self._pos_anim.setEndValue(QPoint(cp.x(), cp.y() + 30))
        self._pos_anim.start()
        self._opa_anim.stop()
        self._opa_anim.setStartValue(self._opacity_val)
        self._opa_anim.setEndValue(0.0)
        self._opa_anim.start()
        QTimer.singleShot(200, self._finish)

    def _finish(self):
        if not self._is_open:
            self.hide()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 12, 12)
        p.setClipPath(path)
        p.fillRect(self.rect(), QColor(36, 36, 36, 250))
        p.setClipping(False)
        p.setPen(QPen(QColor(255, 255, 255, 10), 1))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(QRectF(self.rect()).adjusted(.5, .5, -.5, -.5), 12, 12)
        p.end()


# ═══════════════════════════════════════════════════════
#  CLOCK PANEL
# ═══════════════════════════════════════════════════════

class ClockPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(340, 400)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.SubWindow)
        self._is_open = False
        self._opacity_val = 0.0
        self._pos_anim = QPropertyAnimation(self, b"pos")
        self._pos_anim.setDuration(250)
        self._pos_anim.setEasingCurve(QEasingCurve.OutQuart)
        self._opa_anim = QPropertyAnimation(self, b"panel_opacity")
        self._opa_anim.setDuration(200)
        self._opa_anim.setEasingCurve(QEasingCurve.OutQuad)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(30)
        shadow.setOffset(0, -4)
        shadow.setColor(QColor(0, 0, 0, 80))
        self.setGraphicsEffect(shadow)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.update)
        self._timer.start(1000)
        self._build()
        self.hide()

    def get_panel_opacity(self): return self._opacity_val
    def set_panel_opacity(self, v):
        self._opacity_val = max(0.0, min(1.0, v))
        self.setWindowOpacity(self._opacity_val)
    panel_opacity = Property(float, get_panel_opacity, set_panel_opacity)
    def is_open(self): return self._is_open

    def _build(self):
        lo = QVBoxLayout(self)
        lo.setContentsMargins(16, 16, 16, 16)
        lo.setSpacing(12)
        self._time_label = QLabel()
        self._time_label.setFont(QFont("Segoe UI Light", 42))
        self._time_label.setStyleSheet("color:white;")
        self._time_label.setAlignment(Qt.AlignCenter)
        lo.addWidget(self._time_label)
        self._date_label = QLabel()
        self._date_label.setFont(QFont("Segoe UI", 12))
        self._date_label.setStyleSheet("color:rgba(255,255,255,140);")
        self._date_label.setAlignment(Qt.AlignCenter)
        lo.addWidget(self._date_label)
        sep = QWidget()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background:rgba(255,255,255,8);")
        lo.addWidget(sep)
        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(False)
        self.calendar.setNavigationBarVisible(True)
        self.calendar.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        self.calendar.setStyleSheet("""
            QCalendarWidget{background:transparent;color:white;}
            QCalendarWidget QToolButton{color:white;background:transparent;border:none;border-radius:4px;padding:4px 8px;font-size:12px;}
            QCalendarWidget QToolButton:hover{background:rgba(255,255,255,10);}
            QCalendarWidget QMenu{background:#2d2d2d;color:white;border:1px solid rgba(255,255,255,12);}
            QCalendarWidget QSpinBox{background:rgba(255,255,255,8);color:white;border:1px solid rgba(255,255,255,10);border-radius:4px;}
            QCalendarWidget QAbstractItemView{background:transparent;color:rgba(255,255,255,200);selection-background-color:rgba(0,103,192,180);selection-color:white;font-size:12px;outline:none;}
            QCalendarWidget QAbstractItemView:disabled{color:rgba(255,255,255,40);}
            QCalendarWidget QWidget#qt_calendar_navigationbar{background:transparent;}
        """)
        lo.addWidget(self.calendar)

    def _update_time(self):
        now = QDateTime.currentDateTime()
        self._time_label.setText(now.toString("HH:mm:ss"))
        locale = QLocale(QLocale.English)
        self._date_label.setText(locale.toString(now.date(), "dddd, MMMM d, yyyy"))

    def slide_show(self, x, y):
        self._is_open = True
        self._update_time()
        self.move(x, y + 30)
        self.setWindowOpacity(0.0)
        self.show()
        self.raise_()
        self._pos_anim.stop()
        self._pos_anim.setDuration(250)
        self._pos_anim.setEasingCurve(QEasingCurve.OutQuart)
        self._pos_anim.setStartValue(QPoint(x, y + 30))
        self._pos_anim.setEndValue(QPoint(x, y))
        self._pos_anim.start()
        self._opa_anim.stop()
        self._opa_anim.setStartValue(0.0)
        self._opa_anim.setEndValue(1.0)
        self._opa_anim.start()

    def slide_hide(self):
        if not self._is_open:
            return
        self._is_open = False
        cp = self.pos()
        self._pos_anim.stop()
        self._pos_anim.setDuration(180)
        self._pos_anim.setEasingCurve(QEasingCurve.InQuad)
        self._pos_anim.setStartValue(cp)
        self._pos_anim.setEndValue(QPoint(cp.x(), cp.y() + 30))
        self._pos_anim.start()
        self._opa_anim.stop()
        self._opa_anim.setStartValue(self._opacity_val)
        self._opa_anim.setEndValue(0.0)
        self._opa_anim.start()
        QTimer.singleShot(200, self._finish)

    def _finish(self):
        if not self._is_open:
            self.hide()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 12, 12)
        p.setClipPath(path)
        p.fillRect(self.rect(), QColor(36, 36, 36, 250))
        p.setClipping(False)
        p.setPen(QPen(QColor(255, 255, 255, 10), 1))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(QRectF(self.rect()).adjusted(.5, .5, -.5, -.5), 12, 12)
        p.end()
        self._update_time()


# ═══════════════════════════════════════════════════════
#  TASKBAR APP BUTTON
# ═══════════════════════════════════════════════════════

class TaskbarAppButton(QWidget):
    clicked = Signal()

    def __init__(self, app_id, name, icon_name, parent=None):
        super().__init__(parent)
        self.app_id = app_id
        self.active = False
        self._pixmap = get_pixmap(icon_name, 22, QColor(255, 255, 255))
        self.setFixedSize(46, 40)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(name)
        self._hover_val = 0.0
        self._press_val = 1.0
        self._ha = QPropertyAnimation(self, b"hv")
        self._ha.setDuration(120)
        self._ha.setEasingCurve(QEasingCurve.OutQuad)
        self._pa = QPropertyAnimation(self, b"pv")
        self._pa.setDuration(80)
        self._pa.setEasingCurve(QEasingCurve.OutQuad)

    def get_hv(self): return self._hover_val
    def set_hv(self, v): self._hover_val = v; self.update()
    hv = Property(float, get_hv, set_hv)

    def get_pv(self): return self._press_val
    def set_pv(self, v): self._press_val = v; self.update()
    pv = Property(float, get_pv, set_pv)

    def set_active(self, v):
        self.active = v
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        if self._press_val != 1.0:
            p.translate(w / 2, h / 2)
            p.scale(self._press_val, self._press_val)
            p.translate(-w / 2, -h / 2)
        if self._hover_val > 0.01:
            p.setBrush(QColor(255, 255, 255, int(15 * self._hover_val)))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(3, 3, w - 6, h - 6, 5, 5)
        p.drawPixmap((w - 22) // 2, (h - 22) // 2 - 1, self._pixmap)
        if self.active:
            p.setPen(Qt.NoPen)
            p.setBrush(ACCENT)
            p.drawRoundedRect((w - 16) // 2, h - 4, 16, 3, 1.5, 1.5)
        p.end()

    def enterEvent(self, e):
        self._ha.stop()
        self._ha.setStartValue(self._hover_val)
        self._ha.setEndValue(1.0)
        self._ha.start()

    def leaveEvent(self, e):
        self._ha.stop()
        self._ha.setStartValue(self._hover_val)
        self._ha.setEndValue(0.0)
        self._ha.start()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._pa.stop()
            self._pa.setStartValue(1.0)
            self._pa.setEndValue(0.88)
            self._pa.start()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._pa.stop()
            self._pa.setStartValue(self._press_val)
            self._pa.setEndValue(1.0)
            self._pa.setDuration(150)
            self._pa.setEasingCurve(QEasingCurve.OutBack)
            self._pa.start()
            self.clicked.emit()
            QTimer.singleShot(200, lambda: (
                self._pa.setDuration(80),
                self._pa.setEasingCurve(QEasingCurve.OutQuad)
            ))


# ═══════════════════════════════════════════════════════
#  TASKBAR
# ═══════════════════════════════════════════════════════

class Taskbar(QWidget):
    app_launched = Signal(str)

    def __init__(self, desktop, parent=None):
        super().__init__(parent)
        self.desktop = desktop
        self.running_buttons = {}
        self.setFixedHeight(48)
        self.setMouseTracking(True)

        self._start_hover = False
        self._start_pressed = False
        self._start_hover_val = 0.0
        self._start_press_val = 1.0
        self._start_glow_val = 0.0

        self._shv = QPropertyAnimation(self, b"shv")
        self._shv.setDuration(150)
        self._shv.setEasingCurve(QEasingCurve.OutQuad)
        self._spv = QPropertyAnimation(self, b"spv")
        self._spv.setDuration(100)
        self._spv.setEasingCurve(QEasingCurve.OutQuad)
        self._sgv = QPropertyAnimation(self, b"sgv")
        self._sgv.setDuration(350)
        self._sgv.setEasingCurve(QEasingCurve.OutQuad)

        # Layout
        lo = QHBoxLayout(self)
        lo.setContentsMargins(0, 0, 0, 0)
        lo.setSpacing(0)
        lo.addStretch()

        self.center = QWidget()
        cl = QHBoxLayout(self.center)
        cl.setContentsMargins(6, 4, 6, 4)
        cl.setSpacing(0)

        # Spacer bouton Windows
        spacer = QWidget()
        spacer.setFixedSize(50, 40)
        spacer.setAttribute(Qt.WA_TransparentForMouseEvents)
        cl.addWidget(spacer)

        # File Explorer épinglé
        self._explorer_btn = TaskbarAppButton("file_explorer", "File Explorer", "explo")
        self._explorer_btn.clicked.connect(lambda: self.app_launched.emit("file_explorer"))
        cl.addWidget(self._explorer_btn)

        # Séparateur
        sep = QWidget()
        sep.setFixedSize(1, 22)
        sep.setStyleSheet("background:rgba(255,255,255,8);")
        cl.addWidget(sep)

        # Apps en cours
        self.apps_layout = QHBoxLayout()
        self.apps_layout.setSpacing(2)
        self.apps_layout.setContentsMargins(4, 0, 0, 0)
        cl.addLayout(self.apps_layout)

        lo.addWidget(self.center)
        lo.addStretch()

        # System tray
        self.tray = SystemTray(self)
        lo.addWidget(self.tray)

        # Panels
        self.start_menu = StartMenu(self.desktop)
        self.start_menu.app_clicked.connect(self.app_launched.emit)
        self.clock_panel = ClockPanel(self.desktop)
        self.chevron_panel = ChevronPanel(self.desktop)
        self.quick_panel = QuickPanel(self.desktop)

        self._win_px = get_pixmap("windows", 23)

    # Properties
    def get_shv(self): return self._start_hover_val
    def set_shv(self, v): self._start_hover_val = v; self.update()
    shv = Property(float, get_shv, set_shv)

    def get_spv(self): return self._start_press_val
    def set_spv(self, v): self._start_press_val = v; self.update()
    spv = Property(float, get_spv, set_spv)

    def get_sgv(self): return self._start_glow_val
    def set_sgv(self, v): self._start_glow_val = v; self.update()
    sgv = Property(float, get_sgv, set_sgv)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), TASKBAR_BG)
        p.setPen(QColor(255, 255, 255, 5))
        p.drawLine(0, 0, self.width(), 0)

        cx = self.center.x()
        sr = QRectF(cx + 3, 4, 44, 40)
        scx = sr.x() + 22
        scy = sr.y() + 20

        p.save()
        if self._start_press_val != 1.0:
            p.translate(scx, scy)
            p.scale(self._start_press_val, self._start_press_val)
            p.translate(-scx, -scy)

        if self._start_glow_val > 0.01:
            glow = QRadialGradient(scx, scy, 28)
            glow.setColorAt(0.0, QColor(
                ACCENT.red(), ACCENT.green(), ACCENT.blue(),
                int(50 * self._start_glow_val)
            ))
            glow.setColorAt(1.0, QColor(0, 0, 0, 0))
            p.setBrush(glow)
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(QRectF(scx - 26, scy - 20, 52, 40), 10, 10)

        if self._start_hover_val > 0.01:
            p.setBrush(QColor(255, 255, 255, int(14 * self._start_hover_val)))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(sr.adjusted(2, 2, -2, -2), 5, 5)

        ps = self._win_px.width()
        p.drawPixmap(int(scx - ps / 2), int(scy - ps / 2), self._win_px)
        p.restore()
        p.end()

    def _sr(self):
        return QRect(self.center.x() + 3, 4, 44, 40)

    # Mouse events
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self._sr().contains(event.pos()):
            self._start_pressed = True
            self._spv.stop()
            self._spv.setStartValue(1.0)
            self._spv.setEndValue(0.85)
            self._spv.setDuration(100)
            self._spv.setEasingCurve(QEasingCurve.OutQuad)
            self._spv.start()
            self._sgv.stop()
            self._sgv.setStartValue(1.0)
            self._sgv.setEndValue(0.0)
            self._sgv.start()
            return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if self._start_pressed:
            self._start_pressed = False
            self._spv.stop()
            self._spv.setStartValue(self._start_press_val)
            self._spv.setEndValue(1.0)
            self._spv.setDuration(200)
            self._spv.setEasingCurve(QEasingCurve.OutBack)
            self._spv.start()
            QTimer.singleShot(250, lambda: (
                self._spv.setDuration(100),
                self._spv.setEasingCurve(QEasingCurve.OutQuad)
            ))
            if self._sr().contains(event.pos()):
                self.toggle_start_menu()
            return
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        old = self._start_hover
        self._start_hover = self._sr().contains(event.pos())
        if self._start_hover != old:
            self._shv.stop()
            self._shv.setStartValue(self._start_hover_val)
            self._shv.setEndValue(1.0 if self._start_hover else 0.0)
            self._shv.start()

    def leaveEvent(self, e):
        if self._start_hover:
            self._start_hover = False
            self._shv.stop()
            self._shv.setStartValue(self._start_hover_val)
            self._shv.setEndValue(0.0)
            self._shv.start()

    # Panel toggles — chacun ferme les autres, toggle correct
    def toggle_start_menu(self):
        was = self.start_menu.is_open()
        if self.clock_panel.is_open(): self.clock_panel.slide_hide()
        if self.chevron_panel.is_open(): self.chevron_panel.slide_hide()
        if self.quick_panel.is_open(): self.quick_panel.slide_hide()
        if was:
            self.start_menu.slide_hide()
        else:
            dr = self.desktop.geometry()
            mw, mh = self.start_menu.width(), self.start_menu.height()
            self.start_menu.slide_show(
                (dr.width() - mw) // 2,
                dr.height() - self.height() - mh - 12
            )

    def toggle_clock_panel(self):
        was = self.clock_panel.is_open()
        if self.start_menu.is_open(): self.start_menu.slide_hide()
        if self.chevron_panel.is_open(): self.chevron_panel.slide_hide()
        if self.quick_panel.is_open(): self.quick_panel.slide_hide()
        if was:
            self.clock_panel.slide_hide()
        else:
            dr = self.desktop.geometry()
            pw, ph = self.clock_panel.width(), self.clock_panel.height()
            self.clock_panel.slide_show(
                dr.width() - pw - 8,
                dr.height() - self.height() - ph - 12
            )

    def toggle_chevron_panel(self):
        was = self.chevron_panel.is_open()
        if self.start_menu.is_open(): self.start_menu.slide_hide()
        if self.clock_panel.is_open(): self.clock_panel.slide_hide()
        if self.quick_panel.is_open(): self.quick_panel.slide_hide()
        if was:
            self.chevron_panel.slide_hide()
        else:
            dr = self.desktop.geometry()
            tg = self.tray.mapToGlobal(QPoint(0, 0))
            dp = self.desktop.mapFromGlobal(tg)
            pw, ph = self.chevron_panel.width(), self.chevron_panel.height()
            self.chevron_panel.slide_show(
                dp.x(),
                dr.height() - self.height() - ph - 8
            )

    def toggle_quick_panel(self):
        was = self.quick_panel.is_open()
        if self.start_menu.is_open(): self.start_menu.slide_hide()
        if self.clock_panel.is_open(): self.clock_panel.slide_hide()
        if self.chevron_panel.is_open(): self.chevron_panel.slide_hide()
        if was:
            self.quick_panel.slide_hide()
        else:
            dr = self.desktop.geometry()
            pw, ph = self.quick_panel.width(), self.quick_panel.height()
            self.quick_panel.slide_show(
                dr.width() - pw - 8,
                dr.height() - self.height() - ph - 12
            )

    def close_start_menu(self):
        if self.start_menu.is_open(): self.start_menu.slide_hide()
        if self.clock_panel.is_open(): self.clock_panel.slide_hide()
        if self.chevron_panel.is_open(): self.chevron_panel.slide_hide()
        if self.quick_panel.is_open(): self.quick_panel.slide_hide()

    def set_available_apps(self, apps):
        self.start_menu.set_apps(apps)

    def add_running_app(self, app_id, name, icon_name):
        if app_id not in self.running_buttons:
            btn = TaskbarAppButton(app_id, name, icon_name)
            btn.set_active(True)
            btn.clicked.connect(lambda: self._click(app_id))
            self.apps_layout.addWidget(btn)
            self.running_buttons[app_id] = btn

    def remove_running_app(self, app_id):
        if app_id in self.running_buttons:
            btn = self.running_buttons.pop(app_id)
            self.apps_layout.removeWidget(btn)
            btn.deleteLater()

    def _click(self, app_id):
        self.desktop.window_manager.toggle_window(app_id)


# ═══════════════════════════════════════════════════════
#  SYSTEM TRAY
# ═══════════════════════════════════════════════════════

class SystemTray(QWidget):
    def __init__(self, taskbar, parent=None):
        super().__init__(parent)
        self._taskbar = taskbar
        self.setFixedWidth(210)
        self.setMouseTracking(True)
        self._chevron_hover = False
        self._icons_hover = False
        self._clock_hover = False
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.update)
        self._timer.start(1000)
        self._vol = get_pixmap("volume", 14, QColor(255, 255, 255, 180))
        self._wifi = get_pixmap("wifi", 14, QColor(255, 255, 255, 180))
        self._bat = get_pixmap("battery", 14, QColor(255, 255, 255, 180))
        self._chev = get_pixmap("chevron_up", 10, QColor(255, 255, 255, 120))

    def _chevron_rect(self):
        return QRect(0, 4, 24, self.height() - 8)

    def _icons_rect(self):
        return QRect(26, 4, 72, self.height() - 8)

    def _clock_rect(self):
        return QRect(104, 2, 96, self.height() - 4)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        h = self.height()

        # Chevron ∧
        cr = self._chevron_rect()
        if self._chevron_hover:
            p.setBrush(QColor(255, 255, 255, 10))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(QRectF(cr), 4, 4)
        p.drawPixmap(cr.x() + 7, (h - 10) // 2, self._chev)

        # System icons (wifi/vol/bat) → Quick Panel
        ir = self._icons_rect()
        if self._icons_hover:
            p.setBrush(QColor(255, 255, 255, 10))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(QRectF(ir), 4, 4)
        x = ir.x() + 6
        for px in [self._vol, self._wifi, self._bat]:
            p.drawPixmap(x, (h - 14) // 2, px)
            x += 22

        # Clock → Clock Panel
        clr = self._clock_rect()
        if self._clock_hover:
            p.setBrush(QColor(255, 255, 255, 10))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(QRectF(clr), 4, 4)
        now = QDateTime.currentDateTime()
        p.setPen(QColor(255, 255, 255, 200))
        p.setFont(QFont("Segoe UI", 9))
        p.drawText(
            QRect(clr.x(), 4, clr.width(), h // 2 - 2),
            Qt.AlignCenter, now.toString("HH:mm")
        )
        p.setFont(QFont("Segoe UI", 8))
        p.drawText(
            QRect(clr.x(), h // 2 - 2, clr.width(), h // 2),
            Qt.AlignCenter, now.toString("dd/MM/yyyy")
        )

        # Show desktop line
        p.setPen(QColor(255, 255, 255, 20))
        p.drawLine(self.width() - 4, 10, self.width() - 4, h - 10)
        p.end()

    def mouseMoveEvent(self, event):
        pos = event.pos()
        old = (self._chevron_hover, self._icons_hover, self._clock_hover)
        self._chevron_hover = self._chevron_rect().contains(pos)
        self._icons_hover = self._icons_rect().contains(pos)
        self._clock_hover = self._clock_rect().contains(pos)
        new = (self._chevron_hover, self._icons_hover, self._clock_hover)
        if old != new:
            self.setCursor(Qt.PointingHandCursor if any(new) else Qt.ArrowCursor)
            self.update()

    def leaveEvent(self, e):
        self._chevron_hover = False
        self._icons_hover = False
        self._clock_hover = False
        self.update()

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        pos = event.pos()
        if self._chevron_rect().contains(pos):
            self._taskbar.toggle_chevron_panel()
        elif self._icons_rect().contains(pos):
            self._taskbar.toggle_quick_panel()
        elif self._clock_rect().contains(pos):
            self._taskbar.toggle_clock_panel()