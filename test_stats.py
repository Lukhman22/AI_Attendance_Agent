import requests

def main():
    payload = {
        "report_type": "attendance_stats",
        "format": "pdf",
        "work_date": "2026-07-20", # Actually attendance_stats needs start_date and end_date
        "start_date": "2026-07-01",
        "end_date": "2026-07-31"
    }
    r = requests.post("http://localhost:8000/api/v1/reports/generate", json=payload)
    r.raise_for_status()
    print("PDF generated successfully:", r.json())

if __name__ == "__main__":
    main()
