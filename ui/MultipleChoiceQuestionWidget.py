# ui/MultipleChoiceQuestionWidget.py

from __future__ import annotations

from PySide6.QtCore import QElapsedTimer, QRect, Slot, Qt, Signal
from PySide6.QtGui import QPainter, QBrush
from PySide6.QtWidgets import QApplication

from ui.gaze_widget import GazeWidget


class MultipleChoiceQuestionWidget(GazeWidget):
    """
    Multiple choice question widget with 4 options, plus RESET, REST, and SUBMIT areas.

    Layout
    ------
    - Top row:    Option 0 (left), Option 1 (right)
    - Middle row: RESET (left) | REST + question text (center) | SUBMIT (right)
    - Bottom row: Option 2 (left), Option 3 (right)

    Interaction
    -----------
    activation_mode:
      - "blink": activation is triggered by holding a blink for at least `blink_threshold_ms`
      - "dwell": activation is triggered by dwelling in an area for `dwell_threshold_ms`
                (with an on-screen dwell progress bar after a grace period)

    Selection
    ---------
    - Multi-select: selections are stored as a set of indices {0,1,2,3}
    - RESET clears the selection set
    - SUBMIT emits the currently selected labels in sorted index order

    Signals
    -------
    submitted(object):
        Emits List[str] of selected labels (e.g. ["A","C"]).
    clicked(int, str):
        Emits a click index and a label for logging:
        - option activations emit the option label (e.g., "A")
        - reset emits "reset"
        - submit emits "submit"

    Logging Fields (expected by MainWindow)
    --------------------------------------
    - log_toggles: counts every option toggle
    - log_resets: counts selection resets
    - log_backspaces: always 0 (not used)
    - log_extra: configuration string
    """

    submitted = Signal(object)
    clicked = Signal(int, str)

    def __init__(
        self,
        question: str,
        parent,
        gazepoint_blocked: bool,
        activation_mode: str,
        dwell_threshold_ms: int,
        blink_threshold_ms: int,
        labels=None,
    ):
        """
        Initialize the multiple choice widget.

        Parameters
        ----------
        question : str
            Question text displayed in the center REST area.
        parent : QWidget, optional
            Parent Qt widget.
        activation_mode : str, default="blink"
            "blink" or "dwell".
        dwell_threshold_ms : int, default=1200
            Dwell duration (ms) required to activate an area in dwell mode.
        blink_threshold_ms : int, default=250
            Blink duration (ms) required to activate at the current gaze point in blink mode.
        labels : list[str] | None, optional
            Exactly four option labels. Defaults to ["A","B","C","D"].

        Notes
        -----
        - The widget supports multi-select; toggling is per option.
        - Submit always emits a list of labels ordered by option index.
        """
        super().__init__(parent)

        self.gazePointBlocked = gazepoint_blocked
        self.blink_fired = False
        self.question = question
        self.activation_mode = activation_mode
        self.dwell_threshold_ms = dwell_threshold_ms
        self.blink_threshold_ms = blink_threshold_ms

        if labels is None:
            self.labels = ["A", "B", "C", "D"]
        else:
            assert len(labels) == 4, "MultipleChoiceQuestionWidget requires exactly 4 labels."
            self.labels = labels

        self.selected: set[int] = set()
        self.click_index: int = 0

        self.is_blinking = False
        self.blink_timer = QElapsedTimer()

        self.dwell_timer = QElapsedTimer()
        self.dwell_grace_ms = 700
        self.dwell_area: str | None = None
        self.dwell_progress: float = 0.0

        self.option_rects = [QRect() for _ in range(4)]
        self.rect_reset = QRect()
        self.rect_rest = QRect()
        self.rect_submit = QRect()

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

    def toggle_option(self, index: int):
        """
        Toggle an option on/off by index.

        Parameters
        ----------
        index : int
            Option index in [0, 3].

        Returns
        -------
        None

        Notes
        -----
        - Updates `selected` as a set of indices.
        - Increments `log_toggles` on every toggle attempt that passes validation.
        - Emits a beep and schedules a repaint.
        """
        if not (0 <= index < 4):
            return

        if index in self.selected:
            self.selected.remove(index)
        else:
            self.selected.add(index)

        self.log_toggles += 1
        QApplication.beep()
        self.update()

    def reset_selection(self):
        """
        Clear all selected options.

        Returns
        -------
        None

        Notes
        -----
        - Only counts as a reset if there was at least one selection.
        - Increments `log_resets` when clearing.
        """
        if not self.selected:
            return

        self.selected.clear()
        self.log_resets += 1
        QApplication.beep()
        self.update()

    def activate_submit(self):
        """
        Submit the current selection.

        Returns
        -------
        None

        Notes
        -----
        - Emits `submitted` with the selected labels in ascending index order.
        - Always beeps, even if the selection is empty.
        """
        QApplication.beep()
        result_labels = [self.labels[i] for i in sorted(self.selected)]
        self.submitted.emit(result_labels)
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
              - "opt0".."opt3"
              - "reset"
              - "rest"
              - "submit"
            or None if outside all regions.
        """
        for i, rect in enumerate(self.option_rects):
            if rect.contains(x, y):
                return f"opt{i}"
        if self.rect_reset.contains(x, y):
            return "reset"
        if self.rect_submit.contains(x, y):
            return "submit"
        if self.rect_rest.contains(x, y):
            return "rest"
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
        - Option areas emit the option label via `clicked` then toggle selection.
        - "reset" clears selection.
        - "submit" emits current selection labels.
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
            self.toggle_option(idx)
            return

        if area == "reset":
            self.click_index += 1
            self.clicked.emit(self.click_index, "reset")
            self.reset_selection()
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
        gx, gy = self.map_gaze_to_widget()
        if gx is None or gy is None:
            return
        area = self.area_for_point(int(gx), int(gy))
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

    def _draw_dwell_bar(self, painter: QPainter, rect: QRect, area_name: str):
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
        - Draws selected options with a filled background.
        - Draws dwell bars in dwell mode.
        - Draws the gaze point as a red dot.
        """
        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.black)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setPen(Qt.white)

        w = self.width()
        h = self.height()

        top_h = int(h * 0.35)
        mid_h = int(h * 0.25)
        bottom_h = h - top_h - mid_h

        self.option_rects[0] = QRect(0, 0, w // 2, top_h)
        self.option_rects[1] = QRect(w // 2, 0, w - w // 2, top_h)
        self.option_rects[2] = QRect(0, top_h + mid_h, w // 2, bottom_h)
        self.option_rects[3] = QRect(w // 2, top_h + mid_h, w - w // 2, bottom_h)

        mid_y = top_h
        third_w = w // 3
        self.rect_reset = QRect(0, mid_y, third_w, mid_h)
        self.rect_rest = QRect(third_w, mid_y, third_w, mid_h)
        self.rect_submit = QRect(2 * third_w, mid_y, w - 2 * third_w, mid_h)

        font = painter.font()
        font.setPointSize(max(10, int(h * 0.03)))
        painter.setFont(font)

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
                str(label),
            )

            self._draw_dwell_bar(painter, rect, f"opt{i}")

        painter.setBrush(Qt.NoBrush)
        painter.setPen(Qt.white)
        painter.drawRect(self.rect_reset)
        painter.drawText(self.rect_reset, Qt.AlignCenter | Qt.TextWordWrap, "RESET")
        self._draw_dwell_bar(painter, self.rect_reset, "reset")

        painter.setBrush(Qt.NoBrush)
        painter.setPen(Qt.white)
        painter.drawRect(self.rect_rest)
        question_rect = self.rect_rest.adjusted(10, 10, -10, -10)
        painter.drawText(question_rect, Qt.AlignCenter | Qt.TextWordWrap, self.question)

        painter.setBrush(Qt.NoBrush)
        painter.setPen(Qt.white)
        painter.drawRect(self.rect_submit)
        painter.drawText(self.rect_submit, Qt.AlignCenter | Qt.TextWordWrap, "SUBMIT")
        self._draw_dwell_bar(painter, self.rect_submit, "submit")

        if not self.gazePointBlocked:
            gx, gy = self.map_gaze_to_widget()
            if gx is not None and gy is not None:
                painter.setBrush(QBrush(Qt.red))
                painter.setPen(Qt.NoPen)
                r = self.point_radius
                painter.drawEllipse(int(gx) - r, int(gy) - r, 2 * r, 2 * r)
