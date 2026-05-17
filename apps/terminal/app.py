import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

from datetime import datetime
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPlainTextEdit
from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QFont, QColor, QTextCursor, QPainter

from core.icons import get_pixmap


class TabBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(34)
        self._px = get_pixmap("terminal", 14)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        p.fillRect(self.rect(), QColor(25, 25, 25))

        # Active tab
        p.setBrush(QColor(12, 12, 12))
        p.setPen(QColor(255, 255, 255, 8))
        p.drawRoundedRect(8, 4, 170, 26, 5, 5)

        p.drawPixmap(16, (self.height()-14)//2, self._px)

        p.setFont(QFont("Segoe UI", 9))
        p.setPen(QColor(255, 255, 255, 190))
        p.drawText(QRect(36, 0, 120, self.height()), Qt.AlignVCenter, "Terminal")

        # + tab
        p.setFont(QFont("Segoe UI", 13))
        p.setPen(QColor(255, 255, 255, 100))
        p.drawText(QRect(186, 0, 28, self.height()), Qt.AlignCenter, "+")
        p.end()


class TermEdit(QPlainTextEdit):
    def __init__(self, fs=None, parent=None):
        super().__init__(parent)
        self.fs = fs
        self.cwd = fs.get_base_path() if fs else os.path.expanduser("~")
        self.hist = []
        self.hi = -1
        self.pp = 0

        self.setFont(QFont("Cascadia Code, Cascadia Mono, Consolas", 11))
        self.setStyleSheet("""QPlainTextEdit{background:#0c0c0c;color:#ccc;border:none;
            selection-background-color:#264f78;padding:4px 10px;}""")
        self.setLineWrapMode(QPlainTextEdit.WidgetWidth)
        self.setUndoRedoEnabled(False)

        self._w("WinPy11 Terminal [Version 1.0]\n(c) WinPy11. All rights reserved.\n\n")
        self._prompt()

    def _prompt(self):
        if self.fs:
            try:
                r = os.path.relpath(self.cwd, self.fs.get_base_path())
                d = "C:\\Users\\User" + ("\\" + r.replace("/","\\") if r != "." else "")
            except: d = self.cwd
        else: d = self.cwd
        self._w(f"{d}> ")
        self.pp = self.textCursor().position()

    def _w(self, t):
        c = self.textCursor(); c.movePosition(QTextCursor.End)
        c.insertText(t); self.setTextCursor(c); self.ensureCursorVisible()

    def _cmd(self):
        return self.toPlainText()[self.pp:]

    def _repl(self, t):
        c = self.textCursor(); c.setPosition(self.pp)
        c.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)
        c.removeSelectedText(); c.insertText(t); self.setTextCursor(c)

    def keyPressEvent(self, e):
        c = self.textCursor()
        if c.position() < self.pp:
            c.movePosition(QTextCursor.End); self.setTextCursor(c)
            if e.key() not in (Qt.Key_Up, Qt.Key_Down): return

        if e.key() in (Qt.Key_Return, Qt.Key_Enter):
            cmd = self._cmd().strip(); self._w("\n")
            if cmd:
                self.hist.append(cmd); self.hi = len(self.hist)
                self._exec(cmd)
            self._prompt(); return
        elif e.key() == Qt.Key_Up:
            if self.hist and self.hi > 0:
                self.hi -= 1; self._repl(self.hist[self.hi])
            return
        elif e.key() == Qt.Key_Down:
            if self.hi < len(self.hist)-1:
                self.hi += 1; self._repl(self.hist[self.hi])
            elif self.hi == len(self.hist)-1:
                self.hi = len(self.hist); self._repl("")
            return
        elif e.key() == Qt.Key_Backspace and c.position() <= self.pp: return
        elif e.key() == Qt.Key_C and e.modifiers() & Qt.ControlModifier:
            self._w("^C\n"); self._prompt(); return
        elif e.key() == Qt.Key_L and e.modifiers() & Qt.ControlModifier:
            self.clear(); self._prompt(); return
        super().keyPressEvent(e)

    def _exec(self, cmd):
        parts = cmd.split(); c = parts[0].lower(); args = parts[1:]
        cmds = {"cd":self._cd,"dir":self._dir,"ls":self._dir,
            "cls":lambda a:self.clear(),"clear":lambda a:self.clear(),
            "echo":lambda a:self._w(" ".join(a)+"\n"),
            "pwd":lambda a:self._w(self.cwd+"\n"),
            "mkdir":self._mkdir,"touch":self._touch,"cat":self._cat,"type":self._cat,
            "rm":self._rm,"del":self._rm,"help":lambda a:self._help(),
            "whoami":lambda a:self._w("User\n"),"hostname":lambda a:self._w("WINPY11-PC\n"),
            "date":lambda a:self._w(datetime.now().strftime("%Y-%m-%d %H:%M:%S\n")),
            "neofetch":lambda a:self._neo()}
        if c in cmds: cmds[c](args)
        else: self._w(f"'{cmd}' is not recognized.\nType 'help' for commands.\n")

    def _cd(self, a):
        if not a or a[0]=="~":
            self.cwd = self.fs.get_base_path() if self.fs else os.path.expanduser("~"); return
        t = a[0]
        if t == "..":
            p = os.path.dirname(self.cwd)
            if self.fs and p.startswith(self.fs.get_base_path()): self.cwd = p
            return
        np = os.path.normpath(os.path.join(self.cwd, t))
        if os.path.isdir(np):
            if self.fs and not np.startswith(self.fs.get_base_path()):
                self._w("Access denied.\n")
            else: self.cwd = np
        else: self._w(f"Not found: {t}\n")

    def _dir(self, a):
        try:
            items = os.listdir(self.cwd)
            self._w(f"\n Directory of {self.cwd}\n\n")
            for n in sorted(items):
                fp = os.path.join(self.cwd, n)
                if os.path.isdir(fp): self._w(f"  <DIR>          {n}\n")
                else: self._w(f"  {os.path.getsize(fp):>13,}  {n}\n")
            self._w(f"\n  {len(items)} item(s)\n")
        except: self._w("Access denied.\n")

    def _mkdir(self, a):
        if not a: self._w("Usage: mkdir <name>\n"); return
        try: os.makedirs(os.path.join(self.cwd,a[0]),exist_ok=True)
        except OSError as e: self._w(f"Error: {e}\n")

    def _touch(self, a):
        if not a: self._w("Usage: touch <name>\n"); return
        try: open(os.path.join(self.cwd,a[0]),"a").close()
        except OSError as e: self._w(f"Error: {e}\n")

    def _cat(self, a):
        if not a: self._w("Usage: cat <file>\n"); return
        try:
            with open(os.path.join(self.cwd,a[0]),"r",encoding="utf-8") as f: self._w(f.read()+"\n")
        except FileNotFoundError: self._w(f"Not found: {a[0]}\n")
        except: self._w("Binary file.\n")

    def _rm(self, a):
        if not a: self._w("Usage: rm <name>\n"); return
        import shutil
        fp = os.path.join(self.cwd,a[0])
        try:
            if os.path.isdir(fp): shutil.rmtree(fp)
            elif os.path.isfile(fp): os.remove(fp)
            else: self._w(f"Not found: {a[0]}\n")
        except OSError as e: self._w(f"Error: {e}\n")

    def _help(self):
        self._w("\n cd dir  mkdir  touch  cat  rm  echo  pwd  cls  whoami  date  neofetch  help\n\n")

    def _neo(self):
        self._w("""
  ████████████     User@WINPY11-PC
  ██        ██     OS: WinPy11 v1.0
  ██  ████  ██     Shell: WinPy Terminal
  ██  ████  ██     UI: PySide6
  ██        ██     Theme: Dark
  ████████████
\n""")


class App(QWidget):
    def __init__(self, file_system=None, parent=None):
        super().__init__(parent)
        lo = QVBoxLayout(self); lo.setContentsMargins(0,0,0,0); lo.setSpacing(0)
        lo.addWidget(TabBar())
        lo.addWidget(TermEdit(file_system))