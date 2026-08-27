"""Planning-assumption model. Every field here is a SCENARIO PARAMETER —
none of it is observed in `milanzdravkovic/pharma-sales-data`. The Kaggle
dataset contains no inventory levels, lead times, costs, or service-level
requirements (see docs/planning-assumptions.md, the authoritative,
human-readable version of this same table) — this module exists so that
distinction is enforced in code, not just in prose: every
`ScenarioParameters` instance is explicitly constructed with a value and
is never silently defaulted from something that looks like real data.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ScenarioParameters:
    """All values here are hypothetical planning inputs for constructing a
    supply-planning SCENARIO — never a claim about any real pharmacy's
    actual lead times, costs, or service targets. See
    docs/planning-assumptions.md for the full parameter-by-parameter
    rationale table."""

    lead_time_days: int = 7
    """Days between placing a replenishment order and receiving it.
    Source: Scenario assumption. Reason: the dataset has no supplier data
    of any kind; 7 days is a round, mid-range planning number chosen to
    fit comfortably within the M4 14-day forecast horizon (so lead-time
    demand can always be read directly off the existing forecast without
    extrapolating beyond it), not because it reflects an actual
    pharmaceutical supplier's lead time."""

    review_period_days: int = 7
    """Days between periodic inventory reviews (for the order-up-to
    policy). Source: Scenario assumption. Reason: chosen equal to
    lead_time_days purely for round-number simplicity; a weekly
    review cadence is a common planning convention, not a claim about
    any real pharmacy's actual review cycle."""

    service_level_target: float = 0.95
    """Target cycle service level (probability of NOT stocking out during
    a replenishment lead time), as a fraction in (0, 1). Source: Scenario
    assumption. Reason: 95% is a conventional default in inventory-theory
    teaching material for a "balanced" policy — not a business
    requirement from any real pharmacy."""

    holding_cost_weight: float = 1.0
    """Relative (unitless) weight on inventory exposure (safety stock
    held) in the scenario objective. Source: Scenario assumption. Reason:
    the dataset has no monetary holding-cost data; this is a normalized
    weight for comparing policies within a scenario, not a real cost."""

    stockout_cost_weight: float = 4.0
    """Relative (unitless) weight on expected shortage in the scenario
    objective. Source: Scenario assumption. Reason: set higher than
    holding_cost_weight to reflect the common inventory-planning
    convention that stockouts are usually judged more costly than excess
    stock — a directional assumption, not a measured cost ratio."""

    ordering_cost_weight: float = 1.0
    """Relative (unitless) weight used only in the scenario EOQ-style
    order-quantity calculation (app.optimization.reorder_point). Source:
    Scenario assumption. Reason: no ordering-cost data exists in the
    dataset; this weight lets the EOQ formula produce a normalized
    (non-monetary) order-quantity figure for comparison purposes only."""

    minimum_order_quantity: float = 0.0
    """Floor applied to the scenario order quantity. Source: Scenario
    assumption. Reason: no supplier minimum-order data exists; defaults
    to no floor (0)."""

    maximum_order_quantity: float | None = None
    """Ceiling applied to the scenario order quantity, or None for no
    ceiling. Source: Scenario assumption. Reason: no supplier/warehouse
    capacity data exists in the dataset."""

    shared_capacity_budget: float | None = None
    """Total safety-stock UNITS available to allocate across all ATC
    classes in the cross-class optimization
    (app.optimization.allocation_optimizer) — a hypothetical shared
    warehouse/budget constraint. Source: Scenario assumption. Reason: the
    dataset has no warehouse-capacity data; when None, each scenario
    runner (app.optimization.scenarios) derives it from that scenario's
    own service_level_target so the comparison is meaningful (see
    docs/optimization-methodology.md)."""

    def as_assumption_rows(self) -> list[dict]:
        """Machine-readable version of docs/planning-assumptions.md's
        table — used by app.optimization.outputs so every result object
        carries its own assumption disclosure."""
        return [
            {"parameter": "lead_time_days", "value": self.lead_time_days, "unit": "days", "source": "scenario", "type": "assumption"},
            {"parameter": "review_period_days", "value": self.review_period_days, "unit": "days", "source": "scenario", "type": "assumption"},
            {"parameter": "service_level_target", "value": self.service_level_target, "unit": "fraction", "source": "scenario", "type": "assumption"},
            {"parameter": "holding_cost_weight", "value": self.holding_cost_weight, "unit": "unitless (scenario weight)", "source": "scenario", "type": "assumption"},
            {"parameter": "stockout_cost_weight", "value": self.stockout_cost_weight, "unit": "unitless (scenario weight)", "source": "scenario", "type": "assumption"},
            {"parameter": "ordering_cost_weight", "value": self.ordering_cost_weight, "unit": "unitless (scenario weight)", "source": "scenario", "type": "assumption"},
            {"parameter": "minimum_order_quantity", "value": self.minimum_order_quantity, "unit": "units", "source": "scenario", "type": "assumption"},
            {"parameter": "maximum_order_quantity", "value": self.maximum_order_quantity, "unit": "units", "source": "scenario", "type": "assumption"},
            {"parameter": "shared_capacity_budget", "value": self.shared_capacity_budget, "unit": "units (safety stock, summed across ATC classes)", "source": "scenario", "type": "assumption"},
        ]


# Z-scores (standard normal critical fractile) for the tiers used by the
# piecewise-linear convex reformulation in allocation_optimizer.py, and
# for the standalone per-class safety-stock formula. Chosen as a
# conventional spread of common service-level targets, not tuned to this
# dataset.
SERVICE_LEVEL_TIERS: dict[float, float] = {
    0.50: 0.0000,
    0.80: 0.8416,
    0.90: 1.2816,
    0.95: 1.6449,
    0.98: 2.0537,
    0.99: 2.3263,
}
