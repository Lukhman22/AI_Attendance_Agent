from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from ..schemas import ReportGenerateRequest, ReportGenerateResponse
from ..services.report_service import ReportService
from .deps import get_report_service

router = APIRouter(prefix="/reports", tags=["reports"])

_MEDIA_TYPES = {
    ".csv": "text/csv",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".pdf": "application/pdf",
}


@router.post("/generate", response_model=ReportGenerateResponse)
def generate_report(
    body: ReportGenerateRequest,
    service: ReportService = Depends(get_report_service),
) -> ReportGenerateResponse:
    result = service.generate(
        report_type=body.report_type,
        fmt=body.format,
        work_date=body.work_date,
        year=body.year,
        month=body.month,
        start_date=body.start_date,
        end_date=body.end_date,
    )
    return ReportGenerateResponse(**result)


@router.get("/download/{filename}")
def download_report(
    filename: str,
    service: ReportService = Depends(get_report_service),
) -> FileResponse:
    path = service.resolve_download_path(filename)
    media_type = _MEDIA_TYPES.get(path.suffix.lower(), "application/octet-stream")
    return FileResponse(path, filename=path.name, media_type=media_type)
