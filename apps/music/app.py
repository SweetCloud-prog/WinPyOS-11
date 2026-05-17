"""WinPy11 Music Player — avec extraction pochette MP3"""
import os
import sys
import struct

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QFileDialog, QSizePolicy, QLabel, QSlider
)
from PySide6.QtCore import Qt, Signal, QUrl, QRectF, QPointF, QSize, QRect
from PySide6.QtGui import (
    QFont, QColor, QPainter, QPen, QPixmap, QPainterPath,
    QRadialGradient, QBrush, QIcon
)

from core.icons import get_icon

_HAS_MEDIA = False
try:
    from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
    _HAS_MEDIA = True
except ImportError:
    pass

AUDIO_EXTS = (".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac", ".wma")


def _fmt(ms):
    if ms <= 0:
        return "0:00"
    s = int(ms / 1000)
    return f"{s // 60}:{s % 60:02d}"


def _play_icon(playing, size=28, fg=QColor(20, 20, 20)):
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


# ═══════════════════════════════════════════════════════
#  EXTRACTION POCHETTE — 3 méthodes
# ═══════════════════════════════════════════════════════

def _extract_art_mutagen(path):
    """Méthode 1 : mutagen (si installé)."""
    try:
        import mutagen
        from mutagen.mp3 import MP3
        from mutagen.id3 import ID3

        audio = mutagen.File(path)
        if audio is None:
            return None

        # MP3 avec ID3
        if hasattr(audio, 'tags') and audio.tags:
            for key in audio.tags:
                tag = audio.tags[key]
                # APIC = Attached Picture
                if key.startswith('APIC') or (hasattr(tag, 'FrameID') and tag.FrameID == 'APIC'):
                    if hasattr(tag, 'data'):
                        px = QPixmap()
                        px.loadFromData(tag.data)
                        if not px.isNull():
                            return px

        # MP4/M4A
        if hasattr(audio, 'tags') and audio.tags:
            for key in ['covr', 'cover']:
                if key in audio.tags:
                    covers = audio.tags[key]
                    if covers and len(covers) > 0:
                        px = QPixmap()
                        px.loadFromData(bytes(covers[0]))
                        if not px.isNull():
                            return px

        # FLAC
        if hasattr(audio, 'pictures'):
            for pic in audio.pictures:
                px = QPixmap()
                px.loadFromData(pic.data)
                if not px.isNull():
                    return px

    except Exception:
        pass
    return None


def _extract_art_raw(path):
    """Méthode 2 : extraction brute des tags ID3 (sans dépendance)."""
    try:
        with open(path, 'rb') as f:
            header = f.read(10)
            if header[:3] != b'ID3':
                return None

            # Taille du tag ID3
            size_bytes = header[6:10]
            tag_size = (size_bytes[0] << 21) | (size_bytes[1] << 14) | (size_bytes[2] << 7) | size_bytes[3]

            data = f.read(tag_size)

            # Chercher le frame APIC
            pos = 0
            while pos < len(data) - 10:
                frame_id = data[pos:pos + 4]

                if frame_id == b'APIC':
                    frame_size = struct.unpack('>I', data[pos + 4:pos + 8])[0]
                    frame_data = data[pos + 10:pos + 10 + frame_size]

                    # Parser le frame APIC
                    # Skip encoding byte
                    idx = 1
                    # Skip MIME type (null-terminated)
                    while idx < len(frame_data) and frame_data[idx] != 0:
                        idx += 1
                    idx += 1  # skip null
                    # Skip picture type byte
                    idx += 1
                    # Skip description (null-terminated)
                    while idx < len(frame_data) and frame_data[idx] != 0:
                        idx += 1
                    idx += 1  # skip null

                    # Le reste c'est l'image
                    image_data = frame_data[idx:]
                    if len(image_data) > 100:  # au moins quelques octets
                        px = QPixmap()
                        px.loadFromData(image_data)
                        if not px.isNull():
                            return px

                # Avancer au frame suivant
                if pos + 8 <= len(data):
                    try:
                        fs = struct.unpack('>I', data[pos + 4:pos + 8])[0]
                        if fs <= 0 or fs > tag_size:
                            break
                        pos += 10 + fs
                    except Exception:
                        break
                else:
                    break

    except Exception:
        pass
    return None


def _find_cover_in_folder(path):
    """Méthode 3 : chercher une image cover dans le même dossier."""
    folder = os.path.dirname(path)
    candidates = [
        "cover.jpg", "cover.png", "Cover.jpg", "Cover.png",
        "folder.jpg", "folder.png", "Folder.jpg",
        "album.jpg", "album.png", "Album.jpg",
        "artwork.jpg", "artwork.png", "Artwork.jpg",
        "front.jpg", "front.png", "Front.jpg",
    ]
    for name in candidates:
        cp = os.path.join(folder, name)
        if os.path.exists(cp):
            px = QPixmap(cp)
            if not px.isNull():
                return px

    # Dernière chance : première image jpg/png du dossier
    try:
        for f in os.listdir(folder):
            ext = os.path.splitext(f)[1].lower()
            if ext in ('.jpg', '.jpeg', '.png'):
                fp = os.path.join(folder, f)
                px = QPixmap(fp)
                if not px.isNull() and px.width() > 100 and px.height() > 100:
                    # Probablement une pochette si carrée-ish
                    ratio = px.width() / max(px.height(), 1)
                    if 0.7 < ratio < 1.4:
                        return px
    except Exception:
        pass

    return None


def extract_album_art(path):
    """Essaie les 3 méthodes dans l'ordre."""
    # 1. Mutagen (meilleure qualité)
    art = _extract_art_mutagen(path)
    if art:
        return art

    # 2. Extraction brute ID3 (marche sans dépendance pour les MP3)
    if path.lower().endswith('.mp3'):
        art = _extract_art_raw(path)
        if art:
            return art

    # 3. Image dans le dossier
    art = _find_cover_in_folder(path)
    if art:
        return art

    return None


# ═══════════════════════════════════════════════════════
#  ALBUM ART WIDGET
# ═══════════════════════════════════════════════════════

class AlbumArt(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap = None
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_art(self, pixmap):
        self._pixmap = pixmap
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)

        w, h = self.width(), self.height()

        # Background
        bg = QRadialGradient(w / 2, h / 2, max(w, h) * 0.6)
        bg.setColorAt(0.0, QColor(38, 38, 42))
        bg.setColorAt(1.0, QColor(16, 16, 20))
        p.fillRect(self.rect(), QBrush(bg))

        art_size = min(w, h) - 80
        if art_size < 60:
            p.end()
            return

        ax = (w - art_size) / 2
        ay = (h - art_size) / 2 - 15

        if self._pixmap and not self._pixmap.isNull():
            # ═══ POCHETTE TROUVÉE ═══

            # Ombre
            p.setBrush(QColor(0, 0, 0, 60))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(QRectF(ax + 6, ay + 6, art_size, art_size), 14, 14)

            # Image avec coins arrondis
            clip = QPainterPath()
            clip.addRoundedRect(QRectF(ax, ay, art_size, art_size), 14, 14)
            p.setClipPath(clip)

            scaled = self._pixmap.scaled(
                int(art_size), int(art_size),
                Qt.KeepAspectRatioByExpanding,
                Qt.SmoothTransformation
            )
            sx = max(0, (scaled.width() - int(art_size)) // 2)
            sy = max(0, (scaled.height() - int(art_size)) // 2)
            p.drawPixmap(
                QRectF(ax, ay, art_size, art_size),
                scaled,
                QRectF(sx, sy, art_size, art_size)
            )
            p.setClipping(False)

            # Léger reflet en haut
            reflect = QPainterPath()
            reflect.addRoundedRect(QRectF(ax, ay, art_size, art_size * 0.4), 14, 14)
            p.setClipPath(reflect)
            rg = QRadialGradient(ax + art_size / 2, ay, art_size * 0.5)
            rg.setColorAt(0.0, QColor(255, 255, 255, 15))
            rg.setColorAt(1.0, QColor(255, 255, 255, 0))
            p.fillRect(QRectF(ax, ay, art_size, art_size * 0.4), QBrush(rg))
            p.setClipping(False)

        else:
            # ═══ PAS DE POCHETTE — placeholder ═══
            p.setBrush(QColor(48, 48, 55))
            p.setPen(QPen(QColor(255, 255, 255, 10), 1))
            p.drawRoundedRect(QRectF(ax, ay, art_size, art_size), 14, 14)

            # Note de musique
            cx = ax + art_size / 2
            cy = ay + art_size / 2
            ns = art_size * 0.32

            pw = max(2.5, ns * 0.07)
            note_color = QColor(255, 255, 255, 28)

            # Tige
            stem_x = cx + ns * 0.2
            p.setPen(QPen(note_color, pw))
            p.drawLine(
                QPointF(stem_x, cy - ns * 0.5),
                QPointF(stem_x, cy + ns * 0.3)
            )

            # Tête
            p.setPen(Qt.NoPen)
            p.setBrush(note_color)
            p.drawEllipse(QPointF(cx, cy + ns * 0.33), ns * 0.2, ns * 0.13)

            # Drapeau
            p.setPen(QPen(note_color, pw))
            p.setBrush(Qt.NoBrush)
            flag = QPainterPath()
            flag.moveTo(stem_x, cy - ns * 0.5)
            flag.cubicTo(
                stem_x + ns * 0.35, cy - ns * 0.4,
                stem_x + ns * 0.3, cy - ns * 0.15,
                stem_x, cy - ns * 0.05
            )
            p.drawPath(flag)

        p.end()


# ═══════════════════════════════════════════════════════
#  SEEK BAR
# ═══════════════════════════════════════════════════════

class SeekBar(QWidget):
    seeked = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(44)
        self.setCursor(Qt.PointingHandCursor)
        self.duration = 0
        self.position = 0
        self._hover = False
        self._dragging = False
        self.setMouseTracking(True)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)

        w, h = self.width(), self.height()
        margin = 20
        bar_y = 16
        bar_h = 4 if not self._hover else 6

        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255, 20))
        p.drawRoundedRect(
            QRectF(margin, bar_y - bar_h / 2, w - 2 * margin, bar_h),
            bar_h / 2, bar_h / 2
        )

        ratio = self.position / max(self.duration, 1)
        pw = (w - 2 * margin) * ratio
        if pw > 0:
            p.setBrush(QColor(255, 255, 255, 200))
            p.drawRoundedRect(
                QRectF(margin, bar_y - bar_h / 2, pw, bar_h),
                bar_h / 2, bar_h / 2
            )

        if self._hover or self._dragging:
            p.setBrush(QColor(255, 255, 255))
            p.drawEllipse(QPointF(margin + pw, bar_y), 6, 6)

        p.setFont(QFont("Segoe UI", 8))
        p.setPen(QColor(255, 255, 255, 100))
        p.drawText(QRect(margin, bar_y + 12, 60, 14), Qt.AlignLeft, _fmt(self.position))
        p.drawText(QRect(w - margin - 60, bar_y + 12, 60, 14), Qt.AlignRight, _fmt(self.duration))
        p.end()

    def _pos_from_x(self, x):
        margin = 20
        ratio = max(0, min(1, (x - margin) / max(self.width() - 2 * margin, 1)))
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


# ═══════════════════════════════════════════════════════
#  APP
# ═══════════════════════════════════════════════════════

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
            fb = QLabel("Music Player requires:\npip install PySide6-Multimedia")
            fb.setFont(QFont("Segoe UI", 12))
            fb.setStyleSheet("color:rgba(255,255,255,100);background:#1e1e1e;")
            fb.setAlignment(Qt.AlignCenter)
            lo.addWidget(fb)
            return

        self.player = QMediaPlayer()
        self.audio = QAudioOutput()
        self.audio.setVolume(0.7)
        self.player.setAudioOutput(self.audio)
        self.player.positionChanged.connect(self._on_pos)
        self.player.durationChanged.connect(self._on_dur)
        self.player.playbackStateChanged.connect(self._on_state)
        self.player.mediaStatusChanged.connect(self._on_media_status)

        # Album art
        self.art = AlbumArt()
        lo.addWidget(self.art, 1)

        # Title / Artist
        info = QWidget()
        info.setFixedHeight(56)
        il = QVBoxLayout(info)
        il.setContentsMargins(24, 4, 24, 4)
        il.setSpacing(2)

        self.title_lbl = QLabel("No track")
        self.title_lbl.setFont(QFont("Segoe UI Semibold", 14))
        self.title_lbl.setStyleSheet("color:white;")
        self.title_lbl.setAlignment(Qt.AlignCenter)
        il.addWidget(self.title_lbl)

        self.artist_lbl = QLabel("")
        self.artist_lbl.setFont(QFont("Segoe UI", 10))
        self.artist_lbl.setStyleSheet("color:rgba(255,255,255,70);")
        self.artist_lbl.setAlignment(Qt.AlignCenter)
        il.addWidget(self.artist_lbl)

        lo.addWidget(info)

        # Seek
        self.seek = SeekBar()
        self.seek.seeked.connect(lambda pos: self.player.setPosition(pos))
        lo.addWidget(self.seek)

        # Controls
        ctrl = QWidget()
        ctrl.setFixedHeight(70)
        cl = QHBoxLayout(ctrl)
        cl.setContentsMargins(0, 0, 0, 16)
        cl.setSpacing(0)
        cl.setAlignment(Qt.AlignCenter)

        btn_css = """QPushButton{background:transparent;border:none;border-radius:20px;}
            QPushButton:hover{background:rgba(255,255,255,10);}"""

        # Open
        ob = QPushButton()
        ob.setFixedSize(40, 40)
        ob.setCursor(Qt.PointingHandCursor)
        ob.setIcon(get_icon("folder_open", 16, QColor(255, 255, 255, 160)))
        ob.setIconSize(QSize(16, 16))
        ob.setStyleSheet(btn_css)
        ob.clicked.connect(self._open)
        cl.addWidget(ob)
        cl.addSpacing(24)

        # Prev
        pb = QPushButton()
        pb.setFixedSize(42, 42)
        pb.setCursor(Qt.PointingHandCursor)
        pb.setIcon(get_icon("arrow_left", 18, QColor(255, 255, 255, 200)))
        pb.setIconSize(QSize(18, 18))
        pb.setStyleSheet(btn_css)
        pb.clicked.connect(self._prev)
        cl.addWidget(pb)
        cl.addSpacing(8)

        # Play
        self.play_btn = QPushButton()
        self.play_btn.setFixedSize(56, 56)
        self.play_btn.setCursor(Qt.PointingHandCursor)
        self.play_btn.setIconSize(QSize(28, 28))
        self.play_btn.setIcon(_play_icon(False))
        self.play_btn.setStyleSheet("""
            QPushButton{background:rgba(255,255,255,220);border:none;border-radius:28px;}
            QPushButton:hover{background:white;}
        """)
        self.play_btn.clicked.connect(self._toggle)
        cl.addWidget(self.play_btn)
        cl.addSpacing(8)

        # Next
        nb = QPushButton()
        nb.setFixedSize(42, 42)
        nb.setCursor(Qt.PointingHandCursor)
        nb.setIcon(get_icon("arrow_right", 18, QColor(255, 255, 255, 200)))
        nb.setIconSize(QSize(18, 18))
        nb.setStyleSheet(btn_css)
        nb.clicked.connect(self._next)
        cl.addWidget(nb)
        cl.addSpacing(24)

        # Volume icon
        vi = QPushButton()
        vi.setFixedSize(28, 28)
        vi.setIcon(get_icon("volume", 14, QColor(255, 255, 255, 130)))
        vi.setIconSize(QSize(14, 14))
        vi.setStyleSheet("QPushButton{background:transparent;border:none;}")
        cl.addWidget(vi)

        # Volume slider
        self.vol = QSlider(Qt.Horizontal)
        self.vol.setRange(0, 100)
        self.vol.setValue(70)
        self.vol.setFixedWidth(90)
        self.vol.setStyleSheet("""
            QSlider::groove:horizontal{height:3px;background:rgba(255,255,255,15);border-radius:1px;}
            QSlider::handle:horizontal{background:white;width:12px;height:12px;margin:-5px 0;border-radius:6px;}
            QSlider::sub-page:horizontal{background:rgba(255,255,255,150);border-radius:1px;}
        """)
        self.vol.valueChanged.connect(lambda v: self.audio.setVolume(v / 100))
        cl.addWidget(self.vol)

        lo.addWidget(ctrl)

    def _toggle(self):
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()
        else:
            if self._index < 0 and self._playlist:
                self._index = 0
                self._play()
            else:
                self.player.play()

    def _open(self):
        start = self.fs.get_base_path() if self.fs else os.path.expanduser("~")
        path, _ = QFileDialog.getOpenFileName(
            self, "Open", start,
            "Audio (*.mp3 *.wav *.m4a *.ogg *.flac *.aac);;All (*)"
        )
        if path:
            self.open_file(path)

    def open_file(self, path):
        folder = os.path.dirname(path)
        self._playlist = []
        try:
            for f in sorted(os.listdir(folder)):
                if os.path.splitext(f)[1].lower() in AUDIO_EXTS:
                    self._playlist.append(os.path.join(folder, f))
        except Exception:
            self._playlist = [path]
        self._index = self._playlist.index(path) if path in self._playlist else 0
        self._play()

    def _play(self):
        if not (0 <= self._index < len(self._playlist)):
            return
        path = self._playlist[self._index]

        # Titre et artiste
        name = os.path.basename(path)
        self.title_lbl.setText(os.path.splitext(name)[0])
        self.artist_lbl.setText(os.path.basename(os.path.dirname(path)))

        # ═══ EXTRAIRE LA POCHETTE ═══
        art = extract_album_art(path)
        self.art.set_art(art)  # None si pas trouvée → affiche placeholder

        # Lire
        self.player.setSource(QUrl.fromLocalFile(path))
        self.player.play()

    def _prev(self):
        if self._index > 0:
            self._index -= 1
            self._play()

    def _next(self):
        if self._index < len(self._playlist) - 1:
            self._index += 1
            self._play()

    def _on_pos(self, pos):
        if not self.seek._dragging:
            self.seek.position = pos
            self.seek.update()

    def _on_dur(self, dur):
        self.seek.duration = dur
        self.seek.update()

    def _on_state(self, state):
        self.play_btn.setIcon(_play_icon(state == QMediaPlayer.PlayingState))

    def _on_media_status(self, status):
        if status == QMediaPlayer.EndOfMedia:
            if self._index < len(self._playlist) - 1:
                self._next()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space:
            self._toggle()
        elif event.key() == Qt.Key_Left:
            self._prev()
        elif event.key() == Qt.Key_Right:
            self._next()

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(24, 24, 26))
        p.end()