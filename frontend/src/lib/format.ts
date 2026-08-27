/**
 * Shared display-formatting helpers. Pure presentation — no statistic
 * here is computed from raw data; every input is already a final value
 * the backend returned (or, for the two counting helpers, a plain
 * tally of already-computed categorical values — see domainLabels.ts).
 *
 * `null`/`undefined` means the backend's own SafeFloat sanitizer
 * returned no value (e.g. NaN/Inf, or not computable) — a real,
 * meaningful signal, not a loading state. Callers show Skeleton while
 * loading and only reach these helpers once data has actually arrived,
 * so a null here always renders as an honest "not available" label,
 * never a loading placeholder.
 */

const NOT_AVAILABLE = "Not available";
const NOT_AVAILABLE_COMPACT = "—";

const countFormatter = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 });
const decimalFormatter = new Intl.NumberFormat("en-US", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const rawNumberFormatter = new Intl.NumberFormat("en-US", { maximumFractionDigits: 3 });
const dateFormatter = new Intl.DateTimeFormat("en-US", { year: "numeric", month: "short", day: "numeric" });

/** Large demand figures — thousands separators, whole units. */
export function formatCount(value: number | null | undefined, compact = false): string {
  if (value === null || value === undefined) return compact ? NOT_AVAILABLE_COMPACT : NOT_AVAILABLE;
  return countFormatter.format(value);
}

/** Demand figures that are meaningfully fractional (e.g. average daily
 * demand) — one decimal place. */
export function formatDecimal(value: number | null | undefined, compact = false): string {
  if (value === null || value === undefined) return compact ? NOT_AVAILABLE_COMPACT : NOT_AVAILABLE;
  return decimalFormatter.format(value);
}

/** A number whose scale/precision isn't known ahead of time — e.g. a
 * generic self-documenting "assumptions" table mixing days (7), a
 * fraction (0.95), and unitless weights (1.0, 4.0, 0.0) in one column.
 * formatDecimal's forced single decimal is wrong here (it turns 0.95
 * into a misleading "1.0" — found via real-backend verification on
 * the Supply Planning page's assumptions table); this shows each
 * number at its own natural precision instead, capped at 3 decimals
 * only to guard against floating-point noise. Prefer a more specific
 * formatter (formatDecimal/formatFraction/formatCount/...) whenever the
 * value's convention is actually known. */
export function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined) return NOT_AVAILABLE_COMPACT;
  return rawNumberFormatter.format(value);
}

/** A share/contribution/CR3 percentage already expressed 0-100 by the API. */
export function formatPercent(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined) return NOT_AVAILABLE_COMPACT;
  return `${value.toFixed(digits)}%`;
}

/** A date string -> "Dec 30, 2016". Handles both the bare "YYYY-MM-DD"
 * the API mostly uses (KpiSummary.period) and the space-separated
 * "YYYY-MM-DD HH:MM:SS" a pandas Timestamp sometimes serializes as
 * (KpiSummary.peak_date) — verified against the real running backend,
 * not assumed from the schema alone. A bare date is anchored to UTC
 * midnight so every viewer's timezone shows the same calendar day. */
export function formatDate(value: string | null | undefined): string {
  if (!value) return NOT_AVAILABLE_COMPACT;
  const isBareDate = /^\d{4}-\d{2}-\d{2}$/.test(value);
  const parsed = new Date(isBareDate ? `${value}T00:00:00Z` : value.replace(" ", "T"));
  if (Number.isNaN(parsed.getTime())) return value;
  return dateFormatter.format(parsed);
}

/** A date range as returned by KpiSummary.period. */
export function formatDateRange(start: string | null | undefined, end: string | null | undefined): string {
  if (!start && !end) return NOT_AVAILABLE;
  return `${formatDate(start)} – ${formatDate(end)}`;
}

/** A statistical p-value in conventional notation — never invents a
 * significance verdict, just renders the number readably. */
export function formatPValue(value: number | null | undefined): string {
  if (value === null || value === undefined) return NOT_AVAILABLE_COMPACT;
  if (value < 0.001) return "p < 0.001";
  return `p = ${value.toFixed(3)}`;
}

/** A regression slope (units/month) — signed, one decimal. */
export function formatSlope(value: number | null | undefined): string {
  if (value === null || value === undefined) return NOT_AVAILABLE_COMPACT;
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(1)} units/month`;
}

/** A 0-1 scale strength/statistic value (STL seasonal strength, CV) —
 * these are small-magnitude and meaningfully differ in the 2nd/3rd
 * decimal (e.g. weekly 0.234 vs. annual 0.553), so formatDecimal's
 * fixed 1-decimal convention (built for demand figures) would blur
 * them. Three decimals, unsigned. */
export function formatStrength(value: number | null | undefined): string {
  if (value === null || value === undefined) return NOT_AVAILABLE_COMPACT;
  return value.toFixed(3);
}

/** A coefficient-of-variation (volatility_cv) — unitless ratio, two
 * decimals is the convention already used for it on the Overview page. */
export function formatCV(value: number | null | undefined): string {
  if (value === null || value === undefined) return NOT_AVAILABLE_COMPACT;
  return value.toFixed(2);
}

/** A true 0-1 fraction (service_level / service_level_target from
 * backend/app/schemas/optimization.py — Pydantic `gt=0, lt=1`,
 * documented in docs/planning-assumptions.md as "0.95 (95%)"). This is
 * NOT the same convention as formatPercent's fields (contribution_pct,
 * wape, improvement_pct), which the API already expresses 0-100 — that
 * distinction is the whole reason this is a separate helper rather than
 * a silent *100 inside formatPercent, per M7.7's explicit warning
 * against conflating the two conventions. */
export function formatFraction(value: number | null | undefined, digits = 0): string {
  if (value === null || value === undefined) return NOT_AVAILABLE_COMPACT;
  return `${(value * 100).toFixed(digits)}%`;
}
