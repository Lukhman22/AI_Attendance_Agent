from backend.app.attendance.pdf_parser import read_pdf_attendance

def main():
    with open("uploads/monthperformance23072026121726.pdf", "rb") as f:
        records = read_pdf_attendance(f, "sample.pdf")
    print(f"Extracted {len(records)} records.")
    if records:
        print("First 3 records:")
        for r in records[:3]:
            print(r)
            
if __name__ == "__main__":
    main()
