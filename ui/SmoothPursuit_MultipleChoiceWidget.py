# ui/SmoothPursuit_MultipleChoiceWidget.py
# Smooth Pursuit Multiple Choice Widget with 4 Options

from __future__ import annotations

import math
import time
from typing import Dict, List, Optional, Tuple, Set

import numpy as np
from PySide6.QtCore import Qt, QRect, QTimer, Slot, Signal, QPoint
from PySide6.QtGui import QPainter, QPen
from PySide6.QtWidgets import QApplication

from ui.gaze_widget import GazeWidget


def pearson_corr(a: np.ndarray, b: np.ndarray) -> float:
    """
    Compute the Pearson correlation coefficient between two 1D signals.

    The function:
    - Converts inputs to float NumPy arrays
    - Aligns the signals by trimming to the same length (from the end)
    - Mean-centers both signals
    - Returns the normalized dot product (Pearson's r)

    If either signal has fewer than 3 samples, or if the variance of either
    signal is effectively zero, the function returns 0.0.

    Parameters
    ----------
    a : np.ndarray
        First input signal (1D array-like).
    b : np.ndarray
        Second input signal (1D array-like).

    Returns
    -------
    float
        Pearson correlation coefficient in the range [-1.0, 1.0].
        Returns 0.0 if the correlation is undefined or unreliable.

    Notes
    -----
    - If the input arrays differ in length, only the most recent samples
      (i.e., the last `min(len(a), len(b))` elements) are used.
    - A minimum of 3 samples is required to compute a meaningful correlation.
    - This implementation avoids division-by-zero by checking the vector norms.

    Examples
    --------
    >>> pearson_corr([1, 2, 3], [1, 2, 3])
    1.0
    >>> pearson_corr([1, 2, 3], [3, 2, 1])
    -1.0
    >>> pearson_corr([1, 1, 1], [2, 2, 2])
    0.0
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
    Compute the maximum Pearson correlation between two 1D signals over a range of time lags.

    The function evaluates Pearson correlation coefficients between `a` and `b`
    for all integer sample lags in the interval
    [-max_lag_samples, +max_lag_samples] and returns the maximum value.

    A positive lag means that signal `a` is shifted forward relative to `b`
    (i.e., `a[k:]` is compared with `b[:-k]`), while a negative lag shifts `a`
    backward relative to `b`.

    The signals are first aligned to equal length by keeping only the most recent
    samples.

    If `max_lag_samples` is zero, this function is equivalent to `pearson_corr(a, b)`.

    Parameters
    ----------
    a : np.ndarray
        First input signal (1D array-like).
    b : np.ndarray
        Second input signal (1D array-like).
    max_lag_samples : int
        Maximum number of samples by which the signals may be shifted in either
        direction when computing the correlation.

    Returns
    -------
    float
        Maximum Pearson correlation coefficient across all evaluated lags.
        The value lies in the range [-1.0, 1.0].
        Returns 0.0 if the correlation is undefined or unreliable.

    Notes
    -----
    - A minimum of 3 overlapping samples is required for any lag to be considered.
    - If the input arrays differ in length, only the most recent
      `min(len(a), len(b))` samples are used.
    - This implementation uses `None` to represent “no valid lag overlap,”
      avoiding edge cases where a true best correlation of -1.0 could be mistaken
      for “no result.”

    Examples
    --------
    >>> max_lagged_pearson_corr([1, 2, 3, 4], [0, 1, 2, 3], max_lag_samples=1)
    1.0
    >>> max_lagged_pearson_corr([1, 2, 3], [3, 2, 1], max_lag_samples=2)
    -1.0
    >>> max_lagged_pearson_corr([1, 1, 1], [2, 2, 2], max_lag_samples=5)
    0.0
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
    Compute a Gaussian proximity weight from distances.

    This function maps distances to values in the range (0, 1] using a
    Gaussian (radial basis function) kernel. Smaller distances yield values
    closer to 1, while larger distances decay smoothly toward 0.

    Parameters
    ----------
    dist : np.ndarray
        Array of distances (e.g., Euclidean distances in pixels).
        Must be non-negative.
    sigma : float
        Standard deviation of the Gaussian kernel, controlling the spatial
        falloff. Larger values produce a slower decay.
        A minimum value of 1.0 is enforced for numerical stability.

    Returns
    -------
    np.ndarray
        Array of proximity weights with the same shape as `dist`,
        where values are in the interval (0, 1].

    Notes
    -----
    - The Gaussian is defined as: exp(-d² / (2σ²)).
    - This function does not normalize the output; it is intended for relative
      weighting rather than probability estimation.
    """
    sigma = max(1.0, float(sigma))
    return np.exp(-(dist * dist) / (2.0 * sigma * sigma))


class SmoothPursuitMultipleChoiceWidget(GazeWidget):
    """
    Smooth Pursuit Multiple Choice (multi-select) with separate SUBMIT (MCQ-like UX).

    UI/Behavior
    -----------
    - 4 moving TEXT labels in the corners, each with a moving DOT target:
        A: top-left    circle CW
        B: top-right   circle CCW
        C: bottom-left square CW
        D: bottom-right square CCW
    - Following an option's moving DOT stably TOGGLES that option (multi-select).
    - Following a moving SUBMIT DOT stably submits current selection.

    Decision Signal Model
    ---------------------
    Evidence per option is computed from:
    - correlation between gaze and target motion (X and Y, averaged)
    - plus a spatial proximity term (Gaussian of gaze-to-target distance)
    These are mixed with weights: corr_weight + proximity_weight = 1.0.

    Signals
    -------
    submitted(object):
        Emits ONLY List[str] of selected labels (e.g. ["A","C"]).
    clicked(int, str):
        Emits "toggle:<label>" or "submit" for click logging.
    """

    submitted = Signal(object)
    clicked = Signal(int, str)

    def __init__(
        self,
        question: str,
        labels: Optional[List[str]] = None,
        parent=None,

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

        # Visual params
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
        """
        Initialize a smooth pursuit multi-choice widget with gaze-based toggling and submission.

        The widget shows four moving option targets and a separate SUBMIT target.
        Users toggle options by following the corresponding moving dot target and
        submit by following the SUBMIT moving dot.

        Decision making is based on rolling-window Pearson correlation (with optional
        lag compensation) combined with a spatial proximity term.

        Parameters
        ----------
        question : str
            The question text displayed in the center of the widget.
        labels : list[str], optional
            Exactly four option labels (defaults to ["A","B","C","D"]).
        parent : QWidget, optional
            Parent Qt widget.

        window_ms : int, default=1250
            Length of the rolling time window (in milliseconds) used for correlation
            and proximity computation.
        corr_threshold : float, default=0.73
            Minimum combined score required for an option to become a toggle candidate.
        toggle_stable_samples : int, default=18
            Number of consecutive samples an option must remain best-above-threshold
            before toggling.
        submit_stable_samples : int, default=30
            Number of consecutive samples SUBMIT must remain above threshold before
            submission triggers.

        use_lag_compensation : bool, default=True
            Whether to compensate eye–target latency by evaluating correlation over
            a range of time lags.
        max_lag_ms : int, default=180
            Maximum temporal lag (ms) considered for lag-compensated correlation.

        option_frequency_hz : float, default=0.25
            Motion frequency (Hz) for all option targets.
        submit_frequency_hz : float, default=0.28
            Horizontal oscillation frequency (Hz) for the SUBMIT dot.

        orbit_scale : float, default=0.36
            Relative scale controlling size of orbit shapes (proportional to widget size).

        proximity_sigma_px : float, default=220.0
            Standard deviation (px) of the Gaussian proximity kernel.
        proximity_weight : float, default=0.15
            Weight of the proximity term in the final score.

        toggle_cooldown_ms : int, default=1300
            Cooldown (ms) after a toggle during which no new toggle can occur.
        submit_cooldown_ms : int, default=1400
            Cooldown (ms) after submission during which no further submissions can occur.

        allow_empty_submit : bool, default=False
            If False, submission is disabled until at least one option is selected.

        Notes
        -----
        - Option scoring uses correlation in both X and Y dimensions.
        - Submission scoring uses X-axis correlation only (SUBMIT dot moves horizontally).
        - Stability checks are sample-count based rather than time-based.
        """
        super().__init__(parent)
        self.question = question
        if labels is None:
            self.labels = ["A", "B", "C", "D"]
        else:
            assert len(labels) == 4, "SmoothPursuitMultipleChoiceWidget requires exactly 4 labels."
            self.labels = list(labels)

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

        # Multi-select state
        self.selected: Set[str] = set()

        # Candidate stability counters (sample-count based)
        self._candidate: Optional[str] = None
        self._candidate_count = 0
        self._submit_count = 0

        # Cooldowns (monotonic seconds)
        self._toggle_block_until = 0.0
        self._submit_block_until = 0.0

        # For UI highlight/debug feedback
        self._last_scores: Dict[str, float] = {lab: 0.0 for lab in self.labels}
        self._last_submit_score: float = 0.0

        # Click logging
        self.click_index: int = 0

        # Animation timer (drives repaint for smooth motion)
        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(16)
        self._anim_timer.timeout.connect(self.update)
        self._anim_timer.start()

        # Logging fields expected by MainWindow (keep consistent)
        self.log_toggles = 0
        self.log_resets = 0
        self.log_backspaces = 0
        self.log_extra = "sp_mcq_multi"

    # ---------------- Motion primitives ----------------

    @staticmethod
    def _circle_pos(cx: float, cy: float, r: float, t: float, freq_hz: float, clockwise: bool) -> Tuple[float, float]:
        """
        Compute a point moving on a circle.

        Parameters
        ----------
        cx, cy : float
            Circle center.
        r : float
            Circle radius in pixels.
        t : float
            Time in seconds since motion start.
        freq_hz : float
            Cycles per second.
        clockwise : bool
            If True, motion is clockwise; otherwise counterclockwise.

        Returns
        -------
        (float, float)
            Current (x, y) position on the circular path.

        Notes
        -----
        - The circle is parameterized by angle = 2π f t, with sign determining direction.
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

        The motion follows edges at constant speed, completing one full loop per
        period defined by `freq_hz`. The square is centered at (`cx`, `cy`) and
        has half-side length `half_side`.

        Path order:
          top edge → right edge → bottom edge → left edge

        Parameters
        ----------
        cx, cy : float
            Square center.
        half_side : float
            Half of the side length (pixels).
        t : float
            Time in seconds since motion start.
        freq_hz : float
            Cycles per second.
        clockwise : bool
            If True, motion proceeds clockwise; otherwise counterclockwise.

        Returns
        -------
        (float, float)
            Current (x, y) position on the square perimeter.

        Notes
        -----
        - Uses normalized progress u = (t * f) mod 1.
        - Flips u when counterclockwise for reverse traversal.
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

    def _layout(self) -> Tuple[QRect, Dict[str, Tuple[float, float]], Dict[str, Dict[str, float]], QRect, float]:
        """
        Compute and return all static layout elements for the multi-choice widget.

        This method defines the geometry of the interface based on the current widget
        size. It computes:
        - the central question box,
        - the centers and motion parameters of the 4 option orbits,
        - and the static SUBMIT rectangle and its motion amplitude.

        Returns
        -------
        question_rect : QRect
            Rectangle defining the position and size of the central question text.
        centers : dict[str, (float, float)]
            Mapping from option label to the (x, y) center of its orbit.
        orbit_params : dict[str, dict[str, float]]
            Per-label motion parameters. For A/B uses {"circle_r": r};
            for C/D uses {"square_half": half_side}.
        submit_rect : QRect
            Rectangle defining the static SUBMIT text region.
        submit_ax : float
            Horizontal oscillation amplitude (pixels) for the SUBMIT target dot.

        Notes
        -----
        - A and B (top corners) use circular orbits; C and D (bottom corners) use square orbits.
        - Margins are chosen to keep orbits inside the screen.
        - The SUBMIT dot moves horizontally along a line centered on submit_rect.
        """
        w = max(1, self.width())
        h = max(1, self.height())

        # Smaller center question box
        q_w = int(w * 0.52)
        q_h = int(h * 0.22)
        qx = (w - q_w) // 2
        qy = int(h * 0.36) - q_h // 2
        question_rect = QRect(qx, qy, q_w, q_h)

        base = min(w, h)
        orbit_size = max(280.0, base * self.orbit_scale)
        circle_r = orbit_size * 0.50
        square_half = orbit_size * 0.50

        # margins keep orbits inside screen
        margin = int(orbit_size * 0.72) + 32

        top_y = float(margin)
        bottom_y = float(h * 0.66)
        left_x = float(margin)
        right_x = float(w - margin)

        centers = {
            self.labels[0]: (left_x, top_y),
            self.labels[1]: (right_x, top_y),
            self.labels[2]: (left_x, bottom_y),
            self.labels[3]: (right_x, bottom_y),
        }

        orbit_params = {
            self.labels[0]: {"circle_r": circle_r},
            self.labels[1]: {"circle_r": circle_r},
            self.labels[2]: {"square_half": square_half},
            self.labels[3]: {"square_half": square_half},
        }

        # Submit button
        submit_w = int(max(700, w * 0.50))
        submit_h = int(max(105, h * 0.11))
        submit_y = int(h * 0.88)
        submit_rect = QRect(int(w * 0.5 - submit_w / 2), int(submit_y - submit_h / 2), submit_w, submit_h)

        submit_ax = max(220.0, w * 0.30)
        return question_rect, centers, orbit_params, submit_rect, float(submit_ax)

    def _targets_at_time(self, t: float) -> Tuple[Dict[str, Tuple[float, float]], QRect, Tuple[float, float], float]:
        """
        Compute the instantaneous positions of all moving targets at time `t`.

        This method returns:
        - the moving option target dot positions (A/B circles, C/D squares),
        - the static SUBMIT text rectangle,
        - the moving SUBMIT target dot position,
        - and the SUBMIT dot horizontal amplitude.

        Parameters
        ----------
        t : float
            Time in seconds since widget initialization.

        Returns
        -------
        pos : dict[str, (float, float)]
            Current (x, y) positions of option dot targets for each label.
        submit_rect : QRect
            Static rectangle defining the SUBMIT text region.
        submit_dot : (float, float)
            Current (x, y) position of the moving SUBMIT dot target.
        submit_ax : float
            Horizontal oscillation amplitude (pixels) for the SUBMIT dot.

        Notes
        -----
        - A: circle clockwise
        - B: circle counterclockwise
        - C: square clockwise
        - D: square counterclockwise
        - SUBMIT dot oscillates horizontally: x = center + ax * sin(2π f t)
        """
        w = max(1, self.width())
        _, centers, orbit_params, submit_rect, submit_ax = self._layout()

        pos: Dict[str, Tuple[float, float]] = {}

        # A circle CW
        cx, cy = centers[self.labels[0]]
        r = orbit_params[self.labels[0]]["circle_r"]
        pos[self.labels[0]] = self._circle_pos(cx, cy, r, t, self.option_frequency_hz, clockwise=True)

        # B circle CCW
        cx, cy = centers[self.labels[1]]
        r = orbit_params[self.labels[1]]["circle_r"]
        pos[self.labels[1]] = self._circle_pos(cx, cy, r, t, self.option_frequency_hz, clockwise=False)

        # C square CW
        cx, cy = centers[self.labels[2]]
        hs = orbit_params[self.labels[2]]["square_half"]
        pos[self.labels[2]] = self._square_pos(cx, cy, hs, t, self.option_frequency_hz, clockwise=True)

        # D square CCW
        cx, cy = centers[self.labels[3]]
        hs = orbit_params[self.labels[3]]["square_half"]
        pos[self.labels[3]] = self._square_pos(cx, cy, hs, t, self.option_frequency_hz, clockwise=False)

        # SUBMIT DOT horizontal oscillation (rect stays fixed)
        omega = 2.0 * math.pi * self.submit_frequency_hz
        submit_dot_x = (w * 0.5) + submit_ax * math.sin(omega * t)
        submit_dot_y = float(submit_rect.center().y())

        return pos, submit_rect, (float(submit_dot_x), float(submit_dot_y)), float(submit_ax)

    # ---------------- Rolling buffer maintenance ----------------

    def _estimate_max_lag_samples(self) -> int:
        """
        Estimate the maximum number of samples corresponding to `max_lag_ms`.

        This method converts the maximum temporal lag specified in milliseconds
        (`self.max_lag_ms`) into a number of samples based on the current sampling
        rate estimated from recent timestamps in the rolling buffer.

        Returns
        -------
        int
            Maximum lag in samples for lag-compensated correlation.

        Notes
        -----
        - The sampling interval is estimated via the median of timestamp differences
          for robustness to outliers.
        - If insufficient data is available, a fallback of 30 Hz is used.
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
        Prune the rolling buffers to maintain a fixed temporal window.

        This method removes outdated samples from all time-aligned buffers so that
        only data within the most recent `window_ms` milliseconds are retained.

        Returns
        -------
        None

        Notes
        -----
        - Buffers are pruned synchronously to preserve index alignment.
        - Uses list `pop(0)` (O(N)); acceptable for small windows, but a `deque`
          is recommended if performance becomes an issue at high sampling rates.
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

    # ---------------- Time helper ----------------

    def _now(self) -> float:
        """
        Return the current monotonic time in seconds.

        This timestamp is suitable for cooldown tracking and duration measurement,
        and is not affected by system clock adjustments.

        Returns
        -------
        float
            Current monotonic time in seconds.
        """
        return time.monotonic()

    # ---------------- Gaze input ----------------

    @Slot(float, float)
    def set_gaze(self, x: float, y: float):
        """
        Receive a new gaze sample and update the smooth pursuit decision state.

        This method is called whenever a new gaze position is available. The gaze
        is mapped into widget coordinates and appended to the rolling buffers
        together with the current positions of all moving targets.

        Once enough samples have accumulated in the rolling window, the method
        updates toggle and submission decisions using correlation- and
        proximity-based evidence.

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
        - If gaze mapping fails (invalid/off-screen), candidate stability counters
          are reset to avoid false triggers.
        - Target positions are sampled at the same timestamp as the gaze to preserve
          temporal alignment.
        - A minimum number of samples (12) is required before decision logic runs.
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

        self._t.append(t)
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

    # ---------------- Decision logic (corr + proximity) ----------------

    def _option_score(self, lab: str) -> float:
        """
        Compute the combined smooth pursuit score for a given option label.

        The score reflects how well the user's gaze follows the moving target
        associated with the option. It combines:
        - correlation between gaze and target motion in X and Y (averaged),
        - plus a spatial proximity term (Gaussian of gaze-to-target distance).

        Parameters
        ----------
        lab : str
            Option label for which the score is computed.

        Returns
        -------
        float
            Combined score in [-1.0, 1.0], where higher values indicate stronger
            evidence of intentional following.

        Notes
        -----
        - If lag compensation is enabled, the maximum Pearson correlation across
          a range of temporal lags is used to account for eye–target latency.
        - Proximity is averaged over the same rolling window and mapped from [0,1]
          to [-1,1] before mixing.
        """
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

        corr = 0.5 * (cx + cy)  # [-1, 1]

        # proximity (window-mean), mapped to [-1, 1]
        dist = np.sqrt((gx - tx) ** 2 + (gy - ty) ** 2)
        prox = float(np.mean(gaussian_proximity(dist, self.proximity_sigma_px)))  # 0..1
        prox_mapped = (2.0 * prox) - 1.0

        return float((self.corr_weight * corr) + (self.proximity_weight * prox_mapped))

    def _submit_score(self) -> float:
        """
        Compute the smooth pursuit score for the SUBMIT target.

        The SUBMIT target dot moves horizontally; therefore correlation is evaluated
        along the X-axis only. A spatial proximity term (2D distance) is mixed in
        for robustness.

        Returns
        -------
        float
            Combined submit score in [-1.0, 1.0], where higher values indicate stronger
            evidence that the user is following the SUBMIT target.

        Notes
        -----
        - If lag compensation is enabled, uses maximum Pearson correlation over lags
          to account for eye–target latency.
        - Proximity is averaged over the rolling window and mapped from [0,1] to [-1,1].
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

    def _toggle_label(self, lab: str) -> None:
        """
        Toggle a label in the current multi-selection set.

        This method adds `lab` to the selection if it is not selected, or removes it
        if it is already selected. It emits a click signal for logging, provides an
        auditory beep, and starts a toggle cooldown during which further toggles are
        blocked.

        Parameters
        ----------
        lab : str
            Label to toggle.

        Returns
        -------
        None

        Notes
        -----
        - Multi-select semantics: selection is a set.
        - The cooldown helps prevent rapid accidental repeated toggles.
        """
        if lab in self.selected:
            self.selected.remove(lab)
        else:
            self.selected.add(lab)

        self.log_toggles += 1
        self.click_index += 1
        self.clicked.emit(self.click_index, f"toggle:{lab}")
        QApplication.beep()

        self._toggle_block_until = self._now() + (self.toggle_cooldown_ms / 1000.0)

    def _submit(self) -> None:
        """
        Submit the current multi-selection.

        If empty submission is disabled and no option is selected, the method returns
        without action. Otherwise it emits:
        - clicked(..., "submit") for logging
        - submitted(sorted_list) for downstream handling

        Returns
        -------
        None

        Notes
        -----
        - The `submitted` signal emits ONLY a list of selected labels (sorted),
          e.g. ["A","C"], for consistent logging/handling.
        - A submission cooldown is enforced to avoid repeated submissions.
        """
        if (not self.allow_empty_submit) and (not self.selected):
            return

        self.click_index += 1
        self.clicked.emit(self.click_index, "submit")
        QApplication.beep()

        self._submit_block_until = self._now() + (self.submit_cooldown_ms / 1000.0)

        self.submitted.emit(sorted(self.selected))

    def _update_decision(self) -> None:
        """
        Update toggle and submission decisions based on accumulated gaze data.

        This method evaluates:
        1) Option scores (4 options): selects the best candidate above threshold and
           tracks its stability count to decide toggling.
        2) Submit score: tracks stability count to decide submission.

        Submission is evaluated before toggling to avoid accidental toggles right
        before a submit.

        Returns
        -------
        None

        Notes
        -----
        - An option becomes a toggle candidate when its score is the highest among
          all options and exceeds `corr_threshold`.
        - A candidate must remain stable for `toggle_stable_samples` consecutive
          samples before toggling is triggered.
        - Submission requires submit score to remain above `submit_corr_threshold`
          for `submit_stable_samples` consecutive samples.
        - Cooldowns prevent repeated actions within short time intervals.
        - After a successful submit, candidate tracking state is reset.
        """
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
        if ss >= self.submit_corr_threshold:
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

        # toggle
        if now >= self._toggle_block_until:
            if self._candidate is not None and self._candidate_count >= self.toggle_stable_samples:
                lab = self._candidate
                self._candidate = None
                self._candidate_count = 0
                self._toggle_label(lab)

    # ---------------- Drawing ----------------

    def paintEvent(self, event):
        """
        Render the complete visual state of the multi-choice smooth pursuit widget.

        This method draws:
        - background and instructions,
        - central question text,
        - orbit outlines (circles for A/B; squares for C/D),
        - static option labels and their moving target dots,
        - SUBMIT text and moving target dot, plus a guide line,
        - current gaze position (red dot).

        Parameters
        ----------
        event : QPaintEvent
            Qt paint event (required by Qt signature; unused).

        Returns
        -------
        None

        Notes
        -----
        - Rendering is driven by a timer calling `update()` at ~60 FPS.
        - The current best option (above threshold) is visually highlighted.
        - The SUBMIT dot is the pursuit stimulus; the SUBMIT text rectangle is static.
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

            # instructions
            painter.setPen(Qt.white)
            f = painter.font()
            f.setPointSize(max(16, int(h * 0.028)))
            painter.setFont(f)

            info_rect = QRect(28, 18, w - 56, int(h * 0.13))
            sel_txt = ", ".join(sorted(self.selected)) if self.selected else "-"
            painter.drawText(
                info_rect,
                Qt.AlignLeft | Qt.AlignVCenter | Qt.TextWordWrap,
                "Follow the moving DOT to TOGGLE an option (multi-select). Follow SUBMIT to submit.\n"
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

            # orbit outlines
            orbit_pen = QPen(Qt.gray)
            orbit_pen.setWidth(2)
            painter.setPen(orbit_pen)
            painter.setBrush(Qt.NoBrush)

            for lab in self.labels:
                cx, cy = centers[lab]
                cfg = orbit_params[lab]

                if "circle_r" in cfg:
                    r = float(cfg["circle_r"])
                    painter.drawEllipse(QPoint(int(cx), int(cy)), int(r), int(r))
                else:
                    hs = float(cfg["square_half"])
                    painter.drawRect(QRect(int(cx - hs), int(cy - hs), int(2 * hs), int(2 * hs)))

            # static labels + moving target dots
            for lab in self.labels:
                cx, cy = centers[lab]
                selected = (lab in self.selected)
                highlight = (lab == highlight_opt)

                self._draw_static_label(painter, cx, cy, str(lab), selected=selected, highlight=highlight)

                x, y = opt_pos[lab]
                self._draw_target_dot(painter, x, y, selected=selected, highlight=highlight)

            # submit
            self._draw_submit(painter, submit_rect, submit_dot)

            # gaze point
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
        Draw a static option label at a fixed center position.

        Parameters
        ----------
        painter : QPainter
            Active Qt painter.
        cx, cy : float
            Center position of the label.
        text : str
            Label text to draw (e.g., "A", "B", "C", "D").
        selected : bool
            Whether this option is currently selected (drawn green).
        highlight : bool
            Whether this option is currently the best candidate (thicker white).

        Returns
        -------
        None

        Notes
        -----
        - The label does not move; only the target dot moves.
        - Pen color and width encode interaction state: selected > highlight > normal.
        """
        f = painter.font()
        f.setBold(True)
        f.setPointSize(max(24, int(self.height() * 0.038)))
        painter.setFont(f)

        if selected:
            painter.setPen(QPen(Qt.green, 6))
        elif highlight:
            painter.setPen(QPen(Qt.white, 4))
        else:
            painter.setPen(QPen(Qt.white, 3))

        rect = QRect(int(cx - 80), int(cy - 50), 160, 100)
        painter.drawText(rect, Qt.AlignCenter, text)

    def _draw_target_dot(self, painter: QPainter, x: float, y: float, selected: bool, highlight: bool):
        """
        Draw a moving target dot used for smooth pursuit interaction.

        Parameters
        ----------
        painter : QPainter
            Active Qt painter.
        x, y : float
            Current target dot position.
        selected : bool
            Whether the associated option is selected (green, slightly larger).
        highlight : bool
            Whether the associated option is currently the best candidate (slightly larger).

        Returns
        -------
        None

        Notes
        -----
        - Dots are drawn without outline to reduce visual clutter.
        - Size scales with widget height for visibility across screen sizes.
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

    def _draw_submit(self, painter: QPainter, rect: QRect, dot: Tuple[float, float]):
        """
        Draw the SUBMIT UI element: static text plus a moving target dot.

        Parameters
        ----------
        painter : QPainter
            Active Qt painter.
        rect : QRect
            Static rectangle for the SUBMIT text region.
        dot : (float, float)
            Current (x, y) position of the moving SUBMIT target dot.

        Returns
        -------
        None

        Notes
        -----
        - The SUBMIT text is static for readability; the user follows the moving dot.
        - If submission is disabled (no selection and allow_empty_submit=False),
          the text and dot are drawn gray.
        - When submit evidence is strong, the dot is slightly enlarged.
        """
        f = painter.font()
        f.setBold(True)
        f.setPointSize(max(22, int(self.height() * 0.038)))
        painter.setFont(f)

        sel_txt = ",".join(sorted(self.selected)) if self.selected else "-"
        enabled = (self.allow_empty_submit or bool(self.selected))

        # static text
        if not enabled:
            painter.setPen(QPen(Qt.gray, 3))
        else:
            painter.setPen(QPen(Qt.white, 4))
        painter.drawText(rect, Qt.AlignCenter, f"SUBMIT ({sel_txt})")

        # moving dot target (follow this)
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
