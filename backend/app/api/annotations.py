from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException

from ..database.session import get_db
from sqlalchemy.orm import Session
from ..database.repositories import AttendanceAnnotationRepository
from ..schemas.attendance_annotation import AttendanceAnnotationRead, AttendanceAnnotationUpsert

router = APIRouter(prefix="/annotations", tags=["annotations"])

@router.put("/{employee_id}/{work_date}", response_model=AttendanceAnnotationRead)
def upsert_annotation(
    employee_id: int,
    work_date: date,
    body: AttendanceAnnotationUpsert,
    db: Session = Depends(get_db),
) -> AttendanceAnnotationRead:
    repo = AttendanceAnnotationRepository(db)
    annotation = repo.upsert(employee_id, work_date, body.annotation_type, body.notes)
    db.commit()
    return AttendanceAnnotationRead.model_validate(annotation)

@router.delete("/{annotation_id}", response_model=dict)
def delete_annotation(
    annotation_id: int,
    db: Session = Depends(get_db),
) -> dict:
    repo = AttendanceAnnotationRepository(db)
    success = repo.delete(annotation_id)
    if not success:
        raise HTTPException(status_code=404, detail="Annotation not found")
    db.commit()
    return {"status": "deleted"}

@router.get("", response_model=List[AttendanceAnnotationRead])
def list_annotations(
    work_date: Optional[date] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
) -> List[AttendanceAnnotationRead]:
    repo = AttendanceAnnotationRepository(db)
    if work_date:
        records = repo.list_for_date(work_date)
    elif start_date and end_date:
        records = repo.list_for_range(start_date, end_date)
    else:
        raise HTTPException(status_code=400, detail="Must provide work_date or start_date/end_date")
    
    return [AttendanceAnnotationRead.model_validate(r) for r in records]
