# widgets/gaze_widget.py

from __future__ import annotations

import math
from abc import abstractmethod

from PySide6.QtCore import Slot, QElapsedTimer, Qt, QPointF
from PySide6.QtGui import QGuiApplication, QPainter, QColor, QFont, QFontDatabase
from PySide6.QtWidgets import QWidget


class GazeWidget(QWidget):
    """
    Base widget that stores the latest gaze position and maps it into widget coordinates.

    This class is intended to be subclassed by gaze-interactive UI widgets. It provides:
    - storage for the most recent gaze sample (`gaze_x`, `gaze_y`) in screen space
    - screen geometry lookup for normalization
    - a helper to map the stored gaze sample into the current widget's coordinate system

    Notes
    -----
    - `gaze_x` and `gaze_y` are expected to be calibrated screen-space coordinates
      (e.g., pixel coordinates on the primary screen).
    - Mapping scales the gaze position by the ratio between the widget size and
      the primary screen size.
    """

    def __init__(self, parent=None):
        """
        Initialize the base gaze widget.

        Parameters
        ----------
        parent : QWidget, optional
            Parent Qt widget.

        Notes
        -----
        - Uses the primary screen geometry to establish the normalization reference.
        - `point_radius` is a convenience size used by subclasses when drawing a gaze marker.
        """
        super().__init__(parent)

        self.gaze_x: float | None = None
        self.gaze_y: float | None = None

        screen = QGuiApplication.primaryScreen()
        geom = screen.geometry()
        self.screen_width = geom.width()
        self.screen_height = geom.height()

        self._pulse_timer = QElapsedTimer()
        self._pulse_timer.start()

        self.point_radius = 10

    @Slot(float, float)
    def set_gaze(self, x: float, y: float):
        """
        Store the latest gaze sample and request a repaint.

        Parameters
        ----------
        x : float
            Gaze x-coordinate in screen space (calibrated).
        y : float
            Gaze y-coordinate in screen space (calibrated).

        Returns
        -------
        None

        Notes
        -----
        - Subclasses typically call `super().set_gaze(x, y)` before applying their
          own decision logic.
        - Calls `update()` to trigger a Qt repaint.
        """
        self.gaze_x = x
        self.gaze_y = y
        self.update()

    def map_gaze_to_widget(self) -> tuple[int | None, int | None]:
        """
        Map the stored screen-space gaze coordinates into widget coordinates.

        Returns
        -------
        tuple[int | None, int | None]
            (x, y) gaze position in widget coordinates, or (None, None) if no gaze
            sample is available.

        Notes
        -----
        - Mapping is proportional:
            draw_x = (gaze_x / screen_width)  * widget_width
            draw_y = (gaze_y / screen_height) * widget_height
        - The returned coordinates are integers suitable for drawing.
        """
        if self.gaze_x is None or self.gaze_y is None:
            return None, None

        draw_x = (self.gaze_x / self.screen_width) * self.width()
        draw_y = (self.gaze_y / self.screen_height) * self.height()

        return int(draw_x), int(draw_y)

    def _pulse(self) -> float:
        t = self._pulse_timer.elapsed() / 1000.0
        return 0.5 + 0.5 * math.sin(t * 2.0 * math.pi * 0.35)

    def _draw_gaze(self, p: QPainter):
        gx, gy = self.map_gaze_to_widget()
        if gx is None or gy is None:
            return

        p.save()
        p.setRenderHint(QPainter.Antialiasing, True)

        r = int(self.point_radius)
        pulse = self._pulse()

        # Minimal halo (cheap)
        halo = QColor(self.theme.gaze)
        halo.setAlpha(int(35 + 35 * pulse))
        p.setPen(Qt.NoPen)
        p.setBrush(halo)
        p.drawEllipse(QPointF(gx, gy), r * 2.0, r * 2.0)

        core = QColor(self.theme.gaze)
        core.setAlpha(235)
        p.setBrush(core)
        p.drawEllipse(QPointF(gx, gy), r, r)

        p.restore()

    @abstractmethod
    def paintEvent(self, event):
        pass

    def matchTheme(self, theme: str):
        # TODO: Themenerweiterung...
        match theme:
            case "neon":
                self.theme = NeonTheme()
            case "retro_terminal":
                self.theme = RetroTerminalTheme()
            case "clinical":
                self.theme = ClinicalTheme()
            case "oled_dark":
                self.theme = OledDarkTheme()
            case "sunset_synth":
                self.theme = SunsetSynthTheme()
            case "forest_mist":
                self.theme = ForestMistTheme()
            case "signal_contrast":
                self.theme = SignalContrastTheme()
            case _:
                self.theme = ClinicalTheme()

class NeonTheme:
    bg0: QColor = QColor("#070A12")
    bg1: QColor = QColor("#0B1330")
    neon_cyan: QColor = QColor("#66F0FF")
    neon_pink: QColor = QColor("#FF4FD8")
    neon_violet: QColor = QColor("#9B7CFF")
    text_dim: QColor = QColor("#B7C7E6")
    text: QColor = QColor("#EAF2FF")
    bar_track: QColor = QColor("#1B2546")
    bar_border: QColor = QColor("#4B5B86")
    gaze: QColor = QColor("#FF3B3B")
    panel: QColor = QColor("#0F1838")
    panel_border: QColor = QColor("#44507A")
    submit: QColor = QColor("#66F0FF")
    reset: QColor = QColor("#FF6A6A")
    option_accent: QColor = QColor("#9B7CFF")
    orbit: QColor = QColor("#6F7A9E")
    guide: QColor = QColor("#6F7A9E")
    selected: QColor = QColor("#39FF9A")
    highlight: QColor = QColor("#EAF2FF")
    disabled: QColor = QColor("#7C859E")
    dot: QColor = QColor("#EAF2FF")
    backspace: QColor = QColor("#FF6A6A")
    back: QColor = QColor("#9B7CFF")
    yes: QColor = QColor("#39FF9A")
    no: QColor = QColor("#FF5A5A")

class RetroTerminalTheme:
    bg0: QColor = QColor("#020402")
    bg1: QColor = QColor("#020402")
    neon_cyan: QColor = QColor("#7CFF6B")
    neon_pink: QColor = QColor("#FFD166")
    neon_violet: QColor = QColor("#6AFF55")
    text_dim: QColor = QColor("#6BD65E")
    text: QColor = QColor("#9CFF8A")
    bar_track: QColor = QColor("#041006")
    bar_border: QColor = QColor("#2F6B3A")
    gaze: QColor = QColor("#FFB000")
    panel: QColor = QColor("#020402")
    panel_border: QColor = QColor("#2F6B3A")
    submit: QColor = QColor("#7CFF6B")
    reset: QColor = QColor("#FFB000")
    option_accent: QColor = QColor("#6AFF55")
    orbit: QColor = QColor("#4FAF68")
    guide: QColor = QColor("#4FAF68")
    selected: QColor = QColor("#3CFF9E")
    highlight: QColor = QColor("#9CFF8A")
    disabled: QColor = QColor("#3E6B48")
    dot: QColor = QColor("#9CFF8A")
    backspace: QColor = QColor("#FFB000")
    back: QColor = QColor("#6AFF55")
    yes: QColor = QColor("#3CFF9E")
    no: QColor = QColor("#FFB000")


class ClinicalTheme:
    bg0: QColor = QColor("#F6F8FB")
    bg1: QColor = QColor("#FFFFFF")
    neon_cyan: QColor = QColor("#2563EB")
    neon_pink: QColor = QColor("#BE185D")
    neon_violet: QColor = QColor("#7C3AED")
    text_dim: QColor = QColor("#475569")
    text: QColor = QColor("#1E293B")
    bar_track: QColor = QColor("#E2E8F0")
    bar_border: QColor = QColor("#CBD5E1")
    gaze: QColor = QColor("#DC2626")
    panel: QColor = QColor("#FFFFFF")
    panel_border: QColor = QColor("#CBD5E1")
    submit: QColor = QColor("#2563EB")
    reset: QColor = QColor("#DC2626")
    option_accent: QColor = QColor("#2563EB")
    orbit: QColor = QColor("#64748B")
    guide: QColor = QColor("#64748B")
    selected: QColor = QColor("#059669")
    highlight: QColor = QColor("#0F172A")
    disabled: QColor = QColor("#94A3B8")
    dot: QColor = QColor("#334155")
    backspace: QColor = QColor("#DC2626")
    back: QColor = QColor("#2563EB")
    yes: QColor = QColor("#059669")
    no: QColor = QColor("#DC2626")


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
