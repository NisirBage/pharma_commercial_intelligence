"""Small validation helpers shared across service modules — kept here
instead of duplicated per-service or imported as a "private" name across
modules."""

from datetime import date

import pandas as pd

from app.api.errors import BadRequestError


def parse_date(value: str, field_name: str) -> date:
    try:
        return pd.Timestamp(value).date()
    except (ValueError, TypeError) as exc:
        raise BadRequestError(f"Invalid {field_name}: {value!r} is not a valid date (expected YYYY-MM-DD).") from exc


def validate_date_range(start_date: str | None, end_date: str | None) -> tuple[date | None, date | None]:
    parsed_start = parse_date(start_date, "start_date") if start_date else None
    parsed_end = parse_date(end_date, "end_date") if end_date else None
    if parsed_start and parsed_end and parsed_start > parsed_end:
        raise BadRequestError(f"start_date ({start_date}) must not be after end_date ({end_date}).")
    return parsed_start, parsed_end
