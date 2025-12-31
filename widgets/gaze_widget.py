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
    bg0 = QColor("#020202")
    bg1 = QColor("#020202")

    neon_cyan   = QColor("#00FF9C")
    neon_pink   = QColor("#00FF9C")
    neon_violet = QColor("#00FF9C")

    text = QColor("#00FF9C")
    text_dim = QColor("#007F4E")

    bar_track  = QColor("#001A10")
    bar_border = QColor("#00FF9C")

    gaze = QColor("#FF5555")

    panel = QColor("#020202")
    panel_border = QColor("#00FF9C")

    submit = QColor("#00FF9C")
    reset  = QColor("#FF5555")

    option_accent = QColor("#00FF9C")
    orbit = QColor("#004D30")
    guide = QColor("#004D30")

    selected  = QColor("#00FF9C")
    highlight = QColor("#66FFCC")
    disabled  = QColor("#004D30")

    dot = QColor("#00FF9C")
    backspace = QColor("#FF5555")
    back = QColor("#00FF9C")
    yes = QColor("#00FF9C")
    no  = QColor("#FF5555")

class ClinicalTheme:
    bg0 = QColor("#F1F5F9")
    bg1 = QColor("#E2E8F0")

    neon_cyan   = QColor("#0EA5E9")
    neon_pink   = QColor("#EC4899")
    neon_violet = QColor("#6366F1")

    text = QColor("#020617")
    text_dim = QColor("#475569")

    bar_track  = QColor("#CBD5E1")
    bar_border = QColor("#94A3B8")

    gaze = QColor("#B91C1C")

    panel = QColor("#FFFFFF")
    panel_border = QColor("#94A3B8")

    submit = QColor("#0EA5E9")
    reset  = QColor("#EC4899")

    option_accent = QColor("#0EA5E9")
    orbit = QColor("#64748B")
    guide = QColor("#475569")

    selected  = QColor("#15803D")
    highlight = QColor("#0EA5E9")
    disabled  = QColor("#94A3B8")

    dot = QColor("#020617")
    backspace = QColor("#B91C1C")
    back = QColor("#6366F1")
    yes = QColor("#15803D")
    no  = QColor("#B91C1C")

class OledDarkTheme:
    bg0 = QColor("#000000")
    bg1 = QColor("#000000")

    neon_cyan   = QColor("#00E5FF")
    neon_pink   = QColor("#FF4081")
    neon_violet = QColor("#7C4DFF")

    text = QColor("#EDEDED")
    text_dim = QColor("#9E9E9E")

    bar_track  = QColor("#121212")
    bar_border = QColor("#2A2A2A")

    gaze = QColor("#FF5252")

    panel = QColor("#000000")
    panel_border = QColor("#1F1F1F")

    submit = QColor("#00E5FF")
    reset  = QColor("#FF4081")

    option_accent = QColor("#00E5FF")
    orbit = QColor("#2A2A2A")
    guide = QColor("#1F1F1F")

    selected  = QColor("#69F0AE")
    highlight = QColor("#82B1FF")
    disabled  = QColor("#424242")

    dot = QColor("#EDEDED")
    backspace = QColor("#FF5252")
    back = QColor("#7C4DFF")
    yes = QColor("#69F0AE")
    no  = QColor("#FF5252")