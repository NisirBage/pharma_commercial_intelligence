import { get } from "./client";
import {
  ForecastResponseSchema,
  ForecastDiagnosticsResponseSchema,
  type ForecastResponse,
  type ForecastDiagnosticsResponse,
} from "../types/api";

/** GET /api/v1/forecast/{atc_class} — never re-triggers M4's backtest;
 * reads M4's already-selected, already-backtested model (see M6's
 * lru_cache-based cache, docs/api-design.md). */
export function getForecast(atcClass: string, signal?: AbortSignal): Promise<ForecastResponse> {
  return get(`/api/v1/forecast/${encodeURIComponent(atcClass)}`, ForecastResponseSchema, undefined, signal);
}

/** GET /api/v1/forecast/aggregate — the DIRECT aggregate model M4 found
 * more accurate than summing the 8 per-class forecasts. Never derive an
 * "aggregate" client-side by summing per-class forecast calls instead of
 * calling this endpoint — that would silently reproduce the less-accurate
 * approach M4's own backtest rejected. */
export function getAggregateForecast(signal?: AbortSignal): Promise<ForecastResponse> {
  return get("/api/v1/forecast/aggregate", ForecastResponseSchema, undefined, signal);
}

export function getForecastDiagnostics(atcClass: string, signal?: AbortSignal): Promise<ForecastDiagnosticsResponse> {
  return get(
    `/api/v1/forecast/${encodeURIComponent(atcClass)}/diagnostics`,
    ForecastDiagnosticsResponseSchema,
    undefined,
    signal,
  );
}
