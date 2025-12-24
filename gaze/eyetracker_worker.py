# gaze/eyetracker_worker.py

from __future__ import annotations

import cv2
import numpy as np
from PySide6.QtCore import QThread, Signal


class EyeTrackerWorker(QThread):
    """
    Worker thread that continuously reads frames from a camera and emits gaze/blink signals.

    This thread:
    - captures frames from the default camera (index 0),
    - uses `estimator.extract_features(frame)` to obtain facial features and blink state,
    - emits blink state on every processed frame,
    - if a face is detected and the user is not blinking, predicts gaze coordinates,
    - optionally smooths the gaze signal with a provided `smoother`,
    - emits the smoothed gaze coordinates.

    Signals
    -------
    gaze_updated(float, float)
        Emitted with (x, y) gaze coordinates (typically screen-space coordinates).
    status_updated(str)
        Emitted with a human-readable status string (e.g., no face / blink).
        Empty string indicates nominal tracking.
    blink_state(bool)
        Emitted every frame with current blink state (True if blinking).

    Notes
    -----
    - The worker intentionally does not emit gaze coordinates when:
        - no face is detected (features is None), or
        - a blink is detected (blink is True).
    - The camera is released on thread exit.
    """

    gaze_updated = Signal(float, float)
    status_updated = Signal(str)
    blink_state = Signal(bool)

    def __init__(self, estimator, smoother, parent=None):
        """
        Initialize the worker thread.

        Parameters
        ----------
        estimator : Any
            Object providing:
              - extract_features(frame) -> (features, blink)
              - predict(np.ndarray) -> array-like of (x, y)
        smoother : Any
            Object providing:
              - step(x: int, y: int) -> (x_smooth, y_smooth)
        parent : QObject, optional
            Parent Qt object.

        Notes
        -----
        - The worker starts in a running state. Call `stop()` to request termination.
        """
        super().__init__(parent)
        self.estimator = estimator
        self.smoother = smoother
        self._running = True

    def stop(self):
        """
        Request the worker thread to stop.

        Returns
        -------
        None

        Notes
        -----
        - This sets an internal flag checked in the capture loop.
        - The thread will exit after the next loop iteration completes.
        """
        self._running = False

    def run(self):
        """
        Thread entry point: capture frames, estimate gaze, and emit signals.

        Returns
        -------
        None

        Notes
        -----
        - Opens the default camera via OpenCV (`cv2.VideoCapture(0)`).
        - Emits `blink_state` for every frame read.
        - Emits `status_updated` with:
            - "No face recognized" when features are missing,
            - "Blink detected" when blink is True,
            - "" for nominal operation.
        - Emits `gaze_updated` only when face is detected and not blinking.
        """
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("Failed to open camera.")
            return

        while self._running:
            ret, frame = cap.read()
            if not ret:
                continue

            features, blink = self.estimator.extract_features(frame)

            self.blink_state.emit(bool(blink))

            if features is None:
                self.status_updated.emit("No face recognized")
                continue

            if blink:
                self.status_updated.emit("Blink detected")
                continue

            x, y = self.estimator.predict(np.array([features]))[0]

            x_pred, y_pred = self.smoother.step(int(x), int(y))

            self.status_updated.emit("")
            self.gaze_updated.emit(float(x_pred), float(y_pred))

        cap.release()
        print("EyeTrackerWorker terminated")
