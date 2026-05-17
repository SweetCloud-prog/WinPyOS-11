import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QPlainTextEdit, QMenuBar, QFileDialog
)
from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QFont, QColor, QPainter

from core.icons import get_icon

ACCENT = QColor(0, 103, 192)


class StatusBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(24)
        self.text = "Ln 1, Col 1       UTF-8       Untitled"

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.TextAntialiasing)
        p.fillRect(self.rect(), ACCENT)
        p.setFont(QFont("Segoe UI", 9))
        p.setPen(QColor(255, 255, 255, 220))
        p.drawText(QRect(12, 0, self.width() - 24, self.height()), Qt.AlignVCenter, self.text)
        p.end()


class App(QWidget):
    def __init__(self, file_system=None, parent=None):
        super().__init__(parent)
        self.fs = file_system
        self.cur_file = None
        self.mod = False

        lo = QVBoxLayout(self)
        lo.setContentsMargins(0, 0, 0, 0)
        lo.setSpacing(0)

        mb = QMenuBar()
        mb.setStyleSheet("""
            QMenuBar{background:#2d2d2d;color:white;border-bottom:1px solid rgba(255,255,255,6);padding:2px 4px;}
            QMenuBar::item{padding:4px 10px;border-radius:4px;}
            QMenuBar::item:selected{background:rgba(255,255,255,10);}
            QMenu{background:rgba(44,44,44,248);border:1px solid rgba(255,255,255,12);border-radius:8px;padding:6px 0;color:white;}
            QMenu::item{padding:6px 28px 6px 12px;border-radius:4px;margin:1px 4px;}
            QMenu::item:selected{background:rgba(255,255,255,10);}
            QMenu::separator{height:1px;background:rgba(255,255,255,8);margin:4px 12px;}
        """)

        fm = mb.addMenu("File")
        fm.addAction("New", self._new, "Ctrl+N")
        fm.addAction("Open...", self._open, "Ctrl+O")
        fm.addAction("Save", self._save, "Ctrl+S")
        fm.addAction("Save As...", self._save_as, "Ctrl+Shift+S")

        em = mb.addMenu("Edit")
        em.addAction("Undo", lambda: self.ed.undo(), "Ctrl+Z")
        em.addAction("Redo", lambda: self.ed.redo(), "Ctrl+Y")
        em.addSeparator()
        em.addAction("Cut", lambda: self.ed.cut(), "Ctrl+X")
        em.addAction("Copy", lambda: self.ed.copy(), "Ctrl+C")
        em.addAction("Paste", lambda: self.ed.paste(), "Ctrl+V")

        lo.addWidget(mb)

        self.ed = QPlainTextEdit()
        self.ed.setFont(QFont("Cascadia Code, Consolas", 11))
        self.ed.setStyleSheet("""
            QPlainTextEdit{background:#1e1e1e;color:#d4d4d4;border:none;
            padding:8px 12px;selection-background-color:#264f78;}
        """)
        self.ed.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.ed.setTabStopDistance(32)
        self.ed.textChanged.connect(lambda: setattr(self, 'mod', True))
        self.ed.cursorPositionChanged.connect(self._update_status)
        lo.addWidget(self.ed, 1)

        self.sb = StatusBar()
        lo.addWidget(self.sb)

    def _update_status(self):
        c = self.ed.textCursor()
        f = os.path.basename(self.cur_file) if self.cur_file else "Untitled"
        self.sb.text = f"Ln {c.blockNumber() + 1}, Col {c.columnNumber() + 1}       UTF-8       {f}{'  •' if self.mod else ''}"
        self.sb.update()

    def _new(self):
        self.ed.clear()
        self.cur_file = None
        self.mod = False
        self._update_status()

    def _open(self):
        start = self.fs.get_base_path() if self.fs else ""
        p, _ = QFileDialog.getOpenFileName(
            self, "Open", start,
            "Text (*.txt *.py *.md *.json *.html *.css *.js);;All (*)"
        )
        if p:
            self.open_file(p)

    def open_file(self, path):
        """Ouvre un fichier dans l'éditeur — API publique."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                self.ed.setPlainText(f.read())
            self.cur_file = path
            self.mod = False
            self._update_status()
        except Exception:
            pass

    def _save(self):
        if self.cur_file:
            try:
                with open(self.cur_file, "w", encoding="utf-8") as f:
                    f.write(self.ed.toPlainText())
                self.mod = False
                self._update_status()
            except Exception:
                pass
        else:
            self._save_as()

    def _save_as(self):
        start = self.fs.get_base_path() if self.fs else ""
        p, _ = QFileDialog.getSaveFileName(
            self, "Save As", start, "Text (*.txt);;All (*)"
        )
        if p:
            self.cur_file = p
            self._save()