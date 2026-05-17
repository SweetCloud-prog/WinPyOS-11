import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from core.desktop import Desktop


def create_user_dirs():
    base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "user_data")
    for d in ["Desktop", "Documents", "Downloads", "Pictures", "Music", "Videos"]:
        os.makedirs(os.path.join(base, d), exist_ok=True)
    samples = {
        "Documents/readme.txt": "Welcome to WinPy11!\nThis is a sample document.",
        "Documents/notes.md": "# My Notes\n\n- Item 1\n- Item 2",
        "Desktop/hello.txt": "Hello World!",
        "Documents/script.py": 'print("Hello from WinPy11!")',
    }
    for p, c in samples.items():
        fp = os.path.join(base, p)
        if not os.path.exists(fp):
            with open(fp, "w", encoding="utf-8") as f:
                f.write(c)


def main():
    create_user_dirs()
    app = QApplication(sys.argv)
    app.setApplicationName("WinPy11")
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 9))

    desktop = Desktop()
    desktop.showFullScreen()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()