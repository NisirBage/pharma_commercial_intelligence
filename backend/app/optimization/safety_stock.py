"""Safety-stock calculation.

**Choice of uncertainty source — and why it isn't the textbook default.**
The classic inventory-theory formula (`SS = z * sigma_demand * sqrt(lead_time)`)
uses the standard deviation of RAW historical demand. That would be wrong
here: M4's forecast already explains a large share of that raw variance
(trend, weekly/annual seasonality) — using raw historical demand
variability would double-count signal the model already captures and
systematically overstate the safety stock actually needed. The
textbook-correct quantity is the standard deviation of the FORECAST
ERROR (residual) during the lead time — i.e. how wrong the forecast
itself tends to be — which is exactly what M4's backtesting already
produced. This module uses that, sourced via
`app.optimization.demand_input`, never raw demand variance.

**Three lead-time-uncertainty estimators, all reported, one primary:**

1. **Additive per-step variance (PRIMARY).**
   `sigma_L = sqrt(sum_{h=1..L} std_h^2)`, where `std_h` is the actual
   observed std of the selected model's out-of-fold residual AT horizon
   step h (from M4's 6 backtest folds), not an assumed flat value. This
   is more accurate than the flat-`sqrt(L)` shortcut below whenever error
   variance genuinely differs across the horizon (M4's diagnostics found
   exactly that for the aggregate series — horizon-step MAE ranged
   3.68-23.87, not flat).
2. **Flat sqrt(L) scaling (cross-check).** `sigma_L = std_1 * sqrt(L)`,
   the textbook shortcut, assuming i.i.d. errors across days. Reported
   for comparison; NOT primary, because M4 found significant residual
   autocorrelation for several classes (ALL, N02BE, N05B, N05C —
   Ljung-Box p < 0.003), which violates the independence assumption this
   shortcut relies on.
3. **Empirical fold-level cumulative error (small-sample cross-check).**
   The standard deviation of the 6 backtest folds' own L-day CUMULATIVE
   forecast error (summed within each fold, not across folds) — this
   captures whatever autocorrelation exists directly, with no
   independence assumption at all, at the cost of a very small sample
   (n=6). Reported for comparison only; too fragile at high service
   levels to be primary with just 6 folds.

Where estimators (1) and (3) diverge substantially for a class, that is
itself a signal worth surfacing — see `uncertainty_estimator_spread` in
the result and docs/optimization-insights.md.
"""

from dataclasses import dataclass

from scipy.stats import norm

from app.optimization.demand_input import DemandInput


@dataclass
class SafetyStockResult:
    atc_class: str
    lead_time_days: int
    service_level_target: float
    z_score: float
    sigma_lead_time_primary: float  # additive per-step variance estimator
    sigma_lead_time_flat_sqrt: float  # cross-check
    sigma_lead_time_empirical_fold: float | None  # cross-check (None if <2 folds available)
    safety_stock: float  # = z_score * sigma_lead_time_primary
    uncertainty_estimator_spread_pct: float | None  # relative gap between primary and flat estimators


def sigma_lead_time_additive(demand_input: DemandInput, lead_time_days: int) -> float:
    """Estimator (1), PRIMARY."""
    steps = demand_input.residual_std_by_step[:lead_time_days]
    return float(sum(s**2 for s in steps) ** 0.5)


def sigma_lead_time_flat_sqrt(demand_input: DemandInput, lead_time_days: int) -> float:
    """Estimator (2), cross-check."""
    std_1 = demand_input.residual_std_by_step[0]
    return float(std_1 * (lead_time_days**0.5))


def sigma_lead_time_empirical_fold(demand_input: DemandInput, lead_time_days: int) -> float | None:
    """Estimator (3), cross-check. None if fewer than 2 fold samples exist
    (a standard deviation of 1 point is undefined)."""
    samples = demand_input.fold_cumulative_errors.get(lead_time_days)
    if samples is None or len(samples) < 2:
        return None
    n = len(samples)
    mean = sum(samples) / n
    variance = sum((x - mean) ** 2 for x in samples) / (n - 1)
    return float(variance**0.5)


def newsvendor_critical_fractile_z(stockout_cost_weight: float, holding_cost_weight: float) -> float:
    """Classic newsvendor critical fractile: the cost-minimizing implied
    service level given the RATIO of stockout to holding cost weights —
    `z* = Phi^-1(Cu / (Cu + Co))`, where `Cu` = stockout_cost_weight (the
    relative cost of being one unit short) and `Co` = holding_cost_weight
    (the relative cost of holding one excess unit). Both are unitless
    SCENARIO WEIGHTS (app.optimization.assumptions), never real costs —
    this produces a scenario-implied service level, not a dollar-optimal
    one. This is the one place `stockout_cost_weight` has a
    non-degenerate effect on a single class's own safety stock (varying a
    single global weight uniformly across classes in the cross-class LP —
    app.optimization.allocation_optimizer — does NOT change that LP's
    optimum, since scaling every class's objective term by the same
    constant leaves the argmin unchanged; only the RATIO to
    holding_cost_weight matters, which is exactly what this function
    uses)."""
    if stockout_cost_weight < 0 or holding_cost_weight < 0:
        raise ValueError("cost weights must be non-negative")
    if stockout_cost_weight + holding_cost_weight == 0:
        raise ValueError("at least one cost weight must be positive")
    critical_fractile = stockout_cost_weight / (stockout_cost_weight + holding_cost_weight)
    return float(norm.ppf(critical_fractile))


def compute_safety_stock(
    demand_input: DemandInput, lead_time_days: int, service_level_target: float
) -> SafetyStockResult:
    if not 0 < service_level_target < 1:
        raise ValueError(f"service_level_target must be in (0, 1), got {service_level_target}")
    if lead_time_days < 0:
        raise ValueError(f"lead_time_days must be >= 0, got {lead_time_days}")
    if lead_time_days > len(demand_input.residual_std_by_step):
        raise ValueError(
            f"lead_time_days={lead_time_days} exceeds the {len(demand_input.residual_std_by_step)}-day "
            "forecast horizon available from app.forecasting — cannot estimate lead-time uncertainty beyond it."
        )

    z = float(norm.ppf(service_level_target))

    if lead_time_days == 0:
        # Zero lead time -> zero lead-time demand uncertainty by
        # construction (nothing to protect against between order and
        # receipt). Handled explicitly rather than falling through to a
        # sum-of-zero-terms that happens to also give 0.
        return SafetyStockResult(
            atc_class=demand_input.atc_class,
            lead_time_days=0,
            service_level_target=service_level_target,
            z_score=z,
            sigma_lead_time_primary=0.0,
            sigma_lead_time_flat_sqrt=0.0,
            sigma_lead_time_empirical_fold=None,
            safety_stock=0.0,
            uncertainty_estimator_spread_pct=None,
        )

    sigma_primary = sigma_lead_time_additive(demand_input, lead_time_days)
    sigma_flat = sigma_lead_time_flat_sqrt(demand_input, lead_time_days)
    sigma_empirical = sigma_lead_time_empirical_fold(demand_input, lead_time_days)

    spread_pct = None
    if sigma_flat > 0:
        spread_pct = float((sigma_primary - sigma_flat) / sigma_flat * 100)

    return SafetyStockResult(
        atc_class=demand_input.atc_class,
        lead_time_days=lead_time_days,
        service_level_target=service_level_target,
        z_score=z,
        sigma_lead_time_primary=sigma_primary,
        sigma_lead_time_flat_sqrt=sigma_flat,
        sigma_lead_time_empirical_fold=sigma_empirical,
        safety_stock=float(max(z, 0.0) * sigma_primary),
        uncertainty_estimator_spread_pct=spread_pct,
    )
