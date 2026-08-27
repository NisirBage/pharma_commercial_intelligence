/**
 * Maps backend-computed categorical strings to a display label + Badge
 * variant. The classification itself always comes from the API
 * (app/analytics/trends.py's OLS + p<0.05 test; app/etl/quality_report.py's
 * pass/warn/fail rollup) — nothing here re-derives a verdict, it only
 * picks how an already-computed verdict is labeled and colored so every
 * page presents the same string the same way.
 */

import type { BadgeVariant } from "../components/ui/Badge/Badge";
import type { Status as StatusBadgeStatus } from "../components/ui/StatusBadge/StatusBadge";

/** app/analytics/trends.py: SIGNIFICANCE_ALPHA = 0.05; "growing"/"declining"
 * require p < 0.05, "stable_or_no_significant_trend" otherwise. Growing
 * and declining are deliberately not colored success/danger — a demand
 * trend's direction isn't inherently good or bad for a planning
 * stakeholder, so "info"/"warning" (noteworthy / needs attention) is
 * used instead of a value judgment the backend never made. */
const TREND_LABELS: Record<string, { label: string; variant: BadgeVariant }> = {
  growing: { label: "Growing", variant: "info" },
  declining: { label: "Declining", variant: "warning" },
  stable_or_no_significant_trend: { label: "No significant trend", variant: "neutral" },
};

export function getTrendDisplay(classification: string): { label: string; variant: BadgeVariant } {
  return TREND_LABELS[classification] ?? { label: "Insufficient data", variant: "neutral" };
}

/** app/etl/quality_report.py: overall_status and per-check status are
 * both "pass" | "warn" | "fail". */
const DATA_QUALITY_STATUS: Record<string, StatusBadgeStatus> = {
  pass: "healthy",
  warn: "warning",
  fail: "error",
};

export function getDataQualityStatus(status: string): StatusBadgeStatus {
  return DATA_QUALITY_STATUS[status] ?? "pending";
}

/** app/schemas/anomalies.py: AnomalySeverity = "low" | "medium" | "high",
 * assigned by app/analytics/anomalies.py's z-score/IQR magnitude
 * thresholds — severity (unlike trend direction) is a legitimate
 * escalating-urgency scale, so it does get success/warning/danger. */
const ANOMALY_SEVERITY: Record<string, { label: string; variant: BadgeVariant }> = {
  low: { label: "Low", variant: "neutral" },
  medium: { label: "Medium", variant: "warning" },
  high: { label: "High", variant: "danger" },
};

export function getAnomalySeverityDisplay(severity: string): { label: string; variant: BadgeVariant } {
  return ANOMALY_SEVERITY[severity] ?? { label: severity, variant: "neutral" };
}

/** app/services/forecast_service.py: `autocorrelation_detected` is
 * `lb_pvalue < 0.05` on the Ljung-Box test of a forecast's backtest
 * residuals — detected autocorrelation means the model is leaving
 * predictable structure on the table (a real caveat, "warning"), not
 * detected means the residuals look like white noise (a positive
 * diagnostic sign, "success"). */
export function getAutocorrelationDisplay(detected: boolean): { label: string; variant: BadgeVariant } {
  return detected
    ? { label: "Autocorrelation detected", variant: "warning" }
    : { label: "No autocorrelation detected", variant: "success" };
}
