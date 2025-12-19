# gaze/eyetracker_worker.py

import cv2
from PySide6.QtCore import QThread, Signal
import numpy as np


class EyeTrackerWorker(QThread):
    gaze_updated = Signal(float, float)
    status_updated = Signal(str)    # <- current status (blinking coords, face?)
    blink_state = Signal(bool)      # <- current blink-state (True/False)

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

            # emit blink-state in every frame
            self.blink_state.emit(bool(blink))

            if features is None:
                # no face recognized
                self.status_updated.emit("No face recognized")
                continue

            if blink:
                # blink detected
                self.status_updated.emit("Blink detected")
                continue

            # gaze coords
            x, y = self.estimator.predict(np.array([features]))[0]

            # kalman coords
            x_pred, y_pred = self.smoother.step(int(x), int(y))

            # default status (coordinates, no blink, face ok)
            self.status_updated.emit("")
            self.gaze_updated.emit(float(x_pred), float(y_pred))

        cap.release()
        print("EyeTrackerWorker terminated")
