import subprocess
import time
import requests
import os
import sys

db_file = os.path.expanduser("~/Library/Application Support/AIAttendanceAgent/database.sqlite3")
if os.path.exists(db_file):
    os.remove(db_file)

print("Starting backend...")
proc = subprocess.Popen(["./venv/bin/python", "-m", "uvicorn", "backend.app.main:app", "--port", "8008"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

try:
    for i in range(10):
        try:
            r = requests.get("http://localhost:8008/api/v1/employees")
            if r.status_code == 200:
                print("Backend started successfully.")
                break
        except Exception:
            pass
        time.sleep(1)
    else:
        print("Backend failed to start. Logs:")
        proc.terminate()
        stdout, _ = proc.communicate(timeout=2)
        print(stdout)
        sys.exit(1)

    r = requests.get("http://localhost:8008/api/v1/employees")
    emps = r.json()
    print("Initial Employees:", len(emps))
    assert len(emps) == 0, "Database should be empty!"

    print("Uploading CSV...")
    csv_content = b"Empcode,Name,Date,In Time,Out Time\nNEW001,Demo Guy,2026-08-01,09:00,17:00\n"
    r = requests.post("http://localhost:8008/api/v1/attendance/upload", files={"file": ("test.csv", csv_content, "text/csv")})
    print("Upload status:", r.status_code)

    r = requests.get("http://localhost:8008/api/v1/employees")
    emps = r.json()
    print("Employees after upload:", len(emps))
    assert len(emps) == 1, "Should have exactly 1 employee!"
    assert emps[0]["name"] == "Demo Guy", "Should be the newly uploaded employee!"
    print("SUCCESS: Verified empty db and correct upload flow!")

finally:
    proc.terminate()
    proc.wait(timeout=5)
