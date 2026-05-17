"""
WinPy11 Code — IDE complet
Python + C++ | Syntax highlighting | Exécution intégrée | UI VS Code fidèle
"""
import os
import sys
import re
import time
import json
import shutil
import subprocess

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QPlainTextEdit, QFileDialog, QSplitter, QLabel,
    QStackedWidget, QMenu, QMenuBar, QSizePolicy,
    QTextEdit, QTreeWidget, QTreeWidgetItem,
    QInputDialog, QMessageBox, QLineEdit, QCompleter
)
from PySide6.QtCore import (
    Qt, Signal, QTimer, QRect, QRectF, QSize, QPoint,
    QProcess, QProcessEnvironment, QStringListModel
)
from PySide6.QtGui import (
    QFont, QColor, QPainter, QPen, QTextFormat,
    QSyntaxHighlighter, QTextCharFormat, QTextCursor,
    QFontMetrics, QKeySequence, QPainterPath
)

from core.icons import get_icon, get_pixmap

PYTHON_EXE = sys.executable
MONO = "Cascadia Code, Cascadia Mono, JetBrains Mono, Fira Code, Consolas, Courier New"


# ═══════════════════════════════════════════════════════
#  THEME
# ═══════════════════════════════════════════════════════

class T:
    """Thème VS Code Dark+."""
    BG = QColor(30, 30, 30)
    BG2 = QColor(37, 37, 38)
    BG3 = QColor(24, 24, 24)
    BG_LINE = QColor(40, 40, 40)
    BG_SEL = QColor(38, 79, 120)
    BG_MINI = QColor(25, 25, 25)
    BG_ACT = QColor(51, 51, 51)
    BG_HOVER = QColor(44, 44, 44)
    STATUS = QColor(0, 122, 204)
    STATUS_RUN = QColor(204, 93, 43)
    STATUS_ERR = QColor(204, 43, 43)
    ACCENT = QColor(0, 122, 204)
    BORDER = QColor(37, 37, 38)
    TEXT = QColor(212, 212, 212)
    DIM = QColor(133, 133, 133)
    WHITE = QColor(255, 255, 255)
    # Syntax Python
    KW = QColor(86, 156, 214)
    BI = QColor(220, 220, 170)
    STR = QColor(206, 145, 120)
    NUM = QColor(181, 206, 168)
    CMT = QColor(106, 153, 85)
    DECO = QColor(220, 220, 170)
    CLS = QColor(78, 201, 176)
    FUNC = QColor(220, 220, 170)
    SELF = QColor(86, 156, 214)
    MAGIC = QColor(181, 206, 168)
    # Syntax C++
    CPP_PREPROC = QColor(155, 120, 200)
    CPP_TYPE = QColor(78, 201, 176)


# ═══════════════════════════════════════════════════════
#  DETECT LANGUAGE
# ═══════════════════════════════════════════════════════

def detect_lang(filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    m = {
        "py": "Python", "pyw": "Python",
        "cpp": "C++", "cc": "C++", "cxx": "C++", "c": "C",
        "h": "C++", "hpp": "C++", "hxx": "C++",
        "js": "JavaScript", "ts": "TypeScript",
        "html": "HTML", "htm": "HTML",
        "css": "CSS", "json": "JSON",
        "md": "Markdown", "txt": "Plain Text",
        "xml": "XML", "yaml": "YAML", "yml": "YAML",
        "sh": "Shell", "bat": "Batch",
        "java": "Java", "rs": "Rust", "go": "Go",
    }
    return m.get(ext, "Plain Text")


def detect_ext(lang):
    m = {"Python": ".py", "C++": ".cpp", "C": ".c", "JavaScript": ".js",
         "HTML": ".html", "CSS": ".css", "JSON": ".json"}
    return m.get(lang, ".txt")


# ═══════════════════════════════════════════════════════
#  PYTHON HIGHLIGHTER
# ═══════════════════════════════════════════════════════

class PythonHighlighter(QSyntaxHighlighter):
    def __init__(self, doc):
        super().__init__(doc)
        self._rules = []

        kw = QTextCharFormat(); kw.setForeground(T.KW); kw.setFontWeight(QFont.Bold)
        for w in ["False","None","True","and","as","assert","async","await",
            "break","class","continue","def","del","elif","else","except",
            "finally","for","from","global","if","import","in","is","lambda",
            "nonlocal","not","or","pass","raise","return","try","while","with","yield"]:
            self._rules.append((re.compile(rf"\b{w}\b"), kw))

        bi = QTextCharFormat(); bi.setForeground(T.BI)
        for w in ["print","len","range","int","str","float","list","dict","set","tuple",
            "type","isinstance","input","open","super","enumerate","zip","map","filter",
            "sorted","reversed","abs","min","max","sum","any","all","ord","chr","hex",
            "bin","oct","format","round","id","hash","dir","vars","getattr","setattr",
            "hasattr","delattr","property","staticmethod","classmethod","bool","bytes",
            "bytearray","complex","frozenset","object","slice","iter","next","repr",
            "callable","compile","eval","exec","issubclass"]:
            self._rules.append((re.compile(rf"\b{w}\b"), bi))

        exc = QTextCharFormat(); exc.setForeground(T.CLS)
        for w in ["Exception","ValueError","TypeError","KeyError","IndexError",
            "AttributeError","ImportError","FileNotFoundError","RuntimeError",
            "StopIteration","OSError","ZeroDivisionError","NameError","SyntaxError",
            "NotImplementedError","OverflowError","PermissionError","RecursionError"]:
            self._rules.append((re.compile(rf"\b{w}\b"), exc))

        sf = QTextCharFormat(); sf.setForeground(T.SELF); sf.setFontItalic(True)
        self._rules.append((re.compile(r"\bself\b"), sf))
        self._rules.append((re.compile(r"\bcls\b"), sf))

        dc = QTextCharFormat(); dc.setForeground(T.DECO)
        self._rules.append((re.compile(r"@\w+(\.\w+)*"), dc))

        mg = QTextCharFormat(); mg.setForeground(T.MAGIC); mg.setFontItalic(True)
        self._rules.append((re.compile(r"\b__\w+__\b"), mg))

        nm = QTextCharFormat(); nm.setForeground(T.NUM)
        self._rules.append((re.compile(r"\b\d+\.?\d*([eE][+-]?\d+)?j?\b"), nm))
        self._rules.append((re.compile(r"\b0[xXbBoO][0-9a-fA-F]+\b"), nm))

        fn = QTextCharFormat(); fn.setForeground(T.FUNC)
        self._rules.append((re.compile(r"(?<=\bdef )\w+"), fn))

        cn = QTextCharFormat(); cn.setForeground(T.CLS)
        self._rules.append((re.compile(r"(?<=\bclass )\w+"), cn))

        fc = QTextCharFormat(); fc.setForeground(T.FUNC)
        self._rules.append((re.compile(r"\b\w+(?=\s*\()"), fc))

        self._str = QTextCharFormat(); self._str.setForeground(T.STR)
        self._str_pats = [
            re.compile(r'""".*?"""', re.DOTALL), re.compile(r"'''.*?'''", re.DOTALL),
            re.compile(r'[fFrRbB]?"[^"\\]*(?:\\.[^"\\]*)*"'),
            re.compile(r"[fFrRbB]?'[^'\\]*(?:\\.[^'\\]*)*'"),
        ]
        self._fstr_brace = QTextCharFormat(); self._fstr_brace.setForeground(T.KW)
        self._cmt = QTextCharFormat(); self._cmt.setForeground(T.CMT); self._cmt.setFontItalic(True)

    def highlightBlock(self, text):
        cs = -1; ins = False
        for i, ch in enumerate(text):
            if ch in ('"',"'") and (i==0 or text[i-1]!='\\'): ins = not ins
            elif ch == '#' and not ins: cs = i; break
        if cs >= 0:
            self.setFormat(cs, len(text)-cs, self._cmt)
            before = text[:cs]
        else:
            before = text

        for pat in self._str_pats:
            for m in pat.finditer(before):
                s, e = m.start(), m.end()
                if cs >= 0 and s >= cs: continue
                self.setFormat(s, e-s, self._str)
                mt = m.group()
                if mt and mt[0] in 'fF':
                    depth = 0
                    for j, c in enumerate(mt):
                        if c == '{' and j > 0 and (j+1>=len(mt) or mt[j+1]!='{'):
                            self.setFormat(s+j, 1, self._fstr_brace); depth += 1
                        elif c == '}' and depth > 0:
                            self.setFormat(s+j, 1, self._fstr_brace); depth -= 1

        for pat, fmt in self._rules:
            for m in pat.finditer(before):
                s, e = m.start(), m.end()
                if cs >= 0 and s >= cs: continue
                if self.format(s).foreground().color() == self._str.foreground().color(): continue
                self.setFormat(s, e-s, fmt)


# ═══════════════════════════════════════════════════════
#  C++ HIGHLIGHTER
# ═══════════════════════════════════════════════════════

class CppHighlighter(QSyntaxHighlighter):
    def __init__(self, doc):
        super().__init__(doc)
        self._rules = []

        # Preprocessor
        pp = QTextCharFormat(); pp.setForeground(T.CPP_PREPROC)
        self._rules.append((re.compile(r"^\s*#\w+.*$"), pp))

        # Keywords
        kw = QTextCharFormat(); kw.setForeground(T.KW); kw.setFontWeight(QFont.Bold)
        for w in ["auto","break","case","catch","class","const","constexpr","continue",
            "default","delete","do","else","enum","explicit","extern","false","for",
            "friend","goto","if","inline","mutable","namespace","new","noexcept",
            "nullptr","operator","private","protected","public","register","return",
            "sizeof","static","static_cast","dynamic_cast","reinterpret_cast",
            "const_cast","struct","switch","template","this","throw","true","try",
            "typedef","typeid","typename","union","using","virtual","void","volatile",
            "while","override","final","concept","requires","co_await","co_return","co_yield"]:
            self._rules.append((re.compile(rf"\b{w}\b"), kw))

        # Types
        tp = QTextCharFormat(); tp.setForeground(T.CPP_TYPE)
        for w in ["int","long","short","double","float","char","unsigned","signed",
            "bool","size_t","int8_t","int16_t","int32_t","int64_t",
            "uint8_t","uint16_t","uint32_t","uint64_t",
            "string","vector","map","set","unordered_map","unordered_set",
            "pair","tuple","array","list","deque","queue","stack","priority_queue",
            "shared_ptr","unique_ptr","weak_ptr","optional","variant","any",
            "iostream","ifstream","ofstream","stringstream",
            "cout","cin","cerr","endl","std"]:
            self._rules.append((re.compile(rf"\b{w}\b"), tp))

        # Numbers
        nm = QTextCharFormat(); nm.setForeground(T.NUM)
        self._rules.append((re.compile(r"\b\d+\.?\d*[fFlLuU]*\b"), nm))
        self._rules.append((re.compile(r"\b0[xX][0-9a-fA-F]+[uUlL]*\b"), nm))

        # Functions
        fn = QTextCharFormat(); fn.setForeground(T.FUNC)
        self._rules.append((re.compile(r"\b\w+(?=\s*\()"), fn))

        # Strings
        self._str = QTextCharFormat(); self._str.setForeground(T.STR)
        self._str_pats = [
            re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*"'),
            re.compile(r"'[^'\\]*(?:\\.[^'\\]*)*'"),
        ]

        # Comments
        self._cmt = QTextCharFormat(); self._cmt.setForeground(T.CMT); self._cmt.setFontItalic(True)
        self._cmt_line = re.compile(r"//.*$")
        self._cmt_start = re.compile(r"/\*")
        self._cmt_end = re.compile(r"\*/")

    def highlightBlock(self, text):
        # Single-line comments
        for m in self._cmt_line.finditer(text):
            self.setFormat(m.start(), m.end()-m.start(), self._cmt)

        # Multi-line comments
        self.setCurrentBlockState(0)
        start = 0
        if self.previousBlockState() == 1:
            em = self._cmt_end.search(text)
            if em:
                self.setFormat(0, em.end(), self._cmt)
                start = em.end()
            else:
                self.setFormat(0, len(text), self._cmt)
                self.setCurrentBlockState(1)
                return

        while start < len(text):
            sm = self._cmt_start.search(text, start)
            if not sm: break
            em = self._cmt_end.search(text, sm.end())
            if em:
                self.setFormat(sm.start(), em.end()-sm.start(), self._cmt)
                start = em.end()
            else:
                self.setFormat(sm.start(), len(text)-sm.start(), self._cmt)
                self.setCurrentBlockState(1)
                return

        # Strings
        for pat in self._str_pats:
            for m in pat.finditer(text):
                if self.format(m.start()).foreground().color() == self._cmt.foreground().color(): continue
                self.setFormat(m.start(), m.end()-m.start(), self._str)

        # Preprocessor
        for pat, fmt in self._rules[:1]:
            for m in pat.finditer(text):
                self.setFormat(m.start(), m.end()-m.start(), fmt)

        # Other rules
        for pat, fmt in self._rules[1:]:
            for m in pat.finditer(text):
                s = m.start()
                cf = self.format(s).foreground().color()
                if cf == self._cmt.foreground().color() or cf == self._str.foreground().color(): continue
                self.setFormat(s, m.end()-s, fmt)


# ═══════════════════════════════════════════════════════
#  GENERIC HIGHLIGHTER (json, html, etc.)
# ═══════════════════════════════════════════════════════

class GenericHighlighter(QSyntaxHighlighter):
    def __init__(self, doc):
        super().__init__(doc)
        self._str = QTextCharFormat(); self._str.setForeground(T.STR)
        self._num = QTextCharFormat(); self._num.setForeground(T.NUM)
        self._kw = QTextCharFormat(); self._kw.setForeground(T.KW)

    def highlightBlock(self, text):
        for m in re.finditer(r'"[^"\\]*(?:\\.[^"\\]*)*"', text):
            self.setFormat(m.start(), m.end()-m.start(), self._str)
        for m in re.finditer(r"\b\d+\.?\d*\b", text):
            self.setFormat(m.start(), m.end()-m.start(), self._num)
        for m in re.finditer(r"\b(true|false|null)\b", text):
            self.setFormat(m.start(), m.end()-m.start(), self._kw)


def create_highlighter(lang, doc):
    if lang == "Python": return PythonHighlighter(doc)
    if lang in ("C++", "C"): return CppHighlighter(doc)
    return GenericHighlighter(doc)


# ═══════════════════════════════════════════════════════
#  LINE NUMBER AREA
# ═══════════════════════════════════════════════════════

class LineArea(QWidget):
    def __init__(self, ed):
        super().__init__(ed); self._ed = ed
    def sizeHint(self): return QSize(self._ed.gutter_width(), 0)
    def paintEvent(self, e): self._ed.paint_gutter(e)


# ═══════════════════════════════════════════════════════
#  CODE EDITOR
# ═══════════════════════════════════════════════════════

class CodeEditor(QPlainTextEdit):
    def __init__(self, lang="Python", parent=None):
        super().__init__(parent)
        self.lang = lang
        self._font = QFont(MONO, 11)
        self.setFont(self._font)
        self.setTabStopDistance(QFontMetrics(self._font).horizontalAdvance(" ") * 4)
        self.setLineWrapMode(QPlainTextEdit.NoWrap)

        sb_css = """
            QScrollBar:vertical{background:#1e1e1e;width:11px;}
            QScrollBar::handle:vertical{background:rgba(255,255,255,14);border-radius:3px;min-height:30px;margin:0 2px;}
            QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0;}
            QScrollBar:horizontal{background:#1e1e1e;height:11px;}
            QScrollBar::handle:horizontal{background:rgba(255,255,255,14);border-radius:3px;min-width:30px;margin:2px 0;}
            QScrollBar::add-line:horizontal,QScrollBar::sub-line:horizontal{width:0;}
        """
        self.setStyleSheet(f"""
            QPlainTextEdit{{background:{T.BG.name()};color:{T.TEXT.name()};
            border:none;selection-background-color:{T.BG_SEL.name()};padding-left:4px;}}
            {sb_css}
        """)

        self._gutter = LineArea(self)
        self.blockCountChanged.connect(self._upd_w)
        self.updateRequest.connect(self._upd_area)
        self.cursorPositionChanged.connect(self._hl_line)
        self._upd_w()
        self._hl_line()

        self._hl = create_highlighter(lang, self.document())

        # Bracket matching
        self._bracket_positions = []

    def set_language(self, lang):
        self.lang = lang
        # Recréer le highlighter
        self._hl = create_highlighter(lang, self.document())
        self._hl.rehighlight()

    def gutter_width(self):
        digits = max(3, len(str(self.blockCount())))
        return 16 + QFontMetrics(self._font).horizontalAdvance("9") * digits

    def _upd_w(self):
        self.setViewportMargins(self.gutter_width(), 0, 0, 0)

    def _upd_area(self, rect, dy):
        if dy: self._gutter.scroll(0, dy)
        else: self._gutter.update(0, rect.y(), self._gutter.width(), rect.height())
        if rect.contains(self.viewport().rect()): self._upd_w()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self._gutter.setGeometry(QRect(cr.left(), cr.top(), self.gutter_width(), cr.height()))

    def _hl_line(self):
        sels = []
        if not self.isReadOnly():
            sel = QTextEdit.ExtraSelection()
            sel.format.setBackground(T.BG_LINE)
            sel.format.setProperty(QTextFormat.FullWidthSelection, True)
            sel.cursor = self.textCursor()
            sel.cursor.clearSelection()
            sels.append(sel)

        # Bracket matching
        self._match_brackets(sels)
        self.setExtraSelections(sels)

    def _match_brackets(self, sels):
        """Highlight des brackets correspondants."""
        cursor = self.textCursor()
        text = self.document().toPlainText()
        pos = cursor.position()
        if pos <= 0 or pos > len(text): return

        pairs = {'(': ')', '[': ']', '{': '}'}
        rpairs = {')': '(', ']': '[', '}': '{'}

        char_before = text[pos-1] if pos > 0 else ''
        char_at = text[pos] if pos < len(text) else ''

        check_pos = -1
        if char_before in pairs or char_before in rpairs:
            check_pos = pos - 1
        elif char_at in pairs or char_at in rpairs:
            check_pos = pos

        if check_pos < 0: return

        ch = text[check_pos]
        if ch in pairs:
            match_pos = self._find_matching_forward(text, check_pos, ch, pairs[ch])
        elif ch in rpairs:
            match_pos = self._find_matching_backward(text, check_pos, ch, rpairs[ch])
        else:
            return

        if match_pos >= 0:
            fmt = QTextCharFormat()
            fmt.setBackground(QColor(80, 80, 80))
            fmt.setForeground(QColor(255, 255, 255))

            for p in [check_pos, match_pos]:
                sel = QTextEdit.ExtraSelection()
                sel.format = fmt
                sel.cursor = QTextCursor(self.document())
                sel.cursor.setPosition(p)
                sel.cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor)
                sels.append(sel)

    def _find_matching_forward(self, text, pos, open_ch, close_ch):
        depth = 0
        for i in range(pos, len(text)):
            if text[i] == open_ch: depth += 1
            elif text[i] == close_ch: depth -= 1
            if depth == 0: return i
        return -1

    def _find_matching_backward(self, text, pos, close_ch, open_ch):
        depth = 0
        for i in range(pos, -1, -1):
            if text[i] == close_ch: depth += 1
            elif text[i] == open_ch: depth -= 1
            if depth == 0: return i
        return -1

    def paint_gutter(self, event):
        p = QPainter(self._gutter)
        p.fillRect(event.rect(), T.BG)

        # Separator
        p.setPen(QColor(255, 255, 255, 6))
        p.drawLine(self._gutter.width()-1, event.rect().top(), self._gutter.width()-1, event.rect().bottom())

        block = self.firstVisibleBlock()
        bnum = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())
        cur = self.textCursor().blockNumber()
        p.setFont(self._font)

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                p.setPen(QColor(200, 200, 200) if bnum == cur else T.DIM)
                p.drawText(0, top, self._gutter.width()-14,
                          int(self.blockBoundingRect(block).height()),
                          Qt.AlignRight | Qt.AlignVCenter, str(bnum+1))
            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            bnum += 1
        p.end()

    def keyPressEvent(self, event):
        # Auto-indent
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            c = self.textCursor()
            line = c.block().text()
            indent = ""
            for ch in line:
                if ch in (" ", "\t"): indent += ch
                else: break
            stripped = line.rstrip()

            # Python
            if self.lang == "Python" and stripped.endswith(":"):
                indent += "    "
            # C++ / braces
            elif self.lang in ("C++", "C") and stripped.endswith("{"):
                indent += "    "

            super().keyPressEvent(event)
            self.insertPlainText(indent)

            # Auto close brace
            if self.lang in ("C++", "C") and stripped.endswith("{"):
                pos = self.textCursor()
                self.insertPlainText("\n" + indent[:-4] + "}")
                self.setTextCursor(pos)

            return

        # Tab
        if event.key() == Qt.Key_Tab:
            if event.modifiers() & Qt.ShiftModifier:
                c = self.textCursor()
                c.movePosition(QTextCursor.StartOfBlock)
                c.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, 4)
                if c.selectedText() == "    ": c.removeSelectedText()
                return
            self.insertPlainText("    ")
            return

        # Ctrl+/
        if event.key() == Qt.Key_Slash and event.modifiers() & Qt.ControlModifier:
            self._toggle_comment(); return

        # Auto-close
        pairs = {Qt.Key_ParenLeft: "()", Qt.Key_BracketLeft: "[]", Qt.Key_BraceLeft: "{}"}
        if event.key() in pairs:
            self.insertPlainText(pairs[event.key()])
            c = self.textCursor(); c.movePosition(QTextCursor.Left); self.setTextCursor(c)
            return
        for k, p in [(Qt.Key_QuoteDbl, '""'), (Qt.Key_Apostrophe, "''")]:
            if event.key() == k:
                self.insertPlainText(p)
                c = self.textCursor(); c.movePosition(QTextCursor.Left); self.setTextCursor(c)
                return

        # Ctrl+D duplicate
        if event.key() == Qt.Key_D and event.modifiers() & Qt.ControlModifier:
            c = self.textCursor()
            c.movePosition(QTextCursor.StartOfBlock)
            c.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
            txt = c.selectedText()
            c.movePosition(QTextCursor.EndOfBlock)
            c.insertText("\n" + txt)
            return

        # Ctrl+Shift+K delete line
        if event.key() == Qt.Key_K and event.modifiers() == (Qt.ControlModifier | Qt.ShiftModifier):
            c = self.textCursor()
            c.movePosition(QTextCursor.StartOfBlock)
            c.movePosition(QTextCursor.NextBlock, QTextCursor.KeepAnchor)
            c.removeSelectedText()
            return

        super().keyPressEvent(event)

    def _toggle_comment(self):
        prefix = "# " if self.lang == "Python" else "// "
        c = self.textCursor(); c.beginEditBlock()
        if c.hasSelection():
            start = c.selectionStart(); end = c.selectionEnd()
            c.setPosition(start); sb = c.blockNumber()
            c.setPosition(end); eb = c.blockNumber()
            c.setPosition(start)
            for _ in range(eb - sb + 1):
                c.movePosition(QTextCursor.StartOfBlock)
                line = c.block().text()
                if line.lstrip().startswith(prefix.rstrip()):
                    idx = line.index(prefix.rstrip())
                    c.movePosition(QTextCursor.Right, QTextCursor.MoveAnchor, idx)
                    rm = len(prefix) if len(line) > idx + len(prefix) - 1 and line[idx+len(prefix)-1] == " " else len(prefix)-1
                    c.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, rm)
                    c.removeSelectedText()
                else:
                    c.insertText(prefix)
                c.movePosition(QTextCursor.NextBlock)
        else:
            c.movePosition(QTextCursor.StartOfBlock)
            line = c.block().text()
            if line.lstrip().startswith(prefix.rstrip()):
                idx = line.index(prefix.rstrip())
                c.movePosition(QTextCursor.Right, QTextCursor.MoveAnchor, idx)
                rm = len(prefix) if len(line) > idx + len(prefix) - 1 else len(prefix) - 1
                c.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, rm)
                c.removeSelectedText()
            else:
                c.insertText(prefix)
        c.endEditBlock()


# ═══════════════════════════════════════════════════════
#  ACTIVITY BAR
# ═══════════════════════════════════════════════════════

class ActivityBar(QWidget):
    view_changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(48)
        self._items = [("file","Explorer"),("search","Search")]
        self._active = 0; self._hover = -1
        self.setMouseTracking(True); self.setCursor(Qt.PointingHandCursor)
        self._px = [get_pixmap(n,22,QColor(255,255,255,140)) for n,_ in self._items]
        self._px_a = [get_pixmap(n,22,QColor(255,255,255,255)) for n,_ in self._items]

    def paintEvent(self, event):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), T.BG_ACT)
        for i, (n, tip) in enumerate(self._items):
            y = i * 48
            if i == self._active:
                p.fillRect(QRect(0, y, 2, 48), T.WHITE)
                p.drawPixmap(13, y+13, self._px_a[i])
            elif i == self._hover:
                p.drawPixmap(13, y+13, self._px_a[i])
            else:
                p.drawPixmap(13, y+13, self._px[i])
        p.setPen(QColor(255,255,255,4))
        p.drawLine(self.width()-1, 0, self.width()-1, self.height())
        p.end()

    def mouseMoveEvent(self, e):
        old = self._hover
        self._hover = int(e.position().y()//48) if e.position().y() < len(self._items)*48 else -1
        if old != self._hover: self.update()

    def leaveEvent(self, e): self._hover = -1; self.update()
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and self._hover >= 0:
            self._active = self._hover; self.view_changed.emit(self._active); self.update()


# ═══════════════════════════════════════════════════════
#  EXPLORER PANEL
# ═══════════════════════════════════════════════════════

class ExplorerPanel(QWidget):
    file_opened = Signal(str)

    def __init__(self, root="", parent=None):
        super().__init__(parent)
        self.root = root
        self.setStyleSheet(f"background:{T.BG2.name()};")
        lo = QVBoxLayout(self); lo.setContentsMargins(0,0,0,0); lo.setSpacing(0)

        hdr = QWidget(); hdr.setFixedHeight(34)
        hl = QHBoxLayout(hdr); hl.setContentsMargins(16,0,8,0)
        tl = QLabel("EXPLORER"); tl.setFont(QFont("Segoe UI",8))
        tl.setStyleSheet("color:rgba(255,255,255,50);letter-spacing:1px;")
        hl.addWidget(tl); hl.addStretch()

        # Refresh button
        rb = QPushButton(); rb.setFixedSize(20,20); rb.setCursor(Qt.PointingHandCursor)
        rb.setIcon(get_icon("refresh",12,QColor(255,255,255,100)))
        rb.setStyleSheet("QPushButton{background:transparent;border:none;}QPushButton:hover{background:rgba(255,255,255,8);border-radius:3px;}")
        rb.clicked.connect(self.refresh)
        hl.addWidget(rb)
        lo.addWidget(hdr)

        self.tree = QTreeWidget(); self.tree.setHeaderHidden(True)
        self.tree.setIndentation(16); self.tree.setAnimated(True)
        self.tree.setStyleSheet(f"""
            QTreeWidget{{background:{T.BG2.name()};color:{T.TEXT.name()};border:none;font-size:12px;outline:none;}}
            QTreeWidget::item{{padding:2px 4px;border-radius:3px;margin:0 4px;}}
            QTreeWidget::item:hover{{background:rgba(255,255,255,5);}}
            QTreeWidget::item:selected{{background:rgba(255,255,255,8);}}
            QTreeWidget::branch{{background:transparent;}}
            QScrollBar:vertical{{width:6px;background:transparent;}}
            QScrollBar::handle:vertical{{background:rgba(255,255,255,10);border-radius:2px;min-height:20px;}}
            QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{{height:0;}}
        """)
        self.tree.itemDoubleClicked.connect(self._dbl)
        lo.addWidget(self.tree)

    def set_root(self, p): self.root = p; self.refresh()

    def refresh(self):
        self.tree.clear()
        if not self.root or not os.path.exists(self.root): return
        ri = QTreeWidgetItem([os.path.basename(self.root)])
        ri.setData(0, Qt.UserRole, self.root)
        ri.setIcon(0, get_icon("folder",14)); ri.setExpanded(True)
        self._fill(ri, self.root, 0)
        self.tree.addTopLevelItem(ri)

    def _fill(self, parent, path, depth):
        if depth > 5: return
        try:
            entries = sorted(os.listdir(path), key=lambda x: (not os.path.isdir(os.path.join(path,x)), x.lower()))
        except: return
        for name in entries:
            if name.startswith('.'): continue
            fp = os.path.join(path, name)
            item = QTreeWidgetItem([name])
            item.setData(0, Qt.UserRole, fp)
            if os.path.isdir(fp):
                item.setIcon(0, get_icon("folder",14))
                self._fill(item, fp, depth+1)
            else:
                from core.icons import get_file_icon
                item.setIcon(0, get_file_icon(name, 14))
            parent.addChild(item)

    def _dbl(self, item, col):
        p = item.data(0, Qt.UserRole)
        if p and os.path.isfile(p): self.file_opened.emit(p)


# ═══════════════════════════════════════════════════════
#  OUTPUT PANEL
# ═══════════════════════════════════════════════════════

class OutputPanel(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setFont(QFont(MONO, 10))
        self.setStyleSheet("""
            QPlainTextEdit{background:#1e1e1e;color:#ccc;border:none;padding:6px 10px;selection-background-color:#264f78;}
            QScrollBar:vertical{width:6px;background:transparent;}
            QScrollBar::handle:vertical{background:rgba(255,255,255,10);border-radius:2px;min-height:20px;}
            QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0;}
        """)
        self.setMaximumBlockCount(10000)

    def w_out(self, t):
        c = self.textCursor(); c.movePosition(QTextCursor.End)
        c.insertText(t); self.setTextCursor(c); self.ensureCursorVisible()

    def w_err(self, t):
        c = self.textCursor(); c.movePosition(QTextCursor.End)
        fmt = QTextCharFormat(); fmt.setForeground(QColor(255,85,85))
        c.setCharFormat(fmt); c.insertText(t)
        self.setTextCursor(c); self.ensureCursorVisible()

    def w_info(self, t):
        c = self.textCursor(); c.movePosition(QTextCursor.End)
        fmt = QTextCharFormat(); fmt.setForeground(QColor(78,201,176))
        c.setCharFormat(fmt); c.insertText(t)
        self.setTextCursor(c); self.ensureCursorVisible()


# ═══════════════════════════════════════════════════════
#  RUNNER — Python + C++
# ═══════════════════════════════════════════════════════

def _find_cpp_compiler():
    """Cherche g++, clang++ ou cl.exe."""
    for name in ["g++", "clang++", "c++"]:
        if shutil.which(name): return shutil.which(name)
    # Windows : chercher cl.exe ou MinGW
    for p in [r"C:\MinGW\bin\g++.exe", r"C:\msys64\mingw64\bin\g++.exe",
              r"C:\TDM-GCC-64\bin\g++.exe"]:
        if os.path.exists(p): return p
    return None


class Runner:
    def __init__(self, output):
        self.output = output
        self._proc = None
        self._tmp = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "user_data", ".code_temp"
        )
        os.makedirs(self._tmp, exist_ok=True)
        self._t0 = 0

    def is_running(self):
        return self._proc is not None and self._proc.state() == QProcess.Running

    def run_python(self, code=None, filepath=None, name="untitled.py"):
        if self.is_running(): self.stop()
        if code is not None:
            fp = os.path.join(self._tmp, "_run.py")
            with open(fp, "w", encoding="utf-8") as f: f.write(code)
        elif filepath:
            fp = filepath
            name = os.path.basename(filepath)
        else:
            return
        self._start(PYTHON_EXE, ["-u", fp], name, os.path.dirname(fp))

    def run_cpp(self, code=None, filepath=None, name="untitled.cpp"):
        if self.is_running(): self.stop()

        compiler = _find_cpp_compiler()
        if not compiler:
            self.output.clear()
            self.output.w_err("C++ compiler not found!\n")
            self.output.w_err("Install one of:\n")
            self.output.w_err("  • MinGW (g++): https://www.mingw-w64.org/\n")
            self.output.w_err("  • TDM-GCC: https://jmeubank.github.io/tdm-gcc/\n")
            self.output.w_err("  • MSYS2: https://www.msys2.org/\n")
            return

        if code is not None:
            src = os.path.join(self._tmp, "_run.cpp")
            with open(src, "w", encoding="utf-8") as f: f.write(code)
        elif filepath:
            src = filepath
            name = os.path.basename(filepath)
        else:
            return

        ext = ".exe" if sys.platform == "win32" else ""
        out_bin = os.path.join(self._tmp, f"_run_out{ext}")

        self.output.clear()
        self.output.w_info(f"⚙ Compiling {name}...\n")
        self.output.w_info(f"  Compiler: {compiler}\n")
        self.output.w_info(f"{'─' * 60}\n")

        # Compilation synchrone
        try:
            result = subprocess.run(
                [compiler, "-std=c++17", "-o", out_bin, src],
                capture_output=True, text=True, timeout=30,
                cwd=os.path.dirname(src)
            )
            if result.returncode != 0:
                self.output.w_err(result.stderr)
                self.output.w_err(f"\n✗ Compilation failed\n")
                return
            if result.stderr:
                self.output.w_err(result.stderr)

            self.output.w_info(f"✓ Compiled successfully\n")
            self.output.w_info(f"{'─' * 60}\n")
            self.output.w_info(f"▶ Running...\n")
            self.output.w_info(f"{'─' * 60}\n")

        except FileNotFoundError:
            self.output.w_err(f"Compiler not found: {compiler}\n")
            return
        except subprocess.TimeoutExpired:
            self.output.w_err("Compilation timed out (30s)\n")
            return

        # Exécution
        self._start(out_bin, [], name, os.path.dirname(src))

    def _start(self, exe, args, name, cwd):
        self.output.clear() if not self.output.toPlainText() else None

        if not self.output.toPlainText():
            self.output.w_info(f"▶ Running {name}\n")
            self.output.w_info(f"{'─' * 60}\n")

        self._t0 = time.time()
        self._proc = QProcess()
        self._proc.setWorkingDirectory(cwd)

        env = QProcessEnvironment.systemEnvironment()
        self._proc.setProcessEnvironment(env)

        self._proc.readyReadStandardOutput.connect(self._out)
        self._proc.readyReadStandardError.connect(self._err)
        self._proc.finished.connect(self._done)

        self._proc.start(exe, args)
        if not self._proc.waitForStarted(5000):
            self.output.w_err(f"Failed to start: {exe}\n")
            self._proc = None

    def stop(self):
        if self._proc and self._proc.state() == QProcess.Running:
            self._proc.kill(); self._proc.waitForFinished(2000)
            self.output.w_info("\n⬛ Killed.\n")

    def _out(self):
        if self._proc:
            self.output.w_out(self._proc.readAllStandardOutput().data().decode("utf-8", errors="replace"))

    def _err(self):
        if self._proc:
            self.output.w_err(self._proc.readAllStandardError().data().decode("utf-8", errors="replace"))

    def _done(self, code, status):
        dt = time.time() - self._t0
        self.output.w_info(f"\n{'─' * 60}\n")
        if code == 0:
            self.output.w_info(f"✓ Done ({dt:.2f}s)\n")
        else:
            self.output.w_err(f"✗ Exit code {code} ({dt:.2f}s)\n")
        self._proc = None


# ═══════════════════════════════════════════════════════
#  MINIMAP
# ═══════════════════════════════════════════════════════

class MiniMap(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ed = None; self.setFixedWidth(55); self.setCursor(Qt.PointingHandCursor)

    def set_ed(self, ed):
        self.ed = ed
        try: ed.textChanged.connect(self.update)
        except: pass
        try: ed.updateRequest.connect(lambda: self.update())
        except: pass
        self.update()

    def paintEvent(self, event):
        p = QPainter(self); p.fillRect(self.rect(), T.BG_MINI)
        if not self.ed: p.end(); return
        lines = self.ed.toPlainText().split("\n")
        if not lines: p.end(); return
        h = self.height(); lh = max(0.8, min(2.5, h / max(len(lines), 1)))

        for i, line in enumerate(lines[:int(h/max(lh,0.1))]):
            y = int(i*lh)
            if line.strip():
                indent = len(line)-len(line.lstrip()); length = min(len(line.rstrip()),60)
                x = int(indent*0.6); w = int(length*0.6)
                if line.strip().startswith(("#","//")): p.setBrush(QColor(106,153,85,50))
                elif any(line.strip().startswith(k) for k in ("def ","class ","void ","int ","auto ")): p.setBrush(QColor(86,156,214,70))
                elif line.strip().startswith(("#include","import ","from ")): p.setBrush(QColor(220,220,170,40))
                else: p.setBrush(QColor(200,200,200,30))
                p.setPen(Qt.NoPen); p.drawRect(x+2, y, max(1,w), max(1,int(lh)))

        # Viewport
        block = self.ed.firstVisibleBlock()
        bh = self.ed.blockBoundingRect(block).height()
        fv = block.blockNumber()
        vl = int(self.ed.viewport().height()/max(bh,1))
        vy = int(fv*lh); vh = int(vl*lh)
        p.setBrush(QColor(255,255,255,10)); p.setPen(QPen(QColor(255,255,255,16),1))
        p.drawRect(0, vy, self.width(), vh)
        p.end()

    def mousePressEvent(self, e): self._scroll(e.position().y())
    def mouseMoveEvent(self, e):
        if e.buttons() & Qt.LeftButton: self._scroll(e.position().y())

    def _scroll(self, y):
        if not self.ed: return
        total = max(1, self.ed.document().blockCount())
        line = int((y/max(1,self.height()))*total)
        block = self.ed.document().findBlockByLineNumber(min(line,total-1))
        c = QTextCursor(block); self.ed.setTextCursor(c); self.ed.centerCursor()


# ═══════════════════════════════════════════════════════
#  TAB
# ═══════════════════════════════════════════════════════

class EditorTab:
    def __init__(self, path=None, name="untitled.py"):
        self.path = path
        self.name = name
        self.lang = detect_lang(name)
        self.editor = CodeEditor(self.lang)
        self.modified = False
        self.encoding = "UTF-8"

        if path and os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self.editor.setPlainText(f.read())
                self.name = os.path.basename(path)
                self.lang = detect_lang(self.name)
                self.editor.set_language(self.lang)
            except: pass

        self.editor.textChanged.connect(lambda: setattr(self, 'modified', True))


# ═══════════════════════════════════════════════════════
#  TAB BAR
# ═══════════════════════════════════════════════════════

class TabBar(QWidget):
    tab_clicked = Signal(int)
    tab_closed = Signal(int)
    new_tab = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(35)
        self.tabs = []; self.active = 0; self._hover = -1; self._hover_close = -1
        self.setMouseTracking(True)

    def set_tabs(self, info, active):
        self.tabs = info; self.active = active; self.update()

    def _tw(self):
        return min(200, max(100, (self.width()-32)//max(1,len(self.tabs))))

    def paintEvent(self, event):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing); p.setRenderHint(QPainter.TextAntialiasing)
        p.fillRect(self.rect(), T.BG2)
        tw = self._tw(); x = 0
        for i, (name, mod, lang) in enumerate(self.tabs):
            r = QRect(x, 0, tw, self.height())
            if i == self.active:
                p.fillRect(r, T.BG)
                p.fillRect(QRect(x, 0, tw, 2), T.ACCENT)
            elif i == self._hover:
                p.fillRect(r, T.BG_HOVER)

            # Language-specific icon color
            ic = QColor(80,160,255) if lang == "Python" else QColor(0,160,220) if lang in ("C++","C") else QColor(200,200,200)
            px = get_pixmap("file", 14, ic)
            p.drawPixmap(x+10, (self.height()-14)//2, px)

            p.setFont(QFont("Segoe UI", 9))
            p.setPen(QColor(255,255,255, 200 if i == self.active else 100))
            display = ("● " if mod else "") + name
            fm = p.fontMetrics()
            p.drawText(QRect(x+28, 0, tw-54, self.height()), Qt.AlignVCenter,
                       fm.elidedText(display, Qt.ElideRight, tw-54))

            cx = x + tw - 18; cy = self.height()//2
            if i == self._hover_close:
                p.setBrush(QColor(255,255,255,12)); p.setPen(Qt.NoPen)
                p.drawRoundedRect(cx-7, cy-7, 14, 14, 3, 3)
            if i == self.active or i == self._hover:
                p.setPen(QPen(QColor(255,255,255,90), 1))
                p.drawLine(cx-3, cy-3, cx+3, cy+3)
                p.drawLine(cx+3, cy-3, cx-3, cy+3)
            x += tw

        nr = QRect(x+4, (self.height()-24)//2, 24, 24)
        if self._hover == -2:
            p.setBrush(QColor(255,255,255,6)); p.setPen(Qt.NoPen)
            p.drawRoundedRect(nr, 4, 4)
        p.setPen(QPen(QColor(255,255,255,70), 1.2))
        cx, cy = nr.center().x(), nr.center().y()
        p.drawLine(cx-5, cy, cx+5, cy); p.drawLine(cx, cy-5, cx, cy+5)

        p.setPen(QColor(30,30,30))
        p.drawLine(0, self.height()-1, self.width(), self.height()-1)
        p.end()

    def mouseMoveEvent(self, event):
        tw = self._tw(); mx = event.position().x()
        old_h, old_c = self._hover, self._hover_close
        self._hover = -1; self._hover_close = -1
        for i in range(len(self.tabs)):
            x = i * tw
            if x <= mx < x + tw:
                self._hover = i
                cx = x + tw - 18
                if abs(mx-cx) < 9 and abs(event.position().y()-self.height()/2) < 9:
                    self._hover_close = i
                break
        if len(self.tabs)*tw+4 <= mx < len(self.tabs)*tw+32:
            self._hover = -2
        if old_h != self._hover or old_c != self._hover_close: self.update()

    def leaveEvent(self, e): self._hover = -1; self._hover_close = -1; self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self._hover_close >= 0: self.tab_closed.emit(self._hover_close)
            elif self._hover == -2: self.new_tab.emit()
            elif self._hover >= 0: self.tab_clicked.emit(self._hover)
        elif event.button() == Qt.MiddleButton and self._hover >= 0:
            self.tab_closed.emit(self._hover)


# ═══════════════════════════════════════════════════════
#  BREADCRUMB
# ═══════════════════════════════════════════════════════

class Breadcrumb(QWidget):
    def __init__(self, p=None):
        super().__init__(p); self.setFixedHeight(22); self.parts = []; self.lang = ""

    def set_path(self, path, lang=""):
        self.lang = lang
        self.parts = (path or "untitled").replace("\\","/").split("/")
        self.update()

    def paintEvent(self, event):
        p = QPainter(self); p.setRenderHint(QPainter.TextAntialiasing)
        p.fillRect(self.rect(), T.BG2)
        p.setFont(QFont("Segoe UI",9)); x = 12
        for i, part in enumerate(self.parts[-3:]):
            is_last = (i == len(self.parts[-3:])-1)
            p.setPen(QColor(255,255,255, 200 if is_last else 90))
            p.drawText(QRect(x,0,200,self.height()), Qt.AlignVCenter, part)
            x += p.fontMetrics().horizontalAdvance(part) + 4
            if not is_last:
                p.setPen(QColor(255,255,255,30))
                p.drawText(QRect(x,0,20,self.height()), Qt.AlignVCenter, "›")
                x += 12
        # Language badge
        if self.lang:
            p.setFont(QFont("Segoe UI",7))
            p.setPen(QColor(255,255,255,40))
            p.drawText(QRect(self.width()-80, 0, 70, self.height()), Qt.AlignVCenter|Qt.AlignRight, self.lang)
        p.end()


# ═══════════════════════════════════════════════════════
#  STATUS BAR
# ═══════════════════════════════════════════════════════

class StatusBar(QWidget):
    def __init__(self, p=None):
        super().__init__(p); self.setFixedHeight(22)
        self.ln=1; self.col=1; self.name=""; self.lang="Python"
        self.enc="UTF-8"; self.running=False; self.indent="Spaces: 4"

    def paintEvent(self, event):
        p = QPainter(self); p.setRenderHint(QPainter.TextAntialiasing)
        bg = T.STATUS_RUN if self.running else T.STATUS
        p.fillRect(self.rect(), bg)
        p.setFont(QFont("Segoe UI",9))
        p.setPen(QColor(255,255,255,220))
        left = f"  {'▶ Running...' if self.running else f'Ln {self.ln}, Col {self.col}'}"
        right = f"{self.indent}     {self.enc}     {self.lang}  "
        p.drawText(QRect(0,0,self.width()//2,self.height()), Qt.AlignVCenter|Qt.AlignLeft, left)
        p.drawText(QRect(self.width()//2,0,self.width()//2,self.height()), Qt.AlignVCenter|Qt.AlignRight, right)
        p.end()


# ═══════════════════════════════════════════════════════
#  PANEL HEADER
# ═══════════════════════════════════════════════════════

class PanelHeader(QWidget):
    clear_clicked = Signal()

    def __init__(self, p=None):
        super().__init__(p); self.setFixedHeight(30); self._tabs = ["OUTPUT","TERMINAL","PROBLEMS"]
        self._active = 0; self.setMouseTracking(True)

    def paintEvent(self, event):
        p = QPainter(self); p.setRenderHint(QPainter.TextAntialiasing)
        p.fillRect(self.rect(), T.BG3)
        p.setPen(QColor(255,255,255,4)); p.drawLine(0,0,self.width(),0)
        x = 12; p.setFont(QFont("Segoe UI",8))
        for i, tab in enumerate(self._tabs):
            w = p.fontMetrics().horizontalAdvance(tab)+16
            p.setPen(QColor(255,255,255, 200 if i==self._active else 40))
            p.drawText(QRect(x,0,w,self.height()), Qt.AlignCenter, tab)
            if i == self._active:
                p.fillRect(QRect(x, self.height()-2, w, 2), T.ACCENT)
            x += w
        p.setPen(QPen(QColor(255,255,255,50),1))
        cx = self.width()-20; cy = self.height()//2
        p.drawLine(cx-4,cy-4,cx+4,cy+4); p.drawLine(cx+4,cy-4,cx-4,cy+4)
        p.end()

    def mousePressEvent(self, e):
        if e.position().x() > self.width()-30: self.clear_clicked.emit()


# ═══════════════════════════════════════════════════════
#  APP
# ═══════════════════════════════════════════════════════

class App(QWidget):
    def __init__(self, file_system=None, parent=None):
        super().__init__(parent)
        self.fs = file_system
        self._tabs = []; self._cur = -1

        lo = QVBoxLayout(self); lo.setContentsMargins(0,0,0,0); lo.setSpacing(0)
        self._build_menu(lo)

        self.tab_bar = TabBar()
        self.tab_bar.tab_clicked.connect(self._switch)
        self.tab_bar.tab_closed.connect(self._close)
        self.tab_bar.new_tab.connect(self._new_py)
        lo.addWidget(self.tab_bar)

        main_h = QHBoxLayout(); main_h.setContentsMargins(0,0,0,0); main_h.setSpacing(0)

        self.activity = ActivityBar(); self.activity.view_changed.connect(self._on_act)
        main_h.addWidget(self.activity)

        self.sidebar = QStackedWidget(); self.sidebar.setFixedWidth(220)
        self.explorer = ExplorerPanel(self.fs.get_base_path() if self.fs else os.path.expanduser("~"))
        self.explorer.file_opened.connect(self._open_path)
        self.sidebar.addWidget(self.explorer)

        # Search panel
        sp = QWidget(); sp.setStyleSheet(f"background:{T.BG2.name()};")
        spl = QVBoxLayout(sp); spl.setContentsMargins(12,12,12,12)
        sl = QLabel("SEARCH"); sl.setFont(QFont("Segoe UI",8)); sl.setStyleSheet("color:rgba(255,255,255,50);letter-spacing:1px;")
        spl.addWidget(sl)
        se = QLineEdit(); se.setPlaceholderText("Search...")
        se.setStyleSheet("QLineEdit{background:rgba(255,255,255,6);border:1px solid rgba(255,255,255,8);border-radius:4px;color:white;padding:4px 8px;font-size:12px;}")
        spl.addWidget(se); spl.addStretch()
        self.sidebar.addWidget(sp)
        main_h.addWidget(self.sidebar)

        vs = QSplitter(Qt.Vertical)
        vs.setStyleSheet("QSplitter::handle{background:rgba(255,255,255,2);height:3px;}")

        ea = QWidget(); eal = QVBoxLayout(ea); eal.setContentsMargins(0,0,0,0); eal.setSpacing(0)
        self.bc = Breadcrumb(); eal.addWidget(self.bc)
        eh = QHBoxLayout(); eh.setContentsMargins(0,0,0,0); eh.setSpacing(0)
        self.estack = QStackedWidget(); eh.addWidget(self.estack, 1)
        self.minimap = MiniMap(); eh.addWidget(self.minimap)
        eal.addLayout(eh, 1)
        vs.addWidget(ea)

        oa = QWidget(); oal = QVBoxLayout(oa); oal.setContentsMargins(0,0,0,0); oal.setSpacing(0)
        self.ph = PanelHeader(); self.ph.clear_clicked.connect(lambda: self.output.clear())
        oal.addWidget(self.ph)
        self.output = OutputPanel(); oal.addWidget(self.output)
        vs.addWidget(oa)
        vs.setSizes([500,180])
        main_h.addWidget(vs, 1)
        lo.addLayout(main_h, 1)

        self.status = StatusBar(); lo.addWidget(self.status)
        self.runner = Runner(self.output)
        self._new_py()
        QTimer.singleShot(100, self.explorer.refresh)

    def _build_menu(self, lo):
        mb = QMenuBar()
        mb.setStyleSheet(f"""
            QMenuBar{{background:{T.BG2.name()};color:rgba(255,255,255,160);padding:0 4px;font-size:12px;}}
            QMenuBar::item{{padding:4px 10px;border-radius:3px;}}
            QMenuBar::item:selected{{background:rgba(255,255,255,6);}}
            QMenu{{background:#2d2d2d;border:1px solid rgba(255,255,255,10);border-radius:8px;padding:4px 0;color:rgba(255,255,255,200);}}
            QMenu::item{{padding:5px 28px 5px 12px;border-radius:4px;margin:1px 4px;}}
            QMenu::item:selected{{background:rgba(255,255,255,6);}}
            QMenu::separator{{height:1px;background:rgba(255,255,255,5);margin:4px 12px;}}
        """)

        fm = mb.addMenu("File")
        fm.addAction("New Python File", self._new_py, QKeySequence("Ctrl+N"))
        fm.addAction("New C++ File", self._new_cpp)
        fm.addAction("Open File...", self._open, QKeySequence("Ctrl+O"))
        fm.addAction("Open Folder...", self._open_folder)
        fm.addSeparator()
        fm.addAction("Save", self._save, QKeySequence("Ctrl+S"))
        fm.addAction("Save As...", self._save_as, QKeySequence("Ctrl+Shift+S"))
        fm.addSeparator()
        fm.addAction("Close Tab", lambda: self._close(self._cur), QKeySequence("Ctrl+W"))

        em = mb.addMenu("Edit")
        em.addAction("Undo", lambda: self._ed() and self._ed().undo(), QKeySequence("Ctrl+Z"))
        em.addAction("Redo", lambda: self._ed() and self._ed().redo(), QKeySequence("Ctrl+Y"))
        em.addSeparator()
        em.addAction("Cut", lambda: self._ed() and self._ed().cut(), QKeySequence("Ctrl+X"))
        em.addAction("Copy", lambda: self._ed() and self._ed().copy(), QKeySequence("Ctrl+C"))
        em.addAction("Paste", lambda: self._ed() and self._ed().paste(), QKeySequence("Ctrl+V"))
        em.addSeparator()
        em.addAction("Comment", lambda: self._ed() and self._ed()._toggle_comment(), QKeySequence("Ctrl+/"))
        em.addAction("Select All", lambda: self._ed() and self._ed().selectAll(), QKeySequence("Ctrl+A"))

        rm = mb.addMenu("Run")
        rm.addAction("▶ Run", self._run, QKeySequence("F5"))
        rm.addAction("⬛ Stop", self._stop, QKeySequence("Shift+F5"))
        rm.addSeparator()
        rm.addAction("Run File...", self._run_ext)

        vm = mb.addMenu("View")
        vm.addAction("Toggle Sidebar", self._toggle_sb, QKeySequence("Ctrl+B"))
        vm.addSeparator()
        vm.addAction("Zoom In", lambda: self._zoom(2), QKeySequence("Ctrl++"))
        vm.addAction("Zoom Out", lambda: self._zoom(-2), QKeySequence("Ctrl+-"))

        lo.addWidget(mb)

    def _ed(self):
        return self._tabs[self._cur].editor if 0 <= self._cur < len(self._tabs) else None

    def _tab(self):
        return self._tabs[self._cur] if 0 <= self._cur < len(self._tabs) else None

    def _upd_tabs(self):
        self.tab_bar.set_tabs([(t.name, t.modified, t.lang) for t in self._tabs], self._cur)

    def _upd_status(self):
        ed = self._ed(); tab = self._tab()
        if ed and tab:
            c = ed.textCursor()
            self.status.ln = c.blockNumber()+1; self.status.col = c.columnNumber()+1
            self.status.name = tab.name; self.status.lang = tab.lang
            self.status.running = self.runner.is_running()
            self.status.update()

    def _switch(self, idx):
        if 0 <= idx < len(self._tabs):
            self._cur = idx; tab = self._tabs[idx]
            self.estack.setCurrentWidget(tab.editor)
            self.minimap.set_ed(tab.editor)
            self.bc.set_path(tab.path or tab.name, tab.lang)
            try: tab.editor.cursorPositionChanged.disconnect(self._upd_status)
            except: pass
            tab.editor.cursorPositionChanged.connect(self._upd_status)
            self._upd_tabs(); self._upd_status()

    def _new_py(self):
        tab = EditorTab(name="untitled.py")
        tab.editor.setPlainText('# Python\n\nprint("Hello, World!")\n')
        tab.modified = False
        self._tabs.append(tab); self.estack.addWidget(tab.editor)
        self._switch(len(self._tabs)-1)

    def _new_cpp(self):
        tab = EditorTab(name="untitled.cpp")
        tab.editor.setPlainText('#include <iostream>\n\nint main() {\n    std::cout << "Hello, World!" << std::endl;\n    return 0;\n}\n')
        tab.lang = "C++"; tab.editor.set_language("C++"); tab.modified = False
        self._tabs.append(tab); self.estack.addWidget(tab.editor)
        self._switch(len(self._tabs)-1)

    def _open(self):
        start = self.fs.get_base_path() if self.fs else os.path.expanduser("~")
        p, _ = QFileDialog.getOpenFileName(self, "Open", start,
            "Code (*.py *.cpp *.c *.h *.hpp *.js *.html *.css *.json *.txt);;All (*)")
        if p: self._open_path(p)

    def _open_path(self, path):
        for i, t in enumerate(self._tabs):
            if t.path == path: self._switch(i); return
        tab = EditorTab(path=path)
        self._tabs.append(tab); self.estack.addWidget(tab.editor)
        self._switch(len(self._tabs)-1)

    def _open_folder(self):
        start = self.fs.get_base_path() if self.fs else os.path.expanduser("~")
        p = QFileDialog.getExistingDirectory(self, "Open Folder", start)
        if p: self.explorer.set_root(p)

    def _save(self):
        tab = self._tab()
        if not tab: return
        if tab.path:
            try:
                with open(tab.path, "w", encoding="utf-8") as f:
                    f.write(tab.editor.toPlainText())
                tab.modified = False; self._upd_tabs()
                self.explorer.refresh()
            except Exception as e:
                self.output.w_err(f"Save error: {e}\n")
        else:
            self._save_as()

    def _save_as(self):
        tab = self._tab()
        if not tab: return
        start = self.fs.get_base_path() if self.fs else os.path.expanduser("~")
        ext = detect_ext(tab.lang)
        p, _ = QFileDialog.getSaveFileName(self, "Save As", os.path.join(start, tab.name),
            f"Code (*{ext});;All (*)")
        if p:
            tab.path = p; tab.name = os.path.basename(p)
            new_lang = detect_lang(tab.name)
            if new_lang != tab.lang:
                tab.lang = new_lang; tab.editor.set_language(new_lang)
            self.bc.set_path(p, tab.lang); self._save()

    def _close(self, idx):
        if 0 <= idx < len(self._tabs):
            tab = self._tabs.pop(idx)
            self.estack.removeWidget(tab.editor); tab.editor.deleteLater()
            if not self._tabs: self._new_py()
            else:
                self._cur = min(self._cur, len(self._tabs)-1)
                self._switch(self._cur)

    def _run(self):
        tab = self._tab()
        if not tab: return
        if tab.path: self._save()

        if tab.lang in ("C++", "C"):
            if tab.path:
                self.runner.run_cpp(filepath=tab.path, name=tab.name)
            else:
                self.runner.run_cpp(code=tab.editor.toPlainText(), name=tab.name)
        else:
            if tab.path:
                self.runner.run_python(filepath=tab.path, name=tab.name)
            else:
                self.runner.run_python(code=tab.editor.toPlainText(), name=tab.name)

        self.status.running = True; self.status.update()
        self._rcheck = QTimer(self); self._rcheck.timeout.connect(self._chk_run); self._rcheck.start(500)

    def _run_ext(self):
        start = self.fs.get_base_path() if self.fs else ""
        p, _ = QFileDialog.getOpenFileName(self, "Run", start, "Code (*.py *.cpp *.c)")
        if p:
            lang = detect_lang(p)
            if lang in ("C++", "C"):
                self.runner.run_cpp(filepath=p)
            else:
                self.runner.run_python(filepath=p)
            self.status.running = True; self.status.update()
            self._rcheck = QTimer(self); self._rcheck.timeout.connect(self._chk_run); self._rcheck.start(500)

    def _stop(self):
        self.runner.stop(); self.status.running = False; self.status.update()

    def _chk_run(self):
        if not self.runner.is_running():
            self.status.running = False; self.status.update()
            if hasattr(self, '_rcheck'): self._rcheck.stop()

    def _toggle_sb(self):
        v = self.sidebar.isVisible()
        self.sidebar.setVisible(not v); self.activity.setVisible(not v)

    def _on_act(self, idx):
        self.sidebar.setCurrentIndex(idx)

    def _zoom(self, d):
        ed = self._ed()
        if ed:
            if d > 0: ed.zoomIn(d)
            else: ed.zoomOut(-d)