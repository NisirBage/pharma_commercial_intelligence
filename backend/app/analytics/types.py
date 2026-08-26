"""Shared result types for the analytics layer. Every analytical function
returns one of these instead of a plotting-specific structure, so a future
API layer can serialize them directly (see M3 instructions, "Analytical API
preparation") without reproducing business logic in the frontend.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MetricResult:
    """A single computed number with enough context to stand alone."""

    metric: str
    value: float | int | None
    period: str | None  # e.g. "2014-01-02/2019-10-08" or "2017-01"
    entity: str | None  # e.g. an ATC code, or "ALL" for the whole dataset
    grain: str  # "hourly" | "daily" | "weekly" | "monthly" | "overall"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AnomalyResult:
    """One flagged observation from app.analytics.anomalies."""

    atc_class: str
    timestamp: str
    observed: float
    expected: float
    deviation_pct: float
    anomaly_score: float
    direction: str  # "above" | "below"
    severity: str  # "low" | "medium" | "high"
    method: str  # e.g. "rolling_zscore", "iqr"
    metadata: dict[str, Any] = field(default_factory=dict)
