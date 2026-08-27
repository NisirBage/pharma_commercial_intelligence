# Interview Guide

Prep notes for defending this project's technical and commercial
decisions in an interview. Organized by milestone; this document grows as
later milestones are added. Every answer below should be backed by an
actual file/number in this repo — if you can't point to where a claim
comes from, don't say it in the interview either.

---

## M6 — FastAPI Backend

### Why FastAPI?

Native Pydantic integration (request/response validation with zero
boilerplate — every schema in `app/schemas/` doubles as both validation
and OpenAPI documentation), automatic interactive docs (`/docs`, `/redoc`
— generated from the same schemas, never hand-written and drifting out of
sync), and it's the natural fit for a Python-native project sitting on
top of pandas/scikit-learn/statsmodels/OR-Tools services that are
themselves synchronous — FastAPI runs sync route handlers in a
threadpool automatically, so there was no need to introduce async
SQLAlchemy or rewrite M2-M5's synchronous code to get a modern async
framework's other benefits (routing, dependency injection, docs).

### Why REST?

The domain maps cleanly onto resources (a forecast for a class, a
scenario's optimization run, a set of recommendations) with a small,
fixed set of operations per resource (mostly read, one computation
trigger) — there's no requirement here for GraphQL's flexible field
selection or gRPC's streaming/performance profile. REST plus OpenAPI docs
is also the most legible choice for a frontend developer who hasn't read
the backend (M6 Sec. 28's own stated goal).

### Why API versioning (`/api/v1`)?

Because M6-M9 (frontend, further analytics) will inevitably need
backward-incompatible schema changes at some point, and retrofitting
versioning after clients exist is far more disruptive than starting with
it. `/health` is deliberately left unversioned — a liveness probe's
contract (used by orchestration tooling, not application clients) is
expected to be far more stable than a business-data contract.

### Why Pydantic?

It's what makes "keep routes thin" (below) actually achievable: input
validation (enums, numeric bounds, date formats) is declared once on the
schema and enforced automatically before a route handler ever runs, and
the same schema generates the OpenAPI documentation a frontend developer
reads. `app/schemas/common.SafeFloat` is a concrete example of Pydantic
doing real work — a `BeforeValidator` that converts any NaN/Infinity
value (a real possibility given how much floating-point statistics flows
through M3/M4/M5) into `None` before it can ever reach a JSON response.

### Why keep routes thin?

So the actual business logic (M3/M4/M5) is testable, reusable, and
readable independent of the HTTP layer. Every route in
`app/api/routes/*.py` is 1-5 lines: parse the request, call exactly one
service function, wrap the result. Compare `app/api/routes/optimization.py`
(thin) against `app/services/optimization_service.py` (the actual
translation/validation logic) — the separation is the point.

### How did you separate business logic from HTTP logic?

Three layers, one direction of dependency: **routes** (`app/api/routes/`)
know about HTTP (status codes, query/path parameters) and call
**services** (`app/services/`); services know about the **domain**
(`app/analytics`, `app/forecasting`, `app/optimization` — M3/M4/M5) and
translate between HTTP-shaped requests/responses and domain objects;
the domain layer knows nothing about HTTP at all — it was built in M3-M5,
entirely before any API existed, and M6 changed none of its methodology
(only one small additive field, `DemandInput.fold_results`, was added to
expose data M5 had already computed but discarded).

### How do you prevent expensive forecasting work on every request?

`app/services/cache.py` — see docs/api-design.md, "Caching strategy," in
full. Short version: `functools.lru_cache` wraps the two expensive
computations (the canonical frame, ~1-2s; per-class demand inputs, which
rerun an M4 backtest to recover residuals, ~7-9s total) so they run once
per process, not once per request — measured: a cold `/forecast/{atc_class}`
call takes ~8.9s, every subsequent call ~12ms (docs/api-design.md,
"Performance"). This is explicitly documented as an in-process,
process-lifetime cache — a real simplification versus a production Redis/
materialized-table cache with explicit pipeline-triggered invalidation.

### How would you scale this API?

Horizontally, the in-process `lru_cache` is the first thing that would
need to change — multiple worker processes/pods would each pay the cold-
start cost independently and could serve inconsistent data if the
underlying M4/M5 pipeline reran between workers refreshing. The fix is
exactly what docs/api-design.md's caching section describes: move the
cache to Redis (or a materialized table refreshed by the pipeline job) so
all workers share one warm cache and one invalidation signal. Vertically,
none of the current endpoints are CPU-bound in a way that needs more than
one core per request — the LP solve is milliseconds; the expensive part
is I/O (reading CSVs / re-running a backtest), which caching already
solves.

### How would you introduce authentication?

There's no real user model or write-heavy surface yet — every endpoint
is either a read of computed analytics or a stateless optimization
computation with no side effects. If real users needed to authenticate
(e.g. a real planner's saved scenarios, or role-based access to different
ATC classes), I'd add OAuth2/JWT bearer-token auth via FastAPI's built-in
`Security`/`Depends` mechanism, verified in a dependency injected into
routes that need it — not a global middleware, so read-only public
endpoints (if any remained public) wouldn't pay the auth-check cost.
Building this now, with no real requirement driving it, would be exactly
the "auth for appearance" M6 explicitly warns against.

### How would you deploy this?

`backend/Dockerfile` packages the API (`uvicorn app.main:app`) — see
docs/api-design.md, "Deployment considerations," for why a full
docker-compose stack (API + Postgres) wasn't built: the API's primary
data path is CSV-derived, not database-backed, in this project's current
state. A real deployment would run the container behind a reverse proxy/
load balancer (multiple replicas once the caching layer is externalized —
see "How would you scale this API?"), with `CORS_ALLOWED_ORIGINS` set to
the real frontend's production origin (never `*`) and `ENVIRONMENT=production`
enabling the stricter config-validation paths already present in
`app/core/config.py`.

### How would you handle concurrent optimization requests?

Today, safely by construction: `POST /api/v1/optimization/run` has no
shared mutable state — it reads from the cache (read-only after the
first warm-up) and returns a freshly-computed result every call, so
concurrent requests don't interfere with each other. The one real
concurrency risk is the cache's *cold-start* window: if two requests
race to populate `lru_cache` simultaneously before it's warm, both would
redundantly do the expensive work (not incorrect, just wasteful) — an
`asyncio.Lock`/`threading.Lock` around the cold-start path would close
that gap; not added because it only matters for a handful of requests
during the very first moments after a process starts.

### How would you cache forecasts?

They already are — see "How do you prevent expensive forecasting work on
every request?" above. To make forecasts cacheable ACROSS process
restarts (not just within one process's lifetime), the next step would be
persisting `ForecastOutput` objects (the same structure `GET /api/v1/forecast/{atc_class}`
already returns) to a table or Redis key per ATC class, written once by
the M4 pipeline job rather than computed lazily by the first API request.

### How would you handle database connection failures?

They're already handled at the one place the database is used:
`GET /health`'s `check_database_connection()` (`app/api/deps.py`) catches
any connection exception and reports `"unreachable"` rather than raising
— the endpoint still returns 200 (this API's primary data path doesn't
need a database at all, so a missing one doesn't make the API itself
unhealthy). If a future endpoint DID require the database for a write
path, I'd raise `app.api.errors.ServiceUnavailableError` (503) from that
endpoint specifically, using the same `get_db()` dependency — not a
global "is the DB up" gate in front of every route.

### Why isn't the API directly exposing SQL?

Because a REST API's job is to expose business capabilities (a forecast,
a recommendation, an optimization run), not a query interface — letting
a client construct arbitrary queries is both a SQL-injection surface and
a leak of internal schema details the frontend shouldn't need to know
(M6 Sec. 4: "expose business capabilities rather than internal
implementation details"). Every endpoint here calls a specific, named
service function with a specific, validated request shape.

### How would you monitor API performance?

Today: the request-duration/endpoint log line every request produces
(`app/api/middleware.py`, `X-Request-ID` header + a structured log
entry) is the whole story — appropriate for a single-instance portfolio
deployment, and deliberately NOT Prometheus/Grafana/an APM agent (M6
Sec. 35: no observability stack for resume keywords without a real need
for one). At real production scale, the natural next step is exporting
the same per-request duration/status/endpoint data this middleware
already computes to a metrics backend (e.g. Prometheus via
`prometheus-fastapi-instrumentator`) rather than inventing a new
observability model — the instrumentation point already exists.

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
