import os
import json
import shutil
import configparser
from PySide6.QtWidgets import QWidget, QVBoxLayout, QMenu, QInputDialog, QMessageBox
from PySide6.QtCore import Qt, Signal, QRect, QRectF, QTimer, QPoint
from PySide6.QtGui import (
    QPainter, QLinearGradient, QRadialGradient, QColor,
    QFont, QBrush, QPixmap, QPen
)

from core.icons import get_pixmap, get_icon, get_file_icon
from core.taskbar import Taskbar
from core.window_manager import WindowManager
from core.app_loader import AppLoader
from core.file_system import FileSystem

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
USER_DATA = os.path.join(BASE_DIR, "user_data")
DESKTOP_DIR = os.path.join(USER_DATA, "Desktop")
SETTINGS_PATH = os.path.join(USER_DATA, "settings.json")
ICON_POS_PATH = os.path.join(USER_DATA, "desktop_positions.json")
GRID_W, GRID_H = 86, 96
DEFAULT_WPS = [os.path.join(BASE_DIR, f"wallpaper.{e}") for e in ("jpg", "png", "jpeg")]

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".svg", ".gif", ".bmp", ".avif", ".ico", ".tiff"}
AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac", ".wma"}
VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".wmv", ".flv"}
CODE_EXTS = {".py", ".cpp", ".c", ".h", ".hpp", ".js", ".ts", ".html", ".css", ".json", ".xml", ".yaml", ".yml"}
TEXT_EXTS = {".txt", ".md", ".log", ".ini", ".cfg", ".csv"}


def _load_json(p):
    try:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _save_json(p, d):
    try:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=2)
    except Exception:
        pass


def _get_wp():
    s = _load_json(SETTINGS_PATH)
    wt = s.get("wallpaper_type", "default")
    wp = s.get("wallpaper_path", "")
    if wt == "image" and wp and os.path.exists(wp):
        return ("image", wp)
    if wt == "solid":
        return ("solid", s.get("wallpaper_color", "#011230"))
    for p in DEFAULT_WPS:
        if os.path.exists(p):
            return ("image", p)
    return ("default", None)


class DesktopIcon(QWidget):
    double_clicked = Signal(str, bool)
    request_select = Signal(object, bool)
    position_changed = Signal(str, int, int)

    def __init__(self, name, is_dir=False, app_id=None, icon_name=None, parent=None):
        super().__init__(parent)
        self.name = name
        self.is_dir = is_dir
        self.app_id = app_id
        self.selected = False
        self.setFixedSize(78, 88)
        self.setCursor(Qt.PointingHandCursor)
        self._press_pos = None
        self._dragging = False
        self._drag_offsets = []

        if icon_name:
            self._pixmap = get_pixmap(icon_name, 40)
        elif is_dir:
            self._pixmap = get_pixmap("folder", 40)
        else:
            self._pixmap = get_file_icon(name, 40).pixmap(40, 40)

    def _key(self):
        return f"app:{self.app_id}" if self.app_id else f"file:{self.name}"

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        r = self.rect().adjusted(3, 3, -3, -3)
        if self.selected:
            p.setBrush(QColor(0, 103, 192, 40))
            p.setPen(QPen(QColor(0, 103, 192, 80), 1))
            p.drawRoundedRect(r, 5, 5)
        elif self.underMouse() and not self._dragging:
            p.setBrush(QColor(255, 255, 255, 12))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(r, 5, 5)
        p.drawPixmap((self.width() - 40) // 2, 8, self._pixmap)
        tr = QRect(2, 52, self.width() - 4, 32)
        p.setFont(QFont("Segoe UI", 8))
        p.setPen(QColor(0, 0, 0, 180))
        p.drawText(tr.adjusted(1, 1, 1, 1), Qt.AlignHCenter | Qt.AlignTop | Qt.TextWordWrap, self.name)
        p.setPen(QColor(255, 255, 255, 240))
        p.drawText(tr, Qt.AlignHCenter | Qt.AlignTop | Qt.TextWordWrap, self.name)
        p.end()

    def enterEvent(self, e):
        self.update()

    def leaveEvent(self, e):
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            ctrl = bool(event.modifiers() & Qt.ControlModifier)
            self.request_select.emit(self, ctrl)
            self._press_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self._press_pos and (event.buttons() & Qt.LeftButton):
            delta = event.globalPosition().toPoint() - self._press_pos
            if not self._dragging and delta.manhattanLength() > 8:
                self._start_drag(event.globalPosition().toPoint())
            if self._dragging:
                self._move_group(event.globalPosition().toPoint())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self._dragging:
                self._finish_drag()
            self._press_pos = None
            self._dragging = False
            self._drag_offsets = []

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = False
            self._press_pos = None
            if self.app_id:
                self.double_clicked.emit(self.app_id, False)
            else:
                self.double_clicked.emit(self.name, self.is_dir)

    def _get_selected(self):
        par = self.parent()
        if not par:
            return [self]
        sel = [c for c in par.findChildren(DesktopIcon) if c.selected]
        return sel if self in sel else [self]

    def _start_drag(self, gpos):
        self._dragging = True
        sibs = self._get_selected()
        po = self.parent().mapToGlobal(QPoint(0, 0))
        self._drag_offsets = [
            (s, QPoint(s.x() - (gpos.x() - po.x()), s.y() - (gpos.y() - po.y())), s.pos())
            for s in sibs
        ]
        for s, _, _ in self._drag_offsets:
            s.raise_()

    def _move_group(self, gpos):
        par = self.parent()
        if not par:
            return
        po = par.mapToGlobal(QPoint(0, 0))
        lx, ly = gpos.x() - po.x(), gpos.y() - po.y()
        for s, off, _ in self._drag_offsets:
            s.move(lx + off.x(), ly + off.y())

    def _finish_drag(self):
        par = self.parent()
        if not par:
            return
        for s, _, _ in self._drag_offsets:
            x = max(0, min(round(s.x() / GRID_W) * GRID_W + 6, par.width() - s.width()))
            y = max(0, min(round(s.y() / GRID_H) * GRID_H + 4, par.height() - s.height()))
            s.move(x, y)
            s.position_changed.emit(s._key(), x, y)
            s.update()


class Desktop(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("WinPy11")
        self.setMinimumSize(1280, 720)
        self._wp_cache = None
        self._wp_size = None
        self._sel_start = None
        self._sel_rect = None
        self._selecting = False
        self._positions = {}

        self.file_system = FileSystem()
        self.window_manager = WindowManager(self)
        self.app_loader = AppLoader()
        self.app_loader.scan_apps()

        lo = QVBoxLayout(self)
        lo.setContentsMargins(0, 0, 0, 0)
        lo.setSpacing(0)

        self.desktop_area = QWidget()
        self.desktop_area.setStyleSheet("background:transparent;")
        self.desktop_area.setMouseTracking(True)
        lo.addWidget(self.desktop_area, 1)

        self._load_positions()
        self._refresh_icons()

        self.taskbar = Taskbar(self)
        self.taskbar.app_launched.connect(self.launch_app)
        self.taskbar.set_available_apps(self.app_loader.get_app_list())
        lo.addWidget(self.taskbar)

        self._last_files = set()
        self._update_snapshot()
        self._sync_t = QTimer(self)
        self._sync_t.timeout.connect(self._check_sync)
        self._sync_t.start(3000)
        self._wp_t = QTimer(self)
        self._wp_t.timeout.connect(lambda: (setattr(self, '_wp_cache', None), self.update()))
        self._wp_t.start(5000)

    def _load_positions(self):
        self._positions = _load_json(ICON_POS_PATH)

    def _save_positions(self):
        _save_json(ICON_POS_PATH, self._positions)

    def _on_pos(self, key, x, y):
        self._positions[key] = {"x": x, "y": y}
        self._save_positions()

    def _next_free(self, used):
        mr = max(1, (self.height() - 150) // GRID_H)
        c, r = 0, 0
        while True:
            x, y = c * GRID_W + 6, r * GRID_H + 4
            if (x, y) not in used:
                return x, y
            r += 1
            if r >= mr:
                r = 0
                c += 1

    def _update_snapshot(self):
        os.makedirs(DESKTOP_DIR, exist_ok=True)
        try:
            self._last_files = set(os.listdir(DESKTOP_DIR))
        except Exception:
            self._last_files = set()

    def _check_sync(self):
        os.makedirs(DESKTOP_DIR, exist_ok=True)
        try:
            cur = set(os.listdir(DESKTOP_DIR))
        except Exception:
            return
        if cur != self._last_files:
            self._last_files = cur
            self._refresh_icons()

    def _on_select(self, icon, add):
        if add:
            icon.selected = not icon.selected
            icon.update()
        else:
            for c in self.desktop_area.findChildren(DesktopIcon):
                was = c.selected
                c.selected = (c is icon)
                if c.selected != was:
                    c.update()

    def _refresh_icons(self):
        for c in self.desktop_area.findChildren(DesktopIcon):
            c.deleteLater()
        used = set()

        pinned = [
            ("This PC", "computer", "file_explorer"),
            ("Edge", "edge", "browser"),
            ("Visual Studio Code", "visual", "vscode"),
            ("3D Viewer", "3d", "viewer3d"),
            ("3D Viewer 2.0", "3d", "viewer3d2"),
            ("Planetarium", "stellarium", "planetarium"),
            ("Terminal", "powershell", "terminal"),
            ("Notepad", "notepad", "notepad"),
            ("Calculator", "calculator", "calculator"),
            ("Settings", "settings", "settings"),
        ]

        for name, icon, aid in pinned:
            w = DesktopIcon(name, icon_name=icon, app_id=aid, parent=self.desktop_area)
            self._wire(w)
            pos = self._positions.get(w._key())
            if pos:
                w.move(pos["x"], pos["y"])
            else:
                x, y = self._next_free(used)
                w.move(x, y)
            used.add((w.x(), w.y()))
            w.show()

        os.makedirs(DESKTOP_DIR, exist_ok=True)
        try:
            entries = sorted(os.listdir(DESKTOP_DIR))
        except Exception:
            entries = []

        for name in entries:
            is_dir = os.path.isdir(os.path.join(DESKTOP_DIR, name))
            w = DesktopIcon(name, is_dir=is_dir, parent=self.desktop_area)
            self._wire(w)
            pos = self._positions.get(w._key())
            if pos:
                w.move(pos["x"], pos["y"])
            else:
                x, y = self._next_free(used)
                w.move(x, y)
            used.add((w.x(), w.y()))
            w.show()

    def _wire(self, w):
        w.double_clicked.connect(self._on_dbl)
        w.request_select.connect(self._on_select)
        w.position_changed.connect(self._on_pos)

    def _on_dbl(self, name_or_id, is_dir):
        info = self.app_loader.get_app_info(name_or_id)
        if info:
            self.launch_app(name_or_id)
            return

        if not isinstance(name_or_id, str):
            return

        name = name_or_id
        filepath = os.path.join(DESKTOP_DIR, name)
        ext = os.path.splitext(name)[1].lower()

        if ext == ".url":
            url = self._read_url(name)
            if url:
                self._open_in_browser(url)
                return

        if ext in IMAGE_EXTS:
            self._open_with("photos", filepath)
            return
        if ext in AUDIO_EXTS:
            self._open_with("music", filepath)
            return
        if ext in VIDEO_EXTS:
            self._open_with("video", filepath)
            return
        if ext in CODE_EXTS:
            self._open_with("vscode", filepath)
            return
        if ext in TEXT_EXTS:
            self._open_with("notepad", filepath)
            return
        if is_dir:
            self.launch_app("file_explorer")
            return
        if os.path.isfile(filepath):
            self._open_with("notepad", filepath)

    def _open_with(self, app_id, filepath):
        info = self.app_loader.get_app_info(app_id)
        if not info:
            return
        self.taskbar.close_start_menu()
        win = self.window_manager.create_window(
            info["name"], app_id, info.get("icon_name", "file")
        )
        widget = self.app_loader.load_app(app_id, self.file_system)
        if widget:
            widget._desktop_ref = self
            win.set_content(widget)
            QTimer.singleShot(300, lambda: self._send_file(widget, filepath))
        win.show()
        win.raise_()
        self.taskbar.add_running_app(app_id, info["name"], info.get("icon_name", "file"))

    def _send_file(self, widget, filepath):
        try:
            if hasattr(widget, 'open_file'):
                widget.open_file(filepath)
            elif hasattr(widget, '_open_path'):
                widget._open_path(filepath)
        except Exception as e:
            print(f"[Desktop] Error sending file: {e}")

    def _read_url(self, name):
        path = os.path.join(DESKTOP_DIR, name)
        try:
            cp = configparser.ConfigParser()
            cp.read(path, encoding="utf-8")
            return cp.get("InternetShortcut", "URL", fallback=None)
        except Exception:
            return None

    def _open_in_browser(self, url):
        info = self.app_loader.get_app_info("browser")
        if not info:
            return
        self.taskbar.close_start_menu()
        win = self.window_manager.create_window("Edge", "browser", info.get("icon_name", "edge"))
        widget = self.app_loader.load_app("browser", self.file_system)
        if widget:
            widget._desktop_ref = self
            win.set_content(widget)
            QTimer.singleShot(500, lambda: self._nav_browser(widget, url))
        win.show()
        win.raise_()
        self.taskbar.add_running_app("browser", "Edge", info.get("icon_name", "edge"))

    def _nav_browser(self, widget, url):
        try:
            if hasattr(widget, 'navigate_to'):
                widget.navigate_to(url)
            elif hasattr(widget, '_navigate'):
                widget._navigate(url)
        except Exception:
            pass

    def launch_app(self, app_id):
        info = self.app_loader.get_app_info(app_id)
        if not info:
            return
        self.taskbar.close_start_menu()
        win = self.window_manager.create_window(
            info["name"], app_id, info.get("icon_name", "file")
        )
        widget = self.app_loader.load_app(app_id, self.file_system)
        if widget:
            widget._desktop_ref = self
            win.set_content(widget)
        win.show()
        win.raise_()
        self.taskbar.add_running_app(app_id, info["name"], info.get("icon_name", "file"))

    def app_closed(self, app_id):
        self.taskbar.remove_running_app(app_id)

    def reload_wallpaper(self):
        self._wp_cache = None
        self._wp_size = None
        self.update()

    def _get_wp_px(self):
        sz = (self.width(), self.height())
        if self._wp_cache and self._wp_size == sz:
            return self._wp_cache
        wt, val = _get_wp()
        if wt == "solid" and val:
            px = QPixmap(*sz)
            px.fill(QColor(val))
            self._wp_cache = px
            self._wp_size = sz
            return px
        if wt == "image" and val and os.path.exists(val):
            px = QPixmap(val)
            if not px.isNull():
                sc = px.scaled(sz[0], sz[1], Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                sx = max(0, (sc.width() - sz[0]) // 2)
                sy = max(0, (sc.height() - sz[1]) // 2)
                sc = sc.copy(sx, sy, sz[0], sz[1])
                self._wp_cache = sc
                self._wp_size = sz
                return sc
        return None

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        wp = self._get_wp_px()
        if wp and not wp.isNull():
            p.drawPixmap(0, 0, wp)
        else:
            bg = QLinearGradient(0, 0, w, h)
            bg.setColorAt(0.0, QColor(1, 14, 46))
            bg.setColorAt(0.3, QColor(2, 24, 68))
            bg.setColorAt(0.6, QColor(3, 35, 92))
            bg.setColorAt(1.0, QColor(1, 12, 40))
            p.fillRect(self.rect(), QBrush(bg))
            for cx_f, cy_f, rf, r, g, b, a in [
                (0.50, 0.40, 0.42, 0, 90, 210, 65),
                (0.58, 0.36, 0.30, 170, 40, 140, 40),
                (0.38, 0.50, 0.26, 70, 40, 190, 32),
                (0.46, 0.56, 0.20, 0, 170, 210, 22),
            ]:
                rg = QRadialGradient(int(w * cx_f), int(h * cy_f), int(w * rf))
                rg.setColorAt(0.0, QColor(r, g, b, a))
                rg.setColorAt(1.0, QColor(0, 0, 0, 0))
                p.fillRect(self.rect(), QBrush(rg))
        if self._sel_rect and not self._sel_rect.isNull():
            sr = self._sel_rect.normalized()
            p.setBrush(QColor(0, 103, 192, 25))
            p.setPen(QPen(QColor(0, 103, 192, 140), 1))
            p.drawRect(sr)
        p.end()

    def mousePressEvent(self, event):
        self.taskbar.close_start_menu()
        if event.button() == Qt.LeftButton:
            if not (event.modifiers() & Qt.ControlModifier):
                for c in self.desktop_area.findChildren(DesktopIcon):
                    if c.selected:
                        c.selected = False
                        c.update()
            self._sel_start = event.pos()
            self._sel_rect = QRect()
            self._selecting = True
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._selecting and self._sel_start:
            self._sel_rect = QRect(self._sel_start, event.pos()).normalized()
            self.update()
            for c in self.desktop_area.findChildren(DesktopIcon):
                ir = QRect(c.x() + self.desktop_area.x(), c.y() + self.desktop_area.y(), c.width(), c.height())
                was = c.selected
                c.selected = self._sel_rect.intersects(ir)
                if c.selected != was:
                    c.update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._selecting = False
            self._sel_rect = None
            self._sel_start = None
            self.update()
        super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event):
        clicked = None
        for c in self.desktop_area.findChildren(DesktopIcon):
            ir = QRect(c.x() + self.desktop_area.x(), c.y() + self.desktop_area.y(), c.width(), c.height())
            if ir.contains(event.pos()):
                clicked = c
                break

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu{background:rgba(44,44,44,245);border:1px solid rgba(255,255,255,12);
            border-radius:8px;padding:6px 0;}
            QMenu::item{padding:7px 28px 7px 12px;color:rgba(255,255,255,210);
            border-radius:4px;margin:1px 4px;}
            QMenu::item:selected{background:rgba(255,255,255,10);}
            QMenu::separator{height:1px;background:rgba(255,255,255,8);margin:4px 12px;}
        """)

        if clicked and not clicked.app_id:
            name = clicked.name
            ext = os.path.splitext(name)[1].lower()
            menu.addAction(get_icon("folder_open", 16), "Open",
                           lambda: self._on_dbl(name, clicked.is_dir))
            ow = menu.addMenu(get_icon("chevron_right", 16), "Open with")
            if ext in IMAGE_EXTS:
                ow.addAction("Photos", lambda: self._open_with("photos", os.path.join(DESKTOP_DIR, name)))
            if ext in AUDIO_EXTS:
                ow.addAction("Music", lambda: self._open_with("music", os.path.join(DESKTOP_DIR, name)))
            if ext in VIDEO_EXTS:
                ow.addAction("Video", lambda: self._open_with("video", os.path.join(DESKTOP_DIR, name)))
            ow.addAction("Notepad", lambda: self._open_with("notepad", os.path.join(DESKTOP_DIR, name)))
            ow.addAction("VS Code", lambda: self._open_with("visual", os.path.join(DESKTOP_DIR, name)))
            menu.addSeparator()
            menu.addAction(get_icon("delete", 16), "Delete", lambda: self._del(name))
            menu.addAction(get_icon("rename", 16), "Rename", lambda: self._ren(name))
        else:
            vm = menu.addMenu("View")
            vm.addAction("Sort by name", self._sort)
            vm.addAction("Reset positions", self._sort)
            menu.addSeparator()
            nm = menu.addMenu(get_icon("plus", 16), "New")
            nm.addAction(get_icon("folder", 16), "Folder", self._new_dir)
            nm.addAction(get_icon("file", 16), "Text Document", self._new_file)
            nm.addAction(get_icon("link", 16), "Web Shortcut", self._new_url)
            menu.addSeparator()
            menu.addAction(get_icon("refresh", 16), "Refresh", self._do_refresh)
            menu.addSeparator()
            menu.addAction(get_icon("terminal", 16), "Open Terminal", lambda: self.launch_app("terminal"))
            menu.addAction(get_icon("settings", 16), "Settings", lambda: self.launch_app("settings"))
        menu.exec(event.globalPos())

    def _sort(self):
        self._positions.clear()
        self._save_positions()
        self._refresh_icons()

    def _new_dir(self):
        n, ok = QInputDialog.getText(self, "New Folder", "Name:")
        if ok and n:
            try:
                os.makedirs(os.path.join(DESKTOP_DIR, n), exist_ok=True)
                self._update_snapshot()
                self._refresh_icons()
            except Exception as e:
                QMessageBox.warning(self, "Error", str(e))

    def _new_file(self):
        n, ok = QInputDialog.getText(self, "New File", "Name:", text="Document.txt")
        if ok and n:
            try:
                open(os.path.join(DESKTOP_DIR, n), "w").close()
                self._update_snapshot()
                self._refresh_icons()
            except Exception as e:
                QMessageBox.warning(self, "Error", str(e))

    def _new_url(self):
        name, ok = QInputDialog.getText(self, "Web Shortcut", "Name:")
        if not ok or not name:
            return
        url, ok = QInputDialog.getText(self, "Web Shortcut", "URL:", text="https://")
        if not ok or not url:
            return
        fname = name if name.endswith(".url") else name + ".url"
        try:
            with open(os.path.join(DESKTOP_DIR, fname), "w", encoding="utf-8") as f:
                f.write("[InternetShortcut]\n")
                f.write(f"URL={url}\n")
            self._update_snapshot()
            self._refresh_icons()
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

    def _del(self, name):
        if QMessageBox.question(self, "Delete", f"Delete '{name}'?") == QMessageBox.Yes:
            try:
                fp = os.path.join(DESKTOP_DIR, name)
                if os.path.isdir(fp):
                    shutil.rmtree(fp)
                else:
                    os.remove(fp)
                self._positions.pop(f"file:{name}", None)
                self._save_positions()
                self._update_snapshot()
                self._refresh_icons()
            except Exception as e:
                QMessageBox.warning(self, "Error", str(e))

    def _ren(self, name):
        nn, ok = QInputDialog.getText(self, "Rename", "New name:", text=name)
        if ok and nn and nn != name:
            try:
                os.rename(os.path.join(DESKTOP_DIR, name), os.path.join(DESKTOP_DIR, nn))
                old_key = f"file:{name}"
                if old_key in self._positions:
                    self._positions[f"file:{nn}"] = self._positions.pop(old_key)
                self._save_positions()
                self._update_snapshot()
                self._refresh_icons()
            except Exception as e:
                QMessageBox.warning(self, "Error", str(e))

    def _do_refresh(self):
        self.reload_wallpaper()
        self._update_snapshot()
        self._refresh_icons()