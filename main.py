# main.py

from __future__ import annotations

import argparse
import json, cv2

from pathlib import Path
from typing import Any, Dict, List
from contextlib import contextmanager

from PySide6.QtWidgets import QApplication

from eyetrax import GazeEstimator
from eyetrax.calibration import run_5_point_calibration, run_lissajous_calibration, run_9_point_calibration
from eyetrax.filters import KalmanSmoother, make_kalman, KDESmoother, NoSmoother

from controller.main_window import MainWindow
from widgets import gaze_widget

@contextmanager
def disable_destroy_all_windows():
    original = cv2.destroyAllWindows
    cv2.destroyAllWindows = lambda: None
    try:
        yield
    finally:
        cv2.destroyAllWindows = original

@contextmanager
def skip_first_destroy_window(window_name: str):
    original = cv2.destroyWindow
    called = False

    def patched(name: str):
        nonlocal called
        if name == window_name and not called:
            called = True      # ersten Aufruf ignorieren
            return
        return original(name)  # alle anderen normal

    try:
        cv2.destroyWindow = patched
        yield
    finally:
        cv2.destroyWindow = original


def load_json_item(from_path: str, load: str) -> Any:
    data = json.loads(Path(from_path).read_text(encoding="utf-8"))
    match load:
        case "gazepoint_blocked":
            return data["gazepoint_blocked"]
        case "theme":
            return data["theme"]
        case "calibration":
            return data["calibration"]
        case "filter":
            return data["filter"]
        case "items":
            return data["items"]
        case "dwell_time":
            return data["dwell_time"]
        case "blink_time":
            return data["blink_time"]
        case _:
            print(f"No data available for '{load}'...")
            return None

def calibrate(questionnaire: str, main_estimator: GazeEstimator) -> None:
    calibration_method = load_json_item(questionnaire,"calibration")
    filter_method = load_json_item(questionnaire, "filter")
    match calibration_method:
        case "9-point":
            if filter_method == "kalman":
                run_9_point_calibration(main_estimator)
            else:
                with disable_destroy_all_windows():
                    run_9_point_calibration(main_estimator)
        case "5-point":
            if filter_method == "kalman":
                run_5_point_calibration(main_estimator)
            else:
                with disable_destroy_all_windows():
                    run_5_point_calibration(main_estimator)
        case "lissajous":
            if filter_method == "kalman":
                run_lissajous_calibration(main_estimator)
            else:
                with disable_destroy_all_windows():
                    run_lissajous_calibration(main_estimator)
        case _:
            print(f"No calibration method '{calibration_method}' available...")

def enqueue_from_json(window: MainWindow, items: List[Dict[str, Any]]) -> None:
    for it in items:
        qtype = it["type"]
        text = it.get("text", "")
        activation = it.get("activation")
        match qtype:
            case "info":
                window.info(text, int(it.get("duration", 5)))
            case "yesno":
                window.enqueue_yesno(text, activation)
            case "mcq":
                window.enqueue_mcq(text, activation, labels=it.get("labels"))
            case "likert":
                window.enqueue_likert(text, activation, labels=it.get("labels"))
            case "textgrid":
                window.enqueue_textgrid(text, activation)
            case "sp_yesno":
                window.enqueue_smoothpursuit_yesno(text)
            case "sp_mcq":
                window.enqueue_smoothpursuit_mcq(text, labels=it.get("labels"))
            case "sp_likert":
                window.enqueue_smoothpursuit_likert(text, labels=it.get("labels"))
            case _:
                window.info(f"---DEBUG---\n\nWARNING!\n\nUnknown Question Type Detected:\n'{qtype}'\n\n---DEBUG---", 5)

def get_smoother(questionnaire, main_estimator):
    filter_method = load_json_item(questionnaire, "filter")
    match filter_method:
        case "kalman":
            kalman = make_kalman()
            smoother = KalmanSmoother(kalman)
            smoother.tune(main_estimator, camera_index=0)
            return smoother
        case "kde":
            screen_width, screen_height = gaze_widget.get_screen_size()
            smoother = KDESmoother(screen_width, screen_height, confidence=0.5)
            return smoother
        case "no-filter":
            smoother = NoSmoother()
            return smoother
        case _:
            print(f"No filter method '{filter_method}' available. Applying no filter...")
            smoother = NoSmoother()
            return smoother

def main(questionnaire: str) -> None:
    main_estimator = GazeEstimator()
    calibrate(questionnaire, main_estimator)
    smoother = get_smoother(questionnaire, main_estimator)

    app = QApplication([])
    window = MainWindow(
        main_estimator,
        smoother,
        calibration_method=load_json_item(questionnaire, "calibration"),
        filter_method=load_json_item(questionnaire, "filter"),
        dwell_threshold=load_json_item(questionnaire, "dwell_time"),
        blink_threshold=load_json_item(questionnaire, "blink_time"),
        gazepoint_blocked=load_json_item(questionnaire, "gazepoint_blocked"),
        theme=load_json_item(questionnaire, "theme"),
        parent=None,
    )

    items = load_json_item(questionnaire, "items")
    enqueue_from_json(window, items)

    window.start_questionnaire()
    window.showFullScreen()

    app.exec()


def cli():
    parser = argparse.ArgumentParser(prog="gq-run")

    parser.add_argument(
        "name",
        nargs="?",
        help="Questionnaire Name (e.g. demo)"
    )
    parser.add_argument(
        "--builder",
        action="store_true",
        help="Start Questionnaire Builder (GUI)"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available questionnaires"
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Show version"
    )

    base_dir = Path(__file__).resolve().parent
    questionnaires_dir = base_dir / "questionnaires"

    # ---------- argcomplete ----------
    try:
        import argcomplete

        def questionnaire_name_completer(**kwargs):
            # gibt nur "stems" zurück: demo, study1, ...
            if questionnaires_dir.exists():
                return sorted(p.stem for p in questionnaires_dir.glob("*.json"))
            return []

        # positional "name" Argument finden und Completer anhängen
        for action in parser._actions:
            if getattr(action, "dest", None) == "name":
                action.completer = questionnaire_name_completer

        argcomplete.autocomplete(parser)
    except ImportError:
        pass
    # -------------------------------

    args = parser.parse_args()

    if args.version:
        # robust: Version aus installiertem Paket (pyproject.toml [project].name)
        try:
            from importlib.metadata import version
            print(version("gazequestionnaire"))
        except Exception:
            print("unknown")
        return

    if args.list:
        files = sorted(questionnaires_dir.glob("*.json"))
        if not files:
            print("No questionnaires found.")
            return
        for f in files:
            print(f.stem)
        return

    if args.builder:
        from tools.questionnaire_builder import run as run_builder
        run_builder()
        return

    if not args.name:
        parser.error(
            "\n\n***************** HELP *****************\n\n"
            "- `gq-run your_questionnaire` (e.g. `gq-run demo`) : Runs a Questionnaire\n"
            "- `gq-run --builder` : Runs the Builder (GUI)\n"
            "- `gq-run --list` : Lists available Questionnaires\n"
            "- `gq-run --version` : Shows version\n\n"
            "****************************************\n\n"
        )

    questionnaire_path = questionnaires_dir / f"{args.name}.json"
    if not questionnaire_path.exists():
        parser.error(f"Could not find {questionnaire_path}")

    main(str(questionnaire_path))


if __name__ == "__main__":
    cli()
