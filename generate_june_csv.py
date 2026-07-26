import requests
import json

def main():
    payload = {
        "report_type": "attendance_stats",
        "format": "csv",
        "start_date": "2026-06-01",
        "end_date": "2026-06-30"
    }
    r = requests.post("http://localhost:8000/api/v1/reports/generate", json=payload)
    r.raise_for_status()
    print("CSV generated successfully:", r.json())
    with open(r.json()["path"], "r") as f:
        print(f.read())

if __name__ == "__main__":
    main()
