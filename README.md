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

- Python 3.12
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


>**Troubleshooting I: Virtual Environment** 
>
> If you are on Mac, it is required to configure your python-Interpreter and adding a virtual environment (.venv). 
> If you have issues go to the project root and follow the following steps on the Terminal:
> 1. `brew install python3.12@`
> 2. `python3.12 -m venv env`
> 3. `source env/bin/activate`
> 4. `pip install --upgrade pip`
> 5. `pip install pyside6`
> 6. `pip install eyetrax`
> 7. Set your Interpreter to `GazeQuestionnaire/env/bin/python`
> 
>**Troubleshooting II: Outdated mediapipe** 
> 
> If you are on Mac and you get an Error like this: 
> >AttributeError: module 'mediapipe' has no attribute 'solution'
> 
> the mediapipe package might be old or damaged. You have to uninstall and reinstall mediapipe to solve this issue
> 
> Follow these steps on the Terminal in the virtual environment:
> 
> 1. `pip uninstall -y mediapipe `
> 2. `pip uninstall -y mediapipe-silicon mediapipe-rpi 2>/dev/null || true`
> 3. `pip install mediapipe==0.10.14`


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
  - Repo: https://github.com/ck-zhang/EyeTrax
  - Author: Zhang, C. (2025). EyeTrax (0.2.2) [Computer software]. Zenodo. https://doi.org/10.5281/zenodo.17188537
- For GUI: `pyside6`

---

## License

Intended for academic and research use.
Please contact the author before any commercial use.
