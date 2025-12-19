# ui/LikertScaleQuestionWidget.py

from PySide6.QtCore import QElapsedTimer, QRect, Slot, Qt, Signal
from PySide6.QtGui import QPainter, QBrush
from PySide6.QtWidgets import QApplication

from ui.gaze_widget import GazeWidget


class LikertScaleQuestionWidget(GazeWidget):
    """
    Likert-Scale with 5 Options.

    Layout:
      - Left Half of the Screen: 5 Options vertically ordered (opt0..opt4)
      - Right Half:
          top  : Question (75%)
          bottom : SUBMIT-Area (25%)

    Activation:
      - activation_mode = "blink"
      - activation_mode = "dwell"

    Labels: List of 5 Labels (["gar nicht", "wenig", "neutral", ...])

    Logging:
      - log_toggles      : counts and loggs the toggles
      - log_resets       : 0 (not available here)
      - log_backspaces   : 0 (not available here)
      - log_extra        : Extra Information (Mode, Thresholds, Labels)
    """

    submitted = Signal(object)  # returns the submitted label as Signal

    def __init__(
        self,
        question: str,
        parent=None,
        activation_mode: str = "blink",
        dwell_threshold_ms: int = 1200,
        blink_threshold_ms: int = 150,
        labels=None
    ):
        super().__init__(parent)

        self.blink_fired = False
        self.question = question
        self.activation_mode = activation_mode
        self.dwell_threshold_ms = dwell_threshold_ms
        self.blink_threshold_ms = blink_threshold_ms

        # Labels
        if labels is None:
            self.labels = ["1", "2", "3", "4", "5"]
        else:
            assert len(labels) == 5, "LikertScaleQuestionWidget requires exactly 5 labels."
            self.labels = [str(l) for l in labels]


        self.colors = [
            Qt.darkRed,
            Qt.red,
            Qt.gray,
            Qt.darkGreen,
            Qt.green,
        ]

        # currently chosen Index (0..4) or None
        self.selected_index: int | None = None

        # Blink-Detection
        self.is_blinking = False
        self.blink_timer = QElapsedTimer()

        # Dwell-Detection
        self.dwell_timer = QElapsedTimer()
        self.dwell_grace_ms = 700
        self.dwell_area: str | None = None
        self.dwell_progress: float = 0.0

        # Layout-Areas
        self.question_rect = QRect()
        self.submit_rect = QRect()
        self.option_rects: list[QRect] = [QRect() for _ in range(5)]

        # Logging
        self.log_toggles = 0
        self.log_resets = 0
        self.log_backspaces = 0
        self.log_extra = (
            f"likert;"
            f"mode={self.activation_mode};"
            f"dwell_ms={self.dwell_threshold_ms};"
            f"blink_ms={self.blink_threshold_ms};"
            f"labels={self.labels}"
        )

    @Slot(float, float)
    def set_gaze(self, x: float, y: float):
        super().set_gaze(x, y)

        if self.activation_mode == "dwell":
            gx, gy = self.map_gaze_to_widget()
            if gx is not None:
                self.update_dwell(int(gx), int(gy))

    @Slot(bool)
    def set_blinking(self, blinking: bool):
        if self.activation_mode != "blink":
            return

        # Blink START
        if blinking and not self.is_blinking:
            self.blink_timer.start()
            self.is_blinking = True
            self.blink_fired = False

        elif blinking and self.is_blinking:
            duration = self.blink_timer.elapsed()
            print(duration)
            if duration >= self.blink_threshold_ms and not self.blink_fired:
                self.handle_activation_by_point()
                self.blink_fired = True

        # Blink END
        elif not blinking and self.is_blinking:
            self.is_blinking = False
            self.blink_fired = False

    # selection logic
    def set_selection(self, index: int):
        if not (0 <= index < len(self.labels)):
            return

        if self.selected_index != index:
            self.log_toggles += 1

        self.selected_index = index
        QApplication.beep()
        self.update()

    # logic for submit
    def activate_submit(self):
        if self.selected_index is None:
            return

        QApplication.beep()
        value = self.labels[self.selected_index]
        self.submitted.emit(value)
        self.update()

    # returns the area, where the gaze currently is estimated
    def area_for_point(self, x: int, y: int) -> str | None:
        if self.submit_rect.contains(x, y):
            return "submit"
        if self.question_rect.contains(x, y):
            return "rest"

        for i, rect in enumerate(self.option_rects):
            if rect.contains(x, y):
                return f"opt{i}"

        return None

    # handles the activation logic for all areas
    def handle_activation_for_area(self, area: str | None):
        if area is None or area == "rest":
            return

        if area.startswith("opt"):
            try:
                idx = int(area[3:])
            except ValueError:
                return
            self.set_selection(idx)
        elif area == "submit":
            self.activate_submit()

    # handles the activation where the gaze point is
    def handle_activation_by_point(self):
        x, y = self.map_gaze_to_widget()
        if x is None:
            return
        area = self.area_for_point(int(x), int(y))
        self.handle_activation_for_area(area)

    # dwell-time logic
    def update_dwell(self, x: int, y: int):
        area = self.area_for_point(x, y)

        if area in (None, "rest"):
            self.dwell_area = None
            self.dwell_progress = 0.0
            return

        if self.dwell_area != area:
            self.dwell_area = area
            self.dwell_progress = 0.0
            self.dwell_timer.start()
            self.update()
            return

        elapsed = self.dwell_timer.elapsed()

        if elapsed < self.dwell_grace_ms:
            self.dwell_progress = 0.0
            self.update()
            return

        effective = self.dwell_threshold_ms - self.dwell_grace_ms
        if effective <= 1:
            effective = 1

        self.dwell_progress = max(
            0.0,
            min(1.0, (elapsed - self.dwell_grace_ms) / effective)
        )

        if elapsed >= self.dwell_threshold_ms:
            self.handle_activation_for_area(area)
            self.dwell_timer.start()
            self.dwell_progress = 0.0

        self.update()

    # drawing dwell-bar
    def draw_dwell_bar(self, painter: QPainter, rect: QRect, area_name: str):
        if self.activation_mode != "dwell":
            return
        if self.dwell_area != area_name:
            return
        if self.dwell_progress <= 0.0:
            return

        bar_height = max(4, rect.height() // 15)
        bar_width = int(rect.width() * self.dwell_progress)

        bar_rect = QRect(
            rect.left(),
            rect.bottom() - bar_height + 1,
            bar_width,
            bar_height,
        )
        painter.setBrush(QBrush(Qt.white))
        painter.setPen(Qt.NoPen)
        painter.drawRect(bar_rect)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.black)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setPen(Qt.white)

        w, h = self.width(), self.height()

        # Layout: Left -> Options (45%), Right -> Question+Submit (55%)
        options_w = int(w * 0.45)
        right_w = w - options_w

        # Right Side Layout: Top -> Question and Resting Area (75%), Botton -> Submit (25%)
        question_h = int(h * 0.75)
        submit_h = h - question_h

        self.question_rect = QRect(options_w, 0, right_w, question_h)
        self.submit_rect = QRect(options_w, question_h, right_w, submit_h)

        opt_h = h // 5
        for i in range(5):
            y = i * opt_h
            height = h - y if i == 4 else opt_h
            self.option_rects[i] = QRect(0, y, options_w, height)

        # Fonts
        font = painter.font()
        font.setPointSize(max(10, int(h * 0.035)))
        painter.setFont(font)

        # Question
        painter.drawRect(self.question_rect)
        question_inner = self.question_rect.adjusted(15, 15, -15, -15)
        painter.drawText(
            question_inner,
            Qt.AlignCenter | Qt.TextWordWrap,
            self.question,
        )

        # Submit
        painter.drawRect(self.submit_rect)
        painter.drawText(self.submit_rect, Qt.AlignCenter, "SUBMIT")
        self.draw_dwell_bar(painter, self.submit_rect, "submit")

        # Options
        font.setPointSize(max(9, int(h * 0.03)))
        painter.setFont(font)

        for i, rect in enumerate(self.option_rects):
            label = self.labels[i]

            # Background
            if self.selected_index == i:
                painter.setBrush(QBrush(self.colors[i]))
            else:
                painter.setBrush(Qt.NoBrush)

            painter.setPen(Qt.white)
            painter.drawRect(rect)
            painter.drawText(
                rect.adjusted(10, 5, -10, -5),
                Qt.AlignCenter | Qt.TextWordWrap,
                str(label),
            )

            self.draw_dwell_bar(painter, rect, f"opt{i}")

        # Gaze-Point
        gx, gy = self.map_gaze_to_widget()
        if gx is not None:
            painter.setBrush(QBrush(Qt.red))
            painter.setPen(Qt.NoPen)
            r = self.point_radius
            painter.drawEllipse(int(gx) - r, int(gy) - r, 2 * r, 2 * r)
