import requests
import time
import subprocess
import os

print("Starting backend...")
proc = subprocess.Popen(["./venv/bin/python", "-m", "uvicorn", "backend.app.main:app", "--port", "8000"], env=dict(os.environ, DATABASE_URL="sqlite:///test_verify.db"))

for i in range(10):
    try:
        resp = requests.get("http://localhost:8000/api/v1/employees")
        if resp.status_code == 200:
            break
    except Exception:
        pass
    print(f"Waiting for backend to start... {i}")
    time.sleep(1)

try:
    print("Checking employees...")
    resp = requests.get("http://localhost:8000/api/v1/employees")
    resp.raise_for_status()
    employees = resp.json()
    print(f"Employees count: {len(employees)}")
    if len(employees) > 0:
        print("ERROR: Employees are not empty!", employees)
        exit(1)
        
    print("Uploading CSV...")
    csv_content = b"Empcode,Name,Date,In Time,Out Time\nNEW01,Test User,2026-08-01,09:00,17:00\n"
    resp = requests.post("http://localhost:8000/api/v1/attendance/upload", files={"file": ("test.csv", csv_content, "text/csv")})
    resp.raise_for_status()
    print("Upload result:", resp.json())
    
    print("Checking employees after upload...")
    resp = requests.get("http://localhost:8000/api/v1/employees")
    resp.raise_for_status()
    employees = resp.json()
    print(f"Employees count after upload: {len(employees)}")
    if len(employees) != 1 or employees[0]["name"] != "Test User":
        print("ERROR: Employees do not match expected!", employees)
        exit(1)
        
    print("SUCCESS: The system behaves as expected!")
finally:
    proc.terminate()
    proc.wait()
    if os.path.exists("test_verify.db"):
        os.remove("test_verify.db")
