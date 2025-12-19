# ui/SmoothPursuit_YesNoWidget.py

from __future__ import annotations
import math
from collections import deque
from typing import Deque, Tuple, Optional
from PySide6.QtCore import QElapsedTimer, QTimer, Slot, Qt, Signal
from PySide6.QtGui import QPainter, QBrush
from PySide6.QtWidgets import QApplication

from ui.gaze_widget import GazeWidget


class SmoothPursuitYesNoWidget(GazeWidget):

    submitted = Signal(object)  # "yes" oder "no"

    def __init__(
        self,
        question: str,
        parent=None,
        window_ms: int = 1500,
        eval_interval_ms: int = 100,
        min_window_ms: int = 900,
        min_stable_evals: int = 3,
        max_mean_dist_px: float = 120.0,
        min_dist_margin_px: float = 35.0,
    ):
        super().__init__(parent)

        self.question = question

        # --- Smooth-Pursuit Parameter ---
        self.window_ms = int(window_ms)
        self.eval_interval_ms = int(eval_interval_ms)
        self.min_window_ms = int(min_window_ms)
        self.min_stable_evals = int(min_stable_evals)
        self.max_mean_dist_px = float(max_mean_dist_px)
        self.min_dist_margin_px = float(min_dist_margin_px)

        # Kreisbahn-Parameter (werden zur Laufzeit anhand der Widgetgröße interpretiert)
        # eine 360°-Rotation in ca. 4 Sekunden
        self.angular_speed = 2.0 * math.pi / 4.0

        # Zeitbasis für Target-Bewegung
        self._motion_timer = QElapsedTimer()
        self._motion_timer.start()

        # Gaze-Historie: deque mit (t_ms, x, y) in Widget-Koordinaten
        self._gaze_history: Deque[Tuple[float, float, float]] = deque()

        # Auswertungs-Timer
        self._eval_timer = QTimer(self)
        self._eval_timer.timeout.connect(self._evaluate_selection)
        self._eval_timer.start(self.eval_interval_ms)

        # Auswahlzustand
        self.selection: Optional[str] = None  # "yes" oder "no"
        self._submitted = False

        # Stabilitäts-Tracking für Entscheidungen
        self._last_best_label: Optional[str] = None
        self._stable_eval_count: int = 0

        # ---------- LOGGING ----------
        self.log_toggles = 0
        self.log_resets = 0
        self.log_backspaces = 0
        self.log_submits = 0
        self.log_extra = (
            f"smooth_pursuit_yesno;"
            f"window_ms={self.window_ms};"
            f"eval_interval_ms={self.eval_interval_ms};"
            f"min_window_ms={self.min_window_ms};"
            f"min_stable_evals={self.min_stable_evals};"
            f"max_mean_dist_px={self.max_mean_dist_px};"
            f"min_dist_margin_px={self.min_dist_margin_px};"
            f"angular_speed={self.angular_speed}"
        )
        # -----------------------------

    # ------------------------------------------------------------------
    #   Slots
    # ------------------------------------------------------------------

    @Slot(float, float)
    def set_gaze(self, x: float, y: float):
        """
        Gaze-Position aktualisieren und in die Gaze-Historie einfügen.
        Die eigentliche Auswertung erfolgt im Timer (_evaluate_selection).
        """
        super().set_gaze(x, y)

        gx, gy = self.map_gaze_to_widget()
        if gx is None:
            return

        t_ms = float(self._motion_timer.elapsed())
        self._gaze_history.append((t_ms, float(gx), float(gy)))

        # alte Samples entfernen, die außerhalb des Fensters liegen
        min_time = t_ms - self.window_ms
        while self._gaze_history and self._gaze_history[0][0] < min_time:
            self._gaze_history.popleft()

    # ------------------------------------------------------------------
    #   Smooth Pursuit Auswertung
    # ------------------------------------------------------------------

    def _target_position(self, which: str, t_ms: float) -> Tuple[float, float]:
        """
        Berechnet die Position des Targets 'yes' oder 'no' zum Zeitpunkt t_ms
        in Widget-Koordinaten.
        """
        w = max(1, self.width())
        h = max(1, self.height())

        cx = w / 2.0
        cy = h / 2.0

        # Radius relativ zur kleineren Dimension
        r = 0.32 * min(w, h)

        # Zeit in Sekunden
        t = t_ms / 1000.0

        if which == "yes":
            angle = self.angular_speed * t
        else:  # "no"
            # entgegengesetzte Richtung + Phasenversatz
            angle = -self.angular_speed * t + math.pi

        x = cx + r * math.cos(angle)
        y = cy + r * math.sin(angle)
        return x, y

    def _evaluate_selection(self):
        """Wird periodisch vom QTimer aufgerufen, um eine Entscheidung zu treffen."""
        if self._submitted:
            return

        if len(self._gaze_history) < 12:
            # zu wenige Punkte für sinnvolle Auswertung
            return

        samples = list(self._gaze_history)
        times = [s[0] for s in samples]

        # sicherstellen, dass das Zeitfenster groß genug ist
        window_span = times[-1] - times[0]
        if window_span < self.min_window_ms:
            return

        gx_vals = [s[1] for s in samples]
        gy_vals = [s[2] for s in samples]

        # Durchschnittsdistanz zu YES- und NO-Trajektorie berechnen
        mean_dist = {}
        for label in ("yes", "no"):
            total_dist = 0.0
            for t_ms, gx, gy in zip(times, gx_vals, gy_vals):
                tx, ty = self._target_position(label, t_ms)
                dx = gx - tx
                dy = gy - ty
                total_dist += math.hypot(dx, dy)
            mean_dist[label] = total_dist / len(samples)

        mean_yes = mean_dist["yes"]
        mean_no = mean_dist["no"]

        # beste und zweitbeste Distanz bestimmen
        if mean_yes < mean_no:
            best_label = "yes"
            best_dist = mean_yes
            other_dist = mean_no
        else:
            best_label = "no"
            best_dist = mean_no
            other_dist = mean_yes

        # Kriterien für gültige Auswahl:
        #   - mittlere Distanz unter Threshold
        #   - deutlich besser als die andere Option
        if not (
            best_dist <= self.max_mean_dist_px
            and (other_dist - best_dist) >= self.min_dist_margin_px
        ):
            # Kriterien nicht erfüllt -> Stabilität zurücksetzen
            self._last_best_label = None
            self._stable_eval_count = 0
            return

        # Stabilität prüfen: mehrmals in Folge derselbe beste Kandidat
        if best_label == self._last_best_label:
            self._stable_eval_count += 1
        else:
            self._last_best_label = best_label
            self._stable_eval_count = 1

        if self._stable_eval_count >= self.min_stable_evals:
            self._confirm_selection(best_label)

    def _confirm_selection(self, label: str):
        """Endgültige Auswahl treffen und submitted-Signal emittieren."""
        if self._submitted:
            return
        if label not in ("yes", "no"):
            return

        self.selection = label
        self._submitted = True

        self.log_toggles += 1
        self.log_submits += 1

        QApplication.beep()
        print(f"SmoothPursuitYesNo selection: {label}")
        self.submitted.emit(label)

        self._eval_timer.stop()
        self.update()

    # ------------------------------------------------------------------
    #   Zeichnen
    # ------------------------------------------------------------------

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.black)
        painter.setRenderHint(QPainter.Antialiasing, True)

        w = self.width()
        h = self.height()

        # Frage in der Mitte
        painter.setPen(Qt.white)
        font = painter.font()
        font.setPointSize(max(12, int(h * 0.035)))
        painter.setFont(font)

        question_rect = self.rect().adjusted(
            int(w * 0.1),
            int(h * 0.15),
            -int(w * 0.1),
            -int(h * 0.55),
        )
        painter.drawText(
            question_rect,
            Qt.AlignCenter | Qt.TextWordWrap,
            self.question,
        )

        # Aktuelle Target-Positionen berechnen
        t_now = float(self._motion_timer.elapsed())
        yes_x, yes_y = self._target_position("yes", t_now)
        no_x, no_y = self._target_position("no", t_now)

        target_radius = max(25, int(min(w, h) * 0.04))

        # YES-Target
        if self.selection == "yes":
            painter.setBrush(QBrush(Qt.darkGreen))
        else:
            painter.setBrush(QBrush(Qt.gray))
        painter.setPen(Qt.white)
        painter.drawEllipse(
            int(yes_x) - target_radius,
            int(yes_y) - target_radius,
            2 * target_radius,
            2 * target_radius,
        )
        painter.drawText(
            int(yes_x) - target_radius,
            int(yes_y) - target_radius,
            2 * target_radius,
            2 * target_radius,
            Qt.AlignCenter,
            "YES",
        )

        # NO-Target
        if self.selection == "no":
            painter.setBrush(QBrush(Qt.darkRed))
        else:
            painter.setBrush(QBrush(Qt.gray))
        painter.setPen(Qt.white)
        painter.drawEllipse(
            int(no_x) - target_radius,
            int(no_y) - target_radius,
            2 * target_radius,
            2 * target_radius,
        )
        painter.drawText(
            int(no_x) - target_radius,
            int(no_y) - target_radius,
            2 * target_radius,
            2 * target_radius,
            Qt.AlignCenter,
            "NO",
        )

        # Gaze-Punkt (vom GazeWidget)
        gx, gy = self.map_gaze_to_widget()
        if gx is not None:
            painter.setBrush(QBrush(Qt.red))
            painter.setPen(Qt.NoPen)
            r = self.point_radius
            painter.drawEllipse(int(gx) - r, int(gy) - r, 2 * r, 2 * r)
