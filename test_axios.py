import requests
import subprocess
import time
import re

subprocess.Popen(["./dist/AI Attendance Agent.app/Contents/MacOS/AI Attendance Agent"], stdout=open("app_axios.log", "w"), stderr=subprocess.STDOUT)
time.sleep(5)

port = None
with open("app_axios.log") as f:
    for line in f:
        match = re.search(r"http://127.0.0.1:(\d+)", line)
        if match:
            port = match.group(1)
            break

if not port:
    print("Could not find port")
    exit(1)

url = f"http://127.0.0.1:{port}/api/v1/attendance/upload"
try:
    # Explicitly set content-type without boundary, which is what Axios does when you hardcode the header
    headers = {'Content-Type': 'multipart/form-data'}
    with open("valid_attendance.csv", "rb") as f:
        # We manually construct a body to bypass requests' auto-boundary
        body = b'--boundary\r\nContent-Disposition: form-data; name="file"; filename="test.csv"\r\n\r\nsomedata\r\n--boundary--\r\n'
        resp = requests.post(url, data=body, headers=headers)
        print("Status:", resp.status_code)
        print("Body:", resp.text)
except Exception as e:
    print("Failed:", e)

try: requests.post(f"http://127.0.0.1:{port}/api/v1/system/shutdown")
except: pass
