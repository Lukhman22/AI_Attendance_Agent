from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ...models import IgnoredAttendance
from ...attendance.provider import RawAttendanceRow


class IgnoredAttendanceRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def upsert_unknown_employee(
        self,
        row: RawAttendanceRow,
        *,
        reason: str,
        source: str = "file",
    ) -> IgnoredAttendance:
        existing = self.get_by_code_and_date(row.employee_code, row.work_date)
        if existing is None:
            existing = IgnoredAttendance(
                employee_code=row.employee_code,
                employee_name=row.employee_name,
                work_date=row.work_date,
                reason=reason,
                source=source,
            )
            self._db.add(existing)
        existing.employee_name = row.employee_name
        existing.check_in = row.check_in
        existing.check_out = row.check_out
        existing.work_duration_hours = row.work_duration_hours
        existing.break_duration_hours = row.break_duration_hours
        existing.overtime_hours = row.overtime_hours
        existing.status = row.status
        existing.reason = reason
        existing.source = source
        self._db.flush()
        return existing

    def get_by_code_and_date(self, employee_code: str, work_date) -> IgnoredAttendance | None:
        stmt = select(IgnoredAttendance).where(
            IgnoredAttendance.employee_code == employee_code,
            IgnoredAttendance.work_date == work_date,
        )
        return self._db.scalar(stmt)

    def delete_for_employee_date(self, employee_code: str, work_date) -> None:
        self._db.execute(
            delete(IgnoredAttendance).where(
                IgnoredAttendance.employee_code == employee_code,
                IgnoredAttendance.work_date == work_date,
            )
        )

    def list_for_date(self, work_date) -> list[IgnoredAttendance]:
        stmt = (
            select(IgnoredAttendance)
            .where(IgnoredAttendance.work_date == work_date)
            .order_by(IgnoredAttendance.employee_code)
        )
        return list(self._db.scalars(stmt).all())

    def list_for_range(self, start, end) -> list[IgnoredAttendance]:
        stmt = (
            select(IgnoredAttendance)
            .where(IgnoredAttendance.work_date >= start, IgnoredAttendance.work_date <= end)
            .order_by(IgnoredAttendance.work_date, IgnoredAttendance.employee_code)
        )
        return list(self._db.scalars(stmt).all())

    @staticmethod
    def to_dict(record: IgnoredAttendance) -> dict:
        return {
            "employee_code": record.employee_code,
            "employee_name": record.employee_name,
            "work_date": record.work_date.isoformat() if record.work_date else None,
            "reason": record.reason,
            "status": record.status,
            "source": record.source,
        }
