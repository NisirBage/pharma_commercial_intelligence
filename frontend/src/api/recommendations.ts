import { get } from "./client";
import { RecommendationsResponseSchema, type ScenarioName, type RecommendationsResponse } from "../types/api";

export function getRecommendations(scenario?: ScenarioName, signal?: AbortSignal): Promise<RecommendationsResponse> {
  return get("/api/v1/recommendations", RecommendationsResponseSchema, { scenario }, signal);
}
