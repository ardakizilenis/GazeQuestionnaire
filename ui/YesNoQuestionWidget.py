# ui/YesNoQuestionWidget.py
from PySide6.QtCore import QElapsedTimer, QRect, Slot, Qt, Signal
from PySide6.QtGui import QPainter, QBrush, QFont
from PySide6.QtWidgets import QApplication

from ui.gaze_widget import GazeWidget


class YesNoQuestionWidget(GazeWidget):
    """
    Yes/No-Question with two Answer-Areas and one Submit-Area.

    activation_mode:
      - "blink"
      - "dwell"

    Logging:
      - log_toggles:      toggles between yes and no
      - log_submits:      submitted? marking with 1
      - log_resets:       0 (no resets here)
      - log_backspaces:   0 (no backspaces here)
      - log_extra:        more information
    """

    submitted = Signal(object) # sends a string signal "yes" or "no"
    clicked = Signal(int, str)

    def __init__(
        self,
        question: str,
        parent=None,
        activation_mode: str = "blink",
        dwell_threshold_ms: int = 1200,
        blink_threshold_ms: int = 250,
    ):
        super().__init__(parent)

        self.question = question
        self.activation_mode = activation_mode
        self.dwell_threshold_ms = dwell_threshold_ms
        self.blink_threshold_ms = blink_threshold_ms
        self.selection: str | None = None
        self.click_index: int = 0

        # Blink-Recognition
        self.is_blinking = False
        self.blink_fired = False
        self.blink_timer = QElapsedTimer()

        # Dwell-Recognition
        self.dwell_grace_ms = 700
        self.dwell_timer = QElapsedTimer()
        self.dwell_area: str | None = None
        self.dwell_progress: float = 0.0

        # Areas
        self.yes_rect = QRect()
        self.no_rect = QRect()
        self.submit_rect = QRect()
        self.question_rect = QRect()

        # Logging
        self.log_toggles = 0
        self.log_resets = 0
        self.log_backspaces = 0
        self.log_extra = (
            f"yesno;"
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


    # selection logic
    def set_selection(self, sel: str):
        if sel not in ("yes", "no"):
            return

        # Logging toggle
        if self.selection != sel:
            self.log_toggles += 1

        self.selection = sel
        QApplication.beep()
        self.update()

    # activation logic
    def activate_submit(self):
        if self.selection is None:
            return

        QApplication.beep()
        self.submitted.emit(self.selection)
        self.update()

    # returns the area of the gaze point
    def area_for_point(self, x: int, y: int) -> str | None:
        if self.question_rect.contains(x, y):
            return "rest"
        if self.yes_rect.contains(x, y):
            return "yes"
        if self.no_rect.contains(x, y):
            return "no"
        if self.submit_rect.contains(x, y):
            return "submit"
        return None

    # activates the right function for the area
    def handle_activation_for_area(self, area: str | None):
        if area not in ("yes", "no", "submit"):
            return

        self.click_index += 1
        self.clicked.emit(self.click_index, area)

        if area == "yes":
            self.set_selection("yes")
        elif area == "no":
            self.set_selection("no")
        elif area == "submit":
            self.activate_submit()

    # defines the coordinates at the time of blink
    def handle_activation_by_point(self):
        x, y = self.map_gaze_to_widget()
        if x is None:
            return
        area = self.area_for_point(int(x), int(y))
        self.handle_activation_for_area(area)

    # dwell-recognition based on current gaze-position
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

    def draw_dwell_bar(self, painter: QPainter, rect: QRect, area_name: str):
        if self.activation_mode != "dwell":
            return
        if self.dwell_area != area_name:
            return
        if self.dwell_progress <= 0.0:
            return

        bar_height = max(4, rect.height() // 12)
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

        w = self.width()
        h = self.height()

        submit_h = int(h * 0.20)
        top_h = h - submit_h

        # yes/no-area
        self.yes_rect = QRect(0, 0, w // 2, top_h)
        self.no_rect = QRect(w // 2, 0, w - w // 2, top_h)

        # resting area
        square_side = int(top_h * 0.4)
        if square_side < 80:
            square_side = 80
        qx = (w - square_side) // 2
        qy = (top_h - square_side) // 2
        self.question_rect = QRect(qx, qy, square_side, square_side)

        # submit-area
        self.submit_rect = QRect(0, top_h, w, submit_h)

        # font
        font = painter.font()
        font.setPointSize(15)
        painter.setFont(font)

        # yes/no-area painting
        painter.setPen(Qt.white)

        if self.selection == "yes":
            painter.setBrush(QBrush(Qt.darkGreen))
            painter.drawRect(self.yes_rect)
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(self.no_rect)
        elif self.selection == "no":
            painter.setBrush(QBrush(Qt.darkRed))
            painter.drawRect(self.no_rect)
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(self.yes_rect)
        else:
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(self.yes_rect)
            painter.drawRect(self.no_rect)

        painter.drawText(self.yes_rect, Qt.AlignCenter, "YES")
        painter.drawText(self.no_rect, Qt.AlignCenter, "NO")

        # Dwell-Bar
        self.draw_dwell_bar(painter, self.yes_rect, "yes")
        self.draw_dwell_bar(painter, self.no_rect, "no")

        # draw question-box
        painter.setBrush(Qt.black)
        painter.setPen(Qt.white)
        painter.drawRect(self.question_rect)
        painter.drawText(
            self.question_rect.adjusted(10, 10, -10, -10),
            Qt.AlignCenter | Qt.TextWordWrap,
            self.question,
        )

        # submit-area
        painter.setBrush(Qt.NoBrush)
        painter.setPen(Qt.white)
        painter.drawRect(self.submit_rect)
        painter.drawText(self.submit_rect, Qt.AlignCenter, "SUBMIT")
        self.draw_dwell_bar(painter, self.submit_rect, "submit")

        # Gaze-Point
        gx, gy = self.map_gaze_to_widget()
        if gx is not None:
            painter.setBrush(QBrush(Qt.red))
            painter.setPen(Qt.NoPen)
            r = self.point_radius
            painter.drawEllipse(int(gx) - r, int(gy) - r, 2 * r, 2 * r)
