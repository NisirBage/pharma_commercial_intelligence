/**
 * MSW request handlers — realistic fixtures matching the Zod schemas in
 * src/types/api.ts exactly (mirroring the real backend contract), used
 * ONLY inside the test environment (src/test/setup.ts). These values are
 * plausible test doubles for exercising rendering/interaction logic —
 * never shown to a real user, and never a substitute for the one
 * real-backend integration check (see the M7.10/M7.11 report).
 */

import { http, HttpResponse } from "msw";

const API_BASE_URL = "http://localhost:8000";

function envelope<T>(data: T, source = "test-fixture") {
  return { data, metadata: { generated_at: new Date().toISOString(), source } };
}

export const handlers = [
  http.get(`${API_BASE_URL}/health`, () =>
    HttpResponse.json(envelope({ status: "ok", version: "1.0.0", environment: "test", database: "unreachable" })),
  ),

  http.get(`${API_BASE_URL}/api/v1/kpis/summary`, () =>
    HttpResponse.json(
      envelope({
        total_demand: 127595.5,
        average_daily_demand: 60.59,
        peak_daily_demand: 198.95,
        peak_date: "2016-12-30",
        dominant_atc_class: "N02BE",
        dominant_atc_share_pct: 49.38,
        period: { start: "2014-01-02", end: "2019-10-08" },
      }),
    ),
  ),

  http.get(`${API_BASE_URL}/api/v1/sales/trends`, () =>
    HttpResponse.json(
      envelope({
        atc_class: null,
        grain: "daily",
        start_date: "2014-01-02",
        end_date: "2019-10-08",
        points: [
          { period: "2019-10-06", units_sold: 58.4 },
          { period: "2019-10-07", units_sold: 61.2 },
          { period: "2019-10-08", units_sold: 55.9 },
        ],
      }),
    ),
  ),

  http.get(`${API_BASE_URL}/api/v1/analytics/atc`, () =>
    HttpResponse.json(
      envelope({
        classes: [
          {
            atc_class: "N02BE",
            total_demand: 63005.4,
            average_daily_demand: 29.9,
            peak_daily_demand: 120.3,
            trough_daily_demand: 0,
            contribution_pct: 49.38,
            trend_slope: -0.7,
            trend_classification: "stable_or_no_significant_trend",
            trend_p_value: 0.42,
            volatility_cv: 0.52,
          },
          {
            atc_class: "R03",
            total_demand: 11608.8,
            average_daily_demand: 5.51,
            peak_daily_demand: 45.0,
            trough_daily_demand: 0,
            contribution_pct: 9.1,
            trend_slope: 1.58,
            trend_classification: "growing",
            trend_p_value: 0.01,
            volatility_cv: 1.17,
          },
        ],
        dominant_classes: ["N02BE", "N05B", "R03"],
        concentration: {
          ranked: [
            { atc_code: "N02BE", share_pct: 49.38, cumulative_share_pct: 49.38 },
            { atc_code: "N05B", share_pct: 14.61, cumulative_share_pct: 63.99 },
          ],
          concentration_ratio_top3_pct: 73.09,
          hhi: 2909.9,
          hhi_scale_note: "0-10000 scale.",
        },
      }),
    ),
  ),

  http.get(`${API_BASE_URL}/api/v1/analytics/anomalies`, () =>
    HttpResponse.json(
      envelope({
        atc_class: null,
        method: "rolling_zscore",
        total_count: 2,
        anomalies: [
          {
            atc_class: "N05C",
            timestamp: "2018-02-27",
            observed: 9.0,
            expected: 0.13,
            deviation_pct: 6650.0,
            anomaly_score: 15.5,
            direction: "above",
            severity: "high",
            method: "rolling_zscore",
          },
          {
            atc_class: "R03",
            timestamp: "2019-09-26",
            observed: 31.0,
            expected: 2.88,
            deviation_pct: 976.2,
            anomaly_score: 10.9,
            direction: "above",
            severity: "high",
            method: "rolling_zscore",
          },
        ],
      }),
    ),
  ),

  http.get(`${API_BASE_URL}/api/v1/analytics/seasonality`, () =>
    HttpResponse.json(
      envelope({
        atc_class: "ALL",
        day_of_week_effect: {
          h_statistic: 25.9,
          p_value: 0.0002,
          significant: true,
          mean_units_by_weekday: { Monday: 60.6, Saturday: 65.7 },
          available: true,
          reason: null,
        },
        hour_of_day_effect: {
          h_statistic: 56949.9,
          p_value: 0,
          significant: true,
          mean_units_by_hour: { "8": 0.36, "12": 0.63 },
          available: true,
          reason: null,
        },
        weekly_seasonal_strength: {
          strength: 0.234,
          cycle_period: 7,
          n_periods: 2106,
          interpretation: "0 = no seasonality, ~1 = strong seasonality.",
          available: true,
          reason: null,
        },
        annual_seasonal_strength: {
          strength: 0.553,
          cycle_period: 12,
          n_periods: 70,
          interpretation: "0 = no seasonality, ~1 = strong seasonality.",
          available: true,
          reason: null,
        },
      }),
    ),
  ),

  http.get(`${API_BASE_URL}/api/v1/forecast/aggregate`, () =>
    HttpResponse.json(
      envelope({
        atc_class: "ALL",
        horizon_days: 14,
        model: "ets",
        uncertainty_method: "ets_native_prediction_interval",
        forecast: [{ date: "2019-10-09", prediction: 64.7, lower: 35.0, upper: 94.4 }],
        metrics: { mae: 11.46, rmse: 14.99, wape: 16.27, mase: 0.66 },
      }),
    ),
  ),

  http.get(`${API_BASE_URL}/api/v1/forecast/:atcClass`, ({ params }) =>
    HttpResponse.json(
      envelope({
        atc_class: params.atcClass,
        horizon_days: 14,
        model: "moving_average_14",
        uncertainty_method: "residual_based_backtest_quantile",
        forecast: [{ date: "2019-10-09", prediction: 30.2, lower: 18.0, upper: 42.0 }],
        metrics: { mae: 8.44, rmse: 11.07, wape: 33.71, mase: 0.74 },
      }),
    ),
  ),

  http.get(`${API_BASE_URL}/api/v1/forecast/:atcClass/diagnostics`, ({ params }) =>
    HttpResponse.json(
      envelope({
        atc_class: params.atcClass,
        model: "moving_average_14",
        metrics: { mae: 8.44, rmse: 11.07, wape: 33.71, mase: 0.74 },
        residual_diagnostics: {
          n_residuals: 84,
          mean_residual: 3.54,
          std_residual: 11.55,
          pct_days_underpredicted: 56.0,
          pct_days_overpredicted: 44.0,
          ljung_box: { lags: 7, lb_stat: 25.1, lb_pvalue: 0.00007, autocorrelation_detected: true },
          interpretation: "mean_residual > 0 => systematic underprediction on average.",
        },
        performance_by_horizon_step: [{ horizon_step: 1, mae: 5.2, n_observations: 6 }],
        limitations: ["Residual diagnostics are computed from M4's 6 backtest validation folds."],
      }),
    ),
  ),

  http.get(`${API_BASE_URL}/api/v1/optimization/scenarios`, () =>
    HttpResponse.json(
      envelope({
        scenarios: [
          { name: "conservative", service_level_target: 0.98, lead_time_days: 7, review_period_days: 7, rationale: "Highest service-level target." },
          { name: "balanced", service_level_target: 0.95, lead_time_days: 7, review_period_days: 7, rationale: "Middle service-level target." },
          { name: "lean", service_level_target: 0.9, lead_time_days: 7, review_period_days: 7, rationale: "Lowest service-level target." },
        ],
      }),
    ),
  ),

  http.get(`${API_BASE_URL}/api/v1/optimization/sensitivity`, () =>
    HttpResponse.json(
      envelope({
        atc_class: "N02BE",
        parameter: "service_level_target",
        points: [
          { value: 0.8, safety_stock: 19.0, reorder_point: 301.5 },
          { value: 0.95, safety_stock: 38.0, reorder_point: 320.5 },
        ],
        elasticity: 1.0,
      }),
    ),
  ),

  http.post(`${API_BASE_URL}/api/v1/optimization/run`, () =>
    HttpResponse.json(
      envelope({
        scenario: "balanced",
        assumptions: [{ parameter: "lead_time_days", value: 7, unit: "days", source: "scenario", type: "assumption" }],
        capacity_budget: 103.66,
        atc_results: {
          N02BE: {
            atc_class: "N02BE",
            model_used: "moving_average_14",
            forecast: [30.2],
            forecast_dates: ["2019-10-09"],
            lead_time_days: 7,
            service_level: 0.95,
            safety_stock: 51.94,
            reorder_point: 262.0,
            recommended_order_quantity: 60.0,
            inventory_exposure: 51.94,
            expected_shortage: 2.1,
          },
        },
        allocation_baseline: {
          policy_name: "baseline",
          solver_status: "n/a (closed form)",
          total_capacity_budget: 103.66,
          total_safety_stock_allocated: 103.66,
          total_expected_shortage: 10.0,
          total_weighted_expected_shortage: 25.0,
        },
        allocation_optimized: {
          policy_name: "optimized",
          solver_status: "optimal",
          total_capacity_budget: 103.66,
          total_safety_stock_allocated: 103.66,
          total_expected_shortage: 6.0,
          total_weighted_expected_shortage: 12.86,
        },
        improvement_pct: 48.6,
        warnings: [],
      }),
    ),
  ),

  http.get(`${API_BASE_URL}/api/v1/recommendations`, () =>
    HttpResponse.json(
      envelope({
        scenario: "balanced",
        recommendations: [
          {
            atc_class: "N02BE",
            recommendation: "Treat N02BE as high planning exposure.",
            evidence: ["N02BE represents ~49% of total observed demand."],
            assumptions: ["lead_time_days and service_level_target are scenario assumptions."],
            expected_effect: "A given percentage forecast error translates to a larger absolute unit shortfall.",
            confidence: "medium",
            limitations: ["This recommendation is a scenario simulation, not a real-world business commitment."],
          },
        ],
      }),
    ),
  ),

  http.get(`${API_BASE_URL}/api/v1/data-quality`, () =>
    HttpResponse.json(
      envelope({
        kaggle_dataset_id: "milanzdravkovic/pharma-sales-data",
        overall_status: "warn",
        file_summaries: [{ file_name: "saleshourly.csv", total_records: 50532, valid_records: 50532, rejected_records: 0 }],
        reconciliation: [
          { label: "Daily", reconciled: true, status: "pass", note: "Reconciled" },
          { label: "Weekly", reconciled: true, status: "pass", note: "Reconciled" },
          { label: "Monthly", reconciled: false, status: "warn", note: "Known source inconsistency" },
        ],
        monthly_inconsistency_warning: "salesmonthly.csv does not reconcile with the daily-grain sum.",
      }),
    ),
  ),
];
