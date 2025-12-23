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

## 📁 Project Structure

