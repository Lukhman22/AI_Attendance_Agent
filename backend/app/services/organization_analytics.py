from datetime import date
import calendar
from typing import Any
import re
from sqlalchemy.orm import Session
from ..dashboard.analytics import AnalyticsService
from ..dashboard.summary import DailySummaryService
from ..ai.insights_service import HRInsightsService
from ..database.repositories import PayrollRepository, AttendanceRepository

class OrganizationAnalyticsService:
    def __init__(self, db: Session, settings: Any):
        self.db = db
        self.settings = settings
        self.payroll_repo = PayrollRepository(db)
        self.attendance_repo = AttendanceRepository(db)

    def process(self, intent: str, q_lower: str, target_date: date, year: int, month: int, granularity: str, employees_list: list) -> str:
        if intent == "exec_summary":
            svc = HRInsightsService(self.db, self.settings)
            summary = svc.get_executive_summary(target_date)
            if not summary: return f"No executive summary available for {target_date.isoformat()}."
            return summary.summary_text
            
        if intent == "month_summary":
            svc = HRInsightsService(self.db, self.settings)
            insight = svc.get_monthly_insight(year, month)
            if not insight: return f"No monthly summary available for {year}-{month:02d}."
            return f"Month Summary ({year}-{month:02d}):\nAttendance: {insight.company_attendance_percentage}%\nAvg Daily Hours: {insight.average_daily_hours}\nTotal Deductions: {insight.total_salary_deductions}"

        if intent == "attendance_summary":
            if granularity == "daily":
                svc = DailySummaryService(self.db)
                summary = svc.build(target_date)
                return f"Attendance Summary for {target_date.isoformat()}:\nPresent: {summary.get('employees_present', 0)}\nAbsent: {summary.get('employees_absent', 0)}"
            else:
                svc = AnalyticsService(self.db, self.settings)
                start_date = date(year, month, 1)
                end_date = date(year, month, calendar.monthrange(year, month)[1])
                stats = svc.attendance_stats(start_date, end_date)
                if not stats: return f"No attendance stats available for {year}-{month:02d}."
                total = len(stats)
                avg_att = sum(s["attendance_percentage"] for s in stats) / total
                highest = max(stats, key=lambda s: s["attendance_percentage"])
                lowest = min(stats, key=lambda s: s["attendance_percentage"])
                avg_hours = sum(s.get("average_hours", 0) for s in stats) / total
                total_hours = sum(s.get("total_worked_hours", 0) for s in stats)
                below_50 = len([s for s in stats if s["attendance_percentage"] < 50])
                above_90 = len([s for s in stats if s["attendance_percentage"] > 90])
                total_present_days = sum(s["present_days"] for s in stats)
                total_absent_days = sum(s["absent_days"] for s in stats)
                
                ans = f"Attendance Summary for {year}-{month:02d}:\n"
                ans += f"Total Employees: {total}\n"
                ans += f"Total Present Days: {total_present_days}\n"
                ans += f"Total Absent Days: {total_absent_days}\n"
                ans += f"Average Attendance: {avg_att:.1f}%\n"
                ans += f"Highest Attendance: {highest['employee_name']} ({highest['attendance_percentage']}%)\n"
                ans += f"Lowest Attendance: {lowest['employee_name']} ({lowest['attendance_percentage']}%)\n"
                ans += f"Average Daily Hours: {avg_hours:.1f}\n"
                ans += f"Total Worked Hours: {total_hours:.1f}\n"
                ans += f"Employees below 50%: {below_50}\n"
                ans += f"Employees above 90%: {above_90}"
                return ans

        if intent == "payroll_summary":
            payrolls = self.payroll_repo.list_for_period(year, month)
            if not payrolls: return f"No payroll data for {year}-{month:02d}."
            total_sal = sum(p.final_salary for p in payrolls)
            total_ded = sum(p.salary_deduction for p in payrolls)
            avg_sal = total_sal / len(payrolls) if payrolls else 0
            highest = max(payrolls, key=lambda p: p.final_salary)
            lowest = min(payrolls, key=lambda p: p.final_salary)
            highest_ded = max(payrolls, key=lambda p: p.salary_deduction)
            lowest_ded = min(payrolls, key=lambda p: p.salary_deduction)
            
            def get_name(pid):
                e = next((e for e in employees_list if e.id == pid), None)
                return e.name if e else "Unknown"

            ans = f"Payroll Summary for {year}-{month:02d}:\n"
            ans += f"Total Payroll Paid: {total_sal}\n"
            ans += f"Total Deductions: {total_ded}\n"
            ans += f"Average Salary: {avg_sal:.2f}\n"
            ans += f"Highest Salary: {get_name(highest.employee_id)} ({highest.final_salary})\n"
            ans += f"Lowest Salary: {get_name(lowest.employee_id)} ({lowest.final_salary})\n"
            ans += f"Highest Deduction: {get_name(highest_ded.employee_id)} ({highest_ded.salary_deduction})\n"
            ans += f"Lowest Deduction: {get_name(lowest_ded.employee_id)} ({lowest_ded.salary_deduction})"
            return ans

        # Statistics / specific queries
        if granularity == "daily":
            svc = DailySummaryService(self.db)
            summary = svc.build(target_date)
            present = summary.get("details", {}).get("present", [])
            absentees = summary.get("details", {}).get("absent", [])
            
            if intent in ["absent", "attendance"] and ("how many" in q_lower or "total" in q_lower or "count" in q_lower):
                if "present" in q_lower:
                    return f"Total employees present on {target_date.isoformat()}: {len(present)}."
                else:
                    return f"Total employees absent on {target_date.isoformat()}: {len(absentees)}."

            if intent == "absent" or (intent == "attendance" and "absent" in q_lower):
                if not absentees: return f"No one was absent on {target_date.isoformat()}."
                return f"Absent on {target_date.isoformat()}: " + ", ".join(a.get("employee_name") for a in absentees)
                
            if intent == "missing_punch":
                insight_svc = HRInsightsService(self.db, self.settings)
                daily_insight = insight_svc.get_daily_insight(target_date, generate=False)
                if daily_insight and "missing_punch" in daily_insight.payload:
                    names = [e["employee_name"] for e in daily_insight.payload["missing_punch"]]
                    if names: return f"Missing punches on {target_date.isoformat()}: {', '.join(names)}"
                return f"No one missed check-in/out on {target_date.isoformat()}."
                
            if intent == "hours" and "most" in q_lower:
                if not present: return "No data available."
                person = max(present, key=lambda x: x.get("work_duration_hours") or 0)
                return f"{person.get('employee_name')} worked the most with {person.get('work_duration_hours')} hours."
                
            if intent == "hours" and ("least" in q_lower or "below" in q_lower):
                if not present: return "No data available."
                person = min(present, key=lambda x: x.get("work_duration_hours") or 0)
                return f"{person.get('employee_name')} worked the least with {person.get('work_duration_hours')} hours."
                
            if intent in ["late", "early"]:
                insight_svc = HRInsightsService(self.db, self.settings)
                daily_insight = insight_svc.get_daily_insight(target_date, generate=False)
                if daily_insight:
                    if intent == "late" and "late_arrivals" in daily_insight.payload:
                        lates = [e["employee_name"] for e in daily_insight.payload["late_arrivals"]]
                        if lates: return f"Late arrivals on {target_date.isoformat()}: {', '.join(lates)}"
                        return f"No one was late on {target_date.isoformat()}."
                    if intent == "early" and "early_departures" in daily_insight.payload:
                        earlies = [e["employee_name"] for e in daily_insight.payload["early_departures"]]
                        if earlies: return f"Early departures on {target_date.isoformat()}: {', '.join(earlies)}"
                        return f"No one left early on {target_date.isoformat()}."
                return f"{intent.capitalize()} data not calculated yet for {target_date.isoformat()}."

        if granularity == "monthly" or intent in ["highest_deduction", "best_attendance", "worst_attendance", "top_performers", "attention_required", "leave", "absent", "payroll", "hours", "attendance"]:
            svc = AnalyticsService(self.db, self.settings)
            start_date = date(year, month, 1)
            end_date = date(year, month, calendar.monthrange(year, month)[1])
            stats = svc.attendance_stats(start_date, end_date)
            
            if not stats: return f"No analytics available for {year}-{month:02d}."

            if intent == "best_attendance" or intent == "top_performers" or ("highest" in q_lower and "attendance" in q_lower):
                person = max(stats, key=lambda s: s["attendance_percentage"])
                return f"{person['employee_name']} has the highest attendance ({person['attendance_percentage']}%)."
                
            if intent == "worst_attendance" or ("lowest" in q_lower and "attendance" in q_lower):
                person = min(stats, key=lambda s: s["attendance_percentage"])
                return f"{person['employee_name']} has the lowest attendance ({person['attendance_percentage']}%)."
                
            if intent == "hours" and ("most" in q_lower or "highest" in q_lower or "top" in q_lower):
                person = max(stats, key=lambda s: s.get("total_worked_hours", 0))
                return f"{person['employee_name']} worked the most hours ({person.get('total_worked_hours', 0):.1f})."
                
            if intent == "hours" and ("least" in q_lower or "lowest" in q_lower or "bottom" in q_lower):
                person = min(stats, key=lambda s: s.get("total_worked_hours", 0))
                return f"{person['employee_name']} worked the least hours ({person.get('total_worked_hours', 0):.1f})."
                
            if intent == "attention_required" or ("below" in q_lower and "attendance" in q_lower):
                match = re.search(r'below (\d+)%', q_lower)
                threshold = int(match.group(1)) if match else 50
                below = [s for s in stats if s["attendance_percentage"] < threshold]
                if not below: return f"No employees have attendance below {threshold}% for {year}-{month:02d}."
                names = ", ".join([s["employee_name"] for s in below])
                return f"Employees with attendance below {threshold}%: {names}"
                
            if "above" in q_lower and "attendance" in q_lower:
                match = re.search(r'above (\d+)%', q_lower)
                threshold = int(match.group(1)) if match else 90
                above = [s for s in stats if s["attendance_percentage"] > threshold]
                if not above: return f"No employees have attendance above {threshold}% for {year}-{month:02d}."
                names = ", ".join([s["employee_name"] for s in above])
                return f"Employees with attendance above {threshold}%: {names}"

            if intent == "highest_deduction" or (intent == "payroll" and "highest deduction" in q_lower):
                payrolls = self.payroll_repo.list_for_period(year, month)
                if payrolls:
                    highest = max(payrolls, key=lambda p: p.salary_deduction)
                    emp = next((e for e in employees_list if e.id == highest.employee_id), None)
                    if emp: return f"{emp.name} has the highest deduction of {highest.salary_deduction}."
                return f"No payroll deductions found for {year}-{month:02d}."
                
            if intent == "leave":
                person = max(stats, key=lambda s: s["leave_days"])
                return f"{person['employee_name']} has the most leaves ({person['leave_days']} days)."
                
            if intent == "absent" and ("most" in q_lower or "highest" in q_lower):
                person = max(stats, key=lambda s: s["absent_days"])
                return f"{person['employee_name']} has the most absences ({person['absent_days']} days)."

            if "average attendance" in q_lower:
                avg = sum(s["attendance_percentage"] for s in stats) / len(stats)
                return f"Average company attendance for {year}-{month:02d} is {avg:.1f}%."
                
            if "average working hours" in q_lower or "average hours" in q_lower:
                avg = sum(s.get("average_hours", 0) for s in stats) / len(stats)
                return f"Average company working hours for {year}-{month:02d} is {avg:.1f} per day."
                
            if intent == "absent" and "count" in q_lower:
                total_absent_days = sum(s["absent_days"] for s in stats)
                return f"Total absent days in {year}-{month:02d}: {total_absent_days}"
                
            if intent in ["attendance", "payroll", "leave", "hours"]:
                return "Organization query processed. Try asking for a specific summary or statistic (e.g. 'Attendance Summary', 'Who worked the most hours?')."

        return "Organization analytics query processed. Please be more specific about the statistic you want."
