"""
WinPy11 Photos — Visionneuse d'images minimaliste.
Formats : jpg, jpeg, png, webp, svg, gif, bmp, avif, ico
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QFileDialog, QSizePolicy, QLabel
)
from PySide6.QtCore import Qt, Signal, QRectF, QPointF, QTimer, QRect
from PySide6.QtGui import (
    QFont, QColor, QPainter, QPen, QPixmap, QImageReader,
    QTransform, QPainterPath
)

from core.icons import get_icon, get_pixmap

IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".svg", ".gif", ".bmp", ".avif", ".ico", ".tiff")


class ImageViewport(QWidget):
    """Viewport zoomable avec pan."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)

        self._pixmap = None
        self._zoom = 1.0
        self._offset = QPointF(0, 0)
        self._drag_start = None
        self._drag_offset = None
        self._fit_mode = True

    def set_image(self, pixmap):
        self._pixmap = pixmap
        self._fit_mode = True
        self._offset = QPointF(0, 0)
        self.update()

    def fit_view(self):
        self._fit_mode = True
        self._offset = QPointF(0, 0)
        self.update()

    def rotate_cw(self):
        if self._pixmap and not self._pixmap.isNull():
            t = QTransform().rotate(90)
            self._pixmap = self._pixmap.transformed(t, Qt.SmoothTransformation)
            self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)

        # Background
        p.fillRect(self.rect(), QColor(20, 20, 22))

        if not self._pixmap or self._pixmap.isNull():
            # Empty state
            px = get_pixmap("image", 64, QColor(255, 255, 255, 25))
            p.drawPixmap((self.width() - 64) // 2, self.height() // 2 - 50, px)
            p.setFont(QFont("Segoe UI", 12))
            p.setPen(QColor(255, 255, 255, 40))
            p.drawText(self.rect().adjusted(0, 30, 0, 0), Qt.AlignCenter, "Open an image")
            p.end()
            return

        w, h = self.width(), self.height()
        pw, ph = self._pixmap.width(), self._pixmap.height()

        if self._fit_mode:
            # Fit dans le viewport
            scale_w = w / pw
            scale_h = h / ph
            self._zoom = min(scale_w, scale_h) * 0.92

        dw = pw * self._zoom
        dh = ph * self._zoom
        x = (w - dw) / 2 + self._offset.x()
        y = (h - dh) / 2 + self._offset.y()

        # Ombre
        shadow_r = QRectF(x + 4, y + 4, dw, dh)
        p.fillRect(shadow_r, QColor(0, 0, 0, 40))

        # Image
        p.drawPixmap(QRectF(x, y, dw, dh), self._pixmap, QRectF(0, 0, pw, ph))

        p.end()

    def wheelEvent(self, event):
        self._fit_mode = False
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self._zoom = max(0.05, min(20.0, self._zoom * factor))
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_start = event.position()
            self._drag_offset = QPointF(self._offset)

    def mouseMoveEvent(self, event):
        if self._drag_start and event.buttons() & Qt.LeftButton:
            delta = event.position() - self._drag_start
            self._offset = self._drag_offset + delta
            self._fit_mode = False
            self.update()

    def mouseReleaseEvent(self, event):
        self._drag_start = None

    def mouseDoubleClickEvent(self, event):
        self.fit_view()


class BottomBar(QWidget):
    """Barre de contrôle en bas."""
    prev_clicked = Signal()
    next_clicked = Signal()
    open_clicked = Signal()
    rotate_clicked = Signal()
    fit_clicked = Signal()
    zoom_in_clicked = Signal()
    zoom_out_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(52)
        self.info_text = ""
        self.counter_text = ""

        lo = QHBoxLayout(self)
        lo.setContentsMargins(16, 0, 16, 0)
        lo.setSpacing(6)

        btn_css = """
            QPushButton{background:rgba(255,255,255,6);border:1px solid rgba(255,255,255,6);
            border-radius:6px;color:white;padding:4px;}
            QPushButton:hover{background:rgba(255,255,255,12);}
            QPushButton:disabled{opacity:0.3;}
        """

        # Open
        self.open_btn = QPushButton()
        self.open_btn.setIcon(get_icon("folder_open", 16, QColor(255, 255, 255, 180)))
        self.open_btn.setFixedSize(36, 36)
        self.open_btn.setCursor(Qt.PointingHandCursor)
        self.open_btn.setStyleSheet(btn_css)
        self.open_btn.setToolTip("Open")
        self.open_btn.clicked.connect(self.open_clicked.emit)
        lo.addWidget(self.open_btn)

        lo.addStretch()

        # Prev
        self.prev_btn = QPushButton()
        self.prev_btn.setIcon(get_icon("arrow_left", 16, QColor(255, 255, 255, 180)))
        self.prev_btn.setFixedSize(36, 36)
        self.prev_btn.setCursor(Qt.PointingHandCursor)
        self.prev_btn.setStyleSheet(btn_css)
        self.prev_btn.clicked.connect(self.prev_clicked.emit)
        lo.addWidget(self.prev_btn)

        # Counter label
        self.counter_label = QLabel()
        self.counter_label.setFont(QFont("Segoe UI", 10))
        self.counter_label.setStyleSheet("color: rgba(255,255,255,120);")
        self.counter_label.setAlignment(Qt.AlignCenter)
        self.counter_label.setFixedWidth(60)
        lo.addWidget(self.counter_label)

        # Next
        self.next_btn = QPushButton()
        self.next_btn.setIcon(get_icon("arrow_right", 16, QColor(255, 255, 255, 180)))
        self.next_btn.setFixedSize(36, 36)
        self.next_btn.setCursor(Qt.PointingHandCursor)
        self.next_btn.setStyleSheet(btn_css)
        self.next_btn.clicked.connect(self.next_clicked.emit)
        lo.addWidget(self.next_btn)

        lo.addStretch()

        # Zoom out
        self.zout = QPushButton("−")
        self.zout.setFixedSize(32, 32)
        self.zout.setFont(QFont("Segoe UI", 14))
        self.zout.setCursor(Qt.PointingHandCursor)
        self.zout.setStyleSheet(btn_css)
        self.zout.clicked.connect(self.zoom_out_clicked.emit)
        lo.addWidget(self.zout)

        # Fit
        self.fit_btn = QPushButton()
        self.fit_btn.setIcon(get_icon("maximize", 14, QColor(255, 255, 255, 180)))
        self.fit_btn.setFixedSize(32, 32)
        self.fit_btn.setCursor(Qt.PointingHandCursor)
        self.fit_btn.setStyleSheet(btn_css)
        self.fit_btn.clicked.connect(self.fit_clicked.emit)
        lo.addWidget(self.fit_btn)

        # Zoom in
        self.zin = QPushButton("+")
        self.zin.setFixedSize(32, 32)
        self.zin.setFont(QFont("Segoe UI", 14))
        self.zin.setCursor(Qt.PointingHandCursor)
        self.zin.setStyleSheet(btn_css)
        self.zin.clicked.connect(self.zoom_in_clicked.emit)
        lo.addWidget(self.zin)

        # Rotate
        self.rot_btn = QPushButton()
        self.rot_btn.setIcon(get_icon("refresh", 14, QColor(255, 255, 255, 180)))
        self.rot_btn.setFixedSize(32, 32)
        self.rot_btn.setCursor(Qt.PointingHandCursor)
        self.rot_btn.setStyleSheet(btn_css)
        self.rot_btn.setToolTip("Rotate")
        self.rot_btn.clicked.connect(self.rotate_clicked.emit)
        lo.addWidget(self.rot_btn)

    def set_counter(self, current, total):
        self.counter_label.setText(f"{current}/{total}" if total > 0 else "")
        self.prev_btn.setEnabled(current > 1)
        self.next_btn.setEnabled(current < total)

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(28, 28, 30))
        p.setPen(QColor(255, 255, 255, 5))
        p.drawLine(0, 0, self.width(), 0)
        p.end()


class App(QWidget):
    def __init__(self, file_system=None, parent=None):
        super().__init__(parent)
        self.fs = file_system
        self._images = []
        self._index = -1

        lo = QVBoxLayout(self)
        lo.setContentsMargins(0, 0, 0, 0)
        lo.setSpacing(0)

        # Info bar top
        self._info = QWidget()
        self._info.setFixedHeight(32)
        self._info_text = ""
        lo.addWidget(self._info)

        # Viewport
        self.viewport = ImageViewport()
        lo.addWidget(self.viewport, 1)

        # Bottom bar
        self.bar = BottomBar()
        self.bar.open_clicked.connect(self._open)
        self.bar.prev_clicked.connect(self._prev)
        self.bar.next_clicked.connect(self._next)
        self.bar.rotate_clicked.connect(self.viewport.rotate_cw)
        self.bar.fit_clicked.connect(self.viewport.fit_view)
        self.bar.zoom_in_clicked.connect(lambda: self._zoom(1.3))
        self.bar.zoom_out_clicked.connect(lambda: self._zoom(1 / 1.3))
        lo.addWidget(self.bar)

    def _zoom(self, factor):
        self.viewport._fit_mode = False
        self.viewport._zoom = max(0.05, min(20, self.viewport._zoom * factor))
        self.viewport.update()

    def _open(self):
        start = self.fs.get_base_path() if self.fs else os.path.expanduser("~")
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Image", start,
            "Images (*.jpg *.jpeg *.png *.webp *.svg *.gif *.bmp *.avif *.ico);;All (*)"
        )
        if path:
            self._load(path)

    def open_file(self, path):
        """API publique pour ouvrir depuis le desktop."""
        self._load(path)

    def _load(self, path):
        # Scanner le dossier
        folder = os.path.dirname(path)
        self._images = []
        try:
            for f in sorted(os.listdir(folder)):
                if os.path.splitext(f)[1].lower() in IMAGE_EXTS:
                    self._images.append(os.path.join(folder, f))
        except:
            self._images = [path]

        if path in self._images:
            self._index = self._images.index(path)
        else:
            self._images = [path]
            self._index = 0

        self._show_current()

    def _show_current(self):
        if 0 <= self._index < len(self._images):
            path = self._images[self._index]
            reader = QImageReader(path)
            reader.setAutoTransform(True)
            img = reader.read()
            if not img.isNull():
                self.viewport.set_image(QPixmap.fromImage(img))
            else:
                self.viewport.set_image(None)
            self._info_text = os.path.basename(path)
            self.bar.set_counter(self._index + 1, len(self._images))
            self._info.update()

    def _prev(self):
        if self._index > 0:
            self._index -= 1
            self._show_current()

    def _next(self):
        if self._index < len(self._images) - 1:
            self._index += 1
            self._show_current()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Left:
            self._prev()
        elif event.key() == Qt.Key_Right:
            self._next()
        elif event.key() == Qt.Key_R:
            self.viewport.rotate_cw()
        elif event.key() == Qt.Key_Plus or event.key() == Qt.Key_Equal:
            self._zoom(1.3)
        elif event.key() == Qt.Key_Minus:
            self._zoom(1 / 1.3)
        elif event.key() == Qt.Key_0:
            self.viewport.fit_view()