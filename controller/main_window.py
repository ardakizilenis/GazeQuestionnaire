# widgets/main_window.py

from __future__ import annotations

import os
import re
import time
import csv
from datetime import datetime
from typing import Any, Dict, List, Optional

from PySide6.QtWidgets import QMainWindow, QApplication

from gaze.eyetracker_worker import EyeTrackerWorker
from widgets.question_types.InfoWidget import InfoWidget
from widgets.question_types.LikertScaleQuestionWidget import LikertScaleQuestionWidget
from widgets.question_types.MultipleChoiceQuestionWidget import MultipleChoiceQuestionWidget
from widgets.question_types.SmoothPursuit_LikertScaleWidget import SmoothPursuitLikertScaleWidget
from widgets.question_types.SmoothPursuit_MultipleChoiceWidget import SmoothPursuitMultipleChoiceWidget
from widgets.question_types.SmoothPursuit_YesNoWidget import SmoothPursuitYesNoWidget
from widgets.question_types.TextInputWidget import TextInputWidget
from widgets.question_types.YesNoQuestionWidget import YesNoQuestionWidget


class MainWindow(QMainWindow):
    LOG_COLUMNS = [
        "question_index",
        "question_type",
        "activation_mode",
        "question_text",
        "result",
        "rt_sec",
        "n_toggles",
        "n_resets",
        "n_backspaces",
        "calibration",
        "filter",
        "dwell_threshold_ms",
        "blink_threshold_ms",
        "gazepoint_blocked",
        "theme",
    ]

    CLICK_COLUMNS = [
        "q_index",
        "q_type",
        "q_activation",
        "q_labels",
        "q_toggle_index",
        "q_click_time_no_reset",
        "q_click_time",
        "q_toggled_area",
    ]

    def __init__(self, estimator, smoother, calibration_method, filter_method, dwell_threshold, blink_threshold, gazepoint_blocked, theme, parent, file_name) -> None:
        super().__init__(parent)

        self.estimator = estimator
        self.smoother = smoother
        self.calibration = calibration_method
        self.filter = filter_method
        self.blink_threshold = blink_threshold
        self.dwell_threshold = dwell_threshold
        self.gazepoint_blocked = gazepoint_blocked
        self.theme = theme
        self.parent = parent

        self.setWindowTitle("Gaze Questionnaire")
        self.showFullScreen()

        self.question_queue: List[Dict[str, Any]] = []
        self.current_index: int = -1
        self.current_widget = None
        self.question_counter: int = 0

        self.worker: Optional[EyeTrackerWorker] = None

        self.log_rows: List[Dict[str, Any]] = []
        self.click_rows: List[Dict[str, Any]] = []
        self.question_start_time: Optional[float] = None
        self.last_click_time: Optional[float] = None
        self.current_qmeta: Optional[Dict[str, Any]] = None

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        data_root = os.path.join(base_dir, "data")
        os.makedirs(data_root, exist_ok=True)

        filename = re.sub(".json", "", file_name)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_dir = os.path.join(data_root, f"{filename}_{timestamp}")
        os.makedirs(self.run_dir, exist_ok=True)

        self.log_filename = os.path.join(self.run_dir, "gaze_questionnaire_log.csv")
        self.click_filename = os.path.join(self.run_dir, "gaze_questionnaire_clicks.csv")

    def info(self, text: str, duration_sec: int) -> None:
        self.question_queue.append(
            {"type": "info", "text": text, "duration": int(duration_sec), "activation": None}
        )

    def enqueue_yesno(self, question: str, activation_mode: str) -> None:
        self.question_queue.append({"type": "yesno", "text": question, "activation": activation_mode})

    def enqueue_mcq(self, question: str, activation_mode: str, labels=None) -> None:
        self.question_queue.append(
            {"type": "mcq", "text": question, "activation": activation_mode, "labels": labels}
        )

    def enqueue_likert(self, question: str, activation_mode: str, labels: Optional[List[str]] = None) -> None:
        self.question_queue.append(
            {"type": "likert", "text": question, "activation": activation_mode, "labels": labels}
        )

    def enqueue_textgrid(self, question: str, activation_mode: str) -> None:
        self.question_queue.append({"type": "textgrid", "text": question, "activation": activation_mode})

    def enqueue_smoothpursuit_yesno(self, question: str) -> None:
        self.question_queue.append({"type": "sp_yesno", "text": question, "activation": "smooth_pursuit"})

    def enqueue_smoothpursuit_mcq(self, question: str, labels=None) -> None:
        self.question_queue.append(
            {"type": "sp_mcq", "text": question, "activation": "smooth_pursuit", "labels": labels}
        )

    def enqueue_smoothpursuit_likert(self, question: str, labels=None) -> None:
        self.question_queue.append(
            {"type": "sp_likert", "text": question, "activation": "smooth_pursuit", "labels": labels}
        )

    def start_questionnaire(self) -> None:
        if self.worker is None:
            self.worker = EyeTrackerWorker(self.estimator, self.smoother)
            self.worker.start()

        self.current_index = -1
        self.show_next_question()

    def disconnect_current_widget(self) -> None:
        if self.worker is None or self.current_widget is None:
            return

        try:
            self.worker.gaze_updated.disconnect(self.current_widget.set_gaze)
        except Exception:
            pass

        if hasattr(self.current_widget, "set_blinking"):
            try:
                self.worker.blink_state.disconnect(self.current_widget.set_blinking)
            except Exception:
                pass

        if hasattr(self.current_widget, "clicked"):
            try:
                self.current_widget.clicked.disconnect(self.on_widget_clicked)
            except Exception:
                pass

    def show_next_question(self) -> None:
        self.disconnect_current_widget()
        self.current_index += 1

        if self.current_index >= len(self.question_queue):
            self.finish_questionnaire()
            return

        meta = self.question_queue[self.current_index]

        logical_index: int | None = None
        if meta["type"] != "info":
            self.question_counter += 1
            logical_index = self.question_counter

        match meta["type"]:

            case "info":
                widget = InfoWidget(
                    text = meta.get("text", ""),
                    duration_sec = meta.get("duration", 5),
                    parent = self.parent,
                    gazepoint_blocked = self.gazepoint_blocked,
                    theme=self.theme
                )
            case "yesno":
                widget = YesNoQuestionWidget(
                    question = meta.get("text", ""),
                    activation_mode = meta.get("activation"),
                    parent=self.parent,
                    gazepoint_blocked = self.gazepoint_blocked,
                    dwell_threshold_ms = self.dwell_threshold,
                    blink_threshold_ms = self.blink_threshold,
                    theme=self.theme
                )
            case "mcq":
                widget = MultipleChoiceQuestionWidget(
                    question = meta.get("text", ""),
                    activation_mode = meta.get("activation"),
                    labels = meta.get("labels"),
                    parent = self.parent,
                    gazepoint_blocked = self.gazepoint_blocked,
                    dwell_threshold_ms = self.dwell_threshold,
                    blink_threshold_ms = self.blink_threshold,
                    theme=self.theme
                )
            case "likert":
                widget = LikertScaleQuestionWidget(
                    question = meta.get("text", ""),
                    activation_mode = meta.get("activation"),
                    labels = meta.get("labels"),
                    parent = self.parent,
                    gazepoint_blocked=self.gazepoint_blocked,
                    dwell_threshold_ms=self.dwell_threshold,
                    blink_threshold_ms=self.blink_threshold,
                    theme=self.theme
                )
            case "textgrid":
                widget = TextInputWidget(
                    question = meta.get("text", ""),
                    activation_mode = meta.get("activation"),
                    parent = self.parent,
                    gazepoint_blocked = self.gazepoint_blocked,
                    dwell_threshold_ms = self.dwell_threshold,
                    blink_threshold_ms = self.blink_threshold,
                    theme=self.theme
                )
            case "sp_yesno":
                widget = SmoothPursuitYesNoWidget(
                    meta.get("text", ""),
                    parent = self.parent,
                    gazepoint_blocked = self.gazepoint_blocked,
                    theme=self.theme
                )
            case "sp_mcq":
                widget = SmoothPursuitMultipleChoiceWidget(
                    meta.get("text", ""),
                    parent = self.parent,
                    labels=meta.get("labels"),
                    gazepoint_blocked=self.gazepoint_blocked,
                    theme=self.theme
                )
            case "sp_likert":
                widget = SmoothPursuitLikertScaleWidget(
                    meta.get("text", ""),
                    parent = self.parent,
                    labels=meta.get("labels"),
                    gazepoint_blocked=self.gazepoint_blocked,
                    theme=self.theme
                )
            case _ :
                print("Question Type unknown:", meta["type"])
                self.show_next_question()
                return

        self.current_widget = widget
        self.setCentralWidget(widget)

        if self.worker is not None:
            self.worker.gaze_updated.connect(widget.set_gaze)
            if hasattr(widget, "set_blinking"):
                self.worker.blink_state.connect(widget.set_blinking)

        if hasattr(widget, "submitted"):
            widget.submitted.connect(self.on_question_submitted)

        if hasattr(widget, "clicked"):
            widget.clicked.connect(self.on_widget_clicked)

        self.question_start_time = time.monotonic()
        self.last_click_time = self.question_start_time
        self.current_qmeta = {
            "index": logical_index,
            "type": meta["type"],
            "text": meta.get("text", ""),
            "labels": meta.get("labels"),
            "activation": meta.get("activation", ""),
            "dwell_threshold_ms": self.dwell_threshold,
            "blink_threshold_ms": self.blink_threshold,
            "gazepoint_blocked": self.gazepoint_blocked,
            "calibration": self.calibration,
            "filter": self.filter,
            "theme": self.theme,
        }

    def on_widget_clicked(self, toggle_index, toggled_area):

        if self.question_start_time is None:
            return

        now = time.monotonic()
        time_from_start = now - self.question_start_time

        time_since_last_click = None if self.last_click_time is None else (now - self.last_click_time)
        self.last_click_time = now

        meta = self.current_qmeta or {}
        if meta.get("type") == "info":
            return

        self.click_rows.append(
            {
                "q_index": meta.get("index"),
                "q_type": meta.get("type"),
                "q_activation": meta.get("activation", ""),
                "q_labels": repr(meta.get("labels")),
                "q_toggle_index": int(toggle_index),
                "q_click_time_no_reset": round(time_from_start, 3),
                "q_click_time": None if time_since_last_click is None else round(time_since_last_click, 3),
                "q_toggled_area": str(toggled_area),
            }
        )

    def on_question_submitted(self, result):
        end_time = time.monotonic()
        rt_sec = end_time - self.question_start_time if self.question_start_time is not None else None

        widget = self.current_widget
        meta = self.current_qmeta or {}
        qtype = meta.get("type")
        qnum = meta.get("index")

        if qtype != "info" and widget is not None:
            log_entry = {
                "question_index": qnum,
                "question_type": qtype,
                "activation_mode": meta.get("activation"),
                "question_text": meta.get("text"),
                "result": repr(result),
                "rt_sec": None if rt_sec is None else round(rt_sec, 3),
                "n_toggles": getattr(widget, "log_toggles", 0),
                "n_resets": getattr(widget, "log_resets", 0),
                "n_backspaces": getattr(widget, "log_backspaces", 0),
                "calibration": meta.get("calibration"),
                "filter":meta.get("filter"),
                "dwell_threshold_ms": meta.get("dwell_threshold_ms"),
                "blink_threshold_ms": meta.get("blink_threshold_ms"),
                "gazepoint_blocked": meta.get("gazepoint_blocked"),
                "theme": meta.get("theme")
            }
            self.log_rows.append(log_entry)

        self.show_next_question()

    def write_logs_to_csv(self) -> None:
        if not self.log_rows:
            print("No loggs have been saved")
            return

        rows = sorted(self.log_rows, key=lambda r: (r.get("question_index") is None, r.get("question_index")))

        extra_cols = sorted({k for row in rows for k in row.keys()} - set(self.LOG_COLUMNS))
        fieldnames = self.LOG_COLUMNS + extra_cols

        try:
            with open(self.log_filename, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
                writer.writeheader()
                writer.writerows(rows)
            print(f"Logs saved in: {self.log_filename}")
        except Exception as e:
            print("Error writing Log-File:", e)

    def write_clicks_to_csv(self) -> None:
        if not self.click_rows:
            print("No loggs have been saved")
            return

        rows = sorted(
            self.click_rows,
            key=lambda r: (
                r.get("q_index") is None, r.get("q_index"),
                r.get("q_click_time_no_reset") is None, r.get("q_click_time_no_reset"),
            ),
        )

        extra_cols = sorted({k for row in rows for k in row.keys()} - set(self.CLICK_COLUMNS))
        fieldnames = self.CLICK_COLUMNS + extra_cols

        try:
            with open(self.click_filename, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
                writer.writeheader()
                writer.writerows(rows)
            print(f"Click Logs saved in: {self.click_filename}")
        except Exception as e:
            print("Error writing Click-Logs:", e)

    def finish_questionnaire(self) -> None:

        print("Questionnaire terminated. Loggs written and Question finished.")

        if self.worker is not None and self.worker.isRunning():
            try:
                self.worker.stop()
                self.worker.wait()
            except Exception as e:
                print("Error stopping worker:", e)

        self.write_logs_to_csv()
        self.write_clicks_to_csv()

        QApplication.quit()

    def closeEvent(self, event) -> None:
        if self.worker is not None and self.worker.isRunning():
            try:
                self.worker.stop()
                self.worker.wait()
            except Exception as e:
                print("Error in CloseEvent:", e)

        if self.log_rows:
            self.write_logs_to_csv()
        if self.click_rows:
            self.write_clicks_to_csv()

        event.accept()
