#!/bin/bash

# Change to the directory where this script is located
cd "$(dirname "$0")"

echo "Starting AI Attendance Agent..."

# Activate virtual environment
source venv/bin/activate

# Wait for the server to start (up to 30 seconds) and open the browser
(
  TIMEOUT=30
  while [ $TIMEOUT -gt 0 ]; do
    if curl -s http://127.0.0.1:8000/health > /dev/null; then
      xdg-open http://127.0.0.1:8000
      exit 0
    fi
    sleep 1
    ((TIMEOUT--))
  done
  echo ""
  echo "Error: Server failed to start within 30 seconds."
  echo "Please check the terminal output for errors."
) &

# Start the FastAPI server
uvicorn backend.app.main:app
