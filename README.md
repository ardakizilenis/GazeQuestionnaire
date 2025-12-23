# Gaze Questionnaire Framework

A research-oriented framework for **gaze-based questionnaires** using **eye tracking**, **blink/dwell activation**, and **smooth pursuit interaction**.  
The system enables hands-free answering of questionnaires and logs fine-grained interaction data for later analysis.

This project is intended for **HCI / Eye-Tracking research**, usability studies, and experimental evaluation of alternative input modalities.

---

## ✨ Features

- **Multiple gaze-based interaction techniques**
  - Blink-based selection
  - Dwell-time activation
  - Smooth Pursuit interaction (trajectory matching)
- **Question types**
  - Info screens
  - Yes/No
  - Multiple Choice (MCQ)
  - Likert Scale (5-point)
  - Text input
  - Smooth Pursuit variants (Yes/No, MCQ, Likert)
- **Smooth Pursuit detection**
  - Lag-compensated Pearson correlation
  - Rolling time windows
  - Gaussian proximity bias
  - Stability filters & cooldowns
- **Detailed logging**
  - Per-question response times
  - Toggle / reset / backspace counts
  - Per-click timestamps (high-resolution)
- **Questionnaire Builder GUI**
  - Create and edit questionnaires visually
  - Drag & drop reordering
  - JSON export/import
- **Fullscreen experimental UI**
- **Kalman-smoothed gaze signal**

---

## 🧠 Scientific Background

The smooth pursuit interaction logic is based on established principles from eye-tracking research:

- Trajectory matching between gaze and moving targets
- Lag-compensated cross-correlation
- Temporal stability filtering
- Refractory periods (cooldowns)

The approach is inspired by work such as:

- Vidal et al., *Pursuits: Eye-Based Interaction with Moving Targets* (CHI)
- Khamis et al., *VRPursuits*
- Startsev et al., *Automatic Detection of Smooth Pursuit*

---

## Requirements

- Python 3.10+
- Webcam (or compatible video source)
- Supported OS: Windows, macOS, Linux

---

## Quick Start
1) Build or edit a questionnaire

`
python tools/questionnaire_builder.py
`

3) Save the questionnaire as a JSON file (e.g., questionnaires/questionnaire.json).

4) Run the questionnaire
python main.py

3) Execution flow:
- 9-point gaze calibration
- Optional Kalman filter tuning
- Fullscreen questionnaire execution

---

## Questionnaire JSON Format

Supported keys per item:

- type: question type (see below)
- text: question or info text (required)
- activation: blink or dwell (non-SP types only)
- duration: duration in seconds (info screens only)
- labels: list of labels (MCQ = 4, Likert = 5)

---

## Logging & Output

Each run creates a new directory:

data/run_YYYYMMDD_HHMMSS/
-> gaze_questionnaire_log.csv
-> gaze_questionnaire_clicks.csv

**gaze_questionnaire_log.csv**

One row per question, including:
- Question index and type
- Activation mode
- Question text
- Result (stored via repr)
- Reaction time (seconds)
  
Interaction metrics (toggles, resets, backspaces)

**gaze_questionnaire_clicks.csv**
- Low-level interaction events with timestamps:
- Question index and type
- Toggle index
- Time since question start
- Time since last click
- Toggled area or label

---

## Question Types

| Type        | Description                      | Labels | Activation     |
| ----------- |:--------------------------------:| ------:| --------------:|
| `info`      | Timed information screen         | -      |                |
| `yesno`     | Binary choice                    | -      | blink/dwell    |
| `mcq`       | Multiple Choice                  | 4      | blink / dwell  |
| `likert`    | Likert Scales                    | 5      | blink / dwell  |
| `textgrid`  | Gaze-based text input            | -      | blink / dwell  |
| `sp_yesno`  | Smooth Pursuit Yes/No            | -      | smooth_pursuit |
| `sp_mcq`    | Smooth Pursuit Multiple Choice   | 4      | smooth_pursuit |
| `sp_likert` | Smooth Pursuit Likert Scale      | 5      | smooth_pursuit |

---

## Research Notes

- Obtain ethical approval before running studies with human participants.
- Inform participants about eye tracking, recording, and data handling.
- For synchronization, consider screen and/or audio recording (e.g., OBS).
- The framework is intended for controlled experimental environments.

---

## License

Intended for academic and research use.
Please contact the author before any commercial use.
