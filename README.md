# Gaze Questionnaire v1.4.0

A research-oriented application for **gaze-based questionnaires** using **eye tracking**, **blink/dwell activation**, and **smooth pursuit interaction**.  
The system enables hands-free answering of questionnaires and logs fine-grained interaction data for later analysis.

This project is intended for **HCI / Eye-Tracking research**, usability studies, and experimental evaluation of alternative input modalities.

Download latest version as zip >> [here](https://github.com/ardakizilenis/GazeQuestionnaire/archive/refs/tags/v1.4.0.zip) <<

---

### ++ New Features in 1.4 ++

  - New Calibration from [EyeTrax](https://github.com/ck-zhang/EyeTrax): **Dense Grid Calibration**: Custom number of calibration points, determine rows and colums
  - New Filters: **kalman-ema with ema-alpha value**, determining the strength of the smoothing
  - **KDE confidence**, **EMA strength** and **Dense-Calibration Rows and Columns** (DC Rows, DC Col) are editable in the Builder Tool  
  - *****NOTE: The Questionnaire layout structure has been changed with Version 1.4. For questionnaires with older formatting, please download the Version [v1.3.0](https://github.com/ardakizilenis/GazeQuestionnaire/archive/refs/tags/v1.3.0.zip)*****

---

## Quick Start

#### 1) Install the Libraries

In your terminal, `cd` to the folder where you cloned it (root) and execute...

on MacOS (tested):

```bash
chmod +x setup_macos.sh
./setup_macos.sh
```

on Windows:

```bash
requirements installations coming soon...
```

#### 2) Activate your virtual environment

In the Terminal, activate your virtual environment:

`
source env/bin/activate
`
#### 3) Check if it was installed correctly

When you type

`
gq-run --version
`

in the Terminal, you should see the current version Number.
Running `gq-run` with any flags for the first time initially can take longer.

For all available Flags, type

`gq-run --help`

#### 4) Run the Questionnaire Builder Tool

`
gq-run --builder
`

#### 5) CRUD Questionnaires 

Create, Read, Update or Delete the Demo Questionnaire or your own questionnaires.
>***IMPORTANT***: Save and load your Questionnaire JSONs ALWAYS in and from the `/questionnaires/` folder in the project or they won't execute!

#### 6) Save

Click the Save in the toolbar or press `Ctrl + S` / `command + S` and select `/questionnaires/` as taget folder. **Again, this is important!!**

#### 7) Run the questionnaire

Run your questionnaire like following, without the `.json` ending.

`
gq-run your_questionnaire
`

e.g.:

`
gq-run demo
`


Execution flow:
- Asking for Participant Name
- Asking for Run Order (useful for multiple questionnaires)
- Selected Kalibration Method
- Selected Filter Method
- Fullscreen questionnaire with Questions from the JSON Questionnaire

---

### `gq-run`-Flags

| Command                |                                                   Description                                                   |
|:-----------------------|:---------------------------------------------------------------------------------------------------------------:|
| `qg-run questionnaire` | Searchs for a Questionnaire File `questionnaire.json` and runs the questionnaire, if it is in the proper format |
| `gq-run --builder`     |          Runs the Questionnaire Builder/Editor Tool to create questionnaire JSONs in the proper Format          |
| `gq-run --list`        |                    Shows all the executable Questionnaires in the `questionnaires`-Directory                    |
| `gq-run --version`     |                                 Displays the current GazeQuestionnaire Version                                  |
| `gq-run --help`        |                                  Shows the Help Menu for all `gq-run`-Commands                                  |

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

## Previous Releases

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

## Project Tree

```bash
.
├── /controller
│   ├── __init__.py
│   └── main_window.py
├── /data
├── /gaze
│   ├── __init__.py
│   └── eyetracker_worker.py
├── /questionnaires
│   └── demo.json
├── /tools
│   ├── __init__.py
│   ├── questionnaire_builder.py
│   ├── stylesheets.py
│   └── themes.py
├── /widgets
│   ├── /question_types
│   │   ├── __init__.py
│   │   ├── InfoWidget.py
│   │   ├── LikertScaleQuestionWidget.py
│   │   ├── MultipleChoiceQuestionWidget.py
│   │   ├── SmoothPursuit_LikertScaleWidget.py
│   │   ├── SmoothPursuit_MultipleChoiceWidget
│   │   ├── SmoothPursuit_YesNoWidget.py
│   │   ├── TextInputWidget.py
│   │   └── YesNoQuestionWidget.py
│   ├── __init__.py
│   └── gaze_widget.py
├── .gitignore
├── gaze_model.pkl
├── main.py
├── pyproject.toml
├── README.md
├── setup_macos.sh
└── setup_windows.ps1
```

---

## Logging & Output

Each `run` creates a new directory:

```bash
/data
└── /participantName_runX_questionnaireName_timestamp
    ├── participantName_runX_questionnaire_clicks.csv
    └── participantName_runX_questionnaire_logs.csv
```

**participantName_runX_questionnaire_clicks.csv**

One line added per Click with following logs:

|                       `ParticipantID`                       |         `FileName`         |                                        `RunOrder`                                         |        `ClickTime`         |                    `ClickTime_NoReset`                     | `QuestionIndex`  |            `Activation`            |                `QuestionType`                 |     `QuestionText`      |             `TogglesCount`             |           `Toggled Area`            |                          `Calibration`                          |                                 `Filter`                                 |    `DwellTime_ms`     |    `BlinkTime_ms`     |                 `GazePoint_Blocked`                 |
|:-----------------------------------------------------------:|:--------------------------:|:-----------------------------------------------------------------------------------------:|:--------------------------:|:----------------------------------------------------------:|:----------------:|:----------------------------------:|:---------------------------------------------:|:-----------------------:|:--------------------------------------:|:-----------------------------------:|:---------------------------------------------------------------:|:------------------------------------------------------------------------:|:---------------------:|:---------------------:|:---------------------------------------------------:|
| Name/ID of Participant (asked before Questionnaire starts)  | Name of the Questionnaire  | Order of the current run (for multiple Questionnaires, asked before Questionnaire starts) | Time needed for the Click  |  Timestate after each click (no reseting the click timer)  |  Question Index  | Activation Method (Dwell/Blink/SP) | Type of the Question (MCQ/Likert/Text/YesNo)  | Prompt of the Question  | Counted for the Toggles on each Click  | Toggled Area on the specific Click  | Used calibration Method (9-point / 5-point / lissajous / dense) | Filter Method used (Kalman Filter / Kalman-EMA / KDE Filter / No Filter) | Dwell Time Threshold  | Blink Time Threshold  | Boolean Value, if the Gazepoint was Blocked or not? |


**participantName_runX_questionnaire_logs.csv**

One line added per Submit with following logs:

|                       `ParticipantID`                        |        `FileName`         |                                        `RunOrder`                                         |            `TimeNeeded`             |        `QuestionIndex`         |            `Activation`             |                `QuestionType`                 |     `QuestionText`      |            `Answer`             |                 `TotalToggles`                  |                            `TotalResets`                             |                          `TotalBackspaces` |                          `Calibration`                          |                                 `Filter`                                 |    `DwellTime_ms`    |    `BlinkTime_ms`    |                 `GazePoint_Blocked`                 |    `Theme`     |
|:------------------------------------------------------------:|:-------------------------:|:-----------------------------------------------------------------------------------------:|:-----------------------------------:|:------------------------------:|:-----------------------------------:|:---------------------------------------------:|:-----------------------:|:-------------------------------:|:-----------------------------------------------:|:--------------------------------------------------------------------:|-------------------------------------------:|:---------------------------------------------------------------:|:------------------------------------------------------------------------:|:--------------------:|:--------------------:|:---------------------------------------------------:|:--------------:|
|  Name/ID of Participant (asked before Questionnaire starts)  | Name of the Questionnaire | Order of the current run (for multiple Questionnaires, asked before Questionnaire starts) | Total time needed for each Question | Question Index of the Question | Activation Method (Dwell/Blink/SP)  | Type of the Question (MCQ/Likert/Text/YesNo)  | Prompt of the Question  | Given Answer of the Participant | Number of the toggles in Total for the Question | Number of total resets (only in MultipleChoice with Blink and Dwell) | Number of total Backspaces (only for Text) | Used calibration Method (9-point / 5-point / lissajous / dense) | Filter Method used (Kalman Filter / Kalman-EMA / KDE Filter / No Filter) | Dwell Time Threshold | Blink Time Threshold | Boolean Value, if the Gazepoint was Blocked or not? | Applied Theme  |

---

## Question Types

| Type        |       Description        | Labels |                     Activation |
| ----------- |:------------------------:| ------:|-------------------------------:|
| `info`      | Timed Information screen | -      |                                |
| `yesno`     |  Binary Yes/No Question  | -      | Blink / Dwell / Smooth Pursuit |
| `mcq`       | Multiple Choice Question | 4      | Blink / Dwell / Smooth Pursuit |
| `likert`    |       Likert Scale       | 5      | Blink / Dwell / Smooth Pursuit |
| `textgrid`  |        Text Input        | -      |                  Blink / Dwell |

---

## Research Notes

- Obtain ethical approval before running studies with human participants.
- Inform participants about eye tracking, recording, and data handling.
- For synchronization, consider screen and/or audio recording (e.g., OBS).

---

## Used Repositories and Frameworks

- For Eyetracking: `eyetrax`:
  - Repo: https://github.com/ck-zhang/EyeTrax
  - Author: Zhang, C. (2025). EyeTrax (0.2.2) [Computer software]. Zenodo. https://doi.org/10.5281/zenodo.17188537
- For GUI: `pyside6`

---

## License
Intended for academic and research use.
Please [contact the Author](https://www.ardakizilenis.com/contact-en) before any commercial use.

© 2026 Isik Arda Kizilenis. All rights reserved.
