import requests
import sys
import time
import subprocess
import re

subprocess.Popen(["./dist/AI Attendance Agent.app/Contents/MacOS/AI Attendance Agent"], stdout=open("app.log", "w"), stderr=subprocess.STDOUT)
time.sleep(5)

port = None
with open("app.log") as f:
    for line in f:
        match = re.search(r"http://127.0.0.1:(\d+)", line)
        if match:
            port = match.group(1)
            break

if not port:
    print("Could not find port")
    sys.exit(1)

print(f"Testing on port {port}")
url = f"http://127.0.0.1:{port}/api/v1/attendance/upload"
with open("valid_attendance.csv", "rb") as f:
    try:
        response = requests.post(url, files={"file": ("valid_attendance.csv", f, "text/csv")})
        print(response.status_code)
        print(response.text)
    except Exception as e:
        print(f"Request failed: {e}")

try:
    requests.post(f"http://127.0.0.1:{port}/api/v1/system/shutdown")
except: pass
time.sleep(2)
with open("app.log") as f:
    print("APP LOGS:")
    print(f.read())
