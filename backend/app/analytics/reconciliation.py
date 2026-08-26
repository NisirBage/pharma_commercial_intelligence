"""Analytical reconciliation report — reuses the exact cross-granularity
checks M2 proved (app.etl.validate.check_cross_grain_reconciliation) as an
ongoing analytical quality-control signal, not just a one-time ETL
validation step. This is what lets a downstream dashboard communicate
data-source reliability at a glance, per M3 instructions Sec. 10.
"""

from pathlib import Path

from app.core.config import settings
from app.etl.extract import extract_all
from app.etl.validate import CheckResult, check_cross_grain_reconciliation

_GRAIN_LABEL = {
    "reconciliation_daily_vs_hourly": "Daily",
    "reconciliation_weekly_vs_daily": "Weekly",
    "reconciliation_monthly_vs_daily": "Monthly",
}


def build_reconciliation_report(raw_data_dir: Path | None = None) -> dict:
    datasets = extract_all(raw_data_dir or settings.raw_data_dir)
    checks: list[CheckResult] = check_cross_grain_reconciliation(datasets)

    summary: dict[str, dict] = {}
    lines: list[str] = []
    for check in checks:
        label = _GRAIN_LABEL.get(check.check_name, check.check_name)
        reconciled = check.status == "pass"
        if check.status == "pass":
            note, symbol = "Reconciled", "✓"
        elif check.status == "warn":
            note, symbol = "Source inconsistency detected", "⚠"
        else:
            note, symbol = "Reconciliation FAILED", "✗"

        summary[label] = {"reconciled": reconciled, "status": check.status, "details": check.details}
        lines.append(f"{label}:\n{note} {symbol}")

    return {
        "summary": summary,
        "human_readable": "\n\n".join(lines),
        "all_reconciled_except_known_monthly_issue": all(
            c.status == "pass" or c.check_name == "reconciliation_monthly_vs_daily" for c in checks
        ),
    }
