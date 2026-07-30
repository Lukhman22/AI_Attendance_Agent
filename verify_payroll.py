import os
import sys

# Ensure backend path is configured
base_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(base_path, 'backend'))

from backend.app.database.session import SessionLocal
from backend.app.models.Employee import Employee
from backend.app.models.EmployeeSalary import EmployeeSalary
from backend.app.models.Attendance import Attendance
from backend.app.payroll.payroll_generator import PayrollGenerator
from backend.app.database.base import Base
from backend.app.database.session import engine
from datetime import date
from decimal import Decimal

Base.metadata.create_all(bind=engine)
db = SessionLocal()

# Add a dummy employee and attendance
emp = db.query(Employee).filter_by(employee_code="TEST100").first()
if not emp:
    emp = Employee(employee_code="TEST100", name="Test Employee", monthly_salary=Decimal("0.00"))
    db.add(emp)
    db.commit()

# Add dummy attendance for year 2026, month 6
att = db.query(Attendance).filter_by(employee_id=emp.id, work_date=date(2026, 6, 1)).first()
if not att:
    att = Attendance(employee_id=emp.id, work_date=date(2026, 6, 1), status="present")
    db.add(att)
    db.commit()

# Ensure salary is missing first
sal = db.query(EmployeeSalary).filter_by(employee_id="TEST100").first()
if sal:
    db.delete(sal)
    db.commit()

pg = PayrollGenerator(db)
try:
    print("Testing without salary...")
    pg.generate_month(2026, 6)
    print("FAIL: Expected ApplicationError due to missing salary!")
except Exception as e:
    print(f"SUCCESS: Caught expected error: {e}")

# Now add salary
print("Adding EmployeeSalary...")
sal = EmployeeSalary(employee_id="TEST100", employee_name="Test Employee", monthly_salary=Decimal("50000.00"))
db.add(sal)
db.commit()

try:
    print("Testing with salary...")
    results = pg.generate_month(2026, 6)
    for r in results:
        if r.employee_id == emp.id:
            print(f"Payroll generated for TEST100: Final Salary = {r.final_salary}")
            if float(r.final_salary) > 0:
                print("SUCCESS: Payroll calculation used the stored salary!")
except Exception as e:
    print(f"FAIL: Unexpected error during payroll generation: {e}")
