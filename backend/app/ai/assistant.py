import json
from datetime import date, timedelta
import re
from sqlalchemy.orm import Session

from ..config import settings
from ..database.repositories import EmployeeRepository, PayrollRepository, AttendanceRepository
from ..dashboard.summary import DailySummaryService
from ..dashboard.analytics import AnalyticsService
from .insights_service import HRInsightsService
import calendar

from .classification import QueryClassificationEngine

class EmployeeEngine:
    @staticmethod
    def resolve(q_lower: str, employees: list) -> tuple:
        q_clean = re.sub(r'[^\w\s]', '', q_lower).strip()
        q_words = set(q_clean.split())
        
        mentioned_emps = []
        for e in employees:
            e_name_clean = re.sub(r'[^\w\s]', '', e.name.lower()).strip()
            e_words = e_name_clean.split()
            
            if e_name_clean in q_clean:
                mentioned_emps.append((0, e, "Exact Name Match"))
                continue
            if e_words and e_words[0] in q_words:
                mentioned_emps.append((1, e, "First Name Match"))
                continue
            if len(e_words) > 1 and e_words[-1] in q_words:
                mentioned_emps.append((2, e, "Last Name Match"))
                continue
                
            matched = False
            for w in q_words:
                if len(w) >= 4:
                    for ew in e_words:
                        if len(ew) >= 4 and (w in ew or ew in w):
                            mentioned_emps.append((3, e, "Partial/Fuzzy Match"))
                            matched = True
                            break
                if matched: break
                    
        mentioned_emps.sort(key=lambda x: x[0])
        
        unique_emps = []
        seen_ids = set()
        for _, emp, method in mentioned_emps:
            if emp.id not in seen_ids:
                unique_emps.append((emp, method))
                seen_ids.add(emp.id)
                
        return unique_emps


class HRAssistant:
    def __init__(self, db: Session):
        self.db = db
        self.employee_repo = EmployeeRepository(db)
        self.payroll_repo = PayrollRepository(db)
        self.attendance_repo = AttendanceRepository(db)

    def ask(self, question: str, context: dict | None = None) -> dict:
        q_lower = question.lower()
        context = context or {}
        employees_list = self.employee_repo.list_all()
        
        # ----------------------------------------------------
        # 1. Pipeline Execution
        # ----------------------------------------------------
        explicit_intent = QueryClassificationEngine.detect_what(q_lower)
        unique_emps = EmployeeEngine.resolve(q_lower, employees_list)
        
        # Date processing
        is_date_explicit, has_daily, has_monthly, found_month_num, found_year, offset_days = QueryClassificationEngine.detect_time(q_lower)
        
        dash_date = context.get("work_date")
        if isinstance(dash_date, str): base_date = date.fromisoformat(dash_date)
        elif isinstance(dash_date, date): base_date = dash_date
        else: base_date = date.today()
            
        dash_year = context.get("year") or base_date.year
        dash_month = context.get("month") or base_date.month
        
        if is_date_explicit:
            target_date = base_date + timedelta(days=offset_days)
            year = found_year or dash_year
            month = found_month_num or dash_month
            if has_monthly: granularity = "monthly"
            elif has_daily: granularity = "daily"
            else: granularity = context.get("granularity", "monthly")
        else:
            # Inherit entirely if not explicit
            hist_date_str = context.get("hist_date")
            target_date = date.fromisoformat(hist_date_str) if hist_date_str else base_date
            year = context.get("hist_year") or dash_year
            month = context.get("hist_month") or dash_month
            granularity = context.get("granularity", "monthly")
            
        # Intent processing
        is_intent_explicit = (explicit_intent != "unknown")
        
        # ----------------------------------------------------
        # 2. Clarification Engine & Conversation Continuity
        # ----------------------------------------------------
        intent = explicit_intent
        scope = QueryClassificationEngine.detect_who(q_lower)
        
        # If no explicit intent was provided, we inherit the previous intent if possible
        if not is_intent_explicit:
            if context.get("pending_clarification") == "Yes":
                intent = context.get("pending_intent", "unknown")
                scope = context.get("pending_scope", "EMPLOYEE")
            else:
                intent = context.get("intent", "unknown")
                # Infer WHO dimension independently, but if we're falling back to a pending intent, we might want to preserve the previous WHO if no new one was given.
                # However, the strict rule is: Each dimension must be determined independently.
                # But conversation memory MUST fill in missing dimensions.
                # If WHO was ORGANIZATION, we keep it ORGANIZATION if the user just changed the date.
                if scope == "EMPLOYEE" and not unique_emps:
                    scope = context.get("scope", "EMPLOYEE")
                
        # Determine Employee Context
        target_emp = None
        compare_emp = None
        
        # Clear pending clarification flag since we are processing it
        context.pop("pending_clarification", None)
        context.pop("pending_intent", None)
        context.pop("pending_scope", None)

        if scope == "ORGANIZATION" or scope == "DATASET":
            # Strict isolation. Never reuse employee.
            context.pop("employee_id", None)
            context.pop("compare_employee_id", None)
        elif scope == "COMPARISON":
            if len(unique_emps) >= 2:
                target_emp = unique_emps[0][0]
                compare_emp = unique_emps[1][0]
            elif len(unique_emps) == 1:
                target_emp = unique_emps[0][0]
                last_id = context.get("employee_id")
                if last_id and last_id != target_emp.id:
                    compare_emp = next((e for e in employees_list if e.id == last_id), None)
            else:
                last_id = context.get("employee_id")
                last_comp = context.get("compare_employee_id")
                if last_id: target_emp = next((e for e in employees_list if e.id == last_id), None)
                if last_comp: compare_emp = next((e for e in employees_list if e.id == last_comp), None)
        elif scope == "EMPLOYEE":
            if len(unique_emps) >= 1:
                target_emp = unique_emps[0][0] # explicit swap
            else:
                # Part 3: Pronoun Continuity. Even without pronouns, if there's no new employee, we keep the old one!
                last_id = context.get("employee_id")
                if last_id:
                    target_emp = next((e for e in employees_list if e.id == last_id), None)
                    
        # Verification & Pending State Generation
        if scope == "EMPLOYEE" and not target_emp:
            context["pending_clarification"] = "Yes"
            context["pending_intent"] = intent
            context["pending_scope"] = scope
            return {
                "question": question,
                "answer": "Which employee would you like me to look up?",
                "references": {},
                "context": context
            }
            
        if scope == "COMPARISON" and not (target_emp and compare_emp):
            context["pending_clarification"] = "Yes"
            context["pending_intent"] = intent
            context["pending_scope"] = scope
            return {
                "question": question,
                "answer": "Please specify two employees to compare.",
                "references": {},
                "context": context
            }

        # ----------------------------------------------------
        # 3. Update Conversation State
        # ----------------------------------------------------
        if target_emp: context["employee_id"] = target_emp.id
        if compare_emp: context["compare_employee_id"] = compare_emp.id
        if intent != "unknown": context["intent"] = intent
        context["scope"] = scope
        context["granularity"] = granularity
        context["hist_date"] = target_date.isoformat()
        context["hist_year"] = year
        context["hist_month"] = month

        def build_response(ans: str, refs: dict = None, service: str = "Unknown"):
            if getattr(settings, 'debug', False):
                print(f"--- [DEBUG ROUTING] ---")
                print(f"Intent : {intent.upper()}")
                print(f"Scope : {scope}")
                print(f"Employee : {target_emp.name if target_emp else 'None'}")
                print(f"Date : {target_date.isoformat()} (Granularity: {granularity})")
                print(f"Service : {service}")
                print(f"-----------------------")
            return {
                "question": question,
                "answer": ans,
                "references": refs or {},
                "context": context
            }

        # ----------------------------------------------------
        # 4. Service Router
        # ----------------------------------------------------
        
        if scope == "DATASET":
            if intent == "dataset_info":
                if "department" in q_lower:
                    depts = set(e.department for e in employees_list if getattr(e, 'department', None))
                    return build_response(f"Departments: {', '.join(depts) if depts else 'Not configured.'}", service="Dataset Service")
                return build_response(f"There are {len(employees_list)} employees currently in the system.", service="Dataset Service")
            
            if intent == "average_stats":
                svc = AnalyticsService(self.db, settings)
                start_date = date(year, month, 1)
                end_date = date(year, month, calendar.monthrange(year, month)[1])
                stats = svc.attendance_stats(start_date, end_date)
                if stats:
                    avg_att = sum(s["attendance_percentage"] for s in stats) / len(stats)
                    return build_response(f"Average company attendance for {year}-{month:02d} is {avg_att:.1f}%.", service="Analytics Service")
                return build_response(f"No attendance stats available for {year}-{month:02d}.", service="Analytics Service")
                
        if scope == "ORGANIZATION":
            from ..services.organization_analytics import OrganizationAnalyticsService
            svc = OrganizationAnalyticsService(self.db, settings)
            ans = svc.process(intent, q_lower, target_date, year, month, granularity, employees_list)
            return build_response(ans, {"date": target_date.isoformat(), "year": year, "month": month}, service="Organization Analytics Service")

        if scope == "COMPARISON":
            if granularity == "daily":
                rec1 = self.attendance_repo.get_by_employee_and_date(target_emp.id, target_date)
                rec2 = self.attendance_repo.get_by_employee_and_date(compare_emp.id, target_date)
                if not rec1 or not rec2: return build_response(f"Missing records for {target_date.isoformat()}.", service="Attendance Service")
                
                if intent == "hours":
                    h1, h2 = rec1.work_duration_hours or 0, rec2.work_duration_hours or 0
                    if h1 > h2: ans = f"{target_emp.name} worked more ({h1} hrs) than {compare_emp.name} ({h2} hrs)."
                    elif h2 > h1: ans = f"{compare_emp.name} worked more ({h2} hrs) than {target_emp.name} ({h1} hrs)."
                    else: ans = f"Both worked the same ({h1} hrs)."
                    return build_response(ans, service="Attendance Service")
                elif intent == "attendance":
                    return build_response(f"On {target_date.isoformat()}, {target_emp.name} was {rec1.status} while {compare_emp.name} was {rec2.status}.", service="Attendance Service")
            else:
                svc = AnalyticsService(self.db, settings)
                start_date = date(year, month, 1)
                end_date = date(year, month, calendar.monthrange(year, month)[1])
                stats = svc.attendance_stats(start_date, end_date)
                
                s1 = next((s for s in stats if s["employee_id"] == target_emp.id), None)
                s2 = next((s for s in stats if s["employee_id"] == compare_emp.id), None)
                if not s1 or not s2: return build_response("Missing data for comparison.", service="Analytics Service")
                
                if intent == "hours":
                    h1, h2 = s1["total_worked_hours"], s2["total_worked_hours"]
                    if h1 > h2: ans = f"{target_emp.name} worked more ({h1} hrs) than {compare_emp.name} ({h2} hrs)."
                    elif h2 > h1: ans = f"{compare_emp.name} worked more ({h2} hrs) than {target_emp.name} ({h1} hrs)."
                    else: ans = f"Both worked the same ({h1} hrs)."
                    return build_response(ans, service="Attendance Service")
                elif intent == "leave":
                    l1, l2 = s1["leave_days"], s2["leave_days"]
                    if l1 > l2: ans = f"{target_emp.name} has more leaves ({l1}) than {compare_emp.name} ({l2})."
                    elif l2 > l1: ans = f"{compare_emp.name} has more leaves ({l2}) than {target_emp.name} ({l1})."
                    else: ans = f"Both have {l1} leaves."
                    return build_response(ans, service="Analytics Service")
                elif intent == "attendance":
                    a1, a2 = s1["attendance_percentage"], s2["attendance_percentage"]
                    if a1 > a2: ans = f"{target_emp.name} has better attendance ({a1}%) than {compare_emp.name} ({a2}%)."
                    elif a2 > a1: ans = f"{compare_emp.name} has better attendance ({a2}%) than {target_emp.name} ({a1}%)."
                    else: ans = f"Both have {a1}% attendance."
                    return build_response(ans, service="Analytics Service")
                elif intent == "payroll":
                    p1 = self.payroll_repo.get_for_employee_period(target_emp.id, year, month)
                    p2 = self.payroll_repo.get_for_employee_period(compare_emp.id, year, month)
                    if not p1 or not p2: return build_response("Missing payroll data for comparison.", service="Payroll Service")
                    ans = f"Payroll Comparison:\n- {target_emp.name}: Salary {p1.final_salary}, Deductions {p1.salary_deduction}\n- {compare_emp.name}: Salary {p2.final_salary}, Deductions {p2.salary_deduction}"
                    return build_response(ans, service="Payroll Service")
            return build_response(f"Comparing {target_emp.name} and {compare_emp.name}.", service="Comparison Service")

        if scope == "EMPLOYEE":
            if intent == "payroll" or intent == "why":
                payroll = self.payroll_repo.get_for_employee_period(target_emp.id, year, month)
                if not payroll: return build_response(f"Payroll not generated for {target_emp.name} in {year}-{month:02d}.", service="Payroll Service")
                
                start_date = date(year, month, 1)
                end_date = date(year, month, calendar.monthrange(year, month)[1])
                records = self.attendance_repo.list_for_employee_range(target_emp.id, start_date, end_date)
                
                reasons = []
                for r in records:
                    if r.status != "present" or r.missing_hours > 0 or r.daily_deduction > 0:
                        reason = f"Date: {r.work_date.isoformat()} - Status: {r.status}"
                        if r.missing_hours > 0: reason += f", Missing Hours: {r.missing_hours}"
                        if r.daily_deduction > 0: reason += f", Deduction: {r.daily_deduction}"
                        reasons.append(reason)
                        
                if intent == "why":
                    if not reasons: return build_response(f"No specific deductions for {target_emp.name} in {year}-{month:02d}.", service="Payroll Service")
                    return build_response(f"Salary deduction reasons for {target_emp.name}:\n* " + "\n* ".join(reasons), service="Payroll Service")
                        
                ans = f"Payroll details for {target_emp.name} ({year}-{month:02d}):\n- Salary: {payroll.final_salary}\n- Deductions: {payroll.salary_deduction}\n- Present: {payroll.present_days}\n- Absent: {payroll.absent_days}\n"
                if reasons: ans += "\nDeduction Reasons:\n* " + "\n* ".join(reasons)
                return build_response(ans, {"employee_id": target_emp.id, "payroll_month": f"{year}-{month:02d}"}, service="Payroll Service")

            if intent in ["absent", "leave", "hours", "attendance", "missing_punch", "late", "early", "attendance_summary"]:
                if granularity == "daily":
                    record = self.attendance_repo.get_by_employee_and_date(target_emp.id, target_date)
                    if not record: return build_response(f"No attendance record exists for {target_date.isoformat()}.", service="Attendance Service")
                    
                    if intent == "hours": return build_response(f"{target_emp.name} worked {record.work_duration_hours or 0} hours on {target_date.isoformat()}.", {"employee_id": target_emp.id}, service="Attendance Service")
                    if intent == "attendance" or intent == "attendance_summary": return build_response(f"{target_emp.name} was {record.status} on {target_date.isoformat()}.", {"employee_id": target_emp.id}, service="Attendance Service")
                    if intent in ["absent", "leave"]:
                        ans = "Yes" if record.status == "absent" else "No"
                        return build_response(f"{ans}, {target_emp.name} was {record.status} on {target_date.isoformat()}.", {"employee_id": target_emp.id}, service="Attendance Service")
                    if intent in ["late", "early", "missing_punch"]:
                        ans = f"{target_emp.name}'s record indicates status: {record.status}."
                        if record.missing_hours > 0: ans += f" Missing hours: {record.missing_hours}."
                        return build_response(ans, service="Attendance Service")
                else:
                    svc = AnalyticsService(self.db, settings)
                    start_date = date(year, month, 1)
                    end_date = date(year, month, calendar.monthrange(year, month)[1])
                    stats = svc.attendance_stats(start_date, end_date)
                    stat = next((s for s in stats if s["employee_id"] == target_emp.id), None)
                    
                    if not stat: return build_response(f"No data for {target_emp.name} in {year}-{month:02d}.", service="Analytics Service")
                        
                    if intent == "absent": return build_response(f"{target_emp.name} was absent for {stat['absent_days']} days in {year}-{month:02d}.", {"employee_id": target_emp.id}, service="Analytics Service")
                    if intent == "leave": return build_response(f"{target_emp.name} took {stat['leave_days']} leave days in {year}-{month:02d}.", {"employee_id": target_emp.id}, service="Analytics Service")
                    if intent == "hours": return build_response(f"{target_emp.name} worked a total of {stat['total_worked_hours']} hours in {year}-{month:02d}.", {"employee_id": target_emp.id}, service="Analytics Service")
                    if intent == "attendance" or intent == "attendance_summary": return build_response(f"{target_emp.name} has an attendance of {stat['attendance_percentage']}% in {year}-{month:02d} ({stat['present_days']} present, {stat['absent_days']} absent).", {"employee_id": target_emp.id}, service="Analytics Service")

            # Part 6: If enough information exists, answer it. If not, default to showing their attendance summary instead of saying "Employee selected".
            # By this point, intent was unknown but we have the target_emp. Let's just output their attendance summary for the requested date.
            if granularity == "daily":
                record = self.attendance_repo.get_by_employee_and_date(target_emp.id, target_date)
                if not record: return build_response(f"No records found for {target_emp.name} on {target_date.isoformat()}.", service="General HR Service")
                return build_response(f"{target_emp.name} was {record.status} on {target_date.isoformat()}.", {"employee_id": target_emp.id}, service="General HR Service")
            else:
                svc = AnalyticsService(self.db, settings)
                start_date = date(year, month, 1)
                end_date = date(year, month, calendar.monthrange(year, month)[1])
                stats = svc.attendance_stats(start_date, end_date)
                stat = next((s for s in stats if s["employee_id"] == target_emp.id), None)
                if not stat: return build_response(f"No data for {target_emp.name} in {year}-{month:02d}.", service="General HR Service")
                return build_response(f"{target_emp.name} has {stat['attendance_percentage']}% attendance in {year}-{month:02d}.", {"employee_id": target_emp.id}, service="General HR Service")

        return build_response("I could not determine a specific response for your query. Please rephrase.")
