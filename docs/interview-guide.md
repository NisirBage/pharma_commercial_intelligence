# Interview Guide

Prep notes for defending this project's technical and commercial
decisions in an interview. Organized by milestone; this document grows as
later milestones are added. Every answer below should be backed by an
actual file/number in this repo — if you can't point to where a claim
comes from, don't say it in the interview either.

---

## M5 — Optimization

### Why did you use optimization rather than ML?

Because the problem is a genuine constrained-resource-allocation
question, not a prediction question — M4 already handles prediction.
Given a forecast and its uncertainty, deciding how to allocate a *shared,
limited* inventory budget across 8 competing ATC classes to minimize
total risk is a textbook operations-research problem (a convex
resource-allocation LP), not something an ML model predicts. See
[optimization-methodology.md](optimization-methodology.md) Sections 2-3
for the two-layer structure: the per-class safety-stock/reorder-point
calculation is a deterministic formula (no ML, no optimization needed at
all — just applying a known formula to M4's outputs); the cross-class
allocation is where a real optimization problem exists.

### Why OR-Tools?

Only after confirming a solver was actually needed (see
[optimization-methodology.md](optimization-methodology.md) Section 3) —
the per-class calculation deliberately does NOT use OR-Tools, because
it's closed-form. For the cross-class allocation, OR-Tools' GLOP linear
solver is the right-sized tool: the problem, after a standard convex
piecewise-linear reformulation, is a genuine LP (continuous variables,
linear constraints, convex objective) — no need for a MIP solver, no
need for a heavier NLP solver, and no fabricated justification for a
bigger tool than the problem calls for.

### What is the objective function?

`minimize sum_i(stockout_cost_weight * class_weight_i * ExpectedShortage_i(SS_i))`
subject to `sum_i(SS_i) <= capacity_budget`. Full derivation, including
why an *unweighted* version of this objective is mathematically
degenerate (its optimum equals the naive baseline exactly — a real
finding from testing, not a hypothetical), in
[optimization-methodology.md](optimization-methodology.md) Sections 4 and
7.1.

### What are the decision variables?

Safety stock per ATC class (continuous). Reorder point and recommended
order quantity are derived from it, not independently optimized.
Replenishment frequency (`review_period_days`) was deliberately left as a
fixed scenario input, not a decision variable — see
[optimization-methodology.md](optimization-methodology.md) Section 2 for
why (no real ordering-cost/logistics data to optimize it against).

### What are the constraints?

A single hard linear constraint: total safety stock across all 8 classes
cannot exceed the shared capacity budget. Each class's safety stock is
also implicitly bounded by the LP's finite approximation grid (z up to
3.5, ~99.98% implied service level) — a documented, inconsequential
boundary condition at the budget scale this project's scenarios actually
use.

### Where did your lead-time assumptions come from?

Nowhere real — `lead_time_days=7` is explicitly a scenario assumption
(see [planning-assumptions.md](planning-assumptions.md)), chosen because
it's a round number that fits inside M4's 14-day forecast horizon, not
because it reflects any actual supplier. This is stated in the codebase
itself (`app/optimization/assumptions.py`'s docstrings), not just in
documentation — every `ScenarioParameters` field's docstring says exactly
this.

### Why didn't you claim actual inventory savings?

Because the dataset has no inventory, cost, or supplier data to measure
savings against — the ~48% "improvement" figure in
[optimization-insights.md](optimization-insights.md) is a reduction in a
*simulated, unitless, volume-weighted expected-shortage statistic*
comparing two policies under the SAME hypothetical budget, not a dollar
figure and not validated against any real outcome. Every document in this
milestone (methodology, insights, assumptions) states this explicitly and
repeatedly, per the project's own restriction against fabricating
business impact.

### How would this work with real pharmaceutical data?

See [data-gap-analysis.md](data-gap-analysis.md) for the full breakdown.
Short version: real demand data (censoring-corrected, SKU-grain, channel-
split), real current inventory positions (to turn policy parameters into
actual order triggers), real supplier lead times and costs (to replace
every scenario assumption with an observed value), and — if multi-site —
real warehouse/region data (to extend the single shared-budget LP into a
proper network model).

### What additional data would you request from a client?

In priority order: (1) current inventory positions — without this,
nothing here is an actionable order recommendation, only a policy
parameter; (2) real lead times and any known supplier constraints
(MOQs, capacity); (3) historical stockout records, both to validate this
project's expected-shortage estimates and to correct for demand
censoring in the historical sales data; (4) real cost data (holding,
ordering, stockout) to replace the unitless scenario weights with
dollar-denominated ones.

### How would you handle multiple warehouses?

Not currently supported — the dataset has no location field at all (M1
couldn't even confirm single-site vs. aggregated data). The LP
formulation generalizes cleanly in principle: one capacity constraint per
warehouse instead of one global constraint, and potentially a network-
flow layer if inventory can be transferred between sites — but this is a
materially larger reformulation, not a parameter change, and would need
real location-level demand and capacity data first (see
[data-gap-analysis.md](data-gap-analysis.md)).

### How would you incorporate supplier constraints?

Minimum order quantities and maximum order ceilings already have
placeholder scenario parameters
(`minimum_order_quantity`/`maximum_order_quantity` in
[planning-assumptions.md](planning-assumptions.md)) but are not currently
tied to any real supplier data. Supplier fulfillment CAPACITY (as
distinct from the shared inventory budget already modeled) would need a
new constraint added to the LP, keyed by supplier rather than by ATC
class — straightforward to add once real supplier-capacity data exists.

### How would you handle stockouts contaminating historical demand?

This is a real, currently-unaddressed limitation — every quantity in M2
through M5 treats the Kaggle dataset's recorded sales as true demand.
If a historical stockout occurred, recorded sales for that period
understate actual demand, and the M4 forecast (trained on that data)
would inherit a downward bias. Without stockout records, this censoring
can't be detected or corrected retroactively — see
[data-gap-analysis.md](data-gap-analysis.md), "Demand" section, for what
data would be needed to fix this (and it would require rebuilding the
M4 forecasts on corrected series, not just patching M5's outputs).

### How would you incorporate promotions or product launches?

Promotions: M3's anomaly detection already flags statistically unusual
demand spikes, but explicitly could not and did not attribute any of them
to a promotion — no promotional calendar exists in the dataset. With one,
a promotional-lift term could be added to the forecast (M4) so its effect
doesn't get miscounted as "trend" or "seasonality" or an unexplained
anomaly. Launches: M4's forecasting requires a minimum ~180-day training
window per class — a genuinely new product has no history at all, so this
pipeline would fail outright for it; a real launch-forecasting approach
needs an entirely different method (analogous-product matching, judgmental
overrides), not an extension of what's built here.

### What happens if forecast uncertainty increases?

Directly and transparently: safety stock scales up (validated
monotonically — [optimization-insights.md](optimization-insights.md)
Section 6 — for all 8 classes, real data). The sensitivity analysis
(Section 5 of that document) shows the elasticity of safety stock with
respect to the demand-uncertainty scale factor is exactly 1.0 for every
class — a direct, proportional, mathematically exact pass-through, not
an approximation.

### Why is N02BE prioritized?

Because it's ~49.4% of total observed demand (M3) — the optimizer's
objective weights each class's expected shortage by its own volume
(planning exposure), so a shortfall in the highest-volume class matters
most in absolute-unit terms. It is explicitly NOT prioritized because of
elevated risk — its own forecast-error volatility is the LOWEST of any
class (M3 CV=0.52) — see
[optimization-insights.md](optimization-insights.md) Section 2 and the
project's explicit instruction (M5 Sec. 10) not to conflate volume with
risk.

### Why isn't high CV alone sufficient to prioritize N05C?

Because CV is a RELATIVE measure (std/mean) — a class that's 1% of total
demand can have a very high CV while its ABSOLUTE unit exposure stays
small (N05C's safety stock: 0.36-2.33 units across scenarios, the
smallest of any class). The recommendation engine
(`app.optimization.recommendations`) explicitly checks absolute safety-
stock units for N05C before drawing any conclusion, rather than reacting
to the CV number alone — see
[optimization-insights.md](optimization-insights.md) Section 3, which
also discloses the trade-off this creates (N05C's service level under
the shared-budget optimizer drops well below its scenario target,
because low absolute exposure means it doesn't compete well for a
volume-weighted shared budget — stated plainly, not hidden).
