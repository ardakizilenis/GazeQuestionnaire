# ui/YesNoQuestionWidget.py

from __future__ import annotations

from PySide6.QtCore import QElapsedTimer, QRect, Slot, Qt, Signal
from PySide6.QtGui import QPainter, QBrush
from PySide6.QtWidgets import QApplication

from ui.gaze_widget import GazeWidget


class YesNoQuestionWidget(GazeWidget):
    """
    Yes/No question widget with two answer regions and a submit region.

    Interaction Modes
    -----------------
    activation_mode:
      - "blink": activate by holding a blink for at least `blink_threshold_ms`
      - "dwell": activate by dwelling inside an area for `dwell_threshold_ms`

    Regions
    -------
    - YES: left half (top area)
    - NO: right half (top area)
    - REST: centered question box (ignored for activation)
    - SUBMIT: bottom band (full width)

    Signals
    -------
    submitted(object):
        Emits the selected answer string ("yes" or "no") on submission.
    clicked(int, str):
        Emits a click index and an area identifier ("yes", "no", "submit")
        for logging/analytics.

    Logging Fields (expected by MainWindow)
    --------------------------------------
    - log_toggles: number of selection changes between yes/no
    - log_resets: always 0 (no resets here)
    - log_backspaces: always 0 (no backspaces here)
    - log_extra: configuration string
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
    ):
        """
        Initialize the widget.

        Parameters
        ----------
        question : str
            The question text displayed in the center box.
        parent : QWidget, optional
            Parent Qt widget.
        activation_mode : str, default="blink"
            "blink" or "dwell".
        dwell_threshold_ms : int, default=1200
            Dwell duration (ms) required to activate an area in dwell mode.
        blink_threshold_ms : int, default=250
            Blink duration (ms) required to activate at the current gaze point in blink mode.

        Notes
        -----
        - Selection is stored in `self.selection` as "yes", "no", or None.
        - In dwell mode, a grace period is applied before progress starts filling.
        """
        super().__init__(parent)

        self.question = question
        self.activation_mode = activation_mode
        self.dwell_threshold_ms = int(dwell_threshold_ms)
        self.blink_threshold_ms = int(blink_threshold_ms)

        self.selection: str | None = None
        self.click_index: int = 0

        self.is_blinking = False
        self.blink_fired = False
        self.blink_timer = QElapsedTimer()

        self.dwell_grace_ms = 700
        self.dwell_timer = QElapsedTimer()
        self.dwell_area: str | None = None
        self.dwell_progress: float = 0.0

        self.yes_rect = QRect()
        self.no_rect = QRect()
        self.submit_rect = QRect()
        self.question_rect = QRect()

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
        - Always forwards the gaze to the base `GazeWidget`.
        - In dwell mode, maps gaze to widget coordinates and updates dwell progress.
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
        - A blink triggers activation once it lasts at least `blink_threshold_ms`.
        - Uses `blink_fired` to avoid repeated activations during the same blink.
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

    def set_selection(self, sel: str):
        """
        Set the current selection to "yes" or "no".

        Parameters
        ----------
        sel : str
            Selection string; must be "yes" or "no".

        Returns
        -------
        None

        Notes
        -----
        - Increments `log_toggles` only when the selection changes.
        - Emits a beep and triggers repaint.
        """
        if sel not in ("yes", "no"):
            return

        if self.selection != sel:
            self.log_toggles += 1

        self.selection = sel
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
        - If no selection is made, does nothing.
        - Emits `submitted` with "yes" or "no" and beeps.
        """
        if self.selection is None:
            return

        QApplication.beep()
        self.submitted.emit(self.selection)
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
            One of: "rest", "yes", "no", "submit", or None if outside all areas.
        """
        if self.question_rect.contains(x, y):
            return "rest"
        if self.yes_rect.contains(x, y):
            return "yes"
        if self.no_rect.contains(x, y):
            return "no"
        if self.submit_rect.contains(x, y):
            return "submit"
        return None

    def handle_activation_for_area(self, area: str | None):
        """
        Handle an activation event for a specific area.

        Parameters
        ----------
        area : str | None
            Must be one of "yes", "no", "submit". Other values are ignored.

        Returns
        -------
        None

        Notes
        -----
        - Emits `clicked` for valid areas.
        - "yes"/"no" update selection, "submit" emits `submitted`.
        """
        if area not in ("yes", "no", "submit"):
            return

        self.click_index += 1
        self.clicked.emit(self.click_index, area)

        if area == "yes":
            self.set_selection("yes")
        elif area == "no":
            self.set_selection("no")
        else:
            self.activate_submit()

    def handle_activation_by_point(self):
        """
        Handle an activation at the current gaze point.

        Returns
        -------
        None

        Notes
        -----
        - Maps gaze to widget coordinates.
        - Resolves the area under gaze and dispatches to `handle_activation_for_area`.
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
        - Dwell is ignored in "rest" area and outside all areas.
        - If the dwell area changes, progress resets and timer restarts.
        - A grace period (`dwell_grace_ms`) is applied before progress fills.
        - On reaching `dwell_threshold_ms`, triggers activation and restarts the timer.
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
        Draw a dwell progress bar at the bottom of a given rectangle.

        Parameters
        ----------
        painter : QPainter
            Active painter used for drawing.
        rect : QRect
            Target rectangle where the progress bar is drawn.
        area_name : str
            Area identifier for which to draw the bar ("yes", "no", "submit").

        Returns
        -------
        None

        Notes
        -----
        - Only draws in dwell mode, and only for the currently active dwell area.
        - Bar width is proportional to `dwell_progress`.
        """
        if self.activation_mode != "dwell":
            return
        if self.dwell_area != area_name:
            return
        if self.dwell_progress <= 0.0:
            return

        bar_height = max(4, rect.height() // 12)
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
        - Splits the widget into a top region (YES/NO + question box) and a bottom SUBMIT region.
        - Draws selection highlighting for YES/NO areas.
        - Renders dwell progress bars in dwell mode.
        - Draws the current gaze point as a red dot.
        """
        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.black)
        painter.setRenderHint(QPainter.Antialiasing, True)

        w = self.width()
        h = self.height()

        submit_h = int(h * 0.20)
        top_h = h - submit_h

        self.yes_rect = QRect(0, 0, w // 2, top_h)
        self.no_rect = QRect(w // 2, 0, w - w // 2, top_h)

        square_side = int(top_h * 0.4)
        if square_side < 80:
            square_side = 80
        qx = (w - square_side) // 2
        qy = (top_h - square_side) // 2
        self.question_rect = QRect(qx, qy, square_side, square_side)

        self.submit_rect = QRect(0, top_h, w, submit_h)

        font = painter.font()
        font.setPointSize(15)
        painter.setFont(font)

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

        self.draw_dwell_bar(painter, self.yes_rect, "yes")
        self.draw_dwell_bar(painter, self.no_rect, "no")

        painter.setBrush(Qt.black)
        painter.setPen(Qt.white)
        painter.drawRect(self.question_rect)
        painter.drawText(
            self.question_rect.adjusted(10, 10, -10, -10),
            Qt.AlignCenter | Qt.TextWordWrap,
            self.question,
        )

        painter.setBrush(Qt.NoBrush)
        painter.setPen(Qt.white)
        painter.drawRect(self.submit_rect)
        painter.drawText(self.submit_rect, Qt.AlignCenter, "SUBMIT")
        self.draw_dwell_bar(painter, self.submit_rect, "submit")

        gx, gy = self.map_gaze_to_widget()
        if gx is not None and gy is not None:
            painter.setBrush(QBrush(Qt.red))
            painter.setPen(Qt.NoPen)
            r = self.point_radius
            painter.drawEllipse(int(gx) - r, int(gy) - r, 2 * r, 2 * r)
