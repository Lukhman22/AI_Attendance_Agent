import csv
import io
import fitz
import re
from datetime import date
from typing import List, Dict, Any, Tuple
from decimal import Decimal, InvalidOperation
from sqlalchemy.orm import Session
from sqlalchemy import select, update

from ..models.EmployeeSalary import EmployeeSalary
from ..models.Employee import Employee
from ..schemas import EmployeeSalaryCreate, EmployeeSalaryUpdate
from ..config.settings import get_settings

class SalaryService:
    @staticmethod
    def get_salaries(db: Session):
        employees = db.scalars(select(Employee).order_by(Employee.name)).all()
        salaries = db.scalars(select(EmployeeSalary)).all()
        salary_map = {s.employee_id: s for s in salaries}
        
        result = []
        for emp in employees:
            sal = salary_map.get(emp.employee_code)
            result.append({
                "id": sal.id if sal else 0,
                "employee_id": emp.employee_code,
                "employee_name": emp.name,
                "department": emp.department,
                "monthly_salary": sal.monthly_salary if sal else Decimal("0.00"),
                "effective_from": sal.effective_from if sal else None
            })
        
        emp_codes = {emp.employee_code for emp in employees}
        for sal in salaries:
            if sal.employee_id not in emp_codes:
                result.append({
                    "id": sal.id,
                    "employee_id": sal.employee_id,
                    "employee_name": sal.employee_name or "Unknown",
                    "department": "",
                    "monthly_salary": sal.monthly_salary,
                    "effective_from": sal.effective_from
                })
        return result

    @staticmethod
    def add_salary(db: Session, salary_in: EmployeeSalaryCreate):
        settings = get_settings()
        if salary_in.monthly_salary > Decimal(str(settings.max_monthly_salary)):
            raise ValueError(f"Salary exceeds configured maximum of {settings.max_monthly_salary}")
        
        db_salary = EmployeeSalary(
            employee_id=salary_in.employee_id,
            employee_name=salary_in.employee_name,
            monthly_salary=salary_in.monthly_salary,
            effective_from=salary_in.effective_from or date.today()
        )
        db.add(db_salary)
        db.commit()
        db.refresh(db_salary)
        return db_salary

    @staticmethod
    def update_salary(db: Session, salary_id: int, salary_in: EmployeeSalaryUpdate):
        settings = get_settings()
        if salary_in.monthly_salary > Decimal(str(settings.max_monthly_salary)):
            raise ValueError(f"Salary exceeds configured maximum of {settings.max_monthly_salary}")
            
        db_salary = db.get(EmployeeSalary, salary_id)
        if not db_salary:
            return None
        db_salary.monthly_salary = salary_in.monthly_salary
        db.commit()
        db.refresh(db_salary)
        return db_salary

    @staticmethod
    def bulk_update(db: Session, updates: List[Dict[str, Any]]):
        settings = get_settings()
        max_sal = Decimal(str(settings.max_monthly_salary))
        
        for update_item in updates:
            salary = Decimal(str(update_item["monthly_salary"]))
            if salary > max_sal:
                raise ValueError(f"Salary exceeds configured maximum of {settings.max_monthly_salary}")
            
            salary_id = update_item.get("id")
            if salary_id and salary_id > 0:
                db_salary = db.get(EmployeeSalary, salary_id)
                if db_salary:
                    db_salary.monthly_salary = Decimal(str(update_item["monthly_salary"]))
            else:
                db_salary = EmployeeSalary(
                    employee_id=update_item["employee_id"],
                    employee_name=update_item.get("employee_name", ""),
                    monthly_salary=Decimal(str(update_item["monthly_salary"])),
                    effective_from=date.today()
                )
                db.add(db_salary)
        db.commit()

    @staticmethod
    def delete_salary(db: Session, salary_id: int):
        db_salary = db.get(EmployeeSalary, salary_id)
        if db_salary:
            db.delete(db_salary)
            db.commit()

    @staticmethod
    def _parse_csv(content: bytes) -> List[Dict[str, str]]:
        try:
            text = content.decode('utf-8-sig')
        except UnicodeDecodeError:
            text = content.decode('utf-8', errors='ignore')
            
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        records = []
        try:
            reader = csv.DictReader(io.StringIO(text, newline=''))
            for row in reader:
                cleaned_row = {k.strip().lower() if k else '': v.strip() for k, v in row.items()}
                emp_id = cleaned_row.get('employee id') or cleaned_row.get('employee_id') or cleaned_row.get('id')
                emp_name = cleaned_row.get('employee name') or cleaned_row.get('employee_name') or cleaned_row.get('name')
                salary = cleaned_row.get('salary') or cleaned_row.get('monthly salary') or cleaned_row.get('monthly_salary')
                records.append({
                    "employee_id": emp_id or "",
                    "employee_name": emp_name or "",
                    "monthly_salary": salary or ""
                })
        except Exception as e:
            raise ValueError(f"Malformed CSV: {str(e)}")
        return records

    @staticmethod
    def _parse_pdf(content: bytes) -> List[Dict[str, str]]:
        records = []
        doc = fitz.open(stream=content, filetype="pdf")
        for page in doc:
            text = page.get_text()
            # Simple heuristic extraction: looking for ID, Name, Salary
            # We can use regex to find lines like "EMP001, John Doe, 50000" or similar
            lines = text.split('\n')
            for line in lines:
                # Basic comma or tab separated parsing if present
                parts = [p.strip() for p in re.split(r'[,|\t]', line) if p.strip()]
                if len(parts) >= 3:
                    # check if the first part looks like an ID and last looks like salary
                    if re.match(r'^[A-Z0-9_-]+$', parts[0]) and re.match(r'^[\d\.]+$', parts[-1]):
                        records.append({
                            "employee_id": parts[0],
                            "employee_name": " ".join(parts[1:-1]),
                            "monthly_salary": parts[-1]
                        })
        return records

    @staticmethod
    def parse_preview(db: Session, file_content: bytes, filename: str) -> Dict[str, Any]:
        if filename.lower().endswith('.csv'):
            raw_records = SalaryService._parse_csv(file_content)
        elif filename.lower().endswith('.pdf'):
            raw_records = SalaryService._parse_pdf(file_content)
        else:
            raise ValueError("Unsupported file format. Use CSV or PDF.")

        new_employees = []
        existing_to_update = []
        invalid_rows = []
        duplicates = []
        
        seen_keys = set()
        
        # preload mapping of existing salaries by id and name
        all_salaries = db.scalars(select(EmployeeSalary)).all()
        id_map = {s.employee_id: s for s in all_salaries}
        name_map = {s.employee_name.lower(): s for s in all_salaries if s.employee_name}
        
        # preload active employees to validate matching
        all_emps = db.scalars(select(Employee)).all()
        emp_id_map = {e.employee_code: e for e in all_emps}
        emp_name_map = {e.name.lower(): e for e in all_emps if e.name}

        for idx, row in enumerate(raw_records):
            emp_id = row.get("employee_id")
            emp_name = row.get("employee_name")
            salary_str = row.get("monthly_salary")
            
            if not emp_id and not emp_name:
                invalid_rows.append({"row": idx+1, "data": row, "reason": "Missing ID and Name"})
                continue
                
            if not salary_str:
                invalid_rows.append({"row": idx+1, "data": row, "reason": "Missing Salary"})
                continue
            
            try:
                salary = Decimal(salary_str.replace(',', ''))
                if salary <= 0:
                    invalid_rows.append({"row": idx+1, "data": row, "reason": "Salary must be > 0"})
                    continue
                settings = get_settings()
                if salary > Decimal(str(settings.max_monthly_salary)):
                    invalid_rows.append({"row": idx+1, "data": row, "reason": f"Exceeds max salary {settings.max_monthly_salary}"})
                    continue
            except InvalidOperation:
                invalid_rows.append({"row": idx+1, "data": row, "reason": "Invalid Salary format"})
                continue
            
            # Match employee
            matched_id = emp_id
            matched_name = emp_name
            
            if not matched_id and emp_name:
                emp_match = emp_name_map.get(emp_name.lower())
                if emp_match:
                    matched_id = emp_match.employee_code
                else:
                    sal_match = name_map.get(emp_name.lower())
                    if sal_match:
                        matched_id = sal_match.employee_id
            
            if not matched_id:
                invalid_rows.append({"row": idx+1, "data": row, "reason": "Could not match employee"})
                continue
            
            # Duplicates check
            if matched_id in seen_keys:
                duplicates.append({"row": idx+1, "data": row, "reason": "Duplicate in file"})
                continue
            seen_keys.add(matched_id)

            existing = id_map.get(matched_id)

            item = {
                "employee_id": matched_id,
                "employee_name": matched_name or (existing.employee_name if existing else ""),
                "monthly_salary": str(salary)
            }

            if existing:
                if Decimal(existing.monthly_salary) == salary:
                    invalid_rows.append({"row": idx+1, "data": item, "reason": "No change to salary"})
                else:
                    item["old_salary"] = str(existing.monthly_salary)
                    existing_to_update.append(item)
            else:
                new_employees.append(item)

        return {
            "new_employees": new_employees,
            "existing_to_update": existing_to_update,
            "invalid_rows": invalid_rows,
            "duplicates": duplicates
        }

    @staticmethod
    def confirm_import(db: Session, data: Dict[str, Any]):
        new_emps = data.get("new_employees", [])
        updates = data.get("existing_to_update", [])
        
        for item in new_emps:
            db_salary = EmployeeSalary(
                employee_id=item["employee_id"],
                employee_name=item["employee_name"],
                monthly_salary=Decimal(item["monthly_salary"]),
                effective_from=date.today()
            )
            db.add(db_salary)
            
        for item in updates:
            stmt = select(EmployeeSalary).where(EmployeeSalary.employee_id == item["employee_id"])
            existing = db.scalars(stmt).first()
            if existing:
                existing.monthly_salary = Decimal(item["monthly_salary"])
                
        db.commit()
