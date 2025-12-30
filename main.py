# main.py

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

from PySide6.QtWidgets import QApplication

from eyetrax import GazeEstimator, run_9_point_calibration
from eyetrax.filters import KalmanSmoother, make_kalman

from controller.main_window import MainWindow


def load_questionnaire(path: str) -> List[Dict[str, Any]]:
    """
    Load a questionnaire definition from a JSON file.

    Parameters
    ----------
    path : str
        Path to the questionnaire JSON file. The file must contain a top-level
        object with an "items" key.

    Returns
    -------
    list[dict[str, Any]]
        The list of questionnaire items found under the "items" key.

    Raises
    ------
    FileNotFoundError
        If the given path does not exist.
    json.JSONDecodeError
        If the file is not valid JSON.
    KeyError
        If the JSON does not contain an "items" key.
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data["items"]

def load_gazepoint_blocked(path: str) -> bool:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data["gazepoint_blocked"]

def enqueue_from_json(window: MainWindow, items: List[Dict[str, Any]]) -> None:
    """
    Enqueue questionnaire items onto a MainWindow based on their JSON definitions.

    Parameters
    ----------
    window : MainWindow
        The application window that manages the questionnaire queue.
    items : list[dict[str, Any]]
        Questionnaire items, each containing at least a "type" field and
        optionally fields like "text", "activation", "duration", and "labels".

    Returns
    -------
    None

    Notes
    -----
    Supported item types:
      - "info"
      - "yesno"
      - "mcq"
      - "likert"
      - "textgrid"
      - "sp_yesno"
      - "sp_mcq"
      - "sp_likert"

    Unknown types are ignored with a console message.
    """
    for it in items:
        qtype = it["type"]
        text = it.get("text", "")
        activation = it.get("activation")

        if qtype == "info":
            window.info(text, int(it.get("duration", 5)))
        elif qtype == "yesno":
            window.enqueue_yesno(text, activation or "blink")
        elif qtype == "mcq":
            window.enqueue_mcq(text, activation or "blink", labels=it.get("labels"))
        elif qtype == "likert":
            window.enqueue_likert(text, activation or "blink", labels=it.get("labels"))
        elif qtype == "textgrid":
            window.enqueue_textgrid(text, activation or "dwell")
        elif qtype == "sp_yesno":
            window.enqueue_smoothpursuit_yesno(text)
        elif qtype == "sp_mcq":
            window.enqueue_smoothpursuit_mcq(text, labels=it.get("labels"))
        elif qtype == "sp_likert":
            window.enqueue_smoothpursuit_likert(text, labels=it.get("labels"))
        else:
            print("Unknown question type:", qtype)


def main() -> None:
    """
    Application entry point.

    This function:
    - creates and calibrates the gaze estimator,
    - creates and tunes the Kalman smoother,
    - creates the Qt application and main window,
    - loads questionnaire JSON and enqueues items,
    - starts and shows the questionnaire UI.

    Returns
    -------
    None
    """
    estimator = GazeEstimator()
    run_9_point_calibration(estimator)

    kalman = make_kalman()
    smoother = KalmanSmoother(kalman)
    smoother.tune(estimator, camera_index=0)

    app = QApplication(sys.argv)
    window = MainWindow(
        estimator,
        smoother,
        parent=None,
        gazepoint_blocked=load_gazepoint_blocked("questionnaire.json"),
        dwell_threshold=1200,
        blink_threshold=500
    )

    items = load_questionnaire("questionnaire.json")
    enqueue_from_json(window, items)

    window.start_questionnaire()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
