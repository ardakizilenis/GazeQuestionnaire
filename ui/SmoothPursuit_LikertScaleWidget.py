# ui/SmoothPursuit_LikertWidget.py
# Smooth Pursuit Likert (5 options) rewritten in the SAME style/logic as SmoothPursuitMultipleChoiceWidget.
#
# Layout / Motion (as requested):
# - Label 1: circle CCW, left-middle
# - Label 2: square CW, left-top
# - Label 3: triangle CW, top-middle
# - Label 4: circle CCW, top-right
# - Label 5: square CW, mid-right
# - Center: question box like MCQ / YesNo
# - Bottom: SUBMIT button moving horizontally, same scoring logic as MCQ (X-only corr + proximity)
#
# Decision (MCQ-like):
# - Rolling time window buffers (window_ms)
# - Lag-compensated Pearson correlation (+ optional proximity bias)
# - Stable detection uses SAMPLE COUNTS (toggle_stable_samples / submit_stable_samples)
# - Cooldowns prevent rapid re-triggers
#
# Signals:
#   submitted(object): emits ONLY the selected label string (e.g. "3" or "neutral")
#   clicked(int, str): emits "select:<label>" and "submit"


from __future__ import annotations

import math
import time
from typing import Dict, List, Optional, Tuple, Any

import numpy as np
from PySide6.QtCore import Qt, QRect, QTimer, Slot, Signal, QPoint
from PySide6.QtGui import QPainter, QPen
from PySide6.QtWidgets import QApplication

from ui.gaze_widget import GazeWidget


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

    best = -1.0
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
        if c > best:
            best = c

    return float(best if best > -1.0 else 0.0)


def gaussian_proximity(dist: np.ndarray, sigma: float) -> np.ndarray:
    sigma = max(1.0, float(sigma))
    return np.exp(-(dist * dist) / (2.0 * sigma * sigma))


class SmoothPursuitLikertScaleWidget(GazeWidget):
    """
    Smooth Pursuit Likert (5 options, single-select) with SUBMIT.

    IMPORTANT:
    - labels MUST be passed from JSON (items[i]["labels"]) as a list of 5 strings.
      This widget will use them directly.
    - submitted(object): emits ONLY the selected label string (e.g. "Neutral")
    """

    submitted = Signal(object)
    clicked = Signal(int, str)

    def __init__(
        self,
        question: str,
        labels: Optional[List[str]] = None,
        parent=None,

        # Pursuit params (match MCQ naming)
        window_ms: int = 1250,
        corr_threshold: float = 0.73,
        toggle_stable_samples: int = 18,
        submit_stable_samples: int = 12,
        use_lag_compensation: bool = True,
        max_lag_ms: int = 180,

        # Motion params
        option_frequency_hz: float = 0.25,
        submit_frequency_hz: float = 0.28,

        # Visual / layout
        orbit_scale: float = 0.34,

        # Proximity mixing
        proximity_sigma_px: float = 220.0,
        proximity_weight: float = 0.15,

        # Cooldowns
        toggle_cooldown_ms: int = 1300,
        submit_cooldown_ms: int = 1400,

        # Behaviour
        allow_empty_submit: bool = False,

        # Layout tweak: move everything (except submit) down
        layout_shift_down_px: int = 44,
    ):
        super().__init__(parent)

        self.question = question

        # ---- FIX #2: Actually use provided JSON labels ----
        # Accept list/tuple of 5, or a dict-like containing "labels".
        if labels is None:
            # Some codebases accidentally pass the whole item dict as "labels".
            # We'll *try* to recover if labels is embedded somewhere else later, but default stays numeric.
            self.labels = ["1", "2", "3", "4", "5"]
        else:
            # If someone passed the whole JSON item here by mistake, recover:
            if isinstance(labels, dict) and "labels" in labels:
                labels = labels["labels"]  # type: ignore[assignment]

            if isinstance(labels, (list, tuple)) and len(labels) == 5:
                self.labels = [str(l) for l in labels]
            else:
                raise AssertionError("SmoothPursuitLikertWidget requires exactly 5 labels (list of 5 strings).")

        self.window_ms = int(window_ms)
        self.corr_threshold = float(corr_threshold)
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

        # ---- FIX #1: shift all non-submit content downward ----
        self.layout_shift_down_px = max(int(layout_shift_down_px), int(self.height() * 0.06) if self.height() else layout_shift_down_px)

        # Time reference
        self._t0 = time.monotonic()

        # Rolling buffers (time-based)
        self._t: List[float] = []
        self._gx: List[float] = []
        self._gy: List[float] = []
        self._tx: Dict[str, List[float]] = {lab: [] for lab in self.labels}
        self._ty: Dict[str, List[float]] = {lab: [] for lab in self.labels}
        self._sx: List[float] = []
        self._sy: List[float] = []

        # Single-select state
        self.selected: Optional[str] = None

        # Candidate stability (sample-count based)
        self._candidate: Optional[str] = None
        self._candidate_count = 0
        self._submit_count = 0

        # Cooldowns (monotonic seconds)
        self._toggle_block_until = 0.0
        self._submit_block_until = 0.0

        # For UI highlight
        self._last_scores: Dict[str, float] = {lab: 0.0 for lab in self.labels}
        self._last_submit_score: float = 0.0

        # Click logging
        self.click_index: int = 0

        # Animation timer
        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(16)
        self._anim_timer.timeout.connect(self.update)
        self._anim_timer.start()

        # Logging fields expected by MainWindow (keep consistent)
        self.log_toggles = 0
        self.log_resets = 0
        self.log_backspaces = 0
        self.log_extra = f"sp_likert5;labels={self.labels}"

    # ---------------- Motion primitives ----------------

    @staticmethod
    def _circle_pos(cx: float, cy: float, r: float, t: float, freq_hz: float, clockwise: bool):
        omega = 2.0 * math.pi * freq_hz
        ang = omega * t
        s = 1.0 if clockwise else -1.0
        x = cx + r * math.cos(s * ang)
        y = cy + r * math.sin(s * ang)
        return x, y

    @staticmethod
    def _square_pos(cx: float, cy: float, half_side: float, t: float, freq_hz: float, clockwise: bool):
        u = (t * freq_hz) % 1.0
        if not clockwise:
            u = (1.0 - u) % 1.0

        p = u * 4.0
        x0, x1 = cx - half_side, cx + half_side
        y0, y1 = cy - half_side, cy + half_side

        if 0.0 <= p < 1.0:
            x = x0 + (x1 - x0) * p
            y = y0
        elif 1.0 <= p < 2.0:
            q = p - 1.0
            x = x1
            y = y0 + (y1 - y0) * q
        elif 2.0 <= p < 3.0:
            q = p - 2.0
            x = x1 - (x1 - x0) * q
            y = y1
        else:
            q = p - 3.0
            x = x0
            y = y1 - (y1 - y0) * q

        return x, y

    @staticmethod
    def _triangle_pos(cx: float, cy: float, r: float, t: float, freq_hz: float, clockwise: bool):
        v0 = (cx, cy - r)
        v1 = (cx + (math.sqrt(3) / 2.0) * r, cy + 0.5 * r)
        v2 = (cx - (math.sqrt(3) / 2.0) * r, cy + 0.5 * r)

        verts = [v0, v1, v2]
        if not clockwise:
            verts = [v0, v2, v1]

        u = (t * freq_hz) % 1.0
        p = u * 3.0

        def lerp(a, b, s):
            return (a[0] + (b[0] - a[0]) * s, a[1] + (b[1] - a[1]) * s)

        if 0.0 <= p < 1.0:
            return lerp(verts[0], verts[1], p)
        elif 1.0 <= p < 2.0:
            return lerp(verts[1], verts[2], p - 1.0)
        else:
            return lerp(verts[2], verts[0], p - 2.0)

    # ---------------- Layout ----------------

    def _layout(self) -> Tuple[QRect, Dict[str, Tuple[float, float]], Dict[str, Dict[str, float]], QRect, float]:
        w = max(1, self.width())
        h = max(1, self.height())

        # ---------------- shift (robust) ----------------
        # Use a relative shift so it works across resolutions and fullscreen.
        # Clamp to avoid extreme shifts on very small/large screens.
        shift = float(max(self.layout_shift_down_px, int(h * 0.08)))
        shift = float(min(shift, int(h * 0.18)))

        # ---------------- question box (shifted down) ----------------
        q_w = int(w * 0.52)
        q_h = int(h * 0.22)
        qx = (w - q_w) // 2
        qy = int(h * 0.36) - q_h // 2
        question_rect = QRect(qx, int(qy + shift), q_w, q_h)

        # ---------------- orbit sizing ----------------
        base = min(w, h)
        orbit_size = max(240.0, base * self.orbit_scale)

        top_size = orbit_size * 0.75
        mid_size = orbit_size * 0.80

        circle_r_mid = mid_size * 0.45
        circle_r_top = top_size * 0.45
        square_half_top = top_size * 0.45
        square_half_mid = mid_size * 0.45
        tri_r_top = top_size * 0.50

        # "clearance" approximates how far the moving label can reach from its center.
        top_clear = top_size * 0.65
        mid_clear = mid_size * 0.65

        # ---------------- submit (NOT shifted) ----------------
        submit_w = int(max(380, w * 0.28))
        submit_h = int(max(90, h * 0.095))
        submit_y = int(h * 0.88)
        submit_rect = QRect(int(w * 0.5 - submit_w / 2), int(submit_y - submit_h / 2), submit_w, submit_h)

        submit_ax = max(220.0, w * 0.30)

        # ---------------- horizontal placement ----------------
        margin = int(orbit_size * 0.70) + 32

        # Clamp margins so labels don't get pushed too far out on narrow screens
        left_x = float(max(60.0, min(float(margin), w * 0.30)))
        right_x = float(min(float(w - 60), max(float(w - margin), w * 0.70)))
        mid_x = float(w * 0.50)

        # ---------------- vertical placement (clamped) ----------------
        # TOP row must stay on-screen AND above question box.
        top_y_min = top_clear + 20.0
        top_y_max = max(top_y_min, float(question_rect.top()) - top_clear - 18.0)

        # Start from a natural candidate position, then clamp.
        top_y = float(margin) + shift
        top_y = float(max(top_y_min, min(top_y, top_y_max)))

        # MID row should be below question, but also far enough above submit.
        mid_y_min = float(question_rect.bottom()) + mid_clear + 18.0
        # keep it above submit area (minus clearance)
        mid_y_max = float(submit_rect.top()) - mid_clear - 18.0
        # if screen is too small, fall back to a safe fraction
        mid_y_max = max(mid_y_min, min(mid_y_max, float(h * 0.74)))

        mid_y = float(h * 0.62) + shift
        mid_y = float(max(mid_y_min, min(mid_y, mid_y_max)))

        # ---------------- centers & orbit params (per requested mapping) ----------------
        centers = {
            self.labels[0]: (left_x, mid_y),  # Label 1: left-middle
            self.labels[1]: (left_x, top_y),  # Label 2: left-top
            self.labels[2]: (mid_x, top_y),  # Label 3: top-middle
            self.labels[3]: (right_x, top_y),  # Label 4: top-right
            self.labels[4]: (right_x, mid_y),  # Label 5: mid-right
        }

        orbit_params = {
            self.labels[0]: {"type": "circle", "r": circle_r_mid, "clockwise": False},  # 1 circle CCW
            self.labels[1]: {"type": "square", "hs": square_half_top, "clockwise": True},  # 2 square CW
            self.labels[2]: {"type": "triangle", "r": tri_r_top, "clockwise": True},  # 3 triangle CW
            self.labels[3]: {"type": "circle", "r": circle_r_top, "clockwise": False},  # 4 circle CCW
            self.labels[4]: {"type": "square", "hs": square_half_mid, "clockwise": True},  # 5 square CW
        }

        return question_rect, centers, orbit_params, submit_rect, float(submit_ax)

    def _targets_at_time(self, t: float) -> Tuple[Dict[str, Tuple[float, float]], QRect, float]:
        w = max(1, self.width())
        _, centers, orbit_params, submit_rect_base, submit_ax = self._layout()

        pos: Dict[str, Tuple[float, float]] = {}

        for lab in self.labels:
            cx, cy = centers[lab]
            cfg = orbit_params[lab]
            typ = cfg["type"]

            if typ == "circle":
                pos[lab] = self._circle_pos(cx, cy, float(cfg["r"]), t, self.option_frequency_hz, clockwise=bool(cfg["clockwise"]))
            elif typ == "square":
                pos[lab] = self._square_pos(cx, cy, float(cfg["hs"]), t, self.option_frequency_hz, clockwise=bool(cfg["clockwise"]))
            else:
                pos[lab] = self._triangle_pos(cx, cy, float(cfg["r"]), t, self.option_frequency_hz, clockwise=bool(cfg["clockwise"]))

        # SUBMIT horizontal oscillation
        submit_rect = QRect(submit_rect_base)
        omega = 2.0 * math.pi * self.submit_frequency_hz
        submit_cx = (w * 0.5) + submit_ax * math.sin(omega * t)
        submit_rect.moveCenter(QPoint(int(submit_cx), submit_rect.center().y()))

        return pos, submit_rect, float(submit_ax)

    # ---------------- Rolling buffer maintenance ----------------

    def _estimate_max_lag_samples(self) -> int:
        if len(self._t) >= 6:
            dt = float(np.median(np.diff(np.asarray(self._t, dtype=float))))
            if dt <= 1e-6:
                dt = 1.0 / 30.0
        else:
            dt = 1.0 / 30.0

        max_lag_s = max(0.0, self.max_lag_ms / 1000.0)
        return int(round(max_lag_s / dt))

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

    # ---------------- Gaze input ----------------

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
        opt_pos, submit_rect, _ = self._targets_at_time(t)

        sx = float(submit_rect.center().x())
        sy = float(submit_rect.center().y())

        self._t.append(t)
        self._gx.append(float(gx))
        self._gy.append(float(gy))
        for lab in self.labels:
            tx, ty = opt_pos[lab]
            self._tx[lab].append(float(tx))
            self._ty[lab].append(float(ty))
        self._sx.append(sx)
        self._sy.append(sy)

        self._prune_window()
        if len(self._t) < 12:
            return

        self._update_decision()

    # ---------------- Decision logic (corr + proximity) ----------------

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

        corr = 0.5 * (cx + cy)  # [-1,1]

        dist = np.sqrt((gx - tx) ** 2 + (gy - ty) ** 2)
        prox = float(np.mean(gaussian_proximity(dist, self.proximity_sigma_px)))  # 0..1
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

    # ---------------- Actions ----------------

    def _select(self, lab: str) -> None:
        if self.selected != lab:
            self.selected = lab
            self.log_toggles += 1

        self.click_index += 1
        self.clicked.emit(self.click_index, f"select:{lab}")
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

        best_lab = None
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

        ss = self._submit_score()
        self._last_submit_score = ss
        if ss >= self.corr_threshold:
            self._submit_count += 1
        else:
            self._submit_count = 0

        if now >= self._submit_block_until:
            if self._submit_count >= self.submit_stable_samples:
                self._submit_count = 0
                self._candidate = None
                self._candidate_count = 0
                self._submit()
                return

        if now >= self._toggle_block_until:
            if self._candidate is not None and self._candidate_count >= self.toggle_stable_samples:
                lab = self._candidate
                self._candidate = None
                self._candidate_count = 0
                self._select(lab)

    # ---------------- Drawing ----------------

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.fillRect(self.rect(), Qt.black)

        w = max(1, self.width())
        h = max(1, self.height())

        question_rect, _, _, _, _ = self._layout()
        t = time.monotonic() - self._t0
        opt_pos, submit_rect, submit_ax2 = self._targets_at_time(t)

        painter.setPen(Qt.white)
        f = painter.font()
        f.setPointSize(max(16, int(h * 0.028)))
        painter.setFont(f)

        sel_txt = self.selected if self.selected is not None else "-"
        info_rect = QRect(28, 18, w - 56, int(h * 0.13))
        painter.drawText(
            info_rect,
            Qt.AlignLeft | Qt.AlignVCenter | Qt.TextWordWrap,
            "Follow a moving label to SELECT it. Follow SUBMIT to submit.\n"
            f"Selected: {sel_txt}",
        )

        # submit path line
        submit_path_pen = QPen(Qt.gray)
        submit_path_pen.setWidth(3)
        painter.setPen(submit_path_pen)
        y_line = submit_rect.center().y()
        ax = float(submit_ax2)
        painter.drawLine(int(w * 0.5 - ax), int(y_line), int(w * 0.5 + ax), int(y_line))

        # question text
        qfont = painter.font()
        qfont.setPointSize(max(18, int(h * 0.030)))
        qfont.setBold(False)
        painter.setFont(qfont)
        painter.setPen(Qt.white)
        painter.drawText(
            question_rect.adjusted(16, 16, -16, -16),
            Qt.AlignCenter | Qt.TextWordWrap,
            self.question,
        )

        # highlight best candidate
        highlight_opt: Optional[str] = None
        if self._last_scores:
            best = max(self._last_scores, key=self._last_scores.get)
            if self._last_scores.get(best, 0.0) >= self.corr_threshold:
                highlight_opt = best

        for lab in self.labels:
            x, y = opt_pos[lab]
            selected = (lab == self.selected)
            highlight = (lab == highlight_opt)
            self._draw_moving_label(painter, x, y, lab, selected=selected, highlight=highlight)

        self._draw_submit(painter, submit_rect)

        # gaze point
        gx, gy = self.map_gaze_to_widget()
        if gx is not None and gy is not None:
            painter.setPen(Qt.NoPen)
            painter.setBrush(Qt.red)
            r = self.point_radius
            painter.drawEllipse(int(gx) - r, int(gy) - r, 2 * r, 2 * r)

    def _draw_moving_label(self, painter: QPainter, x: float, y: float, text: str, selected: bool, highlight: bool):
        f = painter.font()
        f.setBold(True)
        f.setPointSize(max(28, int(self.height() * 0.045)))  # a tad smaller to fit long German labels
        painter.setFont(f)

        if selected:
            painter.setPen(QPen(Qt.green, 6))
        elif highlight:
            painter.setPen(QPen(Qt.white, 4))
        else:
            painter.setPen(QPen(Qt.white, 3))

        rect = QRect(int(x - 220), int(y - 90), 440, 180)
        painter.drawText(rect, Qt.AlignCenter | Qt.TextWordWrap, text)

    def _draw_submit(self, painter: QPainter, rect: QRect):
        f = painter.font()
        f.setBold(True)
        f.setPointSize(max(22, int(self.height() * 0.038)))
        painter.setFont(f)

        sel_txt = self.selected if self.selected is not None else "-"

        if (not self.allow_empty_submit) and (self.selected is None):
            painter.setPen(QPen(Qt.gray, 3))
        else:
            painter.setPen(QPen(Qt.white, 4))

        painter.drawText(rect, Qt.AlignCenter, f"SUBMIT ({sel_txt})")
