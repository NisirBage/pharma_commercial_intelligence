# Frontend: Executive Overview Page

`frontend/src/pages/Overview/` — M7.4. The first page to consume live
API data; every number on it traces to one of four independent
TanStack Query hooks. See `docs/frontend-design-system.md` for the
design system this page is built from; this document covers only the
Overview page's data sources and business-interpretation rules.

## Data sources

| Hook | Endpoint | Section(s) |
|---|---|---|
| `useKpiSummary` | `GET /api/v1/kpis/summary` | KPI row, Demand Position |
| `useAtcAnalytics` | `GET /api/v1/analytics/atc` | Demand Position (trend tally), Demand Concentration, Commercial Signals, Next Actions |
| `useDataQuality` | `GET /api/v1/data-quality` | Data Quality, Next Actions |
| `useHealth` | `GET /health` | Data Quality (compact "API status" line only) |

Each hook is called once, at the top of `pages/Overview/index.tsx`, and
its `UseQueryResult` is passed down to the section that needs it — one
endpoint failing renders only that section's `ErrorState`, never blanks
sections whose data arrived fine.

## API → UI mapping

- `total_demand` / `average_daily_demand` / `peak_daily_demand` /
  `peak_date` / `dominant_atc_class` / `dominant_atc_share_pct` → the 4
  KPI cards, formatted by `lib/format.ts` (never rounded/computed
  beyond display formatting).
- `classes[].trend_classification` (`"growing" | "declining" |
  "stable_or_no_significant_trend"`) → grouped by `Array.filter`/count
  only — the classification itself is always the backend's OLS + p<0.05
  verdict (`app/analytics/trends.py`), never re-derived. Labels/colors
  come from `lib/domainLabels.ts`.
- `classes[].volatility_cv` → ranked client-side (`Array.reduce`) to
  find the single highest value for the "Highest variability" signal.
  This is a plain sort/rank for display, not a new statistic.
- `concentration.ranked` → the horizontal bar chart (Recharts
  `BarChart`, `layout="vertical"`) and the paired ranked `Table` — same
  data, two views, so a screen-reader user gets the table's semantics
  while a sighted user gets the chart.
- `concentration.concentration_ratio_top3_pct` / `.hhi` → shown as
  plain numbers; `.hhi_scale_note` is shown **verbatim** in the HHI
  MetricCard's tooltip rather than the frontend picking its own
  concentration-band label.
- `overall_status` / `reconciliation[].status` (`"pass"|"warn"|"fail"`)
  → `StatusBadge` via `lib/domainLabels.ts`'s `getDataQualityStatus`.
- `monthly_inconsistency_warning` → always rendered when present (the
  backend returns it unconditionally); never gated behind a condition,
  per M6 Sec. 19's "never hidden" rule.
- `file_summaries[].total_records` → summed (`Array.reduce`) for a
  single "N files, M total records" line — a plain sum, not analytics.

## Business-interpretation rules

- **No fabricated aggregate trend.** No endpoint returns a pooled/
  aggregate-level trend classification — only per-class trends exist.
  The Demand Position section therefore never claims something like
  "aggregate trend is flat"; instead it tallies the real per-class
  `trend_classification` values ("1 growing, 2 declining, 5 no
  significant trend"), which is a count of already-computed backend
  verdicts, not a new statistic computed in React.
- **Growing/declining are not colored success/danger.** A demand
  trend's direction isn't inherently good or bad for a planning
  stakeholder (growth can mean opportunity or stockout risk; decline
  can mean lost revenue or healthy destocking) — the backend never
  makes that value judgment, so the UI doesn't either. `info` (growing)
  / `warning` (declining) signal "noteworthy" / "needs attention", not
  "good" / "bad". See `lib/domainLabels.ts`.
- **HHI has no client-side band.** `hhi_scale_note`'s reference bands
  (<1500/1500-2500/>2500) are shown as the API's own text in a tooltip;
  the frontend does not classify the HHI value into a band itself, to
  stay strictly inside "never invent a business interpretation."
- **Next Actions are evidence-conditioned, not asserted.** Every item
  either names a specific piece of evidence already shown elsewhere on
  the page (the dominant class, a specific significant-trend class, a
  non-"pass" data-quality status) or is a standing link to another
  section (Forecasting, Supply Planning) — nothing is phrased as a
  recommendation presented as fact.

## Known contract quirks (verified against the running backend)

- `KpiSummary.peak_date` is **not** always a bare `"YYYY-MM-DD"` string
  — the real backend returns `"2016-12-30 00:00:00"` (a stringified
  pandas Timestamp), while `period.start`/`period.end` are bare dates.
  `lib/format.ts`'s `formatDate` handles both. Found during the M7.4
  real-backend integration check (Sec. 14 of the milestone) — the MSW
  fixture alone (bare-date format) would not have caught this.
- Local dev CORS: the backend's `CORS_ALLOWED_ORIGINS` (see
  `backend/app/core/config.py`) defaults to `http://localhost:5173`
  only. This repo's frontend dev server runs on port 5175 (see
  `.claude/launch.json` in the harness working directory, chosen to
  avoid colliding with an unrelated sibling project on 5173), so local
  end-to-end testing needs a repo-root `.env` (gitignored) with
  `CORS_ALLOWED_ORIGINS=http://localhost:5173,http://localhost:5175`.
  Not needed for the Vitest suite (MSW intercepts before any real
  request leaves the browser) or the deployed app (its allowed origin
  is a deploy-time config concern) — only for a human or session running
  both dev servers locally.

## Limitations

- The production bundle grew from ~389 KB to ~783 KB with this page's
  Recharts usage (the first real chart in the app) — expected, not a
  regression; code-splitting the chart libraries is a reasonable future
  optimization, deliberately not done here per "avoid premature
  optimization."
- `Highest variability` in Commercial Signals always shows exactly one
  class (whichever has the highest `volatility_cv`) rather than
  "unusually high" classes plural — there's no backend-provided
  threshold for "unusual," and inventing one client-side would be
  exactly the kind of frontend-side statistic this milestone prohibits.
