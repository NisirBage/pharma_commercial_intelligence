import { get } from "./client";
import {
  AtcPerformanceResponseSchema,
  SeasonalityResponseSchema,
  type AtcPerformanceResponse,
  type SeasonalityResponse,
} from "../types/api";

export function getAtcAnalytics(signal?: AbortSignal): Promise<AtcPerformanceResponse> {
  return get("/api/v1/analytics/atc", AtcPerformanceResponseSchema, undefined, signal);
}

/** GET /api/v1/analytics/seasonality — M7.1.5. `atcClass` omitted returns
 * the aggregate across all 8 classes. */
export function getSeasonality(atcClass?: string, signal?: AbortSignal): Promise<SeasonalityResponse> {
  return get("/api/v1/analytics/seasonality", SeasonalityResponseSchema, { atc_class: atcClass }, signal);
}
