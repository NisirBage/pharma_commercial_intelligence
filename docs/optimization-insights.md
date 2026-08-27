# Optimization Insights — M5 Findings

Every number below is from `backend/scripts/run_m5_optimization.py`'s
actual run against the real dataset and the M4-selected models. Framework
(consistent with M3/M4):

- **Observed** — a fact directly readable from the data/prior milestones.
- **Analytical finding** — something calculated from the data.
- **Scenario result** — a number produced under explicit, labeled
  planning assumptions ([planning-assumptions.md](planning-assumptions.md)).
- **Planning implication** — what a supply planner might reasonably do.
- **Limitation** — what cannot be inferred from the dataset.

**This entire document describes a scenario simulation, not a real-world
impact evaluation.** No claim below asserts actual reduced stockouts,
inventory cost savings, or improved service level for any real
pharmacy — the dataset contains no inventory, cost, or supplier data that
could measure any of those (see [data-gap-analysis.md](data-gap-analysis.md)).

---

## 1. The optimized allocation policy vs. the naive baseline

**Scenario result:** For the SAME total inventory exposure (capacity
budget), reallocating that budget by volume-weighted expected-shortage
minimization (the LP) rather than giving every class an equal target
reduces total weighted expected shortage by **47.4% (Conservative), 48.6%
(Balanced), and 49.9% (Lean)** — consistently around **half**, across all
3 scenarios tested.

**Analytical finding:** This is not a coincidence of the specific
scenario chosen — Section 7.1 of
[optimization-methodology.md](optimization-methodology.md) shows
analytically why an *unweighted* version of this same optimization would
have made NO improvement possible (its mathematical optimum equals the
baseline exactly). The ~48% figure is the real, measurable value of
(a) weighting shortage by volume/planning-exposure and (b) coordinating
allocation across classes instead of treating each independently.

**Planning implication:** *If* a shared, limited inventory budget is a
real constraint (which this dataset cannot confirm), coordinating
allocation across drug classes by volume-weighted risk is worth roughly
twice the shortage-risk reduction of an "equal treatment" policy, at zero
additional total inventory cost.

**Limitation:** "Expected shortage" here is a statistical quantity (units
short per replenishment cycle, from the normal-loss formula), not a
dollar figure, and not validated against any real stockout record — this
dataset has none.

---

## 2. N02BE (high-volume, high planning exposure)

**Observed:** N02BE is ~49.4% of total observed demand (M3).

**Scenario result:** Under every scenario, the optimizer gives N02BE a
HIGHER implied service level than its scenario's own uniform target:
**99.53% (vs. 98% target) in Conservative, 98.93% (vs. 95%) in Balanced,
97.72% (vs. 90%) in Lean.** Its safety stock ranges 45.2–58.7 units and
reorder point 327.6–341.2 units depending on scenario.

**Planning implication (per M5's own framing, applied deliberately):**
N02BE is treated as high PLANNING EXPOSURE, not "high risk" — its own
forecast-error volatility is the LOWEST of any class (M3 CV=0.52; M4 test
WAPE 25.1%, mid-pack among all 8 classes). The optimizer prioritizes it
not because it's unusually uncertain, but because its sheer volume means
a given percentage shortfall translates into the largest absolute unit
gap of any class — exactly the volume-weighting mechanism in
[optimization-methodology.md](optimization-methodology.md) Section 4.

**Limitation:** This is a scenario weighting choice (volume-proportional
"exposure"), not a real cost-based prioritization — a real pharmacy might
weight clinical criticality, not just volume.

---

## 3. N05C (highest CV, lowest volume) — and the trade-off it reveals

**Observed:** N05C has the highest historical CV of any class (M3: 1.84)
but only ~1% of total demand; M4 found it essentially unforecastable
(test WAPE 100%).

**Scenario result:** N05C's ABSOLUTE safety stock is small in every
scenario (0.36–2.33 units) — consistent with M3's volume finding, not the
CV finding. But its implied service level under the shared-budget
optimizer is markedly LOWER than its scenario target: **90.3% (vs. 98%)
in Conservative, 78.8% (vs. 95%) in Balanced, and just 57.9% (vs. 90%) in
Lean** — the sharpest gap of any class.

**Analytical finding — the disclosed trade-off:** This is the direct,
honest consequence of volume-weighting (Section 1): under a shared,
limited budget, the LP deliberately sacrifices low-volume classes'
service level to protect high-volume classes' more (in absolute-unit
terms). This is not a flaw to hide — it is exactly what a
volume-weighted objective is designed to do, and it should be stated
plainly to anyone using this policy.

**Planning implication:** N05C's high CV does NOT, by itself, justify
large safety stock — its absolute unit exposure is small regardless of
scenario. But a planner who considers N05C clinically important
independent of its volume (information this dataset cannot provide)
should NOT adopt the volume-weighted allocation as-is for that class —
`app.optimization.allocation_optimizer.optimize_allocation` accepts a
`class_weights` override precisely so a planner with such information
could substitute their own weighting.

**Limitation:** M4 found N05C's forecast itself unreliable (test WAPE
100%) — any safety-stock figure for this class inherits that unreliable
input and should be treated as low-confidence regardless of the
allocation policy.

---

## 4. R03 (confirmed historical growth, but no forecasting edge)

**Observed:** M3 found a statistically significant historical GROWTH
trend for R03. M4 found every candidate forecasting model performed
WORSE than the simple baseline for R03 (kept `moving_average_14`).

**Scenario result:** R03's safety stock ranges 13.0–22.5 units and
reorder point 53.3–62.7 units across scenarios, based entirely on its M4
forecast and forecast-error uncertainty — **not** on an extrapolation of
the M3 growth trend. Its lead-time-uncertainty sensitivity (elasticity
0.22, Section 6 below) is the highest of the 3 classes examined in
detail, consistent with M3's finding that R03 has the 2nd-highest
volatility of any class (CV=1.17).

**Planning implication:** A confirmed historical growth trend is
deliberately NOT used to inflate R03's inventory policy beyond what the
current forecast + uncertainty already implies (per M5 Sec. 10's explicit
instruction) — M4 already showed the trend isn't exploitable for
forecasting at a 14-day horizon, so treating it as an inventory-policy
input on top of the forecast would be double-counting a signal the
forecast couldn't actually use.

**Limitation:** If R03's real-world growth continues but the forecasting
model doesn't capture it (a real, open possibility M4 already flagged),
this policy will systematically under-provision for R03 over time — a
risk worth monitoring operationally, not something this static scenario
run can detect on its own.

---

## 5. Sensitivity analysis: which assumptions move the recommendation most?

Endpoint-to-endpoint elasticity (% change in safety stock per % change in
the parameter), computed for N02BE, N05C, and R03:

| Parameter | N02BE | N05C | R03 | Interpretation |
|---|---:|---:|---:|---|
| `service_level_target` | 7.43 | 7.43 | 7.43 | **Identical across every class** — a mathematical property of this formulation (SS = z·sigma; sigma cancels out of the elasticity), not a coincidence. Service level is, by a wide margin, the single most sensitive assumption in the whole model. |
| `demand_uncertainty_scale` | 1.00 | 1.00 | 1.00 | Also exactly 1.0 for every class by construction (SS is exactly linear in this scale factor) — a direct, proportional pass-through. |
| `lead_time_days` | 0.18 | undefined* | 0.22 | The one genuinely CLASS-SPECIFIC sensitivity, since it depends on each class's own horizon-step error shape (M4). |
| `stockout_cost_weight` | undefined* | undefined* | undefined* | Undefined at the low end of the tested range because the newsvendor critical fractile clips to a 0 safety stock below a 1:1 cost ratio, making the endpoint-to-endpoint % change undefined — not a data problem. |

*"Undefined" = the elasticity's percentage-change denominator was exactly
zero at one endpoint (documented behavior of `app.optimization.sensitivity.elasticity`,
not a missing result).

**Analytical finding:** `service_level_target` dominates every other
assumption's effect on the recommendation by roughly an order of
magnitude. This is the single assumption worth the most scrutiny/
discussion with a real business stakeholder before trusting any output
of this engine.

**Limitation:** Elasticity here measures LOCAL sensitivity around the
tested grid, not a global statement about all possible parameter
combinations.

---

## 6. Validation

All 3 monotonicity sanity checks (M5 Sec. 17) pass for **all 8 ATC
classes**, using the real M4-derived uncertainty: increasing
service-level target never decreased safety stock; increasing lead time
never decreased the reorder point; increasing demand uncertainty never
decreased safety stock. No class violated any check — see
`backend/data/reports/m5_optimization_results.json` for the full
per-class detail.

---

## What this milestone does NOT claim

- No real inventory cost savings, stockout reduction, or service-level
  improvement for any actual pharmacy — no such data exists in this
  dataset.
- No claim that the ~48% shortage-reduction figure would hold under a
  real cost structure, real supplier constraints, or real demand
  patterns different from what M2–M4 observed.
- No claim that volume is the "correct" way to weight planning exposure
  — it is a documented, overridable scenario choice
  ([planning-assumptions.md](planning-assumptions.md)), not a discovered
  business truth.
- No claim about causal drivers of any class's demand, trend, or
  volatility — consistent with M3/M4's same discipline.
