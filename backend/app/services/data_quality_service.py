"""Wraps app.etl (M2) + app.analytics.reconciliation (M3) for
GET /api/v1/data-quality — preserves the documented monthly-source
inconsistency; never hides it for presentation purposes (M6 Sec. 19)."""

from app.core.config import settings
from app.schemas.data_quality import DataQualityResponse, FileSummary, ReconciliationStatus
from app.services import cache

_NOTES = {
    "pass": "Reconciled",
    "warn": "Known source inconsistency — see docs/data-quality-decisions.md",
    "fail": "Reconciliation FAILED",
}


def get_data_quality() -> DataQualityResponse:
    report = cache.get_quality_report()
    reconciliation_report = cache.get_reconciliation_report()

    reconciliation = [
        ReconciliationStatus(
            label=label,
            reconciled=info["reconciled"],
            status=info["status"],
            note=_NOTES.get(info["status"], info["status"]),
        )
        for label, info in reconciliation_report["summary"].items()
    ]

    return DataQualityResponse(
        kaggle_dataset_id=settings.kaggle_dataset_id,
        overall_status=report["overall_status"],
        file_summaries=[
            FileSummary(
                file_name=f["file_name"],
                total_records=f["total_records"],
                valid_records=f["valid_records"],
                rejected_records=f["rejected_records"],
            )
            for f in report["file_summaries"]
        ],
        reconciliation=reconciliation,
        monthly_inconsistency_warning=(
            "salesmonthly.csv does not reconcile with the daily-grain sum for 33/70 months (61/560 cells) — "
            "see docs/data-quality-decisions.md Decision 2. Every monthly figure served by this API is derived "
            "from the canonical hourly fact table, never from salesmonthly.csv."
        ),
    )
