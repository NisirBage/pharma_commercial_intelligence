"""Reorder-point, order-up-to-level, and scenario order-quantity
calculations. All built directly on `app.optimization.safety_stock` —
none of these recompute uncertainty themselves.
"""

from dataclasses import dataclass

from app.optimization.demand_input import DemandInput
from app.optimization.safety_stock import SafetyStockResult, compute_safety_stock


@dataclass
class ReorderPointResult:
    atc_class: str
    lead_time_days: int
    expected_demand_during_lead_time: float
    safety_stock: float
    reorder_point: float
    safety_stock_detail: SafetyStockResult


def compute_reorder_point(
    demand_input: DemandInput, lead_time_days: int, service_level_target: float
) -> ReorderPointResult:
    """Continuous-review (s, Q) policy reorder point:
    ROP = expected demand during lead time + safety stock. Expected
    demand comes directly from M4's point forecast (first `lead_time_days`
    days) — never recomputed or approximated from historical averages."""
    ss_result = compute_safety_stock(demand_input, lead_time_days, service_level_target)
    expected_demand = sum(demand_input.point_forecast[:lead_time_days])
    return ReorderPointResult(
        atc_class=demand_input.atc_class,
        lead_time_days=lead_time_days,
        expected_demand_during_lead_time=float(expected_demand),
        safety_stock=ss_result.safety_stock,
        reorder_point=float(expected_demand + ss_result.safety_stock),
        safety_stock_detail=ss_result,
    )


@dataclass
class OrderUpToResult:
    atc_class: str
    lead_time_days: int
    review_period_days: int
    expected_demand_during_protection_interval: float
    safety_stock: float
    order_up_to_level: float


def compute_order_up_to_level(
    demand_input: DemandInput, lead_time_days: int, review_period_days: int, service_level_target: float
) -> OrderUpToResult:
    """Periodic-review (R, S) policy order-up-to level. The protection
    interval is lead_time + review_period — stock must cover demand until
    the order placed at the NEXT review also arrives, not just until the
    current order arrives."""
    protection_interval = lead_time_days + review_period_days
    if protection_interval > len(demand_input.residual_std_by_step):
        raise ValueError(
            f"lead_time_days + review_period_days = {protection_interval} exceeds the "
            f"{len(demand_input.residual_std_by_step)}-day forecast horizon available."
        )
    ss_result = compute_safety_stock(demand_input, protection_interval, service_level_target)
    expected_demand = sum(demand_input.point_forecast[:protection_interval])
    return OrderUpToResult(
        atc_class=demand_input.atc_class,
        lead_time_days=lead_time_days,
        review_period_days=review_period_days,
        expected_demand_during_protection_interval=float(expected_demand),
        safety_stock=ss_result.safety_stock,
        order_up_to_level=float(expected_demand + ss_result.safety_stock),
    )


def compute_scenario_order_quantity(
    demand_input: DemandInput,
    ordering_cost_weight: float,
    holding_cost_weight: float,
    minimum_order_quantity: float = 0.0,
    maximum_order_quantity: float | None = None,
) -> float:
    """Scenario (non-monetary) EOQ-style order quantity:
    `Q = sqrt(2 * D * ordering_cost_weight / holding_cost_weight)`, where
    D is average DAILY forecast demand and both weights are unitless
    scenario parameters (app.optimization.assumptions) — NOT real costs.
    This is a relative planning figure for comparing scenarios against
    each other, never a claim about an actual cost-optimal order size."""
    if holding_cost_weight <= 0:
        raise ValueError("holding_cost_weight must be > 0")
    avg_daily_demand = sum(demand_input.point_forecast) / len(demand_input.point_forecast)
    q = (2 * avg_daily_demand * ordering_cost_weight / holding_cost_weight) ** 0.5
    q = max(q, minimum_order_quantity)
    if maximum_order_quantity is not None:
        q = min(q, maximum_order_quantity)
    return float(q)
