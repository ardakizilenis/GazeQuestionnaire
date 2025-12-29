# setup_windows.ps1
# Run in PowerShell (not CMD)

Write-Host "Setting up Python environment for GazeQuestionnaire (Windows)"

# 1. Check Python 3.12
$python = Get-Command python -ErrorAction SilentlyContinue

if (-not $python) {
    Write-Error "Python not found. Please install Python 3.12 from https://www.python.org/"
    exit 1
}

$version = python --version
if ($version -notmatch "3.12") {
    Write-Error "Python 3.12 is required. Found: $version"
    exit 1
}

# 2. Create virtual environment
python -m venv env

# 3. Activate venv
.\env\Scripts\Activate.ps1

# 4. Upgrade pip
python -m pip install --upgrade pip

# 5. Install dependencies
pip install pyside6
pip install eyetrax

# 6. Mediapipe cleanup & pin
pip uninstall -y mediapipe mediapipe-silicon mediapipe-rpi 2>$null
pip install mediapipe==0.10.14

Write-Host "Setup completed successfully"
Write-Host "Activate later with: .\env\Scripts\Activate.ps1"
