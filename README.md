# Gaze Questionnaire 1.3

A research-oriented framework for **gaze-based questionnaires** using **eye tracking**, **blink/dwell activation**, and **smooth pursuit interaction**.  
The system enables hands-free answering of questionnaires and logs fine-grained interaction data for later analysis.

This project is intended for **HCI / Eye-Tracking research**, usability studies, and experimental evaluation of alternative input modalities.

---

## DEMO: Yes/No Question

Yes/No Question with Dwell Time Activation (Dwell 1-2 Seconds to Select) and the clean "Clinical" Theme

**Applicable with Dwell, Blink and Smooth Pursuit Activation**

https://github.com/user-attachments/assets/6a6346c5-a7d4-47cc-814e-0f146814e2f0

---

## DEMO: Multiple Choice Question

Multiple Choice Question with Blink Activation (Blink 0.3 Seconds to Select) and the natural "Forest Mist" Theme

**Applicable with Dwell, Blink and Smooth Pursuit Activation**

https://github.com/user-attachments/assets/6de87051-abfc-47e8-9ca0-41e33bb8687e

---

## DEMO: Text Entry

Simple Text Entry Question with Dwell Time Activation and the Futuristic "Neon" Theme

**Applicable with Dwell and Blink, not applicable with Smooth Pursuit**

https://github.com/user-attachments/assets/f34444c0-2f86-40fe-aa8c-b82dc38489d9

---

## DEMO: Likert Scale Question

Likert Scale Question with Smooth Pursuit Activation (Follow a Target for a short time to select it) and the "Oled Dark" Theme

**Applicable with Dwell, Blink and Smooth Pursuit Activation**

https://github.com/user-attachments/assets/bd031e42-9109-4fa6-bee4-f70e8a2bb2ea

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
  - Per-click timestamps
  - activation method
  - question type
  - theme
  - dwell- and blinktime
  - filter method
  - calibration method
- **Questionnaire Builder GUI**
  - Create and edit questionnaires visually
  - Decide dwell and blink time for your surveys
  - Decide activation and filter method
  - Toggle the Gaze Point on/off
  - Drag & drop reordering
  - JSON export/import
- **Fullscreen UI with 7 different Themes**

---

<img width="1181" height="779" alt="BuilderUI" src="https://github.com/user-attachments/assets/81848ad0-38ca-4907-a20a-90ce3e094d57" />


---

### ++ New Features in 1.3 ++

- Redesigned Questionnaire Builder:
  - Choose from different Callibration Methods (9-point, 5-point, lissajous) and Filters (kalman, kde, no filter) and apply them on your Questionnaire
  - Decide about Dwell (Grace Time: 0.7ms) and Blink Time
  - Move the toolbar freely

---

### ++ New Features in 1.2 ++

- 7 New Themes, that can be applied to your Questionnaire:
  - Clinical (Bright, Good for Studies and Focus)
  - Neon (Cyberpunk-inspired Retro Design)
  - Oled Dark (Dark, Battery Saving)
  - Retro Terminal (For Debugging, "Hacker"-Style)
  - Sunset Synth
  - Forest Mist
  - Signal Contrast
- Brand New Redesign of the Interface
- Fixing Performance Issues
- Remove Auto-Save

---

### ++ New Features in 1.1 ++

- Files will be automatically saved. No need to manually save anymore
- Tick Box in the questionnaire Builder to disable the gaze point 

---

## Requirements

- Python 3.12
- Webcam (or compatible video source)
- Supported OS: Windows, macOS, Linux

---

## Quick Start

#### 1) Install the Libraries

MacOS (tested):

```bash
  chmod +x setup_macos.sh
./setup_macos.sh
```

Windows (not tested):

```bash
  .\setup_windows.ps1
```

#### 2) Start the Questionnaire Builder (First Start may take longer than usual)

`
python tools/questionnaire_builder.py
`
#### 3) Click on the "Load" Button (Second Option in the Top Menu Bar) and navigate to the project root

#### 4) Click the `questionnaire.json` file

#### 5) Edit or delete Questions in the Demo File

#### 6) When you are finished, simply close the questionnaire. Your changes will automatically be saved in `questionnaire.json`.

#### 7) Run the questionnaire (First Start may take longer than usual)

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
  - Repo: https://github.com/ck-zhang/EyeTrax
  - Author: Zhang, C. (2025). EyeTrax (0.2.2) [Computer software]. Zenodo. https://doi.org/10.5281/zenodo.17188537
- For GUI: `pyside6`

---

## License

Intended for academic and research use.
Please contact the author before any commercial use.
