# winget install -e --id Python.Python.3.12

# Projekt-Root
py -3.12 -m venv env

# venv aktivieren
.\env\Scripts\Activate.ps1

python -m pip install --upgrade pip

pip install pyside6
pip install eyetrax

# mediapipe cleanup
pip uninstall -y mediapipe | Out-Null

pip uninstall -y mediapipe-silicon mediapipe-rpi 2>$null

pip install mediapipe==0.10.14

pip install argcomplete

pip install -e .
