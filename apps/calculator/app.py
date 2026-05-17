from PySide6.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QSizePolicy
from PySide6.QtCore import Qt, QRect, QRectF
from PySide6.QtGui import QFont, QColor, QPainter, QPen


class CalcButton(QWidget):
    def __init__(self, text, btn_type="num", parent=None):
        super().__init__(parent)
        self.text = text
        self.btn_type = btn_type
        self.pressed_state = False
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumSize(64, 46)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.callback = None

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)

        r = self.rect().adjusted(2, 2, -2, -2)

        if self.btn_type == "equals":
            bg = QColor(0, 103, 192) if not self.pressed_state else QColor(0, 85, 160)
            hover_bg = QColor(20, 115, 200)
        elif self.btn_type == "num":
            bg = QColor(59, 59, 59) if not self.pressed_state else QColor(50, 50, 50)
            hover_bg = QColor(68, 68, 68)
        else:
            bg = QColor(50, 50, 50) if not self.pressed_state else QColor(42, 42, 42)
            hover_bg = QColor(58, 58, 58)

        color = hover_bg if self.underMouse() else bg
        p.setBrush(color)
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(QRectF(r), 5, 5)

        # Text
        fs = 18 if self.btn_type == "num" else 15
        p.setFont(QFont("Segoe UI", fs))
        p.setPen(QColor(255, 255, 255, 230))
        p.drawText(r, Qt.AlignCenter, self.text)

        p.end()

    def enterEvent(self, e):
        self.update()

    def leaveEvent(self, e):
        self.update()

    def mousePressEvent(self, event):
        self.pressed_state = True
        self.update()
        if self.callback:
            self.callback(self.text)

    def mouseReleaseEvent(self, event):
        self.pressed_state = False
        self.update()


class App(QWidget):
    def __init__(self, file_system=None, parent=None):
        super().__init__(parent)
        self.expr = ""
        self.display_val = "0"
        self.last_op = False
        self.last_eq = False

        self.setStyleSheet("background:#202020;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        self.mode_label = DisplayWidget("mode")
        self.mode_label.text = "Standard"
        self.mode_label.setFixedHeight(30)
        layout.addWidget(self.mode_label)

        self.expr_display = DisplayWidget("expr")
        self.expr_display.text = ""
        self.expr_display.setFixedHeight(22)
        layout.addWidget(self.expr_display)

        self.display = DisplayWidget("main")
        self.display.text = "0"
        self.display.setMinimumHeight(80)
        layout.addWidget(self.display)

        layout.addSpacing(4)

        grid = QGridLayout()
        grid.setSpacing(3)

        buttons = [
            ("%", "op"), ("CE", "fn"), ("C", "fn"), ("⌫", "fn"),
            ("¹/ₓ", "op"), ("x²", "op"), ("√", "op"), ("÷", "op"),
            ("7", "num"), ("8", "num"), ("9", "num"), ("×", "op"),
            ("4", "num"), ("5", "num"), ("6", "num"), ("−", "op"),
            ("1", "num"), ("2", "num"), ("3", "num"), ("+", "op"),
            ("±", "fn"), ("0", "num"), (".", "num"), ("=", "equals"),
        ]

        row, col = 0, 0
        for text, btype in buttons:
            btn = CalcButton(text, btype)
            btn.callback = self._on_btn
            grid.addWidget(btn, row, col)
            col += 1
            if col > 3:
                col = 0
                row += 1

        layout.addLayout(grid, 1)

    def _on_btn(self, text):
        if text in "0123456789":
            if self.last_eq:
                self.display_val = ""
                self.expr = ""
                self.last_eq = False
            if self.display_val == "0" or self.last_op:
                self.display_val = text
                self.last_op = False
            else:
                self.display_val += text

        elif text == ".":
            if "." not in self.display_val:
                self.display_val += "."

        elif text in ("+", "−", "×", "÷"):
            op = {"+": "+", "−": "-", "×": "*", "÷": "/"}[text]
            self.expr = self.display_val + " " + op + " "
            self.last_op = True
            self.last_eq = False
            self.expr_display.text = f"{self.display_val} {text}"
            self.expr_display.update()

        elif text == "=":
            if self.expr:
                full = self.expr + self.display_val
                self.expr_display.text = full.replace("*", "×").replace("/", "÷").replace("-", "−") + " ="
                self.expr_display.update()
                try:
                    r = eval(full)
                    self.display_val = str(int(r) if isinstance(r, float) and r == int(r) else r)
                except:
                    self.display_val = "Error"
                self.expr = ""
                self.last_eq = True

        elif text == "C":
            self.display_val = "0"
            self.expr = ""
            self.last_eq = False
            self.expr_display.text = ""
            self.expr_display.update()

        elif text == "CE":
            self.display_val = "0"

        elif text == "⌫":
            self.display_val = self.display_val[:-1] or "0"

        elif text == "±":
            if self.display_val.startswith("-"):
                self.display_val = self.display_val[1:]
            elif self.display_val != "0":
                self.display_val = "-" + self.display_val

        elif text == "x²":
            try:
                v = float(self.display_val)
                r = v ** 2
                self.expr_display.text = f"sqr({self.display_val})"
                self.expr_display.update()
                self.display_val = str(int(r) if r == int(r) else r)
            except:
                self.display_val = "Error"

        elif text == "√":
            try:
                v = float(self.display_val)
                r = v ** 0.5
                self.expr_display.text = f"√({self.display_val})"
                self.expr_display.update()
                self.display_val = str(int(r) if r == int(r) else r)
            except:
                self.display_val = "Error"

        elif text == "¹/ₓ":
            try:
                v = float(self.display_val)
                r = 1 / v
                self.expr_display.text = f"1/({self.display_val})"
                self.expr_display.update()
                self.display_val = str(r)
            except:
                self.display_val = "Error"

        elif text == "%":
            try:
                self.display_val = str(float(self.display_val) / 100)
            except:
                self.display_val = "Error"

        self.display.text = self.display_val
        self.display.update()


class DisplayWidget(QWidget):
    def __init__(self, mode="main", parent=None):
        super().__init__(parent)
        self.mode = mode
        self.text = ""

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.TextAntialiasing)

        if self.mode == "mode":
            p.setFont(QFont("Segoe UI Semibold", 13))
            p.setPen(QColor(255, 255, 255, 220))
            p.drawText(QRect(10, 0, self.width(), self.height()), Qt.AlignVCenter, self.text)

        elif self.mode == "expr":
            p.setFont(QFont("Segoe UI", 11))
            p.setPen(QColor(255, 255, 255, 100))
            p.drawText(QRect(0, 0, self.width() - 12, self.height()), Qt.AlignVCenter | Qt.AlignRight, self.text)

        elif self.mode == "main":
            fs = 44 if len(self.text) <= 10 else max(20, 44 - (len(self.text) - 10) * 3)
            p.setFont(QFont("Segoe UI Semibold", fs))
            p.setPen(QColor(255, 255, 255))
            p.drawText(QRect(0, 0, self.width() - 12, self.height()), Qt.AlignVCenter | Qt.AlignRight, self.text)

        p.end()