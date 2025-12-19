# ui/InfoWidget.py

from PySide6.QtCore import QElapsedTimer, QTimer, Qt, Signal
from PySide6.QtGui import QPainter, QBrush
from ui.gaze_widget import GazeWidget


class InfoWidget(GazeWidget):
    """
    Simple Info-Page with:
      - Text
      - Progressbar at the bottom
      - visible Gaze-Point
    """
    submitted = Signal(object)

    def __init__(self, text: str, duration_sec: int, parent=None):
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
        if self.done:
            return

        elapsed = self.timer.elapsed()
        if elapsed >= self.duration_ms:
            self.done = True
            self.update_timer.stop()
            self.submitted.emit(None)

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.black)

        w = self.width()
        h = self.height()

        font = painter.font()
        font.setPointSize(int(h * 0.05))  # 5% of the height
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(Qt.white)

        # Centered Text Area
        text_rect = self.rect().adjusted(
            int(w * 0.1),
            int(h * 0.1),
            -int(w * 0.1),
            -int(h * 0.3),
        )
        painter.drawText(
            text_rect,
            Qt.AlignCenter | Qt.TextWordWrap,
            self.text,
        )

        # Progressbar
        elapsed = self.timer.elapsed()
        progress = max(0.0, min(1.0, elapsed / self.duration_ms))

        bar_height = int(h * 0.05)
        bar_margin = int(w * 0.05)
        bar_y = h - bar_height - int(h * 0.05)

        # Progressbar-Frame
        painter.setPen(Qt.white)
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(
            bar_margin,
            bar_y,
            w - 2 * bar_margin,
            bar_height,
        )

        # Filling
        fill_width = int((w - 2 * bar_margin) * progress)
        painter.setBrush(QBrush(Qt.white))
        painter.drawRect(
            bar_margin,
            bar_y,
            fill_width,
            bar_height,
        )

        # Gaze-Point
        gx, gy = self.map_gaze_to_widget()
        if gx is not None:
            painter.setRenderHint(QPainter.Antialiasing, True)
            painter.setBrush(QBrush(Qt.red))
            painter.setPen(Qt.NoPen)
            r = self.point_radius
            painter.drawEllipse(int(gx) - r, int(gy) - r, 2 * r, 2 * r)
