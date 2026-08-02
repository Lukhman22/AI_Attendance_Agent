import os
import sys
from datetime import date
sys.path.append(os.path.abspath("."))
from backend.app.database.session import SessionLocal, engine
from backend.app.database.base import Base
from backend.app.models.Employee import Employee
from backend.app.models.Attendance import Attendance
from backend.app.models.EmployeeSalary import EmployeeSalary
from backend.app.services.report_service import ReportService
from backend.app.config import get_settings

def test_reports():
    Base.metadata.create_all(engine)
    db = SessionLocal()
    settings = get_settings()
    
    # Add dummy data
    emp = db.query(Employee).filter_by(employee_code="E01").first()
    if not emp:
        emp = Employee(employee_code="E01", name="Arjun", department="IT", working_days_per_month=22, is_active=True)
        db.add(emp)
        db.commit()
        
    sal = db.query(EmployeeSalary).filter_by(employee_id="E01").first()
    if not sal:
        sal = EmployeeSalary(employee_id="E01", monthly_salary=50000, employee_name="Arjun")
        db.add(sal)
        db.commit()
    
    att = db.query(Attendance).filter_by(employee_id=emp.id, work_date=date(2026, 7, 20)).first()
    if not att:
        att = Attendance(employee_id=emp.id, work_date=date(2026, 7, 20), status="absent", leave_reason="Sick Leave", missing_hours=8, daily_deduction=100, source="manual")
        db.add(att)
        db.commit()
    
    svc = ReportService(db, settings)
    
    try:
        # Test PDF
        pdf_res = svc.generate(
            report_type="daily_summary",
            fmt="pdf",
            work_date=date(2026, 7, 20)
        )
        print("PDF generated:", pdf_res)
        
        # Test Excel
        excel_res = svc.generate(
            report_type="monthly_payroll",
            fmt="excel",
            year=2026,
            month=7
        )
        print("Excel generated:", excel_res)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print("Error generating reports:", e)
    finally:
        db.close()

if __name__ == "__main__":
    test_reports()
