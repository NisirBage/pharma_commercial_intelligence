import { get } from "./client";
import { AnomaliesResponseSchema, type AnomalyMethod, type AnomaliesResponse } from "../types/api";

export interface GetAnomaliesParams {
  atcClass?: string;
  method?: AnomalyMethod;
  severity?: string;
  startDate?: string;
  endDate?: string;
}

export function getAnomalies(params: GetAnomaliesParams = {}, signal?: AbortSignal): Promise<AnomaliesResponse> {
  return get(
    "/api/v1/analytics/anomalies",
    AnomaliesResponseSchema,
    {
      atc_class: params.atcClass,
      method: params.method,
      severity: params.severity,
      start_date: params.startDate,
      end_date: params.endDate,
    },
    signal,
  );
}
