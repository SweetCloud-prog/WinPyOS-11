"""
WinPy11 Video Player
Contrôles EN DESSOUS de la vidéo (pas overlay) pour compatibilité QVideoWidget.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QFileDialog, QSizePolicy, QLabel, QSlider
)
from PySide6.QtCore import Qt, Signal, QUrl, QRectF, QPointF, QSize, QRect, QTimer
from PySide6.QtGui import (
    QFont, QColor, QPainter, QPen, QPixmap, QPainterPath, QIcon
)

from core.icons import get_icon, get_pixmap

_HAS_MEDIA = False
try:
    from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
    from PySide6.QtMultimediaWidgets import QVideoWidget
    _HAS_MEDIA = True
except ImportError:
    pass

VIDEO_EXTS = (".mp4", ".mov", ".avi", ".mkv", ".webm", ".wmv", ".flv")


def _fmt(ms):
    if ms <= 0:
        return "0:00"
    s = int(ms / 1000)
    if s >= 3600:
        return f"{s // 3600}:{(s % 3600) // 60:02d}:{s % 60:02d}"
    return f"{s // 60}:{s % 60:02d}"


def _play_icon(playing, size=24, fg=QColor(255, 255, 255)):
    px = QPixmap(size, size)
    px.fill(Qt.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    p.setBrush(fg)
    if playing:
        bw = int(size * 0.18)
        bh = int(size * 0.6)
        p.drawRoundedRect(int(size * 0.25), int(size * 0.2), bw, bh, 2, 2)
        p.drawRoundedRect(int(size * 0.57), int(size * 0.2), bw, bh, 2, 2)
    else:
        path = QPainterPath()
        path.moveTo(size * 0.3, size * 0.15)
        path.lineTo(size * 0.8, size * 0.5)
        path.lineTo(size * 0.3, size * 0.85)
        path.closeSubpath()
        p.drawPath(path)
    p.end()
    return QIcon(px)


class VideoSeekBar(QWidget):
    """Seekbar custom pour la vidéo."""
    seeked = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(28)
        self.setCursor(Qt.PointingHandCursor)
        self.duration = 0
        self.position = 0
        self._hover = False
        self._dragging = False
        self.setMouseTracking(True)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        margin = 0
        bar_y = h // 2
        bar_h = 4 if not self._hover else 6

        # Track
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255, 25))
        p.drawRoundedRect(QRectF(margin, bar_y - bar_h / 2, w - 2 * margin, bar_h), bar_h / 2, bar_h / 2)

        # Progress
        ratio = self.position / max(self.duration, 1)
        pw = (w - 2 * margin) * ratio
        if pw > 0:
            p.setBrush(QColor(0, 120, 215))
            p.drawRoundedRect(QRectF(margin, bar_y - bar_h / 2, pw, bar_h), bar_h / 2, bar_h / 2)

        # Handle
        if self._hover or self._dragging:
            p.setBrush(QColor(255, 255, 255))
            p.drawEllipse(QPointF(margin + pw, bar_y), 6, 6)

        p.end()

    def _pos_from_x(self, x):
        ratio = max(0, min(1, x / max(self.width(), 1)))
        return int(ratio * self.duration)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self.position = self._pos_from_x(event.position().x())
            self.seeked.emit(self.position)
            self.update()

    def mouseMoveEvent(self, event):
        self._hover = True
        if self._dragging:
            self.position = self._pos_from_x(event.position().x())
            self.seeked.emit(self.position)
        self.update()

    def mouseReleaseEvent(self, event):
        self._dragging = False

    def enterEvent(self, e):
        self._hover = True; self.update()

    def leaveEvent(self, e):
        self._hover = False; self.update()


class App(QWidget):
    def __init__(self, file_system=None, parent=None):
        super().__init__(parent)
        self.fs = file_system
        self._playlist = []
        self._index = -1

        lo = QVBoxLayout(self)
        lo.setContentsMargins(0, 0, 0, 0)
        lo.setSpacing(0)

        if not _HAS_MEDIA:
            fb = QLabel("Video Player requires:\npip install PySide6-Multimedia")
            fb.setFont(QFont("Segoe UI", 12))
            fb.setStyleSheet("color:rgba(255,255,255,100);background:black;")
            fb.setAlignment(Qt.AlignCenter)
            lo.addWidget(fb)
            return

        self.player = QMediaPlayer()
        self.audio_out = QAudioOutput()
        self.audio_out.setVolume(0.7)
        self.player.setAudioOutput(self.audio_out)

        # Video widget — prend tout l'espace
        self.video_w = QVideoWidget()
        self.video_w.setStyleSheet("background:black;")
        self.player.setVideoOutput(self.video_w)
        lo.addWidget(self.video_w, 1)

        # ═══ CONTROLS BAR — en dessous, pas overlay ═══
        ctrl_container = QWidget()
        ctrl_container.setFixedHeight(90)
        ctrl_container.setStyleSheet("background: #181818;")
        ctl = QVBoxLayout(ctrl_container)
        ctl.setContentsMargins(16, 8, 16, 8)
        ctl.setSpacing(6)

        # Seek bar + times
        seek_row = QHBoxLayout()
        seek_row.setSpacing(10)

        self.time_current = QLabel("0:00")
        self.time_current.setFont(QFont("Segoe UI", 8))
        self.time_current.setStyleSheet("color:rgba(255,255,255,120);")
        self.time_current.setFixedWidth(45)
        self.time_current.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        seek_row.addWidget(self.time_current)

        self.seek = VideoSeekBar()
        self.seek.seeked.connect(lambda pos: self.player.setPosition(pos))
        seek_row.addWidget(self.seek, 1)

        self.time_total = QLabel("0:00")
        self.time_total.setFont(QFont("Segoe UI", 8))
        self.time_total.setStyleSheet("color:rgba(255,255,255,120);")
        self.time_total.setFixedWidth(45)
        seek_row.addWidget(self.time_total)

        ctl.addLayout(seek_row)

        # Buttons row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(4)

        btn_css = """QPushButton{background:transparent;border:none;border-radius:18px;}
            QPushButton:hover{background:rgba(255,255,255,10);}"""

        # Title label (gauche)
        self.title_lbl = QLabel("")
        self.title_lbl.setFont(QFont("Segoe UI", 9))
        self.title_lbl.setStyleSheet("color:rgba(255,255,255,100);")
        self.title_lbl.setFixedWidth(200)
        btn_row.addWidget(self.title_lbl)

        btn_row.addStretch()

        # Open
        ob = QPushButton()
        ob.setFixedSize(36, 36); ob.setCursor(Qt.PointingHandCursor)
        ob.setIcon(get_icon("folder_open", 14, QColor(255, 255, 255, 160)))
        ob.setIconSize(QSize(14, 14)); ob.setStyleSheet(btn_css)
        ob.clicked.connect(self._open)
        btn_row.addWidget(ob)
        btn_row.addSpacing(8)

        # Prev
        pv = QPushButton()
        pv.setFixedSize(36, 36); pv.setCursor(Qt.PointingHandCursor)
        pv.setIcon(get_icon("arrow_left", 16, QColor(255, 255, 255, 180)))
        pv.setIconSize(QSize(16, 16)); pv.setStyleSheet(btn_css)
        pv.clicked.connect(self._prev)
        btn_row.addWidget(pv)

        # Play/Pause
        self.play_btn = QPushButton()
        self.play_btn.setFixedSize(44, 44)
        self.play_btn.setCursor(Qt.PointingHandCursor)
        self.play_btn.setIconSize(QSize(24, 24))
        self.play_btn.setIcon(_play_icon(False))
        self.play_btn.setStyleSheet("""
            QPushButton{background:rgba(255,255,255,15);border:none;border-radius:22px;}
            QPushButton:hover{background:rgba(255,255,255,25);}
        """)
        self.play_btn.clicked.connect(self._toggle)
        btn_row.addWidget(self.play_btn)

        # Next
        nx = QPushButton()
        nx.setFixedSize(36, 36); nx.setCursor(Qt.PointingHandCursor)
        nx.setIcon(get_icon("arrow_right", 16, QColor(255, 255, 255, 180)))
        nx.setIconSize(QSize(16, 16)); nx.setStyleSheet(btn_css)
        nx.clicked.connect(self._next)
        btn_row.addWidget(nx)

        btn_row.addStretch()

        # Volume
        vi = QPushButton()
        vi.setFixedSize(28, 28)
        vi.setIcon(get_icon("volume", 14, QColor(255, 255, 255, 120)))
        vi.setIconSize(QSize(14, 14))
        vi.setStyleSheet("QPushButton{background:transparent;border:none;}")
        btn_row.addWidget(vi)

        self.vol = QSlider(Qt.Horizontal)
        self.vol.setRange(0, 100); self.vol.setValue(70)
        self.vol.setFixedWidth(80)
        self.vol.setStyleSheet("""
            QSlider::groove:horizontal{height:3px;background:rgba(255,255,255,15);border-radius:1px;}
            QSlider::handle:horizontal{background:white;width:10px;height:10px;margin:-4px 0;border-radius:5px;}
            QSlider::sub-page:horizontal{background:rgba(0,120,215,200);border-radius:1px;}
        """)
        self.vol.valueChanged.connect(lambda v: self.audio_out.setVolume(v / 100))
        btn_row.addWidget(self.vol)

        ctl.addLayout(btn_row)

        lo.addWidget(ctrl_container)

        # Connexions player
        self.player.positionChanged.connect(self._on_pos)
        self.player.durationChanged.connect(self._on_dur)
        self.player.playbackStateChanged.connect(self._on_state)
        self.player.mediaStatusChanged.connect(self._on_media_status)

    def _toggle(self):
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()
        else:
            if self._index < 0 and self._playlist:
                self._index = 0; self._play()
            else:
                self.player.play()

    def _open(self):
        start = self.fs.get_base_path() if self.fs else os.path.expanduser("~")
        path, _ = QFileDialog.getOpenFileName(self, "Open Video", start,
            "Video (*.mp4 *.mov *.avi *.mkv *.webm *.wmv);;All (*)")
        if path:
            self.open_file(path)

    def open_file(self, path):
        folder = os.path.dirname(path)
        self._playlist = []
        try:
            for f in sorted(os.listdir(folder)):
                if os.path.splitext(f)[1].lower() in VIDEO_EXTS:
                    self._playlist.append(os.path.join(folder, f))
        except Exception:
            self._playlist = [path]
        self._index = self._playlist.index(path) if path in self._playlist else 0
        self._play()

    def _play(self):
        if not (0 <= self._index < len(self._playlist)):
            return
        path = self._playlist[self._index]
        self.title_lbl.setText(os.path.splitext(os.path.basename(path))[0])
        self.player.setSource(QUrl.fromLocalFile(path))
        self.player.play()

    def _prev(self):
        if self._index > 0: self._index -= 1; self._play()

    def _next(self):
        if self._index < len(self._playlist) - 1: self._index += 1; self._play()

    def _on_pos(self, pos):
        if not self.seek._dragging:
            self.seek.position = pos
            self.seek.update()
            self.time_current.setText(_fmt(pos))

    def _on_dur(self, dur):
        self.seek.duration = dur
        self.seek.update()
        self.time_total.setText(_fmt(dur))

    def _on_state(self, state):
        playing = (state == QMediaPlayer.PlayingState)
        self.play_btn.setIcon(_play_icon(playing))

    def _on_media_status(self, status):
        if status == QMediaPlayer.EndOfMedia:
            if self._index < len(self._playlist) - 1:
                self._next()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space:
            self._toggle()
        elif event.key() == Qt.Key_Left:
            self.player.setPosition(max(0, self.player.position() - 5000))
        elif event.key() == Qt.Key_Right:
            self.player.setPosition(min(self.player.duration(), self.player.position() + 5000))
        elif event.key() == Qt.Key_Up:
            v = min(1.0, self.audio_out.volume() + 0.05)
            self.audio_out.setVolume(v)
            self.vol.setValue(int(v * 100))
        elif event.key() == Qt.Key_Down:
            v = max(0.0, self.audio_out.volume() - 0.05)
            self.audio_out.setVolume(v)
            self.vol.setValue(int(v * 100))