#!/bin/zsh

brew install python3.12@
python3.12 -m venv env
source env/bin/activate
pip install --upgrade pip
pip install pyside6
pip install eyetrax
pip uninstall -y mediapipe
pip uninstall -y mediapipe-silicon mediapipe-rpi 2>/dev/null || true
pip install mediapipe==0.10.14
pip install argcomplete
pip install -e .

