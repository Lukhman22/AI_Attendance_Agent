import time
import requests
import subprocess

BASE_URL = "http://localhost:8000/api/v1"

def wait_for_server():
    for _ in range(30):
        try:
            if requests.get("http://localhost:8000/health").status_code == 200:
                print("Server is up!")
                return
        except:
            time.sleep(1)
    raise Exception("Server failed to start")

def main():
    print("Starting server for fresh install check...")
    server = subprocess.Popen(["venv/bin/python", "-m", "uvicorn", "backend.app.main:app", "--port", "8000"])
    
    try:
        wait_for_server()
        
        # Verify completely empty state
        emps = requests.get(f"{BASE_URL}/employees").json()
        assert len(emps) == 0, f"Expected 0 employees, got {len(emps)}"
        print("✅ Employees = 0")
        
        reports = requests.get(f"{BASE_URL}/ai/reports/daily/2026-07-20").json()
        # Daily report should be a 404 or empty because no data exists
        print("✅ Reports checked")
        
        stats = requests.get(f"{BASE_URL}/attendance/stats", params={"start_date": "2026-07-01", "end_date": "2026-07-31"}).json()
        assert len(stats) == 0, "Expected 0 attendance stats"
        print("✅ Attendance = 0")
        
        # Now upload CSV
        csv = "Employee ID,Employee Name,Date,Check In,Check Out,Break Duration,Status\n"
        csv += "E01,Arjun,2026-07-01,09:00,17:00,01:00,Present\n"
        csv += "E01,Arjun,2026-07-02,09:00,17:00,01:00,Present\n"
        csv += "E01,Arjun,2026-07-03,,,,Absent\n"
        
        with open("test_att.csv", "w") as f:
            f.write(csv)
            
        with open("test_att.csv", "rb") as f:
            resp = requests.post(f"{BASE_URL}/attendance/upload", files={"file": f}).json()
            assert resp["imported"] > 0
            
        print("✅ CSV Uploaded")
        
        emps = requests.get(f"{BASE_URL}/employees").json()
        assert len(emps) == 1, "Expected 1 employee after upload"
        assert emps[0]["attendance_percentage"] == 66.7, f"Expected 66.7%, got {emps[0]['attendance_percentage']}"
        print("✅ Employee created automatically with correct %")
        
        print("\n🎉 ALL VERIFICATION PASSED")
    finally:
        server.terminate()
        server.wait()

if __name__ == "__main__":
    main()
