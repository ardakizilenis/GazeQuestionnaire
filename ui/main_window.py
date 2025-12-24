# ui/main_window.py

from __future__ import annotations

import os
import time
import csv
from datetime import datetime
from typing import Any, Dict, List, Optional

from PySide6.QtWidgets import QMainWindow, QApplication

from gaze.eyetracker_worker import EyeTrackerWorker
from ui.InfoWidget import InfoWidget
from ui.LikertScaleQuestionWidget import LikertScaleQuestionWidget
from ui.MultipleChoiceQuestionWidget import MultipleChoiceQuestionWidget
from ui.SmoothPursuit_LikertScaleWidget import SmoothPursuitLikertScaleWidget
from ui.SmoothPursuit_MultipleChoiceWidget import SmoothPursuitMultipleChoiceWidget
from ui.SmoothPursuit_YesNoWidget import SmoothPursuitYesNoWidget
from ui.TextInputWidget import TextInputWidget
from ui.YesNoQuestionWidget import YesNoQuestionWidget


class MainWindow(QMainWindow):
    """
    Main application window that orchestrates the gaze-based questionnaire.

    Responsibilities
    ---------------
    - Maintains a queue of questionnaire items (info/yesno/mcq/likert/textgrid/smooth pursuit variants).
    - Creates and displays the appropriate widget for each item.
    - Starts and manages an EyeTrackerWorker that streams gaze samples and blink state.
    - Collects per-question summary logs and per-click logs.
    - Writes logs to CSV at the end (or on close).

    Questionnaire Item Format
    -------------------------
    Each queued item is a dict with (some) keys:
      - type: "info" | "yesno" | "mcq" | "likert" | "textgrid" | "sp_yesno" | "sp_mcq" | "sp_likert"
      - text: question or info text
      - activation: "blink" | "dwell" | "smooth_pursuit" | None
      - duration: int seconds (only for "info")
      - labels: list[str] optional (for mcq/likert and smooth pursuit variants)

    Logging
    -------
    - gaze_questionnaire_log.csv: one row per non-info question (result + reaction time + counters)
    - gaze_questionnaire_clicks.csv: one row per click/toggle activation (timing + area label)
    """

    def __init__(self, estimator, smoother, parent=None) -> None:
        """
        Initialize the main window and set up logging directories/files.

        Parameters
        ----------
        estimator : Any
            Eye tracking estimator object used by the EyeTrackerWorker.
        smoother : Any
            Smoothing/filtering object used by the EyeTrackerWorker.
        parent : QWidget, optional
            Parent Qt widget.

        Notes
        -----
        - The window is shown fullscreen.
        - A run-specific output directory is created under `<project_root>/data/run_YYYYMMDD_HHMMSS`.
        """
        super().__init__(parent)

        self.estimator = estimator
        self.smoother = smoother

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

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_dir = os.path.join(data_root, f"run_{timestamp}")
        os.makedirs(self.run_dir, exist_ok=True)

        self.log_filename = os.path.join(self.run_dir, "gaze_questionnaire_log.csv")
        self.click_filename = os.path.join(self.run_dir, "gaze_questionnaire_clicks.csv")

    def info(self, text: str, duration_sec: int) -> None:
        """
        Enqueue an informational screen that auto-advances after a duration.

        Parameters
        ----------
        text : str
            Text to display.
        duration_sec : int
            Time in seconds before auto-advancing to the next item.

        Returns
        -------
        None
        """
        self.question_queue.append(
            {"type": "info", "text": text, "duration": int(duration_sec), "activation": None}
        )

    def enqueue_yesno(self, question: str, activation_mode: str) -> None:
        """
        Enqueue a classic (non-smooth-pursuit) yes/no question.

        Parameters
        ----------
        question : str
            Question text.
        activation_mode : str
            "blink" or "dwell".

        Returns
        -------
        None
        """
        self.question_queue.append({"type": "yesno", "text": question, "activation": activation_mode})

    def enqueue_mcq(self, question: str, activation_mode: str, labels=None) -> None:
        """
        Enqueue a classic (non-smooth-pursuit) 4-option multiple choice question.

        Parameters
        ----------
        question : str
            Question text.
        activation_mode : str
            "blink" or "dwell".
        labels : list[str] | None, optional
            Exactly four labels. If None, the widget default labels are used.

        Returns
        -------
        None
        """
        self.question_queue.append(
            {"type": "mcq", "text": question, "activation": activation_mode, "labels": labels}
        )

    def enqueue_likert(self, question: str, activation_mode: str, labels: Optional[List[str]] = None) -> None:
        """
        Enqueue a classic (non-smooth-pursuit) 5-option Likert scale question.

        Parameters
        ----------
        question : str
            Question text.
        activation_mode : str
            "blink" or "dwell".
        labels : list[str] | None, optional
            Exactly five labels. If None, the widget default labels are used.

        Returns
        -------
        None
        """
        self.question_queue.append(
            {"type": "likert", "text": question, "activation": activation_mode, "labels": labels}
        )

    def enqueue_textgrid(self, question: str, activation_mode: str) -> None:
        """
        Enqueue the gaze-based text input widget (3x3 grid).

        Parameters
        ----------
        question : str
            Prompt/question to display above the entered text.
        activation_mode : str
            "blink" or "dwell".

        Returns
        -------
        None
        """
        self.question_queue.append({"type": "textgrid", "text": question, "activation": activation_mode})

    def enqueue_smoothpursuit_yesno(self, question: str) -> None:
        """
        Enqueue a smooth-pursuit yes/no widget.

        Parameters
        ----------
        question : str
            Question text.

        Returns
        -------
        None
        """
        self.question_queue.append({"type": "sp_yesno", "text": question, "activation": "smooth_pursuit"})

    def enqueue_smoothpursuit_mcq(self, question: str, labels=None) -> None:
        """
        Enqueue a smooth-pursuit multiple choice widget (multi-select).

        Parameters
        ----------
        question : str
            Question text.
        labels : list[str] | None, optional
            Exactly four labels. If None, widget default labels are used.

        Returns
        -------
        None
        """
        self.question_queue.append(
            {"type": "sp_mcq", "text": question, "activation": "smooth_pursuit", "labels": labels}
        )

    def enqueue_smoothpursuit_likert(self, question: str, labels=None) -> None:
        """
        Enqueue a smooth-pursuit Likert widget (single-select, 5 options).

        Parameters
        ----------
        question : str
            Question text.
        labels : list[str] | None, optional
            Exactly five labels. If None, widget default labels are used.

        Returns
        -------
        None
        """
        self.question_queue.append(
            {"type": "sp_likert", "text": question, "activation": "smooth_pursuit", "labels": labels}
        )

    def start_questionnaire(self) -> None:
        """
        Start the questionnaire after all items have been enqueued.

        Returns
        -------
        None

        Notes
        -----
        - Creates and starts the EyeTrackerWorker if it is not running yet.
        - Resets the question index and immediately shows the first item.
        """
        if self.worker is None:
            self.worker = EyeTrackerWorker(self.estimator, self.smoother)
            self.worker.start()

        self.current_index = -1
        self.show_next_question()

    def disconnect_current_widget(self) -> None:
        """
        Disconnect worker signals and widget signals from the currently displayed widget.

        Returns
        -------
        None

        Notes
        -----
        - Safe to call even if no worker/widget exists.
        - Disconnection is wrapped in try/except to tolerate already-disconnected signals.
        """
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
        """
        Advance the queue and display the next questionnaire item.

        Returns
        -------
        None

        Notes
        -----
        - If the queue is exhausted, calls `finish_questionnaire()`.
        - Sets up signal connections:
            - gaze_updated -> widget.set_gaze
            - blink_state  -> widget.set_blinking (if supported)
            - widget.submitted -> on_question_submitted
            - widget.clicked   -> on_widget_clicked
        - Initializes per-question timing metadata for logging.
        """
        self.disconnect_current_widget()
        self.current_index += 1

        if self.current_index >= len(self.question_queue):
            self.finish_questionnaire()
            return

        meta = self.question_queue[self.current_index]
        qtype = meta["type"]
        text = meta.get("text", "")
        activation = meta.get("activation")

        logical_index: int | None = None
        if qtype != "info":
            self.question_counter += 1
            logical_index = self.question_counter

        match qtype:
            case "info":
                duration = meta.get("duration", 5)
                widget = InfoWidget(text, duration_sec=duration)
            case "yesno":
                widget = YesNoQuestionWidget(text, activation_mode=activation or "blink")
            case "mcq":
                widget = MultipleChoiceQuestionWidget(
                    text, activation_mode=activation or "blink", labels=meta.get("labels")
                )
            case "likert":
                widget = LikertScaleQuestionWidget(
                    text, activation_mode=activation or "blink", labels=meta.get("labels")
                )
            case "textgrid":
                widget = TextInputWidget(text, activation_mode=activation or "dwell")
            case "sp_yesno":
                widget = SmoothPursuitYesNoWidget(text)
            case "sp_mcq":
                widget = SmoothPursuitMultipleChoiceWidget(text, labels=meta.get("labels"))
            case "sp_likert":
                widget = SmoothPursuitLikertScaleWidget(text, labels=meta.get("labels"))
            case _:
                print("Question Type unknown:", qtype)
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
            "type": qtype,
            "text": text,
            "activation": activation,
        }

    def on_widget_clicked(self, toggle_index, toggled_area):
        """
        Capture per-click logging emitted by the active widget.

        Parameters
        ----------
        toggle_index : Any
            Widget-provided click index (typically an int).
        toggled_area : Any
            Widget-provided descriptor of the activated element, used for click logs.

        Returns
        -------
        None

        Notes
        -----
        - Stores both "time since question start" and "time since last click".
        - Ignores clicks during "info" items (no per-question click logging).
        """
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
                "q_toggle_index": int(toggle_index),
                "q_click_time_no_reset": round(time_from_start, 3),
                "q_click_time": None if time_since_last_click is None else round(time_since_last_click, 3),
                "q_toggled_area": str(toggled_area),
            }
        )

    def on_question_submitted(self, result):
        """
        Handle completion of the current questionnaire item.

        Parameters
        ----------
        result : Any
            Result emitted by the widget's `submitted` signal.
            Examples:
              - yes/no: "yes" or "no"
              - mcq: list[str]
              - likert: str
              - textgrid: str
              - info: None

        Returns
        -------
        None

        Notes
        -----
        - For non-info items, writes a summary row to `self.log_rows`.
        - Immediately advances to the next item.
        """
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
                "extra_metrics": getattr(widget, "log_extra", ""),
            }
            self.log_rows.append(log_entry)

        self.show_next_question()

    def write_logs_to_csv(self) -> None:
        """
        Write per-question summary logs to `gaze_questionnaire_log.csv`.

        Returns
        -------
        None

        Notes
        -----
        - Uses the keys of the first row as CSV header fields.
        - If no rows exist, prints a message and returns.
        """
        if not self.log_rows:
            print("No loggs have been saved")
            return

        fieldnames = list(self.log_rows[0].keys())
        try:
            with open(self.log_filename, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.log_rows)
            print(f"Logs saved in: {self.log_filename}")
        except Exception as e:
            print("Error writing Log-File:", e)

    def write_clicks_to_csv(self) -> None:
        """
        Write per-click logs to `gaze_questionnaire_clicks.csv`.

        Returns
        -------
        None

        Notes
        -----
        - Uses a fixed schema to keep click logs stable across widget types.
        - If no rows exist, prints a message and returns.
        """
        if not self.click_rows:
            print("No loggs have been saved")
            return

        fieldnames = ["q_index", "q_type", "q_toggle_index", "q_click_time_no_reset", "q_click_time", "q_toggled_area"]
        try:
            with open(self.click_filename, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.click_rows)
            print(f"Click Logs saved in: {self.click_filename}")
        except Exception as e:
            print("Error writing Click-Logs:", e)

    def finish_questionnaire(self) -> None:
        """
        Stop eye tracking, write logs, and exit the application.

        Returns
        -------
        None

        Notes
        -----
        - Stops and joins the EyeTrackerWorker if it is running.
        - Writes both summary logs and click logs.
        - Quits the Qt application.
        """
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
        """
        Qt close event handler to ensure worker shutdown and log flushing.

        Parameters
        ----------
        event : QCloseEvent
            The Qt close event.

        Returns
        -------
        None

        Notes
        -----
        - Attempts to stop the worker if running.
        - Writes any accumulated logs before allowing the window to close.
        """
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
