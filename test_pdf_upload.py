import requests

def main():
    files = {'file': ('dummy_attendance.pdf', open('tests/test_data/dummy_attendance.pdf', 'rb'), 'application/pdf')}
    r = requests.post("http://localhost:8000/api/v1/attendance/upload", files=files)
    r.raise_for_status()
    print("Upload result:", r.json())

if __name__ == "__main__":
    main()
