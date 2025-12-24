# ui/SmoothPursuit_YesNoWidget.py
# Smooth Pursuit Yes-No-Widget

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
        - This implementation is numerically stable and avoids division-by-zero
          by checking the vector norms explicitly.

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
    - The function is robust to small sample sizes and avoids invalid
      correlations by explicitly checking overlap length.
    - This method is particularly useful for compensating small temporal delays
      (e.g., eye–target latency) in smooth pursuit analysis.

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
    """
    Compute a Gaussian proximity weight from distances.

    This function maps distances to values in the range (0, 1] using a
    Gaussian (radial basis function) kernel. Smaller distances yield values
    closer to 1, while larger distances decay smoothly toward 0.

    The function is typically used to softly weight spatial proximity, e.g.
    as a complement to correlation-based measures in smooth pursuit analysis.

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
    - Enforcing a minimum sigma avoids division by zero and excessively sharp
      kernels.
    - This function does not normalize the output; it is intended for relative
      weighting rather than probability estimation.

    Examples
    --------
    >>> gaussian_proximity(np.array([0.0, 10.0, 20.0]), sigma=10.0)
    array([1.        , 0.60653066, 0.13533528])
    >>> gaussian_proximity(np.array([0.0]), sigma=0.1)
    array([1.])
    """
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
        submit_stable_samples: int = 30,
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
        """
        Initialize a smooth pursuit Yes/No widget with gaze-based selection and submission.

        The widget presents two moving text labels (YES / NO) and a separate SUBMIT
        target. Users select an option by following its moving target stably with
        their gaze and submit the selection by following the SUBMIT target.

        Decision making is based on rolling-window Pearson correlation (with optional
        lag compensation) combined with a spatial proximity term.

        Parameters
        ----------
        question : str
            The question text displayed in the center of the widget.

        parent : QWidget, optional
            Parent Qt widget.

        window_ms : int, default=1250
            Length of the rolling time window (in milliseconds) used for correlation
            and proximity computation.

        corr_threshold : float, default=0.73
            Minimum combined correlation score required for an option to become a
            selection candidate.

        toggle_stable_samples : int, default=18
            Number of consecutive samples for which an option must remain the best
            candidate before it is selected.

        submit_stable_samples : int, default=30
            Number of consecutive samples for which the SUBMIT target must remain
            above threshold before submission is triggered.

        use_lag_compensation : bool, default=True
            Whether to compensate for temporal delays between gaze and target motion
            by evaluating correlations over a range of time lags.

        max_lag_ms : int, default=180
            Maximum temporal lag (in milliseconds) considered for lag-compensated
            correlation.

        option_frequency_hz : float, default=0.25
            Motion frequency (in Hertz) of the YES/NO option targets.

        submit_frequency_hz : float, default=0.28
            Horizontal oscillation frequency (in Hertz) of the SUBMIT target.

        orbit_scale : float, default=0.36
            Relative scale factor controlling the size of the motion paths
            (proportional to the widget size).

        proximity_sigma_px : float, default=220.0
            Standard deviation (in pixels) of the Gaussian proximity kernel used to
            softly weight spatial closeness between gaze and target.

        proximity_weight : float, default=0.15
            Weight of the proximity term in the final decision score.
            The remaining weight (1 - proximity_weight) is assigned to correlation.

        toggle_cooldown_ms : int, default=1300
            Cooldown duration (in milliseconds) after a selection toggle during which
            no new toggle can occur.

        submit_cooldown_ms : int, default=1400
            Cooldown duration (in milliseconds) after submission during which no
            further submissions can occur.

        allow_empty_submit : bool, default=False
            If False, submission is disabled until a YES or NO option has been selected.

        labels : list of str, optional
            Custom labels for the two options. Must contain exactly two strings.
            Defaults to ["yes", "no"].

        Notes
        -----
        - Option selection uses correlation in both X and Y dimensions.
        - Submission uses X-axis correlation only (since the SUBMIT target moves
          horizontally).
        - All temporal stability checks are sample-count based rather than time-based,
          making them robust to variable frame rates.
        """

        super().__init__(parent)

        self.question = question
        if labels is None:
            self.labels = ["yes", "no"]
        else:
            assert len(labels) == 2, "SmoothPursuitYesNoWidget requires exactly 2 labels."
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

        # Logging fields expected by MainWindow
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
        Compute a point moving along the perimeter of an axis-aligned rectangle.

        The motion follows the rectangle edges at constant speed, completing one
        full loop per period defined by `freq_hz`. The rectangle is centered at
        (`cx`, `cy`) with half-width `half_w` and half-height `half_h`.

        The path order is:
          top edge → right edge → bottom edge → left edge

        Motion direction can be clockwise or counterclockwise.

        Parameters
        ----------
        cx : float
            X-coordinate of the rectangle center.
        cy : float
            Y-coordinate of the rectangle center.
        half_w : float
            Half of the rectangle width.
        half_h : float
            Half of the rectangle height.
        t : float
            Time in seconds since motion start.
        freq_hz : float
            Motion frequency in Hertz (cycles per second).
        clockwise : bool
            If True, motion proceeds clockwise.
            If False, motion proceeds counterclockwise.

        Returns
        -------
        (float, float)
            The (x, y) position of the moving point on the rectangle perimeter.

        Notes
        -----
        - The parameter `u = (t * freq_hz) mod 1` represents normalized progress
          along the full rectangular path.
        - The rectangle is traversed at constant speed along each edge.
        - This path is particularly useful for smooth pursuit stimuli that require
          predictable but non-circular motion.
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

    def _layout(self) -> Tuple[QRect, Dict[str, Tuple[float, float]], Dict[str, Dict[str, float]], QRect, float]:
        """
        Compute and return all static layout elements for the Yes/No smooth pursuit widget.

        This method defines the geometry of the interface based on the current widget
        size. It computes positions for:
        - the central question box,
        - the centers and motion parameters of the YES/NO targets,
        - and the static SUBMIT text area and its motion amplitude.

        The layout adapts automatically to the widget dimensions to remain usable
        across different screen sizes and aspect ratios.

        Returns
        -------
        question_rect : QRect
            Rectangle defining the position and size of the central question text.

        centers : dict[str, tuple[float, float]]
            Mapping from option label ("yes"/"no") to the (x, y) center position
            around which the corresponding moving target is animated.

        orbit_params : dict[str, dict[str, float]]
            Motion parameters for each option target.
            For Yes/No, each entry contains:
                - "half_w": half width of the rectangular motion path
                - "half_h": half height of the rectangular motion path

        submit_rect : QRect
            Static rectangle defining the position and size of the SUBMIT text.
            This rectangle does not move.

        submit_ax : float
            Horizontal oscillation amplitude (in pixels) for the SUBMIT target dot.

        Notes
        -----
        - The question box is intentionally smaller (MCQ-sized) to reduce visual
          dominance and leave more space for moving targets.
        - YES and NO are placed symmetrically on the left and right sides of the
          screen, slightly above the vertical center.
        - Motion path sizes are derived from a global `orbit_scale` factor and
          clamped to reasonable minimums for small screens.
        - The SUBMIT text is positioned near the bottom of the screen and is
          associated with a separate moving dot used for gaze-based submission.
        """
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

    def _targets_at_time(self, t: float) -> Tuple[Dict[str, Tuple[float, float]], QRect, Tuple[float, float], float]:
        """
        Compute the instantaneous positions of all moving targets at time `t`.

        This method returns the current positions of:
        - the moving YES and NO option targets,
        - the static SUBMIT text rectangle,
        - the moving SUBMIT target dot,
        - and the horizontal motion amplitude of the SUBMIT dot.

        Option targets follow rectangular paths centered at predefined locations,
        while the SUBMIT target moves horizontally beneath the question area.
        The SUBMIT text itself remains static.

        Parameters
        ----------
        t : float
            Time in seconds since the widget was initialized.

        Returns
        -------
        pos : dict[str, tuple[float, float]]
            Mapping from option label ("yes"/"no") to the current (x, y) position
            of its moving target.

        submit_rect : QRect
            Static rectangle defining the position and size of the SUBMIT text.

        submit_dot : tuple[float, float]
            Current (x, y) position of the moving SUBMIT target dot that the user
            must follow with their gaze to trigger submission.

        submit_ax : float
            Horizontal oscillation amplitude (in pixels) used for the SUBMIT target.

        Notes
        -----
        - YES moves counterclockwise and NO moves clockwise along identical
          rectangular paths, aiding visual distinction.
        - The SUBMIT target motion is purely horizontal; therefore, submission
          correlation is evaluated along the X-axis only.
        - All returned positions are expressed in widget coordinates.
        """
        w = max(1, self.width())
        _, centers, orbit_params, submit_rect, submit_ax = self._layout()

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

        # SUBMIT DOT horizontal oscillation (rect stays fixed!)
        omega = 2.0 * math.pi * self.submit_frequency_hz
        submit_dot_x = (w * 0.5) + submit_ax * math.sin(omega * t)
        submit_dot_y = float(submit_rect.center().y())

        return pos, submit_rect, (float(submit_dot_x), float(submit_dot_y)), float(submit_ax)

    # ---------------- Rolling buffer maintenance ----------------

    def _estimate_max_lag_samples(self) -> int:
        """
        Estimate the maximum number of samples corresponding to the allowed time lag.

        This method converts the maximum temporal lag specified in milliseconds
        (`self.max_lag_ms`) into a number of samples based on the current sampling
        rate of the gaze data.

        The sampling interval is estimated from the median difference of recent
        timestamps stored in the rolling buffer. If insufficient data is available
        or the estimated interval is invalid, a fallback value corresponding to
        30 Hz is used.

        Returns
        -------
        int
            Maximum lag in samples to be used for lag-compensated correlation.

        Notes
        -----
        - The median of timestamp differences is used for robustness against
          occasional dropped or irregular samples.
        - A minimum fallback sampling rate of 30 Hz ensures stable behavior during
          initialization and transient conditions.
        - The returned value is rounded to the nearest integer to ensure symmetric
          lag evaluation around zero.
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

        This method removes outdated samples from all internal time-aligned buffers
        such that only data within the most recent `window_ms` milliseconds are kept.

        The timestamp buffer (`self._t`) serves as the reference; whenever the oldest
        timestamp falls outside the allowed time window, the corresponding entries
        are removed from all associated gaze, target, and submit buffers to preserve
        alignment.

        Returns
        -------
        None

        Notes
        -----
        - All buffers (`_t`, `_gx`, `_gy`, `_tx`, `_ty`, `_sx`, `_sy`) are pruned
          synchronously to ensure consistent indexing across signals.
        - The method operates in-place and is typically called after appending
          new samples.
        - If no timestamps are present, the method returns immediately.
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
        Return the current monotonic time in seconds.

        This method provides a monotonic timestamp suitable for measuring durations,
        enforcing cooldowns, and computing relative time differences. Unlike wall-clock
        time, monotonic time is guaranteed to be non-decreasing and is not affected by
        system clock adjustments.

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
        sample is mapped into widget coordinates and appended to the rolling buffers
        together with the current positions of all moving targets.

        Based on the accumulated samples within the rolling time window, the method
        updates selection and submission decisions using correlation- and
        proximity-based criteria.

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
        - If the gaze cannot be mapped to widget coordinates (e.g., invalid or
          off-screen), all candidate stability counters are reset.
        - Target positions are sampled at the same timestamp to ensure temporal
          alignment with gaze data.
        - Submission tracking uses the moving SUBMIT target dot, not the static
          SUBMIT text.
        - A minimum number of samples (currently 12) is required before any decision
          logic is evaluated to avoid unstable early behavior.
        """
        super().set_gaze(x, y)

        gx, gy = self.map_gaze_to_widget()
        if gx is None or gy is None:
            self._candidate = None
            self._candidate_count = 0
            self._submit_count = 0
            return

        t = time.monotonic() - self._t0
        opt_pos, submit_rect, submit_dot, _ = self._targets_at_time(t)

        sx, sy = submit_dot

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
        """
        Compute the combined smooth pursuit score for a given option label.

        The score reflects how well the user's gaze follows the moving target
        associated with the given option. It combines:
        - a correlation-based term measuring temporal similarity between gaze and
          target motion, and
        - a proximity-based term measuring spatial closeness.

        Correlation is computed independently for the X and Y dimensions and
        averaged. Proximity is computed as a Gaussian-weighted mean distance over
        the current rolling window. Both terms are mapped to the range [-1, 1] and
        linearly combined.

        Parameters
        ----------
        lab : str
            Option label for which the score is computed.

        Returns
        -------
        float
            Combined option score in the range [-1.0, 1.0], where higher values
            indicate stronger evidence that the user is intentionally following
            the option's target.

        Notes
        -----
        - If lag compensation is enabled, the maximum Pearson correlation across a
          range of temporal lags is used to account for eye–target latency.
        - Correlation contributes a weight of `self.corr_weight`, while spatial
          proximity contributes `self.proximity_weight` to the final score.
        - The proximity term is computed over the same rolling time window as the
          correlation term to ensure temporal consistency.
        - This score is used for candidate selection but does not directly trigger
          actions; stability over multiple samples is required.
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

        corr = 0.5 * (cx + cy)  # [-1,1]

        # proximity (window-mean), mapped to [-1,1]
        dist = np.sqrt((gx - tx) ** 2 + (gy - ty) ** 2)
        prox = float(np.mean(gaussian_proximity(dist, self.proximity_sigma_px)))  # 0..1
        prox_mapped = (2.0 * prox) - 1.0

        return float((self.corr_weight * corr) + (self.proximity_weight * prox_mapped))

    def _submit_score(self) -> float:
        """
        Compute the smooth pursuit score for the SUBMIT target.

        The SUBMIT target moves horizontally only; therefore, correlation is
        evaluated exclusively along the X-axis. This correlation term is combined
        with a spatial proximity term to determine how strongly the user's gaze
        indicates intent to submit.

        Both correlation and proximity are computed over the current rolling time
        window and mapped to the range [-1, 1] before being linearly combined.

        Returns
        -------
        float
            Combined submit score in the range [-1.0, 1.0], where higher values
            indicate stronger evidence that the user is intentionally following
            the SUBMIT target.

        Notes
        -----
        - Only X-axis correlation is used, as the SUBMIT target does not move
          vertically.
        - If lag compensation is enabled, the maximum Pearson correlation across
          a range of temporal lags is used to account for eye–target latency.
        - The spatial proximity term ensures robustness against brief gaze
          deviations and complements the correlation-based measure.
        - Submission is triggered only after this score remains above threshold
          for a sufficient number of consecutive samples.
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
        """
        Select a YES/NO option and update internal state and logs.

        This method sets the current selection to the given choice, emits the
        corresponding click signal for logging, and activates a cooldown period
        during which no further selection changes are allowed.

        Parameters
        ----------
        choice : str
            The selected option label (e.g., "yes" or "no").

        Returns
        -------
        None

        Notes
        -----
        - This widget uses single-selection semantics; any previous selection is
          replaced.
        - A short auditory feedback (beep) is emitted upon selection.
        - The toggle cooldown prevents rapid or accidental repeated selections.
        """
        self.selected = choice

        self.log_toggles += 1
        self.click_index += 1
        self.clicked.emit(self.click_index, f"select:{choice}")
        QApplication.beep()

        self._toggle_block_until = self._now() + (self.toggle_cooldown_ms / 1000.0)

    def _submit(self) -> None:
        """
        Submit the currently selected YES/NO choice.

        This method emits a submission event if submission is allowed under the
        current configuration and state. It logs the submit action, provides
        auditory feedback, and activates a submission cooldown to prevent
        accidental repeated submissions.

        If empty submission is disabled and no option is currently selected,
        the method returns without taking any action.

        Returns
        -------
        None

        Notes
        -----
        - When `allow_empty_submit` is False, submission requires a valid selection.
        - The emitted `submitted` signal contains only the selected choice string
          ("yes" or "no"), or an empty string if empty submission is allowed.
        - A cooldown period is enforced after submission to avoid multiple rapid
          submissions.
        """
        if (not self.allow_empty_submit) and (self.selected is None):
            return

        self.click_index += 1
        self.clicked.emit(self.click_index, "submit")
        QApplication.beep()

        self._submit_block_until = self._now() + (self.submit_cooldown_ms / 1000.0)

        # IMPORTANT: emit ONLY choice string for consistent logging
        self.submitted.emit(self.selected if self.selected is not None else "")

    def _update_decision(self) -> None:
        """
        Update selection and submission decisions based on accumulated gaze data.

        This method evaluates the current rolling-window evidence for:
        - selecting one of the YES/NO options, and
        - submitting the current selection.

        Option selection and submission are handled independently but coordinated
        through cooldowns and stability counters to prevent accidental or repeated
        actions.

        Decision logic proceeds in three stages:
        1. Compute smooth pursuit scores for all options and determine the best
           candidate above the correlation threshold.
        2. Compute the submit score based on the SUBMIT target.
        3. Trigger submission (if eligible) before triggering option selection.

        Returns
        -------
        None

        Notes
        -----
        - Option scores are compared against `corr_threshold`; only the strongest
          candidate above this threshold is considered.
        - A candidate must remain stable for `toggle_stable_samples` consecutive
          samples before being selected.
        - Submission requires the submit score to remain above
          `submit_corr_threshold` for `submit_stable_samples` consecutive samples.
        - Submission is evaluated before option selection to avoid unintended
          toggles immediately before submission.
        - Cooldown timers (`_toggle_block_until`, `_submit_block_until`) prevent
          repeated actions within short time intervals.
        - Upon submission, all candidate tracking state is reset.
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

        # select
        if now >= self._toggle_block_until:
            if self._candidate is not None and self._candidate_count >= self.toggle_stable_samples:
                lab = self._candidate
                self._candidate = None
                self._candidate_count = 0
                self._select(lab)

    # ---------------- Drawing ----------------

    def paintEvent(self, event):
        """
        Render the complete visual state of the Yes/No smooth pursuit widget.

        This method draws all static and dynamic UI elements, including:
        - background and instructions,
        - the central question text,
        - YES and NO option labels with their moving pursuit targets,
        - the SUBMIT text and its moving target dot,
        - visual highlights for current candidates,
        - and the current gaze position.

        Rendering is performed continuously via a timer to support smooth animation
        of moving targets.

        Parameters
        ----------
        event : QPaintEvent
            Qt paint event (unused, but required by Qt's paintEvent signature).

        Returns
        -------
        None

        Notes
        -----
        - The background is cleared to black on every frame.
        - All positions are computed dynamically based on the current widget size
          and elapsed time since initialization.
        - Static elements (question text, labels, SUBMIT text) remain fixed, while
          target dots move along predefined paths.
        - The option with the highest current score above `corr_threshold` is
          visually highlighted to provide feedback.
        - The SUBMIT target dot moves horizontally along a visible guide line.
        - The user's current gaze position is rendered as a red dot for debugging
          and feedback purposes.
        - Antialiasing is enabled to ensure smooth visual appearance.
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

            sel_txt = (self.selected.upper() if self.selected else "-")
            info_rect = QRect(28, 18, w - 56, int(h * 0.13))
            painter.drawText(
                info_rect,
                Qt.AlignLeft | Qt.AlignVCenter | Qt.TextWordWrap,
                "Follow the moving DOT to SELECT YES/NO. Follow SUBMIT to submit.\n"
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

            # ----- draw orbit outlines (grey rectangles) -----
            orbit_pen = QPen(Qt.gray)
            orbit_pen.setWidth(2)
            painter.setPen(orbit_pen)
            painter.setBrush(Qt.NoBrush)

            for lab in self.labels:
                cx, cy = centers[lab]
                hw = float(orbit_params[lab]["half_w"])
                hh = float(orbit_params[lab]["half_h"])
                painter.drawRect(QRect(int(cx - hw), int(cy - hh), int(2 * hw), int(2 * hh)))

            # ----- draw static labels + moving target dots -----
            # display mapping (YES/NO nicer)
            disp = {
                self.labels[0]: "YES" if self.labels[0].lower() == "yes" else str(self.labels[0]).upper(),
                self.labels[1]: "NO" if self.labels[1].lower() == "no" else str(self.labels[1]).upper(),
            }

            for lab in self.labels:
                cx, cy = centers[lab]
                selected = (lab == self.selected)
                highlight = (lab == highlight_opt)

                # static text label (stays at center)
                self._draw_static_label(painter, cx, cy, disp.get(lab, str(lab)), selected=selected,
                                        highlight=highlight)

                # moving dot target (follow this)
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

        This method renders the textual YES/NO label centered at the given
        coordinates. The label itself does not move; only its associated target
        dot is animated. Visual styling reflects the current interaction state.

        Parameters
        ----------
        painter : QPainter
            Active Qt painter used for rendering.
        cx : float
            X-coordinate of the label center.
        cy : float
            Y-coordinate of the label center.
        text : str
            Text to display (e.g., "YES" or "NO").
        selected : bool
            Whether this option is currently selected.
            Selected labels are drawn in green.
        highlight : bool
            Whether this option is currently the best pursuit candidate.
            Highlighted labels are drawn with increased pen width.

        Returns
        -------
        None

        Notes
        -----
        - The label is rendered in a bold font to ensure readability at a distance.
        - Pen color and thickness encode interaction state:
            - selected > highlight > normal
        - The label rectangle is centered on (`cx`, `cy`) and sized to comfortably
          contain short option texts without clipping.
        """
        f = painter.font()
        f.setBold(True)
        f.setPointSize(max(24, int(self.height() * 0.038)))  # kleiner
        painter.setFont(f)

        if selected:
            painter.setPen(QPen(Qt.green, 6))
        elif highlight:
            painter.setPen(QPen(Qt.white, 4))
        else:
            painter.setPen(QPen(Qt.white, 3))

        rect = QRect(int(cx - 140), int(cy - 60), 280, 120)
        painter.drawText(rect, Qt.AlignCenter, text)

    def _draw_target_dot(self, painter: QPainter, x: float, y: float, selected: bool, highlight: bool):
        """
        Draw a moving target dot used for smooth pursuit interaction.

        This method renders the small circular target that the user is expected to
        follow with their gaze. The dot's appearance encodes the current interaction
        state of the associated option.

        Parameters
        ----------
        painter : QPainter
            Active Qt painter used for rendering.
        x : float
            X-coordinate of the target dot.
        y : float
            Y-coordinate of the target dot.
        selected : bool
            Whether the associated option is currently selected.
            Selected targets are drawn in green and slightly larger.
        highlight : bool
            Whether the associated option is currently the best pursuit candidate.
            Highlighted targets are drawn slightly larger to provide feedback.

        Returns
        -------
        None

        Notes
        -----
        - The dot is drawn without an outline to reduce visual clutter.
        - Dot size scales with widget height to maintain visibility across screen
          sizes.
        - Visual priority follows: selected > highlight > normal.
        - The target dot represents the actual pursuit stimulus used in decision
          making.
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
        Draw the SUBMIT UI element consisting of static text and a moving target dot.

        This method renders:
        - a static SUBMIT text label (optionally including the current selection), and
        - a moving target dot that the user must follow with their gaze to trigger
          submission.

        The SUBMIT text remains fixed in place for readability, while the dot moves
        horizontally and serves as the actual smooth pursuit stimulus.

        Parameters
        ----------
        painter : QPainter
            Active Qt painter used for rendering.
        rect : QRect
            Rectangle defining the position and size of the static SUBMIT text.
        dot : tuple[float, float]
            Current (x, y) position of the moving SUBMIT target dot.

        Returns
        -------
        None

        Notes
        -----
        - The SUBMIT text is rendered in a non-bold, slightly smaller font to avoid
          visual dominance and text clipping.
        - Text padding and word wrapping are applied to ensure readability even when
          the selection string is long.
        - The appearance of the target dot reflects submission state:
            - disabled (no selection): gray
            - enabled: white
            - strong submit evidence: slightly larger dot
        - The dot, not the text, is used for correlation and proximity-based
          submission decisions.
        """
        f = painter.font()
        f.setBold(False)  # was: True
        f.setPointSize(max(20, int(self.height() * 0.034)))  # was: 0.038 scale
        painter.setFont(f)

        sel_txt = (self.selected.upper() if self.selected else "-")
        enabled = (self.allow_empty_submit or (self.selected is not None))

        # --- static text (with padding + wrap) ---
        if not enabled:
            painter.setPen(QPen(Qt.gray, 3))
        else:
            painter.setPen(QPen(Qt.white, 4))

        painter.drawText(
            rect.adjusted(12, 6, -12, -6),
            Qt.AlignCenter | Qt.TextWordWrap,
            f"SUBMIT ({sel_txt})",
        )

        # --- moving target dot (follow THIS) ---
        x, y = dot
        painter.setPen(Qt.NoPen)

        if not enabled:
            painter.setBrush(Qt.gray)
            r = max(9, int(self.height() * 0.016))
        else:
            # optional highlight if submit score is high
            if self._last_submit_score >= self.submit_corr_threshold:
                painter.setBrush(Qt.white)
                r = max(11, int(self.height() * 0.020))
            else:
                painter.setBrush(Qt.white)
                r = max(9, int(self.height() * 0.016))

        painter.drawEllipse(int(x) - r, int(y) - r, 2 * r, 2 * r)

