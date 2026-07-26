@echo off
echo ========================================
echo Windows Deployment Pipeline
echo ========================================

IF NOT EXIST "venv\Scripts\activate.bat" (
    echo Virtual environment 'venv' not found.
    echo Creating Python virtual environment...
    python -m venv venv
)

call venv\Scripts\activate.bat
echo Installing dependencies from requirements.txt...
pip install -r requirements.txt

echo Starting robust build pipeline...
python build.py

echo Windows Pipeline Execution Complete.
pause
