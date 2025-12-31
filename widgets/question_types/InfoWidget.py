# widgets/InfoWidget.py
from __future__ import annotations

from PySide6.QtCore import QTimer, Signal, QRect, QRectF
from PySide6.QtGui import (
    QFontMetrics,
    QLinearGradient,
    QPainterPath,
    QPen,
    QBrush,
    QPixmap,
)

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


class InfoWidget(GazeWidget):
    submitted = Signal(object)

    def __init__(self, parent, gazepoint_blocked: bool, theme: str, text: str, duration_sec: int):
        super().__init__(parent)

        self.gazePointBlocked = gazepoint_blocked
        self.text = text
        self.duration_ms = max(1, int(duration_sec * 1000))

        match theme:
            case "neon": self.theme = NeonTheme()
            case "retro_terminal": self.theme = RetroTerminalTheme()
            case "clinical": self.theme = ClinicalTheme()
            case "oled_dark": self.theme = OledDarkTheme()
            case _: self.theme = ClinicalTheme()

        self.base_font = _try_load_futuristic_font()

        self.timer = QElapsedTimer()
        self.timer.start()

        # Weniger Ticks = weniger Last. 33ms ~ 30 FPS, für Progress reicht das meist völlig.
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.on_tick)
        self.update_timer.start(33)

        self.done = False

        # Caches
        self._bg_cache = QPixmap()
        self._bg_cache_size = None

        self._scan_tile = QPixmap()  # 1 tile for scanlines
        self._scan_tile_ready = False

        self._text_cache = QPixmap()
        self._text_cache_key = None  # (w, h, text, font_point, bold)

        self._last_gaze_rect = None  # QRect

        self.setAttribute(Qt.WA_OpaquePaintEvent, True)
        self.setAutoFillBackground(False)

    # ---------- sizing helpers ----------

    def _text_rect(self) -> QRect:
        w, h = self.width(), self.height()
        return QRect(int(w * 0.10), int(h * 0.12), int(w * 0.80), int(h * 0.65))

    def _progress_rect(self) -> QRect:
        w, h = self.width(), self.height()
        bar_h = int(h * 0.050)
        bar_m = int(w * 0.070)
        bar_y = h - bar_h - int(h * 0.060)
        # plus a little padding for glow/border
        pad = max(6, int(min(w, h) * 0.01))
        return QRect(bar_m - pad, bar_y - pad, (w - 2 * bar_m) + 2 * pad, bar_h + 2 * pad)

    # ---------- animation ----------

    def on_tick(self):
        if self.done:
            return

        elapsed = self.timer.elapsed()
        if elapsed >= self.duration_ms:
            self.done = True
            self.update_timer.stop()
            self.submitted.emit(None)

        # Invalidate only what changes: progress bar region (+ gaze dot region if needed)
        regions = [self._progress_rect()]

        if not self.gazePointBlocked:
            gx, gy = self.map_gaze_to_widget()
            if gx is not None and gy is not None:
                r = int(self.point_radius * 2.6)  # halo area
                gaze_rect = QRect(int(gx - r), int(gy - r), int(2 * r), int(2 * r))

                # Update previous + current to avoid trails
                if self._last_gaze_rect is not None:
                    regions.append(self._last_gaze_rect)
                regions.append(gaze_rect)
                self._last_gaze_rect = gaze_rect

        # One combined update call is fine; Qt merges internally.
        for r in regions:
            self.update(r)

    # ---------- caching ----------

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._bg_cache = QPixmap()
        self._bg_cache_size = None
        self._scan_tile_ready = False
        self._text_cache = QPixmap()
        self._text_cache_key = None

    def _ensure_scan_tile(self):
        """Build a tiny pixmap used for scanline tiling (fast)."""
        if self._scan_tile_ready:
            return
        # tile height 6 like before: line + gap
        tile_w, tile_h = 8, 6
        pm = QPixmap(tile_w, tile_h)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        line = QColor("#0A1030")
        line.setAlpha(45)
        p.fillRect(0, 0, tile_w, 1, line)
        p.end()
        self._scan_tile = pm
        self._scan_tile_ready = True

    def _ensure_background_cache(self):
        w, h = self.width(), self.height()
        if w <= 0 or h <= 0:
            return
        if self._bg_cache_size == (w, h) and not self._bg_cache.isNull():
            return

        self._ensure_scan_tile()

        pm = QPixmap(w, h)
        pm.fill(Qt.black)

        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing, True)

        # Base gradient
        bg = QLinearGradient(0, 0, 0, h)
        bg.setColorAt(0.0, self.theme.bg0)
        bg.setColorAt(1.0, self.theme.bg1)
        p.fillRect(QRect(0, 0, w, h), QBrush(bg))

        # Subtle scanlines (tiled)
        p.drawTiledPixmap(0, 0, w, h, self._scan_tile)

        # Corner accents (cheap)
        pad = int(min(w, h) * 0.06)
        corner_len = int(min(w, h) * 0.10)
        corner_th = max(2, int(min(w, h) * 0.004))

        pen = QPen(self.theme.neon_cyan)
        c = QColor(self.theme.neon_cyan)
        c.setAlpha(110)
        pen.setColor(c)
        pen.setWidth(corner_th)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)

        def corner_path(x0, y0, x1, y1, x2, y2):
            path = QPainterPath(QPointF(x0, y0))
            path.lineTo(x1, y1)
            path.lineTo(x2, y2)
            return path

        p.drawPath(corner_path(pad + corner_len, pad, pad, pad, pad, pad + corner_len))
        p.drawPath(corner_path(w - pad - corner_len, pad, w - pad, pad, w - pad, pad + corner_len))
        p.drawPath(corner_path(pad + corner_len, h - pad, pad, h - pad, pad, h - pad - corner_len))
        p.drawPath(corner_path(w - pad - corner_len, h - pad, w - pad, h - pad, w - pad, h - pad - corner_len))

        p.end()

        self._bg_cache = pm
        self._bg_cache_size = (w, h)

    def _make_font_for_text(self) -> QFont:
        w, h = self.width(), self.height()
        title_size = max(14, int(h * 0.050))
        body_size = max(12, int(h * 0.038))

        font = QFont(self.base_font)
        font.setBold(True)
        font.setPointSize(title_size)
        font.setLetterSpacing(QFont.PercentageSpacing, 102)

        # Cheap fit heuristic
        rect = QRectF(self._text_rect())
        fm = QFontMetrics(font)
        approx_lines = max(1, int(fm.horizontalAdvance(self.text) / max(1.0, rect.width())) + 1)
        if approx_lines >= 5:
            font.setPointSize(max(12, int(title_size * 0.88)))
        if approx_lines >= 8:
            font.setBold(False)
            font.setPointSize(max(11, int(body_size)))
        return font

    def _ensure_text_cache(self):
        w, h = self.width(), self.height()
        if w <= 0 or h <= 0:
            return

        font = self._make_font_for_text()
        key = (w, h, self.text, font.pointSize(), font.bold())

        if self._text_cache_key == key and not self._text_cache.isNull():
            return

        tr = self._text_rect()
        pm = QPixmap(w, h)
        pm.fill(Qt.transparent)

        p = QPainter(pm)
        p.setRenderHint(QPainter.TextAntialiasing, True)

        # Glow: reduced to 2 layers, fewer offset draws (fast-ish, and cached)
        glow = QColor(self.theme.neon_cyan)
        glow.setAlpha(70)
        p.setFont(font)

        # layer 1: small blur
        p.setPen(glow)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            p.drawText(QRectF(tr).translated(dx, dy), Qt.AlignCenter | Qt.TextWordWrap, self.text)

        # layer 2: even smaller
        glow2 = QColor(self.theme.neon_violet)
        glow2.setAlpha(45)
        p.setPen(glow2)
        for dx, dy in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
            p.drawText(QRectF(tr).translated(dx, dy), Qt.AlignCenter | Qt.TextWordWrap, self.text)

        # main text
        p.setPen(self.theme.text)
        p.drawText(QRectF(tr), Qt.AlignCenter | Qt.TextWordWrap, self.text)

        p.end()

        self._text_cache = pm
        self._text_cache_key = key

    # ---------- drawing ----------

    def _draw_progress(self, p: QPainter, progress: float):
        w, h = self.width(), self.height()

        bar_height = int(h * 0.050)
        bar_margin = int(w * 0.070)
        bar_y = h - bar_height - int(h * 0.060)

        track = QRectF(bar_margin, bar_y, w - 2 * bar_margin, bar_height)
        radius = bar_height / 2.0

        # Track
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(self.theme.bar_track))
        p.drawRoundedRect(track, radius, radius)

        # Border
        border = QColor(self.theme.bar_border)
        border.setAlpha(190)
        pen = QPen(border)
        pen.setWidth(max(2, int(h * 0.003)))
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(track, radius, radius)

        # Fill (simple gradient; no extra glow rects)
        fill_w = max(0.0, min(track.width(), track.width() * progress))
        if fill_w <= 1:
            return

        fill = QRectF(track.left(), track.top(), fill_w, track.height())
        pulse = self._pulse()

        grad = QLinearGradient(fill.left(), 0, fill.right(), 0)
        c1 = QColor(self.theme.neon_cyan); c1.setAlpha(220)
        c2 = QColor(self.theme.neon_pink); c2.setAlpha(200)
        c3 = QColor(self.theme.neon_violet); c3.setAlpha(190)
        grad.setColorAt(0.0, c1)
        grad.setColorAt(0.55 + 0.08 * (pulse - 0.5), c2)
        grad.setColorAt(1.0, c3)

        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(grad))
        p.drawRoundedRect(fill, radius, radius)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)

        # Background cache
        self._ensure_background_cache()
        if not self._bg_cache.isNull():
            # Only paint the exposed region if you want; simplest: draw full cached bg
            p.drawPixmap(0, 0, self._bg_cache)

        # Animated “nebula” reduced: just a tiny translucent overlay (fast)
        # (Kept outside bg-cache so it can pulse without rebuilding background.)
        pulse = self._pulse()
        w, h = self.width(), self.height()
        overlay = QColor(self.theme.neon_violet)
        overlay.setAlpha(int(10 + 10 * pulse))
        p.fillRect(self.rect(), overlay)

        # Text cache (only rebuild when needed)
        self._ensure_text_cache()
        if not self._text_cache.isNull():
            p.drawPixmap(0, 0, self._text_cache)

        # Progress
        elapsed = self.timer.elapsed()
        progress = max(0.0, min(1.0, elapsed / self.duration_ms))
        self._draw_progress(p, progress)

        # Gaze
        if not self.gazePointBlocked:
            self._draw_gaze(p)
