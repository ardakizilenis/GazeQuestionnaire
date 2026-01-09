# widgets/LikertScaleQuestionWidget.py
from __future__ import annotations

from PySide6.QtCore import QRect, QRectF, Signal
from PySide6.QtGui import (
    QLinearGradient,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import QApplication, QVBoxLayout

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

class LikertScaleQuestionWidget(GazeWidget):

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
        labels=None,
    ):
        super().__init__(parent)

        self.gazePointBlocked = gazepoint_blocked
        self.question = question
        self.activation_mode = activation_mode
        self.dwell_threshold_ms = int(dwell_threshold_ms)
        self.blink_threshold_ms = int(blink_threshold_ms)

        if labels is None:
            self.labels = ["1", "2", "3", "4", "5"]
        else:
            assert len(labels) == 5, "LikertScaleQuestionWidget requires exactly 5 labels."
            self.labels = [str(l) for l in labels]

        self.selected_index: int | None = None
        self.click_index: int = 0

        # Blink state
        self.is_blinking = False
        self.blink_fired = False
        self.blink_timer = QElapsedTimer()

        # Dwell state
        self.dwell_timer = QElapsedTimer()
        self.dwell_grace_ms = 700
        self.dwell_area: str | None = None
        self.dwell_progress: float = 0.0

        # Layout rects
        self.question_rect = QRect()
        self.submit_rect = QRect()
        self.option_rects: list[QRect] = [QRect() for _ in range(5)]

        # Logging (unchanged)
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

        # Theme + font
        self.matchTheme(theme)
        self.base_font = _try_load_futuristic_font()

        # Caches
        self._bg_cache = QPixmap()
        self._bg_cache_size = None

        self._scan_tile = QPixmap()
        self._scan_ready = False

        self._static_ui_cache = QPixmap()
        self._last_gaze_rect = None

        self.setAttribute(Qt.WA_OpaquePaintEvent, True)
        self.setAutoFillBackground(False)

    # ------------------------------------------------------------------ events

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._bg_cache = QPixmap()
        self._bg_cache_size = None
        self._static_ui_cache = QPixmap()
        self._static_ui_key = None
        self._layout_key = None
        self._scan_ready = False

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
            if self.blink_timer.elapsed() >= self.blink_threshold_ms and not self.blink_fired:
                self.handle_activation_by_point()
                self.blink_fired = True
            return

        if not blinking and self.is_blinking:
            self.is_blinking = False
            self.blink_fired = False

    # ------------------------------------------------------------------ logic

    def set_selection(self, index: int):
        if not (0 <= index < 5):
            return
        if self.selected_index != index:
            self.log_toggles += 1
        self.selected_index = index
        QApplication.beep()
        # Only options need repaint (selection highlight)
        for r in self.option_rects:
            self.update(r)

    def activate_submit(self):
        if self.selected_index is None:
            return
        QApplication.beep()
        self.submitted.emit(self.labels[self.selected_index])

    def area_for_point(self, x: int, y: int) -> str | None:
        if self.submit_rect.contains(x, y):
            return "submit"
        if self.question_rect.contains(x, y):
            return "rest"
        for i, rect in enumerate(self.option_rects):
            if rect.contains(x, y):
                return f"opt{i}"
        return None

    def handle_activation_for_area(self, area: str | None):
        if area is None or area == "rest":
            return

        if area.startswith("opt"):
            try:
                idx = int(area[3:])
            except ValueError:
                return
            if not (0 <= idx < 5):
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
            self._update_dwell_region()
            return

        elapsed = self.dwell_timer.elapsed()

        if elapsed < self.dwell_grace_ms:
            self.dwell_progress = 0.0
            self._update_dwell_region()
            return

        effective = max(1, self.dwell_threshold_ms - self.dwell_grace_ms)
        self.dwell_progress = max(0.0, min(1.0, (elapsed - self.dwell_grace_ms) / effective))

        if elapsed >= self.dwell_threshold_ms:
            self.handle_activation_for_area(area)
            self.dwell_timer.start()
            self.dwell_progress = 0.0

        self._update_dwell_region()

    def _update_dwell_region(self):
        r = self._dwell_bar_rect_for_area(self.dwell_area)
        if r is not None:
            self.update(r)

    def _dwell_bar_rect_for_area(self, area: str | None) -> QRect | None:
        if self.activation_mode != "dwell" or area is None:
            return None
        if area == "submit":
            rect = self.submit_rect
        elif area.startswith("opt"):
            try:
                idx = int(area[3:])
            except ValueError:
                return None
            if not (0 <= idx < 5):
                return None
            rect = self.option_rects[idx]
        else:
            return None

        bar_h = max(4, rect.height() // 16)
        pad = 8
        return QRect(rect.left() + pad, rect.bottom() - bar_h - pad + 1, rect.width() - 2 * pad, bar_h + 2)

    # ------------------------------------------------------------------ layout + caches

    def _ensure_layout(self):
        w, h = self.width(), self.height()
        key = (w, h)
        if self._layout_key == key:
            return

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

        self._layout_key = key

        # static UI depends on layout
        self._static_ui_cache = QPixmap()
        self._static_ui_key = None

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
        f.setStyleStrategy(QFont.PreferAntialias)
        f.setBold(True)
        f.setPointSize(max(12, int(h * 0.032)))
        f.setLetterSpacing(QFont.PercentageSpacing, 102)
        return f

    def _ensure_static_ui_cache(self):
        self._ensure_layout()
        w, h = self.width(), self.height()

        font = self._base_font_for(h)
        key = (w, h, self.question, tuple(self.labels), font.pointSize())

        if self._static_ui_key == key and not self._static_ui_cache.isNull():
            return

        pm = QPixmap(w, h)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.TextAntialiasing, True)

        def draw_panel(rect: QRect, accent: QColor, title: str | None = None, title_font: QFont | None = None):
            outer = rect.adjusted(10, 10, -10, -10)
            p.setBrush(self.theme.panel)

            border = QPen(self.theme.panel_border)
            border.setWidth(2)
            p.setPen(border)
            p.drawRoundedRect(QRectF(outer), 14, 14)

            acc = QColor(accent)
            acc.setAlpha(160)
            pen = QPen(acc)
            pen.setWidth(2)
            p.setPen(pen)
            p.drawLine(outer.left() + 12, outer.top() + 10, outer.right() - 12, outer.top() + 10)

            if title:
                p.setPen(self.theme.text)
                p.setFont(title_font or font)
                p.drawText(outer, Qt.AlignCenter, title)

        opt_font = QFont(font)
        opt_font.setBold(True)
        opt_font.setPointSize(max(11, int(h * 0.030)))

        for i, rect in enumerate(self.option_rects):
            draw_panel(rect, self.theme.neon_violet, title=str(self.labels[i]), title_font=opt_font)

        draw_panel(self.question_rect, self.theme.neon_cyan, title=None)
        draw_panel(self.submit_rect, self.theme.submit, title="SUBMIT", title_font=font)

        q_outer = self.question_rect.adjusted(10, 10, -10, -10)
        q_inner = q_outer.adjusted(18, 18, -18, -18)

        q_font = QFont(font)
        q_font.setBold(True)
        q_font.setPointSize(max(12, int(h * 0.030)))
        p.setFont(q_font)

        glow = QColor(self.theme.neon_cyan)
        glow.setAlpha(60)
        p.setPen(glow)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            p.drawText(QRectF(q_inner).translated(dx, dy), Qt.AlignCenter | Qt.TextWordWrap, self.question)

        p.setPen(self.theme.text)
        p.drawText(QRectF(q_inner), Qt.AlignCenter | Qt.TextWordWrap, self.question)

        p.end()
        self._static_ui_cache = pm
        self._static_ui_key = key

    # ------------------------------------------------------------------ drawing

    def _draw_selection_overlay(self, p: QPainter):
        if self.selected_index is None:
            return

        rect = self.option_rects[self.selected_index].adjusted(10, 10, -10, -10)
        # subtle neon fill + thicker border
        fill = QColor(self.theme.neon_pink if self.selected_index <= 1 else self.theme.neon_cyan)
        if self.selected_index == 2:
            fill = QColor(self.theme.neon_violet)
        if self.selected_index >= 3:
            fill = QColor(self.theme.neon_cyan)
        fill.setAlpha(35)
        p.setPen(Qt.NoPen)
        p.setBrush(fill)
        p.drawRoundedRect(QRectF(rect), 14, 14)

        border = QColor(fill)
        border.setAlpha(190)
        pen = QPen(border)
        pen.setWidth(3)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(QRectF(rect), 14, 14)

    def _draw_dwell_bar(self, p: QPainter):
        if self.activation_mode != "dwell":
            return
        if self.dwell_area is None or self.dwell_progress <= 0.0:
            return

        if self.dwell_area == "submit":
            rect = self.submit_rect
            accent = self.theme.submit
        elif self.dwell_area.startswith("opt"):
            try:
                idx = int(self.dwell_area[3:])
            except ValueError:
                return
            if not (0 <= idx < 5):
                return
            rect = self.option_rects[idx]
            accent = self.theme.neon_cyan
        else:
            return

        outer = rect.adjusted(10, 10, -10, -10)
        pad = 14
        bar_h = max(4, outer.height() // 16)
        full_w = max(1, outer.width() - 2 * pad)
        fill_w = int(full_w * self.dwell_progress)

        bar = QRect(outer.left() + pad, outer.bottom() - bar_h - pad + 1, fill_w, bar_h)

        c = QColor(accent)
        c.setAlpha(220)
        p.setPen(Qt.NoPen)
        p.setBrush(c)
        p.drawRoundedRect(QRectF(bar), bar_h / 2.0, bar_h / 2.0)

    # ------------------------------------------------------------------ paint

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)

        self._ensure_layout()
        self._ensure_background()
        self._ensure_static_ui_cache()

        if not self._bg_cache.isNull():
            p.drawPixmap(0, 0, self._bg_cache)
        if not self._static_ui_cache.isNull():
            p.drawPixmap(0, 0, self._static_ui_cache)

        self._draw_selection_overlay(p)
        self._draw_dwell_bar(p)

        if not self.gazePointBlocked:
            self._draw_gaze(p)
