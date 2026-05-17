"""
WinPy11 Planetarium
Ciel étoilé interactif avec constellations, rotation temps réel.
"""
import os
import sys
import math
import time
import random

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QSizePolicy, QSlider, QLabel
)
from PySide6.QtCore import (
    Qt, Signal, QTimer, QRectF, QRect, QPointF,
    QPropertyAnimation, QEasingCurve, Property
)
from PySide6.QtGui import (
    QFont, QColor, QPainter, QPen, QPainterPath,
    QRadialGradient, QLinearGradient, QBrush
)

from core.icons import get_icon, get_pixmap

ACCENT = QColor(0, 120, 255)


# ═══════════════════════════════════════════════════════
#  STAR CATALOG
# ═══════════════════════════════════════════════════════

BRIGHT_STARS = [
    ("Sirius", 6.752, -16.72, -1.46),
    ("Canopus", 6.399, -52.70, -0.74),
    ("Arcturus", 14.261, 19.18, -0.05),
    ("Vega", 18.616, 38.78, 0.03),
    ("Capella", 5.278, 46.00, 0.08),
    ("Rigel", 5.242, -8.20, 0.13),
    ("Procyon", 7.655, 5.22, 0.34),
    ("Betelgeuse", 5.919, 7.41, 0.42),
    ("Altair", 19.846, 8.87, 0.76),
    ("Aldebaran", 4.599, 16.51, 0.86),
    ("Antares", 16.490, -26.43, 0.96),
    ("Spica", 13.420, -11.16, 0.97),
    ("Pollux", 7.755, 28.03, 1.14),
    ("Fomalhaut", 22.961, -29.62, 1.16),
    ("Deneb", 20.690, 45.28, 1.25),
    ("Regulus", 10.140, 11.97, 1.35),
    ("Castor", 7.577, 31.89, 1.58),
    ("Bellatrix", 5.419, 6.35, 1.64),
    ("Alnilam", 5.604, -1.20, 1.69),
    ("Alnitak", 5.679, -1.94, 1.77),
    ("Mintaka", 5.533, -0.30, 2.23),
    ("Saiph", 5.796, -9.67, 2.09),
    ("Dubhe", 11.062, 61.75, 1.79),
    ("Merak", 11.031, 56.38, 2.37),
    ("Phecda", 11.897, 53.69, 2.44),
    ("Megrez", 12.257, 57.03, 3.31),
    ("Alioth", 12.900, 55.96, 1.77),
    ("Mizar", 13.399, 54.93, 2.27),
    ("Alkaid", 13.792, 49.31, 1.86),
    ("Polaris", 2.530, 89.26, 1.98),
    ("Schedar", 0.675, 56.54, 2.23),
    ("Caph", 0.153, 59.15, 2.27),
    ("Mirfak", 3.405, 49.86, 1.80),
    ("Algol", 3.136, 40.96, 2.12),
    ("Hamal", 2.120, 23.46, 2.00),
    ("Diphda", 0.727, -17.99, 2.02),
    ("Achernar", 1.629, -57.24, 0.46),
    ("Acrux", 12.443, -63.10, 0.76),
    ("Mimosa", 12.795, -59.69, 1.25),
    ("Shaula", 17.560, -37.10, 1.63),
    ("Rasalhague", 17.582, 12.56, 2.07),
    ("Eltanin", 17.943, 51.49, 2.23),
    ("Kochab", 14.845, 74.16, 2.08),
    ("Alphard", 9.460, -8.66, 1.98),
    ("Nunki", 18.921, -26.30, 2.02),
    ("Alderamin", 21.310, 62.59, 2.51),
    ("Enif", 21.736, 9.88, 2.39),
    ("Markab", 23.079, 15.21, 2.49),
    ("Scheat", 23.063, 28.08, 2.42),
    ("Algenib", 0.220, 15.18, 2.83),
]

CONSTELLATIONS = [
    ("Orion", [
        ("Betelgeuse", "Bellatrix"), ("Bellatrix", "Mintaka"),
        ("Mintaka", "Alnilam"), ("Alnilam", "Alnitak"),
        ("Alnitak", "Saiph"), ("Saiph", "Rigel"),
        ("Rigel", "Mintaka"), ("Betelgeuse", "Alnitak"),
    ]),
    ("Big Dipper", [
        ("Dubhe", "Merak"), ("Merak", "Phecda"),
        ("Phecda", "Megrez"), ("Megrez", "Alioth"),
        ("Alioth", "Mizar"), ("Mizar", "Alkaid"),
        ("Megrez", "Dubhe"),
    ]),
    ("Cassiopeia", [
        ("Schedar", "Caph"), ("Schedar", "Mirfak"),
    ]),
    ("Pegasus", [
        ("Markab", "Scheat"), ("Scheat", "Algenib"),
        ("Algenib", "Markab"),
    ]),
    ("Summer Triangle", [
        ("Vega", "Deneb"), ("Deneb", "Altair"), ("Altair", "Vega"),
    ]),
]


class StarCatalog:
    def __init__(self):
        self.stars = []
        self.bg_stars = []
        self.constellation_lines = []
        self._map = {}
        self._build()

    def _build(self):
        for name, ra_h, dec_deg, mag in BRIGHT_STARS:
            ra = math.radians(ra_h * 15.0)
            dec = math.radians(dec_deg)
            x = math.cos(dec) * math.cos(ra)
            y = math.sin(dec)
            z = math.cos(dec) * math.sin(ra)
            brightness = max(0.3, min(1.0, 1.0 - (mag + 1.5) / 5.0))
            radius = max(1.0, 4.0 - mag * 0.8)

            if mag < 0:
                color = QColor(200, 220, 255)
            elif mag < 1:
                color = QColor(255, 255, 240)
            elif mag < 2:
                color = QColor(255, 240, 220)
            else:
                color = QColor(255, 220, 180)

            star = {
                'name': name, 'x': x, 'y': y, 'z': z,
                'mag': mag, 'brightness': brightness,
                'radius': radius, 'color': color, 'ra': ra, 'dec': dec,
            }
            self.stars.append(star)
            self._map[name] = star

        rng = random.Random(42)
        for _ in range(2000):
            ra = rng.uniform(0, 2 * math.pi)
            dec = math.asin(rng.uniform(-1, 1))
            x = math.cos(dec) * math.cos(ra)
            y = math.sin(dec)
            z = math.cos(dec) * math.sin(ra)
            self.bg_stars.append({
                'x': x, 'y': y, 'z': z,
                'brightness': rng.uniform(0.1, 0.5),
                'radius': rng.uniform(0.3, 1.2),
            })

        for name, pairs in CONSTELLATIONS:
            lines = []
            for s1, s2 in pairs:
                if s1 in self._map and s2 in self._map:
                    lines.append((self._map[s1], self._map[s2]))
            self.constellation_lines.append((name, lines))

    def project(self, star, rot_x, rot_y, w, h):
        x, y, z = star['x'], star['y'], star['z']
        cry, sry = math.cos(rot_y), math.sin(rot_y)
        x2 = x * cry - z * sry
        z2 = x * sry + z * cry
        crx, srx = math.cos(rot_x), math.sin(rot_x)
        y2 = y * crx - z2 * srx
        z3 = y * srx + z2 * crx
        if z3 < 0.01:
            return None
        fov = 1.8
        sx = w / 2 + x2 / z3 * w * fov / 2
        sy = h / 2 - y2 / z3 * h * fov / 2
        return sx, sy, z3


# ═══════════════════════════════════════════════════════
#  SKY VIEWPORT
# ═══════════════════════════════════════════════════════

class SkyViewport(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)

        self.catalog = None
        self.rot_x = 0.3
        self.rot_y = 0.0
        self.show_constellations = True
        self.show_names = True
        self.time_speed = 0.0
        self.time_offset = 0.0

        self._last_m = None
        self._dragging = False
        self._loading = True
        self._twinkle = 0.0

        self._spinner_angle = 0.0
        self._spinner_anim = QPropertyAnimation(self, b"spinner_angle")
        self._spinner_anim.setDuration(1200)
        self._spinner_anim.setStartValue(0.0)
        self._spinner_anim.setEndValue(360.0)
        self._spinner_anim.setLoopCount(-1)
        self._spinner_anim.setEasingCurve(QEasingCurve.Linear)
        self._spinner_anim.start()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(16)

    def get_spinner_angle(self):
        return self._spinner_angle

    def set_spinner_angle(self, v):
        self._spinner_angle = v
        if self._loading:
            self.update()

    spinner_angle = Property(float, get_spinner_angle, set_spinner_angle)

    def set_catalog(self, catalog):
        self.catalog = catalog
        self._loading = False
        self._spinner_anim.stop()
        self.update()

    def _tick(self):
        if self._loading:
            return
        self._twinkle += 0.03
        if self.time_speed != 0:
            self.time_offset += self.time_speed * 0.002
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        w, h = self.width(), self.height()

        # Sky background
        bg = QRadialGradient(w / 2, h / 2, max(w, h) * 0.7)
        bg.setColorAt(0.0, QColor(8, 10, 18))
        bg.setColorAt(0.5, QColor(4, 5, 12))
        bg.setColorAt(1.0, QColor(1, 2, 6))
        p.fillRect(self.rect(), QBrush(bg))

        # Horizon glow
        hz = QLinearGradient(0, h * 0.7, 0, h)
        hz.setColorAt(0.0, QColor(0, 0, 0, 0))
        hz.setColorAt(0.6, QColor(10, 20, 50, 20))
        hz.setColorAt(1.0, QColor(15, 25, 60, 40))
        p.fillRect(self.rect(), QBrush(hz))

        if self._loading:
            self._draw_loading(p, w, h)
            p.end()
            return

        if not self.catalog:
            p.end()
            return

        ry = self.rot_y + self.time_offset
        rx = self.rot_x

        # Background stars
        for s in self.catalog.bg_stars:
            proj = self.catalog.project(s, rx, ry, w, h)
            if not proj:
                continue
            sx, sy, _ = proj
            if sx < -5 or sx > w + 5 or sy < -5 or sy > h + 5:
                continue
            tw = 0.7 + 0.3 * math.sin(self._twinkle * 2.3 + s['x'] * 100 + s['y'] * 73)
            alpha = int(s['brightness'] * 255 * tw)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(220, 230, 255, max(10, min(255, alpha))))
            p.drawEllipse(QPointF(sx, sy), s['radius'], s['radius'])

        # Constellation lines
        if self.show_constellations:
            for name, lines in self.catalog.constellation_lines:
                name_drawn = False
                for s1, s2 in lines:
                    p1 = self.catalog.project(s1, rx, ry, w, h)
                    p2 = self.catalog.project(s2, rx, ry, w, h)
                    if p1 and p2:
                        sx1, sy1, _ = p1
                        sx2, sy2, _ = p2
                        if (0 <= sx1 <= w or 0 <= sx2 <= w) and (0 <= sy1 <= h or 0 <= sy2 <= h):
                            p.setPen(QPen(QColor(80, 130, 200, 40), 1))
                            p.drawLine(QPointF(sx1, sy1), QPointF(sx2, sy2))

                            # Constellation name at midpoint of first line
                            if not name_drawn and self.show_names:
                                mx = (sx1 + sx2) / 2
                                my = (sy1 + sy2) / 2 - 12
                                p.setFont(QFont("Segoe UI", 7))
                                p.setPen(QColor(100, 140, 220, 60))
                                p.drawText(QPointF(mx - 20, my), name)
                                name_drawn = True

        # Bright stars
        for star in self.catalog.stars:
            proj = self.catalog.project(star, rx, ry, w, h)
            if not proj:
                continue
            sx, sy, _ = proj
            if sx < -20 or sx > w + 20 or sy < -20 or sy > h + 20:
                continue

            tw = 0.8 + 0.2 * math.sin(self._twinkle * 1.7 + star['ra'] * 50)
            r = star['radius'] * tw
            color = star['color']
            alpha = int(star['brightness'] * 255 * tw)

            # Glow halo
            if r > 1.5:
                glow = QRadialGradient(sx, sy, r * 4)
                glow.setColorAt(0.0, QColor(color.red(), color.green(), color.blue(), max(5, alpha // 4)))
                glow.setColorAt(1.0, QColor(0, 0, 0, 0))
                p.setPen(Qt.NoPen)
                p.setBrush(QBrush(glow))
                p.drawEllipse(QPointF(sx, sy), r * 4, r * 4)

            # Star body
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(color.red(), color.green(), color.blue(), max(30, min(255, alpha))))
            p.drawEllipse(QPointF(sx, sy), r, r)

            # Bright center
            if star['mag'] < 1.5:
                p.setBrush(QColor(255, 255, 255, min(255, alpha + 50)))
                p.drawEllipse(QPointF(sx, sy), max(0.5, r * 0.4), max(0.5, r * 0.4))

            # Star name
            if self.show_names and star['mag'] < 1.8:
                p.setFont(QFont("Segoe UI", 8))
                p.setPen(QColor(180, 200, 255, max(30, min(150, alpha))))
                p.drawText(QPointF(sx + r + 4, sy + 3), star['name'])

        # Compass
        self._draw_compass(p, w, h)

        # Info
        p.setFont(QFont("Segoe UI", 8))
        p.setPen(QColor(255, 255, 255, 50))
        visible = sum(1 for s in self.catalog.stars if self.catalog.project(s, rx, ry, w, h))
        p.drawText(QRect(10, 8, w - 20, 14), Qt.AlignRight,
                    f"{visible} bright stars visible  ·  {len(self.catalog.bg_stars)} background")

        p.end()

    def _draw_loading(self, p, w, h):
        cx, cy = w // 2, h // 2

        p.setFont(QFont("Segoe UI Light", 28))
        p.setPen(QColor(255, 255, 255, 180))
        p.drawText(QRect(0, cy - 80, w, 40), Qt.AlignCenter, "✦")

        p.setFont(QFont("Segoe UI Light", 16))
        p.setPen(QColor(255, 255, 255, 120))
        p.drawText(QRect(0, cy - 40, w, 30), Qt.AlignCenter, "P L A N E T A R I U M")

        p.setPen(QPen(QColor(255, 255, 255, 15), 2))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QPointF(cx, cy + 30), 16, 16)
        p.setPen(QPen(ACCENT, 2))
        p.drawArc(QRect(cx - 16, cy + 14, 32, 32), int(self._spinner_angle * 16), 90 * 16)

        p.setFont(QFont("Segoe UI", 9))
        p.setPen(QColor(255, 255, 255, 60))
        p.drawText(QRect(0, cy + 60, w, 20), Qt.AlignCenter, "Mapping stars...")

    def _draw_compass(self, p, w, h):
        cx, cy = 40, h - 40
        r = 22

        p.setPen(QPen(QColor(255, 255, 255, 20), 1))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QPointF(cx, cy), r, r)

        angle = -self.rot_y - self.time_offset
        nx = cx + math.sin(angle) * (r - 4)
        ny = cy - math.cos(angle) * (r - 4)
        p.setPen(QPen(QColor(255, 80, 80, 140), 1.5))
        p.drawLine(QPointF(cx, cy), QPointF(nx, ny))
        p.setFont(QFont("Segoe UI", 7))
        p.setPen(QColor(255, 80, 80, 100))
        p.drawText(QPointF(nx - 3, ny - 4), "N")

    # Mouse
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._last_m = event.position()
            self._dragging = True

    def mouseMoveEvent(self, event):
        if self._dragging and self._last_m:
            dx = event.position().x() - self._last_m.x()
            dy = event.position().y() - self._last_m.y()
            self._last_m = event.position()
            self.rot_y -= dx * 0.004
            self.rot_x = max(-math.pi / 2 + 0.1, min(math.pi / 2 - 0.1, self.rot_x + dy * 0.004))

    def mouseReleaseEvent(self, event):
        self._dragging = False


# ═══════════════════════════════════════════════════════
#  DOCK WIDGETS
# ═══════════════════════════════════════════════════════

class DockToggle(QWidget):
    toggled = Signal(bool)

    def __init__(self, label, checked=True, parent=None):
        super().__init__(parent)
        self.label = label
        self.checked = checked
        self._hover = False
        self.setFixedHeight(34)
        self.setMinimumWidth(90)
        self.setCursor(Qt.PointingHandCursor)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        r = QRectF(2, 2, self.width() - 4, self.height() - 4)

        if self.checked:
            p.setBrush(QColor(ACCENT.red(), ACCENT.green(), ACCENT.blue(), 30))
            p.setPen(QPen(QColor(ACCENT.red(), ACCENT.green(), ACCENT.blue(), 100), 1))
        elif self._hover:
            p.setBrush(QColor(255, 255, 255, 8))
            p.setPen(Qt.NoPen)
        else:
            p.setBrush(Qt.NoBrush)
            p.setPen(Qt.NoPen)
        p.drawRoundedRect(r, 7, 7)

        p.setFont(QFont("Segoe UI", 9))
        p.setPen(QColor(255, 255, 255, 200 if self.checked else 120))
        p.drawText(self.rect(), Qt.AlignCenter, self.label)

        if self.checked:
            p.setPen(Qt.NoPen)
            p.setBrush(ACCENT)
            p.drawRoundedRect((self.width() - 14) // 2, self.height() - 4, 14, 2.5, 1, 1)
        p.end()

    def enterEvent(self, e):
        self._hover = True
        self.update()

    def leaveEvent(self, e):
        self._hover = False
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.checked = not self.checked
            self.toggled.emit(self.checked)
            self.update()


class TimeSlider(QWidget):
    value_changed = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(34)
        self.setMinimumWidth(140)

        lo = QHBoxLayout(self)
        lo.setContentsMargins(6, 0, 6, 0)
        lo.setSpacing(4)

        tl = QLabel("⏱")
        tl.setFont(QFont("Segoe UI", 10))
        tl.setStyleSheet("color:rgba(255,255,255,120);")
        tl.setFixedWidth(16)
        lo.addWidget(tl)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(-100, 100)
        self.slider.setValue(0)
        self.slider.setStyleSheet("""
            QSlider::groove:horizontal{height:3px;background:rgba(255,255,255,10);border-radius:1px;}
            QSlider::handle:horizontal{background:white;width:12px;height:12px;margin:-5px 0;border-radius:6px;}
            QSlider::sub-page:horizontal{background:rgba(0,120,255,140);border-radius:1px;}
        """)
        self.slider.valueChanged.connect(self._on)
        lo.addWidget(self.slider)

        self._vl = QLabel("0×")
        self._vl.setFont(QFont("Segoe UI", 8))
        self._vl.setStyleSheet("color:rgba(255,255,255,80);")
        self._vl.setFixedWidth(26)
        self._vl.setAlignment(Qt.AlignCenter)
        lo.addWidget(self._vl)

    def _on(self, v):
        speed = v / 10.0
        self._vl.setText(f"{speed:.0f}×" if speed == int(speed) else f"{speed:.1f}×")
        self.value_changed.emit(speed)


class FloatingDock(QWidget):
    constellations_toggled = Signal(bool)
    names_toggled = Signal(bool)
    speed_changed = Signal(float)

    DOCK_W = 480
    DOCK_H = 50

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(self.DOCK_H)

        lo = QHBoxLayout(self)
        lo.setContentsMargins(14, 6, 14, 6)
        lo.setSpacing(6)

        self.const_btn = DockToggle("Constellations", True)
        self.const_btn.toggled.connect(self.constellations_toggled.emit)
        lo.addWidget(self.const_btn)

        self.names_btn = DockToggle("Names", True)
        self.names_btn.toggled.connect(self.names_toggled.emit)
        lo.addWidget(self.names_btn)

        sep = QWidget()
        sep.setFixedSize(1, 22)
        sep.setStyleSheet("background:rgba(255,255,255,8);")
        lo.addWidget(sep)

        self.time_slider = TimeSlider()
        self.time_slider.value_changed.connect(self.speed_changed.emit)
        lo.addWidget(self.time_slider, 1)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(0, 0, self.width(), self.height())
        path = QPainterPath()
        path.addRoundedRect(r, 14, 14)
        p.setClipPath(path)
        p.fillRect(r, QColor(12, 12, 15, 210))
        p.setClipping(False)
        p.setPen(QPen(QColor(255, 255, 255, 6), 1))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(r.adjusted(.5, .5, -.5, -.5), 14, 14)
        p.end()


# ═══════════════════════════════════════════════════════
#  APP
# ═══════════════════════════════════════════════════════

class App(QWidget):
    def __init__(self, file_system=None, parent=None):
        super().__init__(parent)

        lo = QVBoxLayout(self)
        lo.setContentsMargins(0, 0, 0, 0)
        lo.setSpacing(0)

        self.viewport = SkyViewport()
        lo.addWidget(self.viewport, 1)

        self.dock = FloatingDock(self)
        self.dock.constellations_toggled.connect(self._toggle_const)
        self.dock.names_toggled.connect(self._toggle_names)
        self.dock.speed_changed.connect(self._set_speed)

        self._position_dock()

        # Load catalog after UI shows
        QTimer.singleShot(300, self._load)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._position_dock()

    def _position_dock(self):
        dw = min(self.dock.DOCK_W, self.width() - 40)
        self.dock.setFixedWidth(dw)
        self.dock.move((self.width() - dw) // 2, self.height() - self.dock.DOCK_H - 16)
        self.dock.raise_()

    def _load(self):
        catalog = StarCatalog()
        self.viewport.set_catalog(catalog)

    def _toggle_const(self, v):
        self.viewport.show_constellations = v
        self.viewport.update()

    def _toggle_names(self, v):
        self.viewport.show_names = v
        self.viewport.update()

    def _set_speed(self, v):
        self.viewport.time_speed = v