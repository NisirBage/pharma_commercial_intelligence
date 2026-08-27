# API Design

`backend/app/main.py` + `backend/app/api/`, `backend/app/schemas/`,
`backend/app/services/`. This is an integration layer over M2 (data), M3
(analytics), M4 (forecasting), and M5 (optimization) — it contains no new
business logic beyond request/response translation, input validation, and
caching. Every number an endpoint returns is computed by code that
already existed before M6.

## Architecture

```
Frontend
   |
FastAPI (app/main.py)                    <- CORS, request-ID/duration logging, exception handlers
   |
Routes (app/api/routes/*.py)             <- thin: parse request, call one service function, wrap the result
   |
Services (app/services/*.py)             <- request/response translation, input validation, caching
   |
Analytics / Forecasting / Optimization   <- app/analytics, app/forecasting, app/optimization (M3/M4/M5, unmodified)
   |
Data access                              <- app/analytics/data_access.py, app/optimization/demand_input.py
   |
Database (optional) / canonical CSV-derived data (M2)
```

**Routes never contain business logic.** A route parses the HTTP
request into a Pydantic model, calls exactly one service function, and
wraps the result in the common envelope. All validation beyond what
Pydantic's field constraints express (cross-field rules, "is this a
known ATC class," date-range ordering) lives in the service layer, not
the route (M6 Sec. 33).

## Endpoint inventory

| Method | Path | Source milestone | Notes |
|---|---|---|---|
| GET | `/health` | — | Liveness check; DB check is best-effort, never fails the request |
| GET | `/api/v1/kpis/summary` | M3 | Total/average/peak demand, dominant class |
| GET | `/api/v1/sales/trends` | M2/M3 | Filterable by ATC class, date range, grain |
| GET | `/api/v1/analytics/atc` | M3 | Per-class performance + demand concentration |
| GET | `/api/v1/analytics/anomalies` | M3 | Rolling z-score / IQR, filterable |
| GET | `/api/v1/forecast/{atc_class}` | M4 | 14-day forecast + interval + metrics |
| GET | `/api/v1/forecast/aggregate` | M4 | The DIRECT aggregate model — never a sum of per-class forecasts |
| GET | `/api/v1/forecast/{atc_class}/diagnostics` | M4 | Residual bias/autocorrelation, per-horizon-step error, limitations |
| GET | `/api/v1/optimization/scenarios` | M5 | The 3 named scenarios and their parameters |
| GET | `/api/v1/optimization/sensitivity` | M5 | One parameter's sweep for one ATC class |
| POST | `/api/v1/optimization/run` | M5 | Runs the full safety-stock/allocation engine for a scenario |
| GET | `/api/v1/recommendations` | M5 | Explainable per-class recommendations |
| GET | `/api/v1/data-quality` | M2/M3 | Per-file record counts + reconciliation status |

Full request/response schemas: `/docs` (Swagger UI) or `/redoc` once the
app is running — every field, enum, and validation rule is documented
there directly from the Pydantic models (`app/schemas/`), not duplicated
here.

## Response envelope

Every successful response: `{"data": ..., "metadata": {"generated_at", "source"}}`.
Every error: `{"error": {"code", "message", "details"}}`. One shape, used
everywhere (`app/schemas/common.py`) — no per-endpoint variation (M6 Sec.
20: "consistency over elaborate wrappers").

## Error handling

| Condition | Status | Code |
|---|---|---|
| Unknown ATC class | 404 | `not_found` |
| Invalid date format / date range / severity | 400 | `bad_request` |
| Pydantic validation failure (invalid scenario, service level, lead time, grain, method) | 422 | `validation_error` |
| Optimization solver infeasible/unbounded | 422 | `optimization_infeasible` |
| M4 model registry / raw data not available | 503 | `service_unavailable` |
| Anything unexpected | 500 | `internal_error` — message and stack trace never reach the client (`app/api/errors.py`); the real exception is logged server-side only |

Domain code raises a typed exception (`app/api/errors.py`) and lets it
propagate; a single set of registered handlers (`register_exception_handlers`)
turns each into the envelope above. Routes never construct an error
response themselves.

## Database integration

The API's PRIMARY data path does **not** require a database — it's the
same CSV-derived canonical frame M2/M3/M4/M5 already used
(`app.analytics.data_access.load_from_raw_csv`). `app/api/deps.py`
provides a properly-scoped, per-request `get_db()` session dependency
(never a single global session) for when a database IS reachable, but
only `/health` currently uses it, and treats a connection failure as a
normal, reportable state rather than a crash. No second database
abstraction was introduced — the existing `app/db/session.py` /
`app/models/` from M2 are reused as-is.

## Caching strategy

Two computations are expensive enough that M6 Sec. 26 explicitly forbids
re-running them per request:

- **The canonical demand frame** (`app.analytics.data_access.load_from_raw_csv`)
  — roughly 1-2s to rebuild from the raw CSVs.
- **Per-ATC-class demand inputs** (`app.optimization.demand_input.build_all_demand_inputs`)
  — re-runs an M4 backtest per class to recover residuals; roughly 7-9s
  total across 8 classes (measured: see "Performance").

Both are wrapped in `functools.lru_cache` (`app/services/cache.py`) — the
**first** request pays the cost, every subsequent request in the
process's lifetime reads from memory. Every service module accesses
these via `from app.services import cache; cache.get_x()` (module-
qualified, not `from app.services.cache import get_x`) specifically so
the whole cache can be swapped out cleanly in tests
(`tests/api/conftest.py`'s `patched_cache` fixture) without patching each
consumer individually.

**This is an in-process, process-LIFETIME cache — a documented
simplification, not a production caching architecture.** A real
deployment would instead:

- Persist these to Redis or a materialized table, not process memory
  (so a restart, or running multiple worker processes, doesn't each pay
  the cost independently or serve stale data after another worker
  refreshes).
- Invalidate explicitly when the M4/M5 pipelines actually rerun (a
  scheduled retraining job, or a webhook), not "however long this
  process happens to stay up."

`cache.clear_all_caches()` is the seam a future invalidation trigger (or
admin endpoint) would call — already used by the test suite.

## Optimization execution

`POST /api/v1/optimization/run` calls M5's existing `app.optimization.scenarios.run_scenario`
+ `app.optimization.allocation_optimizer.optimize_allocation` (an OR-Tools
GLOP linear program, milliseconds to solve — the expensive part is the
cached demand-input layer above, not the LP itself). Measured: ~130-360ms
per call with a warm cache (see "Performance"), dominated by response
serialization and recommendation-text assembly, not the solve.

## Security review

- **SQL injection**: no raw SQL is ever built from request input anywhere
  in this API — the one DB dependency (`get_db`) is used for a hardcoded
  `SELECT 1` liveness probe only; nothing else queries the database at
  all yet (see "Database integration").
- **Path traversal / unsafe file access**: no endpoint accepts a
  filesystem path from the client. `raw_data_dir`/`quality_report_dir`
  are server-side configuration (`app/core/config.py`), never derived
  from request input.
- **Arbitrary code execution**: no endpoint evaluates request input as
  code, a query expression, or a template.
- **Excessive request sizes**: request bodies are small, fixed Pydantic
  models (a scenario name + two optional numeric overrides) — there is no
  endpoint that accepts an unbounded body, list, or file upload.
- **CORS**: never `allow_origins=["*"]`. Origins are explicit and
  configurable via `CORS_ALLOWED_ORIGINS` (default: the Vite dev server
  origin only, `http://localhost:5173`) — see `.env.example`.
- **Secret exposure**: no endpoint returns configuration, file paths, or
  environment values. `.env` is gitignored; `.env.example` ships only
  placeholder values.
- **Verbose exception responses**: the catch-all handler
  (`app/api/errors.py`) never serializes an exception's message or
  traceback into the response — only a fixed `"An unexpected error
  occurred."` string; the real detail is logged server-side.
- **No authentication was added.** This is a portfolio project with no
  real users, credentials, or write operations beyond a stateless
  optimization computation — adding auth "for appearance" without a real
  requirement would be exactly what M6 Sec. 32 warns against. See
  `docs/interview-guide.md`, "How would you introduce authentication?"
  for how this would be added if the API had real users.
- **Data-vs-assumption disclosure is itself a data-integrity control**:
  every optimization response carries its own `assumptions` array
  (`source: "scenario"`, `type: "assumption"` on every row) so a client
  can never mistake a scenario-derived number for an observed dataset
  fact — enforced by `app.optimization.assumptions.ScenarioParameters`
  being a frozen dataclass (`tests/unit/optimization/test_data_integrity.py`).

## Performance (local, TestClient-measured — NOT a production throughput claim)

| Endpoint | Cold (first call) | Warm (cached), avg of 5 |
|---|---:|---:|
| `GET /health` | 804ms | 155ms |
| `GET /api/v1/kpis/summary` | 1,093ms (loads raw CSVs) | 230ms |
| `GET /api/v1/sales/trends` | — | 341ms |
| `GET /api/v1/forecast/{atc_class}` | 8,911ms (reruns M4 backtest for all 8 classes, once) | 12ms |
| `POST /api/v1/optimization/run` | — | 183ms |

The forecast/optimization cold cost (~9s) is the entire point of the
caching strategy above — it happens once per process, not once per
request. These numbers are from FastAPI's `TestClient` on a single local
machine (which has its own non-trivial per-call overhead vs. a real
deployed `uvicorn` server) — not a claim about production request
throughput or concurrency.

## Deployment considerations

No Docker Compose stack exists yet for this project (M2-M5 ran entirely
against CSV-derived data, no live database needed). `backend/Dockerfile`
(added in M6) packages the API alone — `uvicorn app.main:app` — without
introducing a database container, since the API's primary path doesn't
require one. A full docker-compose stack (API + Postgres) would be
natural future work once the M2 database path is actually exercised in
anger, but building one now, unused, would be exactly the kind of
premature infrastructure M6's own instructions warn against (Sec. 39).

Scaling/production considerations are discussed in
`docs/interview-guide.md`.
