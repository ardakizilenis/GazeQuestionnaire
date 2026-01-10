# widgets/SmoothPursuit_YesNoWidget.py
# Smooth Pursuit Yes-No-Widget (Neon theme + performance caches)

from __future__ import annotations

import math
import time
from typing import Dict, List, Optional, Tuple

import numpy as np
from PySide6.QtCore import QRect, QTimer, Signal
from PySide6.QtGui import (
    QLinearGradient,
    QPen,
    QPixmap,
    QPainterPath, QFont, QFontDatabase,
)
from PySide6.QtWidgets import QApplication

from widgets.gaze_widget import *


# -------------------------- signal processing (unchanged) --------------------------


def pearson_corr(a: np.ndarray, b: np.ndarray) -> float:
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    if a.size < 3 or b.size < 3:
        return 0.0
    if a.size != b.size:
        m = min(a.size, b.size)
        a = a[-m:]
        b = b[-m:]

    a = a - a.mean()
    b = b - b.mean()
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom < 1e-9:
        return 0.0
    return float(np.dot(a, b) / denom)


def max_lagged_pearson_corr(a: np.ndarray, b: np.ndarray, max_lag_samples: int) -> float:
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    if a.size < 3 or b.size < 3:
        return 0.0

    m = min(a.size, b.size)
    a = a[-m:]
    b = b[-m:]

    max_lag_samples = int(max(0, max_lag_samples))
    if max_lag_samples == 0:
        return pearson_corr(a, b)

    best: Optional[float] = None
    for k in range(-max_lag_samples, max_lag_samples + 1):
        if k == 0:
            aa, bb = a, b
        elif k > 0:
            aa, bb = a[k:], b[:-k]
        else:
            kk = -k
            aa, bb = a[:-kk], b[kk:]

        if aa.size < 3 or bb.size < 3:
            continue

        c = pearson_corr(aa, bb)
        if best is None or c > best:
            best = c

    return float(best) if best is not None else 0.0


def gaussian_proximity(dist: np.ndarray, sigma: float) -> np.ndarray:
    sigma = max(1.0, float(sigma))
    return np.exp(-(dist * dist) / (2.0 * sigma * sigma))


# -------------------------- neon theme + font helpers --------------------------

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


# -------------------------- widget --------------------------


class SmoothPursuitYesNoWidget(GazeWidget):

    submitted = Signal(object)
    clicked = Signal(int, str)

    def __init__(
        self,
        question: str,
        parent,
        gazepoint_blocked: bool,
        theme: str,
        # Pursuit params
        window_ms: int = 1250,
        corr_threshold: float = 0.73,
        toggle_stable_samples: int = 18,
        submit_stable_samples: int = 30,
        use_lag_compensation: bool = True,
        max_lag_ms: int = 180,
        # Motion params
        option_frequency_hz: float = 0.25,
        submit_frequency_hz: float = 0.28,
        # Visual/layout
        orbit_scale: float = 0.36,
        # Proximity mixing
        proximity_sigma_px: float = 220.0,
        proximity_weight: float = 0.15,
        # Cooldowns
        toggle_cooldown_ms: int = 1300,
        submit_cooldown_ms: int = 1400,
        # Behaviour
        allow_empty_submit: bool = False,
    ):
        super().__init__(parent)

        self.gazePointBlocked = gazepoint_blocked
        self.question = question
        self.labels = ["yes", "no"]

        self.window_ms = int(window_ms)
        self.corr_threshold = float(corr_threshold)
        self.submit_corr_threshold = float(self.corr_threshold + 0.06)
        self.toggle_stable_samples = int(toggle_stable_samples)
        self.submit_stable_samples = int(submit_stable_samples)
        self.use_lag_compensation = bool(use_lag_compensation)
        self.max_lag_ms = int(max_lag_ms)

        self.option_frequency_hz = float(option_frequency_hz)
        self.submit_frequency_hz = float(submit_frequency_hz)

        self.orbit_scale = float(orbit_scale)

        self.proximity_sigma_px = float(proximity_sigma_px)
        self.proximity_weight = float(max(0.0, min(1.0, proximity_weight)))
        self.corr_weight = 1.0 - self.proximity_weight

        self.toggle_cooldown_ms = int(toggle_cooldown_ms)
        self.submit_cooldown_ms = int(submit_cooldown_ms)
        self.allow_empty_submit = bool(allow_empty_submit)

        self._t0 = time.monotonic()

        self._t: List[float] = []
        self._gx: List[float] = []
        self._gy: List[float] = []
        self._tx: Dict[str, List[float]] = {lab: [] for lab in self.labels}
        self._ty: Dict[str, List[float]] = {lab: [] for lab in self.labels}
        self._sx: List[float] = []
        self._sy: List[float] = []

        self.selected: Optional[str] = None

        self._candidate: Optional[str] = None
        self._candidate_count = 0
        self._submit_count = 0

        self._toggle_block_until = 0.0
        self._submit_block_until = 0.0

        self._last_scores: Dict[str, float] = {lab: 0.0 for lab in self.labels}
        self._last_submit_score: float = 0.0

        self.click_index: int = 0

        self.log_toggles = 0
        self.log_resets = 0
        self.log_backspaces = 0
        self.log_extra = "sp_yesno"

        # ---- neon theme + caches ----
        self.matchTheme(theme)

        self.base_font = _try_load_futuristic_font()

        self._scan_tile = QPixmap()
        self._scan_ready = False

        self._bg_cache = QPixmap()
        self._bg_cache_size = None

        # layout cache
        self._layout_key = None
        self._question_rect = QRect()
        self._submit_rect = QRect()
        self._submit_ax = 0.0
        self._submit_line_y = 0
        self._centers: Dict[str, Tuple[float, float]] = {}
        self._orbit_hw_hh: Dict[str, Tuple[float, float]] = {}
        self._orbit_paths: Dict[str, QPainterPath] = {}

        # static ui cache (orbits, question panel + text, base labels, submit guide line)
        self._static_ui_cache = QPixmap()
        self._static_ui_key = None

        # header cache (instruction line without dynamic Selected:)
        self._info_cache = QPixmap()
        self._info_cache_key = None

        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(16)
        self._anim_timer.timeout.connect(self.update)
        self._anim_timer.start()

        self.setAttribute(Qt.WA_OpaquePaintEvent, True)
        self.setAutoFillBackground(False)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._bg_cache = QPixmap()
        self._bg_cache_size = None
        self._layout_key = None
        self._static_ui_cache = QPixmap()
        self._static_ui_key = None
        self._info_cache = QPixmap()
        self._info_cache_key = None

    # ---------------- background caches ----------------

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
        w, h = max(1, self.width()), max(1, self.height())
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

    # ---------------- layout + paths ----------------

    @staticmethod
    def _rect_path_pos(
        cx: float, cy: float, half_w: float, half_h: float, t: float, freq_hz: float, clockwise: bool
    ) -> Tuple[float, float]:
        u = (t * freq_hz) % 1.0
        if not clockwise:
            u = (1.0 - u) % 1.0

        p = u * 4.0
        x0, x1 = cx - half_w, cx + half_w
        y0, y1 = cy - half_h, cy + half_h

        if 0.0 <= p < 1.0:
            return x0 + (x1 - x0) * p, y0
        if 1.0 <= p < 2.0:
            q = p - 1.0
            return x1, y0 + (y1 - y0) * q
        if 2.0 <= p < 3.0:
            q = p - 2.0
            return x1 - (x1 - x0) * q, y1
        q = p - 3.0
        return x0, y1 - (y1 - y0) * q

    def _layout(self) -> Tuple[QRect, Dict[str, Tuple[float, float]], Dict[str, Tuple[float, float]], QRect, float]:
        w = max(1, self.width())
        h = max(1, self.height())

        q_w = int(w * 0.52)
        q_h = int(h * 0.22)
        qx = (w - q_w) // 2
        qy = int(h * 0.175) - q_h // 2
        question_rect = QRect(qx, qy, q_w, q_h)

        base = min(w, h)
        orbit_size = max(260.0, base * self.orbit_scale)
        half_w = orbit_size * 0.50
        half_h = orbit_size * 0.60

        margin = int(orbit_size * 0.72) + 32

        mid_y = float(h * 0.54)
        left_x = float(margin)
        right_x = float(w - margin)

        centers = {self.labels[0]: (left_x, mid_y), self.labels[1]: (right_x, mid_y)}
        hw_hh = {self.labels[0]: (half_w, half_h), self.labels[1]: (half_w, half_h)}

        submit_w = int(max(380, w * 0.28))
        submit_h = int(max(90, h * 0.095))
        submit_y = int(h * 0.88)
        submit_rect = QRect(int(w * 0.5 - submit_w / 2), int(submit_y - submit_h / 2), submit_w, submit_h)

        submit_ax = max(220.0, w * 0.30)
        return question_rect, centers, hw_hh, submit_rect, float(submit_ax)

    def _ensure_layout_cache(self):
        w, h = max(1, self.width()), max(1, self.height())
        key = (w, h, float(self.orbit_scale))
        if self._layout_key == key:
            return

        qrect, centers, hw_hh, submit_rect, submit_ax = self._layout()
        self._question_rect = qrect
        self._centers = centers
        self._orbit_hw_hh = hw_hh
        self._submit_rect = submit_rect
        self._submit_ax = float(submit_ax)
        self._submit_line_y = int(self._submit_rect.center().y())

        # precompute orbit paths
        self._orbit_paths = {}
        for lab in self.labels:
            cx, cy = self._centers[lab]
            hw, hh = self._orbit_hw_hh[lab]
            path = QPainterPath()
            path.addRect(cx - hw, cy - hh, 2 * hw, 2 * hh)
            self._orbit_paths[lab] = path

        self._layout_key = key
        self._static_ui_cache = QPixmap()
        self._static_ui_key = None
        self._info_cache = QPixmap()
        self._info_cache_key = None

    def _ensure_static_ui_cache(self):
        self._ensure_layout_cache()
        w, h = max(1, self.width()), max(1, self.height())

        info_pt = max(15, int(h * 0.027))
        q_pt = max(18, int(h * 0.030))
        lab_pt = max(30, int(h * 0.050))
        submit_pt = max(20, int(h * 0.036))

        key = (w, h, self.question, info_pt, q_pt, lab_pt, submit_pt)
        if self._static_ui_key == key and not self._static_ui_cache.isNull():
            return

        pm = QPixmap(w, h)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.TextAntialiasing, True)

        # orbit outlines
        orbit_pen = QPen(self.theme.orbit)
        orbit_pen.setWidth(2)
        orbit_pen.setCosmetic(True)
        p.setPen(orbit_pen)
        p.setBrush(Qt.NoBrush)
        for lab in self.labels:
            p.drawPath(self._orbit_paths[lab])

        # submit guide line
        guide = QColor(self.theme.guide)
        guide.setAlpha(170)
        pen = QPen(guide)
        pen.setWidth(3)
        pen.setCosmetic(True)
        p.setPen(pen)
        ax = float(self._submit_ax)
        y_line = int(self._submit_line_y)
        p.drawLine(int(w * 0.5 - ax), y_line, int(w * 0.5 + ax), y_line)

        # question panel + text
        qr = self._question_rect.adjusted(10, 10, -10, -10)
        p.setBrush(self.theme.panel)
        pen = QPen(self.theme.panel_border)
        pen.setWidth(2)
        pen.setCosmetic(True)
        p.setPen(pen)
        p.drawRoundedRect(qr, 16, 16)

        qfont = QFont(self.base_font)
        qfont.setBold(False)
        qfont.setPointSize(q_pt)
        p.setFont(qfont)

        glow = QColor(self.theme.neon_cyan)
        glow.setAlpha(55)
        inner = qr.adjusted(16, 16, -16, -16)
        p.setPen(glow)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            p.drawText(QRect(inner).translated(dx, dy), Qt.AlignCenter | Qt.TextWordWrap, self.question)
        p.setPen(self.theme.text)
        p.drawText(inner, Qt.AlignCenter | Qt.TextWordWrap, self.question)

        # base YES/NO labels (dim)
        lfont = QFont(self.base_font)
        lfont.setBold(True)
        lfont.setPointSize(lab_pt)
        p.setFont(lfont)
        p.setPen(self.theme.text_dim)

        disp = {self.labels[0]: "YES", self.labels[1]: "NO"}
        for lab in self.labels:
            cx, cy = self._centers[lab]
            rect = QRect(int(cx - 220), int(cy - 90), 440, 180)
            p.drawText(rect, Qt.AlignCenter, disp.get(lab, lab).upper())

        p.end()
        self._static_ui_cache = pm
        self._static_ui_key = key

    def _targets_at_time(self, t: float) -> Tuple[Dict[str, Tuple[float, float]], QRect, Tuple[float, float], float]:
        self._ensure_layout_cache()
        w = max(1, self.width())

        pos: Dict[str, Tuple[float, float]] = {}

        # YES (left): rectangle CCW
        cx, cy = self._centers[self.labels[0]]
        hw, hh = self._orbit_hw_hh[self.labels[0]]
        pos[self.labels[0]] = self._rect_path_pos(cx, cy, hw, hh, t, self.option_frequency_hz, clockwise=False)

        # NO (right): rectangle CW
        cx, cy = self._centers[self.labels[1]]
        hw, hh = self._orbit_hw_hh[self.labels[1]]
        pos[self.labels[1]] = self._rect_path_pos(cx, cy, hw, hh, t, self.option_frequency_hz, clockwise=True)

        omega = 2.0 * math.pi * self.submit_frequency_hz
        submit_dot_x = (w * 0.5) + self._submit_ax * math.sin(omega * t)
        submit_dot_y = float(self._submit_line_y)

        return pos, self._submit_rect, (float(submit_dot_x), float(submit_dot_y)), float(self._submit_ax)

    # ---------------- rolling buffer maintenance ----------------

    def _estimate_max_lag_samples(self) -> int:
        if len(self._t) >= 6:
            dt = float(np.median(np.diff(np.asarray(self._t, dtype=float))))
            if dt <= 1e-6:
                dt = 1.0 / 30.0
        else:
            dt = 1.0 / 30.0
        return int(round(max(0.0, self.max_lag_ms / 1000.0) / dt))

    def _prune_window(self) -> None:
        if not self._t:
            return
        newest = self._t[-1]
        min_t = newest - (self.window_ms / 1000.0)

        while self._t and self._t[0] < min_t:
            self._t.pop(0)
            self._gx.pop(0)
            self._gy.pop(0)
            for lab in self.labels:
                self._tx[lab].pop(0)
                self._ty[lab].pop(0)
            self._sx.pop(0)
            self._sy.pop(0)

    def _now(self) -> float:
        return time.monotonic()

    # ---------------- gaze input ----------------

    @Slot(float, float)
    def set_gaze(self, x: float, y: float):
        super().set_gaze(x, y)

        gx, gy = self.map_gaze_to_widget()
        if gx is None or gy is None:
            self._candidate = None
            self._candidate_count = 0
            self._submit_count = 0
            return

        t = time.monotonic() - self._t0
        opt_pos, _, submit_dot, _ = self._targets_at_time(t)
        sx, sy = submit_dot

        self._t.append(float(t))
        self._gx.append(float(gx))
        self._gy.append(float(gy))
        for lab in self.labels:
            tx, ty = opt_pos[lab]
            self._tx[lab].append(float(tx))
            self._ty[lab].append(float(ty))
        self._sx.append(float(sx))
        self._sy.append(float(sy))

        self._prune_window()
        if len(self._t) < 12:
            return

        self._update_decision()

    # ---------------- decision logic ----------------

    def _option_score(self, lab: str) -> float:
        gx = np.asarray(self._gx, dtype=float)
        gy = np.asarray(self._gy, dtype=float)
        tx = np.asarray(self._tx[lab], dtype=float)
        ty = np.asarray(self._ty[lab], dtype=float)

        if self.use_lag_compensation:
            max_lag_samples = self._estimate_max_lag_samples()
            cx = max_lagged_pearson_corr(gx, tx, max_lag_samples)
            cy = max_lagged_pearson_corr(gy, ty, max_lag_samples)
        else:
            cx = pearson_corr(gx, tx)
            cy = pearson_corr(gy, ty)

        corr = 0.5 * (cx + cy)

        dist = np.sqrt((gx - tx) ** 2 + (gy - ty) ** 2)
        prox = float(np.mean(gaussian_proximity(dist, self.proximity_sigma_px)))
        prox_mapped = (2.0 * prox) - 1.0

        return float((self.corr_weight * corr) + (self.proximity_weight * prox_mapped))

    def _submit_score(self) -> float:
        gx = np.asarray(self._gx, dtype=float)
        gy = np.asarray(self._gy, dtype=float)
        sx = np.asarray(self._sx, dtype=float)
        sy = np.asarray(self._sy, dtype=float)

        if self.use_lag_compensation:
            max_lag_samples = self._estimate_max_lag_samples()
            corr = max_lagged_pearson_corr(gx, sx, max_lag_samples)
        else:
            corr = pearson_corr(gx, sx)

        dist = np.sqrt((gx - sx) ** 2 + (gy - sy) ** 2)
        prox = float(np.mean(gaussian_proximity(dist, self.proximity_sigma_px)))
        prox_mapped = (2.0 * prox) - 1.0

        return float((self.corr_weight * corr) + (self.proximity_weight * prox_mapped))

    def _select(self, choice: str) -> None:
        if self.selected != choice:
            self.selected = choice
            self.log_toggles += 1

        self.click_index += 1
        self.clicked.emit(self.click_index, f"select:{choice}")
        QApplication.beep()

        self._toggle_block_until = self._now() + (self.toggle_cooldown_ms / 1000.0)

    def _submit(self) -> None:
        if (not self.allow_empty_submit) and (self.selected is None):
            return

        self.click_index += 1
        self.clicked.emit(self.click_index, "submit")
        QApplication.beep()

        self._submit_block_until = self._now() + (self.submit_cooldown_ms / 1000.0)
        self.submitted.emit(self.selected if self.selected is not None else "")

    def _update_decision(self) -> None:
        now = self._now()

        # option scores
        best_lab: Optional[str] = None
        best_score = -999.0
        for lab in self.labels:
            s = self._option_score(lab)
            self._last_scores[lab] = s
            if s > best_score:
                best_score = s
                best_lab = lab

        option_candidate = best_lab if (best_lab is not None and best_score >= self.corr_threshold) else None

        if option_candidate is None:
            self._candidate = None
            self._candidate_count = 0
        else:
            if option_candidate == self._candidate:
                self._candidate_count += 1
            else:
                self._candidate = option_candidate
                self._candidate_count = 1

        # submit score
        ss = self._submit_score()
        self._last_submit_score = ss
        if ss >= self.submit_corr_threshold:
            self._submit_count += 1
        else:
            self._submit_count = 0

        # submit first
        if now >= self._submit_block_until and self._submit_count >= self.submit_stable_samples:
            self._submit_count = 0
            self._candidate = None
            self._candidate_count = 0
            self._submit()
            return

        # select
        if now >= self._toggle_block_until and self._candidate is not None and self._candidate_count >= self.toggle_stable_samples:
            lab = self._candidate
            self._candidate = None
            self._candidate_count = 0
            self._select(lab)

    # ---------------- paint (fast) ----------------

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)

        w, h = max(1, self.width()), max(1, self.height())
        self._ensure_background()
        self._ensure_layout_cache()
        self._ensure_static_ui_cache()

        # background + static layers
        p.drawPixmap(0, 0, self._bg_cache)
        p.drawPixmap(0, 0, self._static_ui_cache)
        p.drawPixmap(0, 0, self._info_cache)

        # highlight best candidate
        highlight_opt: Optional[str] = None
        if self._last_scores:
            best = max(self._last_scores, key=self._last_scores.get)
            if self._last_scores.get(best, 0.0) >= self.corr_threshold:
                highlight_opt = best

        # dynamic: Selected line (small)
        info_rect = QRect(28, 18, w - 56, int(h * 0.13))
        font = QFont(self.base_font)
        font.setPointSize(max(15, int(h * 0.027)))
        font.setBold(False)
        p.setFont(font)
        p.setPen(self.theme.text)
        sel_txt = self.selected.upper() if self.selected else "-"
        p.drawText(info_rect.adjusted(14, 10, -14, -10), Qt.AlignLeft | Qt.AlignBottom, f"Selected: {sel_txt}")

        # current positions for moving targets
        t = time.monotonic() - self._t0
        opt_pos, submit_rect, submit_dot, _ = self._targets_at_time(t)

        # overlay label styling for highlight/selected (only for up to 2 labels)
        lab_font = QFont(self.base_font)
        lab_font.setBold(True)
        lab_font.setPointSize(max(30, int(h * 0.050)))
        p.setFont(lab_font)

        def _label_rect(lab: str) -> QRect:
            cx, cy = self._centers[lab]
            return QRect(int(cx - 220), int(cy - 90), 440, 180)

        disp = {self.labels[0]: "YES", self.labels[1]: "NO"}

        if highlight_opt is not None:
            pen = QPen(self.theme.highlight, 4)
            pen.setCosmetic(True)
            p.setPen(pen)
            p.drawText(_label_rect(highlight_opt), Qt.AlignCenter, disp.get(highlight_opt, highlight_opt).upper())

        if self.selected is not None:
            pen = QPen(self.theme.selected, 6)
            pen.setCosmetic(True)
            p.setPen(pen)
            p.drawText(_label_rect(self.selected), Qt.AlignCenter, disp.get(self.selected, self.selected).upper())

        # moving YES/NO dots
        p.setPen(Qt.NoPen)
        for lab in self.labels:
            x, y = opt_pos[lab]
            selected = (lab == self.selected)
            highlight = (lab == highlight_opt)

            if selected:
                p.setBrush(self.theme.selected)
                r = max(10, int(h * 0.018))
            elif highlight:
                p.setBrush(self.theme.dot)
                r = max(9, int(h * 0.016))
            else:
                p.setBrush(self.theme.dot)
                r = max(8, int(h * 0.014))

            p.drawEllipse(int(x) - r, int(y) - r, 2 * r, 2 * r)

        # submit (text + dot)
        enabled = (self.allow_empty_submit or (self.selected is not None))
        submit_font = QFont(self.base_font)
        submit_font.setBold(True)
        submit_font.setPointSize(max(20, int(h * 0.036)))
        p.setFont(submit_font)

        pen = QPen(self.theme.text if enabled else self.theme.disabled, 4 if enabled else 3)
        pen.setCosmetic(True)
        p.setPen(pen)
        p.drawText(submit_rect, Qt.AlignCenter, f"SUBMIT ({sel_txt}) ⏎")

        sx, sy = submit_dot
        p.setPen(Qt.NoPen)
        if not enabled:
            p.setBrush(self.theme.disabled)
            rr = max(9, int(h * 0.016))
        else:
            p.setBrush(self.theme.dot)
            rr = max(11, int(h * 0.020)) if (self._last_submit_score >= self.submit_corr_threshold) else max(9, int(h * 0.016))
        p.drawEllipse(int(sx) - rr, int(sy) - rr, 2 * rr, 2 * rr)

        # gaze
        if not self.gazePointBlocked:
            self._draw_gaze(p)
