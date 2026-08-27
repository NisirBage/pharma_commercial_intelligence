from enum import Enum

from pydantic import BaseModel

from app.schemas.common import SafeFloat


class AnomalyMethod(str, Enum):
    rolling_zscore = "rolling_zscore"
    iqr = "iqr"


class AnomalySeverity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class AnomalyItem(BaseModel):
    atc_class: str
    timestamp: str
    observed: SafeFloat
    expected: SafeFloat
    deviation_pct: SafeFloat
    anomaly_score: SafeFloat
    direction: str
    severity: str
    method: str


class AnomaliesResponse(BaseModel):
    atc_class: str | None
    method: str
    total_count: int
    anomalies: list[AnomalyItem]
