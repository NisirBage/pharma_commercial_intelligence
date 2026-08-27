import type { GetAnomaliesParams } from "../api/anomalies";
import type { GetSensitivityParams, RunOptimizationBody } from "../api/optimization";
import type { GetSalesTrendsParams } from "../api/sales";
import type { ScenarioName } from "../types/api";

/** Every TanStack Query key used in the app, in one place — so cache
 * invalidation/sharing (e.g. Overview and Supply Planning both reading a
 * "balanced" optimization run) is never done by guessing a matching
 * array shape in two different files. */
export const queryKeys = {
  health: ["health"] as const,
  kpiSummary: ["kpiSummary"] as const,
  salesTrends: (params: GetSalesTrendsParams) => ["salesTrends", params] as const,
  atcAnalytics: ["atcAnalytics"] as const,
  seasonality: (atcClass?: string) => ["seasonality", atcClass ?? "ALL"] as const,
  anomalies: (params: GetAnomaliesParams) => ["anomalies", params] as const,
  forecast: (atcClass: string) => ["forecast", atcClass] as const,
  aggregateForecast: ["forecast", "aggregate"] as const,
  forecastDiagnostics: (atcClass: string) => ["forecastDiagnostics", atcClass] as const,
  optimizationScenarios: ["optimizationScenarios"] as const,
  optimizationSensitivity: (params: GetSensitivityParams) => ["optimizationSensitivity", params] as const,
  optimizationRun: (body: RunOptimizationBody) => ["optimizationRun", body] as const,
  recommendations: (scenario?: ScenarioName) => ["recommendations", scenario ?? "balanced"] as const,
  dataQuality: ["dataQuality"] as const,
};
