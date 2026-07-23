from datetime import date
from typing import Optional

from pydantic import BaseModel


class AttendanceAnnotationBase(BaseModel):
    annotation_type: str
    notes: Optional[str] = None


class AttendanceAnnotationUpsert(AttendanceAnnotationBase):
    pass


class AttendanceAnnotationRead(AttendanceAnnotationBase):
    id: int
    employee_id: int
    work_date: date

    class Config:
        from_attributes = True
