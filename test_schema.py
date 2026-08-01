import asyncio
from pydantic import BaseModel, Field
from typing import Any

class DailySummaryResponse(BaseModel):
    work_date: str
    details: dict[str, Any] = Field(default_factory=dict)

print(DailySummaryResponse(work_date="today").model_dump_json())
