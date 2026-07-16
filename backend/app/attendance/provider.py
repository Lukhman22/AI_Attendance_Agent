from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, time
from decimal import Decimal
from typing import BinaryIO


@dataclass(slots=True)
class RawAttendanceRow:
    employee_code: str
    employee_name: str
    department: str | None
    work_date: date
    check_in: time | None
    check_out: time | None
    work_duration_hours: Decimal | None
    break_duration_hours: Decimal | None
    overtime_hours: Decimal | None
    status: str | None


class AttendanceProvider(ABC):
    """Abstraction for biometric attendance sources (CSV/Excel today, API later)."""

    @abstractmethod
    def fetch_records(self) -> list[RawAttendanceRow]:
        raise NotImplementedError


class FileAttendanceProvider(AttendanceProvider):
    def __init__(self, file_obj: BinaryIO, filename: str) -> None:
        self._file_obj = file_obj
        self._filename = filename.lower()

    def fetch_records(self) -> list[RawAttendanceRow]:
        from .csv_reader import read_attendance_file

        return read_attendance_file(self._file_obj, self._filename)


class ApiAttendanceProvider(AttendanceProvider):
    """Placeholder-ready adapter for future biometric software API pull integrations."""

    def __init__(self, payload: list[dict]) -> None:
        self._payload = payload

    def fetch_records(self) -> list[RawAttendanceRow]:
        from .csv_reader import normalize_api_payload

        return normalize_api_payload(self._payload)
