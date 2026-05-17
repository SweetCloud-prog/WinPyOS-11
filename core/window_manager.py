from PySide6.QtWidgets import QWidget, QVBoxLayout, QGraphicsDropShadowEffect
from PySide6.QtCore import Qt, Signal, QRect, QRectF, QPoint
from PySide6.QtGui import QFont, QColor, QPainter, QPen, QPainterPath

from core.icons import get_pixmap

ACCENT = QColor(0, 103, 192)
RADIUS = 8
EDGE_SIZE = 8  # Zone de détection pour le resize


class TitleBar(QWidget):
    close_clicked = Signal()
    minimize_clicked = Signal()
    maximize_clicked = Signal()

    def __init__(self, title, icon_name, parent=None):
        super().__init__(parent)
        self.setFixedHeight(32)
        self._title = title
        self._icon_px = get_pixmap(icon_name, 16)
        self._drag_pos = None
        self._hovered = None
        self.setMouseTracking(True)

    def _btn_rects(self):
        w = self.width()
        bw = 46
        return {
            "min": QRect(w - bw * 3, 0, bw, 32),
            "max": QRect(w - bw * 2, 0, bw, 32),
            "close": QRect(w - bw, 0, bw, 32),
        }

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)

        p.drawPixmap(10, 8, self._icon_px)

        p.setFont(QFont("Segoe UI", 9))
        p.setPen(QColor(255, 255, 255, 175))
        p.drawText(QRect(32, 0, self.width() - 180, 32), Qt.AlignVCenter, self._title)

        rects = self._btn_rects()

        # Minimize
        r = rects["min"]
        if self._hovered == "min":
            p.fillRect(r, QColor(255, 255, 255, 16))
        p.setPen(QPen(QColor(255, 255, 255, 180), 1))
        p.drawLine(r.x() + 18, 16, r.x() + 28, 16)

        # Maximize / Restore
        r = rects["max"]
        if self._hovered == "max":
            p.fillRect(r, QColor(255, 255, 255, 16))
        p.setPen(QPen(QColor(255, 255, 255, 180), 1))
        p.setBrush(Qt.NoBrush)
        pw = self.parent()
        if pw and hasattr(pw, '_maximized') and pw._maximized:
            p.drawRect(r.x() + 20, 10, 7, 7)
            p.drawRect(r.x() + 17, 13, 7, 7)
        else:
            p.drawRect(r.x() + 18, 10, 9, 9)

        # Close
        r = rects["close"]
        if self._hovered == "close":
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(196, 43, 28))
            path = QPainterPath()
            path.moveTo(r.x(), r.y())
            path.lineTo(r.right() - RADIUS, r.y())
            path.quadTo(r.right(), r.y(), r.right(), r.y() + RADIUS)
            path.lineTo(r.right(), r.bottom())
            path.lineTo(r.x(), r.bottom())
            path.closeSubpath()
            p.drawPath(path)

        cx = r.center().x()
        cy = r.center().y()
        p.setPen(QPen(QColor(255, 255, 255, 220 if self._hovered == "close" else 180), 1.2))
        p.drawLine(cx - 5, cy - 5, cx + 5, cy + 5)
        p.drawLine(cx + 5, cy - 5, cx - 5, cy + 5)
        p.end()

    def _hit(self, pos):
        for name, rect in self._btn_rects().items():
            if rect.contains(pos):
                return name
        return None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            h = self._hit(event.position().toPoint())
            if h == "close":
                self.close_clicked.emit()
            elif h == "min":
                self.minimize_clicked.emit()
            elif h == "max":
                self.maximize_clicked.emit()
            else:
                self._drag_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None:
            pw = self.parent()
            if pw and hasattr(pw, '_maximized') and pw._maximized:
                old_w = pw.width()
                pw.toggle_maximize()
                ratio = event.position().x() / max(old_w, 1)
                new_x = int(event.globalPosition().x() - pw.width() * ratio)
                pw.move(new_x, 0)
                self._drag_pos = event.globalPosition().toPoint()
                return
            if pw:
                delta = event.globalPosition().toPoint() - self._drag_pos
                pw.move(pw.pos() + delta)
                self._drag_pos = event.globalPosition().toPoint()
        else:
            old = self._hovered
            self._hovered = self._hit(event.position().toPoint())
            if old != self._hovered:
                self.update()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton and not self._hit(event.position().toPoint()):
            self.maximize_clicked.emit()

    def leaveEvent(self, e):
        if self._hovered:
            self._hovered = None
            self.update()


class AppWindow(QWidget):
    closed = Signal(str)

    def __init__(self, title, app_id, icon_name, parent=None):
        super().__init__(parent)
        self.app_id = app_id
        self._maximized = False
        self._normal_geo = None
        self.setMouseTracking(True)
        self.setMinimumSize(420, 320)
        self.resize(840, 560)

        # Resize
        self._edge = ""
        self._resize_pos = None
        self._resize_geo = None

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(30)
        shadow.setOffset(0, 5)
        shadow.setColor(QColor(0, 0, 0, 100))
        self.setGraphicsEffect(shadow)

        lo = QVBoxLayout(self)
        lo.setContentsMargins(0, 0, 0, 0)
        lo.setSpacing(0)

        self.title_bar = TitleBar(title, icon_name, self)
        self.title_bar.close_clicked.connect(self.close_window)
        self.title_bar.minimize_clicked.connect(self.hide)
        self.title_bar.maximize_clicked.connect(self.toggle_maximize)
        lo.addWidget(self.title_bar)

        self.content_area = QWidget()
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        lo.addWidget(self.content_area, 1)

    def set_content(self, w):
        while self.content_layout.count():
            it = self.content_layout.takeAt(0)
            if it.widget():
                it.widget().setParent(None)
        self.content_layout.addWidget(w)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        rad = 0 if self._maximized else RADIUS
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), rad, rad)
        p.setClipPath(path)
        p.fillRect(self.rect(), QColor(32, 32, 32))
        if not self._maximized:
            p.setClipping(False)
            p.setPen(QPen(QColor(255, 255, 255, 12), 1))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(QRectF(self.rect()).adjusted(.5, .5, -.5, -.5), rad, rad)
        p.end()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not self._maximized:
            path = QPainterPath()
            path.addRoundedRect(QRectF(self.rect()), RADIUS, RADIUS)
            self.setMask(path.toFillPolygon().toPolygon())
        else:
            self.clearMask()

    def close_window(self):
        self.closed.emit(self.app_id)
        self.hide()
        self.deleteLater()

    def toggle_maximize(self):
        if self._maximized:
            if self._normal_geo:
                self.setGeometry(self._normal_geo)
            self._maximized = False
        else:
            self._normal_geo = self.geometry()
            par = self.parent()
            if par:
                self.setGeometry(0, 0, par.width(), par.height())
            self._maximized = True
        self.title_bar.update()
        self.update()

    # ═══════════════════════════════════════════
    #  EDGE DETECTION — 4 côtés + 4 coins
    # ═══════════════════════════════════════════

    def _detect_edge(self, pos):
        """
        Retourne une string décrivant le bord :
          "n", "s", "w", "e"           → côtés
          "nw", "ne", "sw", "se"       → coins
          ""                           → rien
        """
        if self._maximized:
            return ""

        x = pos.x()
        y = pos.y()
        w = self.width()
        h = self.height()
        m = EDGE_SIZE

        on_top = y < m
        on_bottom = y > h - m
        on_left = x < m
        on_right = x > w - m

        if on_top and on_left:
            return "nw"
        if on_top and on_right:
            return "ne"
        if on_bottom and on_left:
            return "sw"
        if on_bottom and on_right:
            return "se"
        if on_top:
            return "n"
        if on_bottom:
            return "s"
        if on_left:
            return "w"
        if on_right:
            return "e"

        return ""

    def _edge_cursor(self, edge):
        """Retourne le QCursor pour un bord donné."""
        if edge in ("n", "s"):
            return Qt.SizeVerCursor
        if edge in ("w", "e"):
            return Qt.SizeHorCursor
        if edge in ("nw", "se"):
            return Qt.SizeFDiagCursor
        if edge in ("ne", "sw"):
            return Qt.SizeBDiagCursor
        return Qt.ArrowCursor

    # ═══════════════════════════════════════════
    #  MOUSE EVENTS — resize
    # ═══════════════════════════════════════════

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            edge = self._detect_edge(event.position().toPoint())
            if edge:
                self._edge = edge
                self._resize_pos = event.globalPosition().toPoint()
                self._resize_geo = self.geometry()
                return

        # Mettre au premier plan
        self.raise_()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        # ── En cours de resize ──
        if self._edge and self._resize_pos is not None:
            gp = event.globalPosition().toPoint()
            dx = gp.x() - self._resize_pos.x()
            dy = gp.y() - self._resize_pos.y()
            geo = QRect(self._resize_geo)
            min_w = self.minimumWidth()
            min_h = self.minimumHeight()

            # Côté droit
            if "e" in self._edge:
                geo.setRight(max(geo.left() + min_w, self._resize_geo.right() + dx))

            # Côté gauche
            if "w" in self._edge:
                new_left = self._resize_geo.left() + dx
                if geo.right() - new_left >= min_w:
                    geo.setLeft(new_left)

            # Côté bas
            if "s" in self._edge:
                geo.setBottom(max(geo.top() + min_h, self._resize_geo.bottom() + dy))

            # Côté haut
            if "n" in self._edge:
                new_top = self._resize_geo.top() + dy
                if geo.bottom() - new_top >= min_h:
                    geo.setTop(new_top)

            self.setGeometry(geo)
            return

        # ── Hover : changer curseur ──
        if not self._maximized:
            edge = self._detect_edge(event.position().toPoint())
            self.setCursor(self._edge_cursor(edge))
        else:
            self.setCursor(Qt.ArrowCursor)

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._edge:
            self._edge = ""
            self._resize_pos = None
            self._resize_geo = None
            return
        super().mouseReleaseEvent(event)


class WindowManager:
    def __init__(self, desktop):
        self.desktop = desktop
        self.windows = {}
        self._n = 0

    def create_window(self, title, app_id, icon_name):
        self._n += 1
        iid = f"{app_id}_{self._n}"
        win = AppWindow(title, iid, icon_name, self.desktop.desktop_area)
        win.closed.connect(self._closed)
        off = (self._n % 8) * 30
        win.move(80 + off, 40 + off)
        self.windows[iid] = win
        return win

    def _closed(self, iid):
        self.windows.pop(iid, None)
        base = iid.rsplit("_", 1)[0]
        if not any(k.startswith(base + "_") for k in self.windows):
            self.desktop.app_closed(base)

    def toggle_window(self, app_id):
        for wid, win in self.windows.items():
            if wid.startswith(app_id + "_"):
                if win.isVisible():
                    win.hide()
                else:
                    win.show()
                    win.raise_()
                return