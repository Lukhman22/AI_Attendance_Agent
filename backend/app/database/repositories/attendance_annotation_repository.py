from datetime import date
from typing import Sequence

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ...models import AttendanceAnnotation


class AttendanceAnnotationRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_for_date(self, employee_id: int, work_date: date) -> AttendanceAnnotation | None:
        stmt = select(AttendanceAnnotation).where(
            AttendanceAnnotation.employee_id == employee_id,
            AttendanceAnnotation.work_date == work_date
        )
        return self._db.scalar(stmt)

    def list_for_date(self, work_date: date) -> Sequence[AttendanceAnnotation]:
        stmt = select(AttendanceAnnotation).where(AttendanceAnnotation.work_date == work_date)
        return self._db.scalars(stmt).all()

    def list_for_range(self, start_date: date, end_date: date) -> Sequence[AttendanceAnnotation]:
        stmt = select(AttendanceAnnotation).where(
            AttendanceAnnotation.work_date >= start_date,
            AttendanceAnnotation.work_date <= end_date
        )
        return self._db.scalars(stmt).all()

    def upsert(self, employee_id: int, work_date: date, annotation_type: str, notes: str | None = None) -> AttendanceAnnotation:
        existing = self.get_for_date(employee_id, work_date)
        if existing is None:
            record = AttendanceAnnotation(
                employee_id=employee_id,
                work_date=work_date,
                annotation_type=annotation_type,
                notes=notes,
            )
            self._db.add(record)
            self._db.flush()
            return record

        existing.annotation_type = annotation_type
        existing.notes = notes
        self._db.flush()
        return existing

    def delete(self, annotation_id: int) -> bool:
        stmt = delete(AttendanceAnnotation).where(AttendanceAnnotation.id == annotation_id)
        result = self._db.execute(stmt)
        self._db.flush()
        return result.rowcount > 0
