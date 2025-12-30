# ui/TextInputWidget.py

from __future__ import annotations

from PySide6.QtCore import QElapsedTimer, QRect, Slot, Qt, Signal
from PySide6.QtGui import QPainter, QBrush
from PySide6.QtWidgets import QApplication

from ui.gaze_widget import GazeWidget


class TextInputWidget(GazeWidget):
    """
    Eye-tracking text input widget using a 3x3 grid with two interaction modes.

    Modes
    -----
    groups:
        Select one of four letter groups using N/W/E/S cells.
        SW = BACKSPACE, SE = SUBMIT, center shows prompt + current text.
    letters:
        After selecting a group, choose a letter from 7 slots:
        ["NW", "NE", "W", "E", "SW", "S", "SE"] mapped onto the group's characters.
        N = BACK (return to groups mode).

    Activation Modes
    ----------------
    activation_mode:
      - "blink": a blink held for at least `blink_threshold_ms` triggers activation
      - "dwell": dwelling within a cell for `dwell_threshold_ms` triggers activation
                with an on-screen dwell progress bar (after a grace period)

    Signals
    -------
    submitted(object):
        Emits the final entered text (str) upon submit.
    clicked(int, str):
        Emits a click index and a label describing the activated action, used for logging.

    Logging Fields (expected by MainWindow)
    --------------------------------------
    - log_toggles: number of appended characters
    - log_resets: always 0 (no resets)
    - log_backspaces: number of backspaces
    - log_extra: configuration string
    """

    submitted = Signal(object)
    clicked = Signal(int, str)

    def __init__(
        self,
        parent,
        question: str,
        gazepoint_blocked: bool,
        activation_mode: str,
        dwell_threshold_ms: int,
        blink_threshold_ms: int
    ):
        """
        Initialize the 3x3 grid text input widget.

        Parameters
        ----------
        question : str
            Prompt text shown in the center cell.
        parent : QWidget, optional
            Parent Qt widget.
        activation_mode : str, default="dwell"
            "dwell" or "blink".
        dwell_threshold_ms : int, default=1200
            Dwell duration (ms) required to activate a cell in dwell mode.
        blink_threshold_ms : int, default=250
            Blink duration (ms) required to activate the cell under gaze in blink mode.

        Notes
        -----
        - The widget starts in "groups" mode.
        - Group definitions are fixed to four strings:
          "ABCDEFG", "HIJKLMN", "OPQRSTU", "VWXYZ " (space included).
        """
        super().__init__(parent)

        self.question = question
        self.gazePointBlocked = gazepoint_blocked
        self.activation_mode = activation_mode
        self.dwell_threshold_ms = int(dwell_threshold_ms)
        self.blink_threshold_ms = int(blink_threshold_ms)

        self.current_text: str = ""
        self.click_index: int = 0

        self.mode: str = "groups"
        self.current_group_index: int | None = None

        self.groups: list[str] = [
            "ABCDEFG",
            "HIJKLMN",
            "OPQRSTU",
            "VWXYZ ",
        ]

        self.is_blinking = False
        self.blink_fired = False
        self.blink_timer = QElapsedTimer()

        self.dwell_timer = QElapsedTimer()
        self.dwell_grace_ms = 700
        self.dwell_area: str | None = None
        self.dwell_progress: float = 0.0

        self.cells: dict[str, QRect] = {k: QRect() for k in ("NW", "N", "NE", "W", "C", "E", "SW", "S", "SE")}

        self.log_toggles = 0
        self.log_resets = 0
        self.log_backspaces = 0
        self.log_extra = (
            f"textgrid;"
            f"mode={self.activation_mode};"
            f"dwell_ms={self.dwell_threshold_ms};"
            f"blink_ms={self.blink_threshold_ms}"
        )

    def _emit_click(self, label: str) -> None:
        """
        Emit a click event for logging.

        Parameters
        ----------
        label : str
            Action label (e.g., "group:0(A-G)", "char:A", "backspace", "submit").

        Returns
        -------
        None
        """
        self.click_index += 1
        self.clicked.emit(self.click_index, label)

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
        - Always forwards gaze to the base `GazeWidget`.
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

    def append_char(self, ch: str) -> None:
        """
        Append a character to the current text.

        Parameters
        ----------
        ch : str
            Character to append (use " " for space).

        Returns
        -------
        None

        Notes
        -----
        - Increments `log_toggles`.
        - Emits a beep.
        """
        self.log_toggles += 1
        self.current_text += ch
        QApplication.beep()

    def backspace(self) -> None:
        """
        Remove the last character from the current text.

        Returns
        -------
        None

        Notes
        -----
        - Increments `log_backspaces` if a character is removed.
        - Emits a beep when deletion occurs.
        """
        if not self.current_text:
            return
        self.current_text = self.current_text[:-1]
        self.log_backspaces += 1
        QApplication.beep()

    def submit(self) -> None:
        """
        Submit the current text.

        Returns
        -------
        None

        Notes
        -----
        - Emits `submitted` with the full current text.
        - Emits a beep.
        """
        QApplication.beep()
        self.submitted.emit(self.current_text)

    def area_for_point(self, x: int, y: int) -> str | None:
        """
        Determine which grid cell contains a given point.

        Parameters
        ----------
        x : int
            X coordinate in widget space.
        y : int
            Y coordinate in widget space.

        Returns
        -------
        str | None
            One of "NW","N","NE","W","C","E","SW","S","SE", or None if outside all cells.
        """
        for key, rect in self.cells.items():
            if rect.contains(x, y):
                return key
        return None

    def handle_activation_by_point(self) -> None:
        """
        Trigger activation based on the current gaze point.

        Returns
        -------
        None

        Notes
        -----
        - Maps the current gaze to widget space and activates the cell under gaze.
        """
        gx, gy = self.map_gaze_to_widget()
        if gx is None or gy is None:
            return
        area = self.area_for_point(int(gx), int(gy))
        self.handle_activation(area)

    def handle_activation(self, area: str | None) -> None:
        """
        Dispatch an activation to the appropriate handler depending on current mode.

        Parameters
        ----------
        area : str | None
            Activated cell key.

        Returns
        -------
        None

        Notes
        -----
        - In "groups" mode, selects a letter group or triggers backspace/submit.
        - In "letters" mode, selects a letter or returns back to groups mode.
        """
        if area is None:
            return
        if self.mode == "groups":
            self.handle_groups_activation(area)
        else:
            self.handle_letters_activation(area)

    def handle_groups_activation(self, area: str) -> None:
        """
        Handle activation events while in "groups" mode.

        Parameters
        ----------
        area : str
            Activated cell key.

        Returns
        -------
        None

        Notes
        -----
        - N/W/E/S enter "letters" mode for group indices 0..3.
        - SW triggers backspace.
        - SE triggers submit.
        """
        if area == "N":
            self._emit_click("group:0(A-G)")
            self.current_group_index = 0
            self.mode = "letters"
            QApplication.beep()
        elif area == "W":
            self._emit_click("group:1(H-N)")
            self.current_group_index = 1
            self.mode = "letters"
            QApplication.beep()
        elif area == "E":
            self._emit_click("group:2(O-U)")
            self.current_group_index = 2
            self.mode = "letters"
            QApplication.beep()
        elif area == "S":
            self._emit_click("group:3(V-Z_)")
            self.current_group_index = 3
            self.mode = "letters"
            QApplication.beep()
        elif area == "SW":
            self._emit_click("backspace")
            self.backspace()
        elif area == "SE":
            self._emit_click("submit")
            self.submit()

        self.update()

    def handle_letters_activation(self, area: str) -> None:
        """
        Handle activation events while in "letters" mode.

        Parameters
        ----------
        area : str
            Activated cell key.

        Returns
        -------
        None

        Notes
        -----
        - N = BACK to groups mode.
        - Letter slots are: ["NW","NE","W","E","SW","S","SE"] mapped to the group's string.
        - After choosing a letter, returns to "groups" mode.
        """
        if self.current_group_index is None:
            self.mode = "groups"
            return

        letters = self.groups[self.current_group_index]

        if area == "N":
            self._emit_click("back")
            self.mode = "groups"
            self.current_group_index = None
            QApplication.beep()
            self.update()
            return

        slots = ["NW", "NE", "W", "E", "SW", "S", "SE"]
        if area in slots:
            idx = slots.index(area)
            if idx < len(letters):
                ch = letters[idx]
                char_to_add = " " if ch == " " else ch
                self._emit_click("char:SPACE" if char_to_add == " " else f"char:{char_to_add}")
                self.append_char(char_to_add)

        self.mode = "groups"
        self.current_group_index = None
        self.update()

    def update_dwell(self, x: int, y: int) -> None:
        """
        Update dwell detection state from the current gaze position.

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
        - If gaze moves to a new cell, the dwell timer restarts.
        - Progress stays at 0 during `dwell_grace_ms`, then linearly fills until
          `dwell_threshold_ms`.
        - When threshold is reached, triggers activation and resets progress.
        """
        area = self.area_for_point(x, y)

        if area is None:
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
            self.handle_activation(area)
            self.dwell_timer.start()
            self.dwell_progress = 0.0

        self.update()

    def draw_dwell_bar(self, painter: QPainter, area_key: str) -> None:
        """
        Draw the dwell progress bar for a cell.

        Parameters
        ----------
        painter : QPainter
            Active painter used for drawing.
        area_key : str
            Cell key for which to draw the bar.

        Returns
        -------
        None

        Notes
        -----
        - Only draws in dwell mode, and only for the currently active dwell cell.
        - Bar width is proportional to `dwell_progress`.
        """
        if self.activation_mode != "dwell":
            return
        if self.dwell_area != area_key:
            return
        if self.dwell_progress <= 0.0:
            return

        rect = self.cells[area_key]
        bar_height = max(4, rect.height() // 15)
        bar_width = int(rect.width() * self.dwell_progress)

        bar_rect = QRect(rect.left(), rect.bottom() - bar_height + 1, bar_width, bar_height)
        painter.setBrush(QBrush(Qt.white))
        painter.setPen(Qt.NoPen)
        painter.drawRect(bar_rect)

    def paintEvent(self, event):
        """
        Paint the complete 3x3 grid UI.

        Parameters
        ----------
        event : QPaintEvent
            Qt paint event (required signature; unused).

        Returns
        -------
        None

        Notes
        -----
        - Computes cell rectangles from the widget size each frame.
        - Draws either groups-mode or letters-mode content.
        - Renders the gaze point as a red dot.
        """
        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.black)
        painter.setRenderHint(QPainter.Antialiasing, True)

        w, h = self.width(), self.height()
        cell_w = w // 3
        cell_h = h // 3

        keys = [
            ["NW", "N", "NE"],
            ["W", "C", "E"],
            ["SW", "S", "SE"],
        ]
        for row in range(3):
            for col in range(3):
                key = keys[row][col]
                x = col * cell_w
                y = row * cell_h
                cw = cell_w if col < 2 else w - 2 * cell_w
                ch = cell_h if row < 2 else h - 2 * cell_h
                self.cells[key] = QRect(x, y, cw, ch)

        font = painter.font()
        font.setPointSize(20)
        painter.setFont(font)

        painter.setPen(Qt.white)
        painter.setBrush(Qt.NoBrush)
        for rect in self.cells.values():
            painter.drawRect(rect)

        if self.mode == "groups":
            self.paint_groups_mode(painter)
        else:
            self.paint_letters_mode(painter)

        if not self.gazePointBlocked:
            gx, gy = self.map_gaze_to_widget()
            if gx is not None and gy is not None:
                painter.setBrush(QBrush(Qt.red))
                painter.setPen(Qt.NoPen)
                r = self.point_radius
                painter.drawEllipse(int(gx) - r, int(gy) - r, 2 * r, 2 * r)

    def paint_groups_mode(self, painter: QPainter) -> None:
        """
        Paint the UI content for "groups" mode.

        Parameters
        ----------
        painter : QPainter
            Active painter.

        Returns
        -------
        None

        Notes
        -----
        - N/W/E/S show the four letter groups.
        - SW shows BACKSPACE, SE shows SUBMIT.
        - Center cell shows prompt and current text.
        - Draws dwell bars for actionable cells in dwell mode.
        """
        painter.setPen(Qt.white)
        painter.setBrush(Qt.NoBrush)

        painter.drawText(self.cells["N"], Qt.AlignCenter | Qt.TextWordWrap, "A, B, C, D, E, F, G")
        painter.drawText(self.cells["W"], Qt.AlignCenter | Qt.TextWordWrap, "H, I, J, K, L, M, N")
        painter.drawText(self.cells["E"], Qt.AlignCenter | Qt.TextWordWrap, "O, P, Q, R, S, T, U")
        painter.drawText(self.cells["S"], Qt.AlignCenter | Qt.TextWordWrap, "V, W, X, Y, Z, ␣")
        painter.drawText(self.cells["SW"], Qt.AlignCenter | Qt.TextWordWrap, "BACKSPACE")
        painter.drawText(self.cells["SE"], Qt.AlignCenter | Qt.TextWordWrap, "SUBMIT")

        c_rect = self.cells["C"]
        text_rect = c_rect.adjusted(10, 10, -10, -10)
        painter.drawText(
            text_rect,
            Qt.AlignCenter | Qt.TextWordWrap,
            f"{self.question}\n\n> {self.current_text}",
        )

        for key in ["N", "W", "E", "S", "SW", "SE"]:
            self.draw_dwell_bar(painter, key)

    def paint_letters_mode(self, painter: QPainter) -> None:
        """
        Paint the UI content for "letters" mode (one selected group).

        Parameters
        ----------
        painter : QPainter
            Active painter.

        Returns
        -------
        None

        Notes
        -----
        - N cell is "BACK" to return to groups.
        - Letter slots are: ["NW","NE","W","E","SW","S","SE"].
        - Center cell shows prompt and current text.
        - Draws dwell bars for actionable cells in dwell mode.
        """
        if self.current_group_index is None:
            return

        letters = self.groups[self.current_group_index]
        slots = ["NW", "NE", "W", "E", "SW", "S", "SE"]

        painter.drawText(self.cells["N"], Qt.AlignCenter | Qt.TextWordWrap, "BACK")

        for i, key in enumerate(slots):
            if i >= len(letters):
                continue
            ch = letters[i]
            label = "SPACE" if ch == " " else ch
            painter.drawText(self.cells[key], Qt.AlignCenter | Qt.TextWordWrap, str(label))

        c_rect = self.cells["C"]
        text_rect = c_rect.adjusted(10, 10, -10, -10)
        painter.drawText(
            text_rect,
            Qt.AlignCenter | Qt.TextWordWrap,
            f"{self.question}\n\n> {self.current_text}",
        )

        for key in ["N"] + slots:
            self.draw_dwell_bar(painter, key)
