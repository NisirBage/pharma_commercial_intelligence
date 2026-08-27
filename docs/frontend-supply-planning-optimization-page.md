# Frontend: Supply Planning & Optimization Page

`frontend/src/pages/SupplyPlanning/` — M7.7. A decision-support surface
around M5's cross-class safety-stock LP. See
`docs/frontend-design-system.md` for the design system,
`docs/optimization-methodology.md` and `docs/planning-assumptions.md`
for the underlying M5 methodology this page presents (read in full
during this milestone's discovery pass, not assumed).

## Purpose and business interpretation

This is a **scenario simulation**, not a claim about real inventory —
the Kaggle dataset contains no inventory, cost, or supplier data
(`docs/planning-assumptions.md`). The page shows how a *hypothetical*
shared safety-stock budget would be best allocated across the 8 ATC
classes to minimize total volume-weighted expected shortage, under
explicit, documented planning assumptions. The page's own header
states this plainly rather than letting a reader infer it.

**API-provided facts vs. frontend-derived values vs. UI presentation
decisions**, made explicit throughout:
- **API-provided facts**: every number in the Optimization Summary,
  Recommended Plan, and Sensitivity sections — capacity budget,
  improvement %, per-class safety stock/reorder point/order quantity,
  solver status, sensitivity points, elasticity.
- **Frontend-derived values**: "Avg Forecast Demand"-style KPIs don't
  exist on this page (unlike Forecasting's) — the only derived figures
  here are the sensitivity chart's baseline reference values for
  `demand_uncertainty_scale` (1.0, by definition — see "Sensitivity
  semantics" below) and `stockout_cost_weight` (4.0, the fixed value
  all 3 scenarios share per `planning-assumptions.md`'s table) —
  neither is an API field, both are documented in code comments and
  here.
- **UI presentation decisions**: which fields to show, table column
  order, the service-level-as-percent input convention (see below),
  the "stale result" banner wording.

## Page architecture

One page, no tabs — Scenario/Planning Controls → Optimization Summary
→ Recommended Plan → Sensitivity Analysis, matching the existing
single-route convention (`/planning`, unchanged). Sensitivity is a
GET, auto-fetched once an ATC class and parameter are chosen (both
always have a value — no separate "run" click); the optimization run
is a POST, **never** auto-fired — only `handleRun()` calls
`runMutation.mutate(...)`, exclusively from the Run button's `onClick`.

## APIs consumed

| Hook | Endpoint | Method |
|---|---|---|
| `useOptimizationScenarios()` | `/api/v1/optimization/scenarios` | GET |
| `useOptimizationSensitivity({atcClass, scenario, parameter})` | `/api/v1/optimization/sensitivity` | GET |
| `useOptimizationRun()` | `/api/v1/optimization/run` | POST (mutation) |

All three hooks, and the underlying `api/optimization.ts` module,
already existed from M7.2 scaffolding and needed no changes — the
run hook was already a `useMutation` with `isPending` driving
button-disable, exactly this milestone's requirement.

## Scenario semantics

A scenario is a named bundle (conservative/balanced/lean) that varies
**only** `service_level_target` (98%/95%/90%) — every other assumption
held fixed, so any difference in results is attributable to the
service-level choice alone. Scenarios are loaded from the API, never
hardcoded; the Select's options and each scenario's rationale text
(shown below the controls) are the API's own words.

## Optimization request semantics

`OptimizationRunRequest` has exactly three fields — `scenario`
(default `balanced`), `service_level` (optional override, `0 < x < 1`),
`lead_time_days` (optional override, `0-14`) — verified by reading
`backend/app/schemas/optimization.py` directly. **No other planning
input exists on this endpoint**; the form exposes exactly these three
controls and nothing else (no cost weights, no order-quantity bounds —
those are fixed scenario constants, not request fields).

**Units convention**: `service_level`/`service_level_target` are true
0–1 fractions (Pydantic `gt=0, lt=1`), a genuinely different
convention from every other percent-shaped field this app has shown
(`contribution_pct`, `wape`, `improvement_pct` are already 0–100). The
new `formatFraction` helper in `lib/format.ts` exists specifically to
avoid silently conflating the two. The service-level **input**,
however, is typed as a whole percent (1–99) for usability — a user
types "92" meaning 92%, and the form divides by 100 before sending
`0.92` to the API; this is a UI presentation decision, not a backend
convention.

## Sensitivity semantics

A sweep of ONE of 4 parameters for ONE ATC class, holding the current
scenario's other values fixed: `lead_time_days`, `service_level_target`,
`demand_uncertainty_scale` (a multiplier on the forecast-error std —
1.0 is unscaled/baseline by definition), or `stockout_cost_weight` (a
newsvendor cost-ratio weight). Each point returns `{value, safety_stock,
reorder_point}`; `elasticity` is the API's own endpoint-to-endpoint
%-change-in-safety-stock per %-change-in-parameter summary — never
computed client-side.

The chart identifies "Current Baseline" (a `ReferenceLine` + a
`MetricCard`) using: the currently-selected scenario's own
`service_level_target`/`lead_time_days` for those two parameters (real
API-sourced form state), or the two frontend-derived constants above
for the other two. Chart x-axis ticks are pinned to the actual swept
grid values (`ticks={data.points.map(p => p.value)}`) rather than
Recharts' default evenly-spaced numeric ticks — found necessary during
real-backend verification (the real 5-point service-level grid
0.8/0.9/0.95/0.98/0.99 doesn't sit on "nice" round tick positions).

## Result interpretation

**There is no per-class baseline breakdown in the API response** —
confirmed by reading `app/optimization/outputs.py`'s own docstring
("uses the OPTIMIZED (LP) allocation's per-class safety stock/reorder
point as the 'official' recommended policy") and
`AllocationPolicySchema`'s `extra="ignore"` (which deliberately drops
the domain layer's per-class baseline detail). This directly shapes
the UI:
- **Recommended Plan** (`atc_results`) shows only the **optimized**
  per-class figures — safety stock, reorder point, recommended order
  quantity, expected shortage, and the class's *implied* service level
  (which varies per class after reallocation — real data shows this
  ranging from ~76% to ~99% across classes for the balanced scenario,
  the documented "low-volume classes deprioritized" trade-off). There
  is intentionally **no "change"/"current quantity" column** — no such
  comparison data exists per row, and no current/observed inventory
  exists in the dataset at all (`planning-assumptions.md`).
- **Optimization Summary** is the only place a baseline-vs-optimized
  comparison exists — `improvement_pct` and the two `allocation_*`
  aggregate totals.
- **Infeasibility is an HTTP 422 error** (`code:
  "optimization_infeasible"`), not a 200 response with a status field
  — `OptimizationSummary` detects this via `error instanceof ApiError
  && error.code === "optimization_infeasible"` and shows a distinct
  "No feasible allocation found" panel with the API's own explanation,
  never a generic error and never calling an infeasible plan a
  recommendation.
- The `assumptions[]` table is rendered verbatim — parameter, value,
  unit, source, type — the API's own self-documenting record of every
  scenario constant that fed the run.

## Loading / error / empty states

Every independent operation (scenarios GET, sensitivity GET, run POST)
has its own `Skeleton`/`ErrorState`-with-retry/`EmptyState`. Before any
run, `OptimizationSummary` shows a single `EmptyState` explaining what
to do next. While a run is pending, a `role="status"` banner says so
explicitly — and says whether the figures still visible are from the
previous run.

## State management

Deliberately four separate pieces of state (M7.7 Sec. 8), NOT the
naive "just read `mutation.data`" approach:
1. **Current configuration** — local `useState` for
   scenario/serviceLevelPct/leadTimeDays.
2. **Last successful result** — `lastSuccess`, a `useState` set only
   inside `onSuccess`. **This was a real bug found by this milestone's
   own test suite**: `useMutation`'s `data` field does not reliably
   survive a *subsequent failed* call in this app's TanStack Query
   setup — a test asserting "a failed run does not overwrite a
   previous successful result" failed against the initial
   `runMutation.data`-based implementation, proving the assumption
   wrong. Fixed by tracking `lastSuccess` explicitly, decoupled from
   the mutation's own internal state.
3. **Running state** — `runMutation.isPending`.
4. **Error state** — `runMutation.isError`/`.error`.

`isStale` compares the form's current values against
`lastSuccess.body` (not `runMutation.variables`, which would
reflect the last *attempted* — possibly failed — configuration) to
flag, without hiding, a result that no longer matches what's on
screen.

## Accessibility

Semantic `<section aria-labelledby>` per section; every form control
labeled (`Select`, and the new page-local `NumberField`, which mirrors
`Select`'s exact `aria-describedby`/`aria-invalid` wiring); validation
errors are `role="alert"` and associated via `aria-describedby`;
`accessibilityLayer` on the sensitivity chart; `ChartLegend` for
safety-stock/reorder-point series; solver status and implied service
level are always paired with text, never color-only; accessible
`Table`s for both the recommendation and the sensitivity sweep, so
neither is chart-only.

## Performance

Response sizes are small at this dataset's scale — 8 ATC classes, a
5-6-point sensitivity sweep, ~9 assumption rows. No display cap was
needed anywhere on this page (contrast Demand Intelligence's
1,048-row anomalies response, or the historical-series slicing on
Forecasting). The 14-day per-class forecast array embedded in each
`atc_results` entry is not rendered here (Forecasting already owns
that view) — the Recommended Plan table shows only the planning
outputs.

## Real-browser verification

Started the real backend + frontend and verified: all 3 scenarios'
`capacity_budget`/`improvement_pct` match `docs/optimization-methodology.md`'s
published table exactly (Balanced 103.66 units/48.6%, Lean 80.76
units/49.9%); a real POST run's full 8-class response, including the
documented service-level trade-off (76–99% implied service level
across classes); a real sensitivity sweep (N02BE, service_level_target,
elasticity 7.43); client-side validation correctly blocking an
out-of-range input before it reaches the network; the real backend's
own validation-error shape for an out-of-range value sent directly;
and the network log, confirming exactly one POST per Run click (plus
its CORS preflight OPTIONS — not a duplicate) with no accidental POST
on page load.

## Bugs found and fixed during integration

1. **Assumptions table showing `1.0` instead of `0.95`** for
   `service_level_target`. Root cause: `formatDecimal` (built for
   demand-scale figures, forces exactly 1 decimal) was applied to a
   generic mixed-scale assumptions column (which also contains 7,
   1.0, 4.0, 0.0 for other rows) — `(0.95).toFixed(1)` rounds to
   `"1.0"`. Fixed by adding `formatNumber` to `lib/format.ts`, a
   genuinely generic "natural precision, capped at 3 decimals"
   formatter for exactly this "value convention isn't known ahead of
   time" case, rather than a one-off fix.
2. **Sensitivity chart's numeric x-axis ticks didn't align with the
   actual swept values** (Recharts' default evenly-spaced ticks vs.
   the real irregular grid). Fixed by pinning `ticks` to the response's
   own point values.
3. The two state-management bugs described under "State management"
   above, found by the test suite before the real-browser step.

Discovered but not "fixed" (per instructions — never patch the
backend to match frontend assumptions, and never overwrite a mock to
match reality): the MSW test fixture's `allocation_baseline.solver_status`
is `"n/a (closed form)"`, while the real backend returns `"heuristic
(no solver)"` — a stale/inaccurate mock value from earlier scaffolding,
not a contract problem (the schema field is a plain `str`, and the
frontend's `getSolverStatusDisplay` mapping gracefully falls back to
showing the raw string for either value). Left as-is; noted here for
visibility.

## Limitations

- The service-level and lead-time override inputs use a practical
  1–99% / 0–14-day range rather than the backend's exact open interval
  `(0, 1)` for service level — a deliberate, documented UI
  simplification, not a mismatch a real user would hit in practice.
- Two of the four sensitivity baseline reference values
  (`demand_uncertainty_scale`, `stockout_cost_weight`) are frontend
  constants derived from reading `planning-assumptions.md` and the
  sweep functions' own docstrings, not read live from any API field —
  clearly commented in code and here, per the instruction to
  distinguish API facts from frontend-derived values.
- No pagination or display cap was implemented anywhere on this page;
  none was needed at this dataset's scale.

## Assumptions made explicit

- `demand_uncertainty_scale`'s baseline is 1.0 "by definition" (the
  sweep scales the actual forecast-error std by this factor).
- `stockout_cost_weight`'s baseline is 4.0 because it is the single
  fixed value all 3 named scenarios share (verified in
  `planning-assumptions.md`'s assumption table — unlike
  `service_level_target`, it does not vary by scenario).

No backend contract gap was discovered during this milestone — every
field the intended UI needed already existed and was consistent with
its own documentation.
