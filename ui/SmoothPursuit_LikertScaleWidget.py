# ui/SmoothPursuit_LikertWidget.py
# Smooth Pursuit Likert Scale Widget with 5 options

from __future__ import annotations

import math
import time
from typing import Dict, List, Optional, Tuple

import numpy as np
from PySide6.QtCore import Qt, QRect, QTimer, Slot, Signal, QPoint
from PySide6.QtGui import QPainter, QPen, QPolygon
from PySide6.QtWidgets import QApplication

from ui.gaze_widget import GazeWidget


def pearson_corr(a: np.ndarray, b: np.ndarray) -> float:
    """
    Compute the Pearson correlation coefficient between two 1D signals.

    The function:
    - Converts inputs to float NumPy arrays
    - Aligns signals by trimming to equal length (keeping most recent samples)
    - Mean-centers both signals
    - Returns the normalized dot product (Pearson's r)

    If either signal has fewer than 3 samples, or if either has (near) zero
    variance, the function returns 0.0.

    Parameters
    ----------
    a : np.ndarray
        First input signal (1D array-like).
    b : np.ndarray
        Second input signal (1D array-like).

    Returns
    -------
    float
        Pearson correlation coefficient in [-1.0, 1.0], or 0.0 if undefined.
    """
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
    Compute the maximum Pearson correlation between two 1D signals over a lag range.

    Pearson correlations are evaluated for integer sample lags in
    [-max_lag_samples, +max_lag_samples], and the maximum value is returned.

    Positive lag means that signal `a` is shifted forward relative to `b`
    (i.e., `a[k:]` vs `b[:-k]`). Negative lag shifts `a` backward.

    Parameters
    ----------
    a : np.ndarray
        First input signal (1D array-like).
    b : np.ndarray
        Second input signal (1D array-like).
    max_lag_samples : int
        Maximum lag in samples to search in both directions.

    Returns
    -------
    float
        Maximum Pearson correlation across tested lags in [-1.0, 1.0].
        Returns 0.0 if correlation is undefined or if overlap is insufficient.

    Notes
    -----
    - Uses `None` to represent “no valid overlap,” avoiding edge cases where a true
      best correlation of -1.0 could be mistaken for “no result.”
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
    """
    Compute Gaussian proximity weights from distances.

    Parameters
    ----------
    dist : np.ndarray
        Non-negative distances (e.g., Euclidean pixels).
    sigma : float
        Standard deviation of the Gaussian kernel (minimum 1.0 enforced).

    Returns
    -------
    np.ndarray
        Proximity weights in (0, 1], computed as exp(-d^2 / (2*sigma^2)).
    """
    sigma = max(1.0, float(sigma))
    return np.exp(-(dist * dist) / (2.0 * sigma * sigma))


class SmoothPursuitLikertScaleWidget(GazeWidget):
    """
    Smooth Pursuit Likert Scale (5 options) with separate SUBMIT (single-select UX).

    UI/Behavior
    -----------
    - Five moving option targets (each option has a moving DOT stimulus and a static label).
    - Following an option's moving DOT stably selects that option (single-select).
    - Following the SUBMIT moving DOT stably submits the current selection.

    Decision Signal Model
    ---------------------
    Evidence per option is computed from:
    - correlation between gaze and target motion (X and Y, averaged),
    - plus a spatial proximity term (Gaussian of gaze-to-target distance),
    mixed as: score = corr_weight * corr + proximity_weight * prox_mapped.

    Signals
    -------
    submitted(object):
        Emits ONLY the selected label string (e.g., "3") or "" if empty submit allowed.
    clicked(int, str):
        Emits "select:<label>" or "submit" for click logging.
    """

    submitted = Signal(object)
    clicked = Signal(int, str)

    def __init__(
        self,
        question: str,
        labels: Optional[List[str]] = None,
        parent=None,
        window_ms: int = 1250,
        corr_threshold: float = 0.73,
        toggle_stable_samples: int = 18,
        submit_stable_samples: int = 20,
        use_lag_compensation: bool = True,
        max_lag_ms: int = 180,
        option_frequency_hz: float = 0.25,
        submit_frequency_hz: float = 0.28,
        orbit_scale: float = 0.34,
        proximity_sigma_px: float = 220.0,
        proximity_weight: float = 0.15,
        toggle_cooldown_ms: int = 1300,
        submit_cooldown_ms: int = 1400,
        allow_empty_submit: bool = False,
        layout_shift_down_px: int = 44,
    ):
        """
        Initialize a smooth pursuit Likert (5-point) widget.

        Parameters
        ----------
        question : str
            Question text displayed in the center of the widget.
        labels : list[str] or dict, optional
            Custom labels for the 5 options. Accepts:
            - list/tuple of length 5
            - dict with key "labels" containing a list/tuple of length 5
            Defaults to ["1","2","3","4","5"].
        parent : QWidget, optional
            Parent Qt widget.

        window_ms : int, default=1250
            Rolling time window (ms) used for correlation/proximity computation.
        corr_threshold : float, default=0.73
            Minimum combined score for an option to be considered as a candidate.
        toggle_stable_samples : int, default=18
            Consecutive samples required to select an option.
        submit_stable_samples : int, default=20
            Consecutive samples required to trigger submission.
        use_lag_compensation : bool, default=True
            If True, correlation is maximized over a lag range to compensate latency.
        max_lag_ms : int, default=180
            Maximum lag window (ms) used for lag-compensated correlation.

        option_frequency_hz : float, default=0.25
            Motion frequency (Hz) for option targets.
        submit_frequency_hz : float, default=0.28
            Horizontal oscillation frequency (Hz) for SUBMIT target dot.
        orbit_scale : float, default=0.34
            Relative scaling factor for orbit sizes.
        proximity_sigma_px : float, default=220.0
            Sigma (px) for Gaussian proximity term.
        proximity_weight : float, default=0.15
            Weight of proximity term in combined score (0..1).
        toggle_cooldown_ms : int, default=1300
            Cooldown (ms) after selecting during which selection changes are blocked.
        submit_cooldown_ms : int, default=1400
            Cooldown (ms) after submitting during which resubmission is blocked.
        allow_empty_submit : bool, default=False
            If False, SUBMIT is disabled until an option is selected.
        layout_shift_down_px : int, default=44
            Vertical shift applied to option layout (question/options) but not submit.

        Notes
        -----
        - Option selection uses XY correlation; submission uses X-only correlation
          because the SUBMIT dot moves horizontally.
        - Stability checks are sample-count based.
        """
        super().__init__(parent)

        self.question = question

        if labels is None:
            self.labels = ["1", "2", "3", "4", "5"]
        else:
            if isinstance(labels, dict) and "labels" in labels:
                labels = labels["labels"]  # type: ignore[assignment]
            if isinstance(labels, (list, tuple)) and len(labels) == 5:
                self.labels = [str(l) for l in labels]
            else:
                raise AssertionError("SmoothPursuitLikertWidget requires exactly 5 labels (list of 5 strings).")

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

        base_shift = int(self.height() * 0.06) if self.height() else int(layout_shift_down_px)
        self.layout_shift_down_px = max(int(layout_shift_down_px), base_shift)

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

        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(16)
        self._anim_timer.timeout.connect(self.update)
        self._anim_timer.start()

        self.log_toggles = 0
        self.log_resets = 0
        self.log_backspaces = 0
        self.log_extra = f"sp_likert5;labels={self.labels}"

    @staticmethod
    def _circle_pos(cx: float, cy: float, r: float, t: float, freq_hz: float, clockwise: bool) -> Tuple[float, float]:
        """
        Compute a point moving on a circle.

        Parameters
        ----------
        cx, cy : float
            Center of the circle.
        r : float
            Radius in pixels.
        t : float
            Time in seconds since motion start.
        freq_hz : float
            Motion frequency in Hertz.
        clockwise : bool
            If True, rotate clockwise; otherwise counterclockwise.

        Returns
        -------
        (float, float)
            Current (x, y) position.
        """
        omega = 2.0 * math.pi * freq_hz
        ang = omega * t
        s = 1.0 if clockwise else -1.0
        x = cx + r * math.cos(s * ang)
        y = cy + r * math.sin(s * ang)
        return x, y

    @staticmethod
    def _square_pos(
        cx: float, cy: float, half_side: float, t: float, freq_hz: float, clockwise: bool
    ) -> Tuple[float, float]:
        """
        Compute a point moving along the perimeter of an axis-aligned square.

        Parameters
        ----------
        cx, cy : float
            Square center.
        half_side : float
            Half side length (pixels).
        t : float
            Time in seconds since motion start.
        freq_hz : float
            Motion frequency in Hertz.
        clockwise : bool
            If True, traverse clockwise; otherwise counterclockwise.

        Returns
        -------
        (float, float)
            Current (x, y) position on the square perimeter.
        """
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
    def _triangle_pos(cx: float, cy: float, r: float, t: float, freq_hz: float, clockwise: bool) -> Tuple[float, float]:
        """
        Compute a point moving along an equilateral triangle perimeter.

        Parameters
        ----------
        cx, cy : float
            Triangle center.
        r : float
            Radius-like scale for triangle size.
        t : float
            Time in seconds since motion start.
        freq_hz : float
            Motion frequency in Hertz.
        clockwise : bool
            If True, traverse vertices in one order; otherwise reversed.

        Returns
        -------
        (float, float)
            Current (x, y) position on the triangle perimeter.
        """
        v0 = (cx, cy - r)
        v1 = (cx + (math.sqrt(3) / 2.0) * r, cy + 0.5 * r)
        v2 = (cx - (math.sqrt(3) / 2.0) * r, cy + 0.5 * r)

        if clockwise:
            verts = [v0, v1, v2]
        else:
            verts = [v0, v2, v1]

        u = (t * freq_hz) % 1.0
        p = u * 3.0

        def lerp(a: Tuple[float, float], b: Tuple[float, float], s: float) -> Tuple[float, float]:
            return (a[0] + (b[0] - a[0]) * s, a[1] + (b[1] - a[1]) * s)

        if 0.0 <= p < 1.0:
            return lerp(verts[0], verts[1], p)
        if 1.0 <= p < 2.0:
            return lerp(verts[1], verts[2], p - 1.0)
        return lerp(verts[2], verts[0], p - 2.0)

    def _layout(self) -> Tuple[QRect, Dict[str, Tuple[float, float]], Dict[str, Dict[str, float]], QRect, float]:
        """
        Compute geometry for the Likert widget.

        Returns
        -------
        question_rect : QRect
            Rectangle for the question text (shifted down).
        centers : dict[str, (float, float)]
            Orbit centers for the 5 labels.
        orbit_params : dict[str, dict[str, float]]
            Per-label motion configuration, containing:
            - "type": "circle" | "square" | "triangle"
            - "r" or "hs" for size
            - "clockwise": bool
        submit_rect : QRect
            Static SUBMIT text rectangle (not shifted).
        submit_ax : float
            Horizontal oscillation amplitude (pixels) for the SUBMIT dot.

        Notes
        -----
        - Applies a robust vertical shift to option layout to avoid crowding.
        - Centers are clamped so that orbits remain within the screen and do not
          overlap the question or submit regions excessively.
        """
        w = max(1, self.width())
        h = max(1, self.height())

        shift = float(max(self.layout_shift_down_px, int(h * 0.08)))
        shift = float(min(shift, int(h * 0.18)))

        q_w = int(w * 0.52)
        q_h = int(h * 0.22)
        qx = (w - q_w) // 2
        qy = int(h * 0.36) - q_h // 2
        question_rect = QRect(qx, int(qy + shift), q_w, q_h)

        base = min(w, h)
        orbit_size = max(240.0, base * self.orbit_scale)

        top_size = orbit_size * 0.75
        mid_size = orbit_size * 0.80

        circle_r_mid = mid_size * 0.45
        circle_r_top = top_size * 0.45
        square_half_top = top_size * 0.45
        square_half_mid = mid_size * 0.45
        tri_r_top = top_size * 0.50

        top_clear = top_size * 0.65
        mid_clear = mid_size * 0.65

        submit_w = int(max(700, w * 0.50))
        submit_h = int(max(105, h * 0.11))
        submit_y = int(h * 0.88)
        submit_rect = QRect(int(w * 0.5 - submit_w / 2), int(submit_y - submit_h / 2), submit_w, submit_h)

        submit_ax = max(220.0, w * 0.30)

        margin = int(orbit_size * 0.70) + 32

        left_x = float(max(60.0, min(float(margin), w * 0.30)))
        right_x = float(min(float(w - 60), max(float(w - margin), w * 0.70)))
        mid_x = float(w * 0.50)

        top_y_min = top_clear + 20.0
        top_y_max = max(top_y_min, float(question_rect.top()) - top_clear - 18.0)
        top_y = float(margin) + shift
        top_y = float(max(top_y_min, min(top_y, top_y_max)))

        mid_y_min = float(question_rect.bottom()) + mid_clear + 18.0
        mid_y_max = float(submit_rect.top()) - mid_clear - 18.0
        mid_y_max = max(mid_y_min, min(mid_y_max, float(h * 0.74)))
        mid_y = float(h * 0.62) + shift
        mid_y = float(max(mid_y_min, min(mid_y, mid_y_max)))

        centers = {
            self.labels[0]: (left_x, mid_y),
            self.labels[1]: (left_x, top_y),
            self.labels[2]: (mid_x, top_y),
            self.labels[3]: (right_x, top_y),
            self.labels[4]: (right_x, mid_y),
        }

        orbit_params: Dict[str, Dict[str, float]] = {
            self.labels[0]: {"type": "circle", "r": circle_r_mid, "clockwise": 0.0},
            self.labels[1]: {"type": "square", "hs": square_half_top, "clockwise": 1.0},
            self.labels[2]: {"type": "triangle", "r": tri_r_top, "clockwise": 1.0},
            self.labels[3]: {"type": "circle", "r": circle_r_top, "clockwise": 0.0},
            self.labels[4]: {"type": "square", "hs": square_half_mid, "clockwise": 1.0},
        }

        return question_rect, centers, orbit_params, submit_rect, float(submit_ax)

    def _targets_at_time(self, t: float) -> Tuple[Dict[str, Tuple[float, float]], QRect, Tuple[float, float], float]:
        """
        Compute the instantaneous positions of all moving targets at time `t`.

        Parameters
        ----------
        t : float
            Time in seconds since widget initialization.

        Returns
        -------
        pos : dict[str, (float, float)]
            Current positions of each option's moving dot target.
        submit_rect : QRect
            Static rectangle for SUBMIT text.
        submit_dot : (float, float)
            Current (x, y) position of the moving SUBMIT dot target.
        submit_ax : float
            Horizontal oscillation amplitude used for SUBMIT dot.

        Notes
        -----
        - Option dots follow their configured orbit type (circle/square/triangle).
        - SUBMIT dot oscillates horizontally; y-position is slightly offset downward
          for visual alignment with the submit text area.
        """
        w = max(1, self.width())
        _, centers, orbit_params, submit_rect, submit_ax = self._layout()

        pos: Dict[str, Tuple[float, float]] = {}
        for lab in self.labels:
            cx, cy = centers[lab]
            cfg = orbit_params[lab]
            typ = str(cfg["type"])
            clockwise = bool(int(cfg.get("clockwise", 1.0)))

            if typ == "circle":
                pos[lab] = self._circle_pos(cx, cy, float(cfg["r"]), t, self.option_frequency_hz, clockwise=clockwise)
            elif typ == "square":
                pos[lab] = self._square_pos(cx, cy, float(cfg["hs"]), t, self.option_frequency_hz, clockwise=clockwise)
            else:
                pos[lab] = self._triangle_pos(cx, cy, float(cfg["r"]), t, self.option_frequency_hz, clockwise=clockwise)

        omega = 2.0 * math.pi * self.submit_frequency_hz
        submit_dot_x = (w * 0.5) + submit_ax * math.sin(omega * t)
        submit_dot_y = float(submit_rect.center().y() + int(self.height() * 0.03))

        return pos, submit_rect, (float(submit_dot_x), float(submit_dot_y)), float(submit_ax)

    def _estimate_max_lag_samples(self) -> int:
        """
        Estimate the number of samples corresponding to `max_lag_ms`.

        The sampling interval is estimated using the median of differences between
        recent timestamps in the rolling buffer. If insufficient samples exist,
        falls back to 30 Hz.

        Returns
        -------
        int
            Maximum lag in samples for lag-compensated correlation.
        """
        if len(self._t) >= 6:
            dt = float(np.median(np.diff(np.asarray(self._t, dtype=float))))
            if dt <= 1e-6:
                dt = 1.0 / 30.0
        else:
            dt = 1.0 / 30.0

        max_lag_s = max(0.0, self.max_lag_ms / 1000.0)
        return int(round(max_lag_s / dt))

    def _prune_window(self) -> None:
        """
        Prune rolling buffers to keep only the most recent `window_ms` milliseconds.

        Returns
        -------
        None

        Notes
        -----
        - Buffers are pruned synchronously to preserve index alignment across time,
          gaze, option targets, and submit targets.
        """
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
        """
        Return current monotonic time in seconds.

        Returns
        -------
        float
            Monotonic timestamp suitable for cooldown tracking.
        """
        return time.monotonic()

    @Slot(float, float)
    def set_gaze(self, x: float, y: float):
        """
        Receive a gaze sample, update rolling buffers, and update decisions.

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
        - If gaze cannot be mapped into widget coordinates, decision counters reset.
        - Target positions are sampled at the same timestamp for alignment.
        - Requires a minimum number of samples (12) before decision logic runs.
        """
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

    def _option_score(self, lab: str) -> float:
        """
        Compute the combined smooth pursuit score for an option label.

        Parameters
        ----------
        lab : str
            The option label whose score is computed.

        Returns
        -------
        float
            Combined score in [-1.0, 1.0]. Higher means stronger evidence of following.

        Notes
        -----
        - Uses XY correlation (averaged) plus proximity term.
        - If lag compensation is enabled, uses max correlation over a lag range.
        """
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
        """
        Compute the combined smooth pursuit score for the SUBMIT target.

        Returns
        -------
        float
            Combined score in [-1.0, 1.0].

        Notes
        -----
        - Uses X-only correlation (SUBMIT dot moves horizontally) plus proximity term.
        - If lag compensation is enabled, uses max correlation over a lag range.
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

    def _select(self, lab: str) -> None:
        """
        Select a Likert option (single-select) and emit logging signals.

        Parameters
        ----------
        lab : str
            The label to select.

        Returns
        -------
        None

        Notes
        -----
        - Updates `self.selected` only if the selection changes.
        - Emits clicked(..., "select:<lab>") for logging.
        - Starts a selection cooldown to prevent rapid re-selection.
        """
        if self.selected != lab:
            self.selected = lab
            self.log_toggles += 1

        self.click_index += 1
        self.clicked.emit(self.click_index, f"select:{lab}")
        QApplication.beep()

        self._toggle_block_until = self._now() + (self.toggle_cooldown_ms / 1000.0)

    def _submit(self) -> None:
        """
        Submit the current selection.

        Returns
        -------
        None

        Notes
        -----
        - If empty submission is not allowed and there is no selection, returns.
        - Emits clicked(..., "submit") and submitted(<label or "">).
        - Starts a submit cooldown to prevent repeated submissions.
        """
        if (not self.allow_empty_submit) and (self.selected is None):
            return

        self.click_index += 1
        self.clicked.emit(self.click_index, "submit")
        QApplication.beep()

        self._submit_block_until = self._now() + (self.submit_cooldown_ms / 1000.0)

        self.submitted.emit(self.selected if self.selected is not None else "")

    def _update_decision(self) -> None:
        """
        Update selection and submission decisions from rolling-window evidence.

        Returns
        -------
        None

        Notes
        -----
        - Computes option scores, picks best-above-threshold as candidate, and
          requires stability for `toggle_stable_samples` to select.
        - Computes submit score and requires stability for `submit_stable_samples`
          to submit.
        - Submission is evaluated before selection.
        - Cooldowns block triggers for short periods after actions.
        """
        now = self._now()

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

        ss = self._submit_score()
        self._last_submit_score = ss
        if ss >= self.submit_corr_threshold:
            self._submit_count += 1
        else:
            self._submit_count = 0

        if now >= self._submit_block_until and self._submit_count >= self.submit_stable_samples:
            self._submit_count = 0
            self._candidate = None
            self._candidate_count = 0
            self._submit()
            return

        if now >= self._toggle_block_until and self._candidate is not None and self._candidate_count >= self.toggle_stable_samples:
            lab = self._candidate
            self._candidate = None
            self._candidate_count = 0
            self._select(lab)

    def paintEvent(self, event):
        """
        Render the complete visual state of the Likert smooth pursuit widget.

        This method draws:
        - background and instructions,
        - question text,
        - orbit outlines for each option,
        - static labels and moving dot targets,
        - SUBMIT text and its moving dot target (plus guide line),
        - current gaze point (red).

        Parameters
        ----------
        event : QPaintEvent
            Qt paint event (required signature; unused).

        Returns
        -------
        None
        """
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.Antialiasing, True)
            painter.fillRect(self.rect(), Qt.black)

            w = max(1, self.width())
            h = max(1, self.height())

            question_rect, centers, orbit_params, _, _ = self._layout()
            t = time.monotonic() - self._t0
            opt_pos, submit_rect, submit_dot, submit_ax2 = self._targets_at_time(t)

            painter.setPen(Qt.white)
            f = painter.font()
            f.setPointSize(max(16, int(h * 0.028)))
            painter.setFont(f)

            sel_txt = self.selected if self.selected is not None else "-"
            info_rect = QRect(28, 18, w - 56, int(h * 0.13))
            painter.drawText(
                info_rect,
                Qt.AlignLeft | Qt.AlignVCenter | Qt.TextWordWrap,
                "Follow the moving DOT to SELECT an option. Follow SUBMIT to submit.\n"
                f"Selected: {sel_txt}",
            )

            submit_path_pen = QPen(Qt.gray)
            submit_path_pen.setWidth(3)
            painter.setPen(submit_path_pen)
            y_line = submit_rect.center().y() + int(h * 0.03)
            ax = float(submit_ax2)
            painter.drawLine(int(w * 0.5 - ax), int(y_line), int(w * 0.5 + ax), int(y_line))

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

            highlight_opt: Optional[str] = None
            if self._last_scores:
                best = max(self._last_scores, key=self._last_scores.get)
                if self._last_scores.get(best, 0.0) >= self.corr_threshold:
                    highlight_opt = best

            orbit_pen = QPen(Qt.gray)
            orbit_pen.setWidth(2)
            painter.setPen(orbit_pen)
            painter.setBrush(Qt.NoBrush)

            for lab in self.labels:
                cx, cy = centers[lab]
                cfg = orbit_params[lab]
                self._draw_orbit_path(painter, cx, cy, cfg)

            for lab in self.labels:
                cx, cy = centers[lab]
                selected = (lab == self.selected)
                highlight = (lab == highlight_opt)

                self._draw_static_label(painter, cx, cy, lab, selected=selected, highlight=highlight)

                x, y = opt_pos[lab]
                self._draw_target_dot(painter, x, y, selected=selected, highlight=highlight)

            self._draw_submit(painter, submit_rect, submit_dot)

            gx, gy = self.map_gaze_to_widget()
            if gx is not None and gy is not None:
                painter.setPen(Qt.NoPen)
                painter.setBrush(Qt.red)
                r = self.point_radius
                painter.drawEllipse(int(gx) - r, int(gy) - r, 2 * r, 2 * r)

        finally:
            painter.end()

    def _draw_static_label(self, painter: QPainter, cx: float, cy: float, text: str, selected: bool, highlight: bool):
        """
        Draw a static (non-moving) label centered at (cx, cy).

        Parameters
        ----------
        painter : QPainter
            Active Qt painter.
        cx, cy : float
            Label center position.
        text : str
            Label text to render.
        selected : bool
            If True, draw as selected (green).
        highlight : bool
            If True, draw as current best candidate (thicker white).

        Returns
        -------
        None
        """
        f = painter.font()
        f.setPointSize(max(24, int(self.height() * 0.038)))
        painter.setFont(f)

        if selected:
            painter.setPen(QPen(Qt.green, 6))
        elif highlight:
            painter.setPen(QPen(Qt.white, 4))
        else:
            painter.setPen(QPen(Qt.white, 3))

        rect = QRect(int(cx - 220), int(cy - 90), 440, 180)
        painter.drawText(rect, Qt.AlignCenter | Qt.TextWordWrap, text)

    def _draw_target_dot(self, painter: QPainter, x: float, y: float, selected: bool, highlight: bool):
        """
        Draw a moving target dot at (x, y).

        Parameters
        ----------
        painter : QPainter
            Active Qt painter.
        x, y : float
            Dot center position.
        selected : bool
            If True, draw as selected (green, larger).
        highlight : bool
            If True, draw as highlighted candidate (slightly larger).

        Returns
        -------
        None
        """
        painter.setPen(Qt.NoPen)

        if selected:
            painter.setBrush(Qt.green)
            r = max(10, int(self.height() * 0.018))
        elif highlight:
            painter.setBrush(Qt.white)
            r = max(9, int(self.height() * 0.016))
        else:
            painter.setBrush(Qt.white)
            r = max(8, int(self.height() * 0.014))

        painter.drawEllipse(int(x) - r, int(y) - r, 2 * r, 2 * r)

    def _draw_orbit_path(self, painter: QPainter, cx: float, cy: float, cfg: Dict[str, float]) -> None:
        """
        Draw the orbit outline for an option.

        Parameters
        ----------
        painter : QPainter
            Active Qt painter.
        cx, cy : float
            Orbit center.
        cfg : dict[str, float]
            Orbit configuration, containing:
            - type: "circle" | "square" | "triangle"
            - r or hs as size parameters

        Returns
        -------
        None
        """
        typ = str(cfg["type"])
        if typ == "circle":
            r = float(cfg["r"])
            painter.drawEllipse(QPoint(int(cx), int(cy)), int(r), int(r))
        elif typ == "square":
            hs = float(cfg["hs"])
            painter.drawRect(QRect(int(cx - hs), int(cy - hs), int(2 * hs), int(2 * hs)))
        else:
            r = float(cfg["r"])
            v0 = QPoint(int(cx), int(cy - r))
            v1 = QPoint(int(cx + (math.sqrt(3) / 2.0) * r), int(cy + 0.5 * r))
            v2 = QPoint(int(cx - (math.sqrt(3) / 2.0) * r), int(cy + 0.5 * r))
            painter.drawPolygon(QPolygon([v0, v1, v2]))

    def _draw_submit(self, painter: QPainter, rect: QRect, dot: Tuple[float, float]):
        """
        Draw the SUBMIT UI: static text plus a moving target dot.

        Parameters
        ----------
        painter : QPainter
            Active Qt painter.
        rect : QRect
            Static rectangle for SUBMIT text.
        dot : (float, float)
            Current (x, y) position of the moving SUBMIT dot.

        Returns
        -------
        None

        Notes
        -----
        - If submission is disabled (no selection and allow_empty_submit=False),
          the text and dot are gray.
        - If submit evidence is strong, the dot is slightly enlarged.
        """
        f = painter.font()
        f.setBold(True)
        f.setPointSize(max(22, int(self.height() * 0.038)))
        painter.setFont(f)

        sel_txt = self.selected if self.selected is not None else "-"
        enabled = (self.allow_empty_submit or (self.selected is not None))

        if not enabled:
            painter.setPen(QPen(Qt.gray, 3))
        else:
            painter.setPen(QPen(Qt.white, 4))
        painter.drawText(rect, Qt.AlignCenter, f"SUBMIT ({sel_txt})")

        x, y = dot
        painter.setPen(Qt.NoPen)

        if not enabled:
            painter.setBrush(Qt.gray)
            r = max(9, int(self.height() * 0.016))
        else:
            if self._last_submit_score >= self.submit_corr_threshold:
                painter.setBrush(Qt.white)
                r = max(11, int(self.height() * 0.020))
            else:
                painter.setBrush(Qt.white)
                r = max(9, int(self.height() * 0.016))

        painter.drawEllipse(int(x) - r, int(y) - r, 2 * r, 2 * r)
