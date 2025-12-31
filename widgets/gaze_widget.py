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

    text: QColor = QColor("#EAF2FF")
    text_dim: QColor = QColor("#B7C7E6")

    panel: QColor = QColor("#0F1838")
    panel_border: QColor = QColor("#44507A")

    submit: QColor = QColor("#66F0FF")
    backspace: QColor = QColor("#FF6A6A")
    back: QColor = QColor("#9B7CFF")

    gaze: QColor = QColor("#FF3B3B")

