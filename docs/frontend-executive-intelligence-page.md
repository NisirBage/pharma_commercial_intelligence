# Frontend — Executive Intelligence Surface (M7.9)

## Purpose

M7.9 is an **integration** milestone, not a new page. The Executive
Overview (`frontend/src/pages/Overview/`) already existed from M7.4 —
this milestone extends it to preview the three intelligence surfaces
built since (Forecasting M7.6, Supply Planning M7.7, Recommendations
M7.8), so the application reads as one coherent commercial-intelligence
product — Overview → Demand → Forecast → Supply Planning →
Recommendations — rather than a home page that stopped tracking the app
around it. No new analytical logic was written: every new section reads
an existing hook and reuses an existing component.

## Route

`/` (unchanged — `index: true` under `RootLayout` in
[frontend/src/routes/router.tsx](../frontend/src/routes/router.tsx)).

## APIs consumed (7 independent GETs, no mutation)

| Section | Hook | Endpoint | New in M7.9? |
|---|---|---|---|
| KPI row, Demand Position | `useKpiSummary()` | `GET /api/v1/kpis/summary` | No (M7.4) |
| Demand Position, Concentration, Commercial Signals | `useAtcAnalytics()` | `GET /api/v1/analytics/atc` | No (M7.4) |
| Data Quality | `useDataQuality()` | `GET /api/v1/data-quality` | No (M7.4) |
| Data Quality (API status) | `useHealth()` | `GET /health` | No (M7.4) |
| **Forecast preview** | `useForecast(undefined)` | `GET /api/v1/forecast/aggregate` | **Yes** |
| **Supply Planning preview** | `useOptimizationScenarios()` | `GET /api/v1/optimization/scenarios` | **Yes** |
| **Recommendations preview** | `useRecommendations()` | `GET /api/v1/recommendations` (default `balanced`) | **Yes** |

All three new hooks already existed (built for Forecasting/Supply
Planning/Recommendations) and needed no changes. `POST
/api/v1/optimization/run` (`useOptimizationRun`, a mutation) is never
called from this page.

## Data-fetching architecture

All 7 queries are independent `useQuery` calls fired in parallel from
`OverviewPage`, each handed down to its own section — the same pattern
M7.4 established. One endpoint failing renders that section's own
`ErrorState` without blanking sections that don't depend on it (verified
by dedicated tests for each of the 3 new sections, following the
existing "failed KPI fetch still lets Concentration render" pattern).

**Cache sharing, not duplication**: the three new queries use the exact
same hooks and query keys their own detail pages use —
`useForecast(undefined)` is the identical call `/forecast` (with no
`:atcClass`) makes; `useOptimizationScenarios()` and `useRecommendations()`
are the identical calls `/planning` and `/recommendations` make on
mount. Navigating from Overview to any of the three pages is typically a
near-instant cache hit rather than a second meaningful request (verified
in the real browser — see below).

## What each new section shows

### Forecast preview
The aggregate 14-day forecast's **first horizon point** (next-day
prediction + interval, if the model provides one), the model's own
backtested **WAPE**, and the **model name** — three direct fields from
the response, with zero client-side averaging or re-derivation of the
14-day series (that stays on `/forecast`). Per-class growing/declining
signals are already surfaced by the existing Commercial Signals section
directly above; this section doesn't repeat them.

### Supply Planning preview
**A genuine, deliberate scope limitation**: `GET
/api/v1/optimization/scenarios` only returns the 3 scenario
*definitions* (service level target, lead time, review period,
rationale) — there is no GET endpoint that returns an actual optimized
allocation, capacity budget, or improvement percentage. Those fields
exist only in the response of `POST /api/v1/optimization/run`, a
mutation that must never fire automatically (M7.7's own rule, re-verified
here by inspecting `backend/app/api/routes/optimization.py` directly:
exactly `GET /scenarios`, `GET /sensitivity`, `POST /run` — no fourth
endpoint). So this section shows a compact 3-row table of the real
scenario definitions and an explicit sentence that an allocation result
only exists after running one on `/planning` — never a fabricated
number standing in for what running the optimizer would produce.

### Recommendations preview
The real **total count** and **low-confidence count** (plain tallies of
the already-categorical `confidence` field — the same kind of
frontend-derived aggregate the Recommendations page's own KPI row
computes, not a new statistic), plus **one featured recommendation
card**: the first `confidence: "low"` item if one exists (the one most
worth scrutinizing), falling back to the first recommendation in the
API's own order otherwise — never re-sorted.

## Drill-down navigation

Every new section's `SectionHeader` carries an `action` link (the same
pattern the existing Data Quality section already used for "View full
report →"): "View forecasts →" → `/forecast`, "Open Supply Planning →"
→ `/planning`, "View all recommendations →" → `/recommendations`. No new
routes, no query parameters invented, no modal pseudo-navigation.

## Bug found and fixed: dead `/demand/atc/:atcClass` links

Discovery surfaced a real, pre-existing defect: `CommercialSignalsSection`
and `NextActionsSection` (both from M7.4) linked to
`/demand/atc/${atcClass}`, which routes to `AtcDetailPage` — an M7.2
scaffold that still reads *"Scaffolding placeholder — implemented in
M7.5."* M7.5 actually shipped a different design (`/demand?tab=atc`, a
shared non-per-class tab — confirmed in
[docs/frontend-demand-intelligence-page.md](frontend-demand-intelligence-page.md):
*"Single route (`/demand`, unchanged from M7.2)"*) and never wired up
per-class routing. These two links were dead — clicking them landed on a
stub, not real content. Both were repointed to `/demand?tab=atc`, the
route that actually shows ATC-class content. The `/demand/atc/:atcClass`
route and its placeholder page were left untouched (no longer linked
from anywhere in the app, but removing the route itself is a separate,
out-of-scope architectural decision for a future milestone).

## Reused components

`MetricCard`, `Card`, `Badge`, `EmptyState`, `ErrorState`, `Skeleton`,
`SectionHeader` (including its existing `action` slot, `Table`
(self-contained horizontal scroll, already used by Concentration/ATC
Analysis). `domainLabels.ts`'s `getRecommendationConfidenceDisplay` and
`format.ts`'s `formatFraction`/`formatPercent`/`formatDecimal` — all
pre-existing, from M7.7/M7.8. No new UI primitive was needed; the only
new CSS is `.previewGrid` in `Overview.module.css` (a responsive
`auto-fit` metric grid, the same pattern `.signalGrid` already used).

## Loading / error / empty behavior

Each of the 3 new sections independently renders `Skeleton` while
loading, its own `ErrorState` (with retry) on failure, and a distinct
`EmptyState` for a genuine zero-result response — never conflating "the
API returned nothing" with "the API failed." Verified with dedicated
tests per section (6 new loading/error/empty tests total) using the
same pattern as the pre-existing sections.

## Accessibility

- Still exactly one `<h1>` ("Executive Overview") — verified with a
  dedicated test.
- Each new section is `<section aria-labelledby>` with its own `<h2>`
  id, matching the existing sections' pattern exactly.
- Every new drill-down link has a distinct, descriptive accessible name
  ("View forecasts →", not "click here").
- Confidence in the Recommendations preview uses the same `Badge`
  (never color-only) as the Recommendations page itself.
- No new interactive controls beyond plain links and the existing
  `Table`/`MetricCard` tooltip triggers — nothing here needed new
  keyboard-handling code.

## Responsive verification

Checked against the real running app (not just component tests) at
375px and 768px, with every section populated (the densest state, not
loading/empty) — `document.documentElement.scrollWidth` never exceeded
`window.innerWidth` at either width. The Supply Planning preview's
3-row scenario table used the existing `Table` component's own
horizontal-scroll container, requiring no new responsive handling.

## Test coverage

16 new tests added to `Overview.test.tsx` (233 total in the full suite,
up from 217): Forecast preview (content, drill-down link, error, empty),
Supply Planning preview (content — including an explicit check that the
"no result yet" disclaimer renders rather than a fabricated number,
drill-down link, error, empty), Recommendations preview (content, tally,
drill-down link, error, empty, "lowest-confidence item is featured, not
just the first" test, and the low-confidence Next Actions item), plus 2
accessibility tests. The two pre-existing tests that asserted the dead
`/demand/atc/N02BE` href and an unscoped `getByRole("table")` (now
ambiguous — the Supply Planning preview added a second `<table>`) were
updated to match the corrected implementation, not weakened.

## Real-browser verification

Performed against the real running backend (port 8020) and frontend dev
server (port 5175), with `frontend/.env.local` pointing at the real
backend for the duration only (created before, deleted after).

- All 7 sections rendered with real values: KPI totals matched the
  established M3 findings (N02BE 49.4%, CR3 73.1%, HHI 2909.9); the
  Forecast preview showed a real next-day prediction (64.7 units,
  interval 35.0–94.4) with a real WAPE (22.3%) and model (`ets`); the
  Supply Planning preview showed the real 3 scenarios (98%/95%/90%
  service level, 7-day lead/review); the Recommendations preview showed
  the real 8-recommendation, 2-low-confidence distribution, featuring
  the real N05C low-confidence item.
- All 3 new drill-down links, plus both corrected `/demand?tab=atc`
  links, verified via direct DOM inspection to carry the correct
  `href`; navigating to `/demand?tab=atc` was confirmed to land on the
  real ATC Analysis tab content, not the dead placeholder.
- Clicked through to `/planning` and `/recommendations`: both rendered
  correctly with the same real data already seen in the Overview
  preview.
- No mutation request (`POST /optimization/run`) fired at any point.
- No horizontal overflow at 375px or 768px with every section populated.

## Bugs found during real-browser verification

**None required a source fix.** One observation worth recording: on
navigating from Overview to `/planning`, `useOptimizationScenarios()`
fired one additional `GET /optimization/scenarios` request rather than
serving purely from cache. This is the same React StrictMode dev-only
double-effect-invocation pattern already documented and accepted in
M7.7/M7.8's own real-browser verification (a single extra GET, never a
mutation, never a loop) — not a production behavior (StrictMode's
double-invoke only happens in development) and not specific to this
milestone's code.

## Performance observations

- 7 parallel GET requests on Overview's mount, each independent — no
  request depends on another's result.
- Production build: 873.90 kB / 255.20 kB gzip (up from 868.98 kB /
  254.10 kB before this milestone — the incremental cost of 3 new
  section components, consistent with the steady per-milestone growth
  already noted in M7.5's own docs; still not code-split, consistent
  with the project's established "avoid premature optimization" stance).
- No polling, no interval-based refetching, no mutation fired on
  render.

## Limitations

- The Recommendations preview's total/low-confidence counts are
  **frontend-derived aggregates** (plain tallies of the API's own
  categorical `confidence` field), not a backend-provided summary — the
  same category of derived value already documented for the
  Recommendations page's own KPI row.
- The Supply Planning preview intentionally omits any
  allocation/capacity/improvement figure — this is a scope decision
  forced by the actual API surface (no GET endpoint returns those
  values), not an oversight. See "Supply Planning preview" above.
- The "featured" recommendation (lowest confidence, or first in order)
  is a frontend selection rule for which one item to preview, not a
  backend-asserted priority — the full, correctly-ordered list is one
  click away on `/recommendations`.
- `/demand/atc/:atcClass` remains an orphaned, unimplemented route —
  now with zero inbound links, but not removed (out of scope for this
  integration milestone).
