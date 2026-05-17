import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLineEdit, QSplitter, QScrollArea, QMenu,
    QInputDialog, QMessageBox, QLabel
)
from PySide6.QtCore import Qt, Signal, QRect, QRectF
from PySide6.QtGui import QFont, QColor, QPainter, QPen

from core.icons import get_pixmap, get_icon, get_file_icon

ACCENT = QColor(0, 103, 192)

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".svg", ".gif", ".bmp", ".avif", ".ico", ".tiff"}
AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac", ".wma"}
VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".wmv", ".flv"}
CODE_EXTS = {".py", ".cpp", ".c", ".h", ".hpp", ".js", ".ts", ".html", ".css", ".json", ".xml", ".yaml", ".yml"}
TEXT_EXTS = {".txt", ".md", ".log", ".ini", ".cfg", ".csv"}


def _app_for_ext(ext):
    """Retourne l'app_id appropriée pour une extension."""
    if ext in IMAGE_EXTS:
        return "photos"
    if ext in AUDIO_EXTS:
        return "music"
    if ext in VIDEO_EXTS:
        return "video"
    if ext in CODE_EXTS:
        return "vscode"
    if ext in TEXT_EXTS:
        return "notepad"
    if ext == ".url":
        return "browser"
    return "notepad"


class FileRow(QWidget):
    double_clicked = Signal(dict)
    selected_sig = Signal(object)

    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.data = data
        self.selected = False
        self.setFixedHeight(30)
        self.setCursor(Qt.PointingHandCursor)
        self.setMouseTracking(True)

        if data["is_dir"]:
            self._px = get_pixmap("folder", 18)
        else:
            self._px = get_file_icon(data["name"], 18).pixmap(18, 18)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        w, h = self.width(), self.height()

        if self.selected:
            p.setBrush(QColor(ACCENT.red(), ACCENT.green(), ACCENT.blue(), 30))
            p.setPen(QPen(QColor(ACCENT.red(), ACCENT.green(), ACCENT.blue(), 50), 1))
            p.drawRoundedRect(QRectF(4, 1, w - 8, h - 2), 3, 3)
        elif self.underMouse():
            p.setBrush(QColor(255, 255, 255, 8))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(QRectF(4, 1, w - 8, h - 2), 3, 3)

        # Icône
        p.drawPixmap(16, (h - 18) // 2, self._px)

        # Nom
        p.setFont(QFont("Segoe UI", 9))
        p.setPen(QColor(255, 255, 255, 210))
        name_w = int(w * 0.42)
        p.drawText(QRect(42, 0, name_w, h), Qt.AlignVCenter, self.data["name"])

        # Date
        p.setFont(QFont("Segoe UI", 8))
        p.setPen(QColor(255, 255, 255, 90))
        dx = int(w * 0.5)
        p.drawText(QRect(dx, 0, 140, h), Qt.AlignVCenter, self.data.get("modified", ""))

        # Taille
        if not self.data["is_dir"]:
            sz = self.data["size"]
            if sz < 1024:
                t = f"{sz} B"
            elif sz < 1048576:
                t = f"{sz / 1024:.1f} KB"
            else:
                t = f"{sz / 1048576:.1f} MB"
            p.drawText(QRect(dx + 150, 0, 100, h), Qt.AlignVCenter | Qt.AlignRight, t)

        p.end()

    def enterEvent(self, e):
        self.update()

    def leaveEvent(self, e):
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.selected_sig.emit(self)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.double_clicked.emit(self.data)


class SideBtn(QWidget):
    clicked = Signal()

    def __init__(self, icon_name, text, parent=None):
        super().__init__(parent)
        self.text = text
        self.active = False
        self.setFixedHeight(28)
        self.setCursor(Qt.PointingHandCursor)
        self._px = get_pixmap(icon_name, 16)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)

        r = QRect(4, 0, self.width() - 8, self.height())
        if self.active:
            p.fillRect(r, QColor(255, 255, 255, 10))
            p.setPen(Qt.NoPen)
            p.setBrush(ACCENT)
            p.drawRoundedRect(2, 6, 3, self.height() - 12, 1.5, 1.5)
        elif self.underMouse():
            p.fillRect(r, QColor(255, 255, 255, 6))

        p.drawPixmap(14, (self.height() - 16) // 2, self._px)
        p.setFont(QFont("Segoe UI", 9))
        p.setPen(QColor(255, 255, 255, 190))
        p.drawText(QRect(36, 0, self.width() - 40, self.height()), Qt.AlignVCenter, self.text)
        p.end()

    def enterEvent(self, e):
        self.update()

    def leaveEvent(self, e):
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()


class App(QWidget):
    def __init__(self, file_system=None, parent=None):
        super().__init__(parent)
        self.fs = file_system
        self.cur = ""
        self.history = [""]
        self.hidx = 0
        self.rows = []

        lo = QVBoxLayout(self)
        lo.setContentsMargins(0, 0, 0, 0)
        lo.setSpacing(0)

        # ═══ TOOLBAR ═══
        tb = QWidget()
        tb.setFixedHeight(42)
        tb.setStyleSheet("background:#2d2d2d;border-bottom:1px solid rgba(255,255,255,6);")
        tl = QHBoxLayout(tb)
        tl.setContentsMargins(8, 0, 8, 0)
        tl.setSpacing(4)

        btn_css = """
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 5px;
                padding: 4px;
            }
            QPushButton:hover {
                background: rgba(255,255,255,10);
            }
            QPushButton:disabled {
                opacity: 0.3;
            }
        """

        self.bk = QPushButton()
        self.bk.setIcon(get_icon("arrow_left", 16, QColor(255, 255, 255, 180)))
        self.bk.setFixedSize(32, 32)
        self.bk.setStyleSheet(btn_css)
        self.bk.clicked.connect(self._back)
        tl.addWidget(self.bk)

        self.fw = QPushButton()
        self.fw.setIcon(get_icon("arrow_right", 16, QColor(255, 255, 255, 180)))
        self.fw.setFixedSize(32, 32)
        self.fw.setStyleSheet(btn_css)
        self.fw.clicked.connect(self._fwd)
        tl.addWidget(self.fw)

        self.up = QPushButton()
        self.up.setIcon(get_icon("arrow_up", 16, QColor(255, 255, 255, 180)))
        self.up.setFixedSize(32, 32)
        self.up.setStyleSheet(btn_css)
        self.up.clicked.connect(self._go_up)
        tl.addWidget(self.up)

        tl.addSpacing(4)

        self.addr = QLineEdit()
        self.addr.setFont(QFont("Segoe UI", 10))
        self.addr.setFixedHeight(28)
        self.addr.setStyleSheet("""
            QLineEdit {
                background: rgba(255,255,255,6);
                border: 1px solid rgba(255,255,255,8);
                border-radius: 5px;
                color: white;
                padding: 0 10px;
            }
            QLineEdit:focus {
                border: 1px solid rgba(0,103,192,180);
            }
        """)
        self.addr.returnPressed.connect(self._addr_go)
        tl.addWidget(self.addr, 1)

        tl.addSpacing(4)

        new_btn = QPushButton()
        new_btn.setIcon(get_icon("plus", 14, QColor(255, 255, 255, 180)))
        new_btn.setFixedSize(32, 32)
        new_btn.setStyleSheet(btn_css)
        new_btn.setToolTip("New")
        new_menu = QMenu(new_btn)
        new_menu.setStyleSheet(self._menu_css())
        new_menu.addAction(get_icon("folder", 14), "New folder", self._new_folder)
        new_menu.addAction(get_icon("file", 14), "New file", self._new_file)
        new_btn.setMenu(new_menu)
        tl.addWidget(new_btn)

        lo.addWidget(tb)

        # ═══ COLUMN HEADER ═══
        ch = QWidget()
        ch.setFixedHeight(26)
        ch.setStyleSheet("background:#262626;border-bottom:1px solid rgba(255,255,255,6);")
        chl = QHBoxLayout(ch)
        chl.setContentsMargins(16, 0, 16, 0)
        for text, stretch in [("Name", 5), ("Date modified", 2), ("Size", 1)]:
            lbl = QLabel(text)
            lbl.setFont(QFont("Segoe UI", 8))
            lbl.setStyleSheet("color:rgba(255,255,255,100);")
            chl.addWidget(lbl, stretch)

        # ═══ SPLITTER ═══
        sp = QSplitter(Qt.Horizontal)
        sp.setStyleSheet("QSplitter::handle{background:transparent;width:1px;}")

        # Sidebar
        sb = QWidget()
        sb.setFixedWidth(200)
        sb.setStyleSheet("background:#252525;border-right:1px solid rgba(255,255,255,6);")
        sbl = QVBoxLayout(sb)
        sbl.setContentsMargins(4, 8, 4, 8)
        sbl.setSpacing(1)

        self.sbtns = []
        nav_items = [
            ("home", "Home", ""),
            ("star", "Favorites", ""),
            ("computer", "Desktop", "Desktop"),
            ("file", "Documents", "Documents"),
            ("download", "Downloads", "Downloads"),
            ("image", "Pictures", "Pictures"),
            ("music", "Music", "Music"),
            ("video", "Videos", "Videos"),
        ]
        for ic, name, path in nav_items:
            btn = SideBtn(ic, name)
            btn.clicked.connect(lambda p=path: self._nav(p))
            sbl.addWidget(btn)
            self.sbtns.append((btn, path))

        sbl.addStretch()
        sp.addWidget(sb)

        # File area
        right = QWidget()
        right.setStyleSheet("background:#1e1e1e;")
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(0)
        rl.addWidget(ch)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollBar:vertical { width: 5px; background: transparent; }
            QScrollBar::handle:vertical {
                background: rgba(255,255,255,18);
                border-radius: 2px;
                min-height: 30px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        """)

        self.lw = QWidget()
        self.lw.setStyleSheet("background:transparent;")
        self.ll = QVBoxLayout(self.lw)
        self.ll.setContentsMargins(0, 2, 0, 2)
        self.ll.setSpacing(0)
        self.ll.setAlignment(Qt.AlignTop)
        self.scroll.setWidget(self.lw)
        rl.addWidget(self.scroll, 1)

        sp.addWidget(right)
        sp.setSizes([200, 600])
        lo.addWidget(sp, 1)

        # Status bar
        self.stat_label = QLabel("  Ready")
        self.stat_label.setFixedHeight(22)
        self.stat_label.setFont(QFont("Segoe UI", 9))
        self.stat_label.setStyleSheet(
            "background:#252525;color:rgba(255,255,255,120);"
            "border-top:1px solid rgba(255,255,255,6);padding-left:12px;"
        )
        lo.addWidget(self.stat_label)

        # Navigate to root
        self._nav("")

    # ═══════════════════════════════════════════════════
    #  NAVIGATION
    # ═══════════════════════════════════════════════════

    def _nav(self, path):
        """Navigue vers un chemin relatif."""
        self.cur = path
        disp = f"C:\\Users\\User\\{path.replace('/', chr(92))}" if path else "C:\\Users\\User"
        self.addr.setText(disp)

        # Sidebar active
        for btn, bp in self.sbtns:
            btn.active = (bp == path)
            btn.update()

        # Clear file list
        self.rows.clear()
        while self.ll.count():
            it = self.ll.takeAt(0)
            if it.widget():
                it.widget().deleteLater()

        # Populate
        if self.fs:
            items = self.fs.list_dir(path)
            for data in items:
                row = FileRow(data)
                row.double_clicked.connect(self._on_double_click)
                row.selected_sig.connect(self._on_select)
                row.setContextMenuPolicy(Qt.CustomContextMenu)
                row.customContextMenuRequested.connect(
                    lambda pos, d=data: self._context_menu(pos, d)
                )
                self.ll.addWidget(row)
                self.rows.append(row)
            self.stat_label.setText(f"  {len(items)} items")

        # History
        if not self.history or self.history[self.hidx] != path:
            self.history = self.history[:self.hidx + 1]
            self.history.append(path)
            self.hidx = len(self.history) - 1

        # Buttons state
        self.bk.setEnabled(self.hidx > 0)
        self.fw.setEnabled(self.hidx < len(self.history) - 1)
        self.up.setEnabled(bool(path))

    def _on_select(self, item):
        for r in self.rows:
            r.selected = (r is item)
            r.update()

    def _on_double_click(self, data):
        """Double-clic sur un élément."""
        if data["is_dir"]:
            self._nav(data["path"])
            return

        # C'est un fichier — l'ouvrir avec la bonne app
        self._open_file_data(data)

    def _open_file_data(self, data):
        """Ouvre un fichier avec l'app appropriée."""
        name = data["name"]
        ext = os.path.splitext(name)[1].lower()
        app_id = _app_for_ext(ext)

        if not self.fs:
            return

        filepath = self.fs.get_path(data["path"])

        # Utiliser _desktop_ref pour lancer l'app avec le fichier
        if hasattr(self, '_desktop_ref') and self._desktop_ref:
            self._desktop_ref._open_with(app_id, filepath)

    def _open_file_with(self, app_id, data):
        """Ouvre un fichier avec une app spécifique (depuis Open With)."""
        if not self.fs:
            return
        filepath = self.fs.get_path(data["path"])
        if hasattr(self, '_desktop_ref') and self._desktop_ref:
            self._desktop_ref._open_with(app_id, filepath)

    # ═══════════════════════════════════════════════════
    #  NAVIGATION BUTTONS
    # ═══════════════════════════════════════════════════

    def _back(self):
        if self.hidx > 0:
            self.hidx -= 1
            self._nav(self.history[self.hidx])

    def _fwd(self):
        if self.hidx < len(self.history) - 1:
            self.hidx += 1
            self._nav(self.history[self.hidx])

    def _go_up(self):
        if self.cur:
            parent = "/".join(self.cur.replace("\\", "/").split("/")[:-1])
            self._nav(parent)

    def _addr_go(self):
        t = self.addr.text().replace("\\", "/")
        prefix = "C:/Users/User/"
        if t.startswith(prefix):
            t = t[len(prefix):]
        elif "C:" in t:
            t = ""
        self._nav(t)

    # ═══════════════════════════════════════════════════
    #  NEW FILE / FOLDER
    # ═══════════════════════════════════════════════════

    def _new_folder(self):
        name, ok = QInputDialog.getText(self, "New Folder", "Name:")
        if ok and name and self.fs:
            path = f"{self.cur}/{name}" if self.cur else name
            self.fs.create_dir(path)
            self._nav(self.cur)

    def _new_file(self):
        name, ok = QInputDialog.getText(self, "New File", "Name:", text="Document.txt")
        if ok and name and self.fs:
            path = f"{self.cur}/{name}" if self.cur else name
            self.fs.create_file(path, "")
            self._nav(self.cur)

    # ═══════════════════════════════════════════════════
    #  CONTEXT MENU
    # ═══════════════════════════════════════════════════

    def _context_menu(self, pos, data):
        menu = QMenu(self)
        menu.setStyleSheet(self._menu_css())

        if data["is_dir"]:
            # Dossier
            menu.addAction(
                get_icon("folder_open", 14), "Open",
                lambda: self._nav(data["path"])
            )
        else:
            # Fichier
            ext = os.path.splitext(data["name"])[1].lower()
            default_app = _app_for_ext(ext)

            # Open (avec l'app par défaut)
            menu.addAction(
                get_icon("folder_open", 14), "Open",
                lambda: self._open_file_data(data)
            )

            # Open with submenu
            ow = menu.addMenu("Open with")
            ow.setStyleSheet(self._menu_css())

            if ext in IMAGE_EXTS:
                ow.addAction("Photos", lambda: self._open_file_with("photos", data))
            if ext in AUDIO_EXTS:
                ow.addAction("Music", lambda: self._open_file_with("music", data))
            if ext in VIDEO_EXTS:
                ow.addAction("Video", lambda: self._open_file_with("video", data))
            if ext in CODE_EXTS:
                ow.addAction("Code", lambda: self._open_file_with("vscode", data))

            # Toujours proposer Notepad et Code
            ow.addSeparator()
            ow.addAction("Notepad", lambda: self._open_file_with("notepad", data))
            ow.addAction("Code", lambda: self._open_file_with("vscode", data))

        menu.addSeparator()
        menu.addAction(
            get_icon("rename", 14), "Rename",
            lambda: self._rename(data)
        )
        menu.addAction(
            get_icon("delete", 14), "Delete",
            lambda: self._delete(data)
        )

        menu.exec(self.mapToGlobal(pos))

    # ═══════════════════════════════════════════════════
    #  RENAME / DELETE
    # ═══════════════════════════════════════════════════

    def _rename(self, data):
        new_name, ok = QInputDialog.getText(
            self, "Rename", "New name:", text=data["name"]
        )
        if ok and new_name and new_name != data["name"] and self.fs:
            self.fs.rename(data["path"], new_name)
            self._nav(self.cur)

    def _delete(self, data):
        reply = QMessageBox.question(
            self, "Delete", f"Delete '{data['name']}'?"
        )
        if reply == QMessageBox.Yes and self.fs:
            self.fs.delete(data["path"])
            self._nav(self.cur)

    # ═══════════════════════════════════════════════════
    #  API PUBLIQUE
    # ═══════════════════════════════════════════════════

    def open_file(self, path):
        """Ouvre un dossier ou fichier depuis l'extérieur."""
        if not self.fs:
            return

        if os.path.isdir(path):
            # Naviguer vers le dossier
            try:
                rel = os.path.relpath(path, self.fs.get_base_path())
                if not rel.startswith(".."):
                    self._nav(rel)
            except ValueError:
                pass
        elif os.path.isfile(path):
            # Naviguer vers le dossier parent
            folder = os.path.dirname(path)
            try:
                rel = os.path.relpath(folder, self.fs.get_base_path())
                if not rel.startswith(".."):
                    self._nav(rel)
            except ValueError:
                pass

    # ═══════════════════════════════════════════════════
    #  STYLE
    # ═══════════════════════════════════════════════════

    @staticmethod
    def _menu_css():
        return """
            QMenu {
                background: rgba(44,44,44,245);
                border: 1px solid rgba(255,255,255,12);
                border-radius: 8px;
                padding: 6px 0;
            }
            QMenu::item {
                padding: 6px 24px 6px 12px;
                color: rgba(255,255,255,210);
                border-radius: 4px;
                margin: 1px 4px;
            }
            QMenu::item:selected {
                background: rgba(255,255,255,10);
            }
            QMenu::separator {
                height: 1px;
                background: rgba(255,255,255,8);
                margin: 4px 12px;
            }
        """