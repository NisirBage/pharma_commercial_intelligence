# Frontend — Recommendations Intelligence Page (M7.8)

## Purpose

`/recommendations` is the platform's "action layer" — the page that answers
*what should a planner pay attention to, why, how confident is the system,
and what evidence backs it up.* Every earlier page (Demand, Forecast, Supply
Planning) surfaces a signal or a computed policy; this page is the only one
that presents pre-packaged, per-class *explanations* combining those
signals into a single human-readable recommendation with its own evidence,
assumptions, expected effect, confidence, and limitations.

It consumes exactly one endpoint, `GET /api/v1/recommendations`, via the
pre-existing `useRecommendations` hook (unchanged — it, its API wrapper,
and its Zod schema all already existed and needed no changes for this
milestone).

## Recommendation semantics (backend-verified, `app/optimization/recommendations.py`)

- **Granularity**: exactly one recommendation per observed ATC class —
  never an aggregate, portfolio-level, or cross-class item. The real
  backend returns 8 (one per `ATC_CLASSES` entry), confirmed for all 3
  scenarios via direct `curl` against the running backend.
- **Source signals**: each recommendation blends findings from M3
  (demand/contribution/volatility analytics), M4 (forecasting/model
  selection and its own backtested WAPE), and M5 (the scenario's own
  reorder-point/safety-stock calculation). Three classes (N02BE, N05C, R03)
  get a rich, class-specific `build_recommendation()` branch; every other
  class gets a generic fallback sentence ("Standard {scenario} scenario
  policy applies — no special-case evidence identified for {atc_class}.").
  Both are rendered identically by the page — the frontend does not
  distinguish "special-cased" from "generic" recommendations, because the
  API doesn't expose that distinction as a field.
- **No priority/severity/status/action field exists.** The schema
  (`RecommendationItemSchema`, mirrored exactly by
  `backend/app/schemas/recommendations.py`) has exactly 7 fields:
  `atc_class`, `recommendation`, `evidence`, `assumptions`,
  `expected_effect`, `confidence`, `limitations`. There is no `priority`,
  `severity`, `status`, `impact` (as a distinct field — `expected_effect`
  serves that role as free text), or executable-action field. The page
  does not invent any of these.
- **No execute/apply endpoint exists.** The recommendations API is
  GET-only. The page never renders an "Apply"/"Execute" button — every
  recommendation is presented as informational guidance only.

## Ranking / order

`build_all_recommendations()` is a dict comprehension over
`demand_inputs` (`{atc: build_recommendation(...) for atc in
demand_inputs}`), and the service layer maps `recs.values()` directly into
the response array with no explicit sort. Empirically, against the real
running backend, the order for all 3 scenarios was consistently
alphabetical: `M01AB, M01AE, N02BA, N02BE, N05B, N05C, R03, R06` — the same
order as the `ATC_CLASSES` constant. The page **preserves this order as
given by the API** and never re-sorts it; this is enforced by a dedicated
ordering test using a 3-item fixture in a deliberately non-alphabetical
sequence (`R06, N05C, N02BE`), asserting the DOM order matches exactly.
Confidence filtering (the one client-side control) also preserves this
relative order — it only removes non-matching items, it never reorders.

## Confidence semantics

`_confidence_from_model_evidence()` (`app/optimization/recommendations.py`)
returns exactly one of three **categorical strings** —
`"low"`, `"medium"`, `"medium-high"` — derived purely from which M4 model
was selected for that class and its own backtested WAPE. There is no
`"high"` tier and no numeric score anywhere in the response; confidence is
**never** a 0–1 fraction, a 0–100 percentage, or any other numeric scale.
Real-backend responses for all 3 scenarios only ever produced these 3
exact strings, confirming the schema.

Because of this, `getRecommendationConfidenceDisplay()`
(`frontend/src/lib/domainLabels.ts`) maps the raw string directly to a
label + `Badge` variant (`low` → warning, `medium` → neutral,
`medium-high` → success) with **no** numeric formatting applied — `formatFraction`/`formatPercent` are deliberately not used here. Unlike
trend direction (a neutral fact), confidence here is treated as a
genuinely positive attribute (more reliable model → more reliable
recommendation), so it gets a warning/neutral/success gradient rather than
a purely informational one.

## Evidence, assumptions, limitations, expected effect

All four are backend-authored prose strings (arrays for evidence/
assumptions/limitations, a single string for expected effect), rendered
**verbatim** — the frontend never rewrites, truncates, or re-derives them.
Real evidence text legitimately contains numeric detail the backend
already computed (e.g. "validation WAPE 41.2%", "~49.4% of total observed
demand") — this is the API's own already-formatted figure embedded in a
sentence, not something the frontend formats, and is left untouched.

- **Evidence** and **limitations** are always shown directly on the card
  (never hidden) — both are central to "why does this recommendation
  exist," and limitations are sometimes class-specific caveats worth
  surfacing prominently.
- **Assumptions** are, on real data, the same 1–2 standard sentences on
  every card (`STANDARD_ASSUMPTIONS` in the backend — a fixed, scenario-
  wide disclaimer, not decision-relevant per-class information). To keep
  8 cards scannable without dropping the information, assumptions sit
  behind a native `<details>`/`<summary>` disclosure — no ARIA needed, and
  keyboard-operable for free (native semantics: `Enter`/`Space` on a
  focused `<summary>` toggles `open`).
- **Expected effect** is shown as its own labeled sub-block on every card
  that has one (all real recommendations do).

## Filters

- **`scenario`** (`conservative` | `balanced` | `lean`) is the one
  server-side parameter the endpoint accepts — implemented as a `Select`
  that re-queries the API on change (verified in the real browser: exactly
  one new network request per scenario change, with the correct
  `?scenario=...` value, and the displayed numbers/text update to that
  scenario's own values — e.g. N05C's absolute safety-stock exposure was
  2.95 units for `balanced` and 2.30 units for `lean` on the real
  backend).
- **Confidence** (`low` | `medium` | `medium-high`) is **client-side
  only** — there is no server-side confidence filter, and the response is
  small and fully bounded (at most 8 items, one per real ATC class), so
  filtering in memory is appropriate per the milestone's own filtering
  guidance. It filters a derived array and never mutates
  `data.recommendations` — proven by a test that asserts the "Total
  Recommendations" KPI (computed from the full, unfiltered array) stays
  correct while the visible card list shrinks.

## Loading / error / empty states

Backed by 3 mutually exclusive branches on `isError` / `isLoading` /
`recommendations.length === 0`, so a request failure can never render as
"no recommendations" — verified by a dedicated test that forces a 503 and
asserts the error UI (with working Retry) appears, while the true-empty
message is explicitly asserted absent. A **separate** empty state exists
for "filter matched nothing" (distinct copy from "API returned zero
recommendations"), so a client-side filter miss is never confused with a
genuinely empty API response.

## Accessibility

- Page heading is a real `<h1>` (`SectionHeader as="h1"`).
- Both filter controls are properly labeled `<Select>`s
  (`getByLabelText` works for both in tests).
- Confidence is never conveyed by color alone — every badge carries its
  own text label (e.g. "Low confidence"), not just a color variant.
- The assumptions disclosure is a native `<details>`/`<summary>` — fully
  keyboard operable with zero custom JS or ARIA, and immune to the
  "`<div>` pretending to be a button" anti-pattern by construction.
- Verified interactively in the real browser: clicking a summary toggles
  the underlying `<details>` element's `open` property correctly.

## Responsive verification

Checked against the real running app (not just component tests) at
375px and 768px viewport widths: `document.documentElement.scrollWidth`
never exceeded `window.innerWidth` at either breakpoint — no horizontal
overflow, no clipped text observed in the rendered card content.

## Charts

None added. Recommendations are fundamentally a decision/list problem —
per the milestone's own guidance, a chart was not added just because
other pages have one; nothing in this response shape (7 short fields per
item, no time series, no distribution worth visualizing beyond the 3
already-adequate confidence-count KPI tiles) benefits from a chart.

## Tests

`frontend/src/pages/Recommendations/Recommendations.test.tsx` — 16 tests:
loading state; error state with retry (and explicit non-empty-state
assertion); true empty state (API returns zero items); full-field
rendering (recommendation text, expected effect, ATC class); confidence
rendered as one of the 3 exact categorical labels only (never a `%` or
digit inside the badge itself — scoped narrowly to the badge text nodes,
not a page-wide "no % anywhere" check, since evidence text legitimately
contains real percentages); evidence and limitations visible without
interaction; the assumptions disclosure's keyboard-accessible toggle
(asserted via the `<details>` element's own `open` property, scoped to
one specific card via `within()` — necessary because all 3 fixture items
share byte-identical assumptions text, so page-wide text queries can't
disambiguate which card's content is which, and jsdom does not implement
native `<details>` closed-content CSS hiding the way a real browser does,
so asserting on rendered-text presence/absence before/after click is not
reliable in this test environment); backend-order preservation using a
deliberately non-alphabetical fixture; 4 filtering tests (apply, distinct
empty-state-for-filter-miss, reset, and scenario-change re-queries the API
with the correct param); a hardcoded-value guard (every rendered value
changes when the mocked response changes, proving nothing is hardcoded);
and 2 accessibility tests (labeled controls, real `<h1>`).

Full frontend suite: **217/217 passing** across 27 files (no regression).
`npx tsc -b`: clean. `npm run lint` (oxlint): clean. `npm run build`:
succeeds (868.98 kB / 254.10 kB gzip — the pre-existing chunk-size warning
from earlier milestones, not a new regression). Backend regression:
**285/285 passing**, unchanged (no backend files were touched).

## Real-browser verification

Performed against the actual running backend (`pharma-backend`, port
8020) and frontend dev server (`pharma-frontend`, port 5175), with
`frontend/.env.local` pointing at the real backend for the duration of
verification only (created before, deleted immediately after).

- `curl`'d `/api/v1/recommendations` directly for all 3 scenarios:
  confirmed 8 items each, alphabetical ATC order, and the confidence
  distribution (2 low / 4 medium / 2 medium-high) held for every scenario.
- Loaded `/recommendations` in the browser: all 8 real cards rendered
  correctly, em-dashes and evidence percentages displayed correctly (no
  mangled encoding — the earlier mojibake-looking output was purely a
  local-terminal `curl`/Python display artifact, not a real backend or
  frontend encoding bug — the browser's own UTF-8 JSON decoding rendered
  every em-dash and percent sign correctly).
- KPI tiles matched the API's own real distribution exactly: Total 8, Low
  2, Medium 4, Medium-High 2.
- Clicked an assumptions `<summary>`: the underlying `<details>` toggled
  `open` correctly, matching the unit-test assertion.
- Set the confidence filter to "low": list narrowed to the matching real
  cards (N05C, R03), KPI tiles stayed at the full 8/2/4/2 (unfiltered),
  and **zero** new network requests fired — confirming the filter is
  genuinely client-side.
- Switched scenario from `balanced` → `lean`: exactly one new request
  fired (`GET /api/v1/recommendations?scenario=lean`), the "Scenario:"
  label updated, and class-specific numeric evidence updated to the new
  scenario's own values (e.g. N05C's absolute safety-stock figure changed
  from 2.95 → 2.30 units) — no stale data from the previous scenario
  leaked through.
- Console errors observed were all for **other, unrelated** endpoints
  (`/health`, `/api/v1/kpis/summary`, `/api/v1/data-quality`,
  `/api/v1/analytics/atc` — CORS failures from pre-existing app-shell
  background fetches) — **none** referenced `/api/v1/recommendations`.
  This is a pre-existing environment/CORS-config gap unrelated to this
  page and out of scope for this milestone (no source under M7.8 touches
  those endpoints).
- Verified no horizontal overflow at 375px and 768px viewport widths.

**No real-data bugs were found in the Recommendations page itself** — no
fix was required as a result of real-browser verification.

## Limitations / assumptions (this implementation)

- The 8/2/4/2 KPI counts (total + confidence-tier tallies) are
  **frontend-derived aggregates** computed client-side from the fetched
  array — the API itself does not provide any pre-aggregated count or
  summary object. These are presentation conveniences, not backend facts.
- The `<details>`-based assumptions disclosure is a **frontend
  presentation decision** (assumptions are near-identical boilerplate
  across cards on real data) — the API does not signal that assumptions
  should be collapsed or expanded; a different UI could equally show them
  inline.
- Ordering preservation relies on the real backend's dict-iteration order
  staying alphabetical, which was empirically verified against the
  running instance but is not a documented contract in the backend
  source itself (`build_all_recommendations()` iterates whatever order
  `demand_inputs` — ultimately `build_all_series(df)`'s own dict order —
  produces). If that upstream ordering ever changed, this page would
  continue to preserve whatever new order the API returns (by design —
  it never re-sorts), so no page-level assumption breaks even if the
  empirical order changes.
- No pagination exists or is needed at this response size (≤ 8 items);
  the page assumes the full response fits comfortably in memory and on
  screen, which held true on real data.
