# main.py

import sys
import json
from PySide6.QtWidgets import QApplication
from pathlib import Path

from eyetrax import GazeEstimator, run_9_point_calibration
from eyetrax.filters import KalmanSmoother, make_kalman


from ui.main_window import MainWindow

def load_questionnaire(path: str):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data["items"]

def enqueue_from_json(window, items):
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
        else:
            print("Unknown question type:", qtype)

def main():
    estimator = GazeEstimator()
    run_9_point_calibration(estimator)

    kalman = make_kalman()
    smoother = KalmanSmoother(kalman)
    smoother.tune(estimator, camera_index=0)

    app = QApplication(sys.argv)
    window = MainWindow(estimator, smoother)

    items = load_questionnaire("questionnaires/questionnaire.json")
    enqueue_from_json(window, items)

    window.start_questionnaire()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

# Jedes toggle mit Timestamp
# Textinput -> Timestamp für JEDEN Buchstaben, allgemein: Timestamp für JEDEN "Click"
# -> Eine große csv-Datei mit Timestamp bei jedem Click zusätzlich zur Overview csv
# (Screen- & Audiorecording mit OBS) -> Datenbereinigung
#
# Ethikantrag (LMU Ethik-Kommission -> Fast Track)
# Einverständniserklärung
# Papierfragebogen (?)
# 12-20 Personen (2 Studien, 1 für Researchers JSON-Editor (6 Experts), 1 für Eyetracker)
# Teilnehmer finden bei Slack, Leute fragen
#
# Mehr Fragen nehmen, die objektiver sind
# Randomisieren von Fragen
#