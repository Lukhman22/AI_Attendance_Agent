"""Parse biometric duration / time strings into decimal hours."""

from __future__ import annotations

import math
import re
from datetime import datetime, time, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

import pandas as pd


_DURATION_RE = re.compile(
    r"^\s*(?:(?P<hours>\d+)\s*[hH:])?\s*(?:(?P<minutes>\d+)\s*[mM]?)?\s*$"
)
_DECIMAL_RE = re.compile(r"^\s*\d+(?:[.,]\d+)?\s*$")
_HHMM_RE = re.compile(r"^\s*(?P<h>\d{1,2}):(?P<m>\d{2})(?::(?P<s>\d{2}))?\s*$")
_HMS_TEXT_RE = re.compile(
    r"^\s*(?P<h>\d+)\s*(?:h|hr|hrs|hour|hours)?\s*"
    r"(?:(?P<m>\d+)\s*(?:m|min|mins|minutes)?)?\s*$",
    re.IGNORECASE,
)


def hours_to_decimal(value: Decimal | float | int | str | None) -> Decimal | None:
    if value is None or value == "":
        return None
    if isinstance(value, Decimal):
        return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if isinstance(value, bool):
        return None
    if isinstance(value, timedelta):
        return (Decimal(str(value.total_seconds())) / Decimal(3600)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
    if isinstance(value, time):
        # Excel duration typed as time-of-day means hours:minutes worked
        return (
            Decimal(value.hour)
            + (Decimal(value.minute) / Decimal(60))
            + (Decimal(value.second) / Decimal(3600))
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if isinstance(value, datetime):
        return hours_to_decimal(value.time())
    if isinstance(value, pd.Timestamp):
        return hours_to_decimal(value.to_pydatetime())
    if isinstance(value, (int, float)):
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            return None
        return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    raw = str(value).strip()
    if not raw or raw.lower() in {"nan", "none", "null", "-", "n/a", "na", "--:--", "--"}:
        return None

    if _DECIMAL_RE.match(raw) and ":" not in raw:
        normalized = raw.replace(",", ".")
        try:
            number = Decimal(normalized)
        except InvalidOperation:
            return None
        return number.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    match = _HHMM_RE.match(raw)
    if match:
        hours = int(match.group("h"))
        minutes = int(match.group("m"))
        seconds = int(match.group("s") or 0)
        total = Decimal(hours) + (Decimal(minutes) / Decimal(60)) + (Decimal(seconds) / Decimal(3600))
        return total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    match = _HMS_TEXT_RE.match(raw)
    if match and (match.group("h") or match.group("m")):
        hours = int(match.group("h") or 0)
        minutes = int(match.group("m") or 0)
        total = Decimal(hours) + (Decimal(minutes) / Decimal(60))
        return total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    match = _DURATION_RE.match(raw)
    if match and (match.group("hours") or match.group("minutes")):
        hours = int(match.group("hours") or 0)
        minutes = int(match.group("minutes") or 0)
        total = Decimal(hours) + (Decimal(minutes) / Decimal(60))
        return total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    return None


def parse_time(value: str | time | datetime | None) -> time | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, time):
        return value
    if isinstance(value, datetime):
        return value.time().replace(microsecond=0)
    if isinstance(value, pd.Timestamp):
        if pd.isna(value):
            return None
        return value.to_pydatetime().time().replace(microsecond=0)
    if isinstance(value, (int, float)):
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            return None
        # Excel time-of-day as fraction of day
        if 0 <= float(value) < 1:
            total_seconds = int(round(float(value) * 24 * 3600))
            hours, rem = divmod(total_seconds, 3600)
            minutes, seconds = divmod(rem, 60)
            return time(hour=hours % 24, minute=minutes, second=seconds)
        return None

    raw = str(value).strip()
    if not raw or raw.lower() in {"nan", "none", "null", "-", "n/a", "na", "--:--", "--"}:
        return None

    # Excel/pandas may stringify timestamps
    if " " in raw and (":" in raw):
        parsed = pd.to_datetime(raw, errors="coerce", dayfirst=True)
        if not pd.isna(parsed):
            return parsed.to_pydatetime().time().replace(microsecond=0)

    for fmt in ("%H:%M:%S", "%H:%M", "%I:%M %p", "%I:%M:%S %p", "%H.%M", "%H.%M.%S"):
        try:
            return datetime.strptime(raw, fmt).time()
        except ValueError:
            continue
    return None


def hours_between(check_in: time | None, check_out: time | None) -> Decimal | None:
    if check_in is None or check_out is None:
        return None
    start = datetime.combine(datetime.today().date(), check_in)
    end = datetime.combine(datetime.today().date(), check_out)
    if end < start:
        # Overnight shift support
        end = end + timedelta(days=1)
    seconds = Decimal((end - start).total_seconds())
    return (seconds / Decimal(3600)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _money_decimal(value: Decimal | int | float | str) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def quantize_money(value: Decimal | int | float | str) -> Decimal:
    return _money_decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
