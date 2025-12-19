# ui/MultipleChoiceQuestionWidget.py

from PySide6.QtCore import QElapsedTimer, QRect, Slot, Qt, Signal
from PySide6.QtGui import QPainter, QBrush
from PySide6.QtWidgets import QApplication

from ui.gaze_widget import GazeWidget


class MultipleChoiceQuestionWidget(GazeWidget):
    """
    Multiple Choice with 4 Answers and RESET/REST/SUBMIT-Areas.

    Layout:
      - Top:    Option 0 (left), Option 1 (right)
      - Middle:   RESET (left) | REST + Question (Center) | SUBMIT (right)
      - Bottom:   Option 2 (left), Option 3 (right)

    Activation:
      - activation_mode = "blink"
      - activation_mode = "dwell"

    Labels:
      - labels are editable ["Text1","Text2","Text3","Text4"]
      - Default: ["A", "B", "C", "D"]

    Logging-Felder:
      - log_toggles:      counts answer toggles
      - log_resets:       counts answer resets
      - log_backspaces:   0 (not available here)
      - log_extra:        More Information (Mode, Thresholds)
    """

    submitted = Signal(object)  # Submits a signal with chosen labels

    def __init__(
        self,
        question: str,
        parent=None,
        activation_mode: str = "blink",
        dwell_threshold_ms: int = 1200,
        blink_threshold_ms: int = 150,
        labels=None,
    ):
        super().__init__(parent)

        self.blink_fired = False
        self.question = question
        self.activation_mode = activation_mode
        self.dwell_threshold_ms = dwell_threshold_ms
        self.blink_threshold_ms = blink_threshold_ms

        # Labels
        if labels is None:
            self.labels = ["A", "B", "C", "D"]
        else:
            assert len(labels) == 4, "MultipleChoiceQuestionWidget requires exactly 4 labels."
            self.labels = labels

        # Selection Set (Set of Indices 0..3)
        self.selected = set()

        # Blink-Recognition
        self.is_blinking = False
        self.blink_timer = QElapsedTimer()

        # Dwell-Recognition
        self.dwell_timer = QElapsedTimer()
        self.dwell_grace_ms = 700
        self.dwell_area: str | None = None
        self.dwell_progress: float = 0.0

        # Areas
        self.option_rects = [QRect() for _ in range(4)]
        self.rect_reset = QRect()
        self.rect_rest = QRect()
        self.rect_submit = QRect()

        # Logging
        self.log_toggles = 0
        self.log_resets = 0
        self.log_backspaces = 0
        self.log_extra = (
            f"mcq;"
            f"mode={self.activation_mode};"
            f"dwell_ms={self.dwell_threshold_ms};"
            f"blink_ms={self.blink_threshold_ms}"
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

    # Logic for toggling (adding to the set and logging it)
    def toggle_option(self, index: int):
        if not (0 <= index < 4):
            return

        if index in self.selected:
            self.selected.remove(index)
        else:
            self.selected.add(index) # <--

        # Logging: counting every toggle
        self.log_toggles += 1

        QApplication.beep()
        self.update()

    # logic for reset button
    def reset_selection(self):
        if self.selected:
            self.selected.clear() # <--
            self.log_resets += 1
            QApplication.beep()
            self.update()

    # logic for submit
    def activate_submit(self):
        QApplication.beep()
        result_labels = [self.labels[i] for i in sorted(self.selected)]
        self.submitted.emit(result_labels) # <--
        self.update()

    # Returns the area of the gaze-point as a string (None, if outside the Widget)
    def area_for_point(self, x: int, y: int) -> str | None:
        # Options
        for i, rect in enumerate(self.option_rects):
            if rect.contains(x, y):
                return f"opt{i}"
        # Middle
        if self.rect_reset.contains(x, y):
            return "reset"
        if self.rect_submit.contains(x, y):
            return "submit"
        if self.rect_rest.contains(x, y):
            return "rest"
        return None

    # Activation Logic for certain areas
    def handle_activation_for_area(self, area: str | None):
        if area is None or area == "rest": # <-- Nothing happens
            return

        if area.startswith("opt"):
            try:
                idx = int(area[3:])
            except ValueError:
                return
            self.toggle_option(idx)

        elif area == "reset":
            self.reset_selection()

        elif area == "submit":
            self.activate_submit()

    # Handles activation of where the gaze-point is
    def handle_activation_by_point(self):
        gx, gy = self.map_gaze_to_widget()
        if gx is None:
            return
        area = self.area_for_point(int(gx), int(gy))
        self.handle_activation_for_area(area)

    # Updates the status of the dwell
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

    # Drawing Dwell-Bar
    def _draw_dwell_bar(self, painter: QPainter, rect: QRect, area_name: str):
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

    # Drawing UI
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.black)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setPen(Qt.white)

        w = self.width()
        h = self.height()

        # Layout
        top_h = int(h * 0.35)
        mid_h = int(h * 0.25)
        bottom_h = h - top_h - mid_h

        # Options top (0,1) and bottom (2,3)
        self.option_rects[0] = QRect(0, 0, w // 2, top_h)
        self.option_rects[1] = QRect(w // 2, 0, w - w // 2, top_h)
        self.option_rects[2] = QRect(0, top_h + mid_h, w // 2, bottom_h)
        self.option_rects[3] = QRect(w // 2, top_h + mid_h, w - w // 2, bottom_h)

        # Middle: RESET | REST (Question) | SUBMIT
        mid_y = top_h
        third_w = w // 3

        self.rect_reset = QRect(0, mid_y, third_w, mid_h)
        self.rect_rest = QRect(third_w, mid_y, third_w, mid_h)
        self.rect_submit = QRect(2 * third_w, mid_y, w - 2 * third_w, mid_h)

        # Fonts
        font = painter.font()
        font.setPointSize(max(10, int(h * 0.03)))
        painter.setFont(font)

        # Options
        for i, rect in enumerate(self.option_rects):
            label = self.labels[i]

            if i in self.selected:
                painter.setBrush(QBrush(Qt.darkGray))
            else:
                painter.setBrush(Qt.NoBrush)

            painter.setPen(Qt.white)
            painter.drawRect(rect)
            painter.drawText(
                rect.adjusted(10, 10, -10, -10),
                Qt.AlignCenter | Qt.TextWordWrap,
                str(label)
            )

            self._draw_dwell_bar(painter, rect, f"opt{i}")

        # RESET
        painter.setBrush(Qt.NoBrush)
        painter.setPen(Qt.white)
        painter.drawRect(self.rect_reset)
        painter.drawText(self.rect_reset, Qt.AlignCenter | Qt.TextWordWrap, "RESET")
        self._draw_dwell_bar(painter, self.rect_reset, "reset")

        # REST/Question
        painter.setBrush(Qt.NoBrush)
        painter.setPen(Qt.white)
        painter.drawRect(self.rect_rest)
        question_rect = self.rect_rest.adjusted(10, 10, -10, -10)
        painter.drawText(question_rect, Qt.AlignCenter | Qt.TextWordWrap, self.question)

        # SUBMIT
        painter.setBrush(Qt.NoBrush)
        painter.setPen(Qt.white)
        painter.drawRect(self.rect_submit)
        painter.drawText(self.rect_submit, Qt.AlignCenter | Qt.TextWordWrap, "SUBMIT")
        self._draw_dwell_bar(painter, self.rect_submit, "submit")

        # Gaze Point
        gx, gy = self.map_gaze_to_widget()
        if gx is not None:
            painter.setBrush(QBrush(Qt.red))
            painter.setPen(Qt.NoPen)
            r = self.point_radius
            painter.drawEllipse(int(gx) - r, int(gy) - r, 2 * r, 2 * r)
