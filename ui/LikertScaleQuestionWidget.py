# ui/LikertScaleQuestionWidget.py

from __future__ import annotations

from PySide6.QtCore import QElapsedTimer, QRect, Slot, Qt, Signal
from PySide6.QtGui import QPainter, QBrush
from PySide6.QtWidgets import QApplication

from ui.gaze_widget import GazeWidget


class LikertScaleQuestionWidget(GazeWidget):
    """
    Likert scale question widget with 5 vertically stacked options and a submit area.

    Layout
    ------
    - Left side (≈45% width): five options (opt0..opt4) stacked vertically.
    - Right side (≈55% width):
        - top (≈75% height): REST/question area (no activation)
        - bottom (≈25% height): SUBMIT area

    Interaction
    -----------
    activation_mode:
      - "blink": activation is triggered by holding a blink for at least `blink_threshold_ms`
      - "dwell": activation is triggered by dwelling in an area for `dwell_threshold_ms`
                (with an on-screen dwell progress bar after a grace period)

    Selection
    ---------
    - Single-select: `selected_index` is 0..4 or None.
    - Selecting an option sets `selected_index`.
    - SUBMIT emits the selected label (string). If nothing is selected, submit does nothing.

    Signals
    -------
    submitted(object):
        Emits the selected label (str) on submission.
    clicked(int, str):
        Emits a click index and a label for logging:
        - option activations emit the option label (e.g., "3")
        - submit emits "submit"

    Logging Fields (expected by MainWindow)
    --------------------------------------
    - log_toggles: counts selection changes
    - log_resets: always 0
    - log_backspaces: always 0
    - log_extra: configuration string (mode, thresholds, labels)
    """

    submitted = Signal(object)
    clicked = Signal(int, str)

    def __init__(
        self,
        question: str,
        parent=None,
        activation_mode: str = "blink",
        dwell_threshold_ms: int = 1200,
        blink_threshold_ms: int = 250,
        labels=None,
    ):
        """
        Initialize the Likert scale widget.

        Parameters
        ----------
        question : str
            Question text displayed in the right-side REST area.
        parent : QWidget, optional
            Parent Qt widget.
        activation_mode : str, default="blink"
            "blink" or "dwell".
        dwell_threshold_ms : int, default=1200
            Dwell duration (ms) required to activate an area in dwell mode.
        blink_threshold_ms : int, default=250
            Blink duration (ms) required to activate at the current gaze point in blink mode.
        labels : list[str] | None, optional
            Exactly five labels (strings). Defaults to ["1","2","3","4","5"].

        Notes
        -----
        - Option highlight colors are fixed from red→green and only used as backgrounds
          when an option is selected.
        """
        super().__init__(parent)

        self.blink_fired = False
        self.question = question
        self.activation_mode = activation_mode
        self.dwell_threshold_ms = int(dwell_threshold_ms)
        self.blink_threshold_ms = int(blink_threshold_ms)

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

        self.selected_index: int | None = None
        self.click_index: int = 0

        self.is_blinking = False
        self.blink_timer = QElapsedTimer()

        self.dwell_timer = QElapsedTimer()
        self.dwell_grace_ms = 700
        self.dwell_area: str | None = None
        self.dwell_progress: float = 0.0

        self.question_rect = QRect()
        self.submit_rect = QRect()
        self.option_rects: list[QRect] = [QRect() for _ in range(5)]

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
        """
        Receive a gaze sample and update dwell state (if enabled).

        Parameters
        ----------
        x : float
            Raw gaze x-coordinate (input space).
        y : float
            Raw gaze y-coordinate (input space).

        Returns
        -------
        None

        Notes
        -----
        - Always forwards gaze to `GazeWidget`.
        - In dwell mode, maps gaze to widget coordinates and updates dwell logic.
        """
        super().set_gaze(x, y)

        if self.activation_mode == "dwell":
            gx, gy = self.map_gaze_to_widget()
            if gx is not None and gy is not None:
                self.update_dwell(int(gx), int(gy))

    @Slot(bool)
    def set_blinking(self, blinking: bool):
        """
        Receive blink state updates and trigger activation in blink mode.

        Parameters
        ----------
        blinking : bool
            True while a blink is ongoing, False when eyes are open.

        Returns
        -------
        None

        Notes
        -----
        - Only active when `activation_mode == "blink"`.
        - A single activation is triggered once per blink when duration reaches
          `blink_threshold_ms`.
        """
        if self.activation_mode != "blink":
            return

        if blinking and not self.is_blinking:
            self.blink_timer.start()
            self.is_blinking = True
            self.blink_fired = False
            return

        if blinking and self.is_blinking:
            duration = self.blink_timer.elapsed()
            if duration >= self.blink_threshold_ms and not self.blink_fired:
                self.handle_activation_by_point()
                self.blink_fired = True
            return

        if (not blinking) and self.is_blinking:
            self.is_blinking = False
            self.blink_fired = False

    def set_selection(self, index: int):
        """
        Select one of the five Likert options.

        Parameters
        ----------
        index : int
            Option index in [0, 4].

        Returns
        -------
        None

        Notes
        -----
        - Increments `log_toggles` only when the selection changes.
        - Emits a beep and schedules a repaint.
        """
        if not (0 <= index < len(self.labels)):
            return

        if self.selected_index != index:
            self.log_toggles += 1

        self.selected_index = index
        QApplication.beep()
        self.update()

    def activate_submit(self):
        """
        Submit the currently selected option.

        Returns
        -------
        None

        Notes
        -----
        - If no option is selected, does nothing.
        - Emits `submitted` with the selected label (string) and beeps.
        """
        if self.selected_index is None:
            return

        QApplication.beep()
        value = self.labels[self.selected_index]
        self.submitted.emit(value)
        self.update()

    def area_for_point(self, x: int, y: int) -> str | None:
        """
        Determine which UI area contains a given point.

        Parameters
        ----------
        x : int
            X coordinate in widget space.
        y : int
            Y coordinate in widget space.

        Returns
        -------
        str | None
            One of:
              - "submit"
              - "rest"
              - "opt0".."opt4"
            or None if outside all regions.
        """
        if self.submit_rect.contains(x, y):
            return "submit"
        if self.question_rect.contains(x, y):
            return "rest"

        for i, rect in enumerate(self.option_rects):
            if rect.contains(x, y):
                return f"opt{i}"

        return None

    def handle_activation_for_area(self, area: str | None):
        """
        Handle an activation event for a given area identifier.

        Parameters
        ----------
        area : str | None
            Area id returned by `area_for_point`.

        Returns
        -------
        None

        Notes
        -----
        - "rest" and None are ignored.
        - Option areas emit the option label via `clicked` then set the selection.
        - "submit" emits "submit" via `clicked` then triggers submission.
        """
        if area is None or area == "rest":
            return

        if area.startswith("opt"):
            try:
                idx = int(area[3:])
            except ValueError:
                return
            if not (0 <= idx < len(self.labels)):
                return

            self.click_index += 1
            self.clicked.emit(self.click_index, str(self.labels[idx]))
            self.set_selection(idx)
            return

        if area == "submit":
            self.click_index += 1
            self.clicked.emit(self.click_index, "submit")
            self.activate_submit()

    def handle_activation_by_point(self):
        """
        Handle an activation at the current gaze point.

        Returns
        -------
        None

        Notes
        -----
        - Maps gaze to widget coordinates, resolves the area under gaze,
          then dispatches to `handle_activation_for_area`.
        """
        x, y = self.map_gaze_to_widget()
        if x is None or y is None:
            return
        area = self.area_for_point(int(x), int(y))
        self.handle_activation_for_area(area)

    def update_dwell(self, x: int, y: int):
        """
        Update dwell detection state given the current gaze position.

        Parameters
        ----------
        x : int
            Gaze x-coordinate in widget space.
        y : int
            Gaze y-coordinate in widget space.

        Returns
        -------
        None

        Notes
        -----
        - Dwell is ignored for None/"rest".
        - When entering a new actionable area, dwell timer restarts.
        - After a grace period, `dwell_progress` fills linearly up to 1.0.
        - When `dwell_threshold_ms` is reached, triggers activation and resets progress.
        """
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

        self.dwell_progress = max(0.0, min(1.0, (elapsed - self.dwell_grace_ms) / effective))

        if elapsed >= self.dwell_threshold_ms:
            self.handle_activation_for_area(area)
            self.dwell_timer.start()
            self.dwell_progress = 0.0

        self.update()

    def draw_dwell_bar(self, painter: QPainter, rect: QRect, area_name: str):
        """
        Draw a dwell progress bar along the bottom edge of an area rectangle.

        Parameters
        ----------
        painter : QPainter
            Active painter used for drawing.
        rect : QRect
            The rectangle of the area.
        area_name : str
            The dwell area identifier to match against `self.dwell_area`.

        Returns
        -------
        None

        Notes
        -----
        - Only draws in dwell mode and only for the currently active dwell area.
        - The bar width is proportional to `dwell_progress`.
        """
        if self.activation_mode != "dwell":
            return
        if self.dwell_area != area_name:
            return
        if self.dwell_progress <= 0.0:
            return

        bar_height = max(4, rect.height() // 15)
        bar_width = int(rect.width() * self.dwell_progress)
        bar_rect = QRect(rect.left(), rect.bottom() - bar_height + 1, bar_width, bar_height)

        painter.setBrush(QBrush(Qt.white))
        painter.setPen(Qt.NoPen)
        painter.drawRect(bar_rect)

    def paintEvent(self, event):
        """
        Paint the widget UI.

        Parameters
        ----------
        event : QPaintEvent
            Qt paint event (required signature; unused).

        Returns
        -------
        None

        Notes
        -----
        - Computes all region rectangles from the current widget size.
        - Draws the question on the right and options on the left.
        - Highlights the selected option with a colored background.
        - Draws dwell bars in dwell mode.
        - Draws the gaze point as a red dot.
        """
        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.black)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setPen(Qt.white)

        w, h = self.width(), self.height()

        options_w = int(w * 0.45)
        right_w = w - options_w

        question_h = int(h * 0.75)
        submit_h = h - question_h

        self.question_rect = QRect(options_w, 0, right_w, question_h)
        self.submit_rect = QRect(options_w, question_h, right_w, submit_h)

        opt_h = h // 5
        for i in range(5):
            y = i * opt_h
            height = h - y if i == 4 else opt_h
            self.option_rects[i] = QRect(0, y, options_w, height)

        font = painter.font()
        font.setPointSize(max(10, int(h * 0.035)))
        painter.setFont(font)

        painter.drawRect(self.question_rect)
        question_inner = self.question_rect.adjusted(15, 15, -15, -15)
        painter.drawText(question_inner, Qt.AlignCenter | Qt.TextWordWrap, self.question)

        painter.drawRect(self.submit_rect)
        painter.drawText(self.submit_rect, Qt.AlignCenter, "SUBMIT")
        self.draw_dwell_bar(painter, self.submit_rect, "submit")

        font.setPointSize(max(9, int(h * 0.03)))
        painter.setFont(font)

        for i, rect in enumerate(self.option_rects):
            label = self.labels[i]

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

        gx, gy = self.map_gaze_to_widget()
        if gx is not None and gy is not None:
            painter.setBrush(QBrush(Qt.red))
            painter.setPen(Qt.NoPen)
            r = self.point_radius
            painter.drawEllipse(int(gx) - r, int(gy) - r, 2 * r, 2 * r)
