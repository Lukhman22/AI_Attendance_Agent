from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

c = canvas.Canvas("tests/test_data/dummy_attendance.pdf", pagesize=A4)

# Page 1
c.drawString(100, 800, "Company: Acme Corp")
c.drawString(100, 780, "Department: Engineering")
c.drawString(100, 760, "Report Month: April-2026")
c.drawString(100, 740, "Employee Code: E001      Employee Name: Alice Smith")
c.drawString(100, 720, "Date    IN    OUT   WORK  BREAK OT    STATUS")
c.drawString(100, 700, "1 09:00 17:00 08:00 01:00 00:00 P")
c.drawString(100, 680, "2 09:15 17:00 07:45 01:00 00:00 P")
c.drawString(100, 660, "3 - - - - - WO")
c.showPage()

# Page 2 (Multi-page employee data)
c.drawString(100, 800, "Employee Code: E002      Employee Name: Bob Jones")
c.drawString(100, 780, "Date    IN    OUT   WORK  BREAK OT    STATUS")
c.drawString(100, 760, "1 10:00 18:00 08:00 01:00 00:00 P")
c.drawString(100, 740, "30 10:00 18:00 08:00 01:00 00:00 P")
c.showPage()

c.save()
print("Generated tests/test_data/dummy_attendance.pdf")
