import { get } from "./client";
import { KpiSummarySchema, type KpiSummary } from "../types/api";

export function getKpiSummary(signal?: AbortSignal): Promise<KpiSummary> {
  return get("/api/v1/kpis/summary", KpiSummarySchema, undefined, signal);
}
