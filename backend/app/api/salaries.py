from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from ..database.session import get_db
from ..schemas import EmployeeSalaryCreate, EmployeeSalaryRead, EmployeeSalaryUpdate
from ..payroll.salary_service import SalaryService

router = APIRouter(prefix="/salaries", tags=["salaries"])

@router.get("", response_model=List[EmployeeSalaryRead])
def get_salaries(db: Session = Depends(get_db)):
    return SalaryService.get_salaries(db)

@router.post("", response_model=EmployeeSalaryRead)
def add_salary(salary_in: EmployeeSalaryCreate, db: Session = Depends(get_db)):
    try:
        return SalaryService.add_salary(db, salary_in)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/bulk")
def bulk_update_salaries(updates: List[Dict[str, Any]], db: Session = Depends(get_db)):
    try:
        SalaryService.bulk_update(db, updates)
        return {"message": "Salaries updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/{salary_id}", response_model=EmployeeSalaryRead)
def update_salary(salary_id: int, salary_in: EmployeeSalaryUpdate, db: Session = Depends(get_db)):
    salary = SalaryService.update_salary(db, salary_id, salary_in)
    if not salary:
        raise HTTPException(status_code=404, detail="Salary not found")
    return salary

@router.delete("/{salary_id}")
def delete_salary(salary_id: int, db: Session = Depends(get_db)):
    try:
        SalaryService.delete_salary(db, salary_id)
        return {"message": "Deleted"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/import/preview")
async def preview_salaries(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        content = await file.read()
        preview = SalaryService.parse_preview(db, content, file.filename)
        return preview
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/import/confirm")
def confirm_import(data: Dict[str, Any], db: Session = Depends(get_db)):
    try:
        SalaryService.confirm_import(db, data)
        return {"message": "Salaries imported successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
