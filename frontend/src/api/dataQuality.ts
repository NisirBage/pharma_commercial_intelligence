import { get } from "./client";
import { DataQualityResponseSchema, type DataQualityResponse } from "../types/api";

export function getDataQuality(signal?: AbortSignal): Promise<DataQualityResponse> {
  return get("/api/v1/data-quality", DataQualityResponseSchema, undefined, signal);
}
