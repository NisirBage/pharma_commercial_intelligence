import { useQuery } from "@tanstack/react-query";
import { getRecommendations } from "../api/recommendations";
import { STALE_TIME } from "../lib/queryConfig";
import { queryKeys } from "../lib/queryKeys";
import type { ScenarioName } from "../types/api";

export function useRecommendations(scenario?: ScenarioName) {
  return useQuery({
    queryKey: queryKeys.recommendations(scenario),
    queryFn: ({ signal }) => getRecommendations(scenario, signal),
    staleTime: STALE_TIME.MEDIUM,
  });
}
