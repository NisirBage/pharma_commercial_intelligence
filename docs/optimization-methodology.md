# Optimization Methodology

Implementation: `backend/app/optimization/`. Every number in this
document comes from `backend/scripts/run_m5_optimization.py`'s actual run
against the real dataset and the M4-selected models — reproducible by
re-running that script (after `backend/scripts/run_m4_backtest.py`, which
it depends on for the model registry).

## 1. Business problem

> Given expected demand and its uncertainty, what inventory/reorder
> policy would provide an appropriate balance between service protection
> and inventory exposure under explicitly defined planning assumptions?

This is a **scenario simulation**, not a real-world optimization — the
Kaggle dataset contains no inventory, cost, or supplier data (see
[planning-assumptions.md](planning-assumptions.md)). Every number this
engine produces is downstream of (a) M2's canonical demand data, (b) M4's
forecasts and their backtested uncertainty, and (c) explicit,
configurable, documented scenario assumptions — never a claim about a
real pharmacy's actual inventory situation.

## 2. Decision variables

Three, deliberately minimal (M5 Sec. 1: "choose only the variables
necessary"):

- **Safety stock** (buffer above expected lead-time demand).
- **Reorder point** (= expected lead-time demand + safety stock; also an
  order-up-to level for a periodic-review variant).
- **Recommended order quantity** (a scenario EOQ-style figure, secondary
  to the two above).

**Replenishment frequency was deliberately NOT treated as a decision
variable** — `review_period_days` is a fixed scenario input. Optimizing
over review cadence as well would require real ordering-cost/logistics
data this project doesn't have; treating it as fixed keeps the model
honest about what it can and can't determine from this dataset.

## 3. Two-layer problem structure — and which layer actually needs a solver

This is the central design decision of M5, and it came from actually
testing whether a solver was needed (see Section 7) rather than assuming
one was.

**Layer 1 — per-class safety stock / reorder point: deterministic,
closed-form, no solver.** Given a lead time and a service-level target,
the safety-stock formula (`app.optimization.safety_stock`) is a direct
calculation: `SS = z(service_level) * sigma_lead_time`. There is nothing
to search over — the answer is uniquely determined by the inputs. Using
OR-Tools here would be exactly the "keyword-driven" use the M5
instructions warn against.

**Layer 2 — cross-class, capacity-constrained allocation: a genuine LP.**
When multiple ATC classes compete for a SHARED, limited capacity budget
(`app.optimization.allocation_optimizer`), deciding how much each class
gets to minimize total risk-weighted expected shortage is a real
constrained resource-allocation problem — see Section 7.

## 4. Objective function

**Layer 2's objective** (the only one requiring optimization):

```
minimize   sum_i ( stockout_cost_weight * class_weight_i * ExpectedShortage_i(SS_i) )
subject to sum_i ( SS_i ) <= capacity_budget
           SS_i in [0, z_max * sigma_lead_time_i]  for every class i
```

- `ExpectedShortage_i(SS_i) = sigma_lead_time_i * L(SS_i / sigma_lead_time_i)`,
  where `L(z) = phi(z) - z*(1 - Phi(z))` is the standard unit-normal loss
  function (Hadley & Whitin) — expected units short per replenishment
  cycle.
- `class_weight_i` defaults to class i's average forecast daily demand,
  normalized to a mean of 1.0 across classes — i.e. "a stockout unit in a
  higher-volume class counts for more." **This weighting is not
  cosmetic — see Section 7.1: an unweighted objective makes the entire
  optimization mathematically pointless.**
- `stockout_cost_weight` is a global scenario scalar (default 4.0) that,
  for this constrained formulation, does not change the optimal
  *allocation* (scaling every term by the same constant doesn't change
  the argmin) — it only matters relative to `holding_cost_weight` in the
  separate, per-class newsvendor calculation (Section 4.1).

**A separate, per-class objective** exists for the "cost-based" framing
requested in M5 Sec. 1 (an alternative to specifying a service-level
target directly): the classic **newsvendor critical fractile**,
`z* = Phi^-1(Cu / (Cu + Co))` where `Cu` = `stockout_cost_weight`, `Co` =
`holding_cost_weight` (`app.optimization.safety_stock.newsvendor_critical_fractile_z`).
This lets a user specify cost *weights* instead of a target service
level and get an implied service level back — used in the
`stockout_cost_weight` sensitivity sweep (Section 12).

## 5. Constraints

- `sum_i(SS_i) <= capacity_budget` (Layer 2 LP — hard constraint).
- `0 <= SS_i <= z_max * sigma_lead_time_i` per class (Layer 2 LP — bounds
  the finite piecewise-linear approximation grid; see Section 7.2).
- `lead_time_days + review_period_days <= 14` (the M4 forecast horizon) —
  enforced by raising, never silently truncating or extrapolating beyond
  the forecast M4 actually produced.
- `minimum_order_quantity <= Q <= maximum_order_quantity` on the scenario
  order-quantity figure.

## 6. Assumptions

Full table: [planning-assumptions.md](planning-assumptions.md).

## 7. Why OR-Tools, and how the LP is actually formulated

### 7.1 The optimization had to be redesigned once — a real finding, not hidden

The first version of Layer 2 minimized an **unweighted** sum of expected
shortage. A synthetic two-class sanity check
(`tests/unit/optimization/test_allocation_optimizer.py`) revealed this
formulation cannot possibly beat the naive baseline: the derivative of
`ExpectedShortage_i(SS_i)` with respect to `SS_i` is `-(1 - Phi(z_i))`,
which is **independent of `sigma_lead_time_i`**. That means the
unweighted objective's true mathematical optimum is to give *every*
class the *same* implied service level — exactly what the naive "same
target for everyone" baseline already does. There was no optimization
problem to solve. Weighting each class's shortage by its own planning
exposure (Section 4) breaks this degeneracy: the optimum then gives
higher-weight classes a higher implied service level, which the
uniform-target baseline cannot replicate — and this is empirically
confirmed in Section 8 below.

### 7.2 LP formulation (the version actually used)

`ExpectedShortage_i(SS_i)` is convex and strictly decreasing in `SS_i`.
Reformulated as an LP via the standard convex piecewise-linear trick:
precompute `(SS, ExpectedShortage)` at a dense grid of z-values (step
0.1, `z` from 0 to 3.5 — `app.optimization.allocation_optimizer._LP_Z_GRID`),
then let each class choose a *continuous convex combination* of grid
points (one non-negative weight variable per grid point per class,
summing to 1). Because the underlying function is convex and the LP
*minimizes* a linear combination of it, the LP relaxation is exact — no
integer/SOS2 variables needed.

**A coarser 6-point grid (the named service-level tiers 50/80/90/95/98/99%)
was tried first and found NOT fine enough** — interpolation error in the
steep near-`z=0` region of the loss function was large enough that the
"optimized" solution could come out *slightly worse* than the baseline on
the exact metric, which a correct LP optimum can never do (the baseline
is always a feasible point in the LP's own feasible region). The dense
36-point grid closes this gap; `tests/unit/optimization/test_allocation_optimizer.py::test_optimized_allocation_beats_or_matches_baseline_on_weighted_shortage`
is the regression test that would catch this class of error again.

**Known boundary condition:** the grid caps at `z=3.5`
(~99.98% implied service level). A capacity budget far exceeding what any
of this project's 3 scenarios would ever derive (Section 9) could, in
principle, let an unconstrained baseline "outperform" the capped LP by
scaling past that ceiling — documented, not hidden, and irrelevant at the
realistic budget scale these scenarios actually use.

Solved with **OR-Tools' GLOP linear solver** (`pywraplp`) — a genuine LP.

## 8. Baseline vs. optimized policy — the mandatory comparison

**Baseline**: every class gets the SAME service-level target (the
scenario's own target), then every class's resulting safety stock is
scaled proportionally so the total exactly fits the shared capacity
budget. No solver; simple, defensible, and — crucially — unweighted by
volume (Section 7.1).

**Optimized**: the LP above, using the SAME total capacity budget.

**Real results, all 3 scenarios** (total *weighted* expected shortage,
lower is better, identical total inventory exposure in both policies):

| Scenario | Capacity budget | Baseline weighted shortage | Optimized weighted shortage | Improvement |
|---|---:|---:|---:|---:|
| Conservative (98%) | 129.43 units | 0.9265 | 0.4871 | **47.4%** |
| Balanced (95%) | 103.66 units | 2.6361 | 1.3544 | **48.6%** |
| Lean (90%) | 80.76 units | 5.9734 | 2.9918 | **49.9%** |

The optimized policy reduces total (volume-weighted) expected shortage by
roughly **47-50%** relative to the naive equal-target baseline, for
*exactly the same total inventory exposure*, in every scenario tested.
See [optimization-insights.md](optimization-insights.md) for what this
means (and doesn't mean) operationally, and for the disclosed trade-off
it makes (low-volume classes are deprioritized to achieve it).

## 9. Scenario design

See [planning-assumptions.md](planning-assumptions.md) for the 3
scenarios' definitions and rationale, and how each one's capacity budget
is derived from its own service-level target.

## 10. Uncertainty treatment

Full derivation: `app.optimization.safety_stock` module docstring.
Summary: safety stock uses the standard deviation of the **forecast
error** (M4 backtest residuals), never raw historical demand variance
(which would double-count what the forecast already explains). Three
estimators are computed and reported for every class:

1. **Additive per-step variance** (primary) —
   `sigma_L = sqrt(sum_{h=1..L} std_h^2)`, using each horizon step's
   *actual* observed residual std from M4's 6 backtest folds.
2. **Flat `sqrt(L)` scaling** (cross-check) — the textbook shortcut,
   assumes i.i.d. errors across days. Not primary, because M4 found
   significant residual autocorrelation for several classes.
3. **Empirical fold-level cumulative error** (small-sample cross-check) —
   the std of the 6 folds' own L-day cumulative error. Captures
   autocorrelation directly, at the cost of only 6 data points.

## 11. Validation

All 8 ATC classes pass all 3 monotonicity sanity checks
(`app.optimization.validation`, M5 Sec. 17) against the real M4-derived
uncertainty: increasing service level never decreases safety stock;
increasing lead time never decreases the reorder point; increasing
demand uncertainty never decreases safety stock. See
[optimization-insights.md](optimization-insights.md) for the full
per-class results.

## 12. Sensitivity analysis

See [optimization-insights.md](optimization-insights.md) for the full
per-class sensitivity results (N02BE, N05C, R03) and their elasticities.

## Performance notes

Full run (8 ATC classes × 3 scenarios, including the LP solve and a
sensitivity sweep on 3 classes): **7.4s** — trivial at this scale. If this
grew to hundreds/thousands of SKUs sharing one capacity constraint:

- The LP's variable count is `O(n_classes * n_grid_points)` — at 36 grid
  points, thousands of SKUs would still solve in well under a second with
  GLOP; this formulation scales linearly and comfortably.
- **`app.optimization.demand_input`** currently re-runs a full M4
  backtest per class to recover per-step residuals — fine at 8 classes
  (~7s total), but at scale this should be replaced by persisting
  per-fold residuals directly from the M4 pipeline (a schema change: a
  `fact_backtest_residual` table) rather than recomputing them.
- A shared capacity constraint spanning e.g. multiple warehouses/regions
  would need one constraint row per shared resource, not a fundamental
  reformulation — the convex piecewise-linear LP trick generalizes
  directly to multiple simultaneous linear constraints.
