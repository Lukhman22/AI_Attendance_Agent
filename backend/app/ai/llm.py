import json
import logging
from typing import Any
from openai import OpenAI

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self.api_key = api_key
        self.model = model
        self.client = OpenAI(api_key=api_key) if api_key else None

    def _call(self, system_prompt: str, user_prompt: str, response_format: dict | None = None) -> Any:
        if not self.client:
            return None
        
        try:
            kwargs = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.0,
            }
            if response_format:
                kwargs["response_format"] = {"type": "json_object"}
            
            response = self.client.chat.completions.create(**kwargs)
            content = response.choices[0].message.content
            
            if response_format:
                return json.loads(content)
            return content
        except Exception as e:
            logger.exception("LLM call failed")
            return None

    def detect_intent(self, question: str) -> dict:
        system = """You are an HR intent classification engine.
Analyze the user's question and output a JSON object with the following keys:
- scope: "ORGANIZATION" (company-wide, department, or statistics), "EMPLOYEE" (specific employee), "COMPARISON" (comparing employees), "DATASET" (general system info like 'how many employees exist')
- intent: Determine the action. Common intents:
   - "attendance_summary" (e.g. give this month's attendance details, attendance report, attendance analytics, attendance dashboard, overall attendance percentage)
   - "payroll_summary" (payroll details, total salary)
   - "exec_summary" (executive summary)
   - "average_stats" (average attendance, average hours)
   - "best_attendance", "worst_attendance", "highest_deduction", "attention_required", "top_performers", "dataset_info", "hours", "late", "early", "missing_punch", "absent", "leave", "payroll", "why" (salary deduction reason), "attendance".
- time_period: object with "has_daily": bool, "has_monthly": bool, "month": int or null, "year": int or null, "offset_days": int (e.g. -1 for yesterday, 0 for today). Set is_explicit=true if explicitly stated.

Output ONLY valid JSON. Example: {"scope": "ORGANIZATION", "intent": "attendance_summary", "time": {"has_daily": false, "has_monthly": true, "month": 4, "year": 2026, "offset_days": 0, "is_explicit": true}}"""

        res = self._call(system, question, response_format=True)
        return res or {}

    def generate_response(self, question: str, data: str) -> str:
        system = """You are an intelligent HR Manager's assistant.
You have been provided with structured data collected from the backend HR system.
Your job is to answer the user's question using ONLY the provided data.
You must adhere strictly to these HR Rules:
1. One working day = 8 hours.
2. Working MORE than 8 hours does NOT increase salary.
3. Working LESS than 8 hours results in salary deduction.
4. Absent days deduct salary.
5. Weekly Offs and Holidays do NOT reduce salary.
6. Attendance Annotations (approved leaves, official duty) are respected.

When answering WHY a salary was deducted, explicitly breakdown:
- Base Salary
- Absent Days
- Underworked Days
- Overtime Days (mention it does not increase salary)
- Attendance %
- Total Deduction
- Final Salary

When providing Organization Analytics (Rich Attendance Summary / Rich Payroll Summary), use a clean, professional, readable format (bullet points, short summaries).
Do NOT invent facts. If the data is missing, say so."""
        
        return self._call(system, f"User Question: {question}\n\nStructured Data:\n{data}") or "I could not generate a response based on the data."

