# ui/TextInputWidget.py

from PySide6.QtCore import QElapsedTimer, QRect, Slot, Qt, Signal
from PySide6.QtGui import QPainter, QBrush, QFont
from PySide6.QtWidgets import QApplication

from ui.gaze_widget import GazeWidget


class TextInputWidget(GazeWidget):
    """
    Eyetracking-Textinput with 3x3-Grid.

    Layout in the Groups-Mode:
        [ NW: (unused)   ][ N: G0 (A–G)     ][ NE: (unused) ]
        [  W: G1 (H-N)   ][ C: Prompt+Text  ][  E: G2 (O-U) ]
        [ SW: BACKSPACE  ][ S: G3 (V-Z + ␣ )][ SE: SUBMIT   ]

    - Choose one Group -> "Letters-Mode" for this Group:
          NW -> 'A' | 'H' | 'O' | 'V'
          N  -> "BACK" (back to all groups)
          NE -> 'B' | 'I' | 'P' | 'W'
          W  -> 'C' | 'J' | 'Q' | 'X'
          E  -> 'D' | 'K' | 'R' | 'Y'
          SW -> 'E' | 'L' | 'S' | 'Z'
          S  -> 'F' | 'M' | 'T' | '␣'
          SE -> 'G' | 'N' | 'U' | unused

      After choosing a letter, it will be appended to the text and the group mode is returned to

    Activation-Modes:
      - activation_mode = "blink":
            blink > blink_threshold_ms on a cell -> Activation
      - activation_mode = "dwell":
            dwell-time > dwell_threshold_ms -> Activation
            -> A Dwell-Bar is bellow to show the activation progress.

    Logging:
      - log_toggles:      how often a char has beeing toggled
      - log_resets:       0 (no Resets here)
      - log_backspaces:   how often a backspace was activated
      - log_extra:        Extra information (tresholds)
    """

    submitted = Signal(object)   # str: inputed text
    clicked = Signal(int, str)

    def __init__(
        self,
        question: str,
        parent=None,
        activation_mode: str = "dwell",
        dwell_threshold_ms: int = 1200,
        blink_threshold_ms: int = 150
    ):
        super().__init__(parent)

        self.question = question
        self.activation_mode = activation_mode
        self.dwell_threshold_ms = dwell_threshold_ms
        self.blink_threshold_ms = blink_threshold_ms

        self.current_text: str = ""
        self.click_index: int = 0

        self.mode: str = "groups"
        self.current_group_index: int | None = None

        self.groups: list[str] = [
            "ABCDEFG",   # Index 0 (NORTH)
            "HIJKLMN",   # Index 1 (WEST)
            "OPQRSTU",   # Index 2 (EAST)
            "VWXYZ ",    # Index 3 (SOUTH)
        ]

        self.is_blinking = False
        self.blink_fired = False
        self.blink_timer = QElapsedTimer()

        self.dwell_timer = QElapsedTimer()
        self.dwell_grace_ms = 700
        self.dwell_area: str | None = None   # "NW","N","NE","W","C","E","SW","S","SE"
        self.dwell_progress: float = 0.0     # 0..1

        self.cells: dict[str, QRect] = {
            "NW": QRect(),
            "N": QRect(),
            "NE": QRect(),
            "W": QRect(),
            "C": QRect(),
            "E": QRect(),
            "SW": QRect(),
            "S": QRect(),
            "SE": QRect(),
        }

        # Logging
        self.log_toggles = 0       # Char Input
        self.log_resets = 0        # Resets (non-existent in text-input)
        self.log_backspaces = 0    # Backspaced
        self.log_extra = (         # extra-metrics
            f"textgrid;"
            f"mode={self.activation_mode};"
            f"dwell_ms={self.dwell_threshold_ms};"
            f"blink_ms={self.blink_threshold_ms}"
        )

    def _emit_click(self, label: str):
        self.click_index += 1
        self.clicked.emit(self.click_index, label)

    # gets x and y coords and maps the gaze point to the UI
    @Slot(float, float)
    def set_gaze(self, x: float, y: float):
        super().set_gaze(x, y)

        if self.activation_mode == "dwell":
            gx, gy = self.map_gaze_to_widget()
            if gx is not None:
                self.update_dwell(int(gx), int(gy))

    # Blinking logic: If Blinking -> Start timer and stop when blinking finishes
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
            if duration >= self.blink_threshold_ms and not self.blink_fired:
                self.handle_activation_by_point()
                self.blink_fired = True

        # Blink END
        elif not blinking and self.is_blinking:
            self.is_blinking = False
            self.blink_fired = False

    # appends the chosen char to the current text (Logs a toggle)
    def append_char(self, ch: str):
        self.log_toggles += 1
        self.current_text += ch
        QApplication.beep()

    # removes the last char from the current text (Logs a toggle)
    def backspace(self):
        if self.current_text:
            self.current_text = self.current_text[:-1]
            self.log_backspaces += 1
            QApplication.beep()

    # submits the written text area (Marks submit with 1 in the csv)
    def submit(self):
        QApplication.beep()
        self.submitted.emit(self.current_text)

    # returns the area in which the gaze point is currently in ("N", "W", "NE", ...)
    def area_for_point(self, x: int, y: int) -> str | None:
        for key, rect in self.cells.items():
            if rect.contains(x, y):
                return key
        return None

    # Activation Handling for the area, where the point is currently in
    def handle_activation_by_point(self):
        gx, gy = self.map_gaze_to_widget()
        if gx is None:
            return
        area = self.area_for_point(int(gx), int(gy))
        self.handle_activation(area)

    # decides the activation method in dependency of the current status
    # (Group-Status Activation vs Letters-Status Activation)
    def handle_activation(self, area: str | None):
        if area is None:
            return
        if self.mode == "groups":
            # if the status is "groups-mode"
            self.handle_groups_activation(area)
        else:
            # if the status is "letters-mode"
            self.handle_letters_activation(area)

    # changes the mode to "letters", if not "backspace", "submit", NE or NW was selected
    # -> The grid redesigns with the letters inside the group
    def handle_groups_activation(self, area: str):
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

        # Backspace / Submit only in "group-mode"
        elif area == "SW":
            self._emit_click("backspace")
            self.backspace()
        elif area == "SE":
            self._emit_click("submit")
            self.submit()

        self.update()

    # letters-mode activation, if the gaze-point was in an area with a letter
    def handle_letters_activation(self, area: str):
        if self.current_group_index is None:
            self.mode = "groups"
            return

        # the letters of the group (according to the index) are being mapped
        letters = self.groups[self.current_group_index]

        # the "NORTH" area is reserved to go back to the letter-groups
        if area == "N":
            self._emit_click("back")
            self.mode = "groups"
            self.current_group_index = None
            QApplication.beep()
            self.update()
            return

        # The given char-array is mapped to the slots
        slots = ["NW", "NE", "W", "E", "SW", "S", "SE"]
        if area in slots:
            idx = slots.index(area)
            if idx < len(letters):
                ch = letters[idx]
                char_to_add = " " if ch == " " else ch

                self._emit_click("char:SPACE" if char_to_add == " " else f"char:{char_to_add}")
                self.append_char(char_to_add)

        # Return to the groups-mode after choosing a letter (Maybe faster and more comfortable with no return?)
        self.mode = "groups"
        self.current_group_index = None
        self.update()

    # handles the dwell-activation logic and the dwell-progress, which is needed for the dwell-progress-bar
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

        # 1) Grace period: первые 100ms kein Fortschritt
        if elapsed < self.dwell_grace_ms:
            self.dwell_progress = 0.0
            self.update()
            return

        # 2) Progress nach Grace
        effective = self.dwell_threshold_ms - self.dwell_grace_ms
        if effective <= 1:
            effective = 1

        self.dwell_progress = max(
            0.0,
            min(1.0, (elapsed - self.dwell_grace_ms) / effective)
        )

        # 3) Aktivierung
        if elapsed >= self.dwell_threshold_ms:
            self.handle_activation(area)
            self.dwell_timer.start()
            self.dwell_progress = 0.0

        self.update()

    # draw method for the dwell-bar
    def draw_dwell_bar(self, painter: QPainter, area_key: str):
        if self.activation_mode != "dwell":
            return
        if self.dwell_area != area_key:
            return
        if self.dwell_progress <= 0.0:
            return

        rect = self.cells[area_key]
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

    # paints the 3x3 grid and UI
    def paintEvent(self, event):
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

        # Fonts
        font = painter.font()
        font.setPointSize(20)
        painter.setFont(font)

        # Groups-Mode vs Letters-Mode
        painter.setPen(Qt.white)
        painter.setBrush(Qt.NoBrush)

        for rect in self.cells.values():
            painter.drawRect(rect)

        if self.mode == "groups":
            self.paint_groups_mode(painter)
        else:
            self.paint_letters_mode(painter)

        # Gaze-Point
        gx, gy = self.map_gaze_to_widget()
        if gx is not None:
            painter.setBrush(QBrush(Qt.red))
            painter.setPen(Qt.NoPen)
            r = self.point_radius
            painter.drawEllipse(int(gx) - r, int(gy) - r, 2 * r, 2 * r)

    # Paints the groups mode
    def paint_groups_mode(self, painter: QPainter):
        painter.setPen(Qt.white)
        painter.setBrush(Qt.NoBrush)

        # N/W/E/S -> Groups
        painter.drawText(self.cells["N"], Qt.AlignCenter | Qt.TextWordWrap, "A, B, C, D, E, F, G")
        painter.drawText(self.cells["W"], Qt.AlignCenter | Qt.TextWordWrap, "H, I, J, K, L, M, N")
        painter.drawText(self.cells["E"], Qt.AlignCenter | Qt.TextWordWrap, "O, P, Q, R, S, T, U")
        painter.drawText(self.cells["S"], Qt.AlignCenter | Qt.TextWordWrap, "V, W, X, Y, Z, ␣")

        # SW -> Backspace
        painter.drawText(self.cells["SW"], Qt.AlignCenter | Qt.TextWordWrap, "BACKSPACE")

        # SE -> Submit
        painter.drawText(self.cells["SE"], Qt.AlignCenter | Qt.TextWordWrap, "SUBMIT")

        # Center: Question + Current Text
        c_rect = self.cells["C"]
        text_rect = c_rect.adjusted(10, 10, -10, -10)
        painter.drawText(
            text_rect,
            Qt.AlignCenter | Qt.TextWordWrap,
            f"{self.question}\n\n> {self.current_text}",
        )

        # Dwell-Bars
        for key in ["N", "W", "E", "S", "SW", "SE"]:
            self.draw_dwell_bar(painter, key)

    # Draw One (selected) Group in the letters mode
    def paint_letters_mode(self, painter: QPainter):
        if self.current_group_index is None:
            return

        letters = self.groups[self.current_group_index]
        slots = ["NW", "NE", "W", "E", "SW", "S", "SE"]

        # N = back to all groups
        painter.drawText(self.cells["N"], Qt.AlignCenter | Qt.TextWordWrap, "BACK")

        # Distributes letters to the slots
        for i, key in enumerate(slots):
            if i >= len(letters):
                continue
            ch = letters[i]
            label = "SPACE" if ch == " " else ch
            painter.drawText(self.cells[key], Qt.AlignCenter | Qt.TextWordWrap, str(label))

        # Center: Question + Current Text
        c_rect = self.cells["C"]
        text_rect = c_rect.adjusted(10, 10, -10, -10)
        painter.drawText(
            text_rect,
            Qt.AlignCenter | Qt.TextWordWrap,
            f"{self.question}\n\n> {self.current_text}",
        )

        # Dwell-Bars
        for key in ["N"] + slots:
            self.draw_dwell_bar(painter, key)
