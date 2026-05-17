from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel

class App(QWidget):
    def __init__(self, file_system=None, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Hello from My App!"))