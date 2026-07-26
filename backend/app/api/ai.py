from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Request
from sqlalchemy.orm import Session
import tempfile
import os

from ..ai.insights_service import HRInsightsService
from ..ai.assistant import HRAssistant
from ..schemas import (
    AiDailyInsightRead,
    AiMonthlyInsightRead,
    AiRecommendationRead,
    ExecutiveSummaryRead,
    SmartAlertRead,
    AiAskRequest,
    AiAskResponse,
)
from .deps import get_hr_insights_service, get_db

router = APIRouter(prefix="/ai", tags=["ai"])

@router.post("/transcribe")
async def transcribe_audio(request: Request, audio: UploadFile = File(...)):
    model = getattr(request.app.state, "whisper_model", None)
    if not model:
        try:
            from faster_whisper import WhisperModel
            import logging
            logger = logging.getLogger(__name__)
            logger.info("Lazy loading Whisper model...")
            model = WhisperModel("base", device="cpu", compute_type="int8")
            request.app.state.whisper_model = model
            logger.info("Whisper model loaded successfully.")
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"Whisper model failed to load: {e}")
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
            tmp_path = tmp.name
            content = await audio.read()
            tmp.write(content)
            
        segments, _ = model.transcribe(tmp_path, beam_size=5)
        text = " ".join([segment.text for segment in segments]).strip()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if 'tmp_path' in locals() and os.path.exists(tmp_path):
            os.remove(tmp_path)
            
    return {"text": text}

@router.post("/ask", response_model=AiAskResponse)
def ask_assistant(
    body: AiAskRequest,
    db: Session = Depends(get_db)
) -> AiAskResponse:
    assistant = HRAssistant(db)
    context_dict = body.context.model_dump() if body.context else {}
    result = assistant.ask(body.question, context=context_dict)
    return AiAskResponse(**result)


@router.get("/insights/daily", response_model=AiDailyInsightRead)
def daily_insights(
    work_date: date = Query(...),
    service: HRInsightsService = Depends(get_hr_insights_service),
) -> AiDailyInsightRead:
    insight = service.get_daily_insight(work_date)
    if insight is None:
        raise HTTPException(status_code=404, detail="No attendance data for this date")
    recommendations = service.get_recommendations(work_date)
    return AiDailyInsightRead.model_validate(insight).model_copy(
        update={
            "recommendations": [AiRecommendationRead.model_validate(r) for r in recommendations],
        }
    )


@router.get("/insights/monthly", response_model=AiMonthlyInsightRead)
def monthly_insights(
    year: int = Query(...),
    month: int = Query(..., ge=1, le=12),
    service: HRInsightsService = Depends(get_hr_insights_service),
) -> AiMonthlyInsightRead:
    insight = service.get_monthly_insight(year, month)
    if insight is None:
        raise HTTPException(status_code=404, detail="No monthly insight available")
    return AiMonthlyInsightRead.model_validate(insight)


@router.get("/executive-summary", response_model=ExecutiveSummaryRead)
def executive_summary(
    work_date: date = Query(...),
    service: HRInsightsService = Depends(get_hr_insights_service),
) -> ExecutiveSummaryRead:
    summary = service.get_executive_summary(work_date)
    if summary is None:
        raise HTTPException(status_code=404, detail="No executive summary available")
    recommendations = service.get_recommendations(work_date)
    alerts = service.get_alerts(work_date=work_date)
    return ExecutiveSummaryRead.model_validate(summary).model_copy(
        update={
            "recommendations": [AiRecommendationRead.model_validate(r) for r in recommendations],
            "alerts": [SmartAlertRead.model_validate(a) for a in alerts],
        }
    )
