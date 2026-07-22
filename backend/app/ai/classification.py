import re

class QueryClassificationEngine:
    @staticmethod
    def detect_who(q_lower: str) -> str:
        if "compare" in q_lower: return "COMPARISON"
        
        dataset_kws = ["how many employees exist", "departments", "department", "dataset"]
        if any(kw in q_lower for kw in dataset_kws): return "DATASET"
        
        org_kws = [
            "who", "all", "everyone", "anybody", "anyone", "company", "organization",
            "overall", "entire", "employees", "total", "combined", "aggregate",
            "team", "staff", "salary summary", "salary details", "payroll summary",
            "attendance summary", "executive summary", "hr summary", "absent details",
            "give company", "give this month's", "statistics", "average", "which employee"
        ]
        if any(re.search(rf"\b{kw}\b", q_lower) for kw in org_kws):
            return "ORGANIZATION"
            
        return "EMPLOYEE"

    @staticmethod
    def detect_what(q_lower: str) -> str:
        if "compare" in q_lower: return "comparison"
        if any(kw in q_lower for kw in ["executive summary", "hr insights", "general statistics"]): return "exec_summary"
        if any(kw in q_lower for kw in ["payroll summary", "salary summary", "summarize salary", "summarize payroll", "total salary", "total payroll", "overall payroll", "monthly payroll summary", "employee salary summary", "combined payroll", "aggregate payroll", "total employee salary", "executive payroll summary", "hr payroll summary", "salary details"]): return "payroll_summary"
        if any(kw in q_lower for kw in ["attendance summary", "attendance report", "attendance statistics", "daily summary"]): return "attendance_summary"
        if any(kw in q_lower for kw in ["average attendance", "average work hours", "average hours"]): return "average_stats"
        if any(kw in q_lower for kw in ["this month's summary", "monthly summary", "summarize month", "summarize this month", "monthly attendance"]): return "month_summary"
        if any(kw in q_lower for kw in ["highest salary deduction", "most deductions", "most deduction", "highest deduction", "highest deductions"]): return "highest_deduction"
        if any(kw in q_lower for kw in ["highest attendance", "best attendance", "perfect attendance"]): return "best_attendance"
        if any(kw in q_lower for kw in ["lowest attendance", "worst attendance", "worst attendance performer"]): return "worst_attendance"
        if any(kw in q_lower for kw in ["top performers", "best employee", "best performer"]): return "top_performers"
        if any(kw in q_lower for kw in ["bottom performers", "worst employee", "worst performer", "attention"]): return "attention_required"
        if "how many employees exist" in q_lower or "departments" in q_lower or "department" in q_lower: return "dataset_info"
        if "attendance history" in q_lower: return "attendance"
        if "missing checkout" in q_lower or "forgot checkout" in q_lower or "missing checkin" in q_lower or "forgot checkin" in q_lower or "missing punch" in q_lower: return "missing_punch"

        if "why" in q_lower: return "why"
        
        if "payroll" in q_lower or "salary" in q_lower or "deduct" in q_lower: return "payroll"
        if "absent" in q_lower or "absentees" in q_lower: return "absent"
        if "leave" in q_lower or "leaves" in q_lower: return "leave"
        if "late" in q_lower: return "late"
        if "early" in q_lower: return "early"
        if "hours" in q_lower or "work" in q_lower: return "hours"
        if "attendance" in q_lower or "present" in q_lower: return "attendance"
        if "why" in q_lower: return "why"
        
        return "unknown"

    @staticmethod
    def detect_time(q_lower: str):
        months = {
            "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6, 
            "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
            "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12
        }
        
        daily_kws = ["today", "this day", "that day", "on this day", "on this date", "yesterday", "daily"]
        monthly_kws = ["this month", "monthly", "during", "month", "last month", "entire month", "whole month"] + list(months.keys())
        
        has_daily = any(kw in q_lower for kw in daily_kws) or re.search(r"\b\d{1,2}/\d{1,2}/\d{4}\b", q_lower)
        has_monthly = any(kw in q_lower for kw in monthly_kws)
        
        found_month_num = None
        for m_name, m_num in months.items():
            if re.search(rf'\b{m_name}\b', q_lower):
                found_month_num = m_num
                break
                
        found_year = None
        year_match = re.search(r'\b(202\d)\b', q_lower)
        if year_match: found_year = int(year_match.group(1))
        
        offset_days = 0
        if "yesterday" in q_lower: offset_days = -1
        
        is_explicit = has_daily or has_monthly or (found_month_num is not None) or (found_year is not None)
        return is_explicit, has_daily, has_monthly, found_month_num, found_year, offset_days
