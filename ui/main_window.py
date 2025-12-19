# ui/main_window.py
from __future__ import annotations

import os, time, csv
from datetime import datetime
from typing import Any, Dict, List, Optional
from PySide6.QtWidgets import QMainWindow, QApplication
from gaze.eyetracker_worker import EyeTrackerWorker
from ui.YesNoQuestionWidget import YesNoQuestionWidget
from ui.MultipleChoiceQuestionWidget import MultipleChoiceQuestionWidget
from ui.LikertScaleQuestionWidget import LikertScaleQuestionWidget
from ui.InfoWidget import InfoWidget
from ui.SmoothPursuit_YesNoWidget import SmoothPursuitYesNoWidget

from ui.TextInputWidget import TextInputWidget


class MainWindow(QMainWindow):
    """
    Central Window for the Gaze-Questionnaire.

      - has a queue of questions with the selection methods (info/yesno/mcq/likert/textgrid/sp_yesno)
      - shows the right widgets from top to bottom
      - controls EyeTrackerWorker (Gaze + Blink)
      - collects the logs & writes them in a CSV
    """

    def __init__(self, estimator, smoother, parent=None) -> None:
        super().__init__(parent)

        self.estimator = estimator
        self.smoother = smoother

        self.setWindowTitle("Gaze Questionnaire")
        self.showFullScreen()

        # Question Queue
        # ... is a List of dicts like:
        #   type: "info" | "yesno" | "mcq" | "likert" | "textgrid" | "sp_yesno"
        #   text: Question / Info-Text
        #   activation: "blink" | "dwell"
        #   duration: int (seconds, only for info-widget)
        #   labels: list[str] (optional at likert and mcq)
        self.question_queue: List[Dict[str, Any]] = []
        self.current_index: int = -1
        self.current_widget = None
        self.question_counter: int = 0

        # EyeTracker Worker
        self.worker: Optional[EyeTrackerWorker] = None

        # Logging
        self.log_rows: List[Dict[str, Any]] = []
        self.question_start_time: Optional[float] = None
        self.current_qmeta: Optional[Dict[str, Any]] = None

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.log_dir = os.path.join(base_dir, "data")
        os.makedirs(self.log_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_filename = os.path.join(
            self.log_dir,
            f"gaze_questionnaire_log_{timestamp}.csv",
        )

    # APIs for Questionnaire Definition

    def info(self, text: str, duration_sec: int) -> None:
        self.question_queue.append(
            {
                "type": "info",
                "text": text,
                "duration": int(duration_sec),
                "activation": None,
            }
        )

    def enqueue_yesno(self, question: str, activation_mode: str) -> None:
        self.question_queue.append(
            {
                "type": "yesno",
                "text": question,
                "activation": activation_mode,
            }
        )

    def enqueue_mcq(self, question: str, activation_mode: str, labels=None) -> None:
        self.question_queue.append(
            {
                "type": "mcq",
                "text": question,
                "activation": activation_mode,
                "labels": labels,
            }
        )

    def enqueue_likert(
        self,
        question: str,
        activation_mode: str,
        labels: Optional[List[str]] = None
    ) -> None:
        self.question_queue.append(
            {
                "type": "likert",
                "text": question,
                "activation": activation_mode,
                "labels": labels
            }
        )

    def enqueue_textgrid(self, question: str, activation_mode: str) -> None:
        self.question_queue.append(
            {
                "type": "textgrid",
                "text": question,
                "activation": activation_mode,
            }
        )

    def enqueue_smoothpursuit_yesno(self, question: str) -> None:
        self.question_queue.append(
            {
                "type": "sp_yesno",
                "text": question,
                "activation": "smooth_pursuit",
            }
        )

    # Questionnaire starts (after enqueuing
    def start_questionnaire(self) -> None:
        """Von main.py aufrufen, nachdem alle Fragen hinzugefügt wurden."""
        if self.worker is None:
            self.worker = EyeTrackerWorker(self.estimator, self.smoother)
            self.worker.start()
        self.current_index = -1
        self.show_next_question()

    # Disconnect current widget after getting a signal
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

    def show_next_question(self) -> None:
        self.disconnect_current_widget()
        self.current_index += 1

        # finish questionnaire after last question
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

        # Making Widget according to question type
        match qtype:
            case "info":
                duration = meta.get("duration", 5)
                widget = InfoWidget(text, duration_sec=duration)
            case "yesno":
                widget = YesNoQuestionWidget(
                    text,
                    activation_mode=activation or "blink",
                )
            case "mcq":
                widget = MultipleChoiceQuestionWidget(
                    text,
                    activation_mode=activation or "blink",
                    labels=meta.get("labels"),
                )
            case "likert":
                widget = LikertScaleQuestionWidget(
                    text,
                    activation_mode=activation or "blink",
                    labels=meta.get("labels")
                )
            case "textgrid":
                widget = TextInputWidget(
                    text,
                    activation_mode=activation or "dwell",
                )
            case "sp_yesno":
                widget = SmoothPursuitYesNoWidget(text)
            case _:
                print("Question Type unknown:", qtype)
                self.show_next_question()
                return

        # Setting widget, connect signals
        self.current_widget = widget
        self.setCentralWidget(widget)

        if self.worker is not None:
            self.worker.gaze_updated.connect(widget.set_gaze)
            if hasattr(widget, "set_blinking"):
                self.worker.blink_state.connect(widget.set_blinking)

        if hasattr(widget, "submitted"):
            widget.submitted.connect(self.on_question_submitted)

        # Logging Meta Data
        self.question_start_time = time.monotonic()
        self.current_qmeta = {
            "index": logical_index,
            "type": qtype,
            "text": text,
            "activation": activation,
        }


    # Get Answer
    def on_question_submitted(self, result):
        end_time = time.monotonic()
        rt_sec = (
            end_time - self.question_start_time
            if self.question_start_time is not None
            else None
        )

        widget = self.current_widget
        meta = self.current_qmeta or {}
        qtype = meta.get("type")
        qnum = meta.get("index")

        # Logg Questions without Info-Screens
        if qtype != "info" and widget is not None:
            log_entry = {
                "question_index": qnum,
                "question_type": qtype,
                "activation_mode": meta.get("activation"),
                "question_text": meta.get("text"),
                "result": repr(result),
                "rt_sec": rt_sec,
                "n_toggles": getattr(widget, "log_toggles", 0),
                "n_resets": getattr(widget, "log_resets", 0),
                "n_backspaces": getattr(widget, "log_backspaces", 0),
                "extra_metrics": getattr(widget, "log_extra", ""),
            }
            self.log_rows.append(log_entry)

        self.show_next_question()

    # Logging and writing to csv
    def write_logs_to_csv(self) -> None:
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

    def finish_questionnaire(self) -> None:
        print("Questionnaire terminated. Loggs written and Question finished.")

        if self.worker is not None and self.worker.isRunning():
            try:
                self.worker.stop()
                self.worker.wait()
            except Exception as e:
                print("Error stopping worker:", e)

        self.write_logs_to_csv()

        QApplication.quit()

    # Closing Window
    def closeEvent(self, event) -> None:
        if self.worker is not None and self.worker.isRunning():
            try:
                self.worker.stop()
                self.worker.wait()
            except Exception as e:
                print("Error in CloseEvent:", e)

        if self.log_rows:
            self.write_logs_to_csv()

        event.accept()
