# Frontend: Demand Intelligence Page

`frontend/src/pages/DemandIntelligence/` — M7.5. One analytical
workspace across four tabs, all reading M3/M7.1.5 backend analytics
directly. See `docs/frontend-design-system.md` for the design system
and `docs/frontend-overview-page.md` for the sibling Executive Overview
page this one follows the same conventions as.

## Page purpose

The story, in order: **how has demand moved → which classes drive it →
what seasonal patterns recur → where are the unusual observations** —
Trends → ATC Analysis → Seasonality → Anomalies, matching the tab
order.

## API endpoints consumed

| Hook | Endpoint | Tab |
|---|---|---|
| `useSalesTrends(params)` | `GET /api/v1/sales/trends` | Trends |
| `useAtcAnalytics()` | `GET /api/v1/analytics/atc` | ATC Analysis |
| `useSeasonality(atcClass?)` | `GET /api/v1/analytics/seasonality` | Seasonality |
| `useAnomalies(params)` | `GET /api/v1/analytics/anomalies` | Anomalies |

All four hooks already existed (M7.2 scaffolding) and needed no
changes. `useAtcAnalytics` is the same hook M7.4's Overview page uses
— TanStack Query's cache means visiting ATC Analysis shortly after
Overview is typically an instant cache hit, not a second request.

## Tab architecture

Single route (`/demand`, unchanged from M7.2), tab selected via
`?tab=trends|atc|seasonality|anomalies` (default `trends`, invalid
values fall back to `trends`). Only the **active tab's section
component is mounted** — switching tabs conditionally renders one of
four components rather than four components with three hidden, so a
tab you haven't opened never fires its query. `Tabs`' existing
`id="tab-{value}"` / `aria-controls="tabpanel-{value}"` wiring is
completed here with a matching `<div role="tabpanel" id="tabpanel-
{value}" aria-labelledby="tab-{value}">` — the first page to actually
pair `Tabs` with a tabpanel.

**Per-tab filters (ATC class, grain, date range, method, severity) are
local `useState` in each section, not URL-persisted.** Only the tab
itself survives refresh/back-forward/direct URL entry; a filter
resets when you leave and return to a tab. This was a deliberate
choice, not an oversight — M7.5's own brief cautions against
over-engineering URL state, and persisting five independent filter
params across four tabs would be exactly that for a first version.
Revisit only if a real workflow need for shareable-filtered-URLs
emerges.

## Filters

- **Trends**: ATC class (`Select`, "Aggregate" + 8 classes),
  grain (`Select`: daily/weekly/monthly), date range (`DateRange`,
  optional — omitted entirely from the request when empty, letting the
  backend's own full-range default apply rather than the frontend
  guessing a boundary).
- **ATC Analysis**: none — the endpoint returns all 8 classes in one
  call.
- **Seasonality**: ATC class only (the endpoint has no other filters).
- **Anomalies**: ATC class, detection method (rolling_zscore/iqr),
  severity (any/low/medium/high), date range.

`frontend/src/pages/DemandIntelligence/atcOptions.ts` is the one
shared "Aggregate + 8 classes" option list and the `"" -> undefined`
sentinel conversion, used by all three ATC-filterable tabs so they
can't drift out of sync.

## Loading / error / empty behavior

Each tab's query independently drives its own `Skeleton`/`ErrorState`
(with retry)/`EmptyState` — one tab's API failure never affects
another tab (they don't even share a query beyond ATC Analysis's cache
overlap with Overview). Anomalies distinguishes "0 anomalies found"
(a real, valid `EmptyState` result) from an API error.

## Seasonality availability handling

Every one of the four seasonality metrics (`day_of_week_effect`,
`hour_of_day_effect`, `weekly_seasonal_strength`,
`annual_seasonal_strength`) carries its own `available` flag and
`reason`. When `available` is false, the section shows "Not available"
plus the API's own `reason` verbatim — never a guessed value, never a
zero standing in for "unknown."

`mean_units_by_weekday`/`mean_units_by_hour` are plain dicts with no
guaranteed key order (verified against the real backend: the real
response returns weekdays alphabetically — Friday, Monday, Saturday...
— not calendar order). Both charts reorder into a fixed, sensible
display order (Monday→Sunday; 0:00→23:00) for readability. This is a
presentation reordering of already-returned values, not a new
statistic.

## Accessibility approach

Same conventions as M7.3/M7.4: `<section aria-labelledby>` per tab
section, the completed ARIA tabs/tabpanel pairing described above,
`accessibilityLayer` on every Recharts chart, a paired accessible
`Table` alongside every bar chart (ATC contribution; concentration
already existed on Overview), status/severity/trend never
color-only (text label always present alongside the `Badge`/icon).

## Responsive behavior

Verified at 375px/768px/desktop against the **real backend** (not just
mocked data) for all four tabs, including the anomaly-heavy Anomalies
tab with its 4-control filter bar and wide table — no horizontal
overflow at any width.

## Performance considerations

- Only the active tab fetches; switching tabs mounts/unmounts sections
  rather than fetching all four up front.
- **The anomalies endpoint has no server-side limit/pagination.**
  Verified against the real backend: an unfiltered aggregate scan
  (`GET /api/v1/analytics/anomalies` with no filters) returns **1,048
  records**. Rendering all of them as table rows and chart bars would
  be exactly the "massive DOM table" this milestone's brief warns
  against — found via the real-browser check, not the MSW-backed unit
  tests (whose fixture only has 2 anomalies). Fixed client-side:
  results are ranked by severity then |anomaly_score| (a sort of
  already-computed fields, not a new statistic) and capped at 100 for
  display, with an explicit "showing N of TOTAL" note pointing at the
  existing ATC/severity/date filters to narrow further. The
  `Anomalies Detected` metric always shows the true, untruncated
  `total_count`. The chart re-sorts its capped subset chronologically
  (severity order would otherwise scramble the date axis) while the
  table keeps the severity-first order, since a "most concerning
  first" table is more useful to a planner than a date-first one.

## Decisions made to avoid duplicating backend analytics

- Trend classification, seasonality strength/significance, and anomaly
  detection/severity are always the backend's own computed values —
  the frontend groups/counts/sorts/formats them, never recomputes.
- The Trends tab's "Avg / Peak (this view)" summary is a plain
  mean/max of the exact points already rendered in the chart —
  display-only, explicitly labeled "computed from the points shown
  above" so it's never mistaken for an official backend statistic.
- HHI's concentration-band interpretation is shown via the API's own
  `hhi_scale_note` text, never a frontend-picked band.

## Limitations

- Filter state resets on tab switch (see "Tab architecture" above) —
  a deliberate scope decision, not a bug.
- The Anomalies chart/table display cap (100) is a fixed constant, not
  user-configurable; a future milestone could add real pagination if
  reviewing more than 100 ranked anomalies at once becomes a genuine
  workflow need.
- Production bundle continues to grow as more Recharts usage is added
  (~783 KB after M7.4 -> ~819 KB after M7.5) — still not code-split,
  consistent with the "avoid premature optimization" stance from prior
  milestones.
