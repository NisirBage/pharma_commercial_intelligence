from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import SafeFloat

MAX_LEAD_TIME_DAYS = 14  # the M4 forecast horizon — see app.optimization.safety_stock


class ScenarioName(str, Enum):
    conservative = "conservative"
    balanced = "balanced"
    lean = "lean"


class OptimizationRunRequest(BaseModel):
    scenario: ScenarioName = Field(ScenarioName.balanced, description="Named planning scenario; overridden per-field by any of the optional parameters below.")
    service_level: float | None = Field(
        None, gt=0, lt=1, description="Override the scenario's default service-level target (exclusive of 0 and 1 — a real probability)."
    )
    lead_time_days: int | None = Field(
        None, ge=0, le=MAX_LEAD_TIME_DAYS, description=f"Override the scenario's default lead time. Capped at {MAX_LEAD_TIME_DAYS} days, the M4 forecast horizon."
    )


class AssumptionRow(BaseModel):
    parameter: str
    value: Any
    unit: str
    source: str
    type: str


class ATCPlanningResultSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")  # the domain dataclass carries a few extra fields (e.g. `scenario`, `recommendation`) served by other endpoints/fields, not duplicated here

    atc_class: str
    model_used: str
    forecast: list[SafeFloat]
    forecast_dates: list[str]
    lead_time_days: int
    service_level: SafeFloat
    safety_stock: SafeFloat
    reorder_point: SafeFloat
    recommended_order_quantity: SafeFloat
    inventory_exposure: SafeFloat
    expected_shortage: SafeFloat


class AllocationPolicySchema(BaseModel):
    model_config = ConfigDict(extra="ignore")  # drops the domain dataclass's per_class breakdown, already exposed per-class in atc_results

    policy_name: str
    solver_status: str
    total_capacity_budget: SafeFloat
    total_safety_stock_allocated: SafeFloat
    total_expected_shortage: SafeFloat
    total_weighted_expected_shortage: SafeFloat


class OptimizationRunResponse(BaseModel):
    scenario: str
    assumptions: list[AssumptionRow]
    capacity_budget: SafeFloat
    atc_results: dict[str, ATCPlanningResultSchema]
    allocation_baseline: AllocationPolicySchema
    allocation_optimized: AllocationPolicySchema
    improvement_pct: SafeFloat
    warnings: list[str] = Field(default_factory=list)


class ScenarioInfo(BaseModel):
    name: str
    service_level_target: float
    lead_time_days: int
    review_period_days: int
    rationale: str


class ScenariosResponse(BaseModel):
    scenarios: list[ScenarioInfo]


class SensitivityParameter(str, Enum):
    lead_time_days = "lead_time_days"
    service_level_target = "service_level_target"
    demand_uncertainty_scale = "demand_uncertainty_scale"
    stockout_cost_weight = "stockout_cost_weight"


class SensitivityPointSchema(BaseModel):
    value: float
    safety_stock: SafeFloat
    reorder_point: SafeFloat


class SensitivityResponse(BaseModel):
    atc_class: str
    parameter: SensitivityParameter
    points: list[SensitivityPointSchema]
    elasticity: SafeFloat
