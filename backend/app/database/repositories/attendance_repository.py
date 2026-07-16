from datetime import date

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, joinedload

from ...models import Attendance, Employee


class AttendanceRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_employee_and_date(self, employee_id: int, work_date: date) -> Attendance | None:
        stmt = select(Attendance).where(
            Attendance.employee_id == employee_id,
            Attendance.work_date == work_date,
        )
        return self._db.scalar(stmt)

    def upsert(self, record: Attendance) -> Attendance:
        existing = self.get_by_employee_and_date(record.employee_id, record.work_date)
        if existing is None:
            self._db.add(record)
            self._db.flush()
            return record

        existing.check_in = record.check_in
        existing.check_out = record.check_out
        existing.work_duration_hours = record.work_duration_hours
        existing.break_duration_hours = record.break_duration_hours
        existing.overtime_hours = record.overtime_hours
        existing.status = record.status
        existing.missing_hours = record.missing_hours
        existing.daily_deduction = record.daily_deduction
        existing.source = record.source
        self._db.flush()
        return existing

    def list_for_date(self, work_date: date) -> list[Attendance]:
        stmt = (
            select(Attendance)
            .options(joinedload(Attendance.employee))
            .where(Attendance.work_date == work_date)
            .order_by(Attendance.id)
        )
        return list(self._db.scalars(stmt).unique().all())

    def list_for_range(self, start: date, end: date) -> list[Attendance]:
        stmt = (
            select(Attendance)
            .options(joinedload(Attendance.employee))
            .where(Attendance.work_date >= start, Attendance.work_date <= end)
            .order_by(Attendance.work_date, Attendance.id)
        )
        return list(self._db.scalars(stmt).unique().all())

    def list_for_employee_range(self, employee_id: int, start: date, end: date) -> list[Attendance]:
        stmt = (
            select(Attendance)
            .options(joinedload(Attendance.employee))
            .where(
                Attendance.employee_id == employee_id,
                Attendance.work_date >= start,
                Attendance.work_date <= end,
            )
            .order_by(Attendance.work_date)
        )
        return list(self._db.scalars(stmt).unique().all())

    def stats_for_range(self, start: date, end: date) -> list[tuple[Employee, int, int, int, int, int, float]]:
        stmt: Select = (
            select(
                Employee,
                func.count().filter(Attendance.status == "present").label("present_days"),
                func.count().filter(Attendance.status == "absent").label("absent_days"),
                func.count().filter(Attendance.status == "leave").label("leave_days"),
                func.count().filter(Attendance.status == "weekly_off").label("weekly_offs"),
                func.count().filter(Attendance.status == "holiday").label("holidays"),
                func.coalesce(func.sum(Attendance.work_duration_hours), 0).label("total_hours"),
            )
            .join(Attendance, Attendance.employee_id == Employee.id)
            .where(Attendance.work_date >= start, Attendance.work_date <= end)
            .group_by(Employee.id)
            .order_by(Employee.name)
        )
        return list(self._db.execute(stmt).all())
