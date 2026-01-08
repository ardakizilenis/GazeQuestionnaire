# gaze/eyetracker_worker.py

from __future__ import annotations

import cv2
import numpy as np
from PySide6.QtCore import QThread, Signal


class EyeTrackerWorker(QThread):
    gaze_updated = Signal(float, float)
    status_updated = Signal(str)
    blink_state = Signal(bool)

    def __init__(self, estimator, smoother, parent=None):
        super().__init__(parent)
        self.estimator = estimator
        self.smoother = smoother
        self._running = True

    def stop(self):
        self._running = False

    def run(self):
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
