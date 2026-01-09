# widgets/YesNoQuestionWidget.py
from __future__ import annotations

from PySide6.QtCore import (
    QRect,
    Signal
)
from PySide6.QtGui import (
    QLinearGradient,
    QPen,
    QPixmap, QFont, QFontDatabase,
)
from PySide6.QtWidgets import QApplication

from widgets.gaze_widget import *


# -----------------------------------------------------------------------------

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

# -----------------------------------------------------------------------------


class YesNoQuestionWidget(GazeWidget):
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

        self.selection: str | None = None
        self.click_index = 0

        # blink
        self.is_blinking = False
        self.blink_fired = False
        self.blink_timer = QElapsedTimer()

        # dwell
        self.dwell_grace_ms = 700
        self.dwell_timer = QElapsedTimer()
        self.dwell_area: str | None = None
        self.dwell_progress: float = 0.0

        # layout rects
        self.yes_rect = QRect()
        self.no_rect = QRect()
        self.submit_rect = QRect()
        self.question_rect = QRect()

        # logging
        self.log_toggles = 0
        self.log_resets = 0
        self.log_backspaces = 0
        self.log_extra = (
            f"yesno;"
            f"mode={self.activation_mode};"
            f"dwell_ms={self.dwell_threshold_ms};"
            f"blink_ms={self.blink_threshold_ms}"
        )

        # theme & font
        self.matchTheme(theme)
        self.base_font = _try_load_futuristic_font()

        # caches for ui
        self._bg_cache = QPixmap()
        self._bg_cache_size = None

        self._text_cache = QPixmap()
        self._text_cache_key = None

        self._scan_tile = QPixmap()
        self._scan_ready = False

        self._last_gaze_rect = None

        self.setAttribute(Qt.WA_OpaquePaintEvent, True)
        self.setAutoFillBackground(False)

    # ------------------------------------------------------------------ timing

    def _pulse(self) -> float:
        return 0.5 + 0.5 * math.sin(self.blink_timer.elapsed() * 0.002)

    # ------------------------------------------------------------------ gaze

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
            if (
                self.blink_timer.elapsed() >= self.blink_threshold_ms
                and not self.blink_fired
            ):
                self.handle_activation_by_point()
                self.blink_fired = True
            return

        if not blinking and self.is_blinking:
            self.is_blinking = False
            self.blink_fired = False

    # ------------------------------------------------------------------ logic

    def set_selection(self, sel: str):
        if sel not in ("yes", "no"):
            return
        if self.selection != sel:
            self.log_toggles += 1
        self.selection = sel
        QApplication.beep()
        self.update(self.yes_rect | self.no_rect)

    def activate_submit(self):
        if self.selection is None:
            return
        QApplication.beep()
        self.submitted.emit(self.selection)

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

    def handle_activation_for_area(self, area: str | None):
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
        x, y = self.map_gaze_to_widget()
        if x is None or y is None:
            return
        self.handle_activation_for_area(self.area_for_point(int(x), int(y)))

    # ------------------------------------------------------------------ dwell

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
            return

        eff = max(1, self.dwell_threshold_ms - self.dwell_grace_ms)
        self.dwell_progress = min(1.0, (elapsed - self.dwell_grace_ms) / eff)

        if elapsed >= self.dwell_threshold_ms:
            self.handle_activation_for_area(area)
            self.dwell_timer.start()
            self.dwell_progress = 0.0

        self.update()

    # ------------------------------------------------------------------ caching

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._bg_cache = QPixmap()
        self._bg_cache_size = None
        self._text_cache = QPixmap()
        self._text_cache_key = None
        self._scan_ready = False

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
        if self._bg_cache_size == (w, h):
            return

        self._ensure_scan_tile()
        pm = QPixmap(w, h)
        pm.fill(Qt.black)
        p = QPainter(pm)

        grad = QLinearGradient(0, 0, 0, h)
        grad.setColorAt(0, self.theme.bg0)
        grad.setColorAt(1, self.theme.bg1)
        p.fillRect(pm.rect(), grad)

        p.drawTiledPixmap(0, 0, w, h, self._scan_tile)
        p.end()

        self._bg_cache = pm
        self._bg_cache_size = (w, h)

    def _ensure_text_cache(self):
        w, h = self.width(), self.height()
        key = (w, h, self.question)
        if self._text_cache_key == key:
            return

        pm = QPixmap(w, h)
        pm.fill(Qt.transparent)
        p = QPainter(pm)

        font = QFont(self.base_font)
        font.setBold(True)
        font.setPointSize(max(14, int(h * 0.03)))
        p.setFont(font)
        p.setPen(self.theme.text)

        p.drawText(
            self.question_rect.adjusted(12, 12, -12, -12),
            Qt.AlignCenter | Qt.TextWordWrap,
            self.question,
        )
        p.end()

        self._text_cache = pm
        self._text_cache_key = key

    # ------------------------------------------------------------------ paint
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)

        self._ensure_background()
        p.drawPixmap(0, 0, self._bg_cache)

        w, h = self.width(), self.height()
        submit_h = int(h * 0.3)
        top_h = h - submit_h

        self.yes_rect = QRect(0, 0, w // 2, top_h)
        self.no_rect = QRect(w // 2, 0, w - w // 2, top_h)
        self.submit_rect = QRect(0, top_h, w, submit_h)

        side = max(100, int(top_h * 0.42))
        self.question_rect = QRect(
            (w - side) // 2,
            (top_h - side) // 2,
            side,
            side,
        )

        # panels
        def panel(rect: QRect, accent: QColor, active: bool):
            pen = QPen(accent if active else self.theme.panel_border)
            pen.setWidth(3 if active else 2)
            p.setPen(pen)
            p.setBrush(self.theme.panel)
            p.drawRoundedRect(rect.adjusted(8, 8, -8, -8), 14, 14)

        panel(self.yes_rect, self.theme.yes, self.selection == "yes")
        panel(self.no_rect, self.theme.no, self.selection == "no")
        panel(self.submit_rect, self.theme.submit, False)

        # labels
        p.setFont(self.base_font)
        p.setPen(self.theme.text)

        # font size for yes/no/submit
        label_font = QFont(self.base_font)
        label_font.setBold(True)
        label_font.setPixelSize(int(self.yes_rect.height() * 0.06))
        p.setFont(label_font)

        p.drawText(self.yes_rect, Qt.AlignCenter, "YES")
        p.drawText(self.no_rect, Qt.AlignCenter, "NO")
        p.drawText(self.submit_rect, Qt.AlignCenter, "SUBMIT")

        # question
        panel(self.question_rect, self.theme.neon_violet, False)
        self._ensure_text_cache()
        p.drawPixmap(0, 0, self._text_cache)

        # dwell bar
        if self.activation_mode == "dwell" and self.dwell_area and self.dwell_progress > 0:
            target = {
                "yes": self.yes_rect,
                "no": self.no_rect,
                "submit": self.submit_rect,
            }.get(self.dwell_area)
            if target:
                bar_w = int(target.width() * self.dwell_progress)
                bar = QRect(target.left(), target.bottom() - 6, bar_w, 6)
                p.fillRect(bar, self.theme.neon_cyan)

        # gaze
        if not self.gazePointBlocked:
            self._draw_gaze(p)
