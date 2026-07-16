from __future__ import annotations

import calendar
import logging
import re
from datetime import date, datetime
from io import BytesIO
from pathlib import Path
from typing import Any, BinaryIO

import pandas as pd

from ..core.exceptions import ApplicationError
from ..utils import hours_to_decimal, parse_time
from .provider import RawAttendanceRow

logger = logging.getLogger(__name__)

COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "employee_code": (
        "employee id",
        "employee_id",
        "emp id",
        "emp_id",
        "empid",
        "emp code",
        "employee code",
        "badge",
        "badge id",
        "biometric id",
        "userid",
        "user id",
        "code",
        "id",
    ),
    "employee_name": (
        "employee name",
        "emp name",
        "staff name",
        "name",
        "employee",
        "fullname",
    ),
    "department": ("department", "dept", "section", "division"),
    "work_date": (
        "date",
        "work date",
        "attendance date",
        "work_date",
        "punch date",
        "att date",
        "day",
    ),
    "check_in": (
        "check-in time",
        "check in time",
        "check in",
        "check_in",
        "in time",
        "intime",
        "clock in",
        "first in",
        "punch in",
        "time in",
    ),
    "check_out": (
        "check-out time",
        "check out time",
        "check out",
        "check_out",
        "out time",
        "outtime",
        "clock out",
        "last out",
        "punch out",
        "time out",
    ),
    "work_duration": (
        "work duration",
        "work_duration",
        "worked hours",
        "work hours",
        "total hours",
        "total work hours",
        "hours worked",
        "duration",
        "worked time",
        "net hours",
    ),
    "break_duration": (
        "break duration",
        "break_duration",
        "break hours",
        "break time",
        "break",
        "lunch",
    ),
    "overtime": ("overtime", "ot", "over time", "ot hours", "overtime hours"),
    "status": (
        "attendance status",
        "att status",
        "status",
        "attendance",
        "day status",
        "remark",
        "remarks",
    ),
}

_MONTHLY_ROW_LABELS: dict[str, str] = {
    "in": "in",
    "out": "out",
    "work": "work",
    "break": "break",
    "ot": "ot",
    "overtime": "ot",
    "status": "status",
}

_MONTH_NAMES = {
    "january": 1,
    "jan": 1,
    "february": 2,
    "feb": 2,
    "march": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "may": 5,
    "june": 6,
    "jun": 6,
    "july": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sep": 9,
    "sept": 9,
    "october": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "december": 12,
    "dec": 12,
}

_META_LABELS = {
    "employee code": "employee_code",
    "emp code": "employee_code",
    "empcode": "employee_code",
    "emp id": "employee_code",
    "employee id": "employee_code",
    "employee name": "employee_name",
    "emp name": "employee_name",
    "staff name": "employee_name",
    "name": "employee_name",
    "department": "department",
    "dept": "department",
    "dept. name": "department",
    "dept name": "department",
    "present": "present",
    "wo": "wo",
    "weekly off": "wo",
    "hl": "hl",
    "holiday": "hl",
    "lv": "lv",
    "leave": "lv",
    "absent": "absent",
    "total work+ot": "total_work_ot",
    "total work + ot": "total_work_ot",
    "tot. work+ot": "total_work_ot",
    "tot work+ot": "total_work_ot",
    "tot.work+ot": "total_work_ot",
    "total workot": "total_work_ot",
    "total ot": "total_ot",
}

_WEEKDAY_TOKENS = {
    "mon",
    "tue",
    "wed",
    "thu",
    "fri",
    "sat",
    "sun",
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
}


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename_map: dict[str, str] = {}
    lowered = {str(col).strip().lower(): col for col in df.columns}
    for canonical, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in lowered:
                rename_map[lowered[alias]] = canonical
                break
    return df.rename(columns=rename_map)


def _looks_like_header_row(values: list[Any]) -> bool:
    joined = " ".join(str(v).strip().lower() for v in values if v is not None and str(v).strip())
    signals = ("employee", "date", "check", "in time", "out time", "duration", "status", "name")
    return sum(1 for token in signals if token in joined) >= 2


def _detect_header_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Company biometric exports often include a title/banner row above the real header."""
    if _looks_like_header_row([str(c) for c in df.columns]):
        return df

    scan_limit = min(10, len(df))
    for idx in range(scan_limit):
        row_values = df.iloc[idx].tolist()
        if _looks_like_header_row(row_values):
            headers = [
                str(v).strip() if v is not None and not pd.isna(v) else f"col_{i}"
                for i, v in enumerate(row_values)
            ]
            body = df.iloc[idx + 1 :].copy()
            body.columns = headers
            body = body.dropna(how="all")
            return body.reset_index(drop=True)
    return df


def _parse_date(value: Any) -> date | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, pd.Timestamp):
        if pd.isna(value):
            return None
        return value.date()

    raw = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    for dayfirst in (True, False):
        parsed = pd.to_datetime(raw, errors="coerce", dayfirst=dayfirst)
        if not pd.isna(parsed):
            return parsed.date()
    return None


def _safe_cell(row: pd.Series, key: str) -> Any:
    if key not in row.index:
        return None
    value = row.get(key)
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, str) and not value.strip():
        return None
    return value


def _row_to_record(row: pd.Series) -> RawAttendanceRow | None:
    code_raw = _safe_cell(row, "employee_code")
    name_raw = _safe_cell(row, "employee_name")
    work_date = _parse_date(_safe_cell(row, "work_date"))
    if code_raw is None or name_raw is None or work_date is None:
        return None

    code = str(code_raw).strip()
    name = str(name_raw).strip()
    if code.lower() in {"nan", "none"} or name.lower() in {"nan", "none"}:
        return None
    # Strip Excel float codes like "1001.0"
    if code.endswith(".0") and code.replace(".", "", 1).isdigit():
        code = code[:-2]

    department = _safe_cell(row, "department")
    department_value = None if department is None else str(department).strip()

    status_raw = _safe_cell(row, "status")
    status = None if status_raw is None else str(status_raw).strip().lower()

    overtime_raw = _safe_cell(row, "overtime")
    overtime_hours = hours_to_decimal(overtime_raw)
    # Biometric CSV exports sometimes omit empty overtime and shift status left.
    if status is None and overtime_raw is not None and overtime_hours is None:
        candidate = str(overtime_raw).strip().lower().replace(" ", "_")
        if candidate in {
            "present",
            "absent",
            "leave",
            "weekly_off",
            "holiday",
            "missing_checkout",
            "p",
            "a",
            "l",
            "lv",
            "wo",
            "h",
            "hl",
        }:
            status = candidate
            overtime_raw = None

    return RawAttendanceRow(
        employee_code=code,
        employee_name=name,
        department=department_value,
        work_date=work_date,
        check_in=parse_time(_safe_cell(row, "check_in")),
        check_out=parse_time(_safe_cell(row, "check_out")),
        work_duration_hours=hours_to_decimal(_safe_cell(row, "work_duration")),
        break_duration_hours=hours_to_decimal(_safe_cell(row, "break_duration")),
        overtime_hours=hours_to_decimal(overtime_raw),
        status=status,
    )


def _cell_text(value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    if isinstance(value, datetime):
        return value.isoformat(sep=" ")
    if isinstance(value, date):
        return value.isoformat()
    text = str(value).strip()
    if text.lower() in {"nan", "none", "nat"}:
        return ""
    return text


def _matrix_from_frame(df: pd.DataFrame) -> list[list[Any]]:
    return [row.tolist() for _, row in df.iterrows()]


def _first_nonempty(row: list[Any]) -> tuple[int, str]:
    for idx, cell in enumerate(row):
        text = _cell_text(cell)
        if text:
            return idx, text
    return -1, ""


def _normalize_label(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower().rstrip(":"))


def _metric_label(text: str) -> str | None:
    label = _normalize_label(text)
    if label in _MONTHLY_ROW_LABELS:
        return _MONTHLY_ROW_LABELS[label]
    # Labels may include trailing notes, e.g. "WORK (Hrs)"
    for key, canonical in _MONTHLY_ROW_LABELS.items():
        if label == key or label.startswith(f"{key} ") or label.startswith(f"{key}("):
            return canonical
    return None


def _parse_day_number(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and not pd.isna(value):
        number = int(value)
        if 1 <= number <= 31 and float(value) == number:
            return number
        return None
    text = _cell_text(value)
    if text.isdigit():
        number = int(text)
        if 1 <= number <= 31:
            return number
    return None


def _day_columns(row: list[Any]) -> dict[int, int]:
    """Map calendar day -> column index from a day header row (1..31)."""
    mapping: dict[int, int] = {}
    for col_idx, cell in enumerate(row):
        day = _parse_day_number(cell)
        if day is not None and day not in mapping:
            mapping[day] = col_idx
    return mapping


def _looks_like_day_header(row: list[Any]) -> bool:
    days = _day_columns(row)
    return len(days) >= 7 and max(days) - min(days) + 1 >= 7


def _resolve_month_token(token: str) -> int | None:
    key = token.strip().lower()
    if key in _MONTH_NAMES:
        return _MONTH_NAMES[key]
    if len(key) >= 3 and key[:3] in _MONTH_NAMES:
        return _MONTH_NAMES[key[:3]]
    return None


def _infer_year_month(matrix: list[list[Any]], filename: str) -> tuple[int, int]:
    blob = " ".join(_cell_text(cell) for row in matrix[:20] for cell in row)
    blob = f"{blob} {filename}"

    match = re.search(
        r"\b(january|february|march|april|may|june|july|august|september|october|november|december|"
        r"jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)\.?\s*[-/]?\s*(20\d{2})\b",
        blob,
        re.IGNORECASE,
    )
    if match:
        month = _resolve_month_token(match.group(1))
        if month:
            return int(match.group(2)), month

    match = re.search(r"\b(20\d{2})[-/.](\d{1,2})\b", blob)
    if match:
        year, month = int(match.group(1)), int(match.group(2))
        if 1 <= month <= 12:
            return year, month
    match = re.search(r"\b(\d{1,2})[-/.](20\d{2})\b", blob)
    if match:
        month, year = int(match.group(1)), int(match.group(2))
        if 1 <= month <= 12:
            return year, month
    match = re.search(
        r"\byear\s*[:=]?\s*(20\d{2}).{0,40}month\s*[:=]?\s*(\d{1,2})",
        blob,
        re.IGNORECASE,
    )
    if match:
        return int(match.group(1)), int(match.group(2))
    match = re.search(
        r"\bmonth\s*[:=]?\s*(\d{1,2}).{0,40}year\s*[:=]?\s*(20\d{2})",
        blob,
        re.IGNORECASE,
    )
    if match:
        return int(match.group(2)), int(match.group(1))

    today = date.today()
    return today.year, today.month


def _extract_meta_from_text(text: str, meta: dict[str, str]) -> None:
    """Regex fallback for 'Label: Value' fragments. Skips ultra-short labels to avoid false hits."""
    for label, key in _META_LABELS.items():
        if key in meta or len(label) < 3:
            continue
        pattern = rf"(?<![a-z0-9]){re.escape(label)}(?![a-z0-9])\s*[:=#-]?\s*([^\s|,;]+(?:\s+[^\s|,;]+)?)"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = match.group(1).strip().rstrip(",;")
            if value and _normalize_label(value) != label and _normalize_label(value) not in _META_LABELS:
                meta[key] = value


def _extract_employee_metadata(rows: list[list[Any]]) -> dict[str, str]:
    """
    Production biometric blocks store labels and values in the same row, e.g.:

    Empcode | K6k031 | Name | Azeem | Present | 20 | WO | 3 | ...
    """
    meta: dict[str, str] = {}
    for row in rows:
        # Prefer adjacent label → value cells (robust for company monthly XLS)
        for idx, cell in enumerate(row):
            raw = _cell_text(cell)
            if not raw:
                continue
            if ":" in raw:
                left, right = raw.split(":", 1)
                mapped = _META_LABELS.get(_normalize_label(left))
                if mapped and right.strip():
                    meta.setdefault(mapped, right.strip())
                    continue
            label = _normalize_label(raw)
            mapped = _META_LABELS.get(label)
            if not mapped:
                continue
            for nxt in row[idx + 1 :]:
                value = _cell_text(nxt)
                if not value:
                    continue
                if _normalize_label(value) in _META_LABELS:
                    break
                meta.setdefault(mapped, value)
                break

        texts = [_cell_text(cell) for cell in row]
        joined = " | ".join(t for t in texts if t)
        if joined:
            _extract_meta_from_text(joined, meta)
    return meta


def _is_weekday_header_row(row: list[Any]) -> bool:
    """Company monthly reports insert Mon/Tue/... between day numbers and IN/OUT rows."""
    tokens = [_normalize_label(_cell_text(c)) for c in row if _cell_text(c)]
    if len(tokens) < 5:
        return False
    hits = sum(1 for token in tokens if token in _WEEKDAY_TOKENS or token[:3] in _WEEKDAY_TOKENS)
    return hits >= 5 and hits >= len(tokens) * 0.7


def _is_monthly_block_matrix(matrix: list[list[Any]]) -> bool:
    """Detect company monthly export: day columns 1-31 with stacked IN/OUT/WORK/Break/OT/Status."""
    metric_hits = 0
    day_headers = 0
    for row in matrix:
        label = _metric_label(_first_nonempty(row)[1])
        if label:
            metric_hits += 1
        if _looks_like_day_header(row):
            day_headers += 1
    return day_headers >= 1 and metric_hits >= 4


def _collect_metric_rows(
    matrix: list[list[Any]], start_idx: int
) -> tuple[dict[str, list[Any]], int]:
    metrics: dict[str, list[Any]] = {}
    idx = start_idx
    while idx < len(matrix):
        row = matrix[idx]
        # Skip blank spacer rows and weekday header rows (Mon..Sun)
        if not any(_cell_text(c) for c in row) or _is_weekday_header_row(row):
            idx += 1
            continue

        _, label_text = _first_nonempty(row)
        label = _metric_label(label_text)
        if label is None:
            break
        metrics[label] = row
        idx += 1
        if len(metrics) >= 6:
            break
    return metrics, idx


def _status_value(raw: Any) -> str | None:
    text = _cell_text(raw)
    if not text:
        return None
    return text.strip().lower()


def _parse_monthly_block_matrix(matrix: list[list[Any]], filename: str) -> list[RawAttendanceRow]:
    year, month = _infer_year_month(matrix, filename)
    days_in_month = calendar.monthrange(year, month)[1]
    records: list[RawAttendanceRow] = []

    idx = 0
    while idx < len(matrix):
        row = matrix[idx]
        if not _looks_like_day_header(row):
            idx += 1
            continue

        day_map = _day_columns(row)
        # Metadata sits above the day header (same employee block)
        meta_window = matrix[max(0, idx - 6) : idx]
        meta = _extract_employee_metadata(meta_window)
        metrics, next_idx = _collect_metric_rows(matrix, idx + 1)
        required = {"in", "out", "work", "break", "ot", "status"}
        if not required.issubset(metrics.keys()):
            idx += 1
            continue

        code = meta.get("employee_code", "").strip()
        name = meta.get("employee_name", "").strip()
        if code.endswith(".0") and code.replace(".", "", 1).isdigit():
            code = code[:-2]
        if not code or not name:
            idx = max(next_idx, idx + 1)
            continue

        department = meta.get("department")
        in_row = metrics["in"]
        out_row = metrics["out"]
        work_row = metrics["work"]
        break_row = metrics["break"]
        ot_row = metrics["ot"]
        status_row = metrics["status"]

        for day, col_idx in sorted(day_map.items()):
            if day > days_in_month:
                continue
            status = _status_value(status_row[col_idx] if col_idx < len(status_row) else None)
            check_in = parse_time(in_row[col_idx] if col_idx < len(in_row) else None)
            check_out = parse_time(out_row[col_idx] if col_idx < len(out_row) else None)
            work_hours = hours_to_decimal(work_row[col_idx] if col_idx < len(work_row) else None)
            break_hours = hours_to_decimal(break_row[col_idx] if col_idx < len(break_row) else None)
            ot_hours = hours_to_decimal(ot_row[col_idx] if col_idx < len(ot_row) else None)

            # Skip completely empty day cells (beyond paid month ending)
            if (
                status is None
                and check_in is None
                and check_out is None
                and work_hours is None
                and break_hours is None
                and ot_hours is None
            ):
                continue

            records.append(
                RawAttendanceRow(
                    employee_code=code,
                    employee_name=name,
                    department=department,
                    work_date=date(year, month, day),
                    check_in=check_in,
                    check_out=check_out,
                    work_duration_hours=work_hours,
                    break_duration_hours=break_hours,
                    overtime_hours=ot_hours,
                    status=status,
                )
            )

        idx = max(next_idx, idx + 1)

    return records


def _try_parse_monthly_block(df: pd.DataFrame, filename: str) -> list[RawAttendanceRow] | None:
    matrix = _matrix_from_frame(df)
    if not _is_monthly_block_matrix(matrix):
        return None

    logger.info("Detected format: Monthly Biometric Report")
    logger.info("Using parser: MonthlyBlockParser")

    records = _parse_monthly_block_matrix(matrix, filename)
    if not records:
        # Monthly layout confirmed — do not fall through to flat CSV column validation
        raise ApplicationError(
            "Monthly biometric report detected but no employee attendance blocks could be extracted",
            code="attendance_monthly_parse_empty",
            details={
                "filename": filename,
                "hint": "Expected Empcode/Name metadata and IN/OUT/WORK/Break/OT/Status rows under day columns 1-31",
            },
        )
    return records


PREFERRED_SHEET_NAMES = (
    "attendance",
    "daily attendance",
    "monthly attendance",
    "sheet1",
    "export",
    "data",
)

# OLE Compound Document (legacy BIFF .xls)
_XLS_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
# ZIP container used by .xlsx / .xlsm
_XLSX_MAGIC_PREFIX = b"PK"


def _looks_like_text_tabular(data: bytes) -> bool:
    """Heuristic: content is plain-text CSV/TSV rather than a binary workbook."""
    sample = data[:8192]
    if not sample or b"\x00" in sample[:1024]:
        return False
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            text = sample.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        return False
    return any(sep in text for sep in (",", "\t", ";", "\n"))


def _detect_file_format(data: bytes, filename: str) -> str:
    """
    Detect real attendance file type from content first, then fall back to extension.

    Returns: 'csv' | 'xls' | 'xlsx'
    """
    if data.startswith(_XLS_MAGIC):
        return "xls"
    if data.startswith(_XLSX_MAGIC_PREFIX):
        return "xlsx"

    name = Path(filename or "").name.lower()
    # Misnamed Excel that is actually CSV text (common biometric export quirk)
    if _looks_like_text_tabular(data):
        return "csv"

    if name.endswith(".xls") and not name.endswith((".xlsx", ".xlsm")):
        return "xls"
    if name.endswith((".xlsx", ".xlsm")):
        return "xlsx"
    return "csv"


def _pick_workbook_sheet(workbook: dict[str, pd.DataFrame]) -> pd.DataFrame:
    if not workbook:
        raise ApplicationError("Attendance workbook has no sheets", code="attendance_file_empty")
    sheet_name = next(
        (key for key in workbook if str(key).strip().lower() in PREFERRED_SHEET_NAMES),
        next(iter(workbook)),
    )
    logger.info("Using workbook sheet %r (available=%s)", sheet_name, list(workbook.keys()))
    return workbook[sheet_name]


def _load_excel_workbook(data: bytes, *, engine: str) -> pd.DataFrame:
    buffer = BytesIO(data)
    workbook = pd.read_excel(buffer, sheet_name=None, header=None, engine=engine)
    return _pick_workbook_sheet(workbook)


def _load_csv_bytes(data: bytes) -> pd.DataFrame:
    # Try common encodings used by biometric exports
    last_error: Exception | None = None
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return pd.read_csv(BytesIO(data), encoding=encoding)
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            continue
    assert last_error is not None
    raise last_error


def _load_dataframe(file_obj: BinaryIO, filename: str) -> pd.DataFrame:
    data = file_obj.read()
    if not data:
        raise ApplicationError("Attendance file is empty", code="attendance_file_empty")

    detected = _detect_file_format(data, filename)
    logger.info(
        "Loading attendance file %r as %s (size=%s bytes, extension_hint=%s)",
        filename,
        detected,
        len(data),
        Path(filename or "").suffix.lower() or "(none)",
    )

    try:
        if detected == "xls":
            return _load_excel_workbook(data, engine="xlrd")
        if detected == "xlsx":
            return _load_excel_workbook(data, engine="openpyxl")
        return _load_csv_bytes(data)
    except ApplicationError:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "Unable to parse attendance file %r (detected=%s) — %s: %s",
            filename,
            detected,
            type(exc).__name__,
            exc,
        )
        raise ApplicationError(
            "Unable to parse attendance file",
            code="attendance_file_parse_error",
            details=f"{type(exc).__name__}: {exc}",
        ) from exc


def read_attendance_file(file_obj: BinaryIO, filename: str) -> list[RawAttendanceRow]:
    try:
        df = _load_dataframe(file_obj, filename)
        if df.empty:
            return []

        # Production biometric monthly Excel (employee blocks + day columns 1-31)
        monthly = _try_parse_monthly_block(df, filename)
        if monthly is not None:
            logger.info(
                "Parsed %s rows via MonthlyBlockParser from %r",
                len(monthly),
                filename,
            )
            return monthly

        logger.info("Detected format: Flat Attendance Table")
        logger.info("Using parser: FlatTableParser")

        # Flat daily table (CSV / simplified Excel)
        framed = _detect_header_frame(df)
        framed = _normalize_columns(framed)
        required = {"employee_code", "employee_name", "work_date"}
        missing = required - set(framed.columns)
        if missing:
            raise ApplicationError(
                f"Attendance file missing required columns: {', '.join(sorted(missing))}",
                code="attendance_file_invalid",
                details={"columns_found": [str(c) for c in framed.columns]},
            )

        records: list[RawAttendanceRow] = []
        for _, row in framed.iterrows():
            record = _row_to_record(row)
            if record is not None:
                records.append(record)
        logger.info("Parsed %s rows from flat daily layout in %r", len(records), filename)
        return records
    except ApplicationError:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "Unable to parse attendance file %r — %s: %s",
            filename,
            type(exc).__name__,
            exc,
        )
        raise ApplicationError(
            "Unable to parse attendance file",
            code="attendance_file_parse_error",
            details=f"{type(exc).__name__}: {exc}",
        ) from exc


def normalize_api_payload(payload: list[dict[str, Any]]) -> list[RawAttendanceRow]:
    """Same contract as file provider so payroll/attendance logic stays untouched."""
    records: list[RawAttendanceRow] = []
    for item in payload:
        work_date = _parse_date(item.get("work_date") or item.get("date"))
        code = str(item.get("employee_code") or item.get("employee_id") or "").strip()
        name = str(item.get("employee_name") or item.get("name") or "").strip()
        if not code or not name or work_date is None:
            continue
        records.append(
            RawAttendanceRow(
                employee_code=code,
                employee_name=name,
                department=item.get("department"),
                work_date=work_date,
                check_in=parse_time(item.get("check_in")),
                check_out=parse_time(item.get("check_out")),
                work_duration_hours=hours_to_decimal(item.get("work_duration") or item.get("work_duration_hours")),
                break_duration_hours=hours_to_decimal(
                    item.get("break_duration") or item.get("break_duration_hours")
                ),
                overtime_hours=hours_to_decimal(item.get("overtime") or item.get("overtime_hours")),
                status=(str(item["status"]).lower() if item.get("status") else None),
            )
        )
    return records
