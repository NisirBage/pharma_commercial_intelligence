# Frontend: Forecasting Intelligence Page

`frontend/src/pages/Forecasting/` — M7.6. A single coherent surface
answering "what's expected, how does it compare with recent history,
and how much should it be trusted" for one series at a time. See
`docs/frontend-design-system.md` for the design system and
`docs/frontend-demand-intelligence-page.md` for the sibling page this
one deliberately does *not* copy the tab pattern from (see "Page
architecture" below for why).

## Purpose

Answers, per the milestone brief: what demand is expected, how it
compares with recent history, how uncertain the forecast is, what
horizon is shown, which series is being forecast, how trustworthy the
model is, and what caveats apply — in that order, top to bottom on the
page.

## Page architecture

**Not tabs.** `useForecast` and `useForecastDiagnostics` are two
small, independent queries (14 forecast points; a handful of
diagnostic fields) that both directly answer "how trustworthy is this
forecast" — splitting them behind a tab click would make the decision
workflow worse, not better, so both render on one page.

**Not `?tab=` either — a route param.** Unlike Demand Intelligence,
`router.tsx` already dedicated `/forecast` and `/forecast/:atcClass`
to this page *before* this milestone, with an explicit comment stating
that intent. The ATC selector therefore **navigates** (`useNavigate`)
rather than holding local state — the URL is the single source of
truth for which series is shown, so refresh/back/forward all work via
the router itself, for free, with no extra code.

**No other controls.** All three forecast endpoints
(`/forecast/aggregate`, `/forecast/{atc_class}`,
`/forecast/{atc_class}/diagnostics`) take **zero query parameters** —
verified by reading `backend/app/api/routes/forecasts.py` directly, not
assumed. There is no grain, horizon, or date-range parameter to expose;
the horizon is fixed at 14 days (`horizon_days` in the response).

## APIs consumed

| Hook | Endpoint | Aggregate convention |
|---|---|---|
| `useForecast(atcClass?)` | `GET /api/v1/forecast/aggregate` or `GET /api/v1/forecast/{atc_class}` | Param **omitted** — a dedicated path, not a value |
| `useForecastDiagnostics(atcClass)` | `GET /api/v1/forecast/{atc_class}/diagnostics` | The literal string **`"ALL"`** — verified in `forecast_service.py` (`KNOWN_FORECAST_ENTITIES = KNOWN_ATC_CLASSES \| {"ALL"}`) |
| `useSalesTrends({atcClass, grain: "daily"})` | `GET /api/v1/sales/trends` | Param **omitted** (M7.5's existing convention) |

Three different "aggregate" conventions across three endpoints of the
same feature, each honored exactly as its own contract specifies —
never unified by guessing. This is why `useForecastDiagnostics` always
receives `atcClass ?? "ALL"` while `useForecast`/`useSalesTrends`
receive `atcClass` (possibly `undefined`) directly.

## Filters

**ATC class only** — a `Select` populated from the shared
`lib/atcOptions.ts` (promoted out of `pages/DemandIntelligence/` in
this milestone, since it's now used by two pages). Selecting an option
calls `navigate(value ? \`/forecast/${value}\` : "/forecast")`. There
are no other filters: the backend has none to expose.

## Forecast interpretation

`ForecastResponse.forecast[]` is **forecast-only** (`date`,
`prediction`, `lower`, `upper`) — it does not include historical
actuals. "Compare with recent history" is achieved by also calling the
*already-existing* `GET /api/v1/sales/trends` for the same ATC class
and merging the two series into one chart-and-table timeline by date.
This is a composition of two established contracts, not a new backend
capability or an invented one.

The full `sales/trends` series is fetched (no date-bound query
params, matching Demand Intelligence's Trends tab default) and sliced
to the trailing 60 days client-side (`HISTORY_WINDOW_DAYS` in
`index.tsx`) rather than computing a bounded date range up front —
simpler, and consistent with that already-shipped, already-performant
pattern, at the cost of transferring more of the series than strictly
displayed. Verified against the real backend: the historical series'
last date and the forecast's first date are exactly adjacent calendar
days (no gap, no overlap).

**Overview KPIs** (`ForecastOverview.tsx`): Latest Historical Demand
and Avg Forecast Demand are read/derived from the same two already-
fetched series above; "Avg Forecast Demand" is a plain mean of the 14
`prediction` values, and "Expected Change" is a plain percent change
between those two — both display-only, both explicitly labeled as
computed in their tooltips, neither a model output. Forecast Accuracy
(WAPE) is read directly from `forecast.metrics.wape`.

## Diagnostics interpretation

`ForecastDiagnostics.tsx` renders `ForecastDiagnosticsResponse`
directly: MAE/RMSE/WAPE/MASE metric cards, residual mean/std,
over/under-prediction percentages, the Ljung-Box autocorrelation
result (mapped to a label+badge via the new
`domainLabels.getAutocorrelationDisplay`, not re-derived — the
`autocorrelation_detected` boolean is already `lb_pvalue < 0.05`,
computed server-side), the per-horizon-step backtest MAE table, and
the `limitations` array verbatim. **No "model health score" is
invented** — every number is either a direct API field or (for
`ForecastOverview`'s two derived KPIs, described above) a transparently
labeled arithmetic derivation.

## Loading / error / empty behavior

`ForecastChart` and `ForecastOverview` share the forecast+history
queries' combined loading/error state; `ForecastDiagnostics` has its
own, entirely independent — verified in the real browser and by test
that a diagnostics failure never blanks the forecast chart, and vice
versa. An empty forecast (`forecast: []`) renders `EmptyState`, not a
zero-length chart.

## Accessibility

Semantic `<section aria-labelledby>` for Diagnostics; the ATC `Select`
is labeled; `accessibilityLayer` on the Recharts chart; a full
accessible `Table` (date, type, observed, prediction, confidence
interval) stands next to the chart so no data point requires hovering
an SVG to read — historical vs. forecast is marked with an explicit
"Type" column, not inferred from color; the confidence interval is
also in that table, not just the shaded chart band; the chart carries
a structural `ReferenceLine` + "Forecast begins" label at the
historical/forecast boundary, not a color-only cue. No `role="tab"`/
`"tabpanel"` semantics apply — this page deliberately isn't a tabbed
interface (see "Page architecture").

## Performance

The forecast (14 points) and diagnostics (a handful of fields, 14
horizon-step rows) responses are both small — no display cap needed.
The historical series (60 sliced points) plus the 14 forecast points
combine to 74 table rows and chart points, well within normal bounds
(contrast with Demand Intelligence's Anomalies tab, which needed a
100-row cap against a real 1,048-row response). Chart x-axis ticks are
capped to roughly 10 labels regardless of series length (same pattern
as Demand Intelligence's Trends tab), so mobile stays readable.

## Testing

20 tests in `Forecasting.test.tsx`: routing (default aggregate,
per-class, invalid-class NotFoundPage, selector-driven navigation,
back/forward), forecast (data rendering, loading, error+retry, empty,
historical/forecast table distinction, confidence-interval rendering,
derived-metric correctness), diagnostics (data rendering, status
badge, independent error state), a hardcoded-value guard (every
headline number proven to come from the mocked response, not a
constant), and accessibility (labeled control, headings, accessible
table). All ATC-selection tests use a real `createMemoryRouter` with
both `/forecast` and `/forecast/:atcClass` registered — the shared
`renderWithProviders` test helper wraps components in a bare
`MemoryRouter` with no `<Routes>` tree, so `useParams()` always
returns `{}` there; this is the first page whose behavior depends on a
path param rather than `useSearchParams`, and the gap was only caught
by watching tests fail for the wrong reason during this milestone.

## Real-browser verification

Started the real backend + frontend and verified: the aggregate
forecast (14 real points, `model: "ets"`, WAPE 22.3%), a representative
per-class forecast (N02BE, `model: "moving_average_14"`, WAPE 33.7%,
correctly different historical values), diagnostics for both
(`/forecast/ALL/diagnostics` — the `"ALL"` convention — and
`/forecast/N02BE/diagnostics`), the historical/forecast date boundary
(exactly adjacent, no gap/overlap), the confidence interval values
matching the API exactly, the ATC selector driving real navigation
end-to-end (dispatching a real `change` event, confirming the URL and
content both update), refresh on `/forecast/N02BE` preserving state,
and no duplicate network requests. No responsive-overflow or data-
mapping bugs were found this pass — unlike M7.4/M7.5, this milestone's
design decisions held up on the first real-backend check.

## Limitations

- The 60-day historical window is a fixed constant, not user-
  configurable — the backend has no "recent window" parameter to
  expose a control for.
- "Expected Change" and "Avg Forecast Demand" depend on the historical
  query succeeding; if only the forecast query succeeds, those two
  KPIs show "Not available" rather than a partial/misleading number.
- Fetching the full historical series and slicing client-side (rather
  than requesting a bounded range) transfers more data than strictly
  displayed — an acceptable, consistency-motivated tradeoff, not a
  hard requirement; see "Forecast interpretation" above.
- Production bundle continues to grow with each chart-using page
  (~819 KB after M7.5 → ~847 KB after M7.6), still not code-split.

## Assumptions made explicit

- "Recent history" means the trailing 60 calendar days immediately
  preceding the forecast's first date — a page-level display choice,
  not a value derived from or asserted by the API.
- The historical series' ATC-code filter and the forecast's ATC class
  are assumed to refer to the same underlying per-class demand series
  (verified true for both the aggregate and the N02BE case against the
  real backend).

No backend limitations or contract gaps were discovered during this
milestone — every field the intended UI needed already existed.
