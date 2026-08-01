from decimal import Decimal, ROUND_HALF_UP

def calculate_attendance_percentage(present_days: int | Decimal, absent_days: int | Decimal, leave_days: int | Decimal) -> float:
    total = float(present_days) + float(absent_days) + float(leave_days)
    if total == 0:
        return 0.0
    return round((float(present_days) / total) * 100.0, 1)
