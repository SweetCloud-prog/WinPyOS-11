"""
WinPy11 3D Viewer — Optimisé
Rendu vectorisé numpy + cache image + LOD dynamique
"""
import os
import sys
import math
import struct
import time
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
    QMatrix4x4, QLinearGradient, QImage, QPolygonF, QVector3D
)

from core.icons import get_icon, get_pixmap

ACCENT = QColor(0, 103, 192)
MODELS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")
os.makedirs(MODELS_DIR, exist_ok=True)

MODE_SOLID = 0
MODE_CLAY = 1
MODE_WIRE = 2


# ═══════════════════════════════════════════════════════
#  MESH — stockage numpy optimisé
# ═══════════════════════════════════════════════════════

class OptimizedMesh:
    """
    Mesh stocké en arrays numpy contigus pour projection vectorisée.
    vertices: (N*3, 3) — tous les vertices de tous les triangles
    normals:  (N, 3)   — une normale par triangle
    """
    __slots__ = ['vertices', 'normals', 'tri_count', 'name', 'center', 'scale']

    def __init__(self):
        self.vertices = None  # shape (N*3, 3)
        self.normals = None  # shape (N, 3)
        self.tri_count = 0
        self.name = ""
        self.center = np.zeros(3, dtype=np.float32)
        self.scale = 1.0

    @staticmethod
    def from_raw(raw_verts, raw_normals, name=""):
        """
        raw_verts: list de (v0, v1, v2) tuples
        raw_normals: list de normal arrays
        """
        m = OptimizedMesh()
        m.name = name
        n = len(raw_verts)
        m.tri_count = n

        if n == 0:
            m.vertices = np.zeros((0, 3), dtype=np.float32)
            m.normals = np.zeros((0, 3), dtype=np.float32)
            return m

        # Pack vertices : [v0_0, v1_0, v2_0, v0_1, v1_1, v2_1, ...]
        m.vertices = np.array(raw_verts, dtype=np.float32).reshape(-1, 3)
        m.normals = np.array(raw_normals, dtype=np.float32).reshape(-1, 3)

        # Normalize normals
        norms = np.linalg.norm(m.normals, axis=1, keepdims=True)
        norms = np.where(norms < 1e-8, 1.0, norms)
        m.normals = m.normals / norms

        # Bounds
        mn = m.vertices.min(axis=0)
        mx = m.vertices.max(axis=0)
        m.center = (mn + mx) / 2.0
        extent = np.linalg.norm(mx - mn)
        m.scale = 2.0 / max(extent, 1e-6)

        return m


# ═══════════════════════════════════════════════════════
#  LOADERS — retournent des OptimizedMesh
# ═══════════════════════════════════════════════════════

def _compute_normal(v0, v1, v2):
    e1 = v1 - v0
    e2 = v2 - v0
    n = np.cross(e1, e2)
    ln = np.linalg.norm(n)
    return n / ln if ln > 1e-10 else np.array([0, 1, 0], dtype=np.float32)


def _load_obj(path):
    verts_pool = []
    norms_pool = []
    raw_tris = []
    raw_normals = []

    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            parts = line.strip().split()
            if not parts:
                continue
            if parts[0] == 'v' and len(parts) >= 4:
                verts_pool.append([float(parts[1]), float(parts[2]), float(parts[3])])
            elif parts[0] == 'vn' and len(parts) >= 4:
                norms_pool.append([float(parts[1]), float(parts[2]), float(parts[3])])
            elif parts[0] == 'f':
                fv, fn = [], []
                for p in parts[1:]:
                    idx = p.split('/')
                    vi = int(idx[0]) - 1
                    if 0 <= vi < len(verts_pool):
                        fv.append(verts_pool[vi])
                    if len(idx) >= 3 and idx[2]:
                        ni = int(idx[2]) - 1
                        if 0 <= ni < len(norms_pool):
                            fn.append(norms_pool[ni])
                for i in range(1, len(fv) - 1):
                    v0 = np.array(fv[0], dtype=np.float32)
                    v1 = np.array(fv[i], dtype=np.float32)
                    v2 = np.array(fv[i + 1], dtype=np.float32)
                    n = np.array(fn[0], dtype=np.float32) if fn else _compute_normal(v0, v1, v2)
                    raw_tris.append((v0, v1, v2))
                    raw_normals.append(n)

    return OptimizedMesh.from_raw(raw_tris, raw_normals, os.path.basename(path))


def _load_stl(path):
    raw_tris = []
    raw_normals = []

    with open(path, 'rb') as f:
        content = f.read()

    # ASCII check
    try:
        text = content[:1000].decode('utf-8', errors='ignore')
        if 'facet normal' in text:
            import re
            text = content.decode('utf-8', errors='ignore')
            np_re = re.compile(r'facet\s+normal\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s+([\d.eE+-]+)')
            vp_re = re.compile(r'vertex\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s+([\d.eE+-]+)')
            cn, cv = None, []
            for line in text.split('\n'):
                line = line.strip()
                m = np_re.match(line)
                if m:
                    cn = np.array([float(m.group(1)), float(m.group(2)), float(m.group(3))], dtype=np.float32)
                    cv = []
                    continue
                m = vp_re.match(line)
                if m:
                    cv.append(np.array([float(m.group(1)), float(m.group(2)), float(m.group(3))], dtype=np.float32))
                    if len(cv) == 3:
                        raw_tris.append((cv[0], cv[1], cv[2]))
                        raw_normals.append(cn if cn is not None else _compute_normal(cv[0], cv[1], cv[2]))
                        cv = []
            return OptimizedMesh.from_raw(raw_tris, raw_normals, os.path.basename(path))
    except Exception:
        pass

    # Binary
    if len(content) < 84:
        return OptimizedMesh.from_raw([], [], os.path.basename(path))

    num = struct.unpack('<I', content[80:84])[0]
    offset = 84
    for _ in range(num):
        if offset + 50 > len(content):
            break
        vals = struct.unpack('<12fH', content[offset:offset + 50])
        n = np.array(vals[0:3], dtype=np.float32)
        v0 = np.array(vals[3:6], dtype=np.float32)
        v1 = np.array(vals[6:9], dtype=np.float32)
        v2 = np.array(vals[9:12], dtype=np.float32)
        raw_tris.append((v0, v1, v2))
        raw_normals.append(n)
        offset += 50

    return OptimizedMesh.from_raw(raw_tris, raw_normals, os.path.basename(path))


def _load_ply(path):
    raw_tris = []
    raw_normals = []

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
    for i in range(hdr_end, min(hdr_end + nv, len(lines))):
        p = lines[i].strip().split()
        if len(p) >= 3:
            verts.append(np.array([float(p[0]), float(p[1]), float(p[2])], dtype=np.float32))

    for i in range(hdr_end + nv, min(hdr_end + nv + nf, len(lines))):
        p = lines[i].strip().split()
        if len(p) >= 4:
            ids = [int(p[j + 1]) for j in range(int(p[0]))]
            for j in range(1, len(ids) - 1):
                if all(0 <= ids[k] < len(verts) for k in [0, j, j + 1]):
                    v0, v1, v2 = verts[ids[0]], verts[ids[j]], verts[ids[j + 1]]
                    raw_tris.append((v0, v1, v2))
                    raw_normals.append(_compute_normal(v0, v1, v2))

    return OptimizedMesh.from_raw(raw_tris, raw_normals, os.path.basename(path))


def _load_trimesh(path):
    try:
        import trimesh
        scene = trimesh.load(path, force='mesh')
        if isinstance(scene, trimesh.Scene):
            scene = trimesh.util.concatenate(scene.dump())

        v = np.array(scene.vertices, dtype=np.float32)
        f = np.array(scene.faces, dtype=np.int32)
        fn = np.array(scene.face_normals, dtype=np.float32) if scene.face_normals is not None else None

        raw_tris = []
        raw_normals = []
        for i, face in enumerate(f):
            v0, v1, v2 = v[face[0]], v[face[1]], v[face[2]]
            n = fn[i] if fn is not None and i < len(fn) else _compute_normal(v0, v1, v2)
            raw_tris.append((v0, v1, v2))
            raw_normals.append(n)

        return OptimizedMesh.from_raw(raw_tris, raw_normals, os.path.basename(path))
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


def _ensure_cube():
    p = os.path.join(MODELS_DIR, "cube.obj")
    if os.path.exists(p):
        return p
    with open(p, 'w') as f:
        f.write("# Cube\n")
        for v in [(-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1), (-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1)]:
            f.write(f"v {v[0]} {v[1]} {v[2]}\n")
        for face in [(1, 2, 3, 4), (5, 8, 7, 6), (1, 4, 8, 5), (2, 6, 7, 3), (4, 3, 7, 8), (1, 5, 6, 2)]:
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

    def mvp_numpy(self, aspect, mesh_scale, mesh_center):
        """Retourne la matrice MVP 4x4 en numpy pour projection vectorisée."""
        # Model
        model = np.eye(4, dtype=np.float32)
        model[0, 0] = model[1, 1] = model[2, 2] = mesh_scale
        model[0, 3] = -mesh_center[0] * mesh_scale
        model[1, 3] = -mesh_center[1] * mesh_scale
        model[2, 3] = -mesh_center[2] * mesh_scale

        # View
        rx = math.radians(self.rx)
        ry = math.radians(self.ry)

        crx, srx = math.cos(rx), math.sin(rx)
        cry, sry = math.cos(ry), math.sin(ry)

        rot_x = np.array([
            [1, 0, 0, 0],
            [0, crx, -srx, 0],
            [0, srx, crx, 0],
            [0, 0, 0, 1]
        ], dtype=np.float32)

        rot_y = np.array([
            [cry, 0, sry, 0],
            [0, 1, 0, 0],
            [-sry, 0, cry, 0],
            [0, 0, 0, 1]
        ], dtype=np.float32)

        trans = np.eye(4, dtype=np.float32)
        trans[0, 3] = self.px
        trans[1, 3] = self.py
        trans[2, 3] = -self.dist

        view = trans @ rot_x @ rot_y

        # Projection
        fov = math.radians(45.0)
        f = 1.0 / math.tan(fov / 2.0)
        near, far = 0.01, 100.0

        proj = np.zeros((4, 4), dtype=np.float32)
        proj[0, 0] = f / aspect
        proj[1, 1] = f
        proj[2, 2] = (far + near) / (near - far)
        proj[2, 3] = (2 * far * near) / (near - far)
        proj[3, 2] = -1.0

        return proj @ view @ model


# ═══════════════════════════════════════════════════════
#  VECTORIZED RENDERER — projection numpy batch
# ═══════════════════════════════════════════════════════

def render_to_image(mesh, cam, w, h, mode, light_dir, moving=False):
    """
    Rend le mesh dans un QImage via numpy vectorisé.
    Retourne (QImage, stats_string).
    """
    if not mesh or mesh.tri_count == 0:
        return None, ""

    aspect = w / max(h, 1)
    mvp = cam.mvp_numpy(aspect, mesh.scale, mesh.center)

    n_tris = mesh.tri_count
    verts = mesh.vertices  # (N*3, 3)

    # ═══ LOD : sous-échantillonner pendant le mouvement ═══
    max_tris = 80000 if not moving else 25000
    step = 1
    if n_tris > max_tris:
        step = max(1, n_tris // max_tris)

    # Indices des triangles à rendre
    tri_indices = np.arange(0, n_tris, step)
    n_render = len(tri_indices)

    # Extraire les vertices des triangles sélectionnés
    v_idx = np.repeat(tri_indices * 3, 3) + np.tile([0, 1, 2], n_render)
    sel_verts = verts[v_idx]  # (n_render*3, 3)

    # ═══ PROJECTION VECTORISÉE ═══
    # Homogeneous coords
    ones = np.ones((sel_verts.shape[0], 1), dtype=np.float32)
    v4 = np.hstack([sel_verts, ones])  # (N*3, 4)

    # Multiply by MVP
    clip = (mvp @ v4.T).T  # (N*3, 4)

    # Perspective divide
    w_clip = clip[:, 3:4]
    w_clip = np.where(np.abs(w_clip) < 1e-6, 1e-6, w_clip)
    ndc = clip[:, :3] / w_clip

    # Screen coords
    sx = (ndc[:, 0] * 0.5 + 0.5) * w
    sy = (0.5 - ndc[:, 1] * 0.5) * h
    sz = ndc[:, 2]

    # Reshape to triangles (n_render, 3, ...)
    sx = sx.reshape(n_render, 3)
    sy = sy.reshape(n_render, 3)
    sz = sz.reshape(n_render, 3)

    # ═══ CLIP : éliminer triangles hors écran ou derrière ═══
    z_max = sz.max(axis=1)
    z_min = sz.min(axis=1)
    x_min = sx.min(axis=1)
    x_max = sx.max(axis=1)
    y_min = sy.min(axis=1)
    y_max = sy.max(axis=1)

    visible = (z_max < 1.5) & (z_min > -1.5) & (x_max > -50) & (x_min < w + 50) & (y_max > -50) & (y_min < h + 50)

    # ═══ BACKFACE CULLING (sauf wireframe) ═══
    if mode != MODE_WIRE:
        e1x = sx[:, 1] - sx[:, 0]
        e1y = sy[:, 1] - sy[:, 0]
        e2x = sx[:, 2] - sx[:, 0]
        e2y = sy[:, 2] - sy[:, 0]
        cross = e1x * e2y - e1y * e2x
        visible = visible & (cross < 0)

    vis_idx = np.where(visible)[0]
    if len(vis_idx) == 0:
        return None, ""

    # ═══ DEPTH SORT ═══
    avg_z = sz[vis_idx].mean(axis=1)
    sort_order = np.argsort(-avg_z)
    vis_idx = vis_idx[sort_order]

    # ═══ LIGHTING ═══
    sel_normals = mesh.normals[tri_indices[vis_idx]]
    dots = np.clip(np.sum(sel_normals * light_dir, axis=1), 0.0, 1.0)
    intensities = 0.22 + 0.78 * dots

    # ═══ RENDER TO QIMAGE ═══
    img = QImage(w, h, QImage.Format_ARGB32_Premultiplied)
    img.fill(Qt.transparent)

    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing, not moving)  # Désactiver AA en mouvement

    n_drawn = 0

    if mode == MODE_WIRE:
        # Batch wireframe : dessiner tous les edges en une passe
        p.setPen(QPen(QColor(0, 200, 255, 90), 1))
        p.setBrush(Qt.NoBrush)

        for idx in vis_idx:
            poly = QPolygonF([
                QPointF(sx[idx, 0], sy[idx, 0]),
                QPointF(sx[idx, 1], sy[idx, 1]),
                QPointF(sx[idx, 2], sy[idx, 2]),
            ])
            p.drawPolygon(poly)
            n_drawn += 1
    else:
        # Solid / Clay avec éclairage
        p.setPen(Qt.NoPen)

        # Pré-calculer les couleurs
        if mode == MODE_SOLID:
            rs = np.clip((55 * intensities + 10), 0, 255).astype(np.int32)
            gs = np.clip((135 * intensities + 15), 0, 255).astype(np.int32)
            bs = np.clip((215 * intensities + 20), 0, 255).astype(np.int32)
        else:
            vs = np.clip((210 * intensities + 15), 0, 255).astype(np.int32)
            rs = gs = bs = vs

        for j, idx in enumerate(vis_idx):
            color = QColor(int(rs[j]), int(gs[j]), int(bs[j]))
            p.setBrush(color)

            if not moving:
                p.setPen(QPen(color.darker(112), 0.3))

            poly = QPolygonF([
                QPointF(sx[idx, 0], sy[idx, 0]),
                QPointF(sx[idx, 1], sy[idx, 1]),
                QPointF(sx[idx, 2], sy[idx, 2]),
            ])
            p.drawConvexPolygon(poly)
            n_drawn += 1

    p.end()

    stats = f"{n_drawn:,}/{mesh.tri_count:,} tris"
    if step > 1:
        stats += f" (LOD {step}x)"

    return img, stats


# ═══════════════════════════════════════════════════════
#  VIEWPORT
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
        self._rotating = False
        self._panning = False
        self._moving = False
        self._auto = True
        self._loading = False
        self._load_text = ""
        self._render_stats = ""

        # Cache
        self._cached_img = None
        self._cache_dirty = True
        self._cache_size = (0, 0)

        self._light = np.array([0.4, 0.7, 0.5], dtype=np.float32)
        self._light = self._light / np.linalg.norm(self._light)

        # Spinner
        self._spinner_angle = 0.0
        self._spinner_anim = QPropertyAnimation(self, b"spinner_angle")
        self._spinner_anim.setDuration(1000)
        self._spinner_anim.setStartValue(0.0)
        self._spinner_anim.setEndValue(360.0)
        self._spinner_anim.setLoopCount(-1)
        self._spinner_anim.setEasingCurve(QEasingCurve.Linear)

        # Move timeout : quand on arrête de bouger, refaire un rendu HQ
        self._move_timer = QTimer(self)
        self._move_timer.setSingleShot(True)
        self._move_timer.timeout.connect(self._on_move_end)

        # Tick pour auto-rotation
        self._tick_timer = QTimer(self)
        self._tick_timer.timeout.connect(self._tick)
        self._tick_timer.start(16)

        # FPS counter
        self._frame_times = []

    def get_spinner_angle(self):
        return self._spinner_angle

    def set_spinner_angle(self, v):
        self._spinner_angle = v
        if self._loading:
            self.update()

    spinner_angle = Property(float, get_spinner_angle, set_spinner_angle)

    def set_loading(self, loading, text=""):
        self._loading = loading
        self._load_text = text
        if loading:
            self._spinner_anim.start()
        else:
            self._spinner_anim.stop()
        self.update()

    def set_mesh(self, mesh):
        self.mesh = mesh
        self._loading = False
        self._spinner_anim.stop()
        self._cache_dirty = True
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
        self._cache_dirty = True
        self.update()

    def _invalidate(self):
        self._cache_dirty = True

    def _tick(self):
        if self._auto and self.mesh:
            self.cam.ry += 0.3
            self._cache_dirty = True
            self._moving = True
            self._move_timer.start(500)
            self.update()

    def _on_move_end(self):
        """Appelé quand on arrête de bouger → rendu haute qualité."""
        self._moving = False
        self._cache_dirty = True
        self.update()

    def paintEvent(self, event):
        t0 = time.perf_counter()
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

        # Loading
        if self._loading:
            self._draw_loading(p, w, h)
            p.end()
            return

        # Empty
        if not self.mesh or self.mesh.tri_count == 0:
            px = get_pixmap("folder_open", 48, QColor(255, 255, 255, 25))
            p.drawPixmap((w - 48) // 2, h // 2 - 55, px)
            p.setFont(QFont("Segoe UI", 12))
            p.setPen(QColor(255, 255, 255, 40))
            p.drawText(self.rect().adjusted(0, 20, 0, 0), Qt.AlignCenter, "Open a 3D model to start")
            p.end()
            return

        # ═══ RENDU 3D AVEC CACHE ═══
        if self._cache_dirty or self._cache_size != (w, h):
            img, stats = render_to_image(
                self.mesh, self.cam, w, h,
                self.mode, self._light, self._moving
            )
            if img:
                self._cached_img = img
                self._render_stats = stats
            self._cache_dirty = False
            self._cache_size = (w, h)

        if self._cached_img:
            p.drawImage(0, 0, self._cached_img)

        # Info overlay
        dt = time.perf_counter() - t0
        self._frame_times.append(dt)
        if len(self._frame_times) > 30:
            self._frame_times.pop(0)
        avg_dt = sum(self._frame_times) / len(self._frame_times)
        fps = int(1.0 / avg_dt) if avg_dt > 0 else 0

        p.setFont(QFont("Segoe UI", 8))
        p.setPen(QColor(255, 255, 255, 60))

        info = f"{self.mesh.name}   ·   {self._render_stats}   ·   {fps} fps"
        modes = ["Solid", "Clay", "Wireframe"]
        p.drawText(QRect(10, h - 22, w - 20, 16), Qt.AlignLeft, info)
        p.drawText(QRect(10, h - 22, w - 20, 16), Qt.AlignRight, modes[self.mode])

        if self._moving and self.mesh.tri_count > 25000:
            p.setFont(QFont("Segoe UI", 8))
            p.setPen(QColor(255, 255, 255, 40))
            p.drawText(QRect(10, 8, w - 20, 16), Qt.AlignRight, "LOD active — release to render full")

        p.end()

    def _draw_loading(self, p, w, h):
        cx, cy = w // 2, h // 2
        p.setPen(QPen(QColor(255, 255, 255, 18), 3))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QPointF(cx, cy - 20), 22, 22)
        p.setPen(QPen(ACCENT, 3))
        p.drawArc(QRect(cx - 22, cy - 42, 44, 44), int(self._spinner_angle * 16), 90 * 16)
        p.setFont(QFont("Segoe UI Semibold", 11))
        p.setPen(QColor(255, 255, 255, 170))
        p.drawText(QRect(0, cy + 14, w, 24), Qt.AlignCenter, "Loading model...")
        if self._load_text:
            p.setFont(QFont("Segoe UI", 9))
            p.setPen(QColor(255, 255, 255, 70))
            p.drawText(QRect(0, cy + 38, w, 20), Qt.AlignCenter, self._load_text)

    def _draw_grid(self, p, w, h):
        mvp_np = self.cam.mvp_numpy(w / max(h, 1), 1.0, np.zeros(3))
        p.setPen(QPen(QColor(255, 255, 255, 10), 1))
        gs = 6
        pts = []
        for i in range(-gs, gs + 1):
            for a, b in [((i, 0, -gs), (i, 0, gs)), ((-gs, 0, i), (gs, 0, i))]:
                for pt in [a, b]:
                    v4 = np.array([pt[0], pt[1], pt[2], 1.0], dtype=np.float32)
                    clip = mvp_np @ v4
                    if abs(clip[3]) < 1e-6:
                        pts.append(None)
                        continue
                    ndc = clip[:3] / clip[3]
                    if abs(ndc[2]) > 1.5:
                        pts.append(None)
                        continue
                    pts.append(((ndc[0] * 0.5 + 0.5) * w, (0.5 - ndc[1] * 0.5) * h))

        for i in range(0, len(pts), 2):
            if pts[i] and pts[i + 1]:
                p.drawLine(QPointF(*pts[i]), QPointF(*pts[i + 1]))

    # ═══ Mouse ═══

    def mousePressEvent(self, event):
        self._last_m = event.position()
        self._auto = False
        self._moving = True
        if event.button() == Qt.LeftButton:
            self._rotating = True
        elif event.button() in (Qt.MiddleButton, Qt.RightButton):
            self._panning = True

    def mouseMoveEvent(self, event):
        if not self._last_m:
            return
        dx = event.position().x() - self._last_m.x()
        dy = event.position().y() - self._last_m.y()
        self._last_m = event.position()

        if self._rotating:
            self.cam.ry += dx * 0.5
            self.cam.rx = max(-89, min(89, self.cam.rx + dy * 0.5))
        elif self._panning:
            self.cam.px += dx * 0.004 * self.cam.dist
            self.cam.py -= dy * 0.004 * self.cam.dist

        self._cache_dirty = True
        self._move_timer.start(200)
        self.update()

    def mouseReleaseEvent(self, event):
        self._rotating = False
        self._panning = False
        self._move_timer.start(100)

    def wheelEvent(self, event):
        self._auto = False
        self._moving = True
        f = 0.9 if event.angleDelta().y() > 0 else 1.1
        self.cam.dist = max(0.3, min(80, self.cam.dist * f))
        self._cache_dirty = True
        self._move_timer.start(200)
        self.update()


# ═══════════════════════════════════════════════════════
#  DOCK
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
            p.setPen(Qt.NoPen);
            p.setBrush(ACCENT)
            p.drawRoundedRect((self.width() - 14) // 2, self.height() - 4, 14, 2.5, 1, 1)
        p.end()

    def enterEvent(self, e):
        self._hover = True; self.update()

    def leaveEvent(self, e):
        self._hover = False; self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton: self.clicked.emit()


class FloatingDock(QWidget):
    mode_changed = Signal(int)
    browse_clicked = Signal()
    DOCK_W = 380
    DOCK_H = 52

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(self.DOCK_H)
        lo = QHBoxLayout(self)
        lo.setContentsMargins(16, 6, 16, 6)
        lo.setSpacing(8)

        self.browse = QPushButton("  Open")
        self.browse.setIcon(get_icon("folder_open", 14, QColor(255, 255, 255, 200)))
        self.browse.setFixedHeight(34)
        self.browse.setFont(QFont("Segoe UI", 9))
        self.browse.setCursor(Qt.PointingHandCursor)
        self.browse.setStyleSheet("""QPushButton{background:rgba(255,255,255,8);border:1px solid rgba(255,255,255,10);
            border-radius:7px;color:white;padding:0 14px;}QPushButton:hover{background:rgba(255,255,255,14);}""")
        self.browse.clicked.connect(self.browse_clicked.emit)
        lo.addWidget(self.browse)

        sep = QWidget();
        sep.setFixedSize(1, 24);
        sep.setStyleSheet("background:rgba(255,255,255,10);")
        lo.addWidget(sep)

        self._btns = []
        for label, mode in [("Solid", MODE_SOLID), ("Clay", MODE_CLAY), ("Wire", MODE_WIRE)]:
            btn = DockBtn(label, active=(mode == MODE_SOLID))
            btn.clicked.connect(lambda m=mode: self._set(m))
            lo.addWidget(btn)
            self._btns.append((btn, mode))

    def _set(self, mode):
        for btn, m in self._btns:
            btn.active = (m == mode);
            btn.update()
        self.mode_changed.emit(mode)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(0, 0, self.width(), self.height())
        path = QPainterPath();
        path.addRoundedRect(r, 14, 14)
        p.setClipPath(path)
        p.fillRect(r, QColor(30, 30, 30, 220))
        p.setClipping(False)
        p.setPen(QPen(QColor(255, 255, 255, 8), 1));
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(r.adjusted(.5, .5, -.5, -.5), 14, 14)
        p.end()


# ═══════════════════════════════════════════════════════
#  APP
# ═══════════════════════════════════════════════════════

class App(QWidget):
    def __init__(self, file_system=None, parent=None):
        super().__init__(parent)
        self.fs = file_system

        lo = QVBoxLayout(self)
        lo.setContentsMargins(0, 0, 0, 0)
        lo.setSpacing(0)

        self.viewport = Viewport()
        lo.addWidget(self.viewport, 1)

        self.dock = FloatingDock(self)
        self.dock.mode_changed.connect(self.viewport.set_mode)
        self.dock.browse_clicked.connect(self._browse)

        self._position_dock()
        QTimer.singleShot(50, self._load_default)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._position_dock()

    def _position_dock(self):
        dw = min(self.dock.DOCK_W, self.width() - 40)
        self.dock.setFixedWidth(dw)
        self.dock.move((self.width() - dw) // 2, self.height() - self.dock.DOCK_H - 16)
        self.dock.raise_()

    def _load_default(self):
        path = _ensure_cube()
        self.viewport.set_loading(True, "Loading default cube...")
        QTimer.singleShot(100, lambda: self._do_load(path, True))

    def _browse(self):
        start = MODELS_DIR if os.listdir(MODELS_DIR) else (self.fs.get_base_path() if self.fs else "")
        path, _ = QFileDialog.getOpenFileName(
            self, "Open 3D Model", start,
            "3D Models (*.obj *.stl *.ply *.glb *.gltf *.fbx *.3ds *.off);;All (*)"
        )
        if path:
            self.viewport.set_loading(True, os.path.basename(path))
            QTimer.singleShot(50, lambda: self._do_load(path))

    def _do_load(self, path, auto_rotate=False):
        self.viewport.set_loading(True, f"Parsing {os.path.basename(path)}...")
        from PySide6.QtWidgets import QApplication
        QApplication.processEvents()

        t0 = time.time()
        mesh = load_mesh(path)
        dt = time.time() - t0

        if mesh and mesh.tri_count > 0:
            self.viewport.set_loading(True, f"{mesh.tri_count:,} triangles loaded in {dt:.2f}s")
            QApplication.processEvents()
            QTimer.singleShot(300, lambda: self._finish(mesh, auto_rotate))
        else:
            self.viewport.set_loading(False)
            self.viewport.mesh = None
            self.viewport.update()

    def _finish(self, mesh, auto_rotate=False):
        self.viewport.set_mesh(mesh)
        if auto_rotate:
            self.viewport._auto = True