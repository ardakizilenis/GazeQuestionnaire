# widgets/TextInputWidget.py
from __future__ import annotations

from PySide6.QtCore import QRect, QRectF, Signal
from PySide6.QtGui import (
    QLinearGradient,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import QApplication

from widgets.gaze_widget import *

def _try_load_futuristic_font() -> QFont:
    preferred = ["Orbitron", "Oxanium", "Exo 2", "Rajdhani", "Space Grotesk", "Inter"]
    fams = set(QFontDatabase.families())
    for fam in preferred:
        if fam in fams:
            f = QFont(fam)
            f.setStyleStrategy(QFont.PreferAntialias)
            return f
    f = QFont()
    f.setStyleStrategy(QFont.PreferAntialias)
    return f


class TextInputWidget(GazeWidget):

    submitted = Signal(object)
    clicked = Signal(int, str)

    def __init__(
        self,
        parent,
        question: str,
        gazepoint_blocked: bool,
        theme: str,
        activation_mode: str,
        dwell_threshold_ms: int,
        blink_threshold_ms: int,
    ):
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
            "RTZUFGH",
            "QWEASDY",
            "IOPJKLM",
            "XCVBN ",
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

        # Theme + font
        self.matchTheme(theme)
        self.base_font = _try_load_futuristic_font()

        # Caches
        self._bg_cache = QPixmap()
        self._bg_cache_size = None

        self._scan_tile = QPixmap()
        self._scan_ready = False

        self._mode_cache = QPixmap()
        self._mode_cache_key = None

        # Center cell
        self._center_cache = QPixmap()
        self._center_cache_key = None

        # Layout
        self._layout_key = None

        self.setAttribute(Qt.WA_OpaquePaintEvent, True)
        self.setAutoFillBackground(False)

    # ------------------------------------------------------------------ utils / logging

    def _emit_click(self, label: str) -> None:
        self.click_index += 1
        self.clicked.emit(self.click_index, label)

    # ------------------------------------------------------------------ Qt hooks

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._bg_cache = QPixmap()
        self._bg_cache_size = None
        self._scan_ready = False
        self._layout_key = None
        self._mode_cache = QPixmap()
        self._mode_cache_key = None
        self._center_cache = QPixmap()
        self._center_cache_key = None

    # ------------------------------------------------------------------ gaze / blink

    @Slot(float, float)
    def set_gaze(self, x: float, y: float):
        super().set_gaze(x, y)
        if self.activation_mode == "dwell":
            gx, gy = self.map_gaze_to_widget()
            if gx is not None and gy is not None:
                self.update_dwell(int(gx), int(gy))

    @Slot(bool)
    def set_blinking(self, blinking: bool):
        if self.activation_mode != "blink":
            return

        if blinking and not self.is_blinking:
            self.blink_timer.start()
            self.is_blinking = True
            self.blink_fired = False
            return

        if blinking and self.is_blinking:
            if self.blink_timer.elapsed() >= self.blink_threshold_ms and not self.blink_fired:
                self.handle_activation_by_point()
                self.blink_fired = True
            return

        if (not blinking) and self.is_blinking:
            self.is_blinking = False
            self.blink_fired = False

    # ------------------------------------------------------------------ input actions

    def append_char(self, ch: str) -> None:
        self.log_toggles += 1
        self.current_text += ch
        QApplication.beep()
        self._center_cache_key = None  # invalidate only center content
        self.update(self.cells["C"])

    def backspace(self) -> None:
        if not self.current_text:
            return
        self.current_text = self.current_text[:-1]
        self.log_backspaces += 1
        QApplication.beep()
        self._center_cache_key = None
        self.update(self.cells["C"])

    def submit(self) -> None:
        QApplication.beep()
        self.submitted.emit(self.current_text)

    # ------------------------------------------------------------------ hit testing

    def area_for_point(self, x: int, y: int) -> str | None:
        for key, rect in self.cells.items():
            if rect.contains(x, y):
                return key
        return None

    def handle_activation_by_point(self) -> None:
        gx, gy = self.map_gaze_to_widget()
        if gx is None or gy is None:
            return
        self.handle_activation(self.area_for_point(int(gx), int(gy)))

    def handle_activation(self, area: str | None) -> None:
        if area is None:
            return
        if self.mode == "groups":
            self.handle_groups_activation(area)
        else:
            self.handle_letters_activation(area)

    def handle_groups_activation(self, area: str) -> None:
        old_mode = self.mode
        old_group = self.current_group_index

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

        # mode switch invalidates mode cache + center cache
        if self.mode != old_mode or self.current_group_index != old_group:
            self._mode_cache_key = None
            self._center_cache_key = None

        self.update()

    def handle_letters_activation(self, area: str) -> None:
        if self.current_group_index is None:
            self.mode = "groups"
            self._mode_cache_key = None
            self._center_cache_key = None
            self.update()
            return

        letters = self.groups[self.current_group_index]

        if area == "N":
            self._emit_click("back")
            self.mode = "groups"
            self.current_group_index = None
            QApplication.beep()
            self._mode_cache_key = None
            self._center_cache_key = None
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

        # after selection, back to groups
        self.mode = "groups"
        self.current_group_index = None
        self._mode_cache_key = None
        self._center_cache_key = None
        self.update()

    # ------------------------------------------------------------------ dwell

    def update_dwell(self, x: int, y: int) -> None:
        area = self.area_for_point(x, y)
        if area is None:
            self.dwell_area = None
            self.dwell_progress = 0.0
            return

        if self.dwell_area != area:
            self.dwell_area = area
            self.dwell_progress = 0.0
            self.dwell_timer.start()
            self.update(self._dwell_bar_rect(area))
            return

        elapsed = self.dwell_timer.elapsed()

        if elapsed < self.dwell_grace_ms:
            self.dwell_progress = 0.0
            self.update(self._dwell_bar_rect(area))
            return

        effective = max(1, self.dwell_threshold_ms - self.dwell_grace_ms)
        self.dwell_progress = max(0.0, min(1.0, (elapsed - self.dwell_grace_ms) / effective))

        if elapsed >= self.dwell_threshold_ms:
            self.handle_activation(area)
            self.dwell_timer.start()
            self.dwell_progress = 0.0

        self.update(self._dwell_bar_rect(area))

    def _dwell_bar_rect(self, area_key: str) -> QRect:
        rect = self.cells[area_key]
        pad = max(10, rect.width() // 18)
        bar_h = max(4, rect.height() // 16)
        # plus a bit for rounded corners
        return QRect(rect.left() + pad - 2, rect.bottom() - bar_h - pad - 2, rect.width() - 2 * pad + 4, bar_h + 6)

    # ------------------------------------------------------------------ layout

    def _ensure_layout(self):
        w, h = self.width(), self.height()
        key = (w, h)
        if self._layout_key == key:
            return

        cell_w = w // 3
        cell_h = h // 3
        keys = [
            ["NW", "N", "NE"],
            ["W", "C", "E"],
            ["SW", "S", "SE"],
        ]

        for row in range(3):
            for col in range(3):
                k = keys[row][col]
                x = col * cell_w
                y = row * cell_h
                cw = cell_w if col < 2 else w - 2 * cell_w
                ch = cell_h if row < 2 else h - 2 * cell_h
                self.cells[k] = QRect(x, y, cw, ch)

        self._layout_key = key
        self._mode_cache_key = None
        self._center_cache_key = None

    # ------------------------------------------------------------------ caches

    def _ensure_scan_tile(self):
        if self._scan_ready:
            return
        pm = QPixmap(8, 6)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        c = QColor("#0A1030")
        c.setAlpha(45)
        p.fillRect(0, 0, 8, 1, c)
        p.end()
        self._scan_tile = pm
        self._scan_ready = True

    def _ensure_background(self):
        w, h = self.width(), self.height()
        if self._bg_cache_size == (w, h) and not self._bg_cache.isNull():
            return

        self._ensure_scan_tile()

        pm = QPixmap(w, h)
        pm.fill(Qt.black)
        p = QPainter(pm)

        grad = QLinearGradient(0, 0, 0, h)
        grad.setColorAt(0.0, self.theme.bg0)
        grad.setColorAt(1.0, self.theme.bg1)
        p.fillRect(pm.rect(), grad)

        p.drawTiledPixmap(0, 0, w, h, self._scan_tile)
        p.end()

        self._bg_cache = pm
        self._bg_cache_size = (w, h)

    def _base_font_for(self, h: int) -> QFont:
        f = QFont(self.base_font)
        f.setBold(True)
        f.setLetterSpacing(QFont.PercentageSpacing, 102)
        f.setPointSize(max(13, int(h * 0.034)))
        return f

    def _draw_panel(self, p: QPainter, rect: QRect, accent: QColor):
        outer = rect.adjusted(10, 10, -10, -10)
        p.setBrush(self.theme.panel)

        pen = QPen(self.theme.panel_border)
        pen.setWidth(2)
        p.setPen(pen)
        p.drawRoundedRect(QRectF(outer), 16, 16)

        acc = QColor(accent)
        acc.setAlpha(165)
        pen2 = QPen(acc)
        pen2.setWidth(2)
        p.setPen(pen2)
        p.drawLine(outer.left() + 14, outer.top() + 12, outer.right() - 14, outer.top() + 12)

    def _ensure_mode_cache(self):
        self._ensure_layout()
        w, h = self.width(), self.height()
        font = self._base_font_for(h)
        key = (w, h, self.mode, self.current_group_index, font.pointSize())
        if self._mode_cache_key == key and not self._mode_cache.isNull():
            return

        pm = QPixmap(w, h)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.TextAntialiasing, True)

        # draw 9 panels (center panel drawn too; its text is separate cache)
        for k, r in self.cells.items():
            # per-key accent choices
            if k == "SE":
                accent = self.theme.submit
            elif k == "SW":
                accent = self.theme.backspace
            elif k == "N" and self.mode == "letters":
                accent = self.theme.back
            else:
                accent = self.theme.neon_violet

            self._draw_panel(p, r, accent)

        p.setFont(font)
        p.setPen(self.theme.text)

        if self.mode == "groups":
            # group labels
            p.drawText(self.cells["N"].adjusted(16, 16, -16, -16), Qt.AlignCenter | Qt.TextWordWrap, "R T Z U\nF G H")
            p.drawText(self.cells["W"].adjusted(16, 16, -16, -16), Qt.AlignCenter | Qt.TextWordWrap, "Q W E\nA S D\nY")
            p.drawText(self.cells["E"].adjusted(16, 16, -16, -16), Qt.AlignCenter | Qt.TextWordWrap, "I O P\nJ K L\nM")
            p.drawText(self.cells["S"].adjusted(16, 16, -16, -16), Qt.AlignCenter | Qt.TextWordWrap, "X C V B N\n␣")
            p.drawText(self.cells["SW"].adjusted(16, 16, -16, -16), Qt.AlignCenter | Qt.TextWordWrap, "BACKSPACE")
            p.drawText(self.cells["SE"].adjusted(16, 16, -16, -16), Qt.AlignCenter | Qt.TextWordWrap, "SUBMIT")

        else:
            # letters mode
            p.drawText(self.cells["N"].adjusted(16, 16, -16, -16), Qt.AlignCenter | Qt.TextWordWrap, "BACK")

            if self.current_group_index is not None:
                letters = self.groups[self.current_group_index]
                slots = ["NW", "NE", "W", "E", "SW", "S", "SE"]
                # slightly smaller for single chars
                lf = QFont(font)
                lf.setPointSize(max(14, int(h * 0.045)))
                p.setFont(lf)

                for i, key2 in enumerate(slots):
                    if i >= len(letters):
                        continue
                    ch = letters[i]
                    label = "SPACE" if ch == " " else ch
                    p.drawText(self.cells[key2].adjusted(16, 16, -16, -16), Qt.AlignCenter, label)

        p.end()
        self._mode_cache = pm
        self._mode_cache_key = key

    def _ensure_center_cache(self):
        self._ensure_layout()
        w, h = self.width(), self.height()
        font = self._base_font_for(h)
        key = (w, h, self.mode, self.current_group_index, self.question, self.current_text, font.pointSize())
        if self._center_cache_key == key and not self._center_cache.isNull():
            return

        pm = QPixmap(w, h)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.TextAntialiasing, True)

        c_rect = self.cells["C"].adjusted(10, 10, -10, -10)
        inner = c_rect.adjusted(16, 16, -16, -16)

        # prompt + text
        # prompt smaller, input bigger
        prompt_font = QFont(font)
        prompt_font.setBold(True)
        prompt_font.setPointSize(max(12, int(h * 0.022)))

        input_font = QFont(font)
        input_font.setBold(True)
        input_font.setPointSize(max(14, int(h * 0.030)))

        # compose a nice layout
        # We do manual two-block draw to avoid heavy layout engines.
        p.setPen(self.theme.text_dim)
        p.setFont(prompt_font)
        p.drawText(QRectF(inner), Qt.AlignHCenter | Qt.AlignTop | Qt.TextWordWrap, self.question)

        # caret-style current text
        p.setPen(self.theme.text)
        p.setFont(input_font)
        p.drawText(
            QRectF(inner).adjusted(0, int(inner.height() * 0.35), 0, 0),
            Qt.AlignHCenter | Qt.AlignTop | Qt.TextWordWrap,
            f"> {self.current_text}",
        )

        p.end()
        self._center_cache = pm
        self._center_cache_key = key

    # ------------------------------------------------------------------ drawing overlays

    def _draw_dwell_bar(self, p: QPainter):
        if self.activation_mode != "dwell":
            return
        if self.dwell_area is None or self.dwell_progress <= 0.0:
            return

        rect = self.cells.get(self.dwell_area)
        if rect is None:
            return

        outer = rect.adjusted(10, 10, -10, -10)
        pad = max(12, outer.width() // 18)
        bar_h = max(4, outer.height() // 16)
        full_w = max(1, outer.width() - 2 * pad)
        fill_w = int(full_w * self.dwell_progress)
        bar = QRect(outer.left() + pad, outer.bottom() - bar_h - pad + 1, fill_w, bar_h)

        # choose accent by cell
        if self.dwell_area == "SE":
            accent = self.theme.submit
        elif self.dwell_area == "SW":
            accent = self.theme.backspace
        elif self.dwell_area == "N" and self.mode == "letters":
            accent = self.theme.back
        else:
            accent = self.theme.neon_cyan

        c = QColor(accent)
        c.setAlpha(220)
        p.setPen(Qt.NoPen)
        p.setBrush(c)
        p.drawRoundedRect(QRectF(bar), bar_h / 2.0, bar_h / 2.0)

    # ------------------------------------------------------------------ painting

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)

        self._ensure_layout()
        self._ensure_background()
        self._ensure_mode_cache()
        self._ensure_center_cache()

        if not self._bg_cache.isNull():
            p.drawPixmap(0, 0, self._bg_cache)

        if not self._mode_cache.isNull():
            p.drawPixmap(0, 0, self._mode_cache)

        if not self._center_cache.isNull():
            p.drawPixmap(0, 0, self._center_cache)

        self._draw_dwell_bar(p)

        if not self.gazePointBlocked:
            self._draw_gaze(p)
