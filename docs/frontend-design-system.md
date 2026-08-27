# Frontend Design System

`frontend/src/styles/` (tokens, global rules), `frontend/src/components/ui/`
(14 reusable primitives), `frontend/src/components/layout/` (AppShell,
Sidebar, Topbar, PageContainer). Built in M7.3 as infrastructure only —
it renders no business data and consumes no API. M7.4+ pages compose
these pieces with real, API-sourced data.

## Design philosophy

This is an internal analytical tool for pharma commercial/supply
planning — not a marketing site or consumer product. The system
optimizes for:

- **Density over decoration.** Planners scan tables and metrics
  repeatedly; the system favors compact, legible layouts over
  whitespace-heavy "SaaS landing page" spacing.
- **Restraint.** One accent color (`--color-primary`), no gradients, no
  pill-shaped buttons, no decorative illustration, no motion beyond
  short, purposeful transitions. Nothing here should read as
  AI-generated or template-derived.
- **Trustworthiness.** Status is never color-only (see StatusBadge).
  Errors never leak raw backend detail (see ErrorState). Numbers are
  never fabricated by a component — every value-bearing prop is
  supplied by the caller from real data.
- **Native HTML first.** No component library (MUI/Chakra/Ant/Bootstrap),
  no utility-CSS framework (Tailwind), no date-picker library, no
  data-grid library. A native `<select>`, a pair of `<input type="date">`,
  and a semantic `<table>` cover everything this app needs.

## Design tokens (`frontend/src/styles/tokens.css`)

Every color, spacing value, radius, shadow, and font size used anywhere
in the app is a CSS custom property defined once in `tokens.css`. No
component `.module.css` file should contain a raw hex value or a magic
pixel number outside of `0`, `1px` borders, and the handful of
fixed-size icon dimensions passed to Lucide components.

**Color** — surfaces (`--color-bg/surface/surface-muted/surface-elevated`),
text (`--color-text-primary/secondary/muted/inverse`), borders
(`--color-border-subtle/border/border-strong`), the single primary accent
(`--color-primary` + `-hover`/`-muted`), semantic status colors with
muted backgrounds (`--color-success/warning/danger/info` +
`-muted`), and dedicated chart-role colors (`--color-observed`,
`--color-forecast`, `--color-interval`) kept separate from the generic
semantic colors so "observed vs. forecast" reads consistently across
every chart in M7.6+.

**Typography** — a role-based scale, not a generic h1–h6 scale:
page title, section title, card title, body, body-small, caption,
metric (large numeric display), table header, table body. Each role
defines size/line-height/weight together so a component picks a role,
not three separate values.

**Spacing** — `--space-xs` (4px) through `--space-2xl` (48px), six
steps. **Radius** — `sm`/`md`/`lg` (4/6/10px), nothing pill-shaped.
**Shadows** — `sm`/`md` only, both subtle.

**Layout** — `--sidebar-width` (240px), `--topbar-height` (56px),
`--page-max-width` (1280px).

## Global CSS (`frontend/src/styles/global.css`)

Box-sizing reset, body/typography defaults, link and focus-visible
styles, light form-element normalization, a `.visually-hidden` utility,
a `.skip-link` utility, a `prefers-reduced-motion` media query, and
`overflow-x: hidden` on `body` as a last line of defense against
accidental horizontal page scroll. Nothing component-specific lives
here — that belongs in the component's own `.module.css`.

## Component inventory (`frontend/src/components/ui/`)

Each component is its own directory with `Component.tsx`,
`Component.module.css`, and `Component.test.tsx`. All 14 are tested
with behavior-oriented (not snapshot) tests using React Testing Library.

| Component | Purpose |
|---|---|
| **Button** | primary/secondary/ghost/danger variants, sm/md sizes, loading state (disables + spinner, `aria-busy`), optional start/end icon. Icon-only buttons must pass `aria-label` — a dev-only console warning fires if omitted. |
| **Card** | title/subtitle/headerAction/footer, default/bordered/elevated variants. The general-purpose content container — used sparingly, not as a default wrapper for everything. |
| **Badge** | neutral/info/success/warning/danger, small inline label. |
| **StatusBadge** | wraps Badge; maps a domain status (healthy/warning/error/available/unavailable/pending) to an icon + color + text. Status is never color-only. |
| **Table** | semantic `<table>`, typed `TableColumn<T>[]`, numeric column alignment, compact/default density, optional sticky header, optional `onRowClick` (making rows keyboard-operable via `role="button"`), empty-state message, visually-hidden caption, horizontal-scroll container. No data-grid dependency. |
| **Tabs** | full ARIA tabs pattern (`role="tablist"/"tab"`, `aria-selected`, arrow-key navigation with wraparound). Fully generic — takes `items`/`value`/`onChange`; pages own their own tab labels (e.g. Trends/ATC/Seasonality/Anomalies is a M7.5 page concern, not baked into this component). |
| **Select** | native `<select>` wrapper with label, helper text, error text, `aria-describedby`/`aria-invalid` wiring. |
| **DateRange** | a pair of native `<input type="date">` elements, cross-constrained (start's max = end's value, end's min = start's value), accessible labels, optional error. |
| **Tooltip** | shown on hover *and* focus (keyboard-reachable), associated via `aria-describedby`, hidden via opacity/pointer-events (never `visibility:hidden`, which would remove it from the accessibility tree). For KPI/statistical/methodology definitions only — never for information required to use the page. |
| **Skeleton** | text/metric/card/table/chart variants, `role="status"`. Renders shape placeholders only — never a fabricated number. |
| **EmptyState** | icon + title + optional description/action, for a successful query that returned no rows. |
| **ErrorState** | icon + title + message + optional retry, `role="alert"`. Message resolution goes through the existing `describeApiError()` (`frontend/src/api/client.ts`) — this component never renders a raw `Error.message` or backend stack trace. |
| **SectionHeader** | eyebrow/title/description/action, configurable heading level (`as="h1"\|"h2"\|"h3"`) so pages control their own heading hierarchy. |
| **MetricCard** | label/value/unit/trend/trendDirection/status/tooltip built on Card + StatusBadge + Tooltip. Renders exactly what it's given — it does not format numbers or include any example data. |

## Layout architecture (`frontend/src/components/layout/`)

```
AppShell                      <- owns only mobile-drawer open/closed state
 ├─ Sidebar (nav, active route highlighting; becomes an off-canvas
 |   drawer + scrim under 1024px)
 └─ main
     ├─ Topbar (page title + optional :atcClass breadcrumb, derived
     |   from the route via components/layout/navigation.ts; an
     |   environment indicator from import.meta.env.MODE; mobile menu
     |   trigger — no fabricated user/avatar/notifications)
     └─ PageContainer (max-width 1280px, responsive padding, vertical
         rhythm) wrapping <Outlet /> for the active route
```

`routes/router.tsx` is unchanged from M7.2 — it still renders
`<RootLayout />` as the layout route. `RootLayout.tsx` now simply
re-exports `AppShell`, so every existing route path
(`/`, `/demand`, `/demand/atc/:atcClass`, `/forecast`,
`/forecast/:atcClass`, `/planning`, `/recommendations`, `/data-quality`)
renders inside the new shell with zero route-architecture changes.

`components/layout/navigation.ts` is the single source of truth for the
six primary nav sections (Overview/Demand Intelligence/Forecasting/
Supply Planning/Recommendations/Data Quality) and their icons — Sidebar
and Topbar both read from it so they can never drift out of sync.
Deliberately excluded: Profile, Messages, Notifications, Billing,
Settings — none of those exist in this application.

## Responsive strategy

Single breakpoint at **1024px** (matching the 768–1024px tablet range
called out in the design brief — tablet gets the mobile nav treatment,
not a third distinct layout):

- **≥1024px (desktop):** Sidebar is a permanent 240px column; Topbar's
  menu button is hidden.
- **<1024px (tablet/mobile):** Sidebar becomes a fixed-position,
  off-canvas drawer (`transform: translateX(-100%)`) toggled by the
  Topbar's menu button, with a click-to-dismiss scrim.
- **<768px:** `PageContainer` reduces its padding/gap one step
  (`--space-lg`/`--space-2xl` → `--space-md`/`--space-xl`).

Every wide element (Table, and any chart added in M7.6+) scrolls
horizontally within its own container; `global.css` sets
`overflow-x: hidden` on `body` as a backstop so a layout mistake in a
future page can't produce page-level horizontal scroll.

## Accessibility strategy

- Semantic HTML first: `<nav>`, `<header>`, `<main>`, `<table>`,
  native form controls — ARIA is added only where semantic HTML can't
  express the pattern (Tabs' `role="tablist"`, Tooltip's
  `role="tooltip"`).
- One `<h1>` per page (the page's own heading — Topbar's title is a
  styled `<span>`, not a competing heading).
- Every interactive element is reachable and operable by keyboard;
  `:focus-visible` is styled globally and never suppressed.
- Icon-only controls have `aria-label` (enforced with a dev warning on
  Button; applied directly on Sidebar's close button and Topbar's menu
  button).
- Status is always paired with text/icon, never color alone
  (StatusBadge, MetricCard's trend arrows).
- `prefers-reduced-motion: reduce` collapses all transitions/animations
  to near-zero duration globally.
- This is a good-faith accessibility implementation, not a certified
  WCAG audit — no AA/AAA conformance claim is made.

## Usage conventions for M7.4+

- Fetch with the existing hooks (`frontend/src/hooks/use*.ts`); render
  `Skeleton` while `isLoading`, `ErrorState` (passing the hook's
  `error`) while `isError`, `EmptyState` when the data resolved but is
  empty, and the real content otherwise. Never render a component in a
  state that implies data is present when it isn't.
- Compose pages from `SectionHeader` + `Card`/`Table`/`MetricCard` +
  Recharts (added when M7.6 needs it) — don't invent new one-off
  layout patterns where an existing primitive covers the case.
- Every value passed into `MetricCard`, `Table`, `StatusBadge`, etc.
  must trace back to an API response. No hardcoded example numbers,
  percentages, or savings figures — the fabrication rule that has held
  since M2 applies to the frontend exactly as it does to the backend.
- Tabs' generic `items` prop is where page-specific labels
  (Trends/ATC/Seasonality/Anomalies for Demand Intelligence, etc.) get
  defined — in the page, not in the shared component.

## What is intentionally not part of this system

- No component library, no CSS/utility framework, no state-management
  library (TanStack Query's cache is the only "global state" the app
  has), no animation library, no date-picker package, no data-grid
  package.
- No user/account surface: no avatar, no profile menu, no notification
  center, no settings page. This app has no concept of a logged-in
  user.
- No business data, charts of real numbers, or KPI values — that is
  entirely M7.4 through M7.9's scope, page by page.
- No dark theme. One light, professional palette; revisit only if a
  real requirement emerges.
