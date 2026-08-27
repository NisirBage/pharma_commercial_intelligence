"""Shared response envelope and generic types used across every endpoint.

Every successful response is `{"data": ..., "metadata": {...}}`; every
error is `{"error": {"code", "message", "details"}}` — one consistent
shape (M6 Sec. 20), never an elaborate per-endpoint wrapper.
"""

import math
from datetime import datetime, timezone
from typing import Annotated, Any, Generic, TypeVar

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

T = TypeVar("T")


def _sanitize_float(v: Any) -> Any:
    """NaN/Infinity are valid Python floats but NOT valid JSON — silently
    letting one through would produce a response a strict JSON parser
    (e.g. `JSON.parse` in a browser) chokes on. Every place this project's
    own analytics/forecasting/optimization code already returns `None` for
    an undefined result (division by zero, insufficient data, etc.) — this
    is a defensive net for anything that slips through, not the primary
    mechanism (M6 Sec. 31 contract-testing requirement)."""
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    return v


SafeFloat = Annotated[float | None, BeforeValidator(_sanitize_float)]


class ResponseMetadata(BaseModel):
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source: str | None = Field(None, description="Which milestone's logic produced this data, e.g. 'M3 analytics'.")


class SuccessResponse(BaseModel, Generic[T]):
    data: T
    metadata: ResponseMetadata = Field(default_factory=ResponseMetadata)


class ErrorDetail(BaseModel):
    field: str | None = None
    message: str


class ErrorBody(BaseModel):
    code: str
    message: str
    details: list[ErrorDetail] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    error: ErrorBody


class MetricValue(BaseModel):
    """Mirrors `app.analytics.types.MetricResult` field-for-field — the
    generic shape used wherever an M3 analytics function's raw output is
    exposed without a more specific schema."""

    model_config = ConfigDict(from_attributes=True)

    metric: str
    value: SafeFloat
    period: str | None
    entity: str | None
    grain: str
    metadata: dict[str, Any] = Field(default_factory=dict)
