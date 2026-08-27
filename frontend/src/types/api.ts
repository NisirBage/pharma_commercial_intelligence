/**
 * Zod schemas mirroring backend/app/schemas/*.py field-for-field.
 *
 * These are the ONLY place API response shapes are defined on the
 * frontend — every api/*.ts module validates against a schema from this
 * file, and every schema here was written by reading the actual Pydantic
 * models (backend/app/schemas/), never guessed. If the backend contract
 * changes, this file (and only this file) should need updating, and a
 * mismatch fails loudly via ApiClientValidationError (see api/client.ts)
 * rather than silently rendering wrong data.
 */

import { z } from "zod";

// ---------------------------------------------------------------------
// Common envelope (backend/app/schemas/common.py)
// ---------------------------------------------------------------------

export const ErrorDetailSchema = z.object({
  field: z.string().nullable().optional(),
  message: z.string(),
});

export const ErrorBodySchema = z.object({
  code: z.string(),
  message: z.string(),
  details: z.array(ErrorDetailSchema).default([]),
});

export const ErrorResponseSchema = z.object({
  error: ErrorBodySchema,
});

export const ResponseMetadataSchema = z.object({
  generated_at: z.string(),
  source: z.string().nullable().optional(),
});
export type ResponseMetadata = z.infer<typeof ResponseMetadataSchema>;

// ---------------------------------------------------------------------
// Health (backend/app/schemas/health.py)
// ---------------------------------------------------------------------

export const HealthSchema = z.object({
  status: z.string(),
  version: z.string(),
  environment: z.string(),
  database: z.string(),
});
export type Health = z.infer<typeof HealthSchema>;

// ---------------------------------------------------------------------
// KPI summary (backend/app/schemas/kpis.py)
// ---------------------------------------------------------------------

export const PeriodRangeSchema = z.object({
  start: z.string().nullable(),
  end: z.string().nullable(),
});
export type PeriodRange = z.infer<typeof PeriodRangeSchema>;

export const KpiSummarySchema = z.object({
  total_demand: z.number().nullable(),
  average_daily_demand: z.number().nullable(),
  peak_daily_demand: z.number().nullable(),
  peak_date: z.string().nullable(),
  dominant_atc_class: z.string().nullable(),
  dominant_atc_share_pct: z.number().nullable(),
  period: PeriodRangeSchema,
});
export type KpiSummary = z.infer<typeof KpiSummarySchema>;

// ---------------------------------------------------------------------
// Sales trends (backend/app/schemas/sales.py)
// ---------------------------------------------------------------------

export const GrainSchema = z.enum(["daily", "weekly", "monthly"]);
export type Grain = z.infer<typeof GrainSchema>;

export const TrendPointSchema = z.object({
  period: z.string(),
  units_sold: z.number().nullable(),
});
export type TrendPoint = z.infer<typeof TrendPointSchema>;

export const SalesTrendsSchema = z.object({
  atc_class: z.string().nullable(),
  grain: GrainSchema,
  start_date: z.string(),
  end_date: z.string(),
  points: z.array(TrendPointSchema),
});
export type SalesTrends = z.infer<typeof SalesTrendsSchema>;

// ---------------------------------------------------------------------
// ATC analytics (backend/app/schemas/analytics.py)
// ---------------------------------------------------------------------

export const AtcPerformanceSchema = z.object({
  atc_class: z.string(),
  total_demand: z.number().nullable(),
  average_daily_demand: z.number().nullable(),
  peak_daily_demand: z.number().nullable(),
  trough_daily_demand: z.number().nullable(),
  contribution_pct: z.number().nullable(),
  trend_slope: z.number().nullable(),
  trend_classification: z.string(),
  trend_p_value: z.number().nullable(),
  volatility_cv: z.number().nullable(),
});
export type AtcPerformance = z.infer<typeof AtcPerformanceSchema>;

export const ConcentrationEntrySchema = z.object({
  atc_code: z.string(),
  share_pct: z.number().nullable(),
  cumulative_share_pct: z.number().nullable(),
});
export type ConcentrationEntry = z.infer<typeof ConcentrationEntrySchema>;

export const DemandConcentrationSchema = z.object({
  ranked: z.array(ConcentrationEntrySchema),
  concentration_ratio_top3_pct: z.number().nullable(),
  hhi: z.number().nullable(),
  hhi_scale_note: z.string(),
});
export type DemandConcentration = z.infer<typeof DemandConcentrationSchema>;

export const AtcPerformanceResponseSchema = z.object({
  classes: z.array(AtcPerformanceSchema),
  dominant_classes: z.array(z.string()),
  concentration: DemandConcentrationSchema,
});
export type AtcPerformanceResponse = z.infer<typeof AtcPerformanceResponseSchema>;

// ---------------------------------------------------------------------
// Anomalies (backend/app/schemas/anomalies.py)
// ---------------------------------------------------------------------

export const AnomalyMethodSchema = z.enum(["rolling_zscore", "iqr"]);
export type AnomalyMethod = z.infer<typeof AnomalyMethodSchema>;

export const AnomalySeveritySchema = z.enum(["low", "medium", "high"]);
export type AnomalySeverity = z.infer<typeof AnomalySeveritySchema>;

export const AnomalyItemSchema = z.object({
  atc_class: z.string(),
  timestamp: z.string(),
  observed: z.number().nullable(),
  expected: z.number().nullable(),
  deviation_pct: z.number().nullable(),
  anomaly_score: z.number().nullable(),
  direction: z.string(),
  severity: z.string(),
  method: z.string(),
});
export type AnomalyItem = z.infer<typeof AnomalyItemSchema>;

export const AnomaliesResponseSchema = z.object({
  atc_class: z.string().nullable(),
  method: z.string(),
  total_count: z.number(),
  anomalies: z.array(AnomalyItemSchema),
});
export type AnomaliesResponse = z.infer<typeof AnomaliesResponseSchema>;

// ---------------------------------------------------------------------
// Seasonality (backend/app/schemas/seasonality.py — M7.1.5)
// ---------------------------------------------------------------------

export const DayOfWeekEffectSchema = z.object({
  h_statistic: z.number().nullable(),
  p_value: z.number().nullable(),
  significant: z.boolean().nullable(),
  mean_units_by_weekday: z.record(z.string(), z.number()).nullable(),
  available: z.boolean(),
  reason: z.string().nullable().optional(),
});
export type DayOfWeekEffect = z.infer<typeof DayOfWeekEffectSchema>;

export const HourOfDayEffectSchema = z.object({
  h_statistic: z.number().nullable(),
  p_value: z.number().nullable(),
  significant: z.boolean().nullable(),
  mean_units_by_hour: z.record(z.string(), z.number()).nullable(),
  available: z.boolean(),
  reason: z.string().nullable().optional(),
});
export type HourOfDayEffect = z.infer<typeof HourOfDayEffectSchema>;

export const SeasonalStrengthInfoSchema = z.object({
  strength: z.number().nullable(),
  cycle_period: z.number().nullable(),
  n_periods: z.number().nullable(),
  interpretation: z.string().nullable(),
  available: z.boolean(),
  reason: z.string().nullable().optional(),
});
export type SeasonalStrengthInfo = z.infer<typeof SeasonalStrengthInfoSchema>;

export const SeasonalityResponseSchema = z.object({
  atc_class: z.string(),
  day_of_week_effect: DayOfWeekEffectSchema,
  hour_of_day_effect: HourOfDayEffectSchema,
  weekly_seasonal_strength: SeasonalStrengthInfoSchema,
  annual_seasonal_strength: SeasonalStrengthInfoSchema,
});
export type SeasonalityResponse = z.infer<typeof SeasonalityResponseSchema>;

// ---------------------------------------------------------------------
// Forecasting (backend/app/schemas/forecasts.py)
// ---------------------------------------------------------------------

export const ForecastPointSchema = z.object({
  date: z.string(),
  prediction: z.number().nullable(),
  lower: z.number().nullable(),
  upper: z.number().nullable(),
});
export type ForecastPoint = z.infer<typeof ForecastPointSchema>;

export const ForecastMetricsSchema = z.object({
  mae: z.number().nullable(),
  rmse: z.number().nullable(),
  wape: z.number().nullable(),
  mase: z.number().nullable(),
});
export type ForecastMetrics = z.infer<typeof ForecastMetricsSchema>;

export const ForecastResponseSchema = z.object({
  atc_class: z.string(),
  horizon_days: z.number(),
  model: z.string(),
  uncertainty_method: z.string(),
  forecast: z.array(ForecastPointSchema),
  metrics: ForecastMetricsSchema,
});
export type ForecastResponse = z.infer<typeof ForecastResponseSchema>;

export const LjungBoxResultSchema = z.object({
  lags: z.number(),
  lb_stat: z.number().nullable(),
  lb_pvalue: z.number().nullable(),
  autocorrelation_detected: z.boolean(),
});
export type LjungBoxResult = z.infer<typeof LjungBoxResultSchema>;

export const ResidualDiagnosticsSchema = z.object({
  n_residuals: z.number(),
  mean_residual: z.number().nullable(),
  std_residual: z.number().nullable(),
  pct_days_underpredicted: z.number().nullable(),
  pct_days_overpredicted: z.number().nullable(),
  ljung_box: LjungBoxResultSchema.nullable(),
  interpretation: z.string(),
});
export type ResidualDiagnostics = z.infer<typeof ResidualDiagnosticsSchema>;

export const HorizonStepErrorSchema = z.object({
  horizon_step: z.number(),
  mae: z.number().nullable(),
  n_observations: z.number(),
});
export type HorizonStepError = z.infer<typeof HorizonStepErrorSchema>;

export const ForecastDiagnosticsResponseSchema = z.object({
  atc_class: z.string(),
  model: z.string(),
  metrics: ForecastMetricsSchema,
  residual_diagnostics: ResidualDiagnosticsSchema,
  performance_by_horizon_step: z.array(HorizonStepErrorSchema),
  limitations: z.array(z.string()),
});
export type ForecastDiagnosticsResponse = z.infer<typeof ForecastDiagnosticsResponseSchema>;

// ---------------------------------------------------------------------
// Optimization (backend/app/schemas/optimization.py)
// ---------------------------------------------------------------------

export const ScenarioNameSchema = z.enum(["conservative", "balanced", "lean"]);
export type ScenarioName = z.infer<typeof ScenarioNameSchema>;

export const AssumptionRowSchema = z.object({
  parameter: z.string(),
  value: z.union([z.string(), z.number(), z.boolean(), z.null()]),
  unit: z.string(),
  source: z.string(),
  type: z.string(),
});
export type AssumptionRow = z.infer<typeof AssumptionRowSchema>;

export const AtcPlanningResultSchema = z.object({
  atc_class: z.string(),
  model_used: z.string(),
  forecast: z.array(z.number().nullable()),
  forecast_dates: z.array(z.string()),
  lead_time_days: z.number(),
  service_level: z.number().nullable(),
  safety_stock: z.number().nullable(),
  reorder_point: z.number().nullable(),
  recommended_order_quantity: z.number().nullable(),
  inventory_exposure: z.number().nullable(),
  expected_shortage: z.number().nullable(),
});
export type AtcPlanningResult = z.infer<typeof AtcPlanningResultSchema>;

export const AllocationPolicySchema = z.object({
  policy_name: z.string(),
  solver_status: z.string(),
  total_capacity_budget: z.number().nullable(),
  total_safety_stock_allocated: z.number().nullable(),
  total_expected_shortage: z.number().nullable(),
  total_weighted_expected_shortage: z.number().nullable(),
});
export type AllocationPolicy = z.infer<typeof AllocationPolicySchema>;

export const OptimizationRunResponseSchema = z.object({
  scenario: z.string(),
  assumptions: z.array(AssumptionRowSchema),
  capacity_budget: z.number().nullable(),
  atc_results: z.record(z.string(), AtcPlanningResultSchema),
  allocation_baseline: AllocationPolicySchema,
  allocation_optimized: AllocationPolicySchema,
  improvement_pct: z.number().nullable(),
  warnings: z.array(z.string()).default([]),
});
export type OptimizationRunResponse = z.infer<typeof OptimizationRunResponseSchema>;

export const ScenarioInfoSchema = z.object({
  name: z.string(),
  service_level_target: z.number(),
  lead_time_days: z.number(),
  review_period_days: z.number(),
  rationale: z.string(),
});
export type ScenarioInfo = z.infer<typeof ScenarioInfoSchema>;

export const ScenariosResponseSchema = z.object({
  scenarios: z.array(ScenarioInfoSchema),
});
export type ScenariosResponse = z.infer<typeof ScenariosResponseSchema>;

export const SensitivityParameterSchema = z.enum([
  "lead_time_days",
  "service_level_target",
  "demand_uncertainty_scale",
  "stockout_cost_weight",
]);
export type SensitivityParameter = z.infer<typeof SensitivityParameterSchema>;

export const SensitivityPointSchema = z.object({
  value: z.number(),
  safety_stock: z.number().nullable(),
  reorder_point: z.number().nullable(),
});
export type SensitivityPoint = z.infer<typeof SensitivityPointSchema>;

export const SensitivityResponseSchema = z.object({
  atc_class: z.string(),
  parameter: SensitivityParameterSchema,
  points: z.array(SensitivityPointSchema),
  elasticity: z.number().nullable(),
});
export type SensitivityResponse = z.infer<typeof SensitivityResponseSchema>;

// ---------------------------------------------------------------------
// Recommendations (backend/app/schemas/recommendations.py)
// ---------------------------------------------------------------------

export const RecommendationItemSchema = z.object({
  atc_class: z.string(),
  recommendation: z.string(),
  evidence: z.array(z.string()),
  assumptions: z.array(z.string()),
  expected_effect: z.string(),
  confidence: z.string(),
  limitations: z.array(z.string()),
});
export type RecommendationItem = z.infer<typeof RecommendationItemSchema>;

export const RecommendationsResponseSchema = z.object({
  scenario: ScenarioNameSchema,
  recommendations: z.array(RecommendationItemSchema),
});
export type RecommendationsResponse = z.infer<typeof RecommendationsResponseSchema>;

// ---------------------------------------------------------------------
// Data quality (backend/app/schemas/data_quality.py)
// ---------------------------------------------------------------------

export const FileSummarySchema = z.object({
  file_name: z.string(),
  total_records: z.number(),
  valid_records: z.number(),
  rejected_records: z.number(),
});
export type FileSummary = z.infer<typeof FileSummarySchema>;

export const ReconciliationStatusSchema = z.object({
  label: z.string(),
  reconciled: z.boolean(),
  status: z.string(),
  note: z.string(),
});
export type ReconciliationStatus = z.infer<typeof ReconciliationStatusSchema>;

export const DataQualityResponseSchema = z.object({
  kaggle_dataset_id: z.string(),
  overall_status: z.string(),
  file_summaries: z.array(FileSummarySchema),
  reconciliation: z.array(ReconciliationStatusSchema),
  monthly_inconsistency_warning: z.string(),
});
export type DataQualityResponse = z.infer<typeof DataQualityResponseSchema>;

// ---------------------------------------------------------------------
// The 8 observed ATC classes (M1/M2) — not an API call, a static fact
// about the dataset used for client-side route validation (unknown ATC
// class -> not-found state) and select-input options.
// ---------------------------------------------------------------------

export const ATC_CLASSES = ["M01AB", "M01AE", "N02BA", "N02BE", "N05B", "N05C", "R03", "R06"] as const;
export type AtcClass = (typeof ATC_CLASSES)[number];

export function isKnownAtcClass(value: string): value is AtcClass {
  return (ATC_CLASSES as readonly string[]).includes(value);
}
