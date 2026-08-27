"""Wraps app.analytics.anomalies (M3) for GET /api/v1/analytics/anomalies
— the rolling z-score and IQR methods, unchanged from M3 (M6 Sec. 10)."""

import pandas as pd

from app.analytics import anomalies as anomalies_module
from app.api.errors import BadRequestError, NotFoundError
from app.schemas.anomalies import AnomaliesResponse, AnomalyItem, AnomalyMethod
from app.services import cache
from app.services.atc_registry import KNOWN_ATC_CLASSES
from app.services.validation import validate_date_range


def get_anomalies(
    atc_class: str | None,
    method: AnomalyMethod,
    severity: str | None,
    start_date: str | None,
    end_date: str | None,
) -> AnomaliesResponse:
    if atc_class is not None and atc_class not in KNOWN_ATC_CLASSES:
        raise NotFoundError(f"Unknown ATC class {atc_class!r}. Known classes: {sorted(KNOWN_ATC_CLASSES)}.")
    if severity is not None and severity not in ("low", "medium", "high"):
        raise BadRequestError(f"Invalid severity {severity!r} — must be one of 'low', 'medium', 'high'.")

    parsed_start, parsed_end = validate_date_range(start_date, end_date)

    df = cache.get_canonical_frame()
    if atc_class is not None:
        results = (
            anomalies_module.detect_rolling_zscore(df, atc_class)
            if method == AnomalyMethod.rolling_zscore
            else anomalies_module.detect_iqr(df, atc_class)
        )
    else:
        results = anomalies_module.detect_anomalies(df, methods=(method.value,))

    if severity:
        results = [r for r in results if r.severity == severity]
    if parsed_start:
        results = [r for r in results if pd.Timestamp(r.timestamp).date() >= parsed_start]
    if parsed_end:
        results = [r for r in results if pd.Timestamp(r.timestamp).date() <= parsed_end]

    items = [
        AnomalyItem(
            atc_class=r.atc_class,
            timestamp=r.timestamp,
            observed=r.observed,
            expected=r.expected,
            deviation_pct=r.deviation_pct,
            anomaly_score=r.anomaly_score,
            direction=r.direction,
            severity=r.severity,
            method=r.method,
        )
        for r in results
    ]
    return AnomaliesResponse(atc_class=atc_class, method=method.value, total_count=len(items), anomalies=items)
