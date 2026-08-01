from app.database.session import SessionLocal
from app.models import Employee, EmployeeSalary, Attendance, Payroll
from datetime import date
import calendar

db = SessionLocal()

# Find the latest month with attendance
latest_att = db.query(Attendance.work_date).order_by(Attendance.work_date.desc()).first()
if not latest_att:
    print("No attendance records found.")
    exit(0)

target_date = latest_att[0]
year, month = target_date.year, target_date.month
start = date(year, month, 1)
end = date(year, month, calendar.monthrange(year, month)[1])

print(f"--- TRACE FOR {month}/{year} ---")

emp_count = db.query(Employee).count()
print(f"1. Employees table: {emp_count}")

att_emps = db.query(Attendance.employee_id).filter(
    Attendance.work_date >= start,
    Attendance.work_date <= end
).distinct().count()
print(f"2. Attendance table (distinct employees): {att_emps}")

sal_count = db.query(EmployeeSalary).count()
print(f"3. EmployeeSalary table: {sal_count}")

# Payroll Generation
from app.payroll.payroll_generator import PayrollGenerator
pg = PayrollGenerator(db)
try:
    generated = pg.generate_month(year, month)
    print(f"4. Payroll Generation: {len(generated)}")
except Exception as e:
    print(f"4. Payroll Generation: FAILED ({e})")

pay_count = db.query(Payroll).filter(Payroll.year == year, Payroll.month == month).count()
print(f"5. Payroll table: {pay_count}")

pay_report = db.query(Payroll).filter(Payroll.month == month, Payroll.year == year).count()
print(f"6. Monthly Report: {pay_report}")

db.close()
