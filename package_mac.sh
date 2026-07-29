#!/bin/bash
set -e

echo "========================================"
echo "macOS Deployment Pipeline"
echo "========================================"

if [ ! -d "venv" ]; then
    echo "Virtual environment 'venv' not found."
    echo "Creating Python 3.12 virtual environment..."
    python3.12 -m venv venv
fi

source venv/bin/activate
echo "Installing dependencies from requirements.txt..."
pip install -r requirements.txt

echo "Starting robust build pipeline..."
python build.py

echo "macOS Pipeline Execution Complete."
