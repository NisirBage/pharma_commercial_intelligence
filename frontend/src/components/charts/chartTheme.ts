/**
 * Chart color/style constants for M7.5+ Recharts usage. Mirrors the
 * chart-role and semantic tokens in styles/tokens.css — SVG attributes
 * (Recharts' `stroke`/`fill` props) render as plain attribute values,
 * not through the CSS cascade, so they can't resolve `var(--...)`
 * directly. Keep these in sync by hand if tokens.css changes.
 *
 * No dataset, series, or business value lives here — this is presentation
 * convention only, established ahead of M7.5/M7.6 actually rendering
 * charts.
 */

/** Series-role colors — "observed vs. forecast" must read the same way
 * in every chart across the app, so a page picks a role, not a color. */
export const CHART_SERIES_COLORS = {
  observed: "#2b3648",
  forecast: "#1c4f9c",
  interval: "#c3d5ee",
} as const;

/** Semantic status colors, for charts that need to flag e.g. an anomaly
 * point or a warning threshold — same palette as StatusBadge/Badge. */
export const CHART_STATUS_COLORS = {
  success: "#1a7f4e",
  warning: "#92600a",
  danger: "#b3261e",
  info: "#1d5fb0",
} as const;

/** Chrome shared by every chart: gridlines, axis ticks, reference lines. */
export const CHART_CHROME = {
  grid: "#edeef1",
  axis: "#767f8f",
  axisLabel: "#454e5c",
} as const;

/** Default height (px) for a ChartCard's chart area when the caller
 * doesn't specify one. Recharts' `ResponsiveContainer` fills this. */
export const DEFAULT_CHART_HEIGHT = 320;
