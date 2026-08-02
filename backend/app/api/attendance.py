from datetime import date
from decimal import Decimal
from io import BytesIO

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.orm import Session

from ..dashboard.analytics import AnalyticsService
from ..dashboard.summary import DailySummaryService
from ..database.repositories import AttendanceRepository
from ..database.session import get_db
from ..schemas import AttendanceIngestResult, AttendanceStatsResponse, DailySummaryResponse, AttendanceUpdateReasonRequest, AttendanceRecordRead
from ..services.csv_service import CsvService
from fastapi import HTTPException
from .deps import (
    get_analytics_service,
    get_csv_service,
    get_daily_summary_service,
    get_min_working_hours,
)

router = APIRouter(prefix="/attendance", tags=["attendance"])


@router.post("/upload", response_model=AttendanceIngestResult)
async def upload_attendance(
    file: UploadFile = File(...),
    service: CsvService = Depends(get_csv_service),
) -> AttendanceIngestResult:
    content = await file.read()
    result = service.ingest_upload(BytesIO(content), file.filename or "attendance.csv")
    return AttendanceIngestResult(**result)


@router.post("/ingest-api", response_model=AttendanceIngestResult)
def ingest_api_attendance(
    payload: list[dict],
    service: CsvService = Depends(get_csv_service),
) -> AttendanceIngestResult:
    result = service.ingest_api_payload(payload)
    return AttendanceIngestResult(**result)


@router.get("/daily-summary", response_model=DailySummaryResponse)
def daily_summary(
    work_date: date = Query(...),
    service: DailySummaryService = Depends(get_daily_summary_service),
    min_hours: Decimal = Depends(get_min_working_hours),
) -> DailySummaryResponse:
    return DailySummaryResponse(**service.build(work_date, min_working_hours=min_hours))


@router.get("/stats", response_model=list[AttendanceStatsResponse])
def attendance_stats(
    start_date: date = Query(...),
    end_date: date = Query(...),
    service: AnalyticsService = Depends(get_analytics_service),
) -> list[AttendanceStatsResponse]:
    rows = service.attendance_stats(start_date, end_date)
    return [AttendanceStatsResponse(**row) for row in rows]


@router.get("/records")
def list_records(
    work_date: date = Query(...),
    db: Session = Depends(get_db),
):
    records = AttendanceRepository(db).list_for_date(work_date)
    return [
        {
            "id": r.id,
            "employee_code": r.employee.employee_code if r.employee else None,
            "employee_name": r.employee.name if r.employee else None,
            "work_date": r.work_date,
            "check_in": r.check_in,
            "check_out": r.check_out,
            "work_duration_hours": r.work_duration_hours,
            "break_duration_hours": r.break_duration_hours,
            "overtime_hours": r.overtime_hours,
            "status": r.status,
            "missing_hours": r.missing_hours,
            "daily_deduction": r.daily_deduction,
            "leave_reason": r.leave_reason,
        }
        for r in records
    ]

@router.put("/records/{record_id}/reason", response_model=AttendanceRecordRead)
def update_leave_reason(
    record_id: int,
    body: AttendanceUpdateReasonRequest,
    db: Session = Depends(get_db),
):
    from ..models.Attendance import Attendance
    record = db.query(Attendance).filter(Attendance.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Attendance record not found")
    
    record.leave_reason = body.leave_reason
    db.commit()
    db.refresh(record)
    return record

