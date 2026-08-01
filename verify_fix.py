import time
import requests
import subprocess
import signal

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
    print("Starting server...")
    server = subprocess.Popen(["venv/bin/python", "-m", "uvicorn", "backend.app.main:app", "--port", "8000"])
    
    try:
        wait_for_server()
        
        # 1. Register employee
        emp = requests.post(f"{BASE_URL}/employees", json={
            "employee_code": "E01", "name": "Arjun", "working_days_per_month": 26
        }).json()
        
        requests.post(f"{BASE_URL}/employees/salaries", json={
            "employee_id": str(emp["id"]), "monthly_salary": 50000
        })
        
        # 2. Upload attendance (assume Arjun is present 2 days, absent 1 day)
        csv = "Employee ID,Employee Name,Date,Check In,Check Out,Break Duration,Status\n"
        csv += "E01,Arjun,2026-07-01,09:00,17:00,01:00,Present\n"
        csv += "E01,Arjun,2026-07-02,09:00,17:00,01:00,Present\n"
        csv += "E01,Arjun,2026-07-03,,,,Absent\n"  # absent
        
        with open("test_att.csv", "w") as f:
            f.write(csv)
            
        with open("test_att.csv", "rb") as f:
            resp = requests.post(f"{BASE_URL}/attendance/upload", files={"file": f}).json()
            print("Upload response:", resp)
            
        # 3. Check employees API
        emps = requests.get(f"{BASE_URL}/employees").json()
        arjun = emps[0]
        print("Employee record:", arjun)
        att_pct = arjun.get("attendance_percentage")
        # 2 present, 1 absent = 66.7%
        print(f"Attendance % on Employee: {att_pct}%")
        assert att_pct == 66.7, f"Expected 66.7, got {att_pct}"
        
        # 4. Check Payroll
        requests.post(f"{BASE_URL}/payroll/generate", json={"year": 2026, "month": 7})
        payrolls = requests.get(f"{BASE_URL}/payroll", params={"year": 2026, "month": 7}).json()
        if not payrolls:
            raise Exception("No payrolls generated")
        pr = payrolls[0]
        # Payroll percentage isn't exposed in PayrollRead, but we can check if it matches in insights
        print("Payroll generated:", pr["present_days"], "present,", pr["absent_days"], "absent")
        
        # 5. Check Monthly Attendance Summary (stats)
        stats = requests.get(f"{BASE_URL}/attendance/stats", params={"start_date": "2026-07-01", "end_date": "2026-07-31"}).json()
        stat_pct = stats[0]["attendance_percentage"]
        print(f"Attendance % in Stats: {stat_pct}%")
        assert stat_pct == 66.7, f"Expected 66.7, got {stat_pct}"
        
        print("All checks passed!")
    finally:
        server.terminate()
        server.wait()

if __name__ == "__main__":
    main()
