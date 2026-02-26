# main.py

from __future__ import annotations

import argparse
import json, cv2

from pathlib import Path
from typing import Any, Dict, List
from contextlib import contextmanager

from PySide6.QtWidgets import QApplication, QFileDialog

from eyetrax import GazeEstimator
from eyetrax.calibration import run_5_point_calibration, run_lissajous_calibration, run_9_point_calibration, run_dense_grid_calibration
from eyetrax.filters import KalmanSmoother, KalmanEMASmoother, make_kalman, KDESmoother, NoSmoother

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


def load_json_item(from_path: str, load: str) -> Any:
    data = json.loads(Path(from_path).read_text(encoding="utf-8"))

    # Root level keys
    if load in data:
        return data[load]

    # Params keys
    if "params" in data and load in data["params"]:
        return data["params"][load]

    raise KeyError(f"Key '{load}' not found in JSON.")

def load_file_name(from_path: str) -> str:
    return Path(from_path).name

from contextlib import nullcontext


def calibrate(questionnaire: str, main_estimator: GazeEstimator) -> None:
    calibration_method = load_json_item(questionnaire, "calibration")
    filter_method = load_json_item(questionnaire, "filter")

    calibration_map = {
        "9-point": run_9_point_calibration,
        "5-point": run_5_point_calibration,
        "lissajous": run_lissajous_calibration,
        "dense": run_dense_grid_calibration,
    }

    calibration_function = calibration_map.get(calibration_method)

    if not calibration_function:
        print(f"No calibration method '{calibration_method}' available...")
        return

    kwargs = {}

    if calibration_method == "dense":
        kwargs["rows"] = load_json_item(questionnaire, "dense_rows")
        kwargs["cols"] = load_json_item(questionnaire, "dense_col")
        kwargs["camera_index"] = 0

    context = (
        nullcontext()
        if filter_method == "kalman"
        else disable_destroy_all_windows()
    )

    with context:
        calibration_function(main_estimator, **kwargs)

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
    confidence = load_json_item(questionnaire, "kde_confidence")
    ema_alpha = load_json_item(questionnaire, "ema_strength")
    match filter_method:
        case "kalman":
            kalman = make_kalman()
            smoother = KalmanSmoother(kalman)
            smoother.tune(main_estimator, camera_index=0)
            return smoother
        case "kde":
            screen_width, screen_height = gaze_widget.get_screen_size()
            smoother = KDESmoother(screen_width, screen_height, confidence=confidence)
            return smoother
        case "kalman_ema":
            kalman = make_kalman()
            smoother = KalmanEMASmoother(kalman, ema_alpha=ema_alpha)
            smoother.tune(main_estimator, camera_index=0)
        case "no-filter":
            smoother = NoSmoother()
            return smoother
        case _:
            print(f"No filter method '{filter_method}' available. Applying no filter...")
            smoother = NoSmoother()
            return smoother

def main(questionnaire: str) -> None:
    participant_id = input("Participant ID / Name: ").strip()
    run_order = input("Run order: ").strip()
    main_estimator = GazeEstimator()
    calibrate(questionnaire, main_estimator)
    smoother = get_smoother(questionnaire, main_estimator)

    file_name = load_file_name(questionnaire)

    app = QApplication([])
    window = MainWindow(
        main_estimator,
        smoother,
        participant_id=participant_id,
        run_order=run_order,
        calibration_method=load_json_item(questionnaire, "calibration"),
        filter_method=load_json_item(questionnaire, "filter"),
        dwell_threshold=load_json_item(questionnaire, "dwell_time"),
        blink_threshold=load_json_item(questionnaire, "blink_time"),
        gazepoint_blocked=load_json_item(questionnaire, "gazepoint_blocked"),
        theme=load_json_item(questionnaire, "theme"),
        parent=None,
        file_name = file_name
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
            if questionnaires_dir.exists():
                return sorted(p.stem for p in questionnaires_dir.glob("*.json"))
            return []

        for action in parser._actions:
            if getattr(action, "dest", None) == "name":
                action.completer = questionnaire_name_completer

        argcomplete.autocomplete(parser)
    except ImportError:
        pass
    # -------------------------------

    args = parser.parse_args()

    if args.version:
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
            "- `gq-run --version` : Shows version"
            "\n\n****************************************\n\n"
        )

    questionnaire_path = questionnaires_dir / f"{args.name}.json"
    if not questionnaire_path.exists():
        parser.error(f"Could not find {questionnaire_path}")

    main(str(questionnaire_path))


if __name__ == "__main__":
    # ------------------------------ run with gq-run
    cli()

    # ------------------------------ debug mode
    # main("questionnaires/demo.json")
