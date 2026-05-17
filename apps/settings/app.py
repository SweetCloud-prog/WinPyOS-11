import os
import sys
import json

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QScrollArea, QStackedWidget,
    QSlider, QComboBox, QSizePolicy, QFileDialog,
    QColorDialog, QGridLayout, QPushButton
)
from PySide6.QtCore import (
    Qt, QRect, QRectF, Signal, QPropertyAnimation,
    QEasingCurve, Property, QSize
)
from PySide6.QtGui import (
    QFont, QColor, QPainter, QPen, QPixmap, QImage, QBrush
)

try:
    from core.icons import get_pixmap, get_icon
except ImportError:
    from PySide6.QtGui import QPixmap as _QP
    def get_pixmap(n, s=24, c=None):
        p = _QP(s, s); p.fill(Qt.transparent); return p
    def get_icon(n, s=24, c=None):
        from PySide6.QtGui import QIcon
        return QIcon(get_pixmap(n, s, c))


ACCENT = QColor(0, 103, 192)
CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "user_data", "settings.json"
)


# ═══════════════════════════════════════════════════════
#  CONFIG MANAGER — sauvegarde/charge les vrais paramètres
# ═══════════════════════════════════════════════════════

class Config:
    _data = {}
    _listeners = []

    @classmethod
    def load(cls):
        try:
            if os.path.exists(CONFIG_PATH):
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    cls._data = json.load(f)
        except Exception:
            cls._data = {}

    @classmethod
    def save(cls):
        try:
            os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(cls._data, f, indent=2)
        except Exception:
            pass

    @classmethod
    def get(cls, key, default=None):
        return cls._data.get(key, default)

    @classmethod
    def set(cls, key, value):
        cls._data[key] = value
        cls.save()
        for cb in cls._listeners:
            try:
                cb(key, value)
            except Exception:
                pass

    @classmethod
    def listen(cls, callback):
        cls._listeners.append(callback)


Config.load()


# ═══════════════════════════════════════════════════════
#  WIDGETS UI — Style Windows 11
# ═══════════════════════════════════════════════════════

class ToggleSwitch(QWidget):
    toggled = Signal(bool)

    def __init__(self, checked=False, parent=None):
        super().__init__(parent)
        self.setFixedSize(44, 22)
        self.setCursor(Qt.PointingHandCursor)
        self._checked = checked
        self._pos = 24.0 if checked else 4.0
        self._anim = QPropertyAnimation(self, b"handle_pos")
        self._anim.setDuration(200)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)

    def get_handle_pos(self):
        return self._pos

    def set_handle_pos(self, v):
        self._pos = v
        self.update()

    handle_pos = Property(float, get_handle_pos, set_handle_pos)

    def is_checked(self):
        return self._checked

    def set_checked(self, v):
        if v != self._checked:
            self._checked = v
            self._anim.stop()
            self._anim.setStartValue(self._pos)
            self._anim.setEndValue(24.0 if v else 4.0)
            self._anim.start()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        if self._checked:
            p.setBrush(ACCENT)
            p.setPen(Qt.NoPen)
        else:
            p.setBrush(QColor(60, 60, 60))
            p.setPen(QPen(QColor(255, 255, 255, 70), 1.2))
        p.drawRoundedRect(QRectF(1, 1, 42, 20), 11, 11)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255))
        sz = 14 if self._checked else 12
        p.drawEllipse(QRectF(self._pos, (22 - sz) / 2, sz, sz))
        p.end()

    def mousePressEvent(self, event):
        self._checked = not self._checked
        self._anim.stop()
        self._anim.setStartValue(self._pos)
        self._anim.setEndValue(24.0 if self._checked else 4.0)
        self._anim.start()
        self.toggled.emit(self._checked)

    def sizeHint(self):
        return QSize(44, 22)

    def minimumSizeHint(self):
        return QSize(44, 22)


class WinCombo(QComboBox):
    def __init__(self, items=None, parent=None):
        super().__init__(parent)
        self.setFixedHeight(32)
        self.setMinimumWidth(150)
        if items:
            self.addItems(items)
        self.setStyleSheet("""
            QComboBox {
                background: rgba(255,255,255,6);
                border: 1px solid rgba(255,255,255,10);
                border-radius: 6px;
                color: white;
                padding: 4px 12px;
                font-family: 'Segoe UI';
                font-size: 12px;
            }
            QComboBox:hover { background: rgba(255,255,255,10); }
            QComboBox::drop-down { border: none; width: 28px; }
            QComboBox::down-arrow { image: none; }
            QComboBox QAbstractItemView {
                background: #2d2d2d;
                border: 1px solid rgba(255,255,255,12);
                border-radius: 8px;
                color: white;
                padding: 4px;
                selection-background-color: rgba(255,255,255,10);
                outline: none;
            }
            QComboBox QAbstractItemView::item {
                padding: 6px 12px;
                border-radius: 4px;
            }
            QComboBox QAbstractItemView::item:hover {
                background: rgba(255,255,255,8);
            }
        """)

    def sizeHint(self):
        return QSize(160, 32)

    def minimumSizeHint(self):
        return QSize(150, 32)


class WinSlider(QWidget):
    """Slider avec label de valeur."""
    valueChanged = Signal(int)

    def __init__(self, min_val=0, max_val=100, value=70, suffix="%", parent=None):
        super().__init__(parent)
        self.suffix = suffix
        self.setFixedHeight(32)
        self.setMinimumWidth(200)

        lo = QHBoxLayout(self)
        lo.setContentsMargins(0, 0, 0, 0)
        lo.setSpacing(8)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(min_val, max_val)
        self.slider.setValue(value)
        self.slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 4px;
                background: rgba(255,255,255,12);
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: white;
                width: 18px; height: 18px;
                margin: -7px 0;
                border-radius: 9px;
            }
            QSlider::sub-page:horizontal {
                background: rgba(0,103,192,200);
                border-radius: 2px;
            }
        """)
        lo.addWidget(self.slider, 1)

        self.label = QLabel(f"{value}{suffix}")
        self.label.setFixedWidth(40)
        self.label.setFont(QFont("Segoe UI", 9))
        self.label.setStyleSheet("color: rgba(255,255,255,150);")
        self.label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lo.addWidget(self.label)

        self.slider.valueChanged.connect(self._on_change)

    def _on_change(self, v):
        self.label.setText(f"{v}{self.suffix}")
        self.valueChanged.emit(v)

    def value(self):
        return self.slider.value()

    def setValue(self, v):
        self.slider.setValue(v)

    def sizeHint(self):
        return QSize(200, 32)

    def minimumSizeHint(self):
        return QSize(200, 32)


class ActionButton(QPushButton):
    """Bouton d'action style Win11."""
    def __init__(self, text, accent=False, parent=None):
        super().__init__(text, parent)
        self.setFixedHeight(32)
        self.setCursor(Qt.PointingHandCursor)
        self.setFont(QFont("Segoe UI", 10))
        if accent:
            self.setStyleSheet("""
                QPushButton {
                    background: rgba(0,103,192,200);
                    border: none;
                    border-radius: 6px;
                    color: white;
                    padding: 4px 20px;
                }
                QPushButton:hover { background: rgba(0,103,192,230); }
                QPushButton:pressed { background: rgba(0,103,192,160); }
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background: rgba(255,255,255,6);
                    border: 1px solid rgba(255,255,255,10);
                    border-radius: 6px;
                    color: white;
                    padding: 4px 20px;
                }
                QPushButton:hover { background: rgba(255,255,255,12); }
                QPushButton:pressed { background: rgba(255,255,255,4); }
            """)


# ═══════════════════════════════════════════════════════
#  SETTING CARD — carte de paramètre
# ═══════════════════════════════════════════════════════

class SettingCard(QWidget):
    def __init__(self, icon_name, title, description="", control=None,
                 expandable=False, parent=None):
        super().__init__(parent)
        self._icon = icon_name
        self._title = title
        self._desc = description
        self._control = control
        self._hover = False
        self._expanded = False
        self._expandable = expandable
        self._expand_content = None

        h = 60
        if description:
            h = 68
        self.setFixedHeight(h)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        if control:
            control.setParent(self)

    def set_expand_content(self, widget):
        self._expand_content = widget
        widget.setParent(self)
        widget.hide()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._control:
            try:
                cw = max(self._control.sizeHint().width(), 44)
                ch = max(self._control.sizeHint().height(), 22)
                base_h = 68 if self._desc else 60
                self._control.setGeometry(
                    self.width() - cw - 16,
                    (base_h - ch) // 2,
                    cw, ch
                )
            except Exception:
                pass
        if self._expand_content:
            base_h = 68 if self._desc else 60
            self._expand_content.setGeometry(
                16, base_h, self.width() - 32, self.height() - base_h - 8
            )

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)

        r = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        bg = QColor(255, 255, 255, 14 if self._hover else 8)
        p.setBrush(bg)
        p.setPen(QPen(QColor(255, 255, 255, 8), 1))
        p.drawRoundedRect(r, 8, 8)

        # Icon
        if self._icon:
            px = get_pixmap(self._icon, 20, QColor(255, 255, 255, 200))
            p.drawPixmap(18, (min(self.height(), 68) - 20) // 2, px)

        # Text
        tx = 48 if self._icon else 18
        ctrl_w = 0
        if self._control:
            ctrl_w = max(self._control.width(), 60) + 32
        text_w = self.width() - tx - ctrl_w

        p.setFont(QFont("Segoe UI", 10))
        p.setPen(QColor(255, 255, 255, 220))
        base_h = 68 if self._desc else 60

        if self._desc:
            p.drawText(QRect(tx, 12, text_w, 22), Qt.AlignVCenter, self._title)
            p.setFont(QFont("Segoe UI", 9))
            p.setPen(QColor(255, 255, 255, 80))
            p.drawText(QRect(tx, 34, text_w, 20), Qt.AlignVCenter, self._desc)
        else:
            p.drawText(QRect(tx, 0, text_w, base_h), Qt.AlignVCenter, self._title)

        # Chevron si expandable
        if self._expandable:
            p.setFont(QFont("Segoe UI", 11))
            p.setPen(QColor(255, 255, 255, 60))
            chevron = "˅" if not self._expanded else "˄"
            p.drawText(QRect(self.width() - 36, 0, 24, base_h), Qt.AlignCenter, chevron)

        p.end()

    def enterEvent(self, e):
        self._hover = True
        self.update()

    def leaveEvent(self, e):
        self._hover = False
        self.update()


# ═══════════════════════════════════════════════════════
#  WALLPAPER PREVIEW — Prévisualisation du fond d'écran
# ═══════════════════════════════════════════════════════

class WallpaperPreview(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(180)
        self._image = None
        self._color = QColor(Config.get("wallpaper_color", "#011230"))
        self._load_current()

    def _load_current(self):
        wp = Config.get("wallpaper_path")
        if wp and os.path.exists(wp):
            self._image = QPixmap(wp)

    def set_image(self, path):
        if path and os.path.exists(path):
            self._image = QPixmap(path)
        else:
            self._image = None
        self.update()

    def set_color(self, color):
        self._color = color
        self._image = None
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        # Outer card
        r = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        p.setBrush(QColor(255, 255, 255, 6))
        p.setPen(QPen(QColor(255, 255, 255, 8), 1))
        p.drawRoundedRect(r, 10, 10)

        # Preview area (mock monitor)
        margin = 20
        mon_w = self.width() - margin * 2
        mon_h = self.height() - margin * 2 - 16
        mon_x = margin
        mon_y = margin - 4

        # Monitor border
        p.setBrush(QColor(50, 50, 50))
        p.setPen(QPen(QColor(70, 70, 70), 2))
        p.drawRoundedRect(QRectF(mon_x, mon_y, mon_w, mon_h), 8, 8)

        # Screen content
        scr_m = 6
        scr = QRectF(mon_x + scr_m, mon_y + scr_m, mon_w - scr_m * 2, mon_h - scr_m * 2)

        if self._image and not self._image.isNull():
            scaled = self._image.scaled(
                int(scr.width()), int(scr.height()),
                Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
            )
            # Center crop
            sx = (scaled.width() - int(scr.width())) // 2
            sy = (scaled.height() - int(scr.height())) // 2
            cropped = scaled.copy(sx, sy, int(scr.width()), int(scr.height()))
            p.drawPixmap(int(scr.x()), int(scr.y()), cropped)
        else:
            p.fillRect(scr, QBrush(self._color))

        # Monitor stand
        stand_w = 40
        stand_h = 10
        p.setBrush(QColor(70, 70, 70))
        p.setPen(Qt.NoPen)
        cx = self.width() / 2
        p.drawRect(QRectF(cx - stand_w / 2, mon_y + mon_h, stand_w, stand_h))
        p.drawRoundedRect(QRectF(cx - stand_w * 0.8, mon_y + mon_h + stand_h - 2, stand_w * 1.6, 4), 2, 2)

        p.end()


# ═══════════════════════════════════════════════════════
#  COLOR PICKER GRID
# ═══════════════════════════════════════════════════════

class ColorButton(QWidget):
    clicked = Signal(QColor)

    def __init__(self, color, parent=None):
        super().__init__(parent)
        self.color = color
        self._selected = False
        self._hover = False
        self.setFixedSize(36, 36)
        self.setCursor(Qt.PointingHandCursor)

    def set_selected(self, v):
        self._selected = v
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        if self._selected:
            p.setPen(QPen(QColor(255, 255, 255), 2))
        elif self._hover:
            p.setPen(QPen(QColor(255, 255, 255, 80), 1.5))
        else:
            p.setPen(Qt.NoPen)

        p.setBrush(self.color)
        p.drawRoundedRect(QRectF(3, 3, 30, 30), 6, 6)
        p.end()

    def enterEvent(self, e):
        self._hover = True
        self.update()

    def leaveEvent(self, e):
        self._hover = False
        self.update()

    def mousePressEvent(self, event):
        self.clicked.emit(self.color)


class AccentColorPicker(QWidget):
    color_changed = Signal(QColor)

    def __init__(self, parent=None):
        super().__init__(parent)
        lo = QVBoxLayout(self)
        lo.setContentsMargins(0, 0, 0, 0)
        lo.setSpacing(8)

        lbl = QLabel("Accent color")
        lbl.setFont(QFont("Segoe UI", 10))
        lbl.setStyleSheet("color: rgba(255,255,255,180);")
        lo.addWidget(lbl)

        grid = QGridLayout()
        grid.setSpacing(4)

        self._colors = [
            "#0078d4", "#0099bc", "#7a7574", "#767676",
            "#ff8c00", "#e81123", "#d13438", "#c30052",
            "#bf0077", "#9a0089", "#881798", "#744da9",
            "#8764b8", "#0063b1", "#2d7d9a", "#018574",
            "#00b7c3", "#038387", "#486860", "#498205",
            "#107c10", "#767676", "#4c4a48", "#69797e",
        ]

        self._buttons = []
        current_accent = Config.get("accent_color", "#0078d4")

        for i, hex_color in enumerate(self._colors):
            btn = ColorButton(QColor(hex_color))
            btn.set_selected(hex_color.lower() == current_accent.lower())
            btn.clicked.connect(self._on_color)
            grid.addWidget(btn, i // 6, i % 6)
            self._buttons.append((btn, hex_color))

        lo.addLayout(grid)

        # Custom color button
        custom_btn = ActionButton("Custom color...")
        custom_btn.clicked.connect(self._custom_color)
        lo.addWidget(custom_btn)

    def _on_color(self, color):
        for btn, _ in self._buttons:
            btn.set_selected(btn.color == color)
        Config.set("accent_color", color.name())
        self.color_changed.emit(color)

    def _custom_color(self):
        color = QColorDialog.getColor(
            QColor(Config.get("accent_color", "#0078d4")),
            self, "Choose accent color"
        )
        if color.isValid():
            Config.set("accent_color", color.name())
            self.color_changed.emit(color)
            for btn, _ in self._buttons:
                btn.set_selected(False)


# ═══════════════════════════════════════════════════════
#  NAV BUTTON
# ═══════════════════════════════════════════════════════

class NavBtn(QWidget):
    clicked = Signal()

    def __init__(self, icon_name, text, parent=None):
        super().__init__(parent)
        self._icon = icon_name
        self._text = text
        self.active = False
        self._hover = False
        self.setFixedHeight(38)
        self.setCursor(Qt.PointingHandCursor)
        self._px = get_pixmap(icon_name, 20, QColor(255, 255, 255, 200))

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)

        r = QRect(4, 1, self.width() - 8, self.height() - 2)
        if self.active:
            p.setBrush(QColor(255, 255, 255, 10))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(r, 6, 6)
            p.setBrush(ACCENT)
            p.drawRoundedRect(2, 10, 3, self.height() - 20, 1.5, 1.5)
        elif self._hover:
            p.setBrush(QColor(255, 255, 255, 5))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(r, 6, 6)

        p.drawPixmap(18, (self.height() - 20) // 2, self._px)
        p.setFont(QFont("Segoe UI", 10))
        p.setPen(QColor(255, 255, 255, 210 if self.active else 180))
        p.drawText(QRect(48, 0, self.width() - 56, self.height()), Qt.AlignVCenter, self._text)
        p.end()

    def enterEvent(self, e):
        self._hover = True
        self.update()

    def leaveEvent(self, e):
        self._hover = False
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()


# ═══════════════════════════════════════════════════════
#  SECTION LABEL
# ═══════════════════════════════════════════════════════

class SectionLabel(QWidget):
    def __init__(self, text, parent=None):
        super().__init__(parent)
        self._text = text
        self.setFixedHeight(44)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.TextAntialiasing)
        p.setFont(QFont("Segoe UI Semibold", 12))
        p.setPen(QColor(255, 255, 255, 190))
        p.drawText(QRect(4, 14, self.width(), 24), Qt.AlignVCenter, self._text)
        p.end()


# ═══════════════════════════════════════════════════════
#  DEVICE CARD (About)
# ═══════════════════════════════════════════════════════

class DeviceCard(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(120)
        self._px = get_pixmap("computer", 52)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)

        r = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        p.setBrush(QColor(255, 255, 255, 6))
        p.setPen(QPen(QColor(255, 255, 255, 8), 1))
        p.drawRoundedRect(r, 10, 10)

        p.drawPixmap(24, (self.height() - 52) // 2, self._px)

        tx = 92
        p.setFont(QFont("Segoe UI Semibold", 16))
        p.setPen(QColor(255, 255, 255, 230))
        p.drawText(QRect(tx, 20, 300, 26), Qt.AlignVCenter, "WINPY11-PC")

        p.setFont(QFont("Segoe UI", 10))
        p.setPen(QColor(96, 175, 255))
        p.drawText(QRect(tx, 50, 300, 22), Qt.AlignVCenter, "Rename your PC")

        p.setFont(QFont("Segoe UI", 9))
        p.setPen(QColor(255, 255, 255, 80))
        p.drawText(QRect(tx, 74, 300, 20), Qt.AlignVCenter, "WinPy11 Pro • 23H2 • Build 1.0.0.0")
        p.end()


# ═══════════════════════════════════════════════════════
#  PAGE BUILDER
# ═══════════════════════════════════════════════════════

def _scrollable(widget):
    s = QScrollArea()
    s.setWidgetResizable(True)
    s.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    s.setStyleSheet("""
        QScrollArea{background:transparent;border:none;}
        QScrollBar:vertical{width:5px;background:transparent;}
        QScrollBar::handle:vertical{background:rgba(255,255,255,14);border-radius:2px;min-height:30px;}
        QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0;}
    """)
    s.setWidget(widget)
    return s


def page(title, items):
    w = QWidget()
    w.setStyleSheet("background:transparent;")
    lo = QVBoxLayout(w)
    lo.setContentsMargins(32, 28, 32, 28)
    lo.setSpacing(6)

    tl = QLabel(title)
    tl.setFont(QFont("Segoe UI Semibold", 28))
    tl.setStyleSheet("color:white;")
    lo.addWidget(tl)
    lo.addSpacing(12)

    for item in items:
        if isinstance(item, str):
            lo.addWidget(SectionLabel(item))
        elif isinstance(item, QWidget):
            lo.addWidget(item)
        elif isinstance(item, tuple):
            ic = item[0] if len(item) > 0 else ""
            ti = item[1] if len(item) > 1 else ""
            de = item[2] if len(item) > 2 else ""
            co = item[3] if len(item) > 3 else None
            lo.addWidget(SettingCard(ic, ti, de, co))

    lo.addStretch()

    container = QWidget()
    container.setStyleSheet("background:transparent;")
    cl = QVBoxLayout(container)
    cl.setContentsMargins(0, 0, 0, 0)
    cl.addWidget(_scrollable(w))
    return container


# ═══════════════════════════════════════════════════════
#  PERSONALIZATION PAGE — avec vrai wallpaper picker
# ═══════════════════════════════════════════════════════

class PersonalizationPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background:transparent;")

        lo = QVBoxLayout(self)
        lo.setContentsMargins(32, 28, 32, 28)
        lo.setSpacing(6)

        tl = QLabel("Personalization")
        tl.setFont(QFont("Segoe UI Semibold", 28))
        tl.setStyleSheet("color:white;")
        lo.addWidget(tl)
        lo.addSpacing(12)

        # ── Wallpaper preview ──
        self.preview = WallpaperPreview()
        lo.addWidget(self.preview)
        lo.addSpacing(8)

        # ── Background section ──
        lo.addWidget(SectionLabel("Background"))

        # Choose image button
        choose_card = QWidget()
        choose_card.setFixedHeight(56)
        choose_lo = QHBoxLayout(choose_card)
        choose_lo.setContentsMargins(0, 0, 0, 0)
        choose_lo.setSpacing(8)

        self.choose_btn = ActionButton("Browse photos", accent=True)
        self.choose_btn.clicked.connect(self._pick_wallpaper)
        choose_lo.addWidget(self.choose_btn)

        self.reset_btn = ActionButton("Reset to default")
        self.reset_btn.clicked.connect(self._reset_wallpaper)
        choose_lo.addWidget(self.reset_btn)

        choose_lo.addStretch()
        lo.addWidget(choose_card)

        # Solid color option
        lo.addSpacing(4)
        lo.addWidget(SectionLabel("Or choose a solid color"))

        # Color grid
        color_grid = QWidget()
        cg_lo = QGridLayout(color_grid)
        cg_lo.setSpacing(4)
        cg_lo.setContentsMargins(0, 0, 0, 0)

        wall_colors = [
            "#011230", "#0c2340", "#1a1a2e", "#16213e",
            "#0f3460", "#1b262c", "#2c3333", "#3c4048",
            "#4a0e4e", "#3a1078", "#2b2d42", "#1d3557",
            "#606c38", "#283618", "#3a5a40", "#344e41",
            "#800020", "#590d22", "#6d4c41", "#4e342e",
        ]

        for i, hex_c in enumerate(wall_colors):
            btn = ColorButton(QColor(hex_c))
            btn.clicked.connect(lambda c=QColor(hex_c): self._set_solid_color(c))
            cg_lo.addWidget(btn, i // 5, i % 5)

        lo.addWidget(color_grid)

        # ── Colors section ──
        lo.addSpacing(8)
        lo.addWidget(SectionLabel("Colors"))

        mode_combo = WinCombo(["Dark", "Light"])
        mode_combo.setCurrentText(Config.get("theme_mode", "Dark"))
        mode_combo.currentTextChanged.connect(lambda v: Config.set("theme_mode", v))
        lo.addWidget(SettingCard("image", "App mode", "Choose your default app mode", mode_combo))

        self.accent_picker = AccentColorPicker()
        lo.addWidget(self.accent_picker)

        t1 = ToggleSwitch(Config.get("transparency", True))
        t1.toggled.connect(lambda v: Config.set("transparency", v))
        lo.addWidget(SettingCard("image", "Transparency effects", "Enable transparency in windows", t1))

        # ── Taskbar ──
        lo.addSpacing(4)
        lo.addWidget(SectionLabel("Taskbar"))

        ta_combo = WinCombo(["Center", "Left"])
        ta_combo.setCurrentText(Config.get("taskbar_align", "Center"))
        ta_combo.currentTextChanged.connect(lambda v: Config.set("taskbar_align", v))
        lo.addWidget(SettingCard("settings", "Taskbar alignment", "", ta_combo))

        t2 = ToggleSwitch(Config.get("show_search", True))
        t2.toggled.connect(lambda v: Config.set("show_search", v))
        lo.addWidget(SettingCard("search", "Search", "Show search on taskbar", t2))

        t3 = ToggleSwitch(Config.get("show_widgets", True))
        t3.toggled.connect(lambda v: Config.set("show_widgets", v))
        lo.addWidget(SettingCard("settings", "Widgets", "Show widgets button", t3))

        lo.addStretch()

    def _pick_wallpaper(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose Wallpaper", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.webp);;All (*)"
        )
        if path:
            Config.set("wallpaper_path", path)
            Config.set("wallpaper_type", "image")
            self.preview.set_image(path)
            self._refresh_desktop()

    def _reset_wallpaper(self):
        Config.set("wallpaper_path", "")
        Config.set("wallpaper_type", "default")
        self.preview.set_image(None)
        self.preview.set_color(QColor("#011230"))
        self._refresh_desktop()

    def _set_solid_color(self, color):
        Config.set("wallpaper_type", "solid")
        Config.set("wallpaper_color", color.name())
        Config.set("wallpaper_path", "")
        self.preview.set_color(color)
        self._refresh_desktop()

    def _refresh_desktop(self):
        """Force le rechargement du wallpaper sur le desktop."""
        # Remonter la hiérarchie pour trouver le Desktop
        widget = self.parent()
        while widget is not None:
            if hasattr(widget, 'reload_wallpaper'):
                widget.reload_wallpaper()
                return
            widget = widget.parent() if hasattr(widget, 'parent') else None


# ═══════════════════════════════════════════════════════
#  APP PRINCIPALE
# ═══════════════════════════════════════════════════════

class App(QWidget):
    def __init__(self, file_system=None, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background:#202020;")

        main = QHBoxLayout(self)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)

        # ═══ SIDEBAR ═══
        sidebar = QWidget()
        sidebar.setFixedWidth(290)
        sidebar.setStyleSheet("background:#1c1c1c;border-right:1px solid rgba(255,255,255,5);")

        sl = QVBoxLayout(sidebar)
        sl.setContentsMargins(14, 20, 14, 16)
        sl.setSpacing(0)

        title = QLabel("  Settings")
        title.setFont(QFont("Segoe UI Semibold", 24))
        title.setStyleSheet("color:white;border:none;")
        sl.addWidget(title)
        sl.addSpacing(14)

        search = QLineEdit()
        search.setPlaceholderText("  Find a setting")
        search.setFixedHeight(36)
        search.setFont(QFont("Segoe UI", 10))
        search.setStyleSheet("""
            QLineEdit{background:rgba(255,255,255,5);border:1px solid rgba(255,255,255,8);
            border-radius:6px;color:white;padding:0 14px;}
            QLineEdit:focus{border-bottom:2px solid rgba(0,103,192,220);}
        """)
        sl.addWidget(search)
        sl.addSpacing(14)

        nav_scroll = QScrollArea()
        nav_scroll.setWidgetResizable(True)
        nav_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        nav_scroll.setStyleSheet("""
            QScrollArea{background:transparent;border:none;}
            QScrollBar:vertical{width:3px;background:transparent;}
            QScrollBar::handle:vertical{background:rgba(255,255,255,12);border-radius:1px;}
            QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0;}
        """)

        nav_w = QWidget()
        nav_w.setStyleSheet("background:transparent;")
        nav_lo = QVBoxLayout(nav_w)
        nav_lo.setContentsMargins(0, 0, 0, 0)
        nav_lo.setSpacing(2)

        self._btns = []
        cats = [
            ("computer", "System"),
            ("wifi", "Network & internet"),
            ("image", "Personalization"),
            ("folder", "Apps"),
            ("user", "Accounts"),
            ("shield", "Privacy & security"),
            ("refresh", "Windows Update"),
            ("computer", "About"),
        ]

        for i, (icon, name) in enumerate(cats):
            btn = NavBtn(icon, name)
            btn.clicked.connect(lambda idx=i: self._go(idx))
            nav_lo.addWidget(btn)
            self._btns.append(btn)

        nav_lo.addStretch()
        nav_scroll.setWidget(nav_w)
        sl.addWidget(nav_scroll, 1)

        main.addWidget(sidebar)

        # ═══ PAGES ═══
        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background:#202020;")

        # 0 — System
        brightness = WinSlider(0, 100, Config.get("brightness", 80))
        brightness.valueChanged.connect(lambda v: Config.set("brightness", v))
        volume = WinSlider(0, 100, Config.get("volume", 65))
        volume.valueChanged.connect(lambda v: Config.set("volume", v))

        t_notif = ToggleSwitch(Config.get("notifications", True))
        t_notif.toggled.connect(lambda v: Config.set("notifications", v))
        t_dnd = ToggleSwitch(Config.get("do_not_disturb", False))
        t_dnd.toggled.connect(lambda v: Config.set("do_not_disturb", v))

        scale = WinCombo(["100%", "125%", "150%", "175%", "200%"])
        scale.setCurrentText(Config.get("scale", "125%"))
        scale.currentTextChanged.connect(lambda v: Config.set("scale", v))

        res = WinCombo(["1920×1080", "2560×1440", "3840×2160"])
        res.setCurrentText(Config.get("resolution", "1920×1080"))
        res.currentTextChanged.connect(lambda v: Config.set("resolution", v))

        power = WinCombo(["Balanced", "Best performance", "Best efficiency"])
        power.setCurrentText(Config.get("power_mode", "Balanced"))
        power.currentTextChanged.connect(lambda v: Config.set("power_mode", v))

        self.stack.addWidget(page("System", [
            "Display",
            ("computer", "Brightness", "Adjust screen brightness", brightness),
            ("computer", "Display resolution", "", res),
            ("computer", "Scale", "Change text and app size", scale),
            "Sound",
            ("volume", "Volume", "Master volume", volume),
            "Notifications",
            ("settings", "Notifications", "Get notifications from apps", t_notif),
            ("settings", "Do not disturb", "Silence all notifications", t_dnd),
            "Power",
            ("settings", "Power mode", "", power),
        ]))

        # 1 — Network
        t_wifi = ToggleSwitch(Config.get("wifi", True))
        t_wifi.toggled.connect(lambda v: Config.set("wifi", v))
        t_vpn = ToggleSwitch(Config.get("vpn", False))
        t_vpn.toggled.connect(lambda v: Config.set("vpn", v))
        t_airplane = ToggleSwitch(Config.get("airplane", False))
        t_airplane.toggled.connect(lambda v: Config.set("airplane", v))

        self.stack.addWidget(page("Network & internet", [
            "Connectivity",
            ("wifi", "Wi-Fi", "Connected", t_wifi),
            ("wifi", "Ethernet", "Not connected"),
            ("lock", "VPN", "Disconnected", t_vpn),
            ("wifi", "Airplane mode", "", t_airplane),
        ]))

        # 2 — Personalization (custom page)
        perso_container = QWidget()
        perso_container.setStyleSheet("background:transparent;")
        pcl = QVBoxLayout(perso_container)
        pcl.setContentsMargins(0, 0, 0, 0)
        perso_page = PersonalizationPage()
        pcl.addWidget(_scrollable(perso_page))
        self.stack.addWidget(perso_container)

        # 3 — Apps
        self.stack.addWidget(page("Apps", [
            "Installed apps",
            ("globe", "Edge", "Version 1.0 • Web Browser"),
            ("folder", "File Explorer", "Version 1.0 • File Manager"),
            ("terminal", "Terminal", "Version 1.0 • Command Line"),
            ("notepad", "Notepad", "Version 1.0 • Text Editor"),
            ("calculator", "Calculator", "Version 1.0 • Calculator"),
            ("settings", "Settings", "Version 1.0 • System Settings"),
        ]))

        # 4 — Accounts
        self.stack.addWidget(page("Accounts", [
            "Your info",
            ("user", "User", "Local account"),
            ("settings", "Email & accounts", "Add accounts"),
            "Sign-in options",
            ("lock", "Password", "Last changed: Never"),
            ("lock", "PIN (Windows Hello)", "Not set up"),
        ]))

        # 5 — Privacy
        t_loc = ToggleSwitch(Config.get("location", True))
        t_loc.toggled.connect(lambda v: Config.set("location", v))
        t_cam = ToggleSwitch(Config.get("camera", True))
        t_cam.toggled.connect(lambda v: Config.set("camera", v))
        t_mic = ToggleSwitch(Config.get("microphone", True))
        t_mic.toggled.connect(lambda v: Config.set("microphone", v))

        self.stack.addWidget(page("Privacy & security", [
            "Security",
            ("shield", "Windows Security", "Protection status: OK"),
            "App permissions",
            ("settings", "Location", "Allow location access", t_loc),
            ("video", "Camera", "Allow camera access", t_cam),
            ("volume", "Microphone", "Allow microphone access", t_mic),
        ]))

        # 6 — Update
        self.stack.addWidget(page("Windows Update", [
            "Status",
            ("refresh", "You're up to date", "Last checked: Today"),
            ("refresh", "Check for updates", "Download and install"),
            "Options",
            ("settings", "Update history", "View recent updates"),
            ("settings", "Recovery", "Reset, advanced startup"),
        ]))

        # 7 — About
        about = page("About", [])
        sw = about.findChild(QScrollArea).widget()
        alo = sw.layout()
        # Remove the stretch
        for i in range(alo.count() - 1, -1, -1):
            item = alo.itemAt(i)
            if item and item.spacerItem():
                alo.removeItem(item)
                break

        alo.addWidget(DeviceCard())
        alo.addSpacing(8)
        alo.addWidget(SectionLabel("Device specifications"))
        for ic, t, d in [
            ("computer", "Device name", "WINPY11-PC"),
            ("computer", "Processor", "Python Virtual CPU"),
            ("computer", "RAM", "Unlimited (Virtual)"),
            ("computer", "System type", "64-bit, x64-based"),
        ]:
            alo.addWidget(SettingCard(ic, t, d))
        alo.addSpacing(4)
        alo.addWidget(SectionLabel("Windows specifications"))
        for ic, t, d in [
            ("settings", "Edition", "WinPy11 Pro"),
            ("settings", "Version", "23H2"),
            ("settings", "OS Build", "1.0.0.0"),
        ]:
            alo.addWidget(SettingCard(ic, t, d))
        alo.addStretch()
        self.stack.addWidget(about)

        main.addWidget(self.stack, 1)
        self._go(0)

    def _go(self, idx):
        for i, btn in enumerate(self._btns):
            btn.active = (i == idx)
            btn.update()
        self.stack.setCurrentIndex(idx)