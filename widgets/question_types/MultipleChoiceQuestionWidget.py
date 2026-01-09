# widgets/MultipleChoiceQuestionWidget.py
from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QRect, QRectF, Signal
from PySide6.QtGui import (
    QLinearGradient,
    QPen,
    QPixmap, QFont, QFontDatabase,
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


class MultipleChoiceQuestionWidget(GazeWidget):

    submitted = Signal(object)
    clicked = Signal(int, str)

    def __init__(
        self,
        question: str,
        parent,
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
            self.labels = ["A", "B", "C", "D"]
        else:
            assert len(labels) == 4, "MultipleChoiceQuestionWidget requires exactly 4 labels."
            self.labels = [str(l) for l in labels]

        self.selected: set[int] = set()
        self.click_index: int = 0

        # Blink
        self.is_blinking = False
        self.blink_fired = False
        self.blink_timer = QElapsedTimer()

        # Dwell
        self.dwell_timer = QElapsedTimer()
        self.dwell_grace_ms = 700
        self.dwell_area: str | None = None
        self.dwell_progress: float = 0.0

        # Layout
        self.option_rects = [QRect() for _ in range(4)]
        self.rect_reset = QRect()
        self.rect_rest = QRect()
        self.rect_submit = QRect()
        self._layout_key = None

        # Logging (unchanged)
        self.log_toggles = 0
        self.log_resets = 0
        self.log_backspaces = 0
        self.log_extra = (
            f"mcq;"
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

        self._static_ui_cache = QPixmap()  # panels + labels + question (non-animated)
        self._static_ui_key = None

        self.setAttribute(Qt.WA_OpaquePaintEvent, True)
        self.setAutoFillBackground(False)

    # ------------------------------------------------------------------ Qt

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._bg_cache = QPixmap()
        self._bg_cache_size = None
        self._scan_ready = False
        self._static_ui_cache = QPixmap()
        self._static_ui_key = None
        self._layout_key = None

    # ------------------------------------------------------------------ gaze/blink

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

    # ------------------------------------------------------------------ selection

    def toggle_option(self, index: int):
        if not (0 <= index < 4):
            return

        if index in self.selected:
            self.selected.remove(index)
        else:
            self.selected.add(index)

        self.log_toggles += 1
        QApplication.beep()
        self.update(self.option_rects[index])

    def reset_selection(self):
        if not self.selected:
            return
        self.selected.clear()
        self.log_resets += 1
        QApplication.beep()
        for r in self.option_rects:
            self.update(r)

    def activate_submit(self):
        QApplication.beep()
        result_labels = [self.labels[i] for i in sorted(self.selected)]
        self.submitted.emit(result_labels)

    # ------------------------------------------------------------------ areas

    def area_for_point(self, x: int, y: int) -> str | None:
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
        if area is None or area == "rest":
            return

        if area.startswith("opt"):
            try:
                idx = int(area[3:])
            except ValueError:
                return
            if not (0 <= idx < 4):
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
            return

    def handle_activation_by_point(self):
        gx, gy = self.map_gaze_to_widget()
        if gx is None or gy is None:
            return
        self.handle_activation_for_area(self.area_for_point(int(gx), int(gy)))

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
            self.update()
            return

        effective = max(1, self.dwell_threshold_ms - self.dwell_grace_ms)
        self.dwell_progress = max(0.0, min(1.0, (elapsed - self.dwell_grace_ms) / effective))

        if elapsed >= self.dwell_threshold_ms:
            self.handle_activation_for_area(area)
            self.dwell_timer.start()
            self.dwell_progress = 0.0

        self.update()

    # ------------------------------------------------------------------ caching/layout

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

    def _ensure_layout(self):
        w, h = self.width(), self.height()
        key = (w, h)
        if self._layout_key == key:
            return

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

        self._layout_key = key
        self._static_ui_cache = QPixmap()
        self._static_ui_key = None

    def _base_font_for(self, h: int) -> QFont:
        f = QFont(self.base_font)
        f.setBold(True)
        f.setPointSize(max(12, int(h * 0.030)))
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

        def panel(rect: QRect, accent: QColor, title: str | None = None):
            outer = rect.adjusted(10, 10, -10, -10)
            p.setBrush(self.theme.panel)

            # border
            pen = QPen(self.theme.panel_border)
            pen.setWidth(2)
            p.setPen(pen)
            p.drawRoundedRect(QRectF(outer), 14, 14)

            # subtle accent line
            acc = QColor(accent)
            acc.setAlpha(160)
            pen2 = QPen(acc)
            pen2.setWidth(2)
            p.setPen(pen2)
            p.drawLine(outer.left() + 12, outer.top() + 10, outer.right() - 12, outer.top() + 10)

            if title is not None:
                p.setPen(self.theme.text)
                p.setFont(font)
                p.drawText(outer, Qt.AlignCenter | Qt.TextWordWrap, title)

        # option panels
        opt_font = QFont(font)
        opt_font.setPointSize(max(12, int(h * 0.035)))
        for i, r in enumerate(self.option_rects):
            p.setFont(opt_font)
            panel(r, self.theme.option_accent, str(self.labels[i]))

        # reset/rest/submit panels
        panel(self.rect_reset, self.theme.reset, "RESET")
        panel(self.rect_submit, self.theme.submit, "SUBMIT")
        panel(self.rect_rest, self.theme.neon_cyan, None)

        # question in REST area with light cached glow
        q_outer = self.rect_rest.adjusted(10, 10, -10, -10)
        q_inner = q_outer.adjusted(14, 14, -14, -14)

        q_font = QFont(font)
        q_font.setBold(True)
        q_font.setPointSize(max(11, int(h * 0.024)))
        p.setFont(q_font)

        glow = QColor(self.theme.neon_cyan)
        glow.setAlpha(55)
        p.setPen(glow)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            p.drawText(QRectF(q_inner).translated(dx, dy), Qt.AlignCenter | Qt.TextWordWrap, self.question)

        p.setPen(self.theme.text)
        p.drawText(QRectF(q_inner), Qt.AlignCenter | Qt.TextWordWrap, self.question)

        p.end()
        self._static_ui_cache = pm
        self._static_ui_key = key

    # ------------------------------------------------------------------ drawing overlays

    def _draw_selected_overlays(self, p: QPainter):
        # fill + border only for selected options
        for i in self.selected:
            if not (0 <= i < 4):
                continue
            outer = self.option_rects[i].adjusted(10, 10, -10, -10)

            fill = QColor(self.theme.neon_violet)
            fill.setAlpha(35)
            p.setPen(Qt.NoPen)
            p.setBrush(fill)
            p.drawRoundedRect(QRectF(outer), 14, 14)

            br = QColor(self.theme.neon_violet)
            br.setAlpha(200)
            pen = QPen(br)
            pen.setWidth(3)
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(QRectF(outer), 14, 14)

    def _draw_dwell_bar(self, p: QPainter):
        if self.activation_mode != "dwell":
            return
        if self.dwell_area is None or self.dwell_progress <= 0.0:
            return

        def bar_for(rect: QRect, accent: QColor):
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

        a = self.dwell_area
        if a == "reset":
            bar_for(self.rect_reset, self.theme.reset)
        elif a == "submit":
            bar_for(self.rect_submit, self.theme.submit)
        elif a.startswith("opt"):
            try:
                idx = int(a[3:])
            except ValueError:
                return
            if 0 <= idx < 4:
                bar_for(self.option_rects[idx], self.theme.neon_cyan)

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

        # dynamic overlays
        self._draw_selected_overlays(p)
        self._draw_dwell_bar(p)

        if not self.gazePointBlocked:
            self._draw_gaze(p)
