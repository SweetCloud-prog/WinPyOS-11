"""
WinPy11 3D Viewer
Formats : OBJ, STL, PLY, GLB, GLTF, FBX, 3DS
"""
import os
import sys
import math
import struct
import time
import threading
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QFileDialog, QSizePolicy
)
from PySide6.QtCore import (
    Qt, Signal, QTimer, QRectF, QRect, QPointF,
    QPropertyAnimation, QEasingCurve, Property
)
from PySide6.QtGui import (
    QFont, QColor, QPainter, QPen, QPainterPath,
    QVector3D, QMatrix4x4, QLinearGradient
)

from core.icons import get_icon, get_pixmap

ACCENT = QColor(0, 103, 192)
MODELS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")
os.makedirs(MODELS_DIR, exist_ok=True)

MODE_SOLID = 0
MODE_CLAY = 1
MODE_WIRE = 2


# ═══════════════════════════════════════════════════════
#  MESH
# ═══════════════════════════════════════════════════════

class Triangle:
    __slots__ = ['v0', 'v1', 'v2', 'normal']

    def __init__(self, v0, v1, v2, normal=None):
        self.v0 = np.asarray(v0, dtype=np.float64)
        self.v1 = np.asarray(v1, dtype=np.float64)
        self.v2 = np.asarray(v2, dtype=np.float64)
        if normal is not None:
            self.normal = np.asarray(normal, dtype=np.float64)
        else:
            e1 = self.v1 - self.v0
            e2 = self.v2 - self.v0
            n = np.cross(e1, e2)
            ln = np.linalg.norm(n)
            self.normal = n / ln if ln > 1e-10 else np.array([0.0, 1.0, 0.0])


class Mesh:
    def __init__(self):
        self.triangles = []
        self.center = np.zeros(3)
        self.scale = 1.0
        self.name = ""

    def compute_bounds(self):
        if not self.triangles:
            return
        verts = np.array([[t.v0, t.v1, t.v2] for t in self.triangles]).reshape(-1, 3)
        mn = verts.min(axis=0)
        mx = verts.max(axis=0)
        self.center = (mn + mx) / 2.0
        self.scale = 2.0 / max(np.linalg.norm(mx - mn), 1e-6)


# ═══════════════════════════════════════════════════════
#  LOADERS
# ═══════════════════════════════════════════════════════

def _load_obj(path):
    mesh = Mesh()
    mesh.name = os.path.basename(path)
    verts, norms = [], []
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            parts = line.strip().split()
            if not parts:
                continue
            if parts[0] == 'v' and len(parts) >= 4:
                verts.append([float(parts[1]), float(parts[2]), float(parts[3])])
            elif parts[0] == 'vn' and len(parts) >= 4:
                norms.append([float(parts[1]), float(parts[2]), float(parts[3])])
            elif parts[0] == 'f':
                fv, fn = [], []
                for p in parts[1:]:
                    idx = p.split('/')
                    vi = int(idx[0]) - 1
                    if 0 <= vi < len(verts):
                        fv.append(verts[vi])
                    if len(idx) >= 3 and idx[2]:
                        ni = int(idx[2]) - 1
                        if 0 <= ni < len(norms):
                            fn.append(norms[ni])
                for i in range(1, len(fv) - 1):
                    n = fn[0] if fn else None
                    mesh.triangles.append(Triangle(fv[0], fv[i], fv[i + 1], n))
    mesh.compute_bounds()
    return mesh


def _load_stl(path):
    mesh = Mesh()
    mesh.name = os.path.basename(path)
    with open(path, 'rb') as f:
        header = f.read(80)
        f.seek(0)
        content = f.read()

    # ASCII check
    try:
        text = content.decode('utf-8', errors='ignore')
        if 'facet normal' in text[:1000]:
            import re
            np_re = re.compile(r'facet\s+normal\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s+([\d.eE+-]+)')
            vp_re = re.compile(r'vertex\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s+([\d.eE+-]+)')
            cn, cv = None, []
            for line in text.split('\n'):
                line = line.strip()
                m = np_re.match(line)
                if m:
                    cn = [float(m.group(1)), float(m.group(2)), float(m.group(3))]
                    cv = []
                    continue
                m = vp_re.match(line)
                if m:
                    cv.append([float(m.group(1)), float(m.group(2)), float(m.group(3))])
                    if len(cv) == 3:
                        mesh.triangles.append(Triangle(cv[0], cv[1], cv[2], cn))
                        cv = []
            mesh.compute_bounds()
            return mesh
    except Exception:
        pass

    # Binary
    data = content[80:]
    if len(data) < 4:
        mesh.compute_bounds()
        return mesh
    num = struct.unpack('<I', data[:4])[0]
    offset = 4
    for _ in range(num):
        if offset + 50 > len(data):
            break
        vals = struct.unpack('<12fH', data[offset:offset + 50])
        mesh.triangles.append(Triangle(vals[3:6], vals[6:9], vals[9:12], vals[0:3]))
        offset += 50
    mesh.compute_bounds()
    return mesh


def _load_ply(path):
    mesh = Mesh()
    mesh.name = os.path.basename(path)
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    hdr_end, nv, nf = 0, 0, 0
    for i, line in enumerate(lines):
        l = line.strip()
        if l.startswith('element vertex'):
            nv = int(l.split()[-1])
        elif l.startswith('element face'):
            nf = int(l.split()[-1])
        elif l == 'end_header':
            hdr_end = i + 1
            break
    verts = []
    for i in range(hdr_end, hdr_end + nv):
        p = lines[i].strip().split()
        if len(p) >= 3:
            verts.append([float(p[0]), float(p[1]), float(p[2])])
    for i in range(hdr_end + nv, hdr_end + nv + nf):
        p = lines[i].strip().split()
        if len(p) >= 4:
            ids = [int(p[j + 1]) for j in range(int(p[0]))]
            for j in range(1, len(ids) - 1):
                if all(0 <= ids[k] < len(verts) for k in [0, j, j + 1]):
                    mesh.triangles.append(Triangle(verts[ids[0]], verts[ids[j]], verts[ids[j + 1]]))
    mesh.compute_bounds()
    return mesh


def _load_trimesh(path):
    try:
        import trimesh
        scene = trimesh.load(path, force='mesh')
        if isinstance(scene, trimesh.Scene):
            scene = trimesh.util.concatenate(scene.dump())
        mesh = Mesh()
        mesh.name = os.path.basename(path)
        v = np.array(scene.vertices, dtype=np.float64)
        f = np.array(scene.faces, dtype=np.int32)
        fn = np.array(scene.face_normals, dtype=np.float64) if scene.face_normals is not None else None
        for i, face in enumerate(f):
            n = fn[i] if fn is not None and i < len(fn) else None
            mesh.triangles.append(Triangle(v[face[0]], v[face[1]], v[face[2]], n))
        mesh.compute_bounds()
        return mesh
    except Exception as e:
        print(f"[3DViewer] trimesh: {e}")
        return None


def load_mesh(path):
    ext = path.rsplit('.', 1)[-1].lower() if '.' in path else ''
    loaders = {'obj': _load_obj, 'stl': _load_stl, 'ply': _load_ply}
    if ext in loaders:
        try:
            return loaders[ext](path)
        except Exception as e:
            print(f"[3DViewer] {ext}: {e}")
    return _load_trimesh(path)


def _ensure_default_cube():
    p = os.path.join(MODELS_DIR, "cube.obj")
    if os.path.exists(p):
        return p
    with open(p, 'w') as f:
        f.write("# Cube\n")
        for v in [(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1),(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1)]:
            f.write(f"v {v[0]} {v[1]} {v[2]}\n")
        for face in [(1,2,3,4),(5,8,7,6),(1,4,8,5),(2,6,7,3),(4,3,7,8),(1,5,6,2)]:
            f.write(f"f {' '.join(str(i) for i in face)}\n")
    return p


# ═══════════════════════════════════════════════════════
#  CAMERA
# ═══════════════════════════════════════════════════════

class Camera:
    def __init__(self):
        self.dist = 4.0
        self.rx = 25.0
        self.ry = -35.0
        self.px = 0.0
        self.py = 0.0

    def view(self):
        m = QMatrix4x4()
        m.translate(self.px, self.py, -self.dist)
        m.rotate(self.rx, 1, 0, 0)
        m.rotate(self.ry, 0, 1, 0)
        return m

    def proj(self, aspect):
        m = QMatrix4x4()
        m.perspective(45.0, aspect, 0.01, 100.0)
        return m


# ═══════════════════════════════════════════════════════
#  VIEWPORT — le rendu 3D plein écran
# ═══════════════════════════════════════════════════════

class Viewport(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)

        self.mesh = None
        self.cam = Camera()
        self.mode = MODE_SOLID
        self._last_m = None
        self._rot = False
        self._pan = False
        self._auto = True

        # Loading state
        self._loading = False
        self._load_progress = ""
        self._load_dots = 0

        # Spinner animation
        self._spinner_angle = 0.0
        self._spinner_anim = QPropertyAnimation(self, b"spinner_angle")
        self._spinner_anim.setDuration(1200)
        self._spinner_anim.setStartValue(0.0)
        self._spinner_anim.setEndValue(360.0)
        self._spinner_anim.setLoopCount(-1)
        self._spinner_anim.setEasingCurve(QEasingCurve.Linear)

        self._light = np.array([0.4, 0.7, 0.5])
        self._light = self._light / np.linalg.norm(self._light)

        self._tick_timer = QTimer(self)
        self._tick_timer.timeout.connect(self._tick)
        self._tick_timer.start(16)

    def get_spinner_angle(self):
        return self._spinner_angle

    def set_spinner_angle(self, v):
        self._spinner_angle = v
        if self._loading:
            self.update()

    spinner_angle = Property(float, get_spinner_angle, set_spinner_angle)

    def set_loading(self, loading, text=""):
        self._loading = loading
        self._load_progress = text
        if loading:
            self._spinner_anim.start()
        else:
            self._spinner_anim.stop()
        self.update()

    def set_mesh(self, mesh):
        self.mesh = mesh
        self._loading = False
        self._spinner_anim.stop()
        if mesh:
            self.cam.dist = 3.5 / mesh.scale
            self.cam.rx = 25
            self.cam.ry = -35
            self.cam.px = 0
            self.cam.py = 0
            self._auto = False
        self.update()

    def set_mode(self, mode):
        self.mode = mode
        self.update()

    def _tick(self):
        if self._auto and self.mesh:
            self.cam.ry += 0.3
            self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        w, h = self.width(), self.height()

        # Background
        bg = QLinearGradient(0, 0, 0, h)
        bg.setColorAt(0.0, QColor(32, 32, 35))
        bg.setColorAt(1.0, QColor(20, 20, 22))
        p.fillRect(self.rect(), bg)

        # Grid
        self._draw_grid(p, w, h)

        # Loading state
        if self._loading:
            self._draw_loading(p, w, h)
            p.end()
            return

        # Empty state
        if not self.mesh or not self.mesh.triangles:
            p.setFont(QFont("Segoe UI", 13))
            p.setPen(QColor(255, 255, 255, 50))
            p.drawText(self.rect(), Qt.AlignCenter, "Open a 3D model to start")

            # Icône
            px = get_pixmap("folder_open", 48, QColor(255, 255, 255, 30))
            p.drawPixmap((w - 48) // 2, h // 2 - 60, px)
            p.end()
            return

        # Render mesh
        self._render(p, w, h)

        # Info bottom-left
        p.setFont(QFont("Segoe UI", 8))
        p.setPen(QColor(255, 255, 255, 70))
        tc = len(self.mesh.triangles)
        info = f"{self.mesh.name}   ·   {tc:,} triangles   ·   {tc * 3:,} vertices"
        p.drawText(QRect(10, h - 22, w - 20, 16), Qt.AlignLeft | Qt.AlignVCenter, info)

        p.end()

    def _draw_loading(self, p, w, h):
        """Affiche l'écran de chargement avec spinner."""
        cx, cy = w // 2, h // 2

        # Spinner circle
        p.setPen(QPen(QColor(255, 255, 255, 20), 3))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QPointF(cx, cy - 20), 22, 22)

        # Spinner arc animé
        p.setPen(QPen(ACCENT, 3))
        start_angle = int(self._spinner_angle * 16)
        p.drawArc(QRect(cx - 22, cy - 42, 44, 44), start_angle, 90 * 16)

        # Texte
        p.setFont(QFont("Segoe UI Semibold", 11))
        p.setPen(QColor(255, 255, 255, 180))
        p.drawText(QRect(0, cy + 14, w, 24), Qt.AlignCenter, "Loading model...")

        if self._load_progress:
            p.setFont(QFont("Segoe UI", 9))
            p.setPen(QColor(255, 255, 255, 80))
            p.drawText(QRect(0, cy + 38, w, 20), Qt.AlignCenter, self._load_progress)

    def _draw_grid(self, p, w, h):
        view = self.cam.view()
        proj = self.cam.proj(w / max(h, 1))
        mvp = proj * view
        p.setPen(QPen(QColor(255, 255, 255, 12), 1))
        gs = 8
        for i in range(-gs, gs + 1):
            for a, b in [((i, 0, -gs), (i, 0, gs)), ((-gs, 0, i), (gs, 0, i))]:
                pa = self._proj(a, mvp, w, h)
                pb = self._proj(b, mvp, w, h)
                if pa and pb:
                    p.drawLine(QPointF(*pa[:2]), QPointF(*pb[:2]))

    def _proj(self, pt, mvp, w, h):
        v = QVector3D(float(pt[0]), float(pt[1]), float(pt[2]))
        r = mvp.map(v)
        if abs(r.z()) > 1.5:
            return None
        return ((r.x() * 0.5 + 0.5) * w, (0.5 - r.y() * 0.5) * h, r.z())

    def _render(self, p, w, h):
        view = self.cam.view()
        proj = self.cam.proj(w / max(h, 1))
        model = QMatrix4x4()
        model.scale(self.mesh.scale)
        model.translate(-self.mesh.center[0], -self.mesh.center[1], -self.mesh.center[2])
        mvp = proj * view * model

        # Project all triangles
        buf = []
        for tri in self.mesh.triangles:
            p0 = self._proj(tri.v0, mvp, w, h)
            p1 = self._proj(tri.v1, mvp, w, h)
            p2 = self._proj(tri.v2, mvp, w, h)
            if not (p0 and p1 and p2):
                continue

            # Backface cull (sauf wireframe)
            cross = (p1[0] - p0[0]) * (p2[1] - p0[1]) - (p1[1] - p0[1]) * (p2[0] - p0[0])
            if self.mode != MODE_WIRE and cross > 0:
                continue

            depth = (p0[2] + p1[2] + p2[2]) / 3.0
            buf.append((depth, p0, p1, p2, tri))

        buf.sort(key=lambda x: -x[0])

        for depth, p0, p1, p2, tri in buf:
            path = QPainterPath()
            path.moveTo(p0[0], p0[1])
            path.lineTo(p1[0], p1[1])
            path.lineTo(p2[0], p2[1])
            path.closeSubpath()

            if self.mode == MODE_WIRE:
                p.setPen(QPen(QColor(0, 200, 255, 100), 1))
                p.setBrush(Qt.NoBrush)
                p.drawPath(path)
                continue

            dot = max(0.0, float(np.dot(tri.normal, self._light)))
            intensity = 0.22 + 0.78 * dot

            if self.mode == MODE_SOLID:
                r = min(255, int(55 * intensity + 10))
                g = min(255, int(135 * intensity + 15))
                b = min(255, int(215 * intensity + 20))
                c = QColor(r, g, b)
            else:
                v = min(255, int(210 * intensity + 15))
                c = QColor(v, v, v)

            p.setPen(QPen(c.darker(115), 0.3))
            p.setBrush(c)
            p.drawPath(path)

    # ═══ Mouse ═══

    def mousePressEvent(self, event):
        self._last_m = event.position()
        self._auto = False
        if event.button() == Qt.LeftButton:
            self._rot = True
        elif event.button() in (Qt.MiddleButton, Qt.RightButton):
            self._pan = True

    def mouseMoveEvent(self, event):
        if self._last_m is None:
            return
        dx = event.position().x() - self._last_m.x()
        dy = event.position().y() - self._last_m.y()
        self._last_m = event.position()
        if self._rot:
            self.cam.ry += dx * 0.5
            self.cam.rx = max(-89, min(89, self.cam.rx + dy * 0.5))
            self.update()
        elif self._pan:
            self.cam.px += dx * 0.004 * self.cam.dist
            self.cam.py -= dy * 0.004 * self.cam.dist
            self.update()

    def mouseReleaseEvent(self, event):
        self._rot = False
        self._pan = False

    def wheelEvent(self, event):
        self._auto = False
        f = 0.9 if event.angleDelta().y() > 0 else 1.1
        self.cam.dist = max(0.3, min(80, self.cam.dist * f))
        self.update()


# ═══════════════════════════════════════════════════════
#  DOCK BUTTON
# ═══════════════════════════════════════════════════════

class DockBtn(QWidget):
    clicked = Signal()

    def __init__(self, label, active=False, parent=None):
        super().__init__(parent)
        self.label = label
        self.active = active
        self._hover = False
        self.setFixedSize(64, 38)
        self.setCursor(Qt.PointingHandCursor)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)

        r = QRectF(2, 2, self.width() - 4, self.height() - 4)

        if self.active:
            p.setBrush(QColor(ACCENT.red(), ACCENT.green(), ACCENT.blue(), 35))
            p.setPen(QPen(QColor(ACCENT.red(), ACCENT.green(), ACCENT.blue(), 120), 1))
            p.drawRoundedRect(r, 7, 7)
        elif self._hover:
            p.setBrush(QColor(255, 255, 255, 10))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(r, 7, 7)

        p.setFont(QFont("Segoe UI", 9))
        p.setPen(QColor(255, 255, 255, 220 if self.active else 150))
        p.drawText(self.rect(), Qt.AlignCenter, self.label)

        if self.active:
            p.setPen(Qt.NoPen)
            p.setBrush(ACCENT)
            p.drawRoundedRect((self.width() - 14) // 2, self.height() - 4, 14, 2.5, 1, 1)

        p.end()

    def enterEvent(self, e):
        self._hover = True; self.update()

    def leaveEvent(self, e):
        self._hover = False; self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()


# ═══════════════════════════════════════════════════════
#  FLOATING DOCK — transparent, flotte au-dessus
# ═══════════════════════════════════════════════════════

class FloatingDock(QWidget):
    """Dock flottant en overlay au-dessus du viewport."""
    mode_changed = Signal(int)
    browse_clicked = Signal()

    DOCK_H = 52
    DOCK_W = 380

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setFixedHeight(self.DOCK_H)

        lo = QHBoxLayout(self)
        lo.setContentsMargins(16, 6, 16, 6)
        lo.setSpacing(8)

        # Browse
        self.browse = QPushButton("  Open")
        self.browse.setIcon(get_icon("folder_open", 14, QColor(255, 255, 255, 200)))
        self.browse.setFixedHeight(34)
        self.browse.setFont(QFont("Segoe UI", 9))
        self.browse.setCursor(Qt.PointingHandCursor)
        self.browse.setStyleSheet("""
            QPushButton{background:rgba(255,255,255,8);border:1px solid rgba(255,255,255,10);
            border-radius:7px;color:white;padding:0 14px;}
            QPushButton:hover{background:rgba(255,255,255,14);}
        """)
        self.browse.clicked.connect(self.browse_clicked.emit)
        lo.addWidget(self.browse)

        # Separator
        sep = QWidget()
        sep.setFixedSize(1, 24)
        sep.setStyleSheet("background:rgba(255,255,255,10);")
        lo.addWidget(sep)

        # Mode buttons
        self._btns = []
        for label, mode in [("Solid", MODE_SOLID), ("Clay", MODE_CLAY), ("Wire", MODE_WIRE)]:
            btn = DockBtn(label, active=(mode == MODE_SOLID))
            btn.clicked.connect(lambda m=mode: self._set_mode(m))
            lo.addWidget(btn)
            self._btns.append((btn, mode))

    def _set_mode(self, mode):
        for btn, m in self._btns:
            btn.active = (m == mode)
            btn.update()
        self.mode_changed.emit(mode)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        # Fond pill
        r = QRectF(0, 0, self.width(), self.height())
        path = QPainterPath()
        path.addRoundedRect(r, 14, 14)
        p.setClipPath(path)
        p.fillRect(r, QColor(30, 30, 30, 220))
        p.setClipping(False)

        p.setPen(QPen(QColor(255, 255, 255, 8), 1))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(r.adjusted(.5, .5, -.5, -.5), 14, 14)
        p.end()


# ═══════════════════════════════════════════════════════
#  APP — compose viewport + dock overlay
# ═══════════════════════════════════════════════════════

class App(QWidget):
    def __init__(self, file_system=None, parent=None):
        super().__init__(parent)
        self.fs = file_system

        # Layout : viewport prend tout l'espace
        lo = QVBoxLayout(self)
        lo.setContentsMargins(0, 0, 0, 0)
        lo.setSpacing(0)

        self.viewport = Viewport()
        lo.addWidget(self.viewport, 1)

        # Le dock flotte AU-DESSUS du viewport (overlay)
        self.dock = FloatingDock(self)
        self.dock.mode_changed.connect(self.viewport.set_mode)
        self.dock.browse_clicked.connect(self._browse)

        # Position initiale
        self._position_dock()

        # Charger le cube par défaut
        QTimer.singleShot(50, self._load_default)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._position_dock()

    def _position_dock(self):
        """Centre le dock en bas, flottant au-dessus."""
        dw = min(self.dock.DOCK_W, self.width() - 40)
        self.dock.setFixedWidth(dw)
        x = (self.width() - dw) // 2
        y = self.height() - self.dock.DOCK_H - 16
        self.dock.move(x, y)
        self.dock.raise_()

    def _load_default(self):
        path = _ensure_default_cube()
        self.viewport.set_loading(True, "Loading default cube...")
        QTimer.singleShot(200, lambda: self._do_load(path, auto_rotate=True))

    def _browse(self):
        start = MODELS_DIR
        if self.fs:
            start = self.fs.get_base_path()
        path, _ = QFileDialog.getOpenFileName(
            self, "Open 3D Model", start,
            "3D Models (*.obj *.stl *.ply *.glb *.gltf *.fbx *.3ds *.off);;All (*)"
        )
        if path:
            self.viewport.set_loading(True, os.path.basename(path))
            # Charger en arrière-plan pour ne pas bloquer l'UI
            QTimer.singleShot(50, lambda: self._do_load(path))

    def _do_load(self, path, auto_rotate=False):
        """Charge le mesh (appelé via timer pour laisser l'UI se rafraîchir)."""
        self.viewport.set_loading(True, f"Parsing {os.path.basename(path)}...")
        self.viewport.update()

        # On force un repaint avant le chargement bloquant
        from PySide6.QtWidgets import QApplication
        QApplication.processEvents()

        t0 = time.time()
        mesh = load_mesh(path)
        dt = time.time() - t0

        if mesh and mesh.triangles:
            self.viewport.set_loading(True, f"Loaded {len(mesh.triangles):,} triangles in {dt:.1f}s")
            QApplication.processEvents()
            QTimer.singleShot(400, lambda: self._finish_load(mesh, auto_rotate))
        else:
            self.viewport.set_loading(False)
            self.viewport.mesh = None
            self.viewport.update()

    def _finish_load(self, mesh, auto_rotate=False):
        self.viewport.set_mesh(mesh)
        if auto_rotate:
            self.viewport._auto = True