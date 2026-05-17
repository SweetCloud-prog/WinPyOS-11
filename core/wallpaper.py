"""
Système de fonds d'écran WinPy11.
Charge/sauvegarde depuis settings.json + fond par défaut embarqué.
"""
import os
import json
from PySide6.QtGui import QPixmap, QImage, QColor, QPainter, QPainterPath
from PySide6.QtCore import Qt, QRectF, QSize


BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
USER_DATA = os.path.join(BASE_PATH, "user_data")
SETTINGS_PATH = os.path.join(USER_DATA, "settings.json")

# ═══ FOND PAR DÉFAUT EMBARQUÉ ═══
DEFAULT_WALLPAPER_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080" viewBox="0 0 1920 1080">
    <rect width="1920" height="1080" fill="#011230"/>
    <defs>
        <radialGradient id="bloom1" cx="50%" cy="35%" r="45%">
            <stop offset="0%" stop-color="#0078d4" stop-opacity="0.4"/>
            <stop offset="40%" stop-color="#006fd0" stop-opacity="0.2"/>
            <stop offset="100%" stop-color="#000" stop-opacity="0"/>
        </radialGradient>
        <radialGradient id="bloom2" cx="58%" cy="38%" r="30%">
            <stop offset="0%" stop-color="#aa40b0" stop-opacity="0.3"/>
            <stop offset="50%" stop-color="#9a40a0" stop-opacity="0.15"/>
            <stop offset="100%" stop-color="#000" stop-opacity="0"/>
        </radialGradient>
        <radialGradient id="bloom3" cx="42%" cy="48%" r="25%">
            <stop offset="0%" stop-color="#7040c0" stop-opacity="0.25"/>
            <stop offset="60%" stop-color="#6040a0" stop-opacity="0.12"/>
            <stop offset="100%" stop-color="#000" stop-opacity="0"/>
        </radialGradient>
        <radialGradient id="bloom4" cx="52%" cy="60%" r="22%">
            <stop offset="0%" stop-color="#00c8e0" stop-opacity="0.18"/>
            <stop offset="100%" stop-color="#000" stop-opacity="0"/>
        </radialGradient>
    </defs>
    <use href="#bloom1" x="0%" y="0%" opacity="1"/>
    <use href="#bloom2" x="0%" y="0%" opacity="1"/>
    <use href="#bloom3" x="0%" y="0%" opacity="1"/>
    <use href="#bloom4" x="0%" y="0%" opacity="1"/>
    <g opacity="0.3">
        <ellipse cx="15%" cy="25%" rx="8%" ry="12%" fill="#0078d4"/>
        <ellipse cx="85%" cy="65%" rx="6%" ry="9%" fill="#aa40b0"/>
        <ellipse cx="35%" cy="42%" rx="7%" ry="11%" fill="#7040c0"/>
    </g>
</svg>'''


def load_settings():
    """Charge les paramètres."""
    try:
        if os.path.exists(SETTINGS_PATH):
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def save_settings(settings):
    """Sauvegarde les paramètres."""
    try:
        os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
        return True
    except Exception:
        return False


def get_wallpaper():
    """Retourne le QPixmap du fond d'écran actuel."""
    settings = load_settings()

    # Type priorité : image > solid > default
    wp_path = settings.get("wallpaper_path")
    wp_type = settings.get("wallpaper_type", "default")

    if wp_type == "image" and wp_path and os.path.exists(wp_path):
        pix = QPixmap(wp_path)
        if not pix.isNull():
            return pix.scaled(1920, 1080, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)

    # Solid color
    if wp_type == "solid":
        color_hex = settings.get("wallpaper_color", "#011230")
        color = QColor(color_hex)
        pix = QPixmap(1920, 1080)
        pix.fill(color)
        return pix

    # Default bloom SVG
    return _render_default_wallpaper()


def _render_default_wallpaper(size=(1920, 1080)):
    """Rend le fond d'écran par défaut depuis SVG."""
    pix = QPixmap(*size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)

    # Gradiant de base
    grad = QPainterPath()
    grad.addRect(QRectF(0, 0, *size))
    base_grad = QBrush(QColor("#011230"))
    p.fillPath(grad, base_grad)

    # 4 blooms
    blooms = [
        (0.50, 0.35, 0.42, "#0078d4"),
        (0.58, 0.38, 0.30, "#aa40b0"),
        (0.38, 0.48, 0.26, "#7040c0"),
        (0.46, 0.60, 0.20, "#00c8e0"),
    ]

    for cx_f, cy_f, rad_f, color_hex in blooms:
        cx = size[0] * cx_f
        cy = size[1] * cy_f
        rad = min(size[0], size[1]) * rad_f

        rg = QBrush(QColor(color_hex))
        p.setBrush(rg)
        p.setPen(Qt.NoPen)
        p.drawEllipse(QPointF(cx, cy), rad, rad)

    p.end()
    return pix


def set_wallpaper(path=None, color_hex=None):
    """Définit un nouveau fond d'écran."""
    settings = load_settings()
    if path:
        settings["wallpaper_type"] = "image"
        settings["wallpaper_path"] = path
    elif color_hex:
        settings["wallpaper_type"] = "solid"
        settings["wallpaper_color"] = color_hex
    else:
        settings["wallpaper_type"] = "default"
        settings.pop("wallpaper_path", None)
        settings.pop("wallpaper_color", None)
    save_settings(settings)
    return True