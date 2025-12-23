# Gaze Questionnaire

A research-oriented framework for **gaze-based questionnaires** using **eye tracking**, **blink/dwell activation**, and **smooth pursuit interaction**.  
The system enables hands-free answering of questionnaires and logs fine-grained interaction data for later analysis.

This project is intended for **HCI / Eye-Tracking research**, usability studies, and experimental evaluation of alternative input modalities.

---

## Features

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

## Requirements

- Python 3.10+
- Webcam (or compatible video source)
- Supported OS: Windows, macOS, Linux

---

## Quick Start
1) Start the Questionnaire Builder

`
python tools/questionnaire_builder.py
`

2) Click on the "Load" Button (Second Option in the Top Menu Bar) and navigate to `questionnaires/`

3) Click the `questionnaire.json` file

4) Edit or delete Questions in the Demo File

5) When you are finished, simply save the questionnaire (Third Menu Option) in `questionnaires/questionnaire.json`.

6) Run the questionnaire

`
python main.py
`

Execution flow:
- 9-point gaze calibration
- Kalman-Filter Tuning
- Fullscreen questionnaire with Questions from the JSON

---

## Logging & Output

Each run creates a new directory:

>`data/run_YYYYMMDD_HHMMSS/`
>- `gaze_questionnaire_log.csv`
>- `gaze_questionnaire_clicks.csv`

**gaze_questionnaire_log.csv**

One row per question, including:
- Question index and type
- Activation mode
- Question text
- Result (stored via repr)
- Reaction time (seconds)
- Interaction metrics (toggles, resets, backspaces)

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

## Used Repositories and Frameworks

- For Eyetracking: `eyetrax`:
  - Author: Zhang, C. (2025). EyeTrax (0.2.2) [Computer software]. Zenodo. https://doi.org/10.5281/zenodo.17188537
  - Repo: https://github.com/ck-zhang/EyeTrax
- For GUI: `pyside6`

---

## License

Intended for academic and research use.
Please contact the author before any commercial use.
