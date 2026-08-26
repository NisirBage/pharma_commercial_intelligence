"""Builds the machine-readable data-quality report: per-file record counts
(total/valid/rejected) plus every CheckResult from validate.py, as a single
JSON-serializable dict. Consumed by app/etl/load.py (persists to
data_quality_check) and written to a timestamped file under
settings.quality_report_dir for the future dashboard to read."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from app.etl.extract import DATE_FORMATS, RawDataset
from app.etl.reference_data import ATC_REFERENCE
from app.etl.validate import CheckResult

PRODUCT_COLUMNS = list(ATC_REFERENCE.keys())


def summarize_dataset(ds: RawDataset) -> dict[str, Any]:
    """A row is 'valid' if its date parses and none of its product columns
    are negative. On this dataset every row is currently valid (see M1/M2
    findings) — this still runs for real, rather than being a stub, so a
    future dataset refresh with bad rows would actually be caught."""
    df = ds.frame
    parsed_dates = pd.to_datetime(df["datum"], format=DATE_FORMATS[ds.name], errors="coerce")
    date_ok = parsed_dates.notna()

    present_product_cols = [c for c in PRODUCT_COLUMNS if c in df.columns]
    nonneg_ok = (df[present_product_cols] >= 0).all(axis=1) if present_product_cols else True

    valid_mask = date_ok & nonneg_ok
    total = len(df)
    valid = int(valid_mask.sum())
    rejected = total - valid

    return {
        "file_name": ds.name,
        "total_records": total,
        "valid_records": valid,
        "rejected_records": rejected,
        "rejected_row_indices": df.index[~valid_mask].tolist()[:50],  # capped for report size
    }


def build_report(
    datasets: dict[str, RawDataset],
    check_results: list[CheckResult],
    kaggle_dataset_id: str,
) -> dict[str, Any]:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "kaggle_dataset_id": kaggle_dataset_id,
        "file_summaries": [summarize_dataset(ds) for ds in datasets.values()],
        "checks": [
            {
                "check_name": r.check_name,
                "file_name": r.file_name,
                "status": r.status,
                "details": r.details,
                "checked_at": r.checked_at.isoformat(),
            }
            for r in check_results
        ],
        "overall_status": "fail" if any(r.status == "fail" for r in check_results) else (
            "warn" if any(r.status == "warn" for r in check_results) else "pass"
        ),
    }


def write_report(report: dict[str, Any], output_dir: Path, run_id: int | None = None) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    suffix = f"_run{run_id}" if run_id is not None else ""
    path = output_dir / f"quality_report_{ts}{suffix}.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return path
