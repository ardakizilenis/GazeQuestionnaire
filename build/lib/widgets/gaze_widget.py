# widgets/gaze_widget.py
from __future__ import annotations

import math

from PySide6.QtCore import Slot, QElapsedTimer, Qt, QPointF
from PySide6.QtGui import QPainter, QColor
from PySide6.QtWidgets import QWidget
from screeninfo import get_monitors


# ----------------------------
# Screen helper
# ----------------------------

def get_screen_size():
    m = get_monitors()[0]
    return m.width, m.height


# ----------------------------
# Base theme
# ----------------------------

class BaseTheme:
    bg0: QColor
    bg1: QColor
    neon_cyan: QColor
    neon_pink: QColor
    neon_violet: QColor
    text_dim: QColor
    text: QColor
    bar_track: QColor
    bar_border: QColor
    gaze: QColor
    panel: QColor
    panel_border: QColor
    submit: QColor
    reset: QColor
    option_accent: QColor
    orbit: QColor
    guide: QColor
    selected: QColor
    highlight: QColor
    disabled: QColor
    dot: QColor
    backspace: QColor
    back: QColor
    yes: QColor
    no: QColor


# ----------------------------
# Themes (unchanged colors)
# ----------------------------

class NeonTheme(BaseTheme):
    bg0 = QColor("#070A12")
    bg1 = QColor("#0B1330")
    neon_cyan = QColor("#66F0FF")
    neon_pink = QColor("#FF4FD8")
    neon_violet = QColor("#9B7CFF")
    text_dim = QColor("#B7C7E6")
    text = QColor("#EAF2FF")
    bar_track = QColor("#1B2546")
    bar_border = QColor("#4B5B86")
    gaze = QColor("#FF3B3B")
    panel = QColor("#0F1838")
    panel_border = QColor("#44507A")
    submit = QColor("#66F0FF")
    reset = QColor("#FF6A6A")
    option_accent = QColor("#9B7CFF")
    orbit = QColor("#6F7A9E")
    guide = QColor("#6F7A9E")
    selected = QColor("#39FF9A")
    highlight = QColor("#EAF2FF")
    disabled = QColor("#7C859E")
    dot = QColor("#EAF2FF")
    backspace = QColor("#FF6A6A")
    back = QColor("#9B7CFF")
    yes = QColor("#39FF9A")
    no = QColor("#FF5A5A")


class RetroTerminalTheme(BaseTheme):
    bg0 = QColor("#020402")
    bg1 = QColor("#020402")
    neon_cyan = QColor("#7CFF6B")
    neon_pink = QColor("#FFD166")
    neon_violet = QColor("#6AFF55")
    text_dim = QColor("#6BD65E")
    text = QColor("#9CFF8A")
    bar_track = QColor("#041006")
    bar_border = QColor("#2F6B3A")
    gaze = QColor("#FFB000")
    panel = QColor("#020402")
    panel_border = QColor("#2F6B3A")
    submit = QColor("#7CFF6B")
    reset = QColor("#FFB000")
    option_accent = QColor("#6AFF55")
    orbit = QColor("#4FAF68")
    guide = QColor("#4FAF68")
    selected = QColor("#3CFF9E")
    highlight = QColor("#9CFF8A")
    disabled = QColor("#3E6B48")
    dot = QColor("#9CFF8A")
    backspace = QColor("#FFB000")
    back = QColor("#6AFF55")
    yes = QColor("#3CFF9E")
    no = QColor("#FFB000")


class ClinicalTheme(BaseTheme):
    bg0 = QColor("#F6F8FB")
    bg1 = QColor("#FFFFFF")
    neon_cyan = QColor("#2563EB")
    neon_pink = QColor("#BE185D")
    neon_violet = QColor("#7C3AED")
    text_dim = QColor("#475569")
    text = QColor("#1E293B")
    bar_track = QColor("#E2E8F0")
    bar_border = QColor("#CBD5E1")
    gaze = QColor("#DC2626")
    panel = QColor("#FFFFFF")
    panel_border = QColor("#CBD5E1")
    submit = QColor("#2563EB")
    reset = QColor("#DC2626")
    option_accent = QColor("#2563EB")
    orbit = QColor("#64748B")
    guide = QColor("#64748B")
    selected = QColor("#059669")
    highlight = QColor("#0F172A")
    disabled = QColor("#94A3B8")
    dot = QColor("#334155")
    backspace = QColor("#DC2626")
    back = QColor("#2563EB")
    yes = QColor("#059669")
    no = QColor("#DC2626")

class OledDarkTheme:
    bg0: QColor = QColor("#000000")
    bg1: QColor = QColor("#000000")
    neon_cyan: QColor = QColor("#FFFFFF")
    neon_pink: QColor = QColor("#FBCFE8")
    neon_violet: QColor = QColor("#E5E7EB")
    text_dim: QColor = QColor("#9CA3AF")
    text: QColor = QColor("#EDEDED")
    bar_track: QColor = QColor("#111111")
    bar_border: QColor = QColor("#2A2A2A")
    gaze: QColor = QColor("#FF4D4D")
    panel: QColor = QColor("#000000")
    panel_border: QColor = QColor("#2A2A2A")
    submit: QColor = QColor("#FFFFFF")
    reset: QColor = QColor("#FF4D4D")
    option_accent: QColor = QColor("#E5E7EB")
    orbit: QColor = QColor("#9CA3AF")
    guide: QColor = QColor("#9CA3AF")
    selected: QColor = QColor("#A7F3D0")
    highlight: QColor = QColor("#FFFFFF")
    disabled: QColor = QColor("#6B7280")
    dot: QColor = QColor("#EDEDED")
    backspace: QColor = QColor("#FF4D4D")
    back: QColor = QColor("#E5E7EB")
    yes: QColor = QColor("#A7F3D0")
    no: QColor = QColor("#FF6B6B")

class SunsetSynthTheme:
    bg0 = QColor("#1A1026")
    bg1 = QColor("#24143A")
    neon_cyan = QColor("#FF9F68")
    neon_pink = QColor("#FF5DA2")
    neon_violet = QColor("#B983FF")
    text_dim = QColor("#C7BFE6")
    text = QColor("#FFF1F8")
    bar_track = QColor("#33204D")
    bar_border = QColor("#6B4C9A")
    gaze = QColor("#FF6A6A")
    panel = QColor("#24143A")
    panel_border = QColor("#6B4C9A")
    submit = QColor("#FF9F68")
    reset = QColor("#FF6A6A")
    option_accent = QColor("#B983FF")
    orbit = QColor("#9F8ED6")
    guide = QColor("#9F8ED6")
    selected = QColor("#FFD166")
    highlight = QColor("#FFF1F8")
    disabled = QColor("#7A6F99")
    dot = QColor("#FFF1F8")
    backspace = QColor("#FF6A6A")
    back = QColor("#B983FF")
    yes = QColor("#FFD166")
    no = QColor("#FF6A6A")

class ForestMistTheme:
    bg0 = QColor("#0F1C17")
    bg1 = QColor("#142822")
    neon_cyan = QColor("#6EE7B7")
    neon_pink = QColor("#FCA5A5")
    neon_violet = QColor("#A7F3D0")
    text_dim = QColor("#9FBFB3")
    text = QColor("#ECFEF8")
    bar_track = QColor("#1F3A30")
    bar_border = QColor("#4C7C6C")
    gaze = QColor("#F87171")
    panel = QColor("#142822")
    panel_border = QColor("#4C7C6C")
    submit = QColor("#6EE7B7")
    reset = QColor("#F87171")
    option_accent = QColor("#34D399")
    orbit = QColor("#7DD3C7")
    guide = QColor("#7DD3C7")
    selected = QColor("#34D399")
    highlight = QColor("#ECFEF8")
    disabled = QColor("#5B7F73")
    dot = QColor("#ECFEF8")
    backspace = QColor("#F87171")
    back = QColor("#6EE7B7")
    yes = QColor("#34D399")
    no = QColor("#F87171")

class SignalContrastTheme:
    bg0 = QColor("#0B0B0B")
    bg1 = QColor("#111111")
    neon_cyan = QColor("#00E5FF")
    neon_pink = QColor("#FF1744")
    neon_violet = QColor("#7C4DFF")
    text_dim = QColor("#B0BEC5")
    text = QColor("#FFFFFF")
    bar_track = QColor("#1C1C1C")
    bar_border = QColor("#424242")
    gaze = QColor("#FF1744")
    panel = QColor("#111111")
    panel_border = QColor("#424242")
    submit = QColor("#00E5FF")
    reset = QColor("#FF1744")
    option_accent = QColor("#7C4DFF")
    orbit = QColor("#B0BEC5")
    guide = QColor("#B0BEC5")
    selected = QColor("#00E676")
    highlight = QColor("#FFFFFF")
    disabled = QColor("#757575")
    dot = QColor("#FFFFFF")
    backspace = QColor("#FF1744")
    back = QColor("#7C4DFF")
    yes = QColor("#00E676")
    no = QColor("#FF1744")

# ----------------------------
# GazeWidget
# ----------------------------

class GazeWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.gaze_x: float | None = None
        self.gaze_y: float | None = None

        self.screen_width, self.screen_height = get_screen_size()

        self._pulse_timer = QElapsedTimer()
        self._pulse_timer.start()

        self.point_radius = 10
        self.theme = ClinicalTheme()  # default

    @Slot(float, float)
    def set_gaze(self, x: float, y: float):
        self.gaze_x = x
        self.gaze_y = y
        self.update()

    def map_gaze_to_widget(self):
        if self.gaze_x is None or self.gaze_y is None:
            return None, None
        return (
            int((self.gaze_x / self.screen_width) * self.width()),
            int((self.gaze_y / self.screen_height) * self.height()),
        )

    def _pulse(self):
        t = self._pulse_timer.elapsed() / 1000.0
        return 0.5 + 0.5 * math.sin(t * 2.0 * math.pi * 0.35)

    def _draw_gaze(self, p: QPainter):
        gx, gy = self.map_gaze_to_widget()
        if gx is None or gy is None:
            return

        p.save()
        p.setRenderHint(QPainter.Antialiasing, True)

        r = self.point_radius
        pulse = self._pulse()

        halo = QColor(self.theme.gaze)
        halo.setAlpha(int(35 + 35 * pulse))
        p.setPen(Qt.NoPen)
        p.setBrush(halo)
        p.drawEllipse(QPointF(gx, gy), r * 2, r * 2)

        core = QColor(self.theme.gaze)
        core.setAlpha(235)
        p.setBrush(core)
        p.drawEllipse(QPointF(gx, gy), r, r)

        p.restore()

    def matchTheme(self, theme: str):
        THEMES = {
            "neon": NeonTheme,
            "retro_terminal": RetroTerminalTheme,
            "clinical": ClinicalTheme,
            "oled_dark": OledDarkTheme,
            "sunset_synth": SunsetSynthTheme,
            "forest_mist": ForestMistTheme,
            "signal_contrast": SignalContrastTheme,
        }
        self.theme = THEMES.get(theme, ClinicalTheme)()
