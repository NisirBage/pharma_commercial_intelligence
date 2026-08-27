# Frontend — Data Quality Page

## Purpose

Not a new milestone page in the M7.4-M7.9 analytical sequence — this
closes a **discovery-audit finding**: the "Product Hardening" pass that
followed M7.9 found `/data-quality` was still the M7.2 scaffold stub
("Scaffolding placeholder — implemented in M7.9"), despite being
reachable from two live places in the app — the Sidebar's own top-level
nav item, and the Executive Overview's "View full report →" link. This
page implements the real report those two links promise.

## Route

`/data-quality` (unchanged path, registered since M7.2 —
`frontend/src/routes/router.tsx`).

## API consumed

`GET /api/v1/data-quality` via the pre-existing `useDataQuality()` hook
(unchanged — same hook, same `queryKeys.dataQuality` key, same
`STALE_TIME.LONG` the Overview page's summary card has used since M7.4).
No new endpoint, no new hook, no backend change. `useHealth()` (also
pre-existing) supplies the API-status line, matching the Overview's own
pairing of the two.

## What this page adds beyond the Overview summary

The Overview's `DataQualitySection` deliberately keeps the data-quality
story compact (overall status, a per-check status badge, the failing
check's note only, the documented monthly warning, and a single summed
record count). The full response
(`backend/app/schemas/data_quality.py::DataQualityResponse`) carries
three things Overview never surfaces:

- **`kaggle_dataset_id`** — the dataset's own source citation, shown
  nowhere else in the app.
- **A note for every reconciliation check**, not just the failing one —
  Overview only shows `note` when `!reconciled`; this page shows Daily's
  and Weekly's own "Reconciled" notes too, since a full report should
  say why a check passed, not only why one didn't.
- **Per-file `total_records`/`valid_records`/`rejected_records`** for
  all 4 real source files (`saleshourly.csv`, `salesdaily.csv`,
  `salesweekly.csv`, `salesmonthly.csv`) — Overview only ever showed the
  sum of `total_records`. Rejected-record counts appear on no other page
  in the app.

## Reused components

`SectionHeader` (3 `<section aria-labelledby>` subsections, same
pattern as every other M7.5-M7.9 page), `Card`, `StatusBadge`
(`getDataQualityStatus` from `domainLabels.ts`, unchanged since M7.4),
`Table` (self-contained horizontal scroll, same as Concentration/ATC
Analysis/Supply Planning's scenario table), `EmptyState`, `ErrorState`,
`Skeleton`, `formatCount` from `format.ts`. No new UI primitive, no new
formatter, no new domain-label mapping was needed.

## Loading / error / empty behavior

A single `useDataQuality()` query gates the whole page (there's only one
endpoint to fail here, unlike Overview's independently-gated sections):
`Skeleton` while loading, `ErrorState` with retry on failure, and two
*distinct* empty states nested inside the loaded page — "No
reconciliation checks available" and "No source files available" — for
the (currently hypothetical, but schema-legal) case of an empty array in
either field, never conflated with the true zero-recommendations-style
"API returned nothing at all" case (which itself is covered by
`ErrorState`/`EmptyState` at the top level for a missing `data` object).

## Accessibility

Exactly one `<h1>` ("Data Quality"), three `<h2>` subsections each in
their own `<section aria-labelledby>` (mirrors every other page's
pattern exactly). Status is never color-only — every `StatusBadge`
pairs an icon and a text label. The file-summaries table has a visually-
hidden `<caption>` naming its content, and reuses the same accessible
`Table` component every other page's tables use.

## Responsive behavior

Verified against the real running app at 375px and 768px with the page
fully populated (4-row file table, 3-row reconciliation list, the
monthly warning banner) — no horizontal overflow at either width.

## Tests

`frontend/src/pages/DataQuality/DataQuality.test.tsx` — 12 tests:
loading, error+retry (with an explicit non-empty-state assertion),
distinct empty states for reconciliation/file-summaries; overall
status + dataset id (scoped to the Overall Status region, since the
default fixture's Monthly reconciliation check is *also* "warn" —
an unscoped query would be ambiguous between the two); every
reconciliation check's own note, including the two passing ones; the
monthly warning always rendering; per-file record counts including a
real, meaningful "0 rejected" value; the API-status line; a
hardcoded-value guard (every value changes when the mocked response
changes, scoped correctly where the fixture legitimately repeats a
status word); and 2 accessibility tests (heading structure, status
never color-only).

Full frontend suite: **245/245 passing** across 28 files (up from 233 —
+12 new, no regression). `npx tsc -b`: clean. `npm run lint` (oxlint):
clean. `npm run build`: succeeds (877.32 kB / 256.02 kB gzip, consistent
incremental growth from M7.9's 873.90 kB / 255.20 kB — not a new
concern; still not code-split, per the project's established stance).
Backend regression: **285/285 passing**, unaffected (no backend files
touched).

## Real-browser verification

Performed against the real running backend (port 8020) and frontend dev
server (port 5175), with `frontend/.env.local` pointing at the real
backend for the duration only.

- `curl`'d `/api/v1/data-quality` directly: confirmed the real response
  — 4 source files, all 0 rejected records (53,010 total records
  combined, matching the figure already cited elsewhere in the app),
  overall status `warn`, the documented monthly-reconciliation note.
- Loaded `/data-quality` directly: all 4 files, all 3 reconciliation
  checks (including both passing "Reconciled" notes), the dataset id,
  and the monthly warning rendered correctly with correct em-dashes.
- Clicked Overview's "View full report →": correctly landed on this
  now-real page instead of the former dead stub.
- No horizontal overflow at 375px or 768px with the page fully
  populated.
- Console errors observed were the same transient early-load
  CORS/connection-refused entries seen in every prior real-browser
  session in this project (the dev backend hadn't finished registering
  CORS on the very first request wave) — all requests succeeded on
  retry, and the rendered page had zero missing data.

**No real-data bugs were found** — no fix was required as a result of
real-browser verification.

## Limitations

- This page reads the same single GET the Overview summary already
  reads; there is no server-side filtering, sorting, or pagination
  parameter for either the reconciliation list or the file summaries
  (none is needed at this response size — 3 and 4 rows respectively).
- The API-status line queries `useHealth()` in addition to
  `useDataQuality()` — a second independent GET, matching what Overview
  already does for the same purpose. It is not gated behind the main
  page's loading/error state (it's supplementary context, not the
  page's primary subject), so it can legitimately appear slightly later
  or be silently absent if `/health` fails, without blocking the rest of
  the report.
