# ui/InfoWidget.py

from __future__ import annotations

from PySide6.QtCore import QElapsedTimer, QTimer, Qt, Signal
from PySide6.QtGui import QPainter, QBrush

from ui.gaze_widget import GazeWidget


class InfoWidget(GazeWidget):
    """
    Simple information page that auto-advances after a fixed duration.

    Features
    --------
    - Displays a centered text message.
    - Shows a progress bar at the bottom that fills over time.
    - Draws the current gaze point as a red dot.

    Signals
    -------
    submitted(object):
        Emitted once the timer completes. Payload is always None.
    """

    submitted = Signal(object)

    def __init__(self, text: str, duration_sec: int, parent=None):
        """
        Initialize the info widget.

        Parameters
        ----------
        text : str
            Text content to display.
        duration_sec : int
            Duration in seconds before the widget emits `submitted` and finishes.
        parent : QWidget, optional
            Parent Qt widget.

        Notes
        -----
        - Internally converts `duration_sec` to milliseconds and clamps to at least 1 ms.
        - Uses a QTimer to repaint periodically for smooth progress updates.
        """
        super().__init__(parent)

        self.text = text
        self.duration_ms = max(1, int(duration_sec * 1000))

        self.timer = QElapsedTimer()
        self.timer.start()

        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.on_tick)
        self.update_timer.start(40)

        self.done = False

    def on_tick(self):
        """
        Periodic update handler for progress and completion.

        Returns
        -------
        None

        Notes
        -----
        - Stops itself and emits `submitted(None)` once the duration is reached.
        - Calls `update()` every tick to repaint the progress bar smoothly.
        """
        if self.done:
            return

        elapsed = self.timer.elapsed()
        if elapsed >= self.duration_ms:
            self.done = True
            self.update_timer.stop()
            self.submitted.emit(None)

        self.update()

    def paintEvent(self, event):
        """
        Paint the widget UI (text, progress bar, gaze point).

        Parameters
        ----------
        event : QPaintEvent
            Qt paint event (required signature; unused).

        Returns
        -------
        None

        Notes
        -----
        - The progress bar fills linearly with elapsed time.
        - The gaze point is drawn in widget coordinates using `map_gaze_to_widget()`.
        """
        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.black)

        w = self.width()
        h = self.height()

        font = painter.font()
        font.setPointSize(int(h * 0.05))
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(Qt.white)

        text_rect = self.rect().adjusted(
            int(w * 0.1),
            int(h * 0.1),
            -int(w * 0.1),
            -int(h * 0.3),
        )
        painter.drawText(text_rect, Qt.AlignCenter | Qt.TextWordWrap, self.text)

        elapsed = self.timer.elapsed()
        progress = max(0.0, min(1.0, elapsed / self.duration_ms))

        bar_height = int(h * 0.05)
        bar_margin = int(w * 0.05)
        bar_y = h - bar_height - int(h * 0.05)

        painter.setPen(Qt.white)
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(bar_margin, bar_y, w - 2 * bar_margin, bar_height)

        fill_width = int((w - 2 * bar_margin) * progress)
        painter.setBrush(QBrush(Qt.white))
        painter.drawRect(bar_margin, bar_y, fill_width, bar_height)

        gx, gy = self.map_gaze_to_widget()
        if gx is not None and gy is not None:
            painter.setRenderHint(QPainter.Antialiasing, True)
            painter.setBrush(QBrush(Qt.red))
            painter.setPen(Qt.NoPen)
            r = self.point_radius
            painter.drawEllipse(int(gx) - r, int(gy) - r, 2 * r, 2 * r)
