# ui/SmoothPursuit_YesNoWidget.py
#
# - Rolling window buffers (window_ms)
# - Proximity-boost + rolling correlation (XY for options, X-only for SUBMIT)
# - Stable decisions are SAMPLE-count based (toggle_stable_samples / submit_stable_samples)
# - Cooldowns in ms
# - No circles/frames around moving texts; only text moves
# - Question box sized like MCQ (smaller)
# - submitted(...) emits ONLY the choice string (like normal Yes/No): "yes" or "no"
# - clicked(...) emits "select:yes"/"select:no"/"submit" for CSV logging

from __future__ import annotations

import math
import time
from typing import Dict, List, Optional, Tuple

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
    """
    Returns the maximum Pearson correlation between a and b over integer sample lags
    in [-max_lag_samples, +max_lag_samples].
    Positive lag means: a is shifted forward relative to b (a[k:] vs b[:-k]).
    """
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


class SmoothPursuitYesNoWidget(GazeWidget):
    """
    Smooth Pursuit Yes/No with separate SUBMIT (MCQ-like UX).

    - YES and NO are moving TEXT labels.
    - Following YES/NO stably selects that choice (single-select).
    - Following SUBMIT stably submits current selection.

    Signals:
      submitted(object): emits ONLY "yes" or "no" (string)
      clicked(int, str): emits "select:yes", "select:no", "submit"
    """

    submitted = Signal(object)
    clicked = Signal(int, str)

    def __init__(
        self,
        question: str,
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

        # Visual params / layout
        orbit_scale: float = 0.36,

        # Proximity mixing
        proximity_sigma_px: float = 220.0,
        proximity_weight: float = 0.15,

        # Cooldowns
        toggle_cooldown_ms: int = 1300,
        submit_cooldown_ms: int = 1400,

        # Behaviour
        allow_empty_submit: bool = False,
        labels: Optional[List[str]] = None,  # ["yes","no"] optionally
    ):
        super().__init__(parent)

        self.question = question
        if labels is None:
            self.labels = ["yes", "no"]
        else:
            assert len(labels) == 2, "SmoothPursuitYesNoWidget requires exactly 2 labels."
            self.labels = list(labels)

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

        # Candidate stability (sample-count based, like MCQ)
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
        self.log_extra = "sp_yesno"

    # ---------------- Motion primitives ----------------

    @staticmethod
    def _rect_path_pos(
        cx: float,
        cy: float,
        half_w: float,
        half_h: float,
        t: float,
        freq_hz: float,
        clockwise: bool,
    ):
        """
        Axis-aligned rectangle path along edges, like MCQ square path.

        clockwise=True  => CW
        clockwise=False => CCW
        """
        u = (t * freq_hz) % 1.0
        if not clockwise:
            u = (1.0 - u) % 1.0

        p = u * 4.0
        x0, x1 = cx - half_w, cx + half_w
        y0, y1 = cy - half_h, cy + half_h

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

    # In SmoothPursuitYesNoWidget._layout(), move the YES/NO centers a bit higher.

    def _layout(self) -> Tuple[QRect, Dict[str, Tuple[float, float]], Dict[str, Dict[str, float]], QRect, float]:
        w = max(1, self.width())
        h = max(1, self.height())

        # Smaller center question box (match MCQ sizing)
        q_w = int(w * 0.52)
        q_h = int(h * 0.22)
        qx = (w - q_w) // 2
        qy = int(h * 0.36) - q_h // 2
        question_rect = QRect(qx, qy, q_w, q_h)

        base = min(w, h)
        orbit_size = max(260.0, base * self.orbit_scale)
        half_w = orbit_size * 0.50
        half_h = orbit_size * 0.60

        margin = int(orbit_size * 0.72) + 32

        # WAS: mid_y = float(h * 0.60)
        # NOW: slightly higher
        mid_y = float(h * 0.54)

        left_x = float(margin)
        right_x = float(w - margin)

        centers = {
            self.labels[0]: (left_x, mid_y),  # yes (left)
            self.labels[1]: (right_x, mid_y),  # no  (right)
        }

        orbit_params = {
            self.labels[0]: {"half_w": half_w, "half_h": half_h},
            self.labels[1]: {"half_w": half_w, "half_h": half_h},
        }

        # Submit button (same approach as MCQ)
        submit_w = int(max(380, w * 0.28))
        submit_h = int(max(90, h * 0.095))
        submit_y = int(h * 0.88)
        submit_rect = QRect(int(w * 0.5 - submit_w / 2), int(submit_y - submit_h / 2), submit_w, submit_h)

        submit_ax = max(220.0, w * 0.30)
        return question_rect, centers, orbit_params, submit_rect, float(submit_ax)

    def _targets_at_time(self, t: float) -> Tuple[Dict[str, Tuple[float, float]], QRect, float]:
        w = max(1, self.width())
        _, centers, orbit_params, submit_rect_base, submit_ax = self._layout()

        pos: Dict[str, Tuple[float, float]] = {}

        # YES (left): rectangle CCW
        cx, cy = centers[self.labels[0]]
        hw = orbit_params[self.labels[0]]["half_w"]
        hh = orbit_params[self.labels[0]]["half_h"]
        pos[self.labels[0]] = self._rect_path_pos(cx, cy, hw, hh, t, self.option_frequency_hz, clockwise=False)

        # NO (right): rectangle CW
        cx, cy = centers[self.labels[1]]
        hw = orbit_params[self.labels[1]]["half_w"]
        hh = orbit_params[self.labels[1]]["half_h"]
        pos[self.labels[1]] = self._rect_path_pos(cx, cy, hw, hh, t, self.option_frequency_hz, clockwise=True)

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

        # correlation (XY)
        if self.use_lag_compensation:
            max_lag_samples = self._estimate_max_lag_samples()
            cx = max_lagged_pearson_corr(gx, tx, max_lag_samples)
            cy = max_lagged_pearson_corr(gy, ty, max_lag_samples)
        else:
            cx = pearson_corr(gx, tx)
            cy = pearson_corr(gy, ty)

        corr = 0.5 * (cx + cy)  # [-1,1]

        # proximity (window-mean), mapped to [-1,1]
        dist = np.sqrt((gx - tx) ** 2 + (gy - ty) ** 2)
        prox = float(np.mean(gaussian_proximity(dist, self.proximity_sigma_px)))  # 0..1
        prox_mapped = (2.0 * prox) - 1.0

        return float((self.corr_weight * corr) + (self.proximity_weight * prox_mapped))

    def _submit_score(self) -> float:
        """
        SUBMIT moves in X only => use X correlation only, plus proximity.
        """
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

    def _select(self, choice: str) -> None:
        # single-select (set)
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

        # IMPORTANT: emit ONLY choice string for consistent logging
        self.submitted.emit(self.selected if self.selected is not None else "")

    def _update_decision(self) -> None:
        now = self._now()

        # option scores
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

        # submit score
        ss = self._submit_score()
        self._last_submit_score = ss
        if ss >= self.corr_threshold:
            self._submit_count += 1
        else:
            self._submit_count = 0

        # submit first
        if now >= self._submit_block_until:
            if self._submit_count >= self.submit_stable_samples:
                self._submit_count = 0
                self._candidate = None
                self._candidate_count = 0
                self._submit()
                return

        # select
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

        question_rect, centers, orbit_params, _, _ = self._layout()
        t = time.monotonic() - self._t0
        opt_pos, submit_rect, submit_ax2 = self._targets_at_time(t)

        # instructions
        painter.setPen(Qt.white)
        f = painter.font()
        f.setPointSize(max(16, int(h * 0.028)))
        painter.setFont(f)

        sel_txt = (self.selected.upper() if self.selected else "-")
        info_rect = QRect(28, 18, w - 56, int(h * 0.13))
        painter.drawText(
            info_rect,
            Qt.AlignLeft | Qt.AlignVCenter | Qt.TextWordWrap,
            "Follow YES/NO to SELECT. Follow SUBMIT to submit.\n"
            f"Selected: {sel_txt}",
        )

        # submit path line (match MCQ)
        submit_path_pen = QPen(Qt.gray)
        submit_path_pen.setWidth(3)
        painter.setPen(submit_path_pen)
        y_line = submit_rect.center().y()
        ax = float(submit_ax2)
        painter.drawLine(int(w * 0.5 - ax), int(y_line), int(w * 0.5 + ax), int(y_line))

        # question box text (no frame)
        qfont = painter.font()
        qfont.setPointSize(max(18, int(h * 0.030)))
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

        # draw ONLY moving texts (no circles)
        # Map labels to display text
        disp = {
            self.labels[0]: "YES" if self.labels[0].lower() == "yes" else str(self.labels[0]).upper(),
            self.labels[1]: "NO" if self.labels[1].lower() == "no" else str(self.labels[1]).upper(),
        }

        for lab in self.labels:
            x, y = opt_pos[lab]
            selected = (lab == self.selected)
            highlight = (lab == highlight_opt)
            self._draw_moving_label(painter, x, y, disp.get(lab, str(lab)), selected=selected, highlight=highlight)

        # submit rect
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
        f.setPointSize(max(30, int(self.height() * 0.050)))
        painter.setFont(f)

        if selected:
            painter.setPen(QPen(Qt.green, 6))
        elif highlight:
            painter.setPen(QPen(Qt.white, 4))
        else:
            painter.setPen(QPen(Qt.white, 3))

        rect = QRect(int(x - 120), int(y - 60), 240, 120)
        painter.drawText(rect, Qt.AlignCenter, text)

    def _draw_submit(self, painter: QPainter, rect: QRect):
        f = painter.font()
        f.setBold(True)
        f.setPointSize(max(22, int(self.height() * 0.038)))
        painter.setFont(f)

        sel_txt = (self.selected.upper() if self.selected else "-")

        if (not self.allow_empty_submit) and (self.selected is None):
            painter.setPen(QPen(Qt.gray, 3))
        else:
            painter.setPen(QPen(Qt.white, 4))

        painter.drawText(rect, Qt.AlignCenter, f"SUBMIT ({sel_txt})")
