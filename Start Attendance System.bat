@echo off
cd /d "%~dp0"
call venv\Scripts\activate.bat
echo Starting AI Attendance Agent...

start "" powershell -WindowStyle Hidden -Command "$timeout = 30; while ($timeout -gt 0) { try { $response = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/health' -UseBasicParsing -ErrorAction Stop; if ($response.StatusCode -eq 200) { Start-Process 'http://127.0.0.1:8000'; exit } } catch { }; Start-Sleep -Seconds 1; $timeout-- }; Write-Host 'Error: Server failed to start within 30 seconds.'"

uvicorn backend.app.main:app
