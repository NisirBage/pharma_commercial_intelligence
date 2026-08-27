# Planning Assumptions

Every parameter below is a **scenario assumption** — none of it is
observed in `milanzdravkovic/pharma-sales-data`. The Kaggle dataset
contains no inventory levels, current stock, purchase orders, supplier
lead times, holding/ordering/stockout costs, service-level targets, or
warehouse capacity (see [01-data-dictionary.md](01-data-dictionary.md)).
This table is the human-readable form of
`backend/app/optimization/assumptions.ScenarioParameters` — the two are
kept in sync; `ScenarioParameters.as_assumption_rows()` returns this same
table as structured data, attached to every optimization result so no
consumer of the output can mistake a scenario number for an observed one.

| Parameter | Default value | Unit | Source | Type | Rationale |
|---|---:|---|---|---|---|
| `lead_time_days` | 7 | days | Scenario | Assumption | The dataset has no supplier data of any kind. 7 days is a round, mid-range planning number chosen to fit within the M4 14-day forecast horizon — not a claim about any real supplier's actual lead time. |
| `review_period_days` | 7 | days | Scenario | Assumption | Used only by the periodic-review (order-up-to) calculation. Equal to `lead_time_days` for round-number simplicity — a weekly review cadence is a common planning convention, not a measured cycle. |
| `service_level_target` | 0.95 (95%) | fraction | Scenario | Assumption | A conventional "balanced" default from inventory-theory teaching material. Varied explicitly across the 3 named scenarios (98% / 95% / 90% — see below) — never presented as a real business requirement. |
| `holding_cost_weight` | 1.0 | unitless (scenario weight) | Scenario | Assumption | No monetary holding-cost data exists in the dataset. Used only as a normalized weight — see `docs/optimization-methodology.md` for exactly where it enters the math (the EOQ-style order-quantity formula and the newsvendor critical-fractile calculation). |
| `stockout_cost_weight` | 4.0 | unitless (scenario weight) | Scenario | Assumption | Set higher than `holding_cost_weight` to reflect the common planning convention that stockouts are usually judged costlier than excess stock — a directional assumption, not a measured cost ratio. |
| `ordering_cost_weight` | 1.0 | unitless (scenario weight) | Scenario | Assumption | Used only in the scenario EOQ-style order-quantity calculation. No ordering-cost data exists in the dataset. |
| `minimum_order_quantity` | 0.0 | units | Scenario | Assumption | No supplier minimum-order data exists. Defaults to no floor. |
| `maximum_order_quantity` | None (no ceiling) | units | Scenario | Assumption | No supplier/warehouse capacity data exists. |
| `shared_capacity_budget` | Derived per scenario (see below) | units (safety stock, summed across all 8 ATC classes) | Scenario | Assumption | A hypothetical shared warehouse/budget constraint for the cross-class LP allocation (`app.optimization.allocation_optimizer`). Never observed — the dataset has no warehouse-capacity field. |

## The 3 named scenarios

Every other assumption above is held fixed; only `service_level_target`
(and its downstream effect on `shared_capacity_budget`, see below) varies:

| Scenario | `service_level_target` | Rationale |
|---|---:|---|
| **Conservative** | 98% | Prioritizes stockout avoidance over inventory exposure — for a planner who weights the operational cost of a stockout heavily. |
| **Balanced** | 95% | This project's default; a conventional "reasonable" target used in inventory-planning teaching material absent other information. |
| **Lean** | 90% | Prioritizes minimizing inventory exposure over stockout avoidance — for a capital- or space-constrained planner, accepting more frequent (small) shortfalls. |

**How `shared_capacity_budget` is derived (per scenario, not itself a
free parameter):** for each scenario, every ATC class's *independent*
safety stock is computed at that scenario's `service_level_target` (as if
each class were planned in isolation, with no shared constraint), and
those 8 values are summed. That sum becomes the scenario's total capacity
budget — i.e. "what would an uncoordinated, everyone-gets-this-target
policy cost in total safety stock?" The cross-class LP
(`app.optimization.allocation_optimizer`) then re-allocates that SAME
total budget, so the baseline-vs-optimized comparison in
[optimization-insights.md](optimization-insights.md) is always apples to
apples: identical total inventory exposure, different allocation across
classes.

## What is genuinely observed (for contrast)

Everything the optimization engine treats as real, factual input comes
from earlier milestones, never invented here:

- Point forecasts and forecast-error (residual) uncertainty — from M4's
  already-selected, already-backtested model per ATC class
  (`app.forecasting`, consumed via `app.optimization.demand_input` —
  never rebuilt).
- Historical daily demand — from the canonical hourly fact table (M2/M3).
- Each class's contribution share (used to weight planning exposure in
  the LP objective — `app.optimization.allocation_optimizer.default_class_weights`)
  — from M3's `contribution_by_atc`.

No inventory, cost, or supplier value from this document is ever mixed
into those observed inputs — see
`tests/unit/optimization/test_data_integrity.py` for the executable proof
(scenario parameters are an immutable, frozen dataclass; every
optimization function is checked to leave its `DemandInput` input
byte-for-byte unmodified).
