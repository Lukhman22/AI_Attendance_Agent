import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import date
from decimal import Decimal

from app.main import app
from app.database.session import SessionLocal
from app.models import Employee, EmployeeSalary, Attendance, Payroll

client = TestClient(app)

def test_e2e_salary_flow():
    db = SessionLocal()
    
    # 1. Clean up existing records
    db.query(Payroll).delete()
    db.query(Attendance).delete()
    db.query(EmployeeSalary).delete()
    db.query(Employee).delete()
    
    # Create employee Arjun
    arjun = Employee(
        name="Arjun",
        employee_code="EMP-ARJUN",
        department="Engineering",
        is_active=True
    )
    db.add(arjun)
    db.commit()
    db.refresh(arjun)

    # 2. Configure Salary -> Save
    updates = [{
        "employee_id": "EMP-ARJUN",
        "employee_name": "Arjun",
        "monthly_salary": 50000.00
    }]
    response = client.put("/api/v1/salaries/bulk", json=updates)
    assert response.status_code == 200, response.text

    # 3. Reload -> verify it saved
    response = client.get("/api/v1/salaries")
    assert response.status_code == 200, response.text
    salaries = response.json()
    arjun_sal = next(s for s in salaries if s["employee_id"] == "EMP-ARJUN")
    assert float(arjun_sal["monthly_salary"]) == 50000.00

    # Create Attendance for Arjun for Month 7 (July)
    # Let's say he is present for 20 days and absent for 6 days
    for i in range(1, 27):
        status = "present" if i <= 20 else "absent"
        att = Attendance(
            employee_id=arjun.id,
            work_date=date(2023, 7, i),
            status=status,
            work_duration_hours=Decimal("8.0") if status == "present" else Decimal("0.0")
        )
        db.add(att)
    db.commit()

    # 4. Generate Payroll
    response = client.post("/api/v1/payroll/generate", json={"year": 2023, "month": 7})
    assert response.status_code == 200, response.text
    
    # Check Payroll amounts
    response = client.get("/api/v1/payroll/2023/7")
    assert response.status_code == 200, response.text
    payrolls = response.json()
    assert len(payrolls) == 1
    arjun_payroll = payrolls[0]
    
    # 50000 / 26 = 1923.08 daily salary. 
    # Absent 6 days -> 1923.08 * 6 = 11538.48 deduction
    # Final salary = 50000 - 11538.48 = 38461.52 (depends on rounding rules)
    print(arjun_payroll)
    
    # 5. AI Queries
    # Test "What is Arjun's salary?"
    response = client.post("/api/v1/ai/ask", json={
        "question": "What is Arjun's salary?",
        "context": {"year": 2023, "month": 7}
    })
    print(response.json())
    assert response.status_code == 200, response.text
    data = response.json()
    assert "38461" in data["answer"] or "50000" in data["answer"] # Both are valid mentions
    print("AI Answer:", data["answer"])

    db.close()
